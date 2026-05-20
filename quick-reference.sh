#!/bin/bash

# Quick Reference Guide for Crystal Email Service API
# Generated for local testing - adjust BASE_URL for production

# USAGE: source this file in your shell to get quick commands
# Then run any of the functions defined below

BASE_URL="${1:-http://localhost:8000}"

# Function to pretty-print JSON
pretty_json() {
    python3 -m json.tool <<< "$1" 2>/dev/null || echo "$1"
}

# ============================================================================
# HEALTH & BASIC ENDPOINTS
# ============================================================================

health() {
    echo "Checking API health..."
    curl -s "$BASE_URL/health" | pretty_json
}

get_suppliers() {
    echo "Getting all suppliers..."
    curl -s "$BASE_URL/api/suppliers" | pretty_json
}

# ============================================================================
# JOB MANAGEMENT
# ============================================================================

get_all_jobs() {
    echo "Getting all jobs..."
    curl -s "$BASE_URL/api/jobs?limit=20" | pretty_json
}

create_job() {
    local query="${1:-Test Job}"
    local email1="${2:-test1@example.com}"
    local email2="${3:-test2@example.com}"
    
    echo "Creating job: $query"
    echo "Suppliers: $email1, $email2"
    
    local response=$(curl -s -X POST "$BASE_URL/api/jobs/start" \
        -H "Content-Type: application/json" \
        -d "{
            \"chemical_query\": \"$query\",
            \"supplier_emails\": [\"$email1\", \"$email2\"]
        }")
    
    echo "$response" | pretty_json
    
    # Extract and return job ID
    echo "$response" | grep -o '"job_id": [0-9]*' | grep -o '[0-9]*' | head -1
}

get_job() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: get_job <job_id>"
        return 1
    fi
    echo "Getting job $job_id (with full drilldown)..."
    curl -s "$BASE_URL/api/jobs/$job_id" | pretty_json
}

get_job_suppliers() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: get_job_suppliers <job_id>"
        return 1
    fi
    echo "Getting suppliers for job $job_id..."
    curl -s "$BASE_URL/api/jobs/$job_id/suppliers" | pretty_json
}

get_job_insights() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: get_job_insights <job_id>"
        return 1
    fi
    echo "Getting insights for job $job_id..."
    curl -s "$BASE_URL/api/jobs/$job_id/insights" | pretty_json
}

get_supplier_emails() {
    local supplier_id="$1"
    if [ -z "$supplier_id" ]; then
        echo "Usage: get_supplier_emails <supplier_id>"
        return 1
    fi
    echo "Getting emails for supplier $supplier_id..."
    curl -s "$BASE_URL/api/suppliers/$supplier_id/emails" | pretty_json
}

# ============================================================================
# INSIGHTS & EXTRACTION
# ============================================================================

refresh_insights() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: refresh_insights <job_id>"
        return 1
    fi
    echo "Refreshing insights for job $job_id..."
    curl -s -X POST "$BASE_URL/api/jobs/$job_id/insights/refresh" \
        -H "Content-Type: application/json" | pretty_json
}

get_all_insights_by_supplier() {
    echo "Getting all insights grouped by supplier..."
    curl -s "$BASE_URL/api/insights/by-supplier" | pretty_json
}

# ============================================================================
# REMINDERS & JOB CLOSURE
# ============================================================================

send_reminder() {
    local job_id="$1"
    local supplier_id="$2"
    if [ -z "$job_id" ] || [ -z "$supplier_id" ]; then
        echo "Usage: send_reminder <job_id> <supplier_id>"
        return 1
    fi
    echo "Sending reminder for job $job_id to supplier $supplier_id..."
    curl -s -X POST "$BASE_URL/api/jobs/$job_id/suppliers/$supplier_id/send-reminder" \
        -H "Content-Type: application/json" | pretty_json
}

close_job() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: close_job <job_id>"
        return 1
    fi
    echo "Closing job $job_id..."
    curl -s -X POST "$BASE_URL/api/jobs/$job_id/close" \
        -H "Content-Type: application/json" | pretty_json
}

# ============================================================================
# STATISTICS & ANALYTICS
# ============================================================================

get_summary_stats() {
    echo "Getting overall statistics..."
    curl -s "$BASE_URL/api/stats/summary" | pretty_json
}

get_job_stats() {
    local job_id="$1"
    if [ -z "$job_id" ]; then
        echo "Usage: get_job_stats <job_id>"
        return 1
    fi
    echo "Getting statistics for job $job_id..."
    curl -s "$BASE_URL/api/stats/job/$job_id" | pretty_json
}

# ============================================================================
# WORKFLOW EXAMPLES
# ============================================================================

workflow_complete() {
    echo "========================================"
    echo "Running complete workflow example..."
    echo "========================================"
    
    # 1. Create job
    echo -e "\n[1/5] Creating job..."
    job_response=$(curl -s -X POST "$BASE_URL/api/jobs/start" \
        -H "Content-Type: application/json" \
        -d '{
            "chemical_query": "Test Workflow: 20000 MT Methanol",
            "supplier_emails": ["workflow1@example.com", "workflow2@example.com"]
        }')
    
    job_id=$(echo "$job_response" | grep -o '"job_id": [0-9]*' | grep -o '[0-9]*' | head -1)
    echo "Created job: $job_id"
    
    # 2. Get job details
    echo -e "\n[2/5] Getting job details..."
    curl -s "$BASE_URL/api/jobs/$job_id" | pretty_json | head -30
    
    # 3. Get job statistics
    echo -e "\n[3/5] Getting job statistics..."
    curl -s "$BASE_URL/api/stats/job/$job_id" | pretty_json
    
    # 4. Get insights (should be empty initially)
    echo -e "\n[4/5] Getting insights..."
    curl -s "$BASE_URL/api/jobs/$job_id/insights" | pretty_json
    
    # 5. Get overall stats
    echo -e "\n[5/5] Getting overall statistics..."
    curl -s "$BASE_URL/api/stats/summary" | pretty_json
    
    echo -e "\n========================================"
    echo "✅ Workflow complete!"
    echo "Job ID: $job_id"
    echo "========================================"
}

# ============================================================================
# HELP
# ============================================================================

help() {
    cat << 'EOF'
Crystal Supplier Email Service - API Quick Reference
====================================================

BASIC COMMANDS:
  health                      - Check API health
  get_suppliers              - List all suppliers

JOB MANAGEMENT:
  get_all_jobs               - List all jobs
  create_job "<query>" "<email1>" "<email2>"  - Create new job
  get_job <job_id>           - Get job details (full drilldown)
  close_job <job_id>         - Close a job

SUPPLIER TRACKING:
  get_job_suppliers <job_id> - Get suppliers for job
  get_supplier_emails <supplier_id> - Get all emails from supplier

INSIGHTS:
  refresh_insights <job_id>  - Trigger AI extraction
  get_job_insights <job_id>  - Get insights for job
  get_all_insights_by_supplier - Get insights grouped by supplier

REMINDERS & WORKFLOW:
  send_reminder <job_id> <supplier_id> - Send reminder email

STATISTICS:
  get_summary_stats          - Overall statistics
  get_job_stats <job_id>     - Job-specific statistics

EXAMPLES:
  workflow_complete          - Run complete workflow demo

HELP:
  help                       - Show this message

EXAMPLES:
  --------
  1. Create a job:
     $ job_id=$(create_job "20000 MT Methanol" "supplier1@ex.com" "supplier2@ex.com")
     
  2. Get job details:
     $ get_job $job_id
     
  3. Refresh insights:
     $ refresh_insights $job_id
     
  4. Send reminder:
     $ send_reminder $job_id 1
     
  5. Check statistics:
     $ get_job_stats $job_id

EOF
}

# Print help on first run if no command specified
if [ $# -eq 0 ]; then
    echo "Crystal Supplier Email Service - Quick Reference"
    echo ""
    help
fi
