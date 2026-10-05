import base64
import logging
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel

from rolesmith_ai.config import APP_DIR, load_config
from rolesmith_ai.pipeline.llm import complete_json

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
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


class ReplyDecision(BaseModel):
    should_reply: bool
    reason: str
    reply_draft: str


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

        drafts_created = 0
        for msg_meta in messages:
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])

            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")

            body = get_message_body(payload)
            snippet = msg.get("snippet", "")
            content_to_analyze = body if body else snippet

            if not content_to_analyze.strip():
                continue

            # Check if we should reply and what to say
            system_prompt = f"You are an AI assistant managing job applications for the candidate.\nCandidate Profile:\n{candidate_context}"
            user_prompt = (
                f"Email from: {sender}\nSubject: {subject}\nContent:\n{content_to_analyze[:2000]}\n\n"
                "Determine if this email requires a reply (e.g., asking for availability for an interview, "
                "asking for more information, offer negotiation). If it's an automated rejection or a "
                "do-not-reply email, DO NOT reply."
            )

            try:
                result = complete_json(system_prompt, user_prompt, ReplyDecision)

                if result.should_reply and result.reply_draft:
                    draft_id = create_draft_reply(service, msg["id"], msg["threadId"], sender, subject, result.reply_draft)

                    if draft_id:
                        drafts_created += 1
                        # Mark as read so we don't process it again
                        service.users().messages().modify(userId="me", id=msg["id"], body={"removeLabelIds": ["UNREAD"]}).execute()
                        logger.info(f"Created draft reply for email from {sender}")
            except Exception as e:
                logger.error(f"Failed to process email {msg['id']}: {e}")

        return {"status": "success", "message": f"Processed {len(messages)} emails. Created {drafts_created} drafts.", "drafts_created": drafts_created}

    except HttpError as error:
        return {"status": "error", "message": f"Gmail API error: {error}"}
