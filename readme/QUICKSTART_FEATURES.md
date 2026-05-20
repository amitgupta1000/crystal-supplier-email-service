# Getting Started with New Features

## What's New?

Your Crystal Supplier Email Service now has:

✅ **Complete email utilities** - Send and receive supplier emails  
✅ **AI insights extraction** - Automatic data extraction from emails  
✅ **23 new API endpoints** - Full job and supplier management  
✅ **Job drilldown** - View all job details in one place  
✅ **Response tracking** - Know which suppliers replied  
✅ **Automated reminders** - Send follow-ups automatically  

---

## 5-Minute Quick Start

### 1. Start the Backend
```bash
cd /path/to/crystal-supplier-email-service
python main.py
# or
uvicorn main:app --reload
```

The API will be available at: **http://localhost:8000**

### 2. Create Your First Job
```bash
curl -X POST http://localhost:8000/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "supplier_emails": ["supplier1@example.com", "supplier2@example.com"]
  }'
```

**Response:**
```json
{
  "message": "Job started successfully",
  "job_id": 1,
  "total_suppliers": 2,
  "emails_sent": 2,
  "status": "active"
}
```

### 3. View Job Details
```bash
curl http://localhost:8000/api/jobs/1
```

**Response includes:**
- Job status and timeline
- All suppliers and their reply status
- Email history
- Extracted insights
- Statistics

### 4. Refresh Insights (Extract Data)
```bash
curl -X POST http://localhost:8000/api/jobs/1/insights/refresh
```

**Response:**
```json
{
  "message": "Insights refreshed",
  "new_insights_extracted": 2,
  "insights": [
    {
      "supplier": "Supplier A",
      "contact_person": "John Smith",
      "product": "Methanol Grade A",
      "quantity": "20000 MT",
      "price": "$500/MT",
      "delivery_date": "June 28, 2026"
    }
  ]
}
```

**Done!** 🎉

---

## Using the Quick Reference Script

For easier testing, use the included bash functions:

```bash
# Source the script
source quick-reference.sh

# Now you can use these commands:

# Check health
health

# Get all suppliers
get_suppliers

# Create a job (returns job_id)
job_id=$(create_job "Test Job" "supplier1@ex.com" "supplier2@ex.com")

# Get job details
get_job $job_id

# Get supplier list for job
get_job_suppliers $job_id

# Get insights
get_job_insights $job_id

# Refresh insights
refresh_insights $job_id

# Send reminder to supplier
send_reminder $job_id 1

# Get statistics
get_summary_stats
get_job_stats $job_id

# Run complete workflow example
workflow_complete
```

---

## Common Tasks

### Task 1: Send RFQ to Suppliers

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_query": "Your product query",
    "supplier_emails": ["supplier1@ex.com", "supplier2@ex.com"]
  }'
```

**Option B: Using quick-reference.sh**
```bash
source quick-reference.sh
create_job "Your query" "supplier1@ex.com" "supplier2@ex.com"
```

### Task 2: Check Which Suppliers Replied

**Option A: Get job details**
```bash
curl http://localhost:8000/api/jobs/1 | jq '.suppliers'
```

**Option B: Using quick-reference.sh**
```bash
get_job 1
```

Look for the `"replied"` field for each supplier.

### Task 3: Extract Supplier Data Automatically

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/jobs/1/insights/refresh
```

**Option B: Using quick-reference.sh**
```bash
refresh_insights 1
```

Returns extracted: contact person, product, quantity, price, delivery date

### Task 4: Send Follow-up Email to Non-Responsive Supplier

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/jobs/1/suppliers/2/send-reminder
```

**Option B: Using quick-reference.sh**
```bash
send_reminder 1 2
```

### Task 5: View All Emails for a Supplier

**Option A: Via API**
```bash
curl http://localhost:8000/api/suppliers/2/emails
```

**Option B: Get from job details**
```bash
curl http://localhost:8000/api/jobs/1 | jq '.emails'
```

### Task 6: Get Insights Grouped by Supplier

```bash
curl http://localhost:8000/api/insights/by-supplier
```

Returns insights organized by supplier company name.

### Task 7: Check Overall Statistics

```bash
curl http://localhost:8000/api/stats/summary
```

Shows: total jobs, suppliers, insights, response rates, etc.

### Task 8: Check Job-Specific Statistics

```bash
curl http://localhost:8000/api/stats/job/1
```

Shows: suppliers responding, response rate, insights extracted, etc.

---

## All Endpoints (Quick Reference)

### Health
- `GET /health`

### Suppliers
- `GET /api/suppliers`
- `GET /api/suppliers/{id}/emails`

### Jobs
- `GET /api/jobs`
- `POST /api/jobs/start`
- `GET /api/jobs/{id}`
- `POST /api/jobs/{id}/close`
- `GET /api/jobs/{id}/suppliers`
- `GET /api/jobs/{id}/insights`

### Actions
- `POST /api/jobs/{id}/insights/refresh`
- `POST /api/jobs/{id}/suppliers/{sid}/send-reminder`

### Analytics
- `GET /api/stats/summary`
- `GET /api/stats/job/{id}`
- `GET /api/insights/by-supplier`

---

## Configuration

### Gmail Setup
You need to set these environment variables:

```bash
export GMAIL_IMPERSONATE_USER=noreply@yourdomain.com
export EMAIL_SENDER=noreply@yourdomain.com
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

See [.env.example](.env.example) for all options.

### Generative AI Setup
```bash
export GOOGLE_GENAI_API_KEY=your-api-key
```

Get your API key from [Google AI Studio](https://aistudio.google.com/)

---

## Testing

### Run All Tests
```bash
pytest test_api.py -v
```

### Test Specific Endpoint
```bash
pytest test_api.py::TestJobEndpoints -v
```

### Manual Testing
```bash
chmod +x test-api.sh
./test-api.sh http://localhost:8000
```

---

## Job Lifecycle

```
1. Create Job
   ↓ (sends initial emails)
2. Monitor Responses
   ↓ (wait for supplier emails)
3. Refresh Insights
   ↓ (AI extracts data)
4. Send Reminders (optional)
   ↓ (at T+24h automatically or manual)
5. Close Job
   ↓ (archives results at T+48h automatically)
```

All steps can be triggered manually via API or happen automatically via scheduler.

---

## Key Concepts

### Job
A procurement campaign with a chemical query and target suppliers.

### JobSupplierState
Tracks one supplier for one job:
- Did they reply? (`replied` field)
- When? (`reply_received_at`)
- Did we send reminder? (`reminder_sent_at`)

### SupplierEmail
A single email (sent or received):
- `email_type`: "outbound" or "inbound"
- `subject`, `body`: Email content
- `from_email`, `to_email`: Email addresses
- `sent_at`: Timestamp

### Insight
Extracted data from supplier email:
- `supplier`: Company name
- `contact_person`: Contact name
- `product`: Product description
- `quantity`: Order quantity
- `price`: Price per unit
- `delivery_date`: When available

---

## Response Format

All successful responses follow this pattern:

```json
{
  "message": "Success description",
  "data": { ... }
}
```

For lists:
```json
{
  "data": [ ... ],
  "total": 10,
  "limit": 20
}
```

For errors:
```json
{
  "detail": "Error description"
}
```

---

## Common HTTP Status Codes

- `200` - OK
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found
- `500` - Server Error

---

## Next Steps

1. **Configure Gmail** - Set up domain-wide delegation
2. **Configure AI** - Get and set API key
3. **Create Test Jobs** - Use quick-reference.sh
4. **Monitor Emails** - Check supplier responses
5. **Extract Insights** - Refresh insights
6. **Deploy** - Use deploy-gcp.sh for production

---

## Documentation

For more details, see:
- [API_REFERENCE.md](API_REFERENCE.md) - All endpoints
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Configuration
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production setup

---

## Troubleshooting

### Issue: Email not sending
```
Check GOOGLE_APPLICATION_CREDENTIALS is set
Check service account has Gmail API enabled
Check domain-wide delegation is configured
```

### Issue: Insights not extracting
```
Check GOOGLE_GENAI_API_KEY is set
Check Generative AI API is enabled
Check email body contains supplier data
```

### Issue: API not responding
```
Check backend is running (python main.py)
Check port 8000 is not in use
Check firewall allows localhost:8000
```

---

## Support

For detailed help, see:
- Quick reference: `source quick-reference.sh && help`
- Run tests: `pytest test_api.py -v`
- Check logs: Look at terminal output or log files
- Full docs: [API_REFERENCE.md](API_REFERENCE.md)

---

**Happy supplier emailing! 🚀**
