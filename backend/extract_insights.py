import os
import json
import logging
from typing import List, Dict, Optional
from .email_utils import fetch_unread_replies
from pydantic import BaseModel

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Generative AI
if GENAI_AVAILABLE:
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)


class InsightData(BaseModel):
    """Data model for extracted insights."""
    supplier: str
    contact_person: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    delivery_date: Optional[str] = None


def extract_insights_from_email(email_subject: str, email_body: str) -> Optional[InsightData]:
    """
    Uses Google Generative AI to extract structured insights from an email.
    Returns an InsightData object or None if extraction fails.
    """
    if not GENAI_AVAILABLE:
        logger.error("google-generativeai is not installed")
        return None
    
    if not os.environ.get("GOOGLE_GENAI_API_KEY"):
        logger.warning("GOOGLE_GENAI_API_KEY not set - cannot extract insights")
        return None
    
    try:
        model = genai.GenerativeModel("gemini-pro")
        
        prompt = f"""
        Extract the following information from this supplier email and return as JSON:
        - supplier: Company name
        - contact_person: Name of the person replying
        - product: Product name or description
        - quantity: Quantity offered
        - price: Price quoted
        - delivery_date: Delivery or shipping date
        
        Email Subject: {email_subject}
        Email Body: {email_body}
        
        Return ONLY valid JSON, no other text. If a field is not found, set it to null.
        """
        
        response = model.generate_content(prompt)
        
        if response.text:
            try:
                # Parse the JSON response
                json_str = response.text.strip()
                # Handle case where response might have markdown code blocks
                if json_str.startswith("```"):
                    json_str = json_str.split("```")[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
                
                data = json.loads(json_str)
                insight = InsightData(**data)
                logger.info(f"Successfully extracted insights from email")
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


def process_supplier_responses(supplier_domains: List[str], job_id: int) -> List[InsightData]:
    """
    Fetches unread emails from suppliers and extracts insights using AI.
    Returns a list of InsightData objects.
    """
    logger.info(f"Processing supplier responses for job {job_id}")
    
    # Fetch unread emails from supplier domains
    emails = fetch_unread_replies(supplier_domains)
    logger.info(f"Fetched {len(emails)} unread emails")
    
    insights = []
    
    for email in emails:
        try:
            insight = extract_insights_from_email(email['subject'], email['body'])
            if insight:
                # Extract supplier from email if not already in data
                if not insight.supplier:
                    from_addr = email.get('from', '')
                    insight.supplier = from_addr.split('<')[0].strip() if '<' in from_addr else from_addr
                
                insights.append(insight)
                logger.info(f"Extracted insight from {insight.supplier}")
        except Exception as e:
            logger.error(f"Error processing email from {email.get('from')}: {e}")
            continue
    
    return insights


