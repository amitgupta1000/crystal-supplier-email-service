import csv
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import uvicorn

from backend.database import SessionLocal, Job, JobSupplierState, Insight, SupplierEmail, Base, engine
from backend.scheduler import start_scheduler
from backend.email_utils import send_email_with_attachments, send_reminder_email, fetch_unread_replies
from backend.extract_insights import extract_insights_from_email, process_supplier_responses

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

# Pydantic models for API
class StartJobRequest(BaseModel):
    chemical_query: str
    supplier_emails: List[str]


class JobResponse(BaseModel):
    id: int
    chemical_query: str
    created_at: datetime
    status: str
    reminders_sent: bool
    closed_at: Optional[datetime] = None
    total_responses: int

    class Config:
        from_attributes = True


class SupplierStateResponse(BaseModel):
    id: int
    company_name: str
    email_id: str
    domain: str
    initial_email_sent_at: datetime
    replied: bool
    reply_received_at: Optional[datetime] = None
    reminder_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InsightResponse(BaseModel):
    id: int
    supplier: str
    contact_person: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[str] = None
    price: Optional[str] = None
    delivery_date: Optional[str] = None
    extracted_at: datetime

    class Config:
        from_attributes = True


class EmailResponse(BaseModel):
    id: int
    email_type: str
    from_email: str
    to_email: str
    subject: str
    body: str
    sent_at: datetime

    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    job: JobResponse
    suppliers: List[SupplierStateResponse]
    insights: List[InsightResponse]
    emails: List[EmailResponse]

    class Config:
        from_attributes = True


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
    start_scheduler()
    yield
    logger.info("Shutting down application...")


app = FastAPI(title="CRYSTAL SUPPLIER EMAIL SERVICE", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
def get_all_jobs(db: Session = Depends(get_db), limit: int = 50):
    """Get all jobs with pagination."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    return jobs


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific job including suppliers, emails, and insights."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    suppliers = db.query(JobSupplierState).filter(JobSupplierState.job_id == job_id).all()
    insights = db.query(Insight).filter(Insight.job_id == job_id).all()
    emails = db.query(SupplierEmail).filter(SupplierEmail.job_id == job_id).order_by(SupplierEmail.sent_at.desc()).all()
    
    return {
        "job": job,
        "suppliers": suppliers,
        "insights": insights,
        "emails": emails
    }


@app.post("/api/jobs/start", response_model=dict)
def start_job(request: StartJobRequest, db: Session = Depends(get_db)):
    """Create and start a new RFQ job."""
    try:
        # Create job in database
        new_job = Job(
            chemical_query=request.chemical_query,
            status="active"
        )
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        
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
            
            success = send_email_with_attachments(subject, body, email)
            
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
        
        db.commit()
        
        return {
            "message": "Job started successfully",
            "job_id": new_job.id,
            "chemical_query": new_job.chemical_query,
            "total_suppliers": len(request.supplier_emails),
            "emails_sent": sent_count,
            "status": "active"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error starting job: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting job: {str(e)}")


@app.post("/api/jobs/{job_id}/insights/refresh")
def refresh_insights(job_id: int, db: Session = Depends(get_db)):
    """Manually trigger insights extraction for a job."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get supplier domains for this job
        suppliers = db.query(JobSupplierState).filter(JobSupplierState.job_id == job_id).all()
        domains = list(set([s.domain for s in suppliers]))
        
        logger.info(f"Refreshing insights for job {job_id}, domains: {domains}")
        
        # Process supplier responses
        insights_list = process_supplier_responses(domains, job_id)
        
        inserted_count = 0
        for insight_data in insights_list:
            # Check if insight already exists
            existing = db.query(Insight).filter(
                Insight.job_id == job_id,
                Insight.supplier == insight_data.supplier
            ).first()
            
            if not existing:
                insight = Insight(
                    job_id=job_id,
                    supplier=insight_data.supplier or "Unknown",
                    contact_person=insight_data.contact_person,
                    product=insight_data.product,
                    quantity=insight_data.quantity,
                    price=insight_data.price,
                    delivery_date=insight_data.delivery_date,
                    extracted_at=datetime.utcnow()
                )
                db.add(insight)
                inserted_count += 1
        
        # Update total responses
        job.total_responses = inserted_count
        db.commit()
        
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
                for i in db.query(Insight).filter(Insight.job_id == job_id).all()
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error refreshing insights: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing insights: {str(e)}")


@app.post("/api/jobs/{job_id}/close")
def close_job(job_id: int, db: Session = Depends(get_db)):
    """Manually close a job."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = "closed"
        job.closed_at = datetime.utcnow()
        db.commit()
        
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
        db.rollback()
        logger.error(f"Error closing job: {e}")
        raise HTTPException(status_code=500, detail=f"Error closing job: {str(e)}")


# ============================================================================
# SUPPLIER STATE & EMAIL ENDPOINTS
# ============================================================================

@app.get("/api/jobs/{job_id}/suppliers", response_model=List[SupplierStateResponse])
def get_job_suppliers(job_id: int, db: Session = Depends(get_db)):
    """Get all suppliers for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    suppliers = db.query(JobSupplierState).filter(JobSupplierState.job_id == job_id).all()
    return suppliers


@app.get("/api/suppliers/{supplier_id}/emails", response_model=List[EmailResponse])
def get_supplier_emails(supplier_id: int, db: Session = Depends(get_db)):
    """Get all emails for a specific supplier state."""
    supplier = db.query(JobSupplierState).filter(JobSupplierState.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier state not found")
    
    emails = db.query(SupplierEmail).filter(SupplierEmail.supplier_state_id == supplier_id).order_by(SupplierEmail.sent_at.desc()).all()
    return emails


@app.post("/api/jobs/{job_id}/suppliers/{supplier_id}/send-reminder")
def send_reminder(job_id: int, supplier_id: int, db: Session = Depends(get_db)):
    """Send a reminder email to a supplier."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        supplier = db.query(JobSupplierState).filter(
            JobSupplierState.id == supplier_id,
            JobSupplierState.job_id == job_id
        ).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found for this job")
        
        # Send reminder email
        success = send_reminder_email(
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
            db.commit()
            
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
        db.rollback()
        logger.error(f"Error sending reminder: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending reminder: {str(e)}")


# ============================================================================
# INSIGHTS ENDPOINTS
# ============================================================================

@app.get("/api/jobs/{job_id}/insights", response_model=List[InsightResponse])
def get_job_insights(job_id: int, db: Session = Depends(get_db)):
    """Get all insights for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    insights = db.query(Insight).filter(Insight.job_id == job_id).order_by(Insight.extracted_at.desc()).all()
    return insights


@app.get("/api/insights/by-supplier", response_model=dict)
def get_insights_by_supplier(db: Session = Depends(get_db)):
    """Get all insights grouped by supplier."""
    insights = db.query(Insight).all()
    
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
def get_summary_stats(db: Session = Depends(get_db)):
    """Get overall statistics about jobs and responses."""
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == "active").count()
    closed_jobs = db.query(Job).filter(Job.status == "closed").count()
    
    total_suppliers = db.query(JobSupplierState).count()
    responded_suppliers = db.query(JobSupplierState).filter(JobSupplierState.replied == True).count()
    
    total_insights = db.query(Insight).count()
    
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
def get_job_stats(job_id: int, db: Session = Depends(get_db)):
    """Get statistics for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    total_suppliers = db.query(JobSupplierState).filter(JobSupplierState.job_id == job_id).count()
    responded = db.query(JobSupplierState).filter(
        JobSupplierState.job_id == job_id,
        JobSupplierState.replied == True
    ).count()
    insights = db.query(Insight).filter(Insight.job_id == job_id).count()
    
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
