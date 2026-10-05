import base64
import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field

from rolesmith_ai.config import APP_DIR, load_config
from rolesmith_ai.pipeline.llm import _call_api, complete_json
from rolesmith_ai.store import _connect
from rolesmith_ai.tools.matcher import match_email_to_job

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]
logger = logging.getLogger(__name__)


def get_gmail_service():
    """Authenticate and return the Gmail API service."""
    creds = None
    token_path = APP_DIR / "token.json"
    credentials_path = APP_DIR / "credentials.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(f"Missing {credentials_path}. Please download your OAuth 2.0 Client ID JSON from Google Cloud Console and save it to this path.")
            # Run local server to authenticate
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_draft_reply(service, message_id, thread_id, to_email, subject, reply_body):
    """Create a draft reply to a specific email."""
    try:
        message = EmailMessage()
        message.set_content(reply_body)
        message["To"] = to_email
        message["Subject"] = subject if subject.startswith("Re:") else f"Re: {subject}"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"message": {"raw": encoded_message, "threadId": thread_id}}
        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        return draft["id"]
    except HttpError as error:
        logger.error(f"Failed to create draft: {error}")
        return None


def get_message_body(payload):
    """Recursively extract plain text body from the email payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"].get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8")
            elif "parts" in part:
                return get_message_body(part)
    elif payload.get("mimeType") == "text/plain":
        data = payload["body"].get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8")
    return ""


class Person(BaseModel):
    name: str = Field(description="Name of the person")
    title: Optional[str] = Field(None, description="Job title if mentioned")
    email: Optional[str] = Field(None, description="Email address if mentioned")


class DateItem(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD or descriptive text")
    description: str = Field(description="What is happening on this date")


class ActionItem(BaseModel):
    task: str = Field(description="Task to complete")
    deadline: Optional[str] = Field(None, description="Deadline if provided")


class EmailClassification(BaseModel):
    classification: str = Field(description="Must be one of: confirmation, rejection, interview, follow_up, offer, noise")
    should_reply: bool = Field(description="Whether we should draft a reply to this email")
    reply_draft: str = Field(description="Draft response text if should_reply is True, otherwise empty string")
    summary: str = Field(description="One-sentence summary of the email")
    people: List[Person] = Field(default_factory=list)
    dates: List[DateItem] = Field(default_factory=list)
    action_items: List[ActionItem] = Field(default_factory=list)


def check_job_emails() -> dict:
    """Scan unread emails, identify recruiter/job emails, and draft replies using LLM."""
    try:
        service = get_gmail_service()
    except Exception as e:
        return {"status": "error", "message": f"Gmail Auth failed: {str(e)}"}

    config = load_config()
    candidate_context = f"Name: {config.name}\\nEmail: {config.email}\\nPhone: {config.phone}\\nLocation: {config.location}\\nYears of Experience: {config.experience_years}"

    try:
        # Search for recent unread emails that might be job related
        query = "is:unread (subject:job OR subject:interview OR subject:application OR subject:offer OR from:workday OR from:greenhouse)"
        results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = results.get("messages", [])

        if not messages:
            return {"status": "success", "message": "No new job-related emails found.", "drafts_created": 0}

        # Get all applied jobs for matching
        with _connect() as conn:
            cur = conn.execute("SELECT j.url as job_url, j.title, j.company, a.applied_at FROM jobs j JOIN applications a ON j.url = a.job_url WHERE a.status NOT IN ('rejected', 'offer', 'ghosted')")
            applied_jobs = [dict(r) for r in cur.fetchall()]

        drafts_created = 0
        for msg_meta in messages:
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
            date_str = next((h["value"] for h in headers if h["name"].lower() == "date"), "")

            body = get_message_body(payload)
            snippet = msg.get("snippet", "")
            content_to_analyze = body if body else snippet

            if not content_to_analyze.strip():
                continue

            email_dict = {"sender": sender, "subject": subject, "body": content_to_analyze, "date": date_str}

            match = match_email_to_job(email_dict, applied_jobs)
            if match:
                logger.info(f"Matched email '{subject}' to job URL: {match['job_url']} with score {match['score']}")

            system_prompt = (
                "You are an email classifier and reply drafter for an Application Tracking System.\n"
                f"Candidate Profile:\n{candidate_context}\n\n"
                "Classify the email into exactly one category:\n"
                "- confirmation: Application receipt acknowledged\n"
                "- rejection: Candidate not selected\n"
                "- interview: Interview invitation or scheduling\n"
                "- follow_up: Request for additional info or assessments\n"
                "- offer: Job offer or compensation discussion\n"
                "- noise: Marketing, newsletters, unrelated\n\n"
                "Extract people, dates, and action items. If should_reply is true, provide a reply_draft."
            )

            user_prompt = f"Email from: {sender}\nSubject: {subject}\nDate: {date_str}\nContent:\n{content_to_analyze[:3000]}\n\n"

            try:
                result = complete_json(system_prompt, user_prompt, EmailClassification)

                # Advance state machine in DB if matched
                if match and result.classification != "noise":
                    # map classification to DB status (if applicable)
                    new_status = None
                    if result.classification == "rejection":
                        new_status = "rejected"
                    elif result.classification == "interview":
                        new_status = "interviewing"
                    elif result.classification == "offer":
                        new_status = "offer"

                    if new_status:
                        with _connect() as conn:
                            conn.execute("UPDATE applications SET status = ? WHERE job_url = ?", (new_status, match["job_url"]))
                            # Also update jobs table for consistency
                            conn.execute("UPDATE jobs SET status = ? WHERE url = ?", (new_status, match["job_url"]))
                            conn.commit()
                        logger.info(f"Updated job {match['job_url']} status to {new_status}")

                if result.should_reply and result.reply_draft:
                    draft_id = create_draft_reply(service, msg["id"], msg["threadId"], sender, subject, result.reply_draft)

                    if draft_id:
                        drafts_created += 1
                        # Mark as read so we don't process it again
                        service.users().messages().modify(userId="me", id=msg["id"], body={"removeLabelIds": ["UNREAD"]}).execute()
                        logger.info(f"Created draft reply for email from {sender} (Classification: {result.classification})")

                        if result.classification == "interview":
                            _generate_prep_sheet(sender, subject, content_to_analyze)
            except Exception as e:
                logger.error(f"Failed to process email {msg['id']}: {e}")

        return {"status": "success", "message": f"Processed {len(messages)} emails. Created {drafts_created} drafts.", "drafts_created": drafts_created}

    except HttpError as error:
        return {"status": "error", "message": f"Gmail API error: {error}"}


def _generate_prep_sheet(sender: str, subject: str, email_content: str):
    """Generate a markdown interview prep sheet when an interview is detected."""
    prompt = (
        f"Email from: {sender}\\nSubject: {subject}\\nContent:\\n{email_content[:2000]}\\n\\n"
        "Based on this interview request, generate a markdown 'Interview Prep Cheat Sheet'. "
        "Include a summary of what you can infer about the company, the job role, and list 5 likely "
        "technical or behavioral questions they will ask. Be concise and professional."
    )

    try:
        prep_sheet_md = _call_api(prompt, 8000)

        # Save to file
        safe_name = "".join([c if c.isalnum() else "_" for c in sender.split("@")[0]])
        filepath = APP_DIR / f"interview_prep_{safe_name}.md"
        with open(filepath, "w") as f:
            f.write(prep_sheet_md)
        logger.info(f"Generated interview prep sheet at {filepath}")
    except Exception as e:
        logger.error(f"Failed to generate prep sheet: {e}")


def draft_followups() -> dict:
    """Draft follow-up emails for jobs applied to over 7 days ago with no response."""
    try:
        service = get_gmail_service()
    except Exception as e:
        return {"status": "error", "message": f"Gmail Auth failed: {str(e)}"}

    config = load_config()

    with _connect() as conn:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        cur = conn.execute(
            """
            SELECT a.job_url, j.company, j.title, a.applied_at 
            FROM applications a
            JOIN jobs j ON a.job_url = j.url
            WHERE a.status = 'applied' AND a.applied_at < ?
            LIMIT 50
            """,
            (seven_days_ago,),
        )
        old_applications = [dict(r) for r in cur.fetchall()]

    if not old_applications:
        return {"status": "success", "message": "No old applications needing follow-up.", "drafts_created": 0}

    drafts_created = 0
    for app in old_applications:
        try:
            to_email = ""
            subject = f"Following up: Application for {app['title']} at {app['company']}"

            body = (
                f"Hi Hiring Team,\n\n"
                f"I hope this email finds you well.\n\n"
                f"I am writing to follow up on my application for the {app['title']} position submitted recently. "
                f"I remain very interested in the opportunity to join {app['company']} and would love to know if there are any updates regarding my candidacy.\n\n"
                f"Please let me know if you need any additional information or work samples from my end.\n\n"
                f"Best regards,\n"
                f"{config.name}\n"
                f"{config.phone}"
            )

            message = EmailMessage()
            message.set_content(body)
            message["To"] = to_email
            message["Subject"] = subject

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"message": {"raw": encoded_message}}

            service.users().drafts().create(userId="me", body=create_message).execute()

            conn = _connect()
            conn.execute("UPDATE applications SET status = 'followed_up' WHERE job_url = ?", (app["job_url"],))
            conn.commit()
            conn.close()

            drafts_created += 1
        except Exception as e:
            logger.error(f"Failed to create follow-up for {app['company']}: {e}")

    return {"status": "success", "message": f"Created {drafts_created} follow-up drafts.", "drafts_created": drafts_created}
