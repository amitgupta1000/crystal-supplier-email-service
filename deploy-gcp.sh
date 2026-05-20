#!/bin/bash

# Crystal Supplier Email Service - GCP Deployment Script
# This script automates the deployment process to Google Cloud Platform

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    command -v gcloud >/dev/null 2>&1 || { log_error "gcloud CLI is not installed"; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "Docker is not installed"; exit 1; }
    
    log_info "Prerequisites check passed"
}

# Set up GCP environment
setup_gcp_environment() {
    log_info "Setting up GCP environment..."
    
    # Create variables
    export PROJECT_ID=$1
    export REGION=${2:-us-central1}
    export SERVICE_NAME=crystal-supplier-email-service
    export BUCKET_NAME=crystal-supplier-email-data
    
    gcloud config set project $PROJECT_ID
    
    log_info "GCP Project: $PROJECT_ID"
    log_info "Region: $REGION"
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required Google Cloud APIs..."
    
    gcloud services enable \
        run.googleapis.com \
        cloudsql.googleapis.com \
        storage.googleapis.com \
        artifactregistry.googleapis.com \
        gmail.googleapis.com \
        aiplatform.googleapis.com \
        compute.googleapis.com \
        servicenetworking.googleapis.com
    
    log_info "APIs enabled successfully"
}

# Create Cloud SQL instance
create_cloud_sql() {
    log_info "Creating Cloud SQL PostgreSQL instance..."
    
    local INSTANCE_NAME="crystal-email-db"
    local DB_USER="emailservice"
    local DB_PASSWORD=$1
    
    # Check if instance already exists
    if gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID 2>/dev/null; then
        log_warn "Cloud SQL instance $INSTANCE_NAME already exists"
    else
        gcloud sql instances create $INSTANCE_NAME \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=$REGION \
            --no-backup \
            --project=$PROJECT_ID
        
        log_info "Cloud SQL instance created"
    fi
    
    # Create database
    gcloud sql databases create crystal_db \
        --instance=$INSTANCE_NAME \
        --project=$PROJECT_ID || log_warn "Database may already exist"
    
    # Create database user
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password=$DB_PASSWORD \
        --project=$PROJECT_ID || log_warn "User may already exist"
    
    log_info "Cloud SQL setup completed"
}

# Create Cloud Storage bucket
create_storage_bucket() {
    log_info "Creating Cloud Storage bucket..."
    
    if gsutil ls -b gs://$BUCKET_NAME 2>/dev/null; then
        log_warn "Bucket gs://$BUCKET_NAME already exists"
    else
        gsutil mb -l $REGION gs://$BUCKET_NAME
        gsutil versioning set on gs://$BUCKET_NAME
        log_info "Cloud Storage bucket created"
    fi
}

# Create service account
create_service_account() {
    log_info "Creating service account..."
    
    local SA_NAME="crystal-email-sa"
    local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if service account exists
    if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID 2>/dev/null; then
        log_warn "Service account $SA_EMAIL already exists"
    else
        gcloud iam service-accounts create $SA_NAME \
            --display-name="Crystal Email Service" \
            --project=$PROJECT_ID
        
        log_info "Service account created"
    fi
    
    # Grant IAM roles
    log_info "Granting IAM roles..."
    
    for role in \
        roles/cloudsql.client \
        roles/storage.objectAdmin \
        roles/logging.logWriter
    do
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member=serviceAccount:$SA_EMAIL \
            --role=$role \
            --project=$PROJECT_ID || log_warn "Role $role may already be assigned"
    done
    
    # Create and download service account key
    log_info "Creating service account key..."
    gcloud iam service-accounts keys create sa-key.json \
        --iam-account=$SA_EMAIL \
        --project=$PROJECT_ID
    
    log_info "Service account setup completed"
    export SERVICE_ACCOUNT_EMAIL=$SA_EMAIL
}

# Create Artifact Registry repository
create_artifact_registry() {
    log_info "Creating Artifact Registry repository..."
    
    local REPO_NAME="crystal-repo"
    
    if gcloud artifacts repositories describe $REPO_NAME \
        --location=$REGION \
        --project=$PROJECT_ID 2>/dev/null; then
        log_warn "Repository $REPO_NAME already exists"
    else
        gcloud artifacts repositories create $REPO_NAME \
            --repository-format=docker \
            --location=$REGION \
            --project=$PROJECT_ID
        
        log_info "Artifact Registry repository created"
    fi
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    local IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/crystal-repo/crystal-email-service:latest"
    
    # Build image
    docker build -t $IMAGE_NAME .
    
    # Push to Artifact Registry
    docker push $IMAGE_NAME
    
    log_info "Docker image pushed: $IMAGE_NAME"
    export DOCKER_IMAGE=$IMAGE_NAME
}

# Get Cloud SQL connection name
get_cloud_sql_connection_name() {
    local INSTANCE_NAME="crystal-email-db"
    
    export CLOUD_SQL_CONNECTION=$(gcloud sql instances describe $INSTANCE_NAME \
        --format='value(connectionName)' \
        --project=$PROJECT_ID)
    
    log_info "Cloud SQL Connection Name: $CLOUD_SQL_CONNECTION"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log_info "Deploying to Cloud Run..."
    
    local DB_PASSWORD=$1
    local DB_HOST=$2
    
    gcloud run deploy $SERVICE_NAME \
        --image=$DOCKER_IMAGE \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --timeout=3600 \
        --max-instances=10 \
        --set-env-vars=\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
DATABASE_URL=postgresql://emailservice:${DB_PASSWORD}@${DB_HOST}:5432/crystal_db,\
GCS_BUCKET_NAME=$BUCKET_NAME,\
GMAIL_IMPERSONATE_USER=${GMAIL_USER},\
ENVIRONMENT=production,\
CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION \
        --add-cloudsql-instances=$CLOUD_SQL_CONNECTION \
        --service-account=$SERVICE_ACCOUNT_EMAIL \
        --project=$PROJECT_ID
    
    log_info "Cloud Run deployment completed"
}

# Get Cloud Run service URL
get_service_url() {
    local SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format='value(status.url)' \
        --project=$PROJECT_ID)
    
    log_info "Service URL: $SERVICE_URL"
    export SERVICE_URL=$SERVICE_URL
}

# Main deployment flow
main() {
    echo "================================"
    echo "Crystal Email Service - GCP Deployment"
    echo "================================"
    echo ""
    
    # Get user inputs
    read -p "Enter GCP Project ID: " PROJECT_ID
    read -p "Enter GCP Region (default: us-central1): " REGION
    REGION=${REGION:-us-central1}
    
    read -p "Enter Gmail impersonate user (e.g., noreply@domain.com): " GMAIL_USER
    read -s -p "Enter Cloud SQL database password: " DB_PASSWORD
    echo ""
    
    read -p "Enter Cloud SQL instance IP or hostname: " DB_HOST
    
    # Execute deployment steps
    check_prerequisites
    setup_gcp_environment "$PROJECT_ID" "$REGION"
    enable_apis
    create_cloud_sql "$DB_PASSWORD"
    create_storage_bucket
    create_service_account
    create_artifact_registry
    
    log_info "Configuring Docker authentication..."
    gcloud auth configure-docker ${REGION}-docker.pkg.dev
    
    build_and_push_image
    get_cloud_sql_connection_name
    deploy_to_cloud_run "$DB_PASSWORD" "$DB_HOST"
    get_service_url
    
    echo ""
    echo "================================"
    echo "Deployment completed successfully!"
    echo "================================"
    echo ""
    log_info "Service URL: $SERVICE_URL"
    echo ""
    echo "Next steps:"
    echo "1. Configure your domain to point to the Cloud Run service"
    echo "2. Set up monitoring and logging in Cloud Console"
    echo "3. Configure email forwarding rules"
    echo "4. Set up backup policies for Cloud SQL"
    echo ""
}

# Run main function
main
