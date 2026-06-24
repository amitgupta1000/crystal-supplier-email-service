import os
import json
import logging
import asyncio
import random
from typing import List, Dict, Optional
from .email_utils import fetch_unread_replies
from pydantic import BaseModel

try:
    import google.genai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENAI_MAX_RETRIES = int(os.environ.get("GENAI_MAX_RETRIES", "3"))
GENAI_RETRY_BASE_DELAY_SECONDS = float(os.environ.get("GENAI_RETRY_BASE_DELAY_SECONDS", "1.0"))


def _is_retryable_genai_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retry_markers = [
        "503",
        "unavailable",
        "429",
        "rate",
        "quota",
        "deadline",
        "timeout",
        "internal",
    ]
    return any(marker in msg for marker in retry_markers)

# Initialize Generative AI
genai_client = None
if GENAI_AVAILABLE:
    # Try GOOGLE_API_KEY first, then fall back to GOOGLE_GENAI_API_KEY
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_API_KEY")
    if api_key:
        genai_client = genai.Client(api_key=api_key)
    else:
        logger.warning("GOOGLE_API_KEY or GOOGLE_GENAI_API_KEY not set. Insight extraction will be disabled.")
else:
    logger.warning("google.genai library not found. Insight extraction will be disabled.")


class InsightData(BaseModel):
    """Data model for extracted insights."""
    supplier: str
    contact_person: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    delivery_date: Optional[str] = None
    key_terms: Optional[str] = None
    email_body: Optional[str] = None  # Complete email for drilldowns
    from_email: Optional[str] = None
    message_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_date: Optional[str] = None


async def extract_insights_from_email(
    email_subject: str,
    email_body: str,
    from_email: Optional[str] = None,
    message_id: Optional[str] = None,
    email_date: Optional[str] = None,
) -> Optional[InsightData]:
    """Extract structured insights from supplier email using Generative AI."""
    if not GENAI_AVAILABLE or not genai_client:
        logger.error("google.genai not available or not configured")
        return None
    
    prompt = f"""Extract supplier quote data from this email. Return valid JSON only:
- supplier: Company name (required, infer if needed; use "Internal Test" for self-replies)
- contact_person: Contact name if identifiable
- product: Product description
- quantity: Quantity with units (MT, tons, etc.)
- price: Price with currency and unit
- key_terms: Any other relevant terms (payment, delivery, etc.)
- delivery_date: Delivery timeframe or date

Rules: Always include supplier name. Use null for empty fields. Return ONLY JSON.

Subject: {email_subject}
Body: {email_body}"""

    response = None
    for attempt in range(1, GENAI_MAX_RETRIES + 1):
        try:
            response = await asyncio.to_thread(
                lambda: genai_client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt
                )
            )
            break
        except Exception as e:
            is_retryable = _is_retryable_genai_error(e)
            is_last_attempt = attempt == GENAI_MAX_RETRIES
            if (not is_retryable) or is_last_attempt:
                logger.error(f"Error extracting insights with Generative AI: {e}")
                return None

            # Exponential backoff with small jitter for transient provider pressure.
            delay = (GENAI_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
            logger.warning(
                "Transient Gemini error on attempt %s/%s; retrying in %.2fs: %s",
                attempt,
                GENAI_MAX_RETRIES,
                delay,
                e,
            )
            await asyncio.sleep(delay)
        
    try:
        if response and response.text:
            try:
                json_str = response.text.strip()
                # Handle markdown code blocks
                if json_str.startswith("```"):
                    json_str = json_str.split("```")[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
                
                data = json.loads(json_str)
                # Add the complete email body for drilldowns
                data['email_body'] = email_body
                data['from_email'] = from_email
                data['message_id'] = message_id
                data['email_subject'] = email_subject
                data['email_date'] = email_date
                insight = InsightData(**data)
                logger.info(f"Successfully extracted insights from email")
                logger.debug(f"Extracted data: supplier={insight.supplier}, contact={insight.contact_person}, product={insight.product}, price={insight.price}")
                return insight
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.debug(f"Response text: {response.text}")
                return None
        else:
            logger.warning("No response from Generative AI")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting insights with Generative AI: {e}")
        return None


async def process_supplier_responses(
    supplier_domains: List[str],
    supplier_emails: List[str],
    job_id: int,
    include_read: bool = True,
    since_datetime=None,
    recipient_email: Optional[str] = None,
    subject_phrase: Optional[str] = None,
) -> List[InsightData]:
    """
    Fetches unread emails from suppliers and extracts insights using AI.
    Returns a list of InsightData objects.
    """
    logger.info(f"Processing supplier responses for job {job_id}")
    
    # Fetch unread emails from supplier domains
    emails = await fetch_unread_replies(
        supplier_domains,
        supplier_emails=supplier_emails,
        include_read=include_read,
        since_datetime=since_datetime,
        recipient_email=recipient_email,
        subject_phrase=subject_phrase,
    )
    logger.info(f"Fetched {len(emails)} unread emails")
    
    insights = []
    
    for email in emails:
        try:
            insight = await extract_insights_from_email(
                email['subject'],
                email['body'],
                from_email=email.get('from'),
                message_id=email.get('id'),
                email_date=email.get('date'),
            )
            if insight:
                # Extract supplier from email if not already in data
                if not insight.supplier:
                    from_addr = email.get('from', '')
                    insight.supplier = from_addr.split('<')[0].strip() if '<' in from_addr else from_addr
                
                insights.append(insight)
                logger.info(f"Extracted insight from {insight.supplier}")
            else:
                # Keep inbound reply metadata even when AI extraction fails,
                # so the caller can still mark supplier reply state and store email.
                from_addr = email.get('from', '') or 'Unknown Supplier'
                supplier_name = from_addr.split('<')[0].strip() if '<' in from_addr else from_addr
                insights.append(InsightData(
                    supplier=supplier_name or 'Unknown Supplier',
                    email_body=email.get('body'),
                    from_email=email.get('from'),
                    message_id=email.get('id'),
                    email_subject=email.get('subject'),
                    email_date=email.get('date'),
                ))
                logger.warning("AI extraction failed for %s; preserving raw email for reply tracking", from_addr)
        except Exception as e:
            logger.error(f"Error processing email from {email.get('from')}: {e}")
            continue
    
    return insights


