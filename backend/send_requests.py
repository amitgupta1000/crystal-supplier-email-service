import csv
import logging
from typing import List, Dict
from .email_utils import send_email_with_attachments

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Template 1: Salutation
TEMPLATE_SALUTATION = "{salutation},"

# Template 2: Message Body
TEMPLATE_MESSAGE = """
<p>I would like your offer for {quantity} tonnes of {product} {incoterm} {location}, delivery on {delivery_date}.</p>

<p>Trust you are well.</p>

<p>Look forward to hearing from you,</p>
<p>Amit</p>
"""

def send_rfq_emails(
    product: str,
    quantity: str,
    incoterm: str,
    delivery_date: str,
    csv_file: str = "suppliers.csv"
) -> Dict[str, int]:
    """
    Send RFQ emails to multiple suppliers from a CSV file.
    
    Args:
        product: Product name
        quantity: Quantity in tonnes
        incoterm: Incoterm (CFR, CIF, FOB, etc.)
        delivery_date: Delivery date
        csv_file: Path to suppliers CSV file
        
    Returns:
        Dictionary with success/failure counts
    """
    results = {
        "sent": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    company = row.get('Company Name', '')
                    email = row.get('Email ID', '')
                    location = row.get('Location', '')
                    salutation = row.get('Salutation 1', 'Hello')
                    
                    if not email:
                        logger.warning(f"Skipping {company} - no email address")
                        continue
                    
                    # Render templates
                    salut_text = TEMPLATE_SALUTATION.format(salutation=salutation)
                    msg_text = TEMPLATE_MESSAGE.format(
                        quantity=quantity,
                        product=product,
                        incoterm=incoterm,
                        location=location,
                        delivery_date=delivery_date
                    )
                    
                    body = f"<p>{salut_text}</p>{msg_text}"
                    subject = f"Request for Quote: {quantity} MT {product} - {company}"
                    
                    logger.info(f"Preparing to send email to {email} ({company})")
                    
                    success = send_email_with_attachments(subject, body, email)
                    
                    if success:
                        results["sent"] += 1
                        logger.info(f"Successfully sent RFQ email to {email}")
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Failed to send to {email}")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Error processing {row.get('Company Name', 'Unknown')}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                    
    except FileNotFoundError:
        logger.error(f"Supplier CSV file not found: {csv_file}")
        results["errors"].append(f"CSV file not found: {csv_file}")
    except Exception as e:
        logger.error(f"Error reading supplier CSV: {e}")
        results["errors"].append(f"Error reading CSV: {str(e)}")
    
    return results


def main():
    """Example usage of send_rfq_emails function."""
    product = "Methanol"
    quantity = "20,000"
    incoterm = "CFR"
    delivery_date = "31st July 2026"
    
    logger.info(f"Sending RFQ emails for {quantity} MT {product}")
    results = send_rfq_emails(product, quantity, incoterm, delivery_date)
    
    logger.info(f"Results: {results['sent']} sent, {results['failed']} failed")
    if results["errors"]:
        for error in results["errors"]:
            logger.error(f"  - {error}")


if __name__ == "__main__":
    main()
                
                # In a real run, this would send emails.
                # For safety and testing without credentials, we just log it.
                # success = send_email_with_attachments(subject, body, email)
                # if success:
                #    logger.info(f"Successfully sent to {email}")
                logger.info(f"Dry Run: Email generated for {email}:\nSubject: {subject}\nBody:\n{body}\n{'-'*40}")

    except FileNotFoundError:
        logger.error(f"Could not find {csv_file}")
    except Exception as e:
        logger.error(f"Error processing suppliers: {e}")

if __name__ == "__main__":
    main()
