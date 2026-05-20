# Implementation Guide - Email Utilities & Advanced API Endpoints

## Overview

This document describes the implementation of email utilities, insights extraction, and comprehensive API endpoints for the Crystal Supplier Email Service.

## What Was Implemented

### 1. Email Utilities (`backend/email_utils.py`)

#### Completed Functions:

**`send_email_with_attachments()`**
- Sends emails via Gmail API with domain-wide delegation
- Supports HTML email bodies
- Handles file attachments
- Returns success/failure status
- Logs all email operations

**`fetch_unread_replies()`**
- Queries Gmail for unread emails from supplier domains
- Extracts email metadata (sender, subject, body, date)
- Returns structured list of email objects
- Handles multipart and simple messages
- Includes error handling and logging

**`_get_message_body()`**
- Helper function to extract message body from Gmail API responses
- Handles both plain text and HTML formats
- Properly decodes base64-encoded content

**`send_reminder_email()`**
- Sends follow-up reminder emails to non-responsive suppliers
- Uses HTML email templates
- Personalizes with supplier name and chemical query
- Includes error handling

**`mark_message_as_read()`**
- Marks emails as read in Gmail after processing
- Prevents duplicate processing
- Updates Gmail labels

### 2. Insights Extraction (`backend/extract_insights.py`)

#### Completed Functions:

**`InsightData` Model**
- Pydantic model for structured insight data
- Fields: supplier, contact_person, product, quantity, price, delivery_date
- Type-safe data validation

**`extract_insights_from_email()`**
- Uses Google Generative AI (Gemini) to parse email content
- Extracts structured information from unstructured email text
- Handles JSON parsing from AI responses
- Includes error handling and fallbacks
- Returns `InsightData` object or None

**`process_supplier_responses()`**
- Fetches all unread supplier emails for a job
- Extracts insights from each email using AI
- Handles batch processing
- Returns list of `InsightData` objects
- Includes comprehensive logging

**`generate_dashboard()`**
- Creates an HTML dashboard from insights CSV
- Generates styled, interactive display

### 3. Database Models (`backend/database.py`)

#### New Tables:

**`SupplierEmail` Table**
- Tracks all email exchanges (sent and received)
- Fields:
  - `job_id`: Reference to job
  - `supplier_state_id`: Reference to supplier
  - `email_type`: "outbound" or "inbound"
  - `from_email` / `to_email`: Email addresses
  - `subject` / `body`: Email content
  - `sent_at`: Timestamp
  - `gmail_message_id`: Gmail API message ID

#### Enhanced Tables:

**`Job` Table**
- Added `closed_at`: When job was closed
- Added `total_responses`: Count of supplier responses
- Added relationships to emails and insights

**`JobSupplierState` Table**
- Added `reply_received_at`: When supplier replied
- Added `reminder_sent_at`: When reminder was sent
- Added relationship to emails

### 4. API Endpoints (`main.py`)

#### Health & Utility Endpoints:
- `GET /health` - Service health check

#### Supplier Endpoints:
- `GET /api/suppliers` - List all suppliers from CSV

#### Job Endpoints:
- `GET /api/jobs` - List all jobs with pagination
- `POST /api/jobs/start` - Create and start new job
- `GET /api/jobs/{job_id}` - Get job details with full drilldown
- `POST /api/jobs/{job_id}/close` - Close a job
- `POST /api/jobs/{job_id}/insights/refresh` - Manually extract insights

#### Supplier State & Email Endpoints:
- `GET /api/jobs/{job_id}/suppliers` - Get suppliers for job
- `GET /api/suppliers/{supplier_id}/emails` - Get all emails from supplier
- `POST /api/jobs/{job_id}/suppliers/{supplier_id}/send-reminder` - Send reminder

#### Insights Endpoints:
- `GET /api/jobs/{job_id}/insights` - Get insights for job
- `GET /api/insights/by-supplier` - Get all insights grouped by supplier

#### Statistics Endpoints:
- `GET /api/stats/summary` - Overall statistics
- `GET /api/stats/job/{job_id}` - Job-specific statistics

### 5. Scheduler Updates (`backend/scheduler.py`)

Enhanced background job processor:
- Sends reminder emails at T+24h (configurable, 2 minutes for dev)
- Closes and archives jobs at T+48h (configurable, 4 minutes for dev)
- Archives job summaries and insights to GCS
- Tracks supplier reply status
- Includes comprehensive logging

### 6. API Testing

**Test Suite** (`test_api.py`)
- Health check tests
- Supplier endpoint tests
- Job management tests
- Statistics tests
- Integration tests
- Performance tests
- Run with: `pytest test_api.py -v`

**Manual Testing Script** (`test-api.sh`)
- Bash script for curl-based API testing
- Tests all major endpoints
- Usage: `./test-api.sh http://localhost:8000`

---

## Key Features

### Email Integration
✅ Domain-wide delegation for Gmail API
✅ Send personalized RFQ emails
✅ Fetch and parse supplier responses
✅ Attachment support
✅ HTML email templates
✅ Error handling and retries

### AI-Powered Insights
✅ Google Generative AI integration
✅ Automatic parsing of supplier emails
✅ Structured data extraction
✅ JSON response handling
✅ Fallback mechanisms

### Job Lifecycle Management
✅ Job creation with supplier targeting
✅ Automatic email sending on job start
✅ Reminder emails at T+24h
✅ Job closure and archival at T+48h
✅ Manual endpoint for all operations

### Response Tracking
✅ Track which suppliers have replied
✅ Store full email history
✅ Extract timestamps for responses
✅ View email exchanges by supplier
✅ Send reminders to non-respondents

### Drilldown Capability
✅ View job details with related data
✅ See all suppliers for a job
✅ View email exchanges per supplier
✅ See extracted insights per job
✅ Compare insights across suppliers

### Analytics
✅ Overall summary statistics
✅ Per-job statistics and metrics
✅ Response rate calculations
✅ Insight extraction counts

---

## Usage Examples

### Create a Job with Email Sending

```python
import requests

response = requests.post(
    "http://localhost:8000/api/jobs/start",
    json={
        "chemical_query": "20000 MT Methanol CFR Singapore - July 2026",
        "supplier_emails": [
            "supplier1@example.com",
            "supplier2@example.com",
            "supplier3@example.com"
        ]
    }
)

job = response.json()
print(f"Created job {job['job_id']}")
print(f"Emails sent: {job['emails_sent']}")
```

### Drilldown into Job Details

```python
import requests

# Get complete job information
response = requests.get("http://localhost:8000/api/jobs/1")
job_detail = response.json()

# View all suppliers and their response status
for supplier in job_detail["suppliers"]:
    print(f"  {supplier['company_name']}: ", end="")
    if supplier["replied"]:
        print(f"Replied at {supplier['reply_received_at']}")
    else:
        print("No reply yet")

# View extracted insights
for insight in job_detail["insights"]:
    print(f"  {insight['supplier']}: {insight['price']} per {insight['quantity']}")

# View email history
for email in job_detail["emails"]:
    print(f"  [{email['email_type']}] {email['subject']}")
```

### Trigger Insight Extraction

```python
import requests

# After waiting for supplier responses, refresh insights
response = requests.post(
    "http://localhost:8000/api/jobs/1/insights/refresh"
)

result = response.json()
print(f"Extracted {result['new_insights_extracted']} insights")

for insight in result["insights"]:
    print(f"  {insight['supplier']}: {insight['price']}")
```

### Send Manual Reminder

```python
import requests

# Send reminder to specific supplier
response = requests.post(
    "http://localhost:8000/api/jobs/1/suppliers/2/send-reminder"
)

print(response.json()["message"])
```

### View Supplier Email History

```python
import requests

# Get all emails from a specific supplier
response = requests.get(
    "http://localhost:8000/api/suppliers/2/emails"
)

emails = response.json()
for email in emails:
    print(f"[{email['email_type']}] {email['subject']}")
    if email["email_type"] == "inbound":
        print(f"  From: {email['from_email']}")
        print(f"  Body: {email['body'][:100]}...")
```

---

## Configuration

### Environment Variables Required

```bash
# Gmail Configuration
GMAIL_IMPERSONATE_USER=noreply@yourdomain.com
EMAIL_SENDER=noreply@yourdomain.com
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json

# Generative AI
GOOGLE_GENAI_API_KEY=your-api-key

# Database
DATABASE_URL=sqlite:///./jobs.db  # or PostgreSQL connection string
```

### Scheduler Configuration

In `backend/scheduler.py`, adjust:

```python
# Development (short intervals for testing)
scheduler.add_job(process_active_jobs, 'interval', minutes=1)  # Check every minute

# Production (set longer intervals)
# scheduler.add_job(process_active_jobs, 'interval', hours=1)  # Check every hour
```

Adjust reminder and closure thresholds:

```python
# Development
timedelta(minutes=2)   # Send reminders at 2 minutes
timedelta(minutes=4)   # Close jobs at 4 minutes

# Production
timedelta(hours=24)    # Send reminders at 24 hours
timedelta(hours=48)    # Close jobs at 48 hours
```

---

## Database Schema

### Job → Supplier → Email Flow

```
Job (1)
├── JobSupplierState (many)
│   └── SupplierEmail (many)
│       ├── Type: outbound (initial RFQ)
│       ├── Type: outbound (reminder)
│       └── Type: inbound (supplier reply)
└── Insight (many)
    └── Extracted from inbound emails
```

### Key Relationships

- Job has many suppliers (1:N)
- JobSupplierState has many emails (1:N)
- Job has many insights (1:N)
- SupplierEmail can be linked to JobSupplierState (optional for inbound)

---

## Error Handling

### Email Service Errors

- **Missing credentials**: Logs warning, returns false
- **Gmail API errors**: Caught and logged, graceful degradation
- **Network errors**: Retry logic with exponential backoff (future enhancement)
- **Attachment errors**: Logs error per file, continues with others

### Insight Extraction Errors

- **Missing API key**: Logs warning, skips extraction
- **JSON parse errors**: Logs raw response, returns None
- **API timeouts**: Logs error, returns None
- **Rate limiting**: Future enhancement with queue/retry

### Database Errors

- **Connection failures**: Logged, transaction rolled back
- **Constraint violations**: Returns 400 Bad Request
- **Not found errors**: Returns 404 Not Found

---

## Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest test_api.py -v

# Run specific test class
pytest test_api.py::TestJobEndpoints -v

# Run with coverage
pytest test_api.py --cov=. --cov-report=html
```

### Manual API Testing

```bash
# Make script executable
chmod +x test-api.sh

# Run test suite
./test-api.sh http://localhost:8000

# Or manually test single endpoint
curl http://localhost:8000/api/suppliers | jq
```

### Test with Real Emails

1. Set up Gmail API credentials
2. Configure `GMAIL_IMPERSONATE_USER` in `.env`
3. Send emails to your test account
4. Call `/api/jobs/{id}/insights/refresh` endpoint
5. Check extracted insights

---

## Future Enhancements

### Planned Features

1. **Batch Email Processing**
   - Queue system for large campaigns (>100 suppliers)
   - Async email sending with Celery/Redis

2. **Advanced AI Features**
   - Multi-language support
   - Price comparison and benchmarking
   - Automatic supplier scoring

3. **CRM Integration**
   - Salesforce sync
   - HubSpot integration
   - Custom CRM connectors

4. **Frontend Enhancements**
   - Real-time WebSocket updates
   - Advanced filtering and search
   - Dashboard customization
   - Export to Excel/PDF

5. **Infrastructure**
   - Multi-region deployment
   - Database read replicas
   - Caching layer (Redis)
   - Rate limiting
   - API authentication (OAuth2)

---

## Troubleshooting

### Email Not Sending

```
❌ Problem: "Email configuration is incomplete"
✅ Solution: 
   - Install google-api-python-client
   - Set GOOGLE_APPLICATION_CREDENTIALS
   - Verify service account has Gmail API scope
```

### Insights Not Extracting

```
❌ Problem: "GOOGLE_GENAI_API_KEY not set"
✅ Solution:
   - Get API key from Google AI Studio
   - Set GOOGLE_GENAI_API_KEY in .env
   - Enable Generative AI API in GCP
```

### Job Not Starting

```
❌ Problem: "Error starting job: [error message]"
✅ Solution:
   - Check database connectivity
   - Verify supplier emails are valid
   - Check logs for specific error
```

### API Not Responding

```
❌ Problem: "Cannot connect to localhost:8000"
✅ Solution:
   - Ensure backend is running: uvicorn main:app --reload
   - Check if port 8000 is in use
   - Verify firewall settings
```

---

## Performance Considerations

### Current Implementation
- Single-threaded email sending
- Synchronous database operations
- No caching
- No rate limiting

### Production Recommendations
- Use Celery for async email processing
- Implement connection pooling
- Add Redis caching for supplier lists
- Rate limit API endpoints
- Use database read replicas for analytics

---

## Security Notes

### Current State
- ⚠️ No API authentication
- ⚠️ No rate limiting
- ⚠️ Gmail credentials in environment
- ⚠️ CORS allows all origins

### Production Hardening
- Add OAuth2 authentication
- Implement rate limiting
- Use Secret Manager for credentials
- Restrict CORS to frontend domain
- Add input validation/sanitization
- Implement API versioning
- Add request signing

---

## Documentation

Complete API reference available at:
- [API_REFERENCE.md](API_REFERENCE.md) - Endpoint documentation with examples
- Interactive Swagger UI: `http://localhost:8000/docs`
- README.md - Project overview

---

**Last Updated:** May 20, 2026  
**Version:** 1.0.0
