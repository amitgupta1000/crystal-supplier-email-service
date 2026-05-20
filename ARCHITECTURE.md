# Crystal Supplier Email Service - Architecture Guide

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Users / Suppliers                              │
│                    (Browser / Email Clients)                         │
└────────────┬────────────────────────────────────┬────────────────────┘
             │                                    │
             │ HTTPS                             │ Email
             ▼                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                             │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Cloud Run (Managed Container)             │  │
│  │                                                              │  │
│  │  ┌─────────────────┐         ┌────────────────────────┐   │  │
│  │  │  React Frontend │─────┬───▶│  FastAPI Backend       │   │  │
│  │  │  (Vite Build)   │     │   │  (/api endpoints)      │   │  │
│  │  └─────────────────┘     │   │                        │   │  │
│  │                          │   │  - Job Management      │   │  │
│  │  Port: 3000              │   │  - Supplier Tracking   │   │  │
│  │  (Reverse Proxied)       │   │  - Background Tasks    │   │  │
│  │                          │   │                        │   │  │
│  │                          │   └──────────┬─────────────┘   │  │
│  │                          │              │                 │  │
│  │                          │              ▼                 │  │
│  │                          │   ┌──────────────────┐          │  │
│  │                          └───▶│  APScheduler     │         │  │
│  │                              │  Job Processing  │         │  │
│  │                              └──────────────────┘         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                 │                    │                    │
│         │                 │                    │                    │
│    ┌────▼──────┐  ┌───────▼──────┐   ┌────────▼────────┐          │
│    │ Cloud SQL │  │ Cloud Storage│   │   Gmail API     │          │
│    │PostgreSQL │  │      (GCS)    │   │  Domain Delegation        │
│    │          │  │              │   │                │          │
│    │- Jobs    │  │ - Job Results │   │ - Send Emails  │          │
│    │- Suppliers│ │ - Exports     │   │ - Read Replies │          │
│    │- Insights│  │ - Archives    │   │                │          │
│    └────┬──────┘  └───────┬──────┘   └────────┬────────┘          │
│         │                 │                    │                    │
│         └─────────────────┼────────────────────┘                    │
│                           │                                         │
│               ┌───────────▼──────────┐                             │
│               │  Service Account    │                             │
│               │  (IAM/Permissions)  │                             │
│               │                     │                             │
│               │ - Cloud SQL Access  │                             │
│               │ - GCS Permissions   │                             │
│               │ - Gmail Delegation  │                             │
│               └─────────────────────┘                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend (React + Vite)
- **Language**: JavaScript/JSX
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + PostCSS
- **UI Components**: Lucide React
- **Features**:
  - Multi-column campaign manager interface
  - Real-time job status updates
  - Supplier response tracking
  - Insight visualization

### Backend (FastAPI)
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Server**: Uvicorn
- **ORM**: SQLAlchemy
- **Features**:
  - RESTful API endpoints
  - CORS middleware
  - Async request handling
  - Database session management

### Database (Cloud SQL - PostgreSQL)
- **Engine**: PostgreSQL 15
- **Tables**:
  - `jobs` - RFQ job records
  - `job_supplier_states` - Supplier response tracking
  - `insights` - Extracted pricing/logistics data
- **Features**:
  - ACID compliance
  - Automatic backups
  - Point-in-time recovery
  - Connection pooling

### Cloud Storage (Google Cloud Storage)
- **Bucket**: `crystal-supplier-email-data`
- **Contents**:
  - Job summaries (JSON)
  - Extracted insights (CSV)
  - Email archives
  - Configuration files
- **Features**:
  - Versioning enabled
  - Lifecycle policies
  - Access logging

### Background Scheduler (APScheduler)
- **Type**: BackgroundScheduler
- **Interval**: Every minute (configurable)
- **Tasks**:
  1. Process active jobs
  2. Send reminder emails at T+24h
  3. Close and archive jobs at T+48h
  4. Handle job status updates

### Email Service (Gmail API)
- **Integration**: Domain-wide delegation
- **Permissions**: 
  - `https://www.googleapis.com/auth/gmail.modify`
- **Features**:
  - Send personalized RFQ emails
  - Parse supplier replies
  - Attach quote documents

### AI Service (Google Generative AI)
- **Service**: Gemini API
- **Use Cases**:
  - Extract insights from emails
  - Parse pricing information
  - Identify key contact persons
  - Classify responses

## Data Flow

### New Job Creation
```
User Browser
    │
    ├─▶ POST /api/jobs/start
    │
    ▼
FastAPI Backend
    │
    ├─▶ Create Job record (DB)
    ├─▶ Create JobSupplierState records (DB)
    ├─▶ Start background task queue
    │
    ▼
Response
    │
    └─▶ Return job_id + status (200 OK)
```

### Scheduled Job Processing
```
APScheduler (Every 1 minute)
    │
    ├─▶ Query active jobs
    │
    ├─▶ For each job:
    │   │
    │   ├─▶ Check time since creation
    │   │
    │   ├─▶ If T+24h:
    │   │   ├─▶ Send reminder emails
    │   │   └─▶ Update reminders_sent flag
    │   │
    │   ├─▶ If T+48h:
    │   │   ├─▶ Extract insights
    │   │   ├─▶ Archive to GCS
    │   │   └─▶ Update job status to "closed"
    │   │
    │   └─▶ Commit DB changes
    │
    └─▶ Log completion
```

### Email Reply Processing
```
Supplier Email
    │
    ▼
Gmail API
    │
    ▼
Extract Insights (Generative AI)
    │
    ├─▶ Parse email content
    ├─▶ Extract structured data
    │   ├─ Supplier name
    │   ├─ Contact person
    │   ├─ Product details
    │   ├─ Pricing
    │   └─ Delivery date
    │
    ▼
Store in Database
    │
    ├─▶ Update JobSupplierState (replied = true)
    ├─▶ Insert Insight record
    │
    ▼
Available in Frontend/Reports
```

## Deployment Architecture

### Development Environment
```
Local Machine
├─ Docker Desktop
├─ docker-compose.yml
│  ├─ Backend (uvicorn)
│  ├─ Frontend (Vite)
│  ├─ PostgreSQL (Docker)
│  └─ Adminer (Web UI)
└─ sa-key.json (optional)
```

### Production Environment
```
Google Cloud Platform
│
├─ Cloud Run (Managed)
│  ├─ Frontend (Static)
│  └─ Backend (API)
│
├─ Cloud SQL (PostgreSQL)
│  └─ Database replicas
│
├─ Cloud Storage
│  └─ Job archives
│
├─ Service Account
│  └─ IAM permissions
│
├─ Cloud Monitoring
│  └─ Metrics & Logs
│
├─ Secret Manager
│  └─ Credentials
│
└─ Cloud Scheduler (Optional)
   └─ Periodic jobs
```

## Scalability Considerations

### Horizontal Scaling
- **Cloud Run**: Auto-scales based on requests
  - Min instances: 1
  - Max instances: 10 (configurable)
  - CPU: 2 cores
  - Memory: 2GB (adjustable)

### Vertical Scaling
- **Cloud SQL**: Upgrade instance tier
  - Start: db-f1-micro ($10-15/month)
  - Mid: db-n1-standard-1 ($50-100/month)
  - High: db-n1-highmem-4 ($200+/month)

### Database Scaling
- **Connection Pooling**: SQLAlchemy + pgBouncer
- **Read Replicas**: Cloud SQL read replicas
- **Caching**: Redis for frequently accessed data

## Security Architecture

### Network Security
- **HTTPS/TLS**: All traffic encrypted
- **VPC**: Service isolation (optional)
- **Cloud Armor**: DDoS protection (optional)

### Identity & Access
- **Service Accounts**: Least privilege IAM roles
- **OAuth 2.0**: Gmail API authentication
- **Domain-Wide Delegation**: Service account impersonation

### Data Security
- **Encryption at Rest**: Cloud SQL + GCS
- **Encryption in Transit**: TLS 1.3+
- **Secret Manager**: Credential storage
- **Audit Logging**: All actions logged

### API Security
- **CORS**: Restricted to frontend domain
- **Rate Limiting**: Prevent abuse
- **Authentication**: JWT tokens (future enhancement)
- **Input Validation**: Pydantic models

## Reliability & High Availability

### Fault Tolerance
- **Cloud Run Auto-restart**: Unhealthy containers restarted
- **Database Backups**: Automated daily backups
- **Point-in-Time Recovery**: Up to 35 days retention

### Monitoring & Alerting
- **Cloud Logging**: All application logs
- **Cloud Monitoring**: Metrics and dashboards
- **Alerts**: Error rate, latency, resource usage

### Disaster Recovery
- **RTO**: 15 minutes (restore from backup)
- **RPO**: 24 hours (backup frequency)
- **Multi-region**: Can deploy to alternate region

## Performance Optimization

### Frontend
- **Code Splitting**: Vite automatic chunking
- **Lazy Loading**: React.lazy for components
- **Image Optimization**: WebP format
- **Caching**: Browser cache headers

### Backend
- **Database Indexing**: Indexes on frequently queried columns
- **Query Optimization**: SQLAlchemy with eager loading
- **Connection Pooling**: Reuse database connections
- **Async Operations**: Non-blocking I/O

### Infrastructure
- **Cloud CDN**: Static assets caching (optional)
- **Auto-scaling**: Handle traffic spikes
- **Load Balancing**: Distribute across instances

## Cost Optimization

### Breakdown (Monthly Estimate - Low Traffic)
- **Cloud Run**: $5-20 (compute + requests)
- **Cloud SQL**: $10-15 (db-f1-micro)
- **Cloud Storage**: $1-5 (storage + operations)
- **Total**: ~$20-40/month

### Cost Reduction Strategies
- Use Cloud Run committed use discounts
- Enable Cloud SQL on-demand pricing
- Archive old jobs to Cloud Storage
- Use Cloud Storage Nearline/Coldline for archives
- Implement data retention policies

## Technology Stack Summary

| Layer | Component | Technology |
|-------|-----------|------------|
| **Frontend** | Web UI | React 19, Vite, Tailwind CSS |
| **Backend** | API Server | FastAPI, Uvicorn |
| **Background** | Job Scheduler | APScheduler |
| **Database** | Persistence | PostgreSQL (Cloud SQL) |
| **Storage** | Archives | Google Cloud Storage |
| **Email** | Communication | Gmail API |
| **AI** | Insights | Google Generative AI |
| **Infrastructure** | Hosting | Google Cloud Run |
| **Container** | Deployment | Docker, Artifact Registry |
| **IaC** | Automation | gcloud CLI, scripts |

## Key Metrics & KPIs

### Performance Metrics
- **API Response Time**: < 500ms (p95)
- **Page Load Time**: < 2 seconds
- **Database Query Time**: < 100ms (p95)
- **Error Rate**: < 0.1%

### Business Metrics
- **Jobs Completed**: Tracks RFQ campaigns
- **Supplier Response Rate**: % who replied
- **Average Response Time**: Hours to reply
- **Cost per Job**: Operations cost

### Infrastructure Metrics
- **CPU Utilization**: Target: 50-70%
- **Memory Usage**: Target: 60-80%
- **Database Connections**: Monitor pool usage
- **Storage Growth**: Track data accumulation

## Future Enhancements

### Near Term (3-6 months)
- [ ] WebSocket for real-time updates
- [ ] Advanced search and filtering
- [ ] Batch email operations
- [ ] Export to Excel/PDF

### Medium Term (6-12 months)
- [ ] Multi-language support
- [ ] CRM integration (Salesforce/Pipedrive)
- [ ] Price tracking over time
- [ ] Supplier rating system
- [ ] A/B testing for email templates

### Long Term (12+ months)
- [ ] Machine learning for supplier matching
- [ ] Predictive pricing models
- [ ] Automated negotiation workflows
- [ ] Blockchain for contract management
- [ ] Mobile app (iOS/Android)

---

**Last Updated**: May 2026
**Version**: 1.0
**Architecture Review Date**: _____
