"""
email_utils.py

Utility for sending and reading email notifications.
Uses Gmail API.
"""
import os
import base64
import logging
from typing import List, Optional

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import google.auth
    GOOGLE_API_CLIENT_AVAILABLE = True
except ImportError:
    GOOGLE_API_CLIENT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GMAIL_IMPERSONATE_USER = os.environ.get("GMAIL_IMPERSONATE_USER", "user@example.com")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", GMAIL_IMPERSONATE_USER)
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "").split(",")

def is_email_configured() -> bool:
    missing = []
    if not GOOGLE_API_CLIENT_AVAILABLE:
        missing.append("GOOGLE_API_CLIENT_AVAILABLE (Google API libraries not installed)")
        
    if missing:
        logger.warning(f"Email configuration is incomplete. Missing variables: {', '.join(missing)}")
        return False
    return True

def get_gmail_service(scopes: List[str]):
    """Initializes and returns the Gmail API service using Domain-Wide Delegation."""
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if creds_path and os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=scopes
        )
        delegated_creds = creds.with_subject(GMAIL_IMPERSONATE_USER)
        return build('gmail', 'v1', credentials=delegated_creds, cache_discovery=False)
    
    creds, _ = google.auth.default(scopes=scopes)
    if hasattr(creds, 'with_subject'):
        delegated_creds = creds.with_subject(GMAIL_IMPERSONATE_USER)
        return build('gmail', 'v1', credentials=delegated_creds, cache_discovery=False)
    else:
        # Fallback for standard OAuth2 credentials (e.g. for testing locally without DWD)
        return build('gmail', 'v1', credentials=creds, cache_discovery=False)

def get_gmail_send_service():
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.send'])

def get_gmail_read_service():
    return get_gmail_service(['https://www.googleapis.com/auth/gmail.readonly'])

def send_email_with_attachments(
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
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        logger.info(f"Email sent successfully! Message ID: {sent_message['id']}")
        return True

    except HttpError as error:
        logger.error(f"An error occurred sending email via Gmail API: {error}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error while sending email: {e}")
        return False

def fetch_unread_replies(domains: List[str]) -> List[dict]:
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

    query = "is:unread (" + " OR ".join([f"from:{domain}" for domain in domains]) + ")"
    logger.info(f"Querying Gmail: {query}")
    
    try:
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        extracted_emails = []
        for msg in messages:
            msg_id = msg['id']
            msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            headers = msg_data['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), "Unknown")
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "No Subject")
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), "Unknown Date")
            
            # Extract body
            body = ""
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                        body_data = part['body']['data']
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
            elif 'data' in msg_data['payload']['body']:
                body_data = msg_data['payload']['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                
            extracted_emails.append({
                'id': msg_id,
                'from': sender,
                'subject': subject,
                'date': date,
                'body': body
            })
            
        return extracted_emails

    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []