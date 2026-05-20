# Production Deployment Checklist

Use this checklist before deploying the Crystal Supplier Email Service to production on GCP.

## Pre-Deployment

### Planning
- [ ] Define deployment date and maintenance window
- [ ] Identify rollback plan and recovery procedures
- [ ] Brief team on deployment process
- [ ] Review capacity planning and cost estimates
- [ ] Ensure stakeholder sign-off

### Code Quality
- [ ] All tests passing (backend + frontend)
- [ ] Code review completed
- [ ] Security scan passed (Trivy/SAST)
- [ ] Performance benchmarks reviewed
- [ ] No critical bugs in issue tracker

### Configuration
- [ ] Environment variables defined and validated
- [ ] Database schema migrations tested
- [ ] API keys and credentials secured in Secret Manager
- [ ] CORS policies reviewed and restricted
- [ ] Rate limiting rules configured

### GCP Setup
- [ ] GCP project created and billing enabled
- [ ] Required APIs enabled
- [ ] Service accounts created with least-privilege roles
- [ ] IAM policies reviewed and applied
- [ ] VPC and networking configured (if applicable)

### Infrastructure
- [ ] Cloud SQL instance created and tested
- [ ] Cloud Storage bucket created with versioning
- [ ] Artifact Registry repository created
- [ ] Cloud Run configuration reviewed
- [ ] Monitoring and alerting set up

### Data Preparation
- [ ] Supplier data cleaned and validated
- [ ] Email templates tested and approved
- [ ] Database migrations prepared and tested
- [ ] Data backup strategy implemented
- [ ] CSV files imported to GCS

### Documentation
- [ ] Runbook created and reviewed
- [ ] Troubleshooting guide available
- [ ] Team trained on operations
- [ ] Escalation procedures documented
- [ ] Change log prepared

## Deployment Day

### Pre-Deployment
- [ ] Announce maintenance window to users
- [ ] Create final backup of existing data
- [ ] Prepare communication channel for team
- [ ] Ensure all team members present
- [ ] Start deployment monitoring

### Deployment Steps
- [ ] Execute deploy-gcp.sh or manual steps
- [ ] Verify Cloud Run deployment status
- [ ] Test API endpoints with real data
- [ ] Verify database connectivity
- [ ] Test email sending functionality
- [ ] Test GCS archival

### Post-Deployment Verification
- [ ] Health check endpoint responds correctly
- [ ] API endpoints functioning properly
- [ ] Database queries executing correctly
- [ ] Email service sending successfully
- [ ] Frontend accessible and responsive
- [ ] Cloud Logging capturing events
- [ ] Monitoring dashboards showing data

### User Communication
- [ ] Notify users deployment successful
- [ ] Provide service URL or access instructions
- [ ] Document any UI/UX changes
- [ ] Gather initial feedback
- [ ] Monitor for user-reported issues

## Post-Deployment (24-48 Hours)

### Monitoring
- [ ] Review error rates and logs
- [ ] Check performance metrics
- [ ] Monitor database performance
- [ ] Review email delivery logs
- [ ] Verify scheduled jobs running correctly

### User Feedback
- [ ] Collect user feedback on stability
- [ ] Address any immediate issues
- [ ] Monitor for anomalies
- [ ] Verify all expected features working
- [ ] Performance within expected range

### Documentation
- [ ] Update deployment documentation
- [ ] Document any deviations from plan
- [ ] Update runbooks with lessons learned
- [ ] Create post-incident report if needed
- [ ] Archive deployment notes

## Rollback Checklist (If Needed)

### Decision to Rollback
- [ ] Issue severity assessed
- [ ] Rollback approved by stakeholders
- [ ] Rollback plan activated

### Rollback Execution
- [ ] Revert to previous Cloud Run image
- [ ] Restore database from backup if needed
- [ ] Verify previous version stability
- [ ] Notify users of rollback
- [ ] Document rollback reason

### Post-Rollback
- [ ] Monitor for issues with rollback
- [ ] Communicate status to team
- [ ] Schedule post-mortem
- [ ] Update incident report

## Long-term Maintenance

### Weekly
- [ ] Review Cloud Logging for errors
- [ ] Check Cloud Monitoring alerts
- [ ] Verify backup jobs completed
- [ ] Review resource utilization

### Monthly
- [ ] Review cost optimization opportunities
- [ ] Update dependencies if security patches available
- [ ] Test disaster recovery procedures
- [ ] Review and rotate service account keys
- [ ] Audit IAM permissions

### Quarterly
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Security audit and review
- [ ] Update documentation
- [ ] Team training on changes

## Security Checklist

- [ ] All data encrypted in transit (HTTPS/TLS)
- [ ] All data encrypted at rest
- [ ] Database credentials in Secret Manager
- [ ] Service account keys rotated
- [ ] IAM roles follow least privilege
- [ ] API authentication/authorization implemented
- [ ] CORS policies restricted
- [ ] Rate limiting enabled
- [ ] Cloud Armor policies applied (if applicable)
- [ ] Audit logging enabled
- [ ] VPC service controls configured (if applicable)
- [ ] Security alerts configured

## Performance Checklist

- [ ] Page load time < 2 seconds
- [ ] API response time < 500ms (p95)
- [ ] Database query performance optimal
- [ ] Memory usage within limits
- [ ] CPU utilization acceptable
- [ ] Connection pool configured
- [ ] Caching implemented
- [ ] CDN configured for static assets (if applicable)

## Disaster Recovery Checklist

- [ ] Database backups automated and tested
- [ ] GCS versioning enabled
- [ ] Point-in-time recovery procedures documented
- [ ] RTO (Recovery Time Objective) defined: _____ minutes
- [ ] RPO (Recovery Point Objective) defined: _____ minutes
- [ ] Disaster recovery drill scheduled: _____
- [ ] Alternate region identified (if applicable)
- [ ] Multi-region failover tested (if applicable)

## Compliance Checklist

- [ ] Data retention policies implemented
- [ ] GDPR compliance measures in place (if applicable)
- [ ] SOC 2 compliance requirements met (if applicable)
- [ ] Audit trail enabled and reviewed
- [ ] Access logs maintained
- [ ] Data deletion procedures documented
- [ ] Privacy policy updated
- [ ] Terms of service updated

## Sign-Off

- **Deployment Lead**: _________________ Date: _______
- **Technical Lead**: _________________ Date: _______
- **Security Officer**: _________________ Date: _______
- **Operations Lead**: _________________ Date: _______

## Notes

```
[Add any additional notes, issues, or observations during deployment]




```

---

**Deployment Reference:**
- Start Time: _________
- End Time: _________
- Duration: _________
- Image SHA: _________
- Issues Encountered: _________
- Resolution: _________
