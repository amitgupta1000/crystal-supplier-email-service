import os
import logging
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

logger = logging.getLogger(__name__)

# SSL certificates configured in main.py - reuse environment variables
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

_connectors_by_loop = {}

def get_connector():
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    global _connectors_by_loop
    if loop not in _connectors_by_loop:
        from google.cloud.sql.connector import Connector
        _connectors_by_loop[loop] = Connector(loop=loop)
    return _connectors_by_loop[loop]

async def close_connector():
    global _connectors_by_loop
    for loop, connector in list(_connectors_by_loop.items()):
        try:
            await connector.close_async()
        except Exception:
            pass
    _connectors_by_loop.clear()

async def _getconn():
    connector = get_connector()
    connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME", "gen-lang-client-0665888431:asia-south1:crystal-inventory-dash")
    user = os.environ.get("CLOUD_SQL_USER", "postgres")
    password = os.environ.get("CLOUD_SQL_PASSWORD")
    database = os.environ.get("CLOUD_SQL_DATABASE", "inventory")
    if not password:
        raise ValueError("CLOUD_SQL_PASSWORD environment variable is required")
    return await connector.connect_async(
        connection_name,
        "asyncpg",
        user=user,
        password=password,
        db=database,
    )

if USE_SQLITE:
    DATABASE_URL = "sqlite+aiosqlite:///./jobs.db"
    logger.info("📊 Using SQLite database: ./jobs.db")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )
    
    scheduler_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=False,
        poolclass=None,
    )
else:
    password = os.environ.get("CLOUD_SQL_PASSWORD")
    if not password:
        raise ValueError("CLOUD_SQL_PASSWORD environment variable is required")
    
    logger.info("📊 Using Cloud SQL with Python Connector")
    
    engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=_getconn,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args={"server_settings": {"application_name": "crystal-email-service"}},
    )
    
    scheduler_engine = create_async_engine(
        "postgresql+asyncpg://",
        async_creator=_getconn,
        echo=False,
        future=True,
        pool_pre_ping=False,
        poolclass=None,
        connect_args={"server_settings": {"application_name": "crystal-email-service-scheduler"}},
    )

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

SchedulerAsyncSessionLocal = async_sessionmaker(
    scheduler_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

logger.info("✅ Database initialized")

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    chemical_query = Column(String, index=True)
    user_email = Column(String)  # Email for notifications
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active") # active, closed
    reminders_sent = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    total_responses = Column(Integer, default=0)
    last_summary_sent_at = Column(DateTime, nullable=True)  # For 12-hour summaries
    closure_notification_sent = Column(Boolean, default=False)  # Track closure report
    
    suppliers = relationship("JobSupplierState", back_populates="job", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="job", cascade="all, delete-orphan")
    emails = relationship("SupplierEmail", back_populates="job", cascade="all, delete-orphan")

class JobSupplierState(Base):
    __tablename__ = "job_supplier_states"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    company_name = Column(String)
    email_id = Column(String, index=True)
    domain = Column(String)
    initial_email_sent_at = Column(DateTime, default=datetime.utcnow)
    replied = Column(Boolean, default=False)
    reply_received_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    job = relationship("Job", back_populates="suppliers")
    emails = relationship("SupplierEmail", back_populates="supplier_state", cascade="all, delete-orphan")

class SupplierEmail(Base):
    __tablename__ = "supplier_emails"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    supplier_state_id = Column(Integer, ForeignKey("job_supplier_states.id" if USE_SQLITE else "email_service.job_supplier_states.id"), nullable=True)
    email_type = Column(String)  # "outbound" or "inbound"
    from_email = Column(String)
    to_email = Column(String)
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    gmail_message_id = Column(String, nullable=True, unique=True)
    
    job = relationship("Job", back_populates="emails")
    supplier_state = relationship("JobSupplierState", back_populates="emails")

class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    supplier = Column(String, index=True)
    contact_person = Column(String, nullable=True)
    product = Column(String, nullable=True)
    quantity = Column(String, nullable=True)
    price = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)
    email_body = Column(Text, nullable=True)  # Complete email for drilldowns
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="insights")
