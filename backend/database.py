import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./jobs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    chemical_query = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active") # active, closed
    reminders_sent = Column(Boolean, default=False)
    
    suppliers = relationship("JobSupplierState", back_populates="job")
    insights = relationship("Insight", back_populates="job")

class JobSupplierState(Base):
    __tablename__ = "job_supplier_states"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    company_name = Column(String)
    email_id = Column(String)
    domain = Column(String)
    initial_email_sent_at = Column(DateTime, default=datetime.utcnow)
    replied = Column(Boolean, default=False)
    
    job = relationship("Job", back_populates="suppliers")

class Insight(Base):
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    supplier = Column(String)
    contact_person = Column(String)
    product = Column(String)
    quantity = Column(String)
    price = Column(String)
    delivery_date = Column(String)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="insights")

Base.metadata.create_all(bind=engine)
