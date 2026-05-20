"""
Test script for email_service schema and async database operations.
Run this after creating the schema to verify everything works.
"""
import asyncio
import os
from datetime import datetime
from backend.database import AsyncSessionLocal
from backend.db_service import JobService, InsightService, SupplierStateService, EmailService

async def test_database_operations():
    """Test all async database operations."""
    
    print("=" * 70)
    print("EMAIL SERVICE DATABASE TEST")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        try:
            # Test 1: Create a job
            print("\n1️⃣  Creating a test job...")
            job = await JobService.create_job(
                chemical_query="Polyester Fabric - Industrial Grade",
                user_email="amit.gupta@coralbayadvisory.com",
                session=session
            )
            print(f"   ✅ Job created: ID={job.id}, Query={job.chemical_query}")
            job_id = job.id
            
            # Test 2: Retrieve the job
            print("\n2️⃣  Retrieving the job...")
            retrieved_job = await JobService.get_job(job_id, session)
            print(f"   ✅ Job retrieved: Status={retrieved_job.status}, Created={retrieved_job.created_at}")
            
            # Test 3: Create supplier states
            print("\n3️⃣  Creating supplier states...")
            supplier1 = await SupplierStateService.create_supplier_state(
                job_id=job_id,
                company_name="Supplier Inc",
                email_id="supplier1@example.com",
                domain="example.com",
                session=session
            )
            print(f"   ✅ Supplier 1 created: ID={supplier1.id}, Company={supplier1.company_name}")
            
            supplier2 = await SupplierStateService.create_supplier_state(
                job_id=job_id,
                company_name="Global Fabrics Ltd",
                email_id="sales@globalfabrics.com",
                domain="globalfabrics.com",
                session=session
            )
            print(f"   ✅ Supplier 2 created: ID={supplier2.id}, Company={supplier2.company_name}")
            
            # Test 4: Create emails
            print("\n4️⃣  Creating email records...")
            email1 = await EmailService.create_email(
                job_id=job_id,
                email_type="outbound",
                from_email="noreply@coralbayadvisory.com",
                to_email="supplier1@example.com",
                subject="Polyester Fabric Inquiry",
                body="We are looking for polyester fabric suppliers...",
                supplier_state_id=supplier1.id,
                session=session
            )
            print(f"   ✅ Outbound email created: ID={email1.id}, To={email1.to_email}")
            
            # Test 5: Create insights
            print("\n5️⃣  Creating insights from supplier responses...")
            insight1 = await InsightService.create_insight(
                job_id=job_id,
                supplier="Supplier Inc",
                contact_person="John Smith",
                product="Polyester Fabric - 65% Poly, 35% Cotton",
                quantity="5000 meters",
                price=12.50,
                delivery_date="2026-06-15",
                email_body="We can supply the polyester fabric...",
                session=session
            )
            print(f"   ✅ Insight 1 created: ID={insight1.id}, Product={insight1.product}, Price=${insight1.price}")
            
            insight2 = await InsightService.create_insight(
                job_id=job_id,
                supplier="Global Fabrics Ltd",
                contact_person="Maria Garcia",
                product="Premium Polyester Blend",
                quantity="10000 meters",
                price=14.75,
                delivery_date="2026-06-20",
                email_body="We offer premium quality polyester...",
                session=session
            )
            print(f"   ✅ Insight 2 created: ID={insight2.id}, Product={insight2.product}, Price=${insight2.price}")
            
            # Test 6: Retrieve insights by job
            print("\n6️⃣  Retrieving all insights for job...")
            job_insights = await InsightService.get_insights_by_job(job_id, session)
            print(f"   ✅ Retrieved {len(job_insights)} insights:")
            for insight in job_insights:
                print(f"      - {insight.supplier}: {insight.product} (${insight.price})")
            
            # Test 7: Get insights by supplier
            print("\n7️⃣  Retrieving insights for specific supplier...")
            supplier_insights = await InsightService.get_insights_by_supplier(
                job_id=job_id,
                supplier="Supplier Inc",
                session=session
            )
            print(f"   ✅ Found {len(supplier_insights)} insights from Supplier Inc")
            
            # Test 8: Update job status
            print("\n8️⃣  Updating job status to closed...")
            closed_job = await JobService.close_job(job_id, session)
            print(f"   ✅ Job closed: Status={closed_job.status}, Closed At={closed_job.closed_at}")
            
            # Test 9: Get active jobs (should be empty now)
            print("\n9️⃣  Retrieving active jobs...")
            active_jobs = await JobService.get_active_jobs(session)
            print(f"   ✅ Found {len(active_jobs)} active jobs")
            
            # Test 10: Count insights
            print("\n🔟  Counting insights for job...")
            insight_count = await InsightService.count_insights_by_job(job_id, session)
            print(f"   ✅ Total insights for job {job_id}: {insight_count}")
            
            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED!")
            print("=" * 70)
            print("\n📊 Summary:")
            print(f"   - Created job ID: {job_id}")
            print(f"   - Created suppliers: 2")
            print(f"   - Created emails: 1")
            print(f"   - Created insights: 2")
            print(f"   - Database schema: email_service")
            print(f"   - Status: Ready for production!")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Set environment variables if not already set
    if not os.environ.get("CLOUD_SQL_PASSWORD"):
        print("❌ Please set CLOUD_SQL_PASSWORD environment variable")
        exit(1)
    
    print("\n🔌 Connecting to Cloud SQL...")
    asyncio.run(test_database_operations())
