import csv
import logging
from email_utils import send_email_with_attachments

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

def main():
    product = "Methanol"
    quantity = "20,000"
    incoterm = "CFR"
    delivery_date = "31st July 2026"
    
    csv_file = "suppliers.csv"
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = row['Company Name']
                email = row['Email ID']
                location = row['Location']
                salutation = row.get('Salutation 1', 'Hello')
                
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
