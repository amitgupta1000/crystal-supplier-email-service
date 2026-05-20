"""
Create the email_service schema and tables in Cloud SQL.
Run once to initialize the email service database.
"""
import os
import psycopg2
from psycopg2 import sql

def create_schema_and_tables():
    # Get connection details from environment
    host = os.environ.get("CLOUD_SQL_HOST", "35.200.192.16")
    port = int(os.environ.get("CLOUD_SQL_PORT", "5432"))
    user = os.environ.get("CLOUD_SQL_USER", "postgres")
    password = os.environ.get("CLOUD_SQL_PASSWORD", "")
    
    if not password:
        raise ValueError("CLOUD_SQL_PASSWORD environment variable not set")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="postgres",
        sslmode="require"
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # Create the email_service schema
        print("Creating schema: email_service...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS email_service;")
        
        # Create jobs table
        print("Creating table: email_service.jobs...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_service.jobs (
                id SERIAL PRIMARY KEY,
                chemical_query VARCHAR(500),
                user_email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'active',
                reminders_sent BOOLEAN DEFAULT FALSE,
                closed_at TIMESTAMP,
                total_responses INTEGER DEFAULT 0,
                last_summary_sent_at TIMESTAMP,
                closure_notification_sent BOOLEAN DEFAULT FALSE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create job_supplier_states table
        print("Creating table: email_service.job_supplier_states...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_service.job_supplier_states (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL REFERENCES email_service.jobs(id) ON DELETE CASCADE,
                company_name VARCHAR(255),
                email_id VARCHAR(255),
                domain VARCHAR(255),
                initial_email_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied BOOLEAN DEFAULT FALSE,
                reply_received_at TIMESTAMP,
                reminder_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create supplier_emails table
        print("Creating table: email_service.supplier_emails...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_service.supplier_emails (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL REFERENCES email_service.jobs(id) ON DELETE CASCADE,
                supplier_state_id INTEGER REFERENCES email_service.job_supplier_states(id) ON DELETE SET NULL,
                email_type VARCHAR(50),
                from_email VARCHAR(255),
                to_email VARCHAR(255),
                subject VARCHAR(500),
                body TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gmail_message_id VARCHAR(255) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create insights table
        print("Creating table: email_service.insights...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_service.insights (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL REFERENCES email_service.jobs(id) ON DELETE CASCADE,
                supplier VARCHAR(255),
                contact_person VARCHAR(255),
                product VARCHAR(500),
                quantity VARCHAR(255),
                price DECIMAL(12,2),
                delivery_date DATE,
                email_body TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes for performance
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON email_service.jobs(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_email ON email_service.jobs(user_email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_supplier_states_job_id ON email_service.job_supplier_states(job_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_emails_job_id ON email_service.supplier_emails(job_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_supplier_emails_sent_at ON email_service.supplier_emails(sent_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_job_id ON email_service.insights(job_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_supplier ON email_service.insights(supplier);")
        
        print("\n✅ Schema and tables created successfully!")
        print("\nSchema Structure:")
        print("  - email_service.jobs")
        print("  - email_service.job_supplier_states")
        print("  - email_service.supplier_emails")
        print("  - email_service.insights")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_schema_and_tables()
