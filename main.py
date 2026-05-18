import csv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import logging

from backend.database import SessionLocal, Job, JobSupplierState
from backend.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn
from typing import List, Dict, Any

@asynccontextmanager
async def lifespan(app:FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="EMAIL SERVICE API",lifespan=lifespan)

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



@app.get("/api/suppliers")
def get_suppliers():
    suppliers = []
    try:
        with open("suppliers.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                suppliers.append({
                    "company_name": row.get("Company Name"),
                    "email_id": row.get("Email ID"),
                    "domain": row.get("Email ID").split("@")[-1] if row.get("Email ID") else "",
                    "salutation": row.get("Salutation 1", "Hello")
                })
    except FileNotFoundError:
        logger.error("suppliers.csv not found")
    return suppliers

class StartJobRequest(BaseModel):
    chemical_query: str
    supplier_emails: List[str]

@app.post("/api/jobs/start")
def start_job(request: StartJobRequest, db: Session = Depends(get_db)):
    # Create job in db
    new_job = Job(chemical_query=request.chemical_query)
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Record targeted suppliers
    for email in request.supplier_emails:
        state = JobSupplierState(
            job_id=new_job.id,
            email_id=email,
            domain=email.split("@")[-1] if email else "",
        )
        db.add(state)
    db.commit()
    
    # In a full implementation, this would call email_utils to send initial emails.
    logger.info(f"Started job {new_job.id} for {len(request.supplier_emails)} suppliers")
    return {"message": "Job started successfully", "job_id": new_job.id}

@app.post("/api/jobs/{job_id}/insights/refresh")
def refresh_insights(job_id: int, db: Session = Depends(get_db)):
    # Placeholder for invoking extract_insights.py logic
    logger.info(f"Refreshing insights for job {job_id}")
    
    # Return mock data for now
    return {
        "message": "Insights refreshed",
        "new_insights": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
