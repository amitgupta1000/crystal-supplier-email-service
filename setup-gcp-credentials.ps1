# Setup GCP Credentials for Crystal Supplier Email Service
# PowerShell version for Windows

$ProjectId = "gen-lang-client-0665888431"
$ServiceAccount = "451921002283-compute@developer.gserviceaccount.com"
$KeyFile = "$HOME\.config\gcloud\compute-service-account-key.json"
$KeyDir = Split-Path -Parent $KeyFile

Write-Host "🔐 GCP Credential Setup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Project ID: $ProjectId"
Write-Host "Service Account: $ServiceAccount"
Write-Host "Key Location: $KeyFile"
Write-Host ""

# Create directory if it doesn't exist
if (-not (Test-Path -Path $KeyDir)) {
    New-Item -ItemType Directory -Path $KeyDir -Force | Out-Null
}

# Check if key already exists
if (Test-Path -Path $KeyFile) {
    Write-Host "✅ Service account key already exists" -ForegroundColor Green
} else {
    Write-Host "📥 Creating new service account key..." -ForegroundColor Yellow
    
    # Create a new key
    gcloud iam service-accounts keys create $KeyFile `
        --iam-account=$ServiceAccount `
        --project=$ProjectId
    
    Write-Host "✅ Service account key created" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔍 Verifying Credentials..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# Set environment variable
$env:GOOGLE_APPLICATION_CREDENTIALS = $KeyFile
Write-Host "✅ GOOGLE_APPLICATION_CREDENTIALS set" -ForegroundColor Green
Write-Host ""

# Verify authentication
Write-Host "Testing gcloud authentication..." -ForegroundColor Yellow
gcloud auth activate-service-account --key-file=$KeyFile --project=$ProjectId
Write-Host "✅ Service account authenticated" -ForegroundColor Green
Write-Host ""

# Test GCS access
Write-Host "Testing Cloud Storage access..." -ForegroundColor Yellow
try {
    gsutil ls gs://crystal-supplier-email-data 2>$null
    Write-Host "✅ Cloud Storage bucket accessible" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Cloud Storage bucket not accessible (may need permissions)" -ForegroundColor Yellow
}
Write-Host ""

# Test APIs
Write-Host "Testing enabled APIs..." -ForegroundColor Yellow
$EnabledServices = gcloud services list --enabled --project=$ProjectId --format="value(name)"

if ($EnabledServices -match "gmail") {
    Write-Host "✅ Gmail API enabled" -ForegroundColor Green
} else {
    Write-Host "⚠️  Gmail API not enabled" -ForegroundColor Yellow
}

if ($EnabledServices -match "generativelanguage|cloudaicompanion") {
    Write-Host "✅ Generative AI API enabled" -ForegroundColor Green
} else {
    Write-Host "⚠️  Generative AI API not enabled" -ForegroundColor Yellow
}

if ($EnabledServices -match "sqladmin") {
    Write-Host "✅ Cloud SQL API enabled" -ForegroundColor Green
} else {
    Write-Host "⚠️  Cloud SQL API not enabled" -ForegroundColor Yellow
}

if ($EnabledServices -match "storage.googleapis.com") {
    Write-Host "✅ Cloud Storage API enabled" -ForegroundColor Green
} else {
    Write-Host "⚠️  Cloud Storage API not enabled" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 GCP Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Copy .env.example to .env"
Write-Host "2. Update .env with your actual values:"
Write-Host "   - GOOGLE_GENAI_API_KEY: Your Gemini API key (not service account)"
Write-Host "   - EMAIL_SENDER: The email address to send from"
Write-Host "   - GCS_BUCKET_NAME: Your GCS bucket name"
Write-Host "   - DATABASE_URL: Your Cloud SQL connection string"
Write-Host "3. Run: `$env:GOOGLE_APPLICATION_CREDENTIALS = '$KeyFile'"
Write-Host "4. Test with: python -c 'from google.oauth2 import service_account; print(\"Credentials OK\")'"
Write-Host ""
Write-Host "To make GOOGLE_APPLICATION_CREDENTIALS persistent:" -ForegroundColor Cyan
Write-Host "  [Environment]::SetEnvironmentVariable('GOOGLE_APPLICATION_CREDENTIALS', '$KeyFile', 'User')"
Write-Host ""
