"""
email_utils.py - Gmail API integration for sending and receiving emails.
SSL certificates configured in main.py.
"""
import os
import base64
import logging
import asyncio
from typing import List, Optional
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth
    import httplib2
    import google_auth_httplib2
    GOOGLE_API_CLIENT_AVAILABLE = True
except ImportError:
    GOOGLE_API_CLIENT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GMAIL_IMPERSONATE_USER = os.environ.get("GMAIL_IMPERSONATE_USER", "user@example.com")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", GMAIL_IMPERSONATE_USER)
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "").split(",")


def normalize_google_credentials_path() -> None:
    """Expand and validate GOOGLE_APPLICATION_CREDENTIALS for local runs."""
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        return

    normalized_path = os.path.abspath(os.path.expandvars(os.path.expanduser(creds_path)))
    if os.path.exists(normalized_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = normalized_path
    else:
        logger.debug("Removing non-existent GOOGLE_APPLICATION_CREDENTIALS: %s", normalized_path)
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


normalize_google_credentials_path()

def is_email_configured() -> bool:
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.warning("Email configuration incomplete: Google API libraries not installed")
        return False
    if not GMAIL_IMPERSONATE_USER or GMAIL_IMPERSONATE_USER == "user@example.com":
        logger.warning("Email configuration incomplete: GMAIL_IMPERSONATE_USER is not set")
        return False
    return True

def get_gmail_service(scopes: List[str]):
    """
    Initialize Gmail API service using Application Default Credentials.
    SSL certificates configured in main.py via certifi.
    """
    normalize_google_credentials_path()
    
    # Use Application Default Credentials
    creds, _ = google.auth.default(scopes=scopes)
    
    # Use a configured transport timeout to avoid httplib2 timeout warnings.
    http = httplib2.Http(timeout=60)

    # If using service account, delegate to impersonate user
    if hasattr(creds, 'with_subject'):
        delegated_creds = creds.with_subject(GMAIL_IMPERSONATE_USER)
        authed_http = google_auth_httplib2.AuthorizedHttp(delegated_creds, http=http)
        return build('gmail', 'v1', http=authed_http, cache_discovery=False)
    else:
        authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
        return build('gmail', 'v1', http=authed_http, cache_discovery=False)


def get_gmail_send_service():
    """Gmail service with full scope for sending emails."""
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.modify'])


def get_gmail_read_service():
    """Gmail service with full scope for reading emails."""
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.modify'])


async def send_email_with_attachments(
    subject: str,
    body: str,
    to_email: str,
    attachments: Optional[List[str]] = None
) -> bool:
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return False

    if not is_email_configured():
        return False

    try:
        service = get_gmail_send_service()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {e}")
        return False

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    message = MIMEMultipart()
    message['To'] = to_email
    message['From'] = EMAIL_SENDER
    message['Subject'] = subject

    message.attach(MIMEText(body, 'html'))

    try:
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(file_path)}",
                    )
                    message.attach(part)
                    logger.info(f"Attached file: {os.path.basename(file_path)}")
                except FileNotFoundError:
                    logger.error(f"Attachment file not found: {file_path}. Skipping.")
                except Exception as e:
                    logger.error(f"Error attaching file {file_path}: {e}")

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        logger.info(f"Sending email via Gmail API to {to_email}...")
        sent_message = await asyncio.to_thread(lambda: service.users().messages().send(userId="me", body=create_message).execute())
        logger.info(f"Email sent successfully! Message ID: {sent_message['id']}")
        return True

    except HttpError as error:
        logger.error(f"An error occurred sending email via Gmail API: {error}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error while sending email: {e}")
        return False

async def fetch_unread_replies(
    domains: List[str],
    supplier_emails: Optional[List[str]] = None,
    include_read: bool = False,
    since_datetime: Optional[datetime] = None,
    recipient_email: Optional[str] = None,
    subject_phrase: Optional[str] = None,
) -> List[dict]:
    """
    Fetches unread emails from a list of supplier domains.
    Returns a list of dicts with 'id', 'from', 'subject', 'body', 'date'.
    """
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return []

    try:
        service = get_gmail_read_service()
    except Exception as e:
        logger.error(f"Failed to initialize Gmail read service: {e}")
        return []

    sender_terms = []
    # Prefer exact supplier email IDs, but include supplier domains too since
    # many vendors reply from different aliases within the same domain.
    if supplier_emails:
        sender_terms.extend([f"from:{email}" for email in supplier_emails if email])
    if domains:
        sender_terms.extend([f"from:{domain}" for domain in domains if domain])

    sender_clause = " OR ".join(sender_terms) if sender_terms else ""
    unread_clause = "" if include_read else "is:unread "
    after_clause = ""
    if since_datetime:
        after_clause = f" after:{int(since_datetime.timestamp())}"

    recipient_clause = f" to:{recipient_email}" if recipient_email else ""

    query = f"{unread_clause}({sender_clause}){recipient_clause}{after_clause}" if sender_clause else f"{unread_clause.strip()}{recipient_clause}{after_clause}"
    logger.info(f"Querying Gmail (sender): {query}")
    
    try:
        results = await asyncio.to_thread(lambda: service.users().messages().list(userId='me', q=query, maxResults=50).execute())
        messages = results.get('messages', [])

        if subject_phrase:
            subject_query = f'{unread_clause.strip()} subject:"{subject_phrase}" -from:{EMAIL_SENDER}{after_clause}'.strip()
            logger.info(f"Querying Gmail (subject fallback): {subject_query}")
            subject_results = await asyncio.to_thread(
                lambda: service.users().messages().list(userId='me', q=subject_query, maxResults=50).execute()
            )
            subject_messages = subject_results.get('messages', [])
            if subject_messages:
                seen_ids = {m.get('id') for m in messages if m.get('id')}
                for m in subject_messages:
                    mid = m.get('id')
                    if mid and mid not in seen_ids:
                        messages.append(m)
                        seen_ids.add(mid)
        
        extracted_emails = []
        
        for message in messages:
            try:
                msg = await asyncio.to_thread(lambda mid=message['id']: service.users().messages().get(userId='me', id=mid, format='full').execute())
                headers = msg['payload']['headers']
                
                email_data = {
                    'id': msg['id'],
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                    'body': _get_message_body(msg)
                }
                extracted_emails.append(email_data)
                logger.info(f"Extracted email from {email_data['from']}: {email_data['subject']}")
                
            except Exception as e:
                logger.error(f"Error extracting email {message['id']}: {e}")
                continue
        
        return extracted_emails
        
    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return []
    except Exception as e:
        logger.exception(f"Unexpected error fetching unread replies: {e}")
        return []


def _get_message_body(message: dict) -> str:
    """Extracts the plain text or HTML body from a Gmail message."""
    try:
        if 'parts' in message['payload']:
            # Multipart message
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in message['payload']:
            # Simple message
            if 'data' in message['payload']['body']:
                return base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        return ""
    except Exception as e:
        logger.error(f"Error extracting message body: {e}")
        return ""


async def send_reminder_email(
    supplier_email: str,
    supplier_name: str,
    chemical_query: str,
    job_id: Optional[int] = None,
) -> bool:
    """Sends a reminder email to a supplier who hasn't responded."""
    job_tag = f"[JOB-{job_id}] " if job_id is not None else ""
    subject = f"{job_tag}Reminder: Request for Quote - {chemical_query}"
    
    body = f"""
    <p>Dear {supplier_name},</p>
    
    <p>I hope this email finds you well.</p>
    
    <p>I wanted to follow up on my previous request for a quote regarding:</p>
    <p><strong>{chemical_query}</strong></p>
    
    <p>I would greatly appreciate if you could provide us with a quote at your earliest convenience. 
    If you have any questions or need clarification, please don't hesitate to reach out.</p>
    
    <p>Thank you for your attention to this matter.</p>
    
    <p>Best regards,<br>
    Amit<br>
    Procurement Team</p>
    """
    
    return await send_email_with_attachments(subject, body, supplier_email)


async def mark_message_as_read(message_id: str) -> bool:
    """Marks a Gmail message as read."""
    if not GOOGLE_API_CLIENT_AVAILABLE:
        logger.error("Google API client libraries not installed.")
        return False
    
    try:
        service = get_gmail_read_service()
        await asyncio.to_thread(lambda: service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute())
        logger.info(f"Marked message {message_id} as read")
        return True
    except Exception as e:
        logger.error(f"Error marking message as read: {e}")
        return False
