import os
import json
import logging
import asyncio
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
    email_body: Optional[str] = None  # Complete email for drilldowns


async def extract_insights_from_email(email_subject: str, email_body: str) -> Optional[InsightData]:
    """
    Uses Google Generative AI to extract structured insights from an email.
    Returns an InsightData object or None if extraction fails.
    """
    if not GENAI_AVAILABLE or not genai_client:
        logger.error("google.genai is not available or not configured")
        return None
    
    try:
        
        prompt = f"""
        Extract the following information from this supplier email and return as JSON:
        - supplier: Company name
        - contact_person: Name of the person replying
        - product: Product name or description
        - quantity: Quantity offered (include units like MT, tons, barrels, etc.)
        - price: Price quoted (include currency and unit like $/MT, USD/ton, etc.)
        - delivery_date: Delivery or shipping date (can be specific date or timeframe like "2 weeks", "Q3 2026", etc.)
        
        EXAMPLES OF TYPICAL SUPPLIER RESPONSES:
        
        Example 1 (Formal Quote):
        "Dear Sir, Thank you for your inquiry. We can supply 20,000 MT of Methanol Grade A at $450/MT CFR Singapore. 
        Our quality manager John Smith will handle this order. Delivery available for June 28, 2026. Best regards, 
        BASF Chemical Trading"
        Expected JSON: {{"supplier": "BASF Chemical Trading", "contact_person": "John Smith", "product": "Methanol Grade A", 
        "quantity": "20,000 MT", "price": "$450/MT CFR Singapore", "delivery_date": "June 28, 2026"}}
        
        Example 2 (Informal Response):
        "Hi, we have stock of Methanol available. Price is 425 USD per ton, FOB Rotterdam. Raj Patel from our sales team 
        will send the full quote. We can deliver within 3 weeks. Thanks, Petronas Chemical"
        Expected JSON: {{"supplier": "Petronas Chemical", "contact_person": "Raj Patel", "product": "Methanol", 
        "quantity": null, "price": "425 USD per ton FOB Rotterdam", "delivery_date": "3 weeks"}}
        
        Example 3 (Partial Response):
        "Hi there! We're interested in discussing this opportunity. Our procurement manager Sarah Johnson would like 
        to connect with your team. Let's set up a call next week to discuss pricing and availability."
        Expected JSON: {{"supplier": "Unknown", "contact_person": "Sarah Johnson", "product": null, 
        "quantity": null, "price": null, "delivery_date": "next week"}}
        
        Email Subject: {email_subject}
        Email Body: {email_body}
        
        Return ONLY valid JSON, no other text. If a field is not mentioned or cannot be clearly extracted, set it to null.
        """
        
        response = await asyncio.to_thread(
            lambda: genai_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )
        )
        
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
                # Add the complete email body for drilldowns
                data['email_body'] = email_body
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


async def process_supplier_responses(supplier_domains: List[str], job_id: int) -> List[InsightData]:
    """
    Fetches unread emails from suppliers and extracts insights using AI.
    Returns a list of InsightData objects.
    """
    logger.info(f"Processing supplier responses for job {job_id}")
    
    # Fetch unread emails from supplier domains
    emails = await fetch_unread_replies(supplier_domains)
    logger.info(f"Fetched {len(emails)} unread emails")
    
    insights = []
    
    for email in emails:
        try:
            insight = await extract_insights_from_email(email['subject'], email['body'])
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


