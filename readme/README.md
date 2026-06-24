# Crystal Supplier Email Service

A full-stack application that automates the process of sending Requests for Quote (RFQs) to multiple suppliers for chemical products, tracks their responses, and extracts pricing/logistics insights using AI.

> **📚 Looking for detailed documentation?** 
> We have an extensive collection of guides, API references, and architecture documents. 
> Start by checking out our **Documentation Index** to find exactly what you need.

## Overview

Crystal Supplier Email Service is designed to streamline the supplier communication workflow for bulk chemical procurement. It enables users to:

- **Launch RFQs**: Create jobs that send customized email requests to multiple suppliers simultaneously
- **Track Responses**: Monitor supplier replies and automatically send reminders to non-responsive suppliers
- **Extract Insights**: Use Google Generative AI to automatically parse supplier responses and extract key information (pricing, quantities, delivery dates, contact persons)
- **Archive Results**: Store job summaries and insights in Google Cloud Storage for long-term archival and analysis
- **Manage Campaigns**: View job status, supplier response rates, and collected insights through an intuitive web interface

## Architecture

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (development) / Cloud SQL (production)
- **Task Scheduling**: APScheduler for background job processing
- **Email Integration**: Gmail API with domain-wide delegation
- **AI Integration**: Google Generative AI for insight extraction
- **Cloud Storage**: Google Cloud Storage for archival

### Frontend
- **Framework**: React 19 with Vite
- **Styling**: Tailwind CSS + PostCSS
- **Icons**: Lucide React
- **UI Pattern**: Multi-column campaign manager with real-time updates

## Project Structure

```
crystal-supplier-email-service/
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container configuration
├── suppliers.csv                    # Supplier database
├── message_template.csv             # Email message templates
├── reminder_template.csv            # Reminder email templates
├── insights.csv                     # Extracted insights data
│
├── backend/
│   ├── database.py                  # SQLAlchemy ORM models
│   ├── scheduler.py                 # APScheduler job processing
│   ├── email_utils.py               # Gmail API integration
│   ├── gcs_utils.py                 # Google Cloud Storage operations
│   ├── send_requests.py             # Email sending logic
│   └── extract_insights.py          # AI-powered insight extraction
│
└── frontend/
    ├── package.json                 # Node.js dependencies
    ├── vite.config.js               # Vite bundler configuration
    ├── tailwind.config.js           # Tailwind CSS configuration
    ├── index.html                   # HTML entry point
    ├── src/
    │   ├── main.jsx                 # React application entry
    │   ├── App.jsx                  # Main App component
    │   ├── App.css                  # Application styles
    │   └── index.css                # Global styles
    └── public/                      # Static assets
```

## Features

### 1. Job Management
- Create new RFQ campaigns with chemical product details
- Select target suppliers from the database
- Track job status (active, closed)
- View historical campaigns

### 2. Automated Workflows
- **T+0h**: Send initial RFQ emails to selected suppliers
- **T+24h**: Send automated reminder emails to non-responsive suppliers
- **T+48h**: Close job and archive results to GCS

### 3. Email Integration
- Gmail API integration with domain-wide delegation
- Customizable email templates with supplier personalization
- Automatic recipient filtering and validation
- Support for HTML email content

### 4. Insight Extraction
- Automatic parsing of supplier email replies
- AI-powered extraction of:
  - Supplier name and contact person
  - Product specifications
  - Quantity and pricing information
  - Delivery dates and incoterms
- Structured CSV export of insights

### 5. Data Management
- SQLite database for real-time job tracking (development)
- Cloud SQL support for production deployments
- Automatic GCS archival of closed jobs
- Job summaries and insights CSV generation

### 6. Frontend Dashboard
- Multi-column campaign manager interface
- Real-time job status updates
- Supplier response tracking
- Insight visualization
- Preset query templates

## Prerequisites

### Local Development
- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Git**
- **SQLite3** (usually included with Python)

### Production (GCP)
- Google Cloud project with enabled APIs:
  - Cloud Run
  - Cloud SQL
  - Cloud Storage
  - Gmail API
  - Generative AI API
- Service account with appropriate IAM roles
- Docker container registry (Artifact Registry)

## Setup Instructions

### 1. Local Development Setup

#### Backend Setup
```bash
# Clone the repository
git clone https://github.com/amitgupta1000/crystal-supplier-email-service.git
cd crystal-supplier-email-service

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your GCP credentials and configuration

# Initialize database
python -c "from backend.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Start backend server (development)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Application will be available at http://localhost:5173
```

#### Configure Suppliers Data
Edit `suppliers.csv` with your supplier information:
```csv
Company Name,Email ID,Location,Salutation 1
Supplier A,contact@suppliea.com,Singapore,Dear Mr. Gupta
Supplier B,contact@supplierb.com,Dubai,Dear Sir
```

### 2. Environment Configuration

Create `.env` file in the project root:

```bash
# Google Cloud Configuration
# Local development only. On Cloud Run, use the attached service account via ADC.
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# Gmail Configuration
GMAIL_IMPERSONATE_USER=noreply@yourdomain.com
EMAIL_SENDER=noreply@yourdomain.com
EMAIL_RECIPIENTS=admin@yourdomain.com

# Database (SQLite for dev, Cloud SQL connection string for prod)
DATABASE_URL=sqlite:///./jobs.db

# Google Cloud Storage
GCS_BUCKET_NAME=crystal-supplier-email-data

# Generative AI
GOOGLE_GENAI_API_KEY=your-api-key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

## API Endpoints

### Jobs
- `GET /api/jobs` - List all jobs
- `POST /api/jobs/start` - Create and start a new RFQ job
- `GET /api/jobs/{job_id}` - Get job details
- `POST /api/jobs/{job_id}/insights/refresh` - Refresh extracted insights

### Suppliers
- `GET /api/suppliers` - List all suppliers

### Health Check
- `GET /health` - Service health status

## Database Schema

### Jobs Table
```
- id (Primary Key)
- chemical_query (String)
- created_at (DateTime)
- status (String: 'active' or 'closed')
- reminders_sent (Boolean)
```

### Job Supplier States Table
```
- id (Primary Key)
- job_id (Foreign Key)
- company_name (String)
- email_id (String)
- domain (String)
- initial_email_sent_at (DateTime)
- replied (Boolean)
```

### Insights Table
```
- id (Primary Key)
- job_id (Foreign Key)
- supplier (String)
- contact_person (String)
- product (String)
- quantity (String)
- price (String)
- delivery_date (String)
- extracted_at (DateTime)
```

## Background Scheduler

The APScheduler runs in the application lifespan and processes active jobs every minute:

1. **Reminder Processing**: Identifies jobs at T+24h and sends reminder emails
2. **Job Closure**: Identifies jobs at T+48h, archives results to GCS, and closes jobs
3. **Error Handling**: Logs failures and continues processing other jobs

Note: Development uses shortened intervals (2 and 4 minutes) for testing.

## Production Deployment on GCP

### Prerequisites
- GCP project created
- gcloud CLI installed and configured
- Docker installed locally
- Appropriate IAM permissions

### Step-by-Step Deployment

#### 1. Prepare Google Cloud Environment

```bash
# Set project variables
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export SERVICE_NAME=crystal-supplier-email-service

# Set as default project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudsql.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  gmail.googleapis.com \
  aiplatform.googleapis.com
```

#### 2. Create Cloud SQL Instance

```bash
# Create Cloud SQL PostgreSQL instance (recommended for production)
gcloud sql instances create crystal-email-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --no-backup

# Create database
gcloud sql databases create crystal_db \
  --instance=crystal-email-db

# Create database user
gcloud sql users create emailservice \
  --instance=crystal-email-db \
  --password=YOUR_SECURE_PASSWORD
```

#### 3. Create Cloud Storage Bucket

```bash
# Create GCS bucket for job archival
gsutil mb -l $REGION gs://crystal-supplier-email-data/

# Set retention policy (optional)
gsutil retention set 30d gs://crystal-supplier-email-data/
```

#### 4. Create and Configure Service Account

```bash
# Create service account
gcloud iam service-accounts create crystal-email-sa \
  --display-name="Crystal Email Service"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:crystal-email-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/cloudsql.client

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:crystal-email-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

# Create and download service account key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=crystal-email-sa@$PROJECT_ID.iam.gserviceaccount.com
```

#### 5. Configure Gmail API Access

```bash
# Enable Gmail API impersonation for the service account
# This requires domain-wide delegation setup:

# 1. Go to Google Cloud Console > APIs & Services > Credentials
# 2. Create OAuth 2.0 consent screen (Internal)
# 3. In your Google Workspace domain admin console:
#    - Go to Admin > Security > API Controls
#    - Add the service account client ID with scope:
#      https://www.googleapis.com/auth/gmail.modify

# 2. For local development, set GOOGLE_APPLICATION_CREDENTIALS to your key file path.
#    On Cloud Run, do not set GOOGLE_APPLICATION_CREDENTIALS; use ADC instead.
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
```

#### 6. Build and Push Docker Image

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create crystal-repo \
  --repository-format=docker \
  --location=$REGION

# Build Docker image
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/crystal-repo/crystal-email-service:latest .

# Push to Artifact Registry
docker push $REGION-docker.pkg.dev/$PROJECT_ID/crystal-repo/crystal-email-service:latest
```

#### 7. Deploy to Cloud Run

```bash
# Get Cloud SQL instance connection name
CLOUD_SQL_CONNECTION=$(gcloud sql instances describe crystal-email-db \
  --format='value(connectionName)')

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/crystal-repo/crystal-email-service:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --set-env-vars=\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
DATABASE_URL=postgresql://emailservice:YOUR_SECURE_PASSWORD@CLOUD_SQL_IP:5432/crystal_db,\
GCS_BUCKET_NAME=crystal-supplier-email-data,\
GMAIL_IMPERSONATE_USER=noreply@yourdomain.com,\
GOOGLE_CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION \
  --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
  --service-account=crystal-email-sa@$PROJECT_ID.iam.gserviceaccount.com
```

#### 8. Configure Domain and SSL

```bash
# Map custom domain (optional)
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=email-service.yourdomain.com \
  --region=$REGION

# Verify DNS records and wait for SSL provisioning
```

#### 9. Set Up Cloud Scheduler for Periodic Tasks (Optional)

If you want independent scheduled processing outside of the application:

```bash
# Create Cloud Scheduler job
gcloud scheduler jobs create http process-jobs \
  --location=$REGION \
  --schedule="*/1 * * * *" \
  --uri=https://$SERVICE_NAME.run.app/api/jobs/process \
  --http-method=POST
```

### Production Checklist

- [ ] Cloud SQL backup policies configured
- [ ] Cloud Run auto-scaling limits set appropriately
- [ ] Custom domain mapped with SSL
- [ ] Error logging configured (Cloud Logging)
- [ ] Monitoring alerts set up (Cloud Monitoring)
- [ ] Service account keys rotated periodically
- [ ] Database migrations tested
- [ ] Frontend built and optimized
- [ ] Environment variables securely stored (Secret Manager)
- [ ] CORS policies reviewed and restricted to frontend domain

## Monitoring and Logging

### Cloud Logging
View application logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit=50 --format=json
```

### Cloud Monitoring
Set up dashboards and alerts:
```bash
# View service metrics
gcloud monitoring dashboards list
```

## Troubleshooting

### Email Not Sending
1. Verify Gmail API is enabled
2. Check GOOGLE_APPLICATION_CREDENTIALS path
3. Ensure service account has domain-wide delegation
4. Verify GMAIL_IMPERSONATE_USER has necessary Gmail scopes

### Database Connection Issues
1. Verify Cloud SQL instance is running
2. Check service account has cloudsql.client role
3. Verify DATABASE_URL format and credentials
4. Test connection: `psql $DATABASE_URL -c "SELECT 1"`

### GCS Upload Failures
1. Verify bucket exists: `gsutil ls -b gs://crystal-supplier-email-data/`
2. Check service account has storage.objectAdmin role
3. Verify bucket location matches Cloud Run region

### Scheduler Not Running
1. Check Cloud Run memory allocation (minimum 512Mi recommended)
2. View logs for scheduler errors
3. Verify database connectivity from the container

## Performance Optimization

### Backend
- Use connection pooling for database (SQLAlchemy)
- Implement Redis caching for supplier lists
- Batch email processing for large campaigns
- Consider async email processing with Celery

### Frontend
- Enable production build optimization
- Implement pagination for large job lists
- Use React Query for API caching
- Lazy load dashboard components

### Infrastructure
- Configure Cloud Run concurrency limits
- Set up Cloud SQL connection pooling
- Use Cloud CDN for frontend assets
- Implement rate limiting on API endpoints

## Security Considerations

1. **API Security**
   - Add authentication (JWT/OAuth2) to API endpoints
   - Implement rate limiting
   - Use HTTPS only

2. **Data Protection**
   - Encrypt database at rest
   - Enable encryption in transit
   - Implement field-level encryption for sensitive data

3. **Access Control**
   - Use least-privilege IAM roles
   - Rotate service account keys regularly
   - Implement VPC for database access

4. **Audit Logging**
   - Enable Cloud Audit Logs
   - Log all administrative actions
   - Monitor for suspicious activities

## Development Roadmap

- [ ] WebSocket support for real-time updates
- [ ] Multi-language email template support
- [ ] Advanced analytics dashboard
- [ ] Integration with CRM systems
- [ ] Automated reply parsing with LLMs
- [ ] A/B testing for email templates
- [ ] Supplier performance scoring
- [ ] Price tracking and trend analysis

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Submit a pull request
5. Ensure CI/CD checks pass

## Deployment to GCP Step Summary

**Quick Reference:**
1. Enable GCP APIs (Cloud Run, Cloud SQL, Storage, etc.)
2. Create Cloud SQL PostgreSQL instance
3. Create Cloud Storage bucket
4. Create service account with necessary IAM roles
5. Configure Gmail API domain-wide delegation
6. Build Docker image and push to Artifact Registry
7. Deploy to Cloud Run with environment variables
8. Map custom domain (optional)
9. Configure monitoring and logging
10. Set up backup and disaster recovery

**Estimated Setup Time:** 20-30 minutes
**Monthly Cost (estimated):** $50-200 depending on traffic

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the development team.

## Version History

- **v1.0.0** (Current) - Initial release with core RFQ functionality
