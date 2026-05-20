from apscheduler.schedulers.background import BackgroundScheduler
import logging
from backend.database import SessionLocal, Job, JobSupplierState
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.gcs_utils import upload_job_summary
from backend.email_utils import send_reminder_email

logger = logging.getLogger(__name__)

def process_active_jobs():
    """Process active jobs: send reminders and close stale jobs."""
    logger.info("Running scheduled task to process active jobs...")
    db: Session = SessionLocal()
    try:
        active_jobs = db.query(Job).filter(Job.status == "active").all()
        now = datetime.utcnow()
        
        for job in active_jobs:
            # Using very short intervals for development testing:
            # Reminders at 2 minutes, close at 4 minutes
            # In production this would be hours (24, 48)
            time_since_creation = now - job.created_at
            
            # Check if job should be closed (T+48h or mock 4 minutes)
            if time_since_creation > timedelta(minutes=4):
                logger.info(f"Job {job.id} has reached T+48h (mock 4m). Closing job and archiving to GCS.")
                job.status = "closed"
                job.closed_at = now
                
                # Get job details for archival
                suppliers = db.query(JobSupplierState).filter(JobSupplierState.job_id == job.id).all()
                from backend.database import Insight
                insights = db.query(Insight).filter(Insight.job_id == job.id).all()
                
                # Prepare summary
                summary = {
                    "job_id": job.id,
                    "chemical_query": job.chemical_query,
                    "created_at": job.created_at.isoformat(),
                    "closed_at": now.isoformat(),
                    "status": "closed",
                    "total_suppliers": len(suppliers),
                    "responded_suppliers": sum(1 for s in suppliers if s.replied),
                    "insights_extracted": len(insights)
                }
                
                # Format insights for CSV
                insights_list = [
                    {
                        "Supplier": i.supplier,
                        "Contact_Person": i.contact_person or "",
                        "Product": i.product or "",
                        "Quantity": i.quantity or "",
                        "Price": i.price or "",
                        "Delivery_Date": i.delivery_date or ""
                    }
                    for i in insights
                ]
                
                # Upload to GCS
                upload_job_summary(job.id, summary, insights_list)
                
            # Check if reminders should be sent (T+24h or mock 2 minutes)
            elif time_since_creation > timedelta(minutes=2) and not job.reminders_sent:
                logger.info(f"Job {job.id} has reached T+24h (mock 2m). Sending reminders...")
                
                # Get suppliers who haven't replied
                suppliers = db.query(JobSupplierState).filter(
                    JobSupplierState.job_id == job.id,
                    JobSupplierState.replied == False
                ).all()
                
                for supplier in suppliers:
                    try:
                        success = send_reminder_email(
                            supplier.email_id,
                            supplier.company_name,
                            job.chemical_query
                        )
                        if success:
                            supplier.reminder_sent_at = now
                            logger.info(f"Sent reminder to {supplier.email_id}")
                    except Exception as e:
                        logger.error(f"Error sending reminder to {supplier.email_id}: {e}")
                
                job.reminders_sent = True
                
        db.commit()
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")
    finally:
        db.close()

def start_scheduler():
    """Start the background job scheduler."""
    scheduler = BackgroundScheduler()
    # Check every minute
    scheduler.add_job(process_active_jobs, 'interval', minutes=1)
    scheduler.start()
    logger.info("Background scheduler started")
