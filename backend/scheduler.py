from apscheduler.schedulers.background import BackgroundScheduler
import logging
from backend.database import SessionLocal, Job
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.gcs_utils import upload_job_summary

logger = logging.getLogger(__name__)

def process_active_jobs():
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
            
            if time_since_creation > timedelta(minutes=4):
                logger.info(f"Job {job.id} has reached T+48h (mock 4m). Closing job and archiving to GCS.")
                job.status = "closed"
                
                # Mock archival
                summary = {
                    "chemical_query": job.chemical_query,
                    "created_at": job.created_at.isoformat(),
                    "closed_at": now.isoformat()
                }
                # Upload to GCS
                upload_job_summary(job.id, summary, [])
                
            elif time_since_creation > timedelta(minutes=2) and not job.reminders_sent:
                logger.info(f"Job {job.id} has reached T+24h (mock 2m). Sending reminders...")
                # Logic to identify non-replied suppliers and send reminders would go here
                job.reminders_sent = True
                
        db.commit()
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    # Check every minute
    scheduler.add_job(process_active_jobs, 'interval', minutes=1)
    scheduler.start()
    logger.info("Background scheduler started")
