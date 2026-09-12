# La Marzocco Dashboard - Project Architecture

## Project Overview

This is a serverless AWS-based dashboard for monitoring La Marzocco espresso machines via the La Marzocco Cloud API. The project uses a GitOps deployment model with AWS CodePipeline for continuous deployment.

## Technology Stack

### Core Technologies
- **Runtime**: Python 3.12
- **Cloud Provider**: AWS (Serverless architecture)
- **Deployment**: GitOps via AWS CodePipeline
- **API Client**: pylamarzocco (La Marzocco Cloud API wrapper)

### AWS Services Used
- **Lambda**: Serverless function for data collection and HTML generation
- **S3**: Static website hosting for dashboard files
- **CloudFront**: Global CDN with SSL termination
- **EventBridge**: Scheduled triggers (every 5 minutes)
- **Secrets Manager**: Secure credential storage
- **Route53**: DNS management
- **ACM**: SSL certificate management
- **CodePipeline**: CI/CD automation
- **CodeBuild**: Lambda package building
- **CloudFormation**: Infrastructure as Code

### Python Dependencies
```
pylamarzocco==2.4.3
jinja2>=3.1.0
boto3>=1.26.0
botocore>=1.29.0
aiohttp>=3.8.0
```

## Architecture Patterns

### Serverless Event-Driven Architecture
- EventBridge triggers Lambda every 5 minutes
- Lambda collects data from La Marzocco API
- Lambda generates HTML dashboard using Jinja2 templates
- Lambda uploads HTML and JSON to S3
- CloudFront serves content globally with caching

### Smart CloudFront Invalidation
The project implements intelligent content change detection to reduce costs:
- Compares SHA256 hashes of normalized machine data
- Only invalidates CloudFront when content actually changes
- Stores content hashes in S3 `.cache/` folder
- Reduces invalidation costs by 90% (from ~$70/month to <$5/month)

### GitOps Deployment Flow
1. Developer commits code to GitHub
2. CodePipeline detects changes automatically
3. CodeBuild packages Lambda function with dependencies
4. CloudFormation updates infrastructure
5. Custom Lambda function updates the dashboard Lambda code
6. Dashboard is automatically refreshed

## Project Structure

```
la-marzocco-dashboard/
├── cloudformation/
│   ├── main.yaml                    # Application infrastructure
│   ├── pipeline.yaml                # CI/CD pipeline infrastructure
│   ├── parameters.json              # Application parameters
│   └── pipeline-parameters.json     # Pipeline parameters
├── src/
│   └── lambda_function.py           # Data collector and versioned frontend publisher
├── requirements.txt                 # Python dependencies
├── buildspec.yml                    # CodeBuild specification
├── deploy-pipeline.sh               # Pipeline deployment script
├── .env.example                     # Environment template
└── README.md                        # Comprehensive documentation
```

## Key Implementation Details

### Lambda Function Structure
The main Lambda function (`src/lambda_function.py`) contains:
- `LaMarzoccoDashboard` class with methods for:
  - Installation key management (stored in S3)
  - Credential retrieval from Secrets Manager
  - Content hashing for change detection
  - Machine data collection from API
  - HTML dashboard generation using Jinja2
  - S3 upload and CloudFront invalidation

### Authentication System
- Uses pylamarzocco's installation key system
- Installation keys are generated and stored in S3 for persistence
- Credentials stored in AWS Secrets Manager
- Automatic device registration on first use

### Data Collection
The Lambda function collects comprehensive machine data:
- Machine info (name, model, serial, firmware)
- Status (power, temperature, boilers, scale)
- Statistics (total shots, flushes, recent activity)
- Brewing settings (pre-brewing, dose configuration)
- Recent shots with extraction details
- Maintenance status and firmware updates

### HTML Dashboard
- Responsive design with mobile optimization
- Dark theme optimized for coffee shops
- Collection every 5 minutes; browser JSON refresh every minute
- Optional Matrix background with persistent settings and reduced-motion handling
- Three.js machine viewer and responsive daily-activity/shot views
- Real-time timestamp conversion to local timezone

## Deployment Configuration

### AWS Profile
This project uses the AWS profile **"leo"** for all deployments.

**Important**: The AWS profile "leo" is configured for **us-east-1** in `~/.aws/config`, but the application resources are deployed in **us-west-2**. Always specify `--region us-west-2` when running AWS CLI commands for this project.

### Environment Variables
Required in `.env` file:
- `AWS_REGION`: AWS region (us-west-2 for this deployment)
- `DOMAIN_NAME`: Custom domain for dashboard (espresso.leozh.net)
- `LAMARZOCCO_USERNAME`: La Marzocco Cloud username (stored in Secrets Manager)
- `LAMARZOCCO_PASSWORD`: La Marzocco Cloud password (stored in Secrets Manager)

### Currently Deployed Resources
- **Stack Name**: `la-marzocco-dashboard` (UPDATE_COMPLETE)
- **Pipeline Stack**: `la-marzocco-deployment-pipeline` (UPDATE_COMPLETE)
- **Lambda Function**: `la-marzocco-dashboard-updater` (Python 3.12, 512MB, ~27.9MB code)
- **S3 Bucket**: `la-marzocco-dashboard-exwneqtv`
- **CloudFront Distribution**: `E1CKKDNSRS9CLJ` (dp7eewdlmvfh3.cloudfront.net)
- **Dashboard URL**: https://espresso.leozh.net
- **Route53 Hosted Zone**: `leozh.net` (ZQ8T2XWSALP2Q)
- **Last Updated**: September 16, 2025

### Secrets Management
- La Marzocco credentials stored in Secrets Manager
- Secret name format: `{stack-name}-lamarzocco-credentials`
- Shared between pipeline and Lambda function
- GitHub token stored separately for pipeline access

## Cost Optimization

### Smart Invalidation Strategy
- Content change detection using SHA256 hashes
- Normalized data comparison (excludes timestamps)
- Selective CloudFront invalidation
- Cache storage in S3 `.cache/` folder
- 90%+ cost reduction on invalidations

### Monthly Cost Breakdown (~$2.75)
- Lambda: ~$0.20
- EventBridge: ~$0.09
- S3: ~$0.02
- CloudFront: ~$0.50
- CloudFront Invalidations: ~$0.05 (with smart invalidation)
- Secrets Manager: ~$0.40
- Route53: ~$0.50
- CodePipeline: ~$1.00
- CodeBuild: ~$0.05

## Security Best Practices

### Current Implementation
- Credentials encrypted in Secrets Manager
- HTTPS only via CloudFront and ACM
- S3 bucket not publicly accessible (CloudFront OAC)
- Lambda execution role with minimal permissions
- Least privilege IAM policies
- Secure artifact storage in CodePipeline

### IAM Roles
- Lambda execution role: S3, Secrets Manager, CloudFront access
- CodeBuild role: S3 artifacts, CloudWatch logs
- CloudFormation role: PowerUserAccess + IAM permissions
- CodePipeline role: Orchestration permissions

## Development Workflow

### Local Testing
```bash
pip install -r requirements.txt
export S3_BUCKET_NAME=your-bucket
export LAMARZOCCO_SECRET_NAME=your-secret
export CLOUDFRONT_DISTRIBUTION_ID=your-distribution
python src/lambda_function.py
```

### GitOps Deployment
```bash
git add .
git commit -m "Description"
git push origin main
# Pipeline automatically deploys changes
```

### Manual Pipeline Deployment
```bash
export AWS_PROFILE=leo
export AWS_REGION=us-west-2
./deploy-pipeline.sh
```

## Monitoring and Debugging

### CloudWatch Logs
- Lambda logs: `/aws/lambda/la-marzocco-dashboard-updater`
- CodeBuild logs: `/aws/codebuild/la-marzocco-deployment-pipeline-build`

### Useful Commands
```bash
# View Lambda logs
aws logs tail /aws/lambda/la-marzocco-dashboard-updater --follow

# Test Lambda function
aws lambda invoke --function-name la-marzocco-dashboard-updater response.json

# Check pipeline status
aws codepipeline get-pipeline-state --name la-marzocco-deployment-pipeline-pipeline

# View stack resources
aws cloudformation list-stack-resources --stack-name la-marzocco-dashboard
```

## Important Notes

### AWS Profile and Region Usage
- **Always use AWS profile "leo"** for this project
- Set via: `export AWS_PROFILE=leo`
- Or per-command: `AWS_PROFILE=leo aws ...`
- **CRITICAL**: Always specify `--region us-west-2` for this project
- The profile defaults to us-east-1, but resources are in us-west-2
- Example: `AWS_PROFILE=leo aws lambda list-functions --region us-west-2`

### GitOps Pipeline
- All deployments should go through the CodePipeline
- Direct manual deployments are discouraged
- Pipeline ensures consistent, auditable deployments

### Lambda Package Size
- Lambda deployment package includes all dependencies
- CodeBuild creates the package with `pip install -t`
- Package is zipped and uploaded via custom Lambda function
- Memory size increased to 512MB to handle large packages

### CloudFormation Custom Resources
- Random suffix generator for unique resource names
- Hosted zone lookup for Route53
- ACM certificate manager (us-east-1 for CloudFront)
- All use Lambda-backed custom resources

## Current Deployment Status

### Live Resources (as of verification)
The application is **fully deployed and operational** in AWS:

**Application Stack** (`la-marzocco-dashboard`):
- Status: UPDATE_COMPLETE
- Lambda Function: `la-marzocco-dashboard-updater` (Python 3.12, 512MB RAM, 300s timeout)
- Lambda Code Size: 27.9 MB (includes all dependencies)
- S3 Bucket: `la-marzocco-dashboard-exwneqtv`
- CloudFront Distribution: `E1CKKDNSRS9CLJ`
- CloudFront Domain: `dp7eewdlmvfh3.cloudfront.net`
- Custom Domain: `espresso.leozh.net` (A record pointing to CloudFront)
- EventBridge Rule: `la-marzocco-dashboard-schedule` (triggers every 5 minutes)

**Pipeline Stack** (`la-marzocco-deployment-pipeline`):
- Status: UPDATE_COMPLETE
- Pipeline Name: `la-marzocco-deployment-pipeline-pipeline`
- Last Updated: September 16, 2025
- CodeBuild Project: Active
- GitHub Connection: CodeStar Connections (authorized)

**Supporting Lambda Functions**:
- `la-marzocco-dashboard-certificate-manager` (ACM certificate management)
- `la-marzocco-dashboard-hosted-zone-lookup` (Route53 zone lookup)
- `la-marzocco-dashboard-random-suffix-generator` (unique resource names)
- `la-marzocco-deployment-pipeline-update-lambda` (Lambda code updates)

**Secrets Manager**:
- Secret ARN: `arn:aws:secretsmanager:us-west-2:<account-id>:secret:la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5`
- Contains La Marzocco API credentials (username/password)

**Route53**:
- Hosted Zone: `leozh.net` (ZQ8T2XWSALP2Q)
- A Record: `espresso.leozh.net` → CloudFront distribution
- CNAME Record: ACM validation record for SSL certificate

### Verification Commands
```bash
# Check application stack
AWS_PROFILE=leo aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --region us-west-2

# Check Lambda function
AWS_PROFILE=leo aws lambda get-function \
  --function-name la-marzocco-dashboard-updater \
  --region us-west-2

# Check pipeline status
AWS_PROFILE=leo aws codepipeline get-pipeline-state \
  --name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2

# Test dashboard
curl -I https://espresso.leozh.net
```

## Future Considerations

### Potential Enhancements
- Multi-machine support
- Historical data storage (DynamoDB)
- Alerting via SNS/SES
- Mobile app integration
- Advanced analytics and trends
- User authentication

### Scalability
- Current architecture handles single machine well
- For multiple machines, consider:
  - DynamoDB for state management
  - Step Functions for orchestration
  - API Gateway for REST API
  - Cognito for user management

## Frontend v3

`web/` contains the production frontend and vendored Three.js modules. Bundle it alongside the Lambda module. `frontend_bundle()` computes an asset content hash; Lambda publishes all assets before data and HTML, caching a completion marker in S3. Use `tools/preview.py` for offline rendering from an existing data snapshot. The current release uses private GitLab source and AWS CodeBuild with a direct Lambda update; the GitHub repository remains blocked pending approval.
