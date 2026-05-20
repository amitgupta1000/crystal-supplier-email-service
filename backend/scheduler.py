from apscheduler.schedulers.background import BackgroundScheduler
import logging
import asyncio
from sqlalchemy import select
from backend.database import AsyncSessionLocal, Job, JobSupplierState, Insight, SupplierEmail
from datetime import datetime, timedelta
from backend.gcs_utils import upload_job_summary
from backend.email_utils import send_reminder_email
from backend.notification_service import send_summary_notification, send_closure_notification

logger = logging.getLogger(__name__)

async def process_active_jobs_async():
    """Async function to process active jobs: send summaries, reminders, and close stale jobs."""
    logger.info("Running scheduled task to process active jobs...")
    async with AsyncSessionLocal() as db:
        try:
            # Query all active jobs
            result = await db.execute(select(Job).where(Job.status == "active"))
            active_jobs = result.scalars().all()
            now = datetime.utcnow()
            
            for job in active_jobs:
                # Using very short intervals for development testing:
                # Summaries every 12h (mock 1m), Reminders at T+24h (mock 2m), close at T+48h (mock 4m)
                # In production this would be hours (12, 24, 48)
                time_since_creation = now - job.created_at
                
                # Check if job should be closed (T+48h or mock 4 minutes)
                if time_since_creation > timedelta(minutes=4):
                    if not job.closure_notification_sent:
                        logger.info(f"Job {job.id} has reached T+48h (mock 4m). Sending closure report...")
                        
                        # Get all job details
                        suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                        suppliers = suppliers_result.scalars().all()
                        
                        insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                        insights = insights_result.scalars().all()
                        
                        emails_result = await db.execute(select(SupplierEmail).where(SupplierEmail.job_id == job.id))
                        emails = emails_result.scalars().all()
                        
                        # Send closure notification
                        await send_closure_notification(job, suppliers, insights, emails)
                        job.closure_notification_sent = True
                    
                    # Close the job
                    logger.info(f"Job {job.id} - Closing job and archiving to GCS.")
                    job.status = "closed"
                    job.closed_at = now
                    
                    # Get job details for archival
                    suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                    suppliers = suppliers_result.scalars().all()
                    
                    insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                    insights = insights_result.scalars().all()
                    
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
                    
                # Check if 12-hour summary should be sent (every 12h or mock every 1m)
                elif time_since_creation > timedelta(minutes=1):
                    if not job.last_summary_sent_at or (now - job.last_summary_sent_at) >= timedelta(minutes=1):
                        logger.info(f"Job {job.id} - Sending 12-hour summary report...")
                        
                        suppliers_result = await db.execute(select(JobSupplierState).where(JobSupplierState.job_id == job.id))
                        suppliers = suppliers_result.scalars().all()
                        
                        # Count new insights since last summary
                        if job.last_summary_sent_at:
                            new_insights_result = await db.execute(
                                select(Insight).where(
                                    Insight.job_id == job.id,
                                    Insight.extracted_at > job.last_summary_sent_at
                                )
                            )
                            new_insights_count = len(new_insights_result.scalars().all())
                        else:
                            new_insights_result = await db.execute(select(Insight).where(Insight.job_id == job.id))
                            new_insights_count = len(new_insights_result.scalars().all())
                        
                        # Send summary only if there are new updates
                        if new_insights_count > 0 or not job.last_summary_sent_at:
                            await send_summary_notification(job, suppliers, new_insights_count)
                            job.last_summary_sent_at = now
                
                # Check if reminders should be sent (T+24h or mock 2 minutes)
                elif time_since_creation > timedelta(minutes=2) and not job.reminders_sent:
                    logger.info(f"Job {job.id} has reached T+24h (mock 2m). Sending reminders...")
                    
                    # Get suppliers who haven't replied
                    suppliers_result = await db.execute(select(JobSupplierState).where(
                        JobSupplierState.job_id == job.id,
                        JobSupplierState.replied == False
                    ))
                    suppliers = suppliers_result.scalars().all()
                    
                    for supplier in suppliers:
                        try:
                            success = await send_reminder_email(
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
            
            await db.commit()
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")


def process_active_jobs():
    """Sync wrapper for the async process_active_jobs_async function."""
    asyncio.run(process_active_jobs_async())


def start_scheduler():
    """Start the background job scheduler."""
    scheduler = BackgroundScheduler()
    # Check every minute
    scheduler.add_job(process_active_jobs, 'interval', minutes=1)
    scheduler.start()
    logger.info("Background scheduler started")
