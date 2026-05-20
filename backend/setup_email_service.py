"""
Alternative schema setup using SQLAlchemy async engine.
This approach works better with Cloud SQL Proxy or when IP whitelisting is configured.
"""
import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set DATABASE_URL BEFORE importing database module
host = os.environ.get("CLOUD_SQL_HOST", "35.200.192.16")
port = os.environ.get("CLOUD_SQL_PORT", "5432")
user = os.environ.get("CLOUD_SQL_USER", "postgres")
password = os.environ.get("CLOUD_SQL_PASSWORD")
database = os.environ.get("CLOUD_SQL_DATABASE", "inventory")

if not password:
    print("❌ CLOUD_SQL_PASSWORD environment variable not set")
    sys.exit(1)

# For asyncpg with SSL, use different parameter format
db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
os.environ["DATABASE_URL"] = db_url

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

# Create engine and Base with environment-based DATABASE_URL
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args={"ssl": True},  # Enable SSL for Cloud SQL
)

Base = declarative_base()

# Import models after Base is defined
from backend.database import Job, JobSupplierState, SupplierEmail, Insight

async def create_schema_and_tables():
    """Create the email_service schema and all tables using SQLAlchemy."""
    
    print("=" * 70)
    print("CREATING EMAIL_SERVICE SCHEMA AND TABLES")
    print("=" * 70)
    print(f"\n📍 Target Database: postgresql+asyncpg://...@{host}:{port}/{database}")
    
    try:
        async with engine.begin() as conn:
            # Create schema
            print("\n1️⃣  Creating schema: email_service...")
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS email_service;"))
            print("   ✅ Schema created")
            
            # Create all tables from Base metadata
            print("\n2️⃣  Creating tables from SQLAlchemy models...")
            await conn.run_sync(Base.metadata.create_all)
            print("   ✅ All tables created")
            
            # Create indexes
            print("\n3️⃣  Creating indexes for performance...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON email_service.jobs(status);",
                "CREATE INDEX IF NOT EXISTS idx_jobs_user_email ON email_service.jobs(user_email);",
                "CREATE INDEX IF NOT EXISTS idx_job_supplier_states_job_id ON email_service.job_supplier_states(job_id);",
                "CREATE INDEX IF NOT EXISTS idx_supplier_emails_job_id ON email_service.supplier_emails(job_id);",
                "CREATE INDEX IF NOT EXISTS idx_supplier_emails_sent_at ON email_service.supplier_emails(sent_at);",
                "CREATE INDEX IF NOT EXISTS idx_insights_job_id ON email_service.insights(job_id);",
                "CREATE INDEX IF NOT EXISTS idx_insights_supplier ON email_service.insights(supplier);",
            ]
            for idx_sql in indexes:
                await conn.execute(text(idx_sql))
            print("   ✅ Indexes created")
            
            # Verify tables
            print("\n4️⃣  Verifying tables...")
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'email_service'
                ORDER BY table_name;
            """))
            tables = result.fetchall()
            if tables:
                print(f"   ✅ Found {len(tables)} tables in email_service schema:")
                for table in tables:
                    print(f"      - {table[0]}")
            else:
                print("   ⚠️  No tables found (schema may need to be created separately)")
        
        print("\n" + "=" * 70)
        print("✅ SCHEMA AND TABLES CREATED SUCCESSFULLY!")
        print("=" * 70)
        print("\nSchema Structure:")
        print("  📦 email_service")
        print("    ├── jobs")
        print("    ├── job_supplier_states")
        print("    ├── supplier_emails")
        print("    └── insights")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print(f"📝 Using DATABASE_URL: postgresql+asyncpg://{user}:***@{host}:{port}/{database}\n")
    print("🔌 Connecting to Cloud SQL...\n")
    asyncio.run(create_schema_and_tables())
