# API Reference - Crystal Supplier Email Service

## Base URL
```
http://localhost:8000  (Development)
https://your-service.run.app  (Production)
```

## Authentication
Currently, the API is open to all clients. In production, implement OAuth2 or JWT authentication.

---

## Health & Utility Endpoints

### Health Check
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "Crystal Email Service is running"
}
```

---

## Supplier Endpoints

### Get All Suppliers
```
GET /api/suppliers
```

Returns a list of all suppliers from `suppliers.csv`.

**Response:**
```json
[
  {
    "company_name": "Supplier A",
    "email_id": "contact@suppliera.com",
    "domain": "suppliera.com",
    "salutation": "Dear Mr. Gupta"
  },
  ...
]
```

---

## Job Management Endpoints

### Get All Jobs
```
GET /api/jobs?limit=50
```

**Query Parameters:**
- `limit` (optional, default: 50): Number of jobs to return

**Response:**
```json
[
  {
    "id": 1,
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "created_at": "2026-05-20T10:30:00",
    "status": "active",
    "reminders_sent": false,
    "closed_at": null,
    "total_responses": 0
  },
  ...
]
```

### Create & Start New Job
```
POST /api/jobs/start
```

**Request Body:**
```json
{
  "chemical_query": "20000 MT Methanol CFR Singapore - delivery late June 2026",
  "supplier_emails": [
    "supplier1@example.com",
    "supplier2@example.com",
    "supplier3@example.com"
  ]
}
```

**Response:**
```json
{
  "message": "Job started successfully",
  "job_id": 1,
  "chemical_query": "20000 MT Methanol CFR Singapore - delivery late June 2026",
  "total_suppliers": 3,
  "emails_sent": 3,
  "status": "active"
}
```

### Get Job Details (with Drilldown)
```
GET /api/jobs/{job_id}
```

**Response:**
```json
{
  "job": {
    "id": 1,
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "created_at": "2026-05-20T10:30:00",
    "status": "active",
    "reminders_sent": false,
    "closed_at": null,
    "total_responses": 2
  },
  "suppliers": [
    {
      "id": 1,
      "company_name": "supplier1",
      "email_id": "supplier1@example.com",
      "domain": "example.com",
      "initial_email_sent_at": "2026-05-20T10:30:00",
      "replied": true,
      "reply_received_at": "2026-05-20T11:15:00",
      "reminder_sent_at": null
    },
    ...
  ],
  "insights": [
    {
      "id": 1,
      "supplier": "Supplier A",
      "contact_person": "John Smith",
      "product": "Methanol Grade A",
      "quantity": "20000 MT",
      "price": "$500/MT",
      "delivery_date": "June 28, 2026",
      "extracted_at": "2026-05-20T11:30:00"
    },
    ...
  ],
  "emails": [
    {
      "id": 1,
      "email_type": "outbound",
      "from_email": "noreply@yourdomain.com",
      "to_email": "supplier1@example.com",
      "subject": "Request for Quote: 20000 MT Methanol - supplier1",
      "body": "...",
      "sent_at": "2026-05-20T10:30:00"
    },
    ...
  ]
}
```

### Close Job
```
POST /api/jobs/{job_id}/close
```

**Response:**
```json
{
  "message": "Job closed successfully",
  "job_id": 1,
  "status": "closed",
  "closed_at": "2026-05-20T14:45:00"
}
```

### Refresh Insights for Job
```
POST /api/jobs/{job_id}/insights/refresh
```

Manually trigger AI-powered insight extraction from supplier emails.

**Response:**
```json
{
  "message": "Insights refreshed",
  "job_id": 1,
  "new_insights_extracted": 2,
  "insights": [
    {
      "supplier": "Supplier A",
      "contact_person": "John Smith",
      "product": "Methanol Grade A",
      "quantity": "20000 MT",
      "price": "$500/MT",
      "delivery_date": "June 28, 2026"
    },
    ...
  ]
}
```

---

## Supplier State & Response Endpoints

### Get Suppliers for Job
```
GET /api/jobs/{job_id}/suppliers
```

Get all supplier states for a specific job.

**Response:**
```json
[
  {
    "id": 1,
    "company_name": "Supplier A",
    "email_id": "supplier@example.com",
    "domain": "example.com",
    "initial_email_sent_at": "2026-05-20T10:30:00",
    "replied": true,
    "reply_received_at": "2026-05-20T11:15:00",
    "reminder_sent_at": null
  },
  ...
]
```

### Get Supplier Emails
```
GET /api/suppliers/{supplier_id}/emails
```

Get all email exchanges (sent and received) for a specific supplier.

**Response:**
```json
[
  {
    "id": 1,
    "email_type": "outbound",
    "from_email": "noreply@yourdomain.com",
    "to_email": "supplier@example.com",
    "subject": "Request for Quote: 20000 MT Methanol",
    "body": "...",
    "sent_at": "2026-05-20T10:30:00"
  },
  {
    "id": 2,
    "email_type": "inbound",
    "from_email": "supplier@example.com",
    "to_email": "noreply@yourdomain.com",
    "subject": "RE: Request for Quote: 20000 MT Methanol",
    "body": "We can supply 20000 MT at $500/MT...",
    "sent_at": "2026-05-20T11:15:00"
  },
  ...
]
```

### Send Reminder to Supplier
```
POST /api/jobs/{job_id}/suppliers/{supplier_id}/send-reminder
```

Send a manual reminder email to a supplier who hasn't responded.

**Response:**
```json
{
  "message": "Reminder sent successfully",
  "supplier_id": 1,
  "supplier_email": "supplier@example.com"
}
```

---

## Insights Endpoints

### Get Insights for Job
```
GET /api/jobs/{job_id}/insights
```

Get all extracted insights for a specific job.

**Response:**
```json
[
  {
    "id": 1,
    "supplier": "Supplier A",
    "contact_person": "John Smith",
    "product": "Methanol Grade A",
    "quantity": "20000 MT",
    "price": "$500/MT",
    "delivery_date": "June 28, 2026",
    "extracted_at": "2026-05-20T11:30:00"
  },
  ...
]
```

### Get All Insights Grouped by Supplier
```
GET /api/insights/by-supplier
```

Get all insights across all jobs, grouped by supplier.

**Response:**
```json
{
  "Supplier A": [
    {
      "id": 1,
      "job_id": 1,
      "contact_person": "John Smith",
      "product": "Methanol Grade A",
      "quantity": "20000 MT",
      "price": "$500/MT",
      "delivery_date": "June 28, 2026",
      "extracted_at": "2026-05-20T11:30:00"
    }
  ],
  "Supplier B": [...]
}
```

---

## Statistics & Analytics Endpoints

### Get Summary Statistics
```
GET /api/stats/summary
```

Get overall statistics about all jobs and suppliers.

**Response:**
```json
{
  "jobs": {
    "total": 10,
    "active": 3,
    "closed": 7
  },
  "suppliers": {
    "total": 45,
    "responded": 32,
    "response_rate": "71.1%"
  },
  "insights": {
    "total": 28
  }
}
```

### Get Job Statistics
```
GET /api/stats/job/{job_id}
```

Get detailed statistics for a specific job.

**Response:**
```json
{
  "job_id": 1,
  "chemical_query": "20000 MT Methanol CFR Singapore",
  "status": "active",
  "created_at": "2026-05-20T10:30:00",
  "closed_at": null,
  "suppliers": {
    "total": 10,
    "responded": 7,
    "pending": 3,
    "response_rate": "70.0%"
  },
  "insights_count": 7
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Job not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error message describing the issue"
}
```

---

## Usage Examples

### Example 1: Create and Track a Job

```bash
# 1. Create a new job
curl -X POST http://localhost:8000/api/jobs/start \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_query": "20000 MT Methanol CFR Singapore",
    "supplier_emails": ["supplier1@example.com", "supplier2@example.com"]
  }'

# Response:
# {"message": "Job started successfully", "job_id": 1, ...}

# 2. Get job details
curl http://localhost:8000/api/jobs/1

# 3. Get job statistics
curl http://localhost:8000/api/stats/job/1

# 4. Refresh insights after waiting for responses
curl -X POST http://localhost:8000/api/jobs/1/insights/refresh

# 5. View extracted insights
curl http://localhost:8000/api/jobs/1/insights
```

### Example 2: Monitor Supplier Responses

```bash
# Get all suppliers for a job
curl http://localhost:8000/api/jobs/1/suppliers

# Get emails from a specific supplier
curl http://localhost:8000/api/suppliers/1/emails

# Send reminder to non-responsive supplier
curl -X POST http://localhost:8000/api/jobs/1/suppliers/2/send-reminder
```

### Example 3: Analytics

```bash
# Get overall summary
curl http://localhost:8000/api/stats/summary

# Get insights by supplier (comparison across all jobs)
curl http://localhost:8000/api/insights/by-supplier
```

---

## API Documentation (Swagger UI)

Interactive API documentation is available at:
```
http://localhost:8000/docs
```

---

## Rate Limiting & Quotas

Currently, there are no rate limits. In production, implement:
- Max 100 requests per minute per IP
- Max 10 concurrent jobs per user
- Max 1000 suppliers per job

---

## Changelog

### v1.0.0 (May 2026)
- Initial release
- Core job management
- Supplier response tracking
- Email integration (Gmail API)
- AI-powered insight extraction
- Comprehensive API endpoints
- Statistics and analytics

---

## Support

For API issues or questions, refer to:
- [README.md](../README.md) - Project overview
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment guide
- GitHub Issues - Bug reports and feature requests
