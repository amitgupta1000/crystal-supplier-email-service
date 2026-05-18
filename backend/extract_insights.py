import os
import csv
import json
import logging
import pydantic
from email_utils import fetch_unread_replies
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_dashboard(csv_path: str, html_path: str):
    """Generates a modern HTML dashboard from the insights CSV."""
    if not os.path.exists(csv_path):
        logger.warning("No insights CSV found to generate dashboard.")
        return

    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crystal Supplier Insights</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.5);
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --row-hover: rgba(255, 255, 255, 0.05);
        }
        body {
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at top left, #1e293b, #020617);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            animation: fadeInDown 0.8s ease-out;
        }
        .header h1 {
            font-size: 3rem;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px var(--accent-glow);
        }
        .header p {
            color: var(--text-muted);
            font-size: 1.1rem;
            margin-top: 10px;
        }
        .glass-container {
            width: 100%;
            max-width: 1200px;
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 30px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: fadeInUp 0.8s ease-out;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
        }
        th, td {
            padding: 20px;
            text-align: left;
        }
        th {
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid var(--glass-border);
        }
        tr tbody {
            transition: all 0.3s ease;
        }
        tbody tr {
            background: rgba(255, 255, 255, 0.02);
            border-radius: 12px;
            transition: all 0.3s ease;
        }
        tbody tr:hover {
            background: var(--row-hover);
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }
        td {
            font-size: 1.05rem;
        }
        td:first-child {
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
            font-weight: 600;
            color: #fff;
        }
        td:last-child {
            border-top-right-radius: 12px;
            border-bottom-right-radius: 12px;
        }
        .price {
            color: #10b981;
            font-weight: 800;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Crystal Market Insights</h1>
        <p>Real-time AI-extracted supplier offers and negotiations</p>
    </div>
    <div class="glass-container">
        <table>
            <thead>
                <tr>
                    <th>Supplier</th>
                    <th>Contact Person</th>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Price</th>
                    <th>Delivery Date</th>
                </tr>
            </thead>
            <tbody>
'''
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            html_content += f'''
                <tr>
                    <td>{row.get("Supplier", "")}</td>
                    <td><span class="badge">{row.get("Contact Person", "")}</span></td>
                    <td>{row.get("Product", "")}</td>
                    <td>{row.get("Quantity", "")}</td>
                    <td class="price">{row.get("Price", "")}</td>
                    <td>{row.get("Delivery Date", "")}</td>
                </tr>'''

    html_content += '''
            </tbody>
        </table>
    </div>
</body>
</html>'''

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"Dashboard generated at {html_path}")


class OfferInsight(pydantic.BaseModel):
    Supplier: str
    Contact_Person: str = pydantic.Field(description="The name of the person sending the offer")
    Product: str
    Quantity: str
    Price: str = pydantic.Field(description="The price offered (including currency)")
    Delivery_Date: str

def extract_insight_from_text(text: str) -> dict:
    """Uses Gemini to extract structured data from email text using a Pydantic model."""
    if not GENAI_AVAILABLE:
        logger.error("google-generativeai is not installed.")
        return {}

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set. Cannot proceed with extraction.")
        return {}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Extract the following information from the email text below:
    - Supplier
    - Contact Person
    - Product
    - Quantity
    - Price
    - Delivery Date

    Email text:
    "{text}"
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=OfferInsight,
            ),
        )
        data = json.loads(response.text)
        
        # Map the Pydantic fields to the CSV expected fields
        return {
            "Supplier": data.get("Supplier", ""),
            "Contact Person": data.get("Contact_Person", ""),
            "Product": data.get("Product", ""),
            "Quantity": data.get("Quantity", ""),
            "Price": data.get("Price", ""),
            "Delivery Date": data.get("Delivery_Date", "")
        }
    except Exception as e:
        logger.error(f"Failed to extract info via Gemini: {e}")
        return {}

def main():
    # 1. Fetch unread replies from supplier domains
    supplier_domains = ["petronaschem.com", "basfchem.com", "dowchem.com", "sabic.com", "exxonchem.com"]
    
    logger.info("Fetching unread replies from supplier domains...")
    emails = fetch_unread_replies(supplier_domains)
    
    if not emails:
        logger.info("No unread replies found.")
        return

    insights = []
    for email in emails:
        logger.info(f"Processing email from {email['from']}")
        insight = extract_insight_from_text(email['body'])
        if insight:
            insights.append(insight)
            
    if insights:
        csv_file = "insights.csv"
        file_exists = os.path.isfile(csv_file)
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Supplier", "Contact Person", "Product", "Quantity", "Price", "Delivery Date"])
            if not file_exists:
                writer.writeheader()
            for row in insights:
                writer.writerow(row)
                
        logger.info(f"Appended {len(insights)} new insights to {csv_file}")
        
        # Generate dashboard
        generate_dashboard(csv_file, "insights_dashboard.html")
    else:
        logger.info("No new insights found.")

if __name__ == "__main__":
    main()
