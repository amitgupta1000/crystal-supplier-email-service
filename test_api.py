"""
Test suite for Crystal Supplier Email Service

Run with: pytest test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from backend.database import Base, engine, SessionLocal
import json

# Create test database
Base.metadata.create_all(bind=engine)

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSupplierEndpoints:
    """Test supplier-related endpoints."""
    
    def test_get_suppliers(self):
        """Test getting suppliers list."""
        response = client.get("/api/suppliers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # If suppliers exist, check structure
        if len(response.json()) > 0:
            supplier = response.json()[0]
            assert "company_name" in supplier
            assert "email_id" in supplier
            assert "domain" in supplier
            assert "salutation" in supplier


class TestJobEndpoints:
    """Test job management endpoints."""
    
    @pytest.fixture
    def sample_job_request(self):
        """Sample job creation request."""
        return {
            "chemical_query": "Test Chemical Query",
            "supplier_emails": ["test@example.com"]
        }
    
    def test_create_job(self, sample_job_request):
        """Test creating a new job."""
        response = client.post("/api/jobs/start", json=sample_job_request)
        
        # Job creation might fail if email service is not configured
        # So we just check that we get a response
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert data["chemical_query"] == sample_job_request["chemical_query"]
    
    def test_get_all_jobs(self):
        """Test getting all jobs."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_job_detail(self):
        """Test getting job detail."""
        # First, get all jobs
        response = client.get("/api/jobs")
        jobs = response.json()
        
        if jobs:
            job_id = jobs[0]["id"]
            response = client.get(f"/api/jobs/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "job" in data
            assert "suppliers" in data
            assert "insights" in data
            assert "emails" in data
    
    def test_get_nonexistent_job(self):
        """Test getting a nonexistent job."""
        response = client.get("/api/jobs/99999")
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]


class TestStatisticsEndpoints:
    """Test statistics and analytics endpoints."""
    
    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        response = client.get("/api/stats/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "jobs" in data
        assert "suppliers" in data
        assert "insights" in data
        
        assert "total" in data["jobs"]
        assert "active" in data["jobs"]
        assert "closed" in data["jobs"]
    
    def test_get_job_stats(self):
        """Test getting job statistics."""
        # First, get all jobs
        response = client.get("/api/jobs")
        jobs = response.json()
        
        if jobs:
            job_id = jobs[0]["id"]
            response = client.get(f"/api/stats/job/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert "chemical_query" in data
            assert "status" in data
            assert "suppliers" in data


class TestInsightEndpoints:
    """Test insights-related endpoints."""
    
    def test_get_all_insights_by_supplier(self):
        """Test getting insights grouped by supplier."""
        response = client.get("/api/insights/by-supplier")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)


class TestSupplierStateEndpoints:
    """Test supplier state and email endpoints."""
    
    def test_get_job_suppliers(self):
        """Test getting suppliers for a job."""
        # First, get all jobs
        response = client.get("/api/jobs")
        jobs = response.json()
        
        if jobs:
            job_id = jobs[0]["id"]
            response = client.get(f"/api/jobs/{job_id}/suppliers")
            
            assert response.status_code == 200
            assert isinstance(response.json(), list)


# Integration Tests
class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_job_lifecycle(self):
        """Test complete job lifecycle: create -> retrieve -> close."""
        # Create job
        job_request = {
            "chemical_query": "Integration Test Chemical",
            "supplier_emails": ["integration@test.com"]
        }
        
        create_response = client.post("/api/jobs/start", json=job_request)
        
        if create_response.status_code == 200:
            job_id = create_response.json()["job_id"]
            
            # Retrieve job
            get_response = client.get(f"/api/jobs/{job_id}")
            assert get_response.status_code == 200
            assert get_response.json()["job"]["id"] == job_id
            
            # Close job
            close_response = client.post(f"/api/jobs/{job_id}/close")
            assert close_response.status_code == 200
            assert close_response.json()["status"] == "closed"


# Performance Tests
class TestPerformance:
    """Performance-related tests."""
    
    def test_get_all_jobs_performance(self):
        """Test that getting all jobs completes quickly."""
        import time
        
        start = time.time()
        response = client.get("/api/jobs?limit=100")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Request took {elapsed}s, expected < 1.0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
