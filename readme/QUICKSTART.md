# Project Summary & Deployment Guide

## Project Overview

**Crystal Supplier Email Service** is a full-stack application for automating B2B supplier communication workflows. It enables procurement teams to send Requests for Quote (RFQs) to multiple chemical suppliers simultaneously, track responses, and automatically extract pricing/logistics insights using AI.

### Key Capabilities
- 📧 **Automated RFQ Distribution**: Send personalized emails to multiple suppliers
- 📊 **Response Tracking**: Monitor supplier replies and auto-send reminders
- 🤖 **AI-Powered Insights**: Extract pricing, quantities, and delivery dates using Google Generative AI
- 💾 **Data Archival**: Automatically archive results to Google Cloud Storage
- 📈 **Dashboard**: React-based campaign management interface

---

## Quick Start Guide

### Local Development (Fastest)

```bash
# 1. Clone repository
git clone https://github.com/amitgupta1000/crystal-supplier-email-service.git
cd crystal-supplier-email-service

# 2. Start with Docker Compose
docker-compose up -d

# 3. Access services
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Database Admin: http://localhost:8080
```

### Manual Setup

**Backend:**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Production Deployment on GCP

### Architecture
```
┌─────────────────┐
│   Cloud Run     │ ← Containerized application
├─────────────────┤
│   Cloud SQL     │ ← PostgreSQL database
├─────────────────┤
│  Cloud Storage  │ ← Job archives & exports
├─────────────────┤
│   Gmail API     │ ← Email communication
└─────────────────┘
```

### Deployment Steps (3 options)

#### Option 1: Automated (Recommended)
```bash
chmod +x deploy-gcp.sh
./deploy-gcp.sh
# Follow prompts for project ID, region, database password
```

#### Option 2: Using gcloud CLI (Manual)
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions

#### Option 3: GitHub Actions CI/CD
Push to `main` branch and GitHub Actions will:
- Run tests and linting
- Build Docker image
- Push to Artifact Registry
- Deploy to Cloud Run automatically

### Estimated Setup Time: 20-30 minutes

### Monthly Costs
- **Low Traffic**: $20-40/month
- **Medium Traffic**: $60-150/month
- **High Traffic**: $150-300+/month

---

## Documentation Files

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | Complete project documentation | All users |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Step-by-step GCP deployment guide | DevOps/Cloud engineers |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local development setup | Frontend/Backend developers |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design & technical details | Architects/Technical leads |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Pre/post-deployment checklist | Release managers |

---

## Project Structure

```
crystal-supplier-email-service/
├── main.py                              # FastAPI application
├── requirements.txt                     # Python dependencies
├── Dockerfile                           # Production container
├── docker-compose.yml                   # Local development setup
├── deploy-gcp.sh                        # Automated GCP deployment
├── .env.example                         # Environment variables template
│
├── backend/
│   ├── database.py                      # SQLAlchemy models
│   ├── scheduler.py                     # APScheduler job processing
│   ├── email_utils.py                   # Gmail API integration
│   ├── gcs_utils.py                     # Google Cloud Storage
│   ├── send_requests.py                 # Email sending logic
│   └── extract_insights.py              # AI-powered extraction
│
├── frontend/
│   ├── src/App.jsx                      # Main React component
│   ├── package.json                     # Node.js dependencies
│   ├── vite.config.js                   # Vite configuration
│   └── tailwind.config.js               # Tailwind CSS config
│
└── .github/
    └── workflows/
        └── deploy.yml                   # GitHub Actions CI/CD
```

---

## Key Technologies

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **APScheduler**: Background job scheduling
- **Google Cloud**: GCS, Cloud SQL, Gmail API, Generative AI

### Frontend
- **React 19**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Lucide React**: Icon library

### Infrastructure
- **Docker**: Container technology
- **Google Cloud Run**: Serverless compute
- **Cloud SQL**: Managed PostgreSQL database
- **Cloud Storage**: Object storage for archives
- **Artifact Registry**: Docker image registry

---

## API Endpoints

### Jobs
```
GET  /api/jobs                          # List all jobs
POST /api/jobs/start                    # Create new RFQ job
GET  /api/jobs/{job_id}                 # Get job details
POST /api/jobs/{job_id}/insights/refresh # Refresh insights
```

### Suppliers
```
GET  /api/suppliers                     # List all suppliers
```

### Utilities
```
GET  /health                            # Service health check
GET  /docs                              # Swagger API documentation
```

---

## Environment Configuration

Required environment variables (see `.env.example`):

```bash
# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/sa-key.json
GOOGLE_CLOUD_PROJECT=your-project-id

# Gmail
GMAIL_IMPERSONATE_USER=noreply@yourdomain.com

# Database (SQLite for dev, PostgreSQL for prod)
DATABASE_URL=sqlite:///./jobs.db
# OR
DATABASE_URL=postgresql://user:password@host:5432/crystal_db

# Storage & AI
GCS_BUCKET_NAME=crystal-supplier-email-data
GOOGLE_GENAI_API_KEY=your-api-key
```

---

## Deployment Checklist

### Before Deployment
- [ ] All tests passing
- [ ] Code review completed
- [ ] Security scan passed
- [ ] Environment variables defined
- [ ] Database migrations tested
- [ ] Team trained on operations

### During Deployment
- [ ] Execute deployment script
- [ ] Verify Cloud Run deployment
- [ ] Test API endpoints
- [ ] Verify database connectivity
- [ ] Test email functionality

### After Deployment
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Gather user feedback
- [ ] Document any issues
- [ ] Update runbooks

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for complete checklist.

---

## Troubleshooting

### Common Issues

**Email not sending:**
- Verify Gmail API enabled
- Check service account has domain-wide delegation
- Ensure GMAIL_IMPERSONATE_USER has correct Gmail scope

**Database connection error:**
- Verify Cloud SQL instance running
- Check service account has cloudsql.client role
- Test connection: `psql $DATABASE_URL`

**API responding slowly:**
- Check Cloud Run memory allocation
- Review database query performance
- Check Cloud Logging for errors

**Frontend not loading:**
- Verify Cloud Run service URL
- Check CORS configuration
- Review browser console for errors

See [README.md](README.md#troubleshooting) for more solutions.

---

## Monitoring & Observability

### Cloud Logging
View application logs:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit=50 --format=json
```

### Cloud Monitoring
- CPU utilization
- Memory usage
- Request latency
- Error rate
- Custom dashboards

### Alerts
Set up alerts for:
- High error rate (>5%)
- High latency (p95 > 1s)
- Low success rate
- Database connection errors

---

## Disaster Recovery

### Backups
- **Database**: Automated daily Cloud SQL backups (retention: 35 days)
- **Storage**: Cloud Storage versioning enabled
- **Code**: GitHub repository

### Recovery Procedures
- **Database**: Restore from backup to new instance
- **Application**: Redeploy from previous Docker image
- **Data**: Restore from GCS versioning

### RTO/RPO
- **RTO**: 15 minutes (restore from backup)
- **RPO**: 24 hours (backup frequency)

---

## Performance Tuning

### Backend
- Connection pooling enabled
- Database indexes optimized
- Async request handling
- Compression enabled

### Frontend
- Code splitting with Vite
- Lazy loading of components
- Image optimization
- CSS minification

### Infrastructure
- Cloud Run auto-scaling (1-10 instances)
- Cloud SQL connection pooling
- CDN for static assets (optional)

---

## Security

### Data Protection
- ✅ Encryption in transit (HTTPS/TLS)
- ✅ Encryption at rest (Cloud SQL, GCS)
- ✅ Credentials in Secret Manager
- ✅ IAM least privilege

### API Security
- ✅ CORS restricted to frontend
- ✅ Rate limiting enabled
- ✅ Input validation (Pydantic)
- ✅ Error handling secure

### Audit
- ✅ Cloud Audit Logs enabled
- ✅ All access logged
- ✅ Service account key rotation
- ✅ IAM policy reviews

---

## Cost Optimization

### Reduce Costs
- Use Cloud Run committed use discounts
- Set Cloud SQL maintenance windows during off-peak
- Archive old jobs to Cloud Storage Coldline
- Implement data retention policies
- Right-size instance types

### Monitor Costs
```bash
gcloud billing accounts list
gcloud billing budgets list
```

---

## Advanced Topics

### Adding Authentication
Implement JWT or OAuth2:
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/api/suppliers")
def get_suppliers(credentials = Security(security)):
    # Validate token
    ...
```

### Multi-Region Setup
Deploy to multiple regions with failover:
- Primary: us-central1
- Failover: us-west1
- Global load balancer for routing

### CI/CD Pipeline
GitHub Actions automatically:
- Runs tests and linting
- Builds Docker image
- Pushes to Artifact Registry
- Deploys to Cloud Run

See `.github/workflows/deploy.yml`

---

## Support & Resources

### Documentation
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

### Getting Help
1. Check troubleshooting section in README.md
2. Review logs in Cloud Logging
3. Open GitHub issue with details
4. Contact development team

---

## Development Roadmap

### Next Releases
- [ ] WebSocket support for real-time updates
- [ ] Multi-language email templates
- [ ] Advanced analytics dashboard
- [ ] CRM system integration
- [ ] Supplier performance scoring
- [ ] Price history tracking

---

## Version Info

- **Current Version**: 1.0.0
- **Release Date**: May 2026
- **Status**: Production Ready
- **License**: MIT

---

## Contact & Support

- **Project Owner**: Amit Gupta
- **Repository**: github.com/amitgupta1000/crystal-supplier-email-service
- **Issue Tracker**: GitHub Issues
- **Documentation**: See docs/ directory

---

## Next Steps

1. **Choose Deployment Option**:
   - Local development: Use docker-compose
   - Production: Use deploy-gcp.sh or manual steps

2. **Configure Environment**:
   - Copy .env.example to .env
   - Fill in GCP credentials and configuration

3. **Review Documentation**:
   - README.md for overview
   - DEPLOYMENT.md for GCP setup
   - ARCHITECTURE.md for technical details

4. **Deploy & Test**:
   - Run deployment script
   - Verify all services running
   - Test API endpoints
   - Monitor logs

5. **Customize & Iterate**:
   - Update supplier data
   - Customize email templates
   - Configure monitoring alerts
   - Train team on operations

---

**Last Updated**: May 20, 2026  
**Maintainer**: Development Team  
**Status**: ✅ Production Ready
