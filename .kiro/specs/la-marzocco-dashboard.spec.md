---
title: La Marzocco Dashboard - Serverless Espresso Machine Monitoring
version: 2.3.0
status: completed
created: 2025-07-05
last_updated: 2025-10-31
---

# La Marzocco Dashboard - Project Summary

> Historical v2 project summary. Features, cost estimates, and deployment status below reflect the original implementation. See the [README](../../README.md) for the current dashboard and release process.

> **Note**: This is the project summary document. For detailed specifications, see:
> - [Requirements](./la-marzocco-dashboard/requirements.md) - User stories and acceptance criteria
> - [Design](./la-marzocco-dashboard/design.md) - Architecture and technical design
> - [Tasks](./la-marzocco-dashboard/tasks.md) - Implementation plan and task list

## Project Overview

A serverless web dashboard for monitoring La Marzocco espresso machines via the La Marzocco Cloud API. The project uses a GitOps deployment model with AWS CodePipeline for continuous deployment.

### Key Features
- Real-time machine status monitoring (power, temperature, water level)
- Usage statistics tracking (total shots, flushes, last activity)
- Machine settings display (auto on/off, dosing preferences)
- Maintenance alerts (descaling, cleaning needed)
- Beautiful dark theme optimized for coffee shops
- Auto-refresh every 5 minutes
- JSON API endpoint for integrations
- Mobile responsive design
- Smart CloudFront invalidation (90% cost savings)

### Technology Stack
- **Runtime**: Python 3.12
- **Cloud Provider**: AWS (Serverless architecture)
- **Deployment**: GitOps via AWS CodePipeline
- **API Client**: pylamarzocco (La Marzocco Cloud API wrapper)
- **Template Engine**: Jinja2
- **Charting**: Chart.js

## Architecture Summary

Use the maintained [runtime diagram](../../generated-diagrams/application-architecture.png), [private release diagram](../../generated-diagrams/cicd-pipeline-architecture.png), and [retained GitHub pipeline diagram](../../generated-diagrams/github-pipeline-architecture.png). Editable sources and browser previews are in the [diagram guide](../../docs/diagrams.md).

## Implementation Summary

All implementation tasks have been completed. For the detailed task breakdown, see [Tasks Document](./la-marzocco-dashboard/tasks.md).

**Completed Phases:**
- ✅ Phase 1: Core Infrastructure (3 tasks)
- ✅ Phase 2: Lambda Function Development (4 tasks)
- ✅ Phase 3: Smart CloudFront Invalidation (2 tasks)
- ✅ Phase 4: Frontend Enhancements (5 tasks)
- ✅ Phase 5: API Compatibility Updates (3 tasks)
- ✅ Phase 6: Secrets Management Consolidation (2 tasks)
- ✅ Phase 7: Documentation (4 tasks)
- ✅ Phase 8: Deployment and Testing (4 tasks)

**Total: 27 tasks completed across 8 phases**

## Current Deployment Status

### Live Resources (as of September 16, 2025)
- **Application Stack**: `la-marzocco-dashboard` (UPDATE_COMPLETE)
- **Pipeline Stack**: `la-marzocco-deployment-pipeline` (UPDATE_COMPLETE)
- **Lambda Function**: `la-marzocco-dashboard-updater` (Python 3.12, 512MB, ~27.9MB code)
- **S3 Bucket**: `la-marzocco-dashboard-exwneqtv`
- **CloudFront Distribution**: `E1CKKDNSRS9CLJ` (dp7eewdlmvfh3.cloudfront.net)
- **Dashboard URL**: https://espresso.leozh.net
- **Route53 Hosted Zone**: `leozh.net` (ZQ8T2XWSALP2Q)
- **Region**: us-west-2
- **AWS Account**: <account-id>

### Monthly Cost: ~$2.75
- Lambda: ~$0.20
- EventBridge: ~$0.09
- S3: ~$0.02
- CloudFront: ~$0.50
- CloudFront Invalidations: ~$0.05 (with smart invalidation)
- Secrets Manager: ~$0.40
- Route53: ~$0.50
- CodePipeline: ~$1.00
- CodeBuild: ~$0.05

## Future Enhancements (Not Implemented)

### Potential Features
- [ ] Multi-machine support
- [ ] Historical data storage (DynamoDB)
- [ ] Alerting via SNS/SES
- [ ] Mobile app integration
- [ ] Advanced analytics and trends
- [ ] User authentication
- [ ] Custom dashboard themes
- [ ] Export data to CSV/Excel
- [ ] Integration with other coffee equipment

### Scalability Considerations
- [ ] DynamoDB for state management
- [ ] Step Functions for orchestration
- [ ] API Gateway for REST API
- [ ] Cognito for user management
- [ ] Multi-region deployment
- [ ] Backup and disaster recovery

## Success Criteria

All success criteria have been met:

✅ **Functionality**
- Dashboard displays real-time machine data
- Auto-refresh works correctly
- Mobile responsive design functions properly
- JSON API endpoint is accessible

✅ **Performance**
- Lambda execution time < 30 seconds
- Dashboard loads in < 2 seconds
- CloudFront cache hit ratio > 80%
- Smart invalidation reduces costs by 90%

✅ **Reliability**
- 99.95% uptime (AWS managed services)
- Automatic error recovery
- Fallback data for API failures
- Comprehensive logging

✅ **Cost**
- Monthly cost < $5 (achieved: ~$2.75)
- Smart invalidation optimization implemented
- No unexpected cost spikes

✅ **Security**
- Credentials stored in Secrets Manager
- HTTPS only via CloudFront
- S3 bucket not publicly accessible
- Least privilege IAM policies

✅ **Maintainability**
- GitOps deployment model
- Comprehensive documentation
- Clear code structure
- Automated testing via pipeline

## Lessons Learned

### What Worked Well
1. **GitOps Deployment**: Automatic deployments via CodePipeline simplified operations
2. **Smart Invalidation**: Content change detection saved 90% on CloudFront costs
3. **Serverless Architecture**: Zero maintenance and automatic scaling
4. **Installation Key Auth**: More reliable than OAuth for API authentication
5. **Comprehensive Documentation**: Made project easy to understand and maintain

### Challenges Overcome
1. **API Changes**: La Marzocco API changed authentication method
   - Solution: Migrated to installation key system with S3 persistence
2. **High CloudFront Costs**: Naive invalidation was expensive
   - Solution: Implemented smart content change detection
3. **Statistics Parsing**: API enum parsing issues
   - Solution: Exception-based extraction with fallback to raw API
4. **Mobile Background**: White background on mobile devices
   - Solution: Forced brown gradient with !important declarations
5. **Duplicate Secrets**: Two secrets for same credentials
   - Solution: Consolidated to single shared secret

### Best Practices Established
1. Always use content hashing for change detection
2. Store persistent data (installation keys) in S3
3. Implement comprehensive error handling with fallbacks
4. Use Jinja2 templates for maintainable HTML generation
5. Document all deployment steps and resources
6. Monitor costs and optimize proactively
7. Use GitOps for all deployments
8. Test mobile responsiveness thoroughly

## Conclusion

The La Marzocco Dashboard project is **complete and operational**. All planned features have been implemented, tested, and deployed. The dashboard successfully monitors La Marzocco espresso machines with real-time data, provides a beautiful user interface, and operates at minimal cost (~$2.75/month) with high reliability.

The project demonstrates best practices for serverless architecture, GitOps deployment, cost optimization, and comprehensive documentation. The smart CloudFront invalidation feature alone saves ~$65-70/month, making the project highly cost-effective.

**Status**: ✅ Production Ready
**Version**: 2.3.0
**Last Updated**: September 16, 2025
