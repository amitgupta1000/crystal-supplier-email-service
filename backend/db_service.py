"""
Database service for email_service schema.
Provides async CRUD operations for jobs and insights.
"""
import os
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import Job, Insight, JobSupplierState, SupplierEmail, AsyncSessionLocal

class JobService:
    """Service for managing jobs with async operations."""
    
    @staticmethod
    async def create_job(
        chemical_query: str,
        user_email: str,
        session: AsyncSession
    ) -> Job:
        """Create a new job."""
        job = Job(
            chemical_query=chemical_query,
            user_email=user_email,
            created_at=datetime.utcnow(),
            status="active"
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job
    
    @staticmethod
    async def get_job(job_id: int, session: AsyncSession) -> Optional[Job]:
        """Get a job by ID."""
        result = await session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_jobs_by_user(user_email: str, session: AsyncSession) -> List[Job]:
        """Get all jobs for a user."""
        result = await session.execute(
            select(Job).where(Job.user_email == user_email).order_by(Job.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_active_jobs(session: AsyncSession) -> List[Job]:
        """Get all active jobs."""
        result = await session.execute(
            select(Job).where(Job.status == "active")
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_job_status(
        job_id: int,
        status: str,
        session: AsyncSession
    ) -> Optional[Job]:
        """Update job status (active, closed, etc.)."""
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await session.commit()
        return await JobService.get_job(job_id, session)
    
    @staticmethod
    async def update_job_responses(
        job_id: int,
        total_responses: int,
        session: AsyncSession
    ) -> Optional[Job]:
        """Update total responses count."""
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(total_responses=total_responses, updated_at=datetime.utcnow())
        )
        await session.commit()
        return await JobService.get_job(job_id, session)
    
    @staticmethod
    async def mark_reminders_sent(job_id: int, session: AsyncSession) -> Optional[Job]:
        """Mark reminders as sent for a job."""
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(reminders_sent=True, updated_at=datetime.utcnow())
        )
        await session.commit()
        return await JobService.get_job(job_id, session)
    
    @staticmethod
    async def close_job(job_id: int, session: AsyncSession) -> Optional[Job]:
        """Close a job."""
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status="closed",
                closed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )
        await session.commit()
        return await JobService.get_job(job_id, session)


class InsightService:
    """Service for managing insights with async operations."""
    
    @staticmethod
    async def create_insight(
        job_id: int,
        supplier: str,
        contact_person: Optional[str],
        product: Optional[str],
        quantity: Optional[str],
        price: Optional[float],
        delivery_date: Optional[str],
        email_body: Optional[str],
        session: AsyncSession
    ) -> Insight:
        """Create a new insight from extracted supplier data."""
        insight = Insight(
            job_id=job_id,
            supplier=supplier,
            contact_person=contact_person,
            product=product,
            quantity=quantity,
            price=price,
            delivery_date=delivery_date,
            email_body=email_body,
            extracted_at=datetime.utcnow()
        )
        session.add(insight)
        await session.commit()
        await session.refresh(insight)
        return insight
    
    @staticmethod
    async def get_insight(insight_id: int, session: AsyncSession) -> Optional[Insight]:
        """Get an insight by ID."""
        result = await session.execute(
            select(Insight).where(Insight.id == insight_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_insights_by_job(job_id: int, session: AsyncSession) -> List[Insight]:
        """Get all insights for a job."""
        result = await session.execute(
            select(Insight).where(Insight.job_id == job_id).order_by(Insight.extracted_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_insights_by_supplier(
        job_id: int,
        supplier: str,
        session: AsyncSession
    ) -> List[Insight]:
        """Get all insights from a specific supplier for a job."""
        result = await session.execute(
            select(Insight).where(
                and_(
                    Insight.job_id == job_id,
                    Insight.supplier == supplier
                )
            ).order_by(Insight.extracted_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def count_insights_by_job(job_id: int, session: AsyncSession) -> int:
        """Count insights for a job."""
        result = await session.execute(
            select(Insight).where(Insight.job_id == job_id)
        )
        return len(result.scalars().all())
    
    @staticmethod
    async def get_latest_insights(limit: int = 10, session: AsyncSession = None) -> List[Insight]:
        """Get the latest insights across all jobs."""
        if session is None:
            session = AsyncSessionLocal()
        
        result = await session.execute(
            select(Insight).order_by(Insight.extracted_at.desc()).limit(limit)
        )
        return result.scalars().all()


class SupplierStateService:
    """Service for managing supplier states."""
    
    @staticmethod
    async def create_supplier_state(
        job_id: int,
        company_name: str,
        email_id: str,
        domain: str,
        session: AsyncSession
    ) -> JobSupplierState:
        """Create a new supplier state for a job."""
        supplier_state = JobSupplierState(
            job_id=job_id,
            company_name=company_name,
            email_id=email_id,
            domain=domain,
            initial_email_sent_at=datetime.utcnow()
        )
        session.add(supplier_state)
        await session.commit()
        await session.refresh(supplier_state)
        return supplier_state
    
    @staticmethod
    async def mark_replied(supplier_state_id: int, session: AsyncSession) -> Optional[JobSupplierState]:
        """Mark a supplier as replied."""
        await session.execute(
            update(JobSupplierState)
            .where(JobSupplierState.id == supplier_state_id)
            .values(replied=True, reply_received_at=datetime.utcnow())
        )
        await session.commit()
        result = await session.execute(
            select(JobSupplierState).where(JobSupplierState.id == supplier_state_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def mark_reminder_sent(supplier_state_id: int, session: AsyncSession) -> Optional[JobSupplierState]:
        """Mark a reminder as sent for a supplier."""
        await session.execute(
            update(JobSupplierState)
            .where(JobSupplierState.id == supplier_state_id)
            .values(reminder_sent_at=datetime.utcnow())
        )
        await session.commit()
        result = await session.execute(
            select(JobSupplierState).where(JobSupplierState.id == supplier_state_id)
        )
        return result.scalar_one_or_none()


class EmailService:
    """Service for managing emails."""
    
    @staticmethod
    async def create_email(
        job_id: int,
        email_type: str,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        gmail_message_id: Optional[str] = None,
        supplier_state_id: Optional[int] = None,
        session: AsyncSession = None
    ) -> SupplierEmail:
        """Create a new email record."""
        if session is None:
            session = AsyncSessionLocal()
        
        email = SupplierEmail(
            job_id=job_id,
            supplier_state_id=supplier_state_id,
            email_type=email_type,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            gmail_message_id=gmail_message_id,
            sent_at=datetime.utcnow()
        )
        session.add(email)
        await session.commit()
        await session.refresh(email)
        return email
    
    @staticmethod
    async def get_emails_by_job(job_id: int, session: AsyncSession) -> List[SupplierEmail]:
        """Get all emails for a job."""
        result = await session.execute(
            select(SupplierEmail).where(SupplierEmail.job_id == job_id).order_by(SupplierEmail.sent_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_email_by_gmail_id(gmail_message_id: str, session: AsyncSession) -> Optional[SupplierEmail]:
        """Get an email by Gmail message ID."""
        result = await session.execute(
            select(SupplierEmail).where(SupplierEmail.gmail_message_id == gmail_message_id)
        )
        return result.scalar_one_or_none()


async def get_session() -> AsyncSession:
    """Dependency for FastAPI to get async session."""
    async with AsyncSessionLocal() as session:
        yield session
