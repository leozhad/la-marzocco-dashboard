# La Marzocco Dashboard - Deployed Resources Reference

> Historical resource snapshot: identifiers may still be useful, but statuses, package sizes, costs, and release dates below are not current verification. Use the [README deployment reference](../../README.md#deployment-reference) and [release guide](../../docs/deployment.md). Most resources run in us-west-2; the CloudFront ACM certificate is in us-east-1 and DNS/CDN services are global.

## Quick Reference

This document contains the actual deployed resource identifiers for quick reference when working with the live system.

## ⚠️ Region Notice

**All resources are deployed in `us-west-2`**, even though the AWS profile "leo" defaults to `us-east-1`. Always specify `--region us-west-2` in AWS CLI commands.

## Live Application Resources

### CloudFormation Stacks
- **Application Stack**: `la-marzocco-dashboard` (UPDATE_COMPLETE)
- **Pipeline Stack**: `la-marzocco-deployment-pipeline` (UPDATE_COMPLETE)
- **Region**: us-west-2
- **AWS Account**: <account-id>

### Lambda Functions

#### Main Application Function
- **Name**: `la-marzocco-dashboard-updater`
- **ARN**: `arn:aws:lambda:us-west-2:<account-id>:function:la-marzocco-dashboard-updater`
- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 300 seconds (5 minutes)
- **Code Size**: ~27.9 MB
- **Last Modified**: September 16, 2025
- **Log Group**: `/aws/lambda/la-marzocco-dashboard-updater`

#### Supporting Lambda Functions
- `la-marzocco-dashboard-certificate-manager` - ACM certificate management
- `la-marzocco-dashboard-hosted-zone-lookup` - Route53 zone lookup
- `la-marzocco-dashboard-random-suffix-generator` - Unique resource names
- `la-marzocco-deployment-pipeline-update-lambda` - Lambda code updates

### S3 Bucket
- **Name**: `la-marzocco-dashboard-exwneqtv`
- **Purpose**: Static website hosting for dashboard HTML and JSON
- **Access**: Private (CloudFront OAC only)
- **Cache Folder**: `.cache/` (stores content hashes and installation keys)

### CloudFront Distribution
- **Distribution ID**: `E1CKKDNSRS9CLJ`
- **Domain Name**: `dp7eewdlmvfh3.cloudfront.net`
- **Custom Domain**: `espresso.leozh.net`
- **Origin**: S3 bucket `la-marzocco-dashboard-exwneqtv`
- **SSL Certificate**: ACM certificate (us-east-1)
- **Cache Behaviors**:
  - `/` - Default TTL: 300 seconds (5 minutes)
  - `/data.json` - TTL: 60 seconds (1 minute)

### Route53
- **Hosted Zone**: `leozh.net`
- **Hosted Zone ID**: `ZQ8T2XWSALP2Q`
- **A Record**: `espresso.leozh.net` → CloudFront distribution (Alias)
- **CNAME Record**: `_c0932ee6b098bc52c3c2a8be92909b1f.espresso.leozh.net` → ACM validation

### EventBridge
- **Rule Name**: `la-marzocco-dashboard-schedule`
- **Schedule**: `rate(5 minutes)`
- **Target**: Lambda function `la-marzocco-dashboard-updater`
- **State**: ENABLED

### Secrets Manager
- **Secret Name**: `la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5`
- **Full ARN**: `arn:aws:secretsmanager:us-west-2:<account-id>:secret:la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5`
- **Purpose**: Stores La Marzocco API credentials (username/password)
- **Shared**: Used by both pipeline and Lambda function

### CodePipeline
- **Pipeline Name**: `la-marzocco-deployment-pipeline-pipeline`
- **Last Updated**: September 16, 2025
- **Stages**:
  1. Source (GitHub via CodeStar Connection)
  2. Build (CodeBuild)
  3. Deploy (CloudFormation + Lambda update)

### CodeBuild
- **Project Name**: `la-marzocco-deployment-pipeline-build`
- **Log Group**: `/aws/codebuild/la-marzocco-deployment-pipeline-build`
- **Build Spec**: `buildspec.yml` in repository
- **Runtime**: Python 3.12

### IAM Roles
- **Lambda Execution**: `la-marzocco-dashboard-lambda-role`
- **CodeBuild**: `la-marzocco-deployment-pipeline-codebuild-role`
- **CodePipeline**: `la-marzocco-deployment-pipeline-codepipeline-role`
- **CloudFormation**: `la-marzocco-deployment-pipeline-cloudformation-role`

## Quick Access Commands

### View Dashboard
```bash
# Open in browser
open https://espresso.leozh.net

# Check HTTP status
curl -I https://espresso.leozh.net
```

### Lambda Function
```bash
# Invoke function manually
AWS_PROFILE=leo aws lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --region us-west-2 \
  response.json

# View recent logs
AWS_PROFILE=leo aws logs tail \
  /aws/lambda/la-marzocco-dashboard-updater \
  --follow \
  --region us-west-2

# Get function details
AWS_PROFILE=leo aws lambda get-function \
  --function-name la-marzocco-dashboard-updater \
  --region us-west-2
```

### S3 Bucket
```bash
# List bucket contents
AWS_PROFILE=leo aws s3 ls s3://la-marzocco-dashboard-exwneqtv/ \
  --region us-west-2

# View cache folder
AWS_PROFILE=leo aws s3 ls s3://la-marzocco-dashboard-exwneqtv/.cache/ \
  --region us-west-2

# Download dashboard HTML
AWS_PROFILE=leo aws s3 cp \
  s3://la-marzocco-dashboard-exwneqtv/index.html \
  ./index.html \
  --region us-west-2
```

### CloudFront
```bash
# Get distribution details
AWS_PROFILE=leo aws cloudfront get-distribution \
  --id E1CKKDNSRS9CLJ

# Create invalidation (if needed)
AWS_PROFILE=leo aws cloudfront create-invalidation \
  --distribution-id E1CKKDNSRS9CLJ \
  --paths "/*"

# List recent invalidations
AWS_PROFILE=leo aws cloudfront list-invalidations \
  --distribution-id E1CKKDNSRS9CLJ
```

### Pipeline
```bash
# Get pipeline state
AWS_PROFILE=leo aws codepipeline get-pipeline-state \
  --name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2

# List recent executions
AWS_PROFILE=leo aws codepipeline list-pipeline-executions \
  --pipeline-name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2 \
  --max-items 5

# Start pipeline manually
AWS_PROFILE=leo aws codepipeline start-pipeline-execution \
  --name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2
```

### Secrets Manager
```bash
# Get secret value (credentials)
AWS_PROFILE=leo aws secretsmanager get-secret-value \
  --secret-id la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5 \
  --region us-west-2 \
  --query SecretString \
  --output text | jq .

# Update credentials
AWS_PROFILE=leo aws secretsmanager update-secret \
  --secret-id la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5 \
  --secret-string '{"username":"your-email","password":"your-password"}' \
  --region us-west-2
```

### CloudFormation
```bash
# View application stack
AWS_PROFILE=leo aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --region us-west-2

# View stack outputs
AWS_PROFILE=leo aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --region us-west-2 \
  --query 'Stacks[0].Outputs'

# View stack resources
AWS_PROFILE=leo aws cloudformation list-stack-resources \
  --stack-name la-marzocco-dashboard \
  --region us-west-2

# View stack events (for troubleshooting)
AWS_PROFILE=leo aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  --region us-west-2 \
  --max-items 20
```

### EventBridge
```bash
# View rule details
AWS_PROFILE=leo aws events describe-rule \
  --name la-marzocco-dashboard-schedule \
  --region us-west-2

# List targets
AWS_PROFILE=leo aws events list-targets-by-rule \
  --rule la-marzocco-dashboard-schedule \
  --region us-west-2

# Disable rule (stop automatic updates)
AWS_PROFILE=leo aws events disable-rule \
  --name la-marzocco-dashboard-schedule \
  --region us-west-2

# Enable rule (resume automatic updates)
AWS_PROFILE=leo aws events enable-rule \
  --name la-marzocco-dashboard-schedule \
  --region us-west-2
```

## Monitoring and Logs

### CloudWatch Log Groups
- `/aws/lambda/la-marzocco-dashboard-updater` - Main application logs
- `/aws/lambda/la-marzocco-dashboard-certificate-manager` - Certificate management
- `/aws/lambda/la-marzocco-dashboard-hosted-zone-lookup` - DNS lookup
- `/aws/codebuild/la-marzocco-deployment-pipeline-build` - Build logs

### View Logs
```bash
# Tail Lambda logs in real-time
AWS_PROFILE=leo aws logs tail \
  /aws/lambda/la-marzocco-dashboard-updater \
  --follow \
  --region us-west-2

# Filter for errors
AWS_PROFILE=leo aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "ERROR" \
  --region us-west-2

# Filter for invalidation decisions
AWS_PROFILE=leo aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "invalidation" \
  --region us-west-2

# View CodeBuild logs
AWS_PROFILE=leo aws logs tail \
  /aws/codebuild/la-marzocco-deployment-pipeline-build \
  --follow \
  --region us-west-2
```

## Cost Monitoring

### View Current Costs
```bash
# Get cost for Lambda function (last 30 days)
AWS_PROFILE=leo aws ce get-cost-and-usage \
  --time-period Start=2025-09-01,End=2025-09-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://filter.json \
  --region us-east-1

# Note: Cost Explorer API is only available in us-east-1
```

### Expected Monthly Costs
- Lambda: ~$0.20
- EventBridge: ~$0.09
- S3: ~$0.02
- CloudFront: ~$0.50
- CloudFront Invalidations: ~$0.05 (with smart invalidation)
- Secrets Manager: ~$0.40
- Route53: ~$0.50
- CodePipeline: ~$1.00
- CodeBuild: ~$0.05
- **Total**: ~$2.81/month

## Troubleshooting Quick Reference

### Dashboard Not Loading
1. Check CloudFront distribution status
2. Verify S3 bucket has content
3. Check Route53 DNS records
4. Test Lambda function manually
5. Review CloudWatch logs

### Lambda Function Errors
1. Check environment variables are set
2. Verify Secrets Manager access
3. Check S3 bucket permissions
4. Verify CloudFront invalidation permissions
5. Review API authentication

### Pipeline Failures
1. Check GitHub connection status
2. Review CodeBuild logs
3. Verify CloudFormation events
4. Check IAM permissions
5. Validate template syntax

## Security Notes

- All credentials stored in Secrets Manager (encrypted at rest)
- S3 bucket not publicly accessible (CloudFront OAC only)
- HTTPS enforced via CloudFront
- Lambda execution role follows least privilege
- IAM roles scoped to specific resources
- CloudTrail enabled for audit logging

## Backup and Recovery

### Important Data to Backup
- `.env` file (configuration)
- CloudFormation templates
- Lambda function code (in Git)
- Secrets Manager credentials (securely)

### Recovery Procedure
1. Restore Git repository
2. Deploy pipeline stack: `./deploy-pipeline.sh`
3. Update Secrets Manager credentials
4. Push to GitHub to trigger deployment
5. Verify dashboard functionality

## Last Verified
- **Date**: October 30, 2025
- **Stack Status**: UPDATE_COMPLETE
- **Dashboard Status**: Operational
- **Last Lambda Update**: September 16, 2025
