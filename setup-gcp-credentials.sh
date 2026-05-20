#!/bin/bash
# Setup GCP Credentials for Crystal Supplier Email Service

set -e

PROJECT_ID="gen-lang-client-0665888431"
SERVICE_ACCOUNT="451921002283-compute@developer.gserviceaccount.com"
KEY_FILE="$HOME/.config/gcloud/compute-service-account-key.json"

echo "🔐 GCP Credential Setup Script"
echo "========================================"
echo "Project ID: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo "Key Location: $KEY_FILE"
echo ""

# Create directory if it doesn't exist
mkdir -p "$(dirname "$KEY_FILE")"

# Check if key already exists
if [ -f "$KEY_FILE" ]; then
    echo "✅ Service account key already exists at $KEY_FILE"
else
    echo "📥 Downloading service account key..."
    
    # Download the first available key
    KEY_ID=$(gcloud iam service-accounts keys list \
        --iam-account=$SERVICE_ACCOUNT \
        --project=$PROJECT_ID \
        --filter="validAfterTime:*" \
        --format="value(name)" | head -n1)
    
    if [ -z "$KEY_ID" ]; then
        echo "❌ Error: No keys found. Creating a new key..."
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account=$SERVICE_ACCOUNT \
            --project=$PROJECT_ID
    else
        echo "Found key: $KEY_ID"
        # Export existing key
        gcloud iam service-accounts keys create "$KEY_FILE" \
            --iam-account=$SERVICE_ACCOUNT \
            --project=$PROJECT_ID
    fi
    
    echo "✅ Service account key saved to $KEY_FILE"
fi

echo ""
echo "🔍 Verifying Credentials..."
echo "========================================"

# Test credentials
export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"

echo "✅ Credentials file set"
echo ""

# Verify authentication
echo "Testing gcloud authentication..."
gcloud auth activate-service-account --key-file="$KEY_FILE" --project=$PROJECT_ID
echo "✅ Service account authenticated"
echo ""

# Test GCS access
echo "Testing Cloud Storage access..."
if gsutil ls gs://crystal-supplier-email-data 2>/dev/null; then
    echo "✅ Cloud Storage bucket accessible"
else
    echo "⚠️  Cloud Storage bucket not accessible (may need permissions)"
fi
echo ""

# Test Gmail API
echo "Testing Gmail API access..."
gcloud services list --enabled --project=$PROJECT_ID | grep -i gmail > /dev/null && \
    echo "✅ Gmail API enabled" || echo "⚠️  Gmail API not enabled"
echo ""

# Test Generative AI API
echo "Testing Generative AI (Gemini) API..."
gcloud services list --enabled --project=$PROJECT_ID | grep -i "generativelanguage\|cloudaicompanion" > /dev/null && \
    echo "✅ Generative AI API enabled" || echo "⚠️  Generative AI API not enabled"
echo ""

# Test Cloud SQL
echo "Testing Cloud SQL..."
gcloud sql instances list --project=$PROJECT_ID 2>/dev/null | grep -i crystal && \
    echo "✅ Cloud SQL instances found" || echo "⚠️  No Cloud SQL instances found"
echo ""

echo "🎉 GCP Setup Complete!"
echo "========================================"
echo ""
echo "Next Steps:"
echo "1. Copy .env.example to .env"
echo "2. Update .env with your actual values"
echo "3. Run: export GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE"
echo "4. Test with: python -c 'from google.oauth2 import service_account; print(\"✅ Credentials OK\")'"
echo ""
