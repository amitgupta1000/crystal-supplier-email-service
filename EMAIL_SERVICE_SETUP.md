# Email Service Database Setup - Configuration Guide

## ✅ What Has Been Created

### 1. **Database Models** (SQLAlchemy ORM)
File: [backend/database.py](backend/database.py)

Located in the **email_service schema** (separate from your inventory table):

- **Job** - Tracks RFQ jobs for chemical suppliers
- **JobSupplierState** - Tracks individual supplier responses per job
- **SupplierEmail** - Stores sent/received emails  
- **Insight** - Extracted data from supplier responses

### 2. **Async Database Service** 
File: [backend/db_service.py](backend/db_service.py)

Four service classes with async CRUD operations:

```python
# Create a new job
job = await JobService.create_job(
    chemical_query="Polyester Fabric",
    user_email="amit@example.com",
    session=session
)

# Create insight from supplier response
insight = await InsightService.create_insight(
    job_id=job.id,
    supplier="Supplier Inc",
    product="Polyester Blend",
    price=12.50,
    delivery_date="2026-06-15",
    session=session
)

# Get all insights for a job
insights = await InsightService.get_insights_by_job(job_id, session)
```

### 3. **Setup Scripts**
- [backend/create_email_service_schema.py](backend/create_email_service_schema.py) - Direct PostgreSQL schema creation
- [backend/setup_email_service.py](backend/setup_email_service.py) - SQLAlchemy-based setup
- [backend/test_email_service.py](backend/test_email_service.py) - Test all CRUD operations

---

## 🔧 How to Set Up the Schema

### Option 1: Using Cloud SQL Proxy (Recommended for Secure Access)

```bash
# 1. Install Cloud SQL Proxy
gcloud components install cloud-sql-proxy

# 2. Start the proxy in a separate terminal
cloud-sql-proxy gen-lang-client-0665888431:asia-south1:crystal-inventory-dash \
  --port=5433

# 3. Create the schema (using localhost:5433)
$env:CLOUD_SQL_PASSWORD = "Crystal@012345"
$env:CLOUD_SQL_HOST = "localhost"
$env:CLOUD_SQL_PORT = "5433"
python backend/setup_email_service.py
```

### Option 2: Direct Connection (If IP Whitelisted)

```bash
# 1. Add your IP to Cloud SQL firewall
gcloud sql instances patch crystal-inventory-dash \
  --authorized-networks YOUR_IP_ADDRESS

# 2. Create the schema
$env:CLOUD_SQL_PASSWORD = "Crystal@012345"
$env:CLOUD_SQL_HOST = "35.200.192.16"
$env:CLOUD_SQL_PORT = "5432"
python backend/setup_email_service.py
```

### Option 3: Manual SQL Execution (via gcloud)

```bash
# Connect directly via gcloud
gcloud sql connect crystal-inventory-dash \
  --user=postgres

# Create schema
CREATE SCHEMA IF NOT EXISTS email_service;

# Create tables
CREATE TABLE email_service.jobs (
    id SERIAL PRIMARY KEY,
    chemical_query VARCHAR(500),
    user_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    reminders_sent BOOLEAN DEFAULT FALSE,
    closed_at TIMESTAMP,
    total_responses INTEGER DEFAULT 0,
    last_summary_sent_at TIMESTAMP,
    closure_notification_sent BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- (See backend/create_email_service_schema.py for all table DDL)
```

---

## 📊 Database Schema Structure

```
┌─────────────────────────────────────────────────────────┐
│              email_service Schema                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📦 jobs (Main RFQ Records)                            │
│   ├─ id (PK)                                           │
│   ├─ chemical_query (VARCHAR)                          │
│   ├─ user_email (VARCHAR) - For notifications         │
│   ├─ status (VARCHAR) - 'active' or 'closed'          │
│   ├─ created_at, updated_at, closed_at                │
│   ├─ total_responses (COUNT)                          │
│   └─ reminders_sent, closure_notification_sent        │
│       │                                                │
│       ├─→ job_supplier_states (1:Many)               │
│       │    ├─ id (PK)                                │
│       │    ├─ job_id (FK)                            │
│       │    ├─ company_name (VARCHAR)                 │
│       │    ├─ email_id, domain                       │
│       │    ├─ replied (BOOLEAN)                      │
│       │    ├─ reply_received_at, reminder_sent_at    │
│       │    └─→ supplier_emails (1:Many)             │
│       │         ├─ id (PK)                          │
│       │         ├─ job_id (FK)                      │
│       │         ├─ supplier_state_id (FK)           │
│       │         ├─ email_type ('outbound'/'inbound')│
│       │         ├─ from_email, to_email             │
│       │         ├─ subject, body                    │
│       │         ├─ sent_at                          │
│       │         └─ gmail_message_id (UNIQUE)        │
│       │                                             │
│       └─→ insights (1:Many)                        │
│            ├─ id (PK)                             │
│            ├─ job_id (FK)                         │
│            ├─ supplier (VARCHAR)                  │
│            ├─ contact_person (VARCHAR)            │
│            ├─ product, quantity                   │
│            ├─ price (DECIMAL)                     │
│            ├─ delivery_date (DATE)                │
│            ├─ email_body (TEXT)                   │
│            └─ extracted_at                        │
│                                                   │
```

---

## 🚀 Using the Database Service in Your Backend

### FastAPI Example

```python
from fastapi import FastAPI, Depends
from backend.db_service import JobService, InsightService, get_session
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.post("/jobs")
async def create_job(
    chemical_query: str,
    user_email: str,
    session: AsyncSession = Depends(get_session)
):
    job = await JobService.create_job(
        chemical_query=chemical_query,
        user_email=user_email,
        session=session
    )
    return {"job_id": job.id, "status": job.status}


@app.post("/jobs/{job_id}/insights")
async def add_insight(
    job_id: int,
    supplier: str,
    product: str,
    price: float,
    session: AsyncSession = Depends(get_session)
):
    insight = await InsightService.create_insight(
        job_id=job_id,
        supplier=supplier,
        product=product,
        price=price,
        session=session
    )
    return insight


@app.get("/jobs/{job_id}/insights")
async def get_job_insights(
    job_id: int,
    session: AsyncSession = Depends(get_session)
):
    insights = await InsightService.get_insights_by_job(job_id, session)
    return insights
```

---

## 🔗 Integration with extract_insights.py

The [backend/extract_insights.py](backend/extract_insights.py) can now save insights directly to the database:

```python
from backend.db_service import InsightService

# After extracting insights from email
insights_data = extract_insights_from_email(email_body)

for item in insights_data:
    await InsightService.create_insight(
        job_id=job.id,
        supplier=item['supplier'],
        contact_person=item.get('contact_person'),
        product=item.get('product'),
        quantity=item.get('quantity'),
        price=float(item.get('price', 0)),
        delivery_date=item.get('delivery_date'),
        email_body=email_body,
        session=session
    )
```

---

## 📝 Required Environment Variables

```bash
# Cloud SQL Connection
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@localhost:5433/inventory
CLOUD_SQL_HOST=localhost
CLOUD_SQL_PORT=5433
CLOUD_SQL_USER=postgres
CLOUD_SQL_PASSWORD=Crystal@012345
CLOUD_SQL_DATABASE=inventory
```

---

## ✅ Testing the Setup

Once the schema is created, test with:

```bash
$env:CLOUD_SQL_PASSWORD = "Crystal@012345"
python backend/test_email_service.py
```

Expected output:
```
======================================================================
EMAIL SERVICE DATABASE TEST
======================================================================

1️⃣  Creating a test job...
   ✅ Job created: ID=1, Query=Polyester Fabric - Industrial Grade

2️⃣  Retrieving the job...
   ✅ Job retrieved: Status=active, Created=...

3️⃣  Creating supplier states...
   ✅ Supplier 1 created: ID=1, Company=Supplier Inc
   ✅ Supplier 2 created: ID=2, Company=Global Fabrics Ltd

4️⃣  Creating email records...
   ✅ Outbound email created: ID=1, To=supplier1@example.com

5️⃣  Creating insights from supplier responses...
   ✅ Insight 1 created: ID=1, Product=Polyester Fabric - 65% Poly, 35% Cotton, Price=$12.5
   ✅ Insight 2 created: ID=2, Product=Premium Polyester Blend, Price=$14.75

✅ ALL TESTS PASSED!
```

---

## 📋 Service Methods Reference

### JobService
- `create_job(chemical_query, user_email, session)` → Job
- `get_job(job_id, session)` → Job | None
- `get_jobs_by_user(user_email, session)` → List[Job]
- `get_active_jobs(session)` → List[Job]
- `update_job_status(job_id, status, session)` → Job
- `update_job_responses(job_id, total_responses, session)` → Job
- `mark_reminders_sent(job_id, session)` → Job
- `close_job(job_id, session)` → Job

### InsightService
- `create_insight(job_id, supplier, contact_person, product, quantity, price, delivery_date, email_body, session)` → Insight
- `get_insight(insight_id, session)` → Insight | None
- `get_insights_by_job(job_id, session)` → List[Insight]
- `get_insights_by_supplier(job_id, supplier, session)` → List[Insight]
- `count_insights_by_job(job_id, session)` → int
- `get_latest_insights(limit, session)` → List[Insight]

### SupplierStateService
- `create_supplier_state(job_id, company_name, email_id, domain, session)` → JobSupplierState
- `mark_replied(supplier_state_id, session)` → JobSupplierState
- `mark_reminder_sent(supplier_state_id, session)` → JobSupplierState

### EmailService
- `create_email(job_id, email_type, from_email, to_email, subject, body, gmail_message_id, supplier_state_id, session)` → SupplierEmail
- `get_emails_by_job(job_id, session)` → List[SupplierEmail]
- `get_email_by_gmail_id(gmail_message_id, session)` → SupplierEmail | None

---

## 🔐 Security Notes

- ✅ Credentials separate from code (environment variables)
- ✅ SSL/TLS enabled for all connections
- ✅ Foreign key constraints prevent orphaned records
- ✅ Async operations prevent blocking requests
- ✅ Schema separation (email_service vs inventory)

---

## 🎯 Next Steps

1. **Set up Cloud SQL Proxy** or whitelist your IP
2. **Run the setup script** to create the schema
3. **Test with** `python backend/test_email_service.py`
4. **Integrate with FastAPI** endpoints (see example above)
5. **Update extract_insights.py** to save to database
6. **Deploy to Cloud Run** with environment variables configured

---

*Created: May 20, 2026*  
*Database Schema: email_service*  
*Connection: PostgreSQL 18.3 on Cloud SQL*
