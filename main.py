import csv
import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Optional, AsyncGenerator

# Expand home directory in GOOGLE_APPLICATION_CREDENTIALS if present
if gcp_creds := os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    expanded_path = os.path.expanduser(gcp_creds)
    if os.path.exists(expanded_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = expanded_path
        print(f"✅ GCP Credentials found at: {expanded_path}")
    else:
        print(f"⚠️  GCP Credentials path not found: {expanded_path}")

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict
import logging
import uvicorn

from backend.database import AsyncSessionLocal, Job, JobSupplierState, Insight, SupplierEmail, Base, engine
from backend.scheduler import start_scheduler
from backend.email_utils import send_email_with_attachments, send_reminder_email, fetch_unread_replies
from backend.extract_insights import extract_insights_from_email, process_supplier_responses
from backend.notification_service import send_insight_notification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db():
    """Initialize database tables on startup."""
    try:
        async with engine.begin() as conn:
            # Create email_service schema if it doesn't exist
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS email_service;"))
            # Create all tables from ORM models
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Database initialization failed (will retry on first request): {e}")
        # Don't fail startup - tables will be created on first request

# Pydantic models for API
class StartJobRequest(BaseModel):
    chemical_query: str
    supplier_emails: List[str]
    user_email: str  # Email for notifications


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    chemical_query: str
    created_at: datetime
    status: str
    reminders_sent: bool
    closed_at: Optional[datetime] = None
    total_responses: int


class SupplierStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    company_name: str
    email_id: str
    domain: str
    initial_email_sent_at: datetime
    replied: bool
    reply_received_at: Optional[datetime] = None
    reminder_sent_at: Optional[datetime] = None


class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    supplier: str
    contact_person: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    delivery_date: Optional[str] = None
    extracted_at: datetime


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email_type: str
    from_email: str
    to_email: str
    subject: str
    body: str
    sent_at: datetime


class JobDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    job: JobResponse
    suppliers: List[SupplierStateResponse]
    insights: List[InsightResponse]
    emails: List[EmailResponse]


class SupplierResponse(BaseModel):
    company_name: str
    email_id: str
    domain: str
    salutation: str


class HealthResponse(BaseModel):
    status: str
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    await init_db()
    start_scheduler()
    yield
    logger.info("Shutting down application...")
    await engine.dispose()


app = FastAPI(title="CRYSTAL SUPPLIER EMAIL SERVICE", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        yield session


# ============================================================================
# HEALTH & UTILITY ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Crystal Email Service is running"
    }


# ============================================================================
# SUPPLIER ENDPOINTS
# ============================================================================

@app.get("/api/suppliers", response_model=List[SupplierResponse])
def get_suppliers():
    """Get all suppliers from suppliers.csv."""
    suppliers = []
    try:
        with open("suppliers.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                suppliers.append({
                    "company_name": row.get("Company Name", ""),
                    "email_id": row.get("Email ID", ""),
                    "domain": row.get("Email ID", "").split("@")[-1] if row.get("Email ID") else "",
                    "salutation": row.get("Salutation 1", "Hello")
                })
    except FileNotFoundError:
        logger.error("suppliers.csv not found")
    return suppliers


# ============================================================================
# JOB ENDPOINTS
# ============================================================================

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_all_jobs(db: AsyncSession = Depends(get_db), limit: int = 50):
    """Get all jobs with pagination."""
    query = select(Job).order_by(Job.created_at.desc()).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific job including suppliers, emails, and insights."""
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    suppliers_query = select(JobSupplierState).where(JobSupplierState.job_id == job_id)
    suppliers_result = await db.execute(suppliers_query)
    suppliers = suppliers_result.scalars().all()
    
    insights_query = select(Insight).where(Insight.job_id == job_id)
    insights_result = await db.execute(insights_query)
    insights = insights_result.scalars().all()
    
    emails_query = select(SupplierEmail).where(SupplierEmail.job_id == job_id).order_by(SupplierEmail.sent_at.desc())
    emails_result = await db.execute(emails_query)
    emails = emails_result.scalars().all()
    
    return {
        "job": job,
        "suppliers": suppliers,
        "insights": insights,
        "emails": emails
    }


@app.post("/api/jobs/start", response_model=dict)
async def start_job(request: StartJobRequest, db: AsyncSession = Depends(get_db)):
    """Create and start a new RFQ job."""
    try:
        # Create job in database
        new_job = Job(
            chemical_query=request.chemical_query,
            user_email=request.user_email,
            status="active"
        )
        db.add(new_job)
        await db.flush()  # Get the job ID without committing
        
        logger.info(f"Created job {new_job.id} with query: {request.chemical_query}")
        
        # Record targeted suppliers
        sent_count = 0
        for email in request.supplier_emails:
            domain = email.split("@")[-1] if email else ""
            
            state = JobSupplierState(
                job_id=new_job.id,
                company_name=email.split("@")[0],  # Use email prefix as company name for now
                email_id=email,
                domain=domain,
            )
            db.add(state)
            await db.flush()
            
            # Send initial RFQ email
            subject = f"Request for Quote: {request.chemical_query}"
            body = f"""
            <p>Hello,</p>
            
            <p>I hope this email finds you well. I am reaching out regarding the following procurement inquiry:</p>
            
            <p><strong>{request.chemical_query}</strong></p>
            
            <p>Could you please provide a quote with the following details:</p>
            <ul>
                <li>Product specifications</li>
                <li>Pricing</li>
                <li>Quantity available</li>
                <li>Delivery timeline</li>
                <li>Terms & conditions</li>
            </ul>
            
            <p>Please reply to this email at your earliest convenience. If you have any questions, feel free to ask.</p>
            
            <p>Thank you for your time and consideration.</p>
            
            <p>Best regards,<br>
            Amit<br>
            Procurement Team</p>
            """
            
            success = await send_email_with_attachments(subject, body, email)
            
            if success:
                sent_count += 1
                email_record = SupplierEmail(
                    job_id=new_job.id,
                    supplier_state_id=state.id,
                    email_type="outbound",
                    from_email="noreply@yourdomain.com",
                    to_email=email,
                    subject=subject,
                    body=body
                )
                db.add(email_record)
            else:
                logger.warning(f"Failed to send email to {email}")
        
        await db.commit()
        
        return {
            "message": "Job started successfully",
            "job_id": new_job.id,
            "chemical_query": new_job.chemical_query,
            "total_suppliers": len(request.supplier_emails),
            "emails_sent": sent_count,
            "status": "active",
            "notification_email": new_job.user_email
        }
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting job: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting job: {str(e)}")


@app.post("/api/jobs/{job_id}/insights/refresh")
async def refresh_insights(job_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger insights extraction for a job."""
    try:
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get supplier domains for this job
        suppliers_query = select(JobSupplierState).where(JobSupplierState.job_id == job_id)
        suppliers_result = await db.execute(suppliers_query)
        suppliers = suppliers_result.scalars().all()
        domains = list(set([s.domain for s in suppliers]))
        
        logger.info(f"Refreshing insights for job {job_id}, domains: {domains}")
        
        # Process supplier responses
        insights_list = await process_supplier_responses(domains, job_id)
        
        inserted_count = 0
        for insight_data in insights_list:
            # Check if insight already exists
            existing_query = select(Insight).where(
                Insight.job_id == job_id,
                Insight.supplier == insight_data.supplier
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if not existing:
                insight = Insight(
                    job_id=job_id,
                    supplier=insight_data.supplier or "Unknown",
                    contact_person=insight_data.contact_person,
                    product=insight_data.product,
                    quantity=insight_data.quantity,
                    price=insight_data.price,
                    delivery_date=insight_data.delivery_date,
                    email_body=insight_data.email_body,
                    extracted_at=datetime.utcnow()
                )
                db.add(insight)
                inserted_count += 1
        
        # Update total responses
        job.total_responses = inserted_count
        await db.commit()
        
        # Send notification if there are new insights
        if inserted_count > 0:
            new_insights_query = select(Insight).where(Insight.job_id == job_id)
            new_insights_result = await db.execute(new_insights_query)
            new_insights = new_insights_result.scalars().all()
            await send_insight_notification(job, inserted_count, new_insights)
        
        return {
            "message": "Insights refreshed",
            "job_id": job_id,
            "new_insights_extracted": inserted_count,
            "insights": [
                {
                    "supplier": i.supplier,
                    "contact_person": i.contact_person,
                    "product": i.product,
                    "quantity": i.quantity,
                    "price": i.price,
                    "delivery_date": i.delivery_date
                }
                for i in new_insights
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error refreshing insights: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing insights: {str(e)}")


@app.post("/api/jobs/{job_id}/close")
async def close_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Manually close a job."""
    try:
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = "closed"
        job.closed_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Closed job {job_id}")
        
        return {
            "message": "Job closed successfully",
            "job_id": job_id,
            "status": "closed",
            "closed_at": job.closed_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error closing job: {e}")
        raise HTTPException(status_code=500, detail=f"Error closing job: {str(e)}")


# ============================================================================
# SUPPLIER STATE & EMAIL ENDPOINTS
# ============================================================================

@app.get("/api/jobs/{job_id}/suppliers", response_model=List[SupplierStateResponse])
async def get_job_suppliers(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get all suppliers for a specific job."""
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    suppliers_query = select(JobSupplierState).where(JobSupplierState.job_id == job_id)
    suppliers_result = await db.execute(suppliers_query)
    suppliers = suppliers_result.scalars().all()
    return suppliers


@app.get("/api/suppliers/{supplier_id}/emails", response_model=List[EmailResponse])
async def get_supplier_emails(supplier_id: int, db: AsyncSession = Depends(get_db)):
    """Get all emails for a specific supplier state."""
    supplier_query = select(JobSupplierState).where(JobSupplierState.id == supplier_id)
    supplier_result = await db.execute(supplier_query)
    supplier = supplier_result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier state not found")
    
    emails_query = select(SupplierEmail).where(SupplierEmail.supplier_state_id == supplier_id).order_by(SupplierEmail.sent_at.desc())
    emails_result = await db.execute(emails_query)
    emails = emails_result.scalars().all()
    return emails


@app.post("/api/jobs/{job_id}/suppliers/{supplier_id}/send-reminder")
async def send_reminder(job_id: int, supplier_id: int, db: AsyncSession = Depends(get_db)):
    """Send a reminder email to a supplier."""
    try:
        job_query = select(Job).where(Job.id == job_id)
        job_result = await db.execute(job_query)
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        supplier_query = select(JobSupplierState).where(
            JobSupplierState.id == supplier_id,
            JobSupplierState.job_id == job_id
        )
        supplier_result = await db.execute(supplier_query)
        supplier = supplier_result.scalar_one_or_none()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found for this job")
        
        # Send reminder email
        success = await send_reminder_email(
            supplier.email_id,
            supplier.company_name,
            job.chemical_query
        )
        
        if success:
            supplier.reminder_sent_at = datetime.utcnow()
            
            email_record = SupplierEmail(
                job_id=job_id,
                supplier_state_id=supplier_id,
                email_type="outbound",
                from_email="noreply@yourdomain.com",
                to_email=supplier.email_id,
                subject=f"Reminder: Request for Quote - {job.chemical_query}",
                body="[Reminder email sent]"
            )
            db.add(email_record)
            await db.commit()
            
            return {
                "message": "Reminder sent successfully",
                "supplier_id": supplier_id,
                "supplier_email": supplier.email_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send reminder email")
            
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error sending reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending reminder: {str(e)}")


# ============================================================================
# INSIGHTS ENDPOINTS
# ============================================================================

@app.get("/api/jobs/{job_id}/insights", response_model=List[InsightResponse])
async def get_job_insights(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get all insights for a specific job."""
    job_query = select(Job).where(Job.id == job_id)
    job_result = await db.execute(job_query)
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    insights_query = select(Insight).where(Insight.job_id == job_id).order_by(Insight.extracted_at.desc())
    insights_result = await db.execute(insights_query)
    insights = insights_result.scalars().all()
    return insights


@app.get("/api/insights/by-supplier", response_model=dict)
async def get_insights_by_supplier(db: AsyncSession = Depends(get_db)):
    """Get all insights grouped by supplier."""
    insights_query = select(Insight)
    insights_result = await db.execute(insights_query)
    insights = insights_result.scalars().all()
    
    grouped = {}
    for insight in insights:
        supplier = insight.supplier or "Unknown"
        if supplier not in grouped:
            grouped[supplier] = []
        grouped[supplier].append({
            "id": insight.id,
            "job_id": insight.job_id,
            "contact_person": insight.contact_person,
            "product": insight.product,
            "quantity": insight.quantity,
            "price": insight.price,
            "delivery_date": insight.delivery_date,
            "extracted_at": insight.extracted_at
        })
    
    return grouped


# ============================================================================
# STATISTICS & ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats/summary")
async def get_summary_stats(db: AsyncSession = Depends(get_db)):
    """Get overall statistics about jobs and responses."""
    total_jobs_result = await db.execute(select(Job))
    total_jobs = len(total_jobs_result.scalars().all())
    
    active_jobs_result = await db.execute(select(Job).where(Job.status == "active"))
    active_jobs = len(active_jobs_result.scalars().all())
    
    closed_jobs_result = await db.execute(select(Job).where(Job.status == "closed"))
    closed_jobs = len(closed_jobs_result.scalars().all())
    
    total_suppliers_result = await db.execute(select(JobSupplierState))
    total_suppliers = len(total_suppliers_result.scalars().all())
    
    responded_suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.replied == True))
    responded_suppliers = len(responded_suppliers_result.scalars().all())
    
    total_insights_result = await db.execute(select(Insight))
    total_insights = len(total_insights_result.scalars().all())
    
    return {
        "jobs": {
            "total": total_jobs,
            "active": active_jobs,
            "closed": closed_jobs
        },
        "suppliers": {
            "total": total_suppliers,
            "responded": responded_suppliers,
            "response_rate": f"{(responded_suppliers / max(total_suppliers, 1) * 100):.1f}%"
        },
        "insights": {
            "total": total_insights
        }
    }


@app.get("/api/stats/job/{job_id}")
async def get_job_stats(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get statistics for a specific job."""
    job_query = select(Job).where(Job.id == job_id)
    job_result = await db.execute(job_query)
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    total_suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job_id))
    total_suppliers = len(total_suppliers_result.scalars().all())
    
    responded_result = await db.execute(select(JobSupplierState).where(
        JobSupplierState.job_id == job_id,
        JobSupplierState.replied == True
    ))
    responded = len(responded_result.scalars().all())
    
    insights_result = await db.execute(select(Insight).where(Insight.job_id == job_id))
    insights = len(insights_result.scalars().all())
    
    return {
        "job_id": job_id,
        "chemical_query": job.chemical_query,
        "status": job.status,
        "created_at": job.created_at,
        "closed_at": job.closed_at,
        "suppliers": {
            "total": total_suppliers,
            "responded": responded,
            "pending": total_suppliers - responded,
            "response_rate": f"{(responded / max(total_suppliers, 1) * 100):.1f}%"
        },
        "insights_count": insights
    }


if __name__ == "__main__":
    import os
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
