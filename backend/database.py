import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./jobs.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    chemical_query = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active") # active, closed
    reminders_sent = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    total_responses = Column(Integer, default=0)
    
    suppliers = relationship("JobSupplierState", back_populates="job", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="job", cascade="all, delete-orphan")
    emails = relationship("SupplierEmail", back_populates="job", cascade="all, delete-orphan")

class JobSupplierState(Base):
    __tablename__ = "job_supplier_states"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
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
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    supplier_state_id = Column(Integer, ForeignKey("job_supplier_states.id"), nullable=True)
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
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    supplier = Column(String, index=True)
    contact_person = Column(String, nullable=True)
    product = Column(String, nullable=True)
    quantity = Column(String, nullable=True)
    price = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="insights")
