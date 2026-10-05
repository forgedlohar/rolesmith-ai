"""Match incoming emails to applied jobs using multi-signal scoring.
Based on career-flow's heuristic matcher.
"""

import logging
import re
from datetime import datetime
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Known ATS notification sender patterns
ATS_SENDER_PATTERNS = {
    "greenhouse.io",
    "lever.co",
    "icims.com",
    "myworkdayjobs.com",
    "jobvite.com",
    "smartrecruiters.com",
    "workable.com",
    "ashbyhq.com",
    "breezy.hr",
    "recruitee.com",
    "jazz.co",
}

ATS_SENDER_PREFIXES = {"noreply", "no-reply", "notifications", "careers", "jobs", "talent", "recruiting"}

_COMPANY_SUBJECT_PATTERNS = [
    r"(?:applying|applied)\s+(?:to|at)\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are|will|would)\b|$)",
    r"(?:position|role|job|opportunity)\s+at\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are|will|would)\b|$)",
    r"(?:application|interest)\s+(?:to|at|in|for)\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are|will|would)\b|$)",
    r"for\s+your\s+(?:application|interest)\s+(?:to|at|in)\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are|will|would)\b|$)",
    r"security\s+code\s+for\s+your\s+application\s+to\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are)\b|$)",
    r"information\s+about\s+your\s+application\s+to\s+(.+?)(?:\s*[!.,]|\s+\b(?:has|have|had|was|is|are)\b|$)",
    r"thank\s+you\s+from\s+(.+?)(?:\s*[!.,]|$)",
    r"^(.+?)\s*[:|]\s+(?:thank\s+you|we\s+received|application|your\s+application)",
]

_GENERIC_WORDS = {"us", "the", "you", "your", "we", "our", "it", "a", "an", "this", "that", "they", "their", "its"}

_JOB_TITLE_WORDS = {
    "engineer",
    "developer",
    "manager",
    "director",
    "analyst",
    "scientist",
    "architect",
    "designer",
    "consultant",
    "specialist",
    "coordinator",
    "senior",
    "junior",
    "staff",
    "principal",
    "associate",
    "lead",
    "head",
    "vp",
    "vice",
    "president",
    "officer",
    "cto",
    "ceo",
    "cfo",
    "coo",
}

_LEGAL_SUFFIXES = re.compile(
    r"\s*,?\s+(?:inc|llc|ltd|corp|co|plc|gmbh|ag|sa|bv|nv|pty|pte|srl|sas|sro)\.?\s*$",
    re.IGNORECASE,
)


def extract_company_from_subject(subject: str) -> str | None:
    s = subject.strip()
    for pattern in _COMPANY_SUBJECT_PATTERNS:
        m = re.search(pattern, s, re.IGNORECASE)
        if not m:
            continue
        candidate = m.group(1).strip().strip("!.,")
        if not candidate or len(candidate) < 2:
            continue
        if candidate.lower() in _GENERIC_WORDS:
            continue
        if len(candidate.split()) > 5:
            continue
        candidate_words = set(candidate.lower().split())
        if candidate_words & _JOB_TITLE_WORDS:
            continue
        return candidate
    return None


def normalize_company(name: str) -> str:
    if not name:
        return ""
    n = _LEGAL_SUFFIXES.sub("", name)
    n = re.sub(r"[^\w\s]", "", n)
    return n.lower().strip()


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _extract_domain(address: str) -> str:
    if "@" in address:
        return address.split("@")[-1].strip().lower()
    try:
        parsed = urlparse(address)
        host = parsed.hostname or ""
        return host.lower()
    except Exception:
        return address.lower()


def _domain_root(domain: str) -> str:
    parts = domain.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def _title_keywords(title: str | None) -> set[str]:
    if not title:
        return set()
    stops = {"the", "a", "an", "and", "or", "at", "in", "for", "of", "to", "with", "is", "are", "we"}
    words = re.findall(r"[a-z]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in stops}


def match_email_to_job(email: dict, applied_jobs: list[dict]) -> dict | None:
    """Match a single email to the best applied job."""
    sender = email.get("sender", "")
    sender_domain = _extract_domain(sender)
    sender_root = _domain_root(sender_domain)
    sender_local = sender.split("@")[0].lower() if "@" in sender else ""
    subject = (email.get("subject") or "").lower()
    body = (email.get("body") or "").lower()
    email_date_str = email.get("date", "")

    email_dt = None
    if email_date_str:
        try:
            email_dt = datetime.fromisoformat(email_date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    subject_company_raw = extract_company_from_subject(email.get("subject") or "")
    subject_company_norm = normalize_company(subject_company_raw) if subject_company_raw else ""

    best_match = None
    best_score = 0

    for job in applied_jobs:
        score = 0
        signals = []

        job_url = job.get("job_url", job.get("url", ""))
        company = (job.get("company") or "").lower()
        title = job.get("title") or ""

        score += 20  # baseline for DB job

        if sender_root:
            if company and len(company) > 3 and (company in sender_root or sender_root.split(".")[0] == company):
                score += 40
                signals.append(f"company_in_domain:{company}")

        if company and len(company) > 2:
            if company in subject:
                score += 25
                signals.append(f"company_in_subject:{company}")
            elif company in body[:2000]:
                score += 15
                signals.append(f"company_in_body:{company}")

        title_kw = _title_keywords(title)
        if title_kw:
            subject_words = set(re.findall(r"[a-z]+", subject))
            overlap = title_kw & subject_words
            if len(overlap) >= 2:
                score += 20
                signals.append(f"title_overlap:{','.join(overlap)}")
            elif len(overlap) == 1:
                score += 10
                signals.append(f"title_partial:{','.join(overlap)}")

        is_ats = any(ats in sender_domain for ats in ATS_SENDER_PATTERNS) or sender_local in ATS_SENDER_PREFIXES
        if is_ats:
            score += 10
            signals.append("ats_sender")

        if email_dt and job.get("applied_at"):
            try:
                applied_dt = datetime.fromisoformat(job["applied_at"].replace("Z", "+00:00"))
                delta_days = abs((email_dt - applied_dt).days)
                if delta_days <= 30:
                    score += 5
                    signals.append(f"temporal:{delta_days}d")
            except (ValueError, TypeError):
                pass

        if subject_company_norm and company and len(subject_company_norm) > 2:
            job_company_norm = normalize_company(company)
            subj_slug = _slug(subject_company_norm)
            job_slug = _slug(job_company_norm) if job_company_norm else ""
            if job_company_norm and (
                subject_company_norm == job_company_norm
                or subject_company_norm in job_company_norm
                or job_company_norm in subject_company_norm
                or (subj_slug and job_slug and (subj_slug == job_slug or subj_slug in job_slug or job_slug in subj_slug))
            ):
                score += 35
                signals.append(f"subject_company:{subject_company_raw}")

        if score >= 40 and score > best_score:
            best_score = score
            best_match = {
                "job_url": job_url,
                "score": score,
                "signals": signals,
            }

    if best_match:
        log.debug(f"Best match: {best_match['job_url'][:60]} (score: {best_match['score']})")
    return best_match
