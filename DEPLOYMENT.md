# Crystal Supplier Email Service - Production Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the Crystal Supplier Email Service to Google Cloud Platform (GCP) as a production-ready service.

## Prerequisites

### Local Development Environment
- Google Cloud SDK (gcloud CLI) installed and configured
- Docker installed and running
- Git installed
- Service account credentials with appropriate IAM permissions
- Access to your organization's GCP project

### GCP Account Requirements
- Active GCP billing account
- Permissions to:
  - Create and manage Cloud Run services
  - Create and manage Cloud SQL instances
  - Create Cloud Storage buckets
  - Create service accounts and manage IAM
  - Enable APIs
  - Configure custom domains

### Required GCP APIs
The deployment script will enable these APIs:
- Cloud Run
- Cloud SQL Admin
- Cloud Storage
- Artifact Registry
- Gmail API
- Generative AI API
- Compute Engine
- Service Networking

## Architecture Overview

### Components
1. **Cloud Run** - Containerized FastAPI backend and frontend serving
2. **Cloud SQL** - PostgreSQL database for persistent storage
3. **Cloud Storage** - GCS bucket for job archives and exports
4. **Artifact Registry** - Docker image storage
5. **Service Account** - IAM identity for inter-service communication
6. **Cloud Scheduler** (optional) - Periodic job processing

### Data Flow
```
User Browser → Cloud Run (Frontend)
                ↓
            FastAPI Backend
                ↓
        Cloud SQL (Jobs DB) + GCS (Archives)
                ↓
          Gmail API (Outbound)
                ↓
        Supplier Emails
```

## Step-by-Step Deployment

### Option 1: Automated Deployment (Recommended)

#### 1. Prepare Your Environment

```bash
# Clone the repository
git clone https://github.com/amitgupta1000/crystal-supplier-email-service.git
cd crystal-supplier-email-service

# Make the deployment script executable
chmod +x deploy-gcp.sh

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
```

#### 2. Run Deployment Script

```bash
./deploy-gcp.sh
```

The script will prompt for:
- GCP Project ID
- Deployment region
- Gmail impersonate user email
- Cloud SQL database password
- Cloud SQL instance hostname

The script will automatically:
- Enable required GCP APIs
- Create Cloud SQL PostgreSQL instance
- Create Cloud Storage bucket
- Create service account with necessary roles
- Create Artifact Registry repository
- Build and push Docker image
- Deploy to Cloud Run

#### 3. Post-Deployment Configuration

After the script completes:

```bash
# Get the Cloud Run service URL
gcloud run services describe crystal-supplier-email-service \
  --region=us-central1 \
  --format='value(status.url)'

# Configure custom domain (optional)
gcloud run domain-mappings create \
  --service=crystal-supplier-email-service \
  --domain=email-service.yourdomain.com \
  --region=us-central1

# Verify DNS configuration
gcloud run domain-mappings list
```

### Option 2: Manual Step-by-Step Deployment

#### Step 1: Set Up Environment Variables

```bash
# Export variables for use throughout deployment
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export SERVICE_NAME="crystal-supplier-email-service"
export BUCKET_NAME="crystal-supplier-email-data"

# Set as default project
gcloud config set project $PROJECT_ID
```

#### Step 2: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudsql.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  gmail.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com
```

#### Step 3: Create Cloud SQL PostgreSQL Instance

```bash
# Create the instance
gcloud sql instances create crystal-email-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --no-backup \
  --enable-bin-log

# Create the database
gcloud sql databases create crystal_db \
  --instance=crystal-email-db

# Create database user
gcloud sql users create emailservice \
  --instance=crystal-email-db \
  --password=YourSecurePassword123!

# Get instance IP for connection
gcloud sql instances describe crystal-email-db \
  --format='value(ipAddresses[0].ipAddress)'
```

**Note:** Save the IP address returned above for later use.

#### Step 4: Create Cloud Storage Bucket

```bash
# Create bucket
gsutil mb -l $REGION gs://$BUCKET_NAME

# Enable versioning
gsutil versioning set on gs://$BUCKET_NAME

# Set lifecycle policy (optional - delete old jobs after 180 days)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 180}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://$BUCKET_NAME
```

#### Step 5: Create and Configure Service Account

```bash
# Create service account
gcloud iam service-accounts create crystal-email-sa \
  --display-name="Crystal Email Service"

export SA_EMAIL="crystal-email-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary IAM roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/cloudsql.client

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/storage.objectAdmin

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/logging.logWriter

# Create and download key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=$SA_EMAIL
```

#### Step 6: Configure Gmail API Domain-Wide Delegation

This step requires access to your Google Workspace admin console.

```bash
# Get the client ID of the service account
gcloud iam service-accounts describe $SA_EMAIL \
  --format='value(oauth2Config.clientId)'

# In Google Workspace Admin Console:
# 1. Go to Admin > Security > API Controls > Domain-wide delegation
# 2. Add the service account client ID
# 3. Grant scopes: https://www.googleapis.com/auth/gmail.modify
```

#### Step 7: Create Artifact Registry Repository

```bash
gcloud artifacts repositories create crystal-repo \
  --repository-format=docker \
  --location=$REGION

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

#### Step 8: Build and Push Docker Image

```bash
# Build the image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo/crystal-email-service:latest .

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo/crystal-email-service:latest
```

#### Step 9: Get Cloud SQL Connection Name

```bash
export CLOUD_SQL_CONNECTION=$(gcloud sql instances describe crystal-email-db \
  --format='value(connectionName)')

echo $CLOUD_SQL_CONNECTION
# Output format: project:region:instance-name
```

#### Step 10: Deploy to Cloud Run

```bash
gcloud run deploy $SERVICE_NAME \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo/crystal-email-service:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --min-instances=1 \
  --set-env-vars=\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
DATABASE_URL=postgresql://emailservice:YourSecurePassword123!@CLOUD_SQL_IP:5432/crystal_db,\
CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION,\
GCS_BUCKET_NAME=$BUCKET_NAME,\
GMAIL_IMPERSONATE_USER=noreply@yourdomain.com,\
ENVIRONMENT=production \
  --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
  --service-account=$SA_EMAIL
```

#### Step 11: Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service=$SERVICE_NAME \
  --domain=email-service.yourdomain.com \
  --region=$REGION

# Get SSL certificates and DNS information
gcloud run domain-mappings describe email-service.yourdomain.com \
  --region=$REGION

# Configure DNS CNAME in your domain registrar pointing to goog-managed-cert.com
```

## Post-Deployment Configuration

### 1. Database Migration

If migrating from SQLite to PostgreSQL, run migrations:

```bash
# Connect to Cloud SQL instance
gcloud sql connect crystal-email-db \
  --user=emailservice

# In the psql prompt, run:
psql crystal_db < migration.sql

# Exit psql
\q
```

### 2. Upload Data Files

```bash
# Upload supplier data to GCS (for reference)
gsutil cp suppliers.csv gs://$BUCKET_NAME/data/
gsutil cp message_template.csv gs://$BUCKET_NAME/data/
gsutil cp reminder_template.csv gs://$BUCKET_NAME/data/
```

### 3. Set Up Monitoring

```bash
# Create a Cloud Monitoring dashboard
gcloud monitoring dashboards create --config-from-file=- << EOF
{
  "displayName": "Crystal Email Service Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Cloud Run Requests",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" resource.label.service_name=\"$SERVICE_NAME\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF
```

### 4. Configure Cloud Logging

```bash
# Create log sink for important events
gcloud logging sinks create crystal-email-sink \
  storage.googleapis.com/crystal-email-logs \
  --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR'
```

### 5. Set Up Alerts

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="High Error Rate Alert" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05
```

## Verification

### 1. Test API Endpoints

```bash
# Get the Cloud Run service URL
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(status.url)')

# Test API health
curl $SERVICE_URL/health

# Get suppliers list
curl $SERVICE_URL/api/suppliers

# Get jobs list
curl $SERVICE_URL/api/jobs
```

### 2. Test Database Connection

```bash
gcloud sql connect crystal-email-db --user=emailservice
# Test query: SELECT 1;
\q
```

### 3. Verify GCS Access

```bash
gsutil ls gs://$BUCKET_NAME
```

### 4. Check Cloud Run Logs

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit=50 \
  --format=json
```

## Scaling and Performance

### Auto-scaling Configuration

Cloud Run automatically scales based on traffic. To adjust scaling:

```bash
# Update max instances
gcloud run services update $SERVICE_NAME \
  --max-instances=50 \
  --region=$REGION

# Update min instances (for faster response times)
gcloud run services update $SERVICE_NAME \
  --min-instances=2 \
  --region=$REGION
```

### Database Connection Pooling

Update `requirements.txt` to include connection pooling:

```python
# In backend/database.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## Backup and Disaster Recovery

### 1. Enable Cloud SQL Automated Backups

```bash
gcloud sql backups create \
  --instance=crystal-email-db

# Configure automated backups
gcloud sql instances patch crystal-email-db \
  --backup-start-time=03:00 \
  --retained-backups-count=30 \
  --transaction-log-retention-days=7
```

### 2. Cloud Storage Backup

```bash
# Enable object versioning (already done)
# Restore a deleted object:
gsutil restore gs://crystal-supplier-email-data/path/to/file
```

### 3. Test Disaster Recovery

```bash
# Create a backup
gcloud sql backups create \
  --instance=crystal-email-db

# Test restoration to a new instance
gcloud sql instances clone crystal-email-db crystal-email-db-dr \
  --async
```

## Security Best Practices

### 1. Use Secret Manager

```bash
# Store sensitive data in Secret Manager instead of env vars
gcloud secrets create db-password --data-file=- << EOF
YourSecurePassword123!
EOF

# Grant service account access
gcloud secrets add-iam-policy-binding db-password \
  --member=serviceAccount:$SA_EMAIL \
  --role=roles/secretmanager.secretAccessor
```

### 2. Configure VPC Service Controls (Optional)

```bash
# Create VPC service perimeter
gcloud access-context-manager perimeters create \
  --display-name="crystal-perimeter" \
  --resources=projects/$PROJECT_ID \
  --restricted-services=storage.googleapis.com,sqladmin.googleapis.com
```

### 3. Implement API Authentication

Add to `main.py`:

```python
from fastapi.security import HTTPBearer, HTTPAuthCredential
from fastapi import Security

security = HTTPBearer()

@app.get("/api/suppliers")
def get_suppliers(credentials: HTTPAuthCredential = Security(security)):
    # Validate JWT token
    token = credentials.credentials
    # Validate and proceed
    ...
```

### 4. Enable Cloud Armor (Optional)

```bash
gcloud compute security-policies create crystal-armor \
  --description="Cloud Armor policy for Crystal Email Service"

# Add rate limiting rule
gcloud compute security-policies rules create 100 \
  --security-policy=crystal-armor \
  --action=rate-based-ban \
  --rate-limit-options=exceeding-traffic-percent=90,rate-limit-options=enforce-on-key=IP
```

## Troubleshooting

### Cloud Run Deployment Issues

```bash
# View detailed deployment logs
gcloud run services describe $SERVICE_NAME --region=$REGION

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=100 \
  --format=json
```

### Database Connection Problems

```bash
# Test Cloud SQL connectivity
gcloud sql connect crystal-email-db --user=emailservice

# View connection errors
gcloud logging read "resource.type=cloudsql_database" --limit=50
```

### Email Sending Issues

```bash
# Verify Gmail API is enabled
gcloud services list --enabled | grep gmail

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL"
```

## Cost Estimation

### Monthly Estimated Costs (Low Traffic)
- Cloud Run: $5-20 (compute + requests)
- Cloud SQL (db-f1-micro): $10-15
- Cloud Storage: $1-5 (storage + requests)
- **Total: ~$20-40/month**

### Monthly Estimated Costs (High Traffic)
- Cloud Run (scaled): $50-200
- Cloud SQL (larger instance): $50-100
- Cloud Storage: $5-20
- **Total: ~$105-320/month**

## Next Steps

1. [ ] Configure custom domain
2. [ ] Set up monitoring and alerting
3. [ ] Enable Cloud Armor for DDoS protection
4. [ ] Configure automated backups
5. [ ] Set up CI/CD pipeline for deployments
6. [ ] Enable audit logging
7. [ ] Configure email forwarding rules
8. [ ] Set up team access and roles

## Support and Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

## Rollback Procedures

### Rollback to Previous Image

```bash
# View available images
gcloud container images list --repository=${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo

# Deploy previous version
gcloud run deploy $SERVICE_NAME \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo/crystal-email-service:previous-tag \
  --region=$REGION
```

### Rollback Database Changes

```bash
# List available backups
gcloud sql backups list --instance=crystal-email-db

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=crystal-email-db
```

---

**Last Updated:** May 2026
**Version:** 1.0.0
