# La Marzocco Dashboard - Deployment Guide

## ⚠️ CRITICAL: Region Configuration

**The AWS profile "leo" defaults to `us-east-1`, but ALL project resources are deployed in `us-west-2`.**

You MUST always specify `--region us-west-2` when running AWS CLI commands for this project, or commands will fail to find resources.

```bash
# CORRECT - Always specify region
AWS_PROFILE=leo aws lambda list-functions --region us-west-2

# WRONG - Will look in us-east-1 and find nothing
AWS_PROFILE=leo aws lambda list-functions
```

## AWS Profile Configuration

### Required Profile
This project **MUST** use the AWS profile named **"leo"** for all deployments and AWS operations.

### Setting the Profile
```bash
# Set for current session
export AWS_PROFILE=leo

# Verify profile is set
echo $AWS_PROFILE

# Or use per-command
AWS_PROFILE=leo aws cloudformation describe-stacks
```

### Profile Configuration
Ensure your `~/.aws/credentials` and `~/.aws/config` files contain the "leo" profile:

```ini
# ~/.aws/credentials
[leo]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

# ~/.aws/config
[profile leo]
region = us-east-1  # Note: Profile default is us-east-1
output = json
```

**IMPORTANT**: The AWS profile "leo" has a default region of `us-east-1` in the config file, but this project's resources are deployed in **us-west-2**. You MUST always specify `--region us-west-2` when running AWS CLI commands for this project, or the commands will fail to find resources.

## GitOps Deployment Model

### Primary Deployment Method
This project uses **GitOps** for all deployments. Changes are deployed automatically through the AWS CodePipeline when code is pushed to GitHub.

### Deployment Flow
1. Developer makes changes locally
2. Commits changes to Git
3. Pushes to GitHub main branch
4. CodePipeline automatically detects changes
5. CodeBuild packages Lambda function
6. CloudFormation updates infrastructure
7. Custom Lambda updates dashboard function
8. Dashboard is live with new changes

### GitOps Commands
```bash
# Make changes to code
vim src/lambda_function.py

# Commit changes
git add .
git commit -m "Update Lambda function with new feature"

# Deploy via GitOps
git push origin main

# Monitor deployment
aws codepipeline get-pipeline-state \
  --name la-marzocco-deployment-pipeline-pipeline \
  --profile leo \
  --region us-west-2
```

## Pipeline Deployment

### Initial Pipeline Setup
The CodePipeline must be deployed once before GitOps can work.

```bash
# Set AWS profile
export AWS_PROFILE=leo
export AWS_REGION=us-west-2

# Ensure .env file exists with configuration
cp .env.example .env
# Edit .env with your values

# Deploy the pipeline
./deploy-pipeline.sh
```

### Pipeline Stack Details
- **Stack Name**: `la-marzocco-deployment-pipeline`
- **Region**: `us-west-2`
- **Template**: `cloudformation/pipeline.yaml`
- **Parameters**: `cloudformation/pipeline-parameters.json`

### Pipeline Components
1. **Source Stage**: GitHub repository via CodeStar Connection
2. **Build Stage**: CodeBuild packages Lambda function
3. **Deploy Stage**: 
   - Creates CloudFormation change set
   - Executes change set
   - Updates Lambda function code

## Secrets Management

### La Marzocco Credentials
Credentials are stored in AWS Secrets Manager and shared between pipeline and Lambda.

**Current Secret ARN**: `arn:aws:secretsmanager:us-west-2:<account-id>:secret:la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5`

```bash
# Find the secret name
aws secretsmanager list-secrets \
  --region us-west-2 \
  --profile leo \
  --query 'SecretList[?contains(Name, `lamarzocco-credentials`)].Name' \
  --output text

# Update credentials (use the actual secret name from above)
aws secretsmanager update-secret \
  --secret-id la-marzocco-deployment-pipeline-lamarzocco-credentials-wmmEA5 \
  --secret-string '{"username":"your-email@example.com","password":"your-password"}' \
  --region us-west-2 \
  --profile leo
```

### GitHub Connection
The pipeline uses AWS CodeStar Connections for GitHub integration.

**Important**: After initial pipeline deployment, you must manually activate the GitHub connection:
1. Go to AWS Console → Developer Tools → Connections
2. Find the connection named "la-marzocco-github"
3. Click "Update pending connection"
4. Authorize GitHub access

## Application Stack Deployment

### Automatic Deployment
The application stack is deployed automatically by the CodePipeline. You should **NOT** deploy it manually.

### Stack Details
- **Stack Name**: `la-marzocco-dashboard`
- **Region**: `us-west-2`
- **Template**: `cloudformation/main.yaml`
- **Parameters**: `cloudformation/parameters.json`

### Stack Resources
- Lambda function for dashboard updates
- S3 bucket for static hosting
- CloudFront distribution with SSL
- Route53 DNS records
- EventBridge rule for scheduling
- IAM roles and policies
- CloudWatch log groups

## Environment Configuration

### Required Environment Variables
Create a `.env` file with the following:

```bash
# AWS Configuration
AWS_REGION=us-west-2

# Domain Configuration
DOMAIN_NAME=espresso.leozh.net

# La Marzocco Credentials (for initial setup only)
LAMARZOCCO_USERNAME=your-email@example.com
LAMARZOCCO_PASSWORD=your-password
```

### Lambda Environment Variables
Set automatically by CloudFormation:
- `S3_BUCKET_NAME`: S3 bucket for dashboard files
- `LAMARZOCCO_SECRET_NAME`: Secrets Manager secret name
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution ID

## Deployment Verification

### Check Pipeline Status
```bash
# View pipeline state
aws codepipeline get-pipeline-state \
  --name la-marzocco-deployment-pipeline-pipeline \
  --profile leo \
  --region us-west-2

# View pipeline executions
aws codepipeline list-pipeline-executions \
  --pipeline-name la-marzocco-deployment-pipeline-pipeline \
  --profile leo \
  --region us-west-2 \
  --max-items 5
```

### Check Application Stack
```bash
# View stack status
aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2

# View stack resources
aws cloudformation list-stack-resources \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2
```

### Test Lambda Function
```bash
# Invoke Lambda function
aws lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --payload '{}' \
  --profile leo \
  --region us-west-2 \
  response.json

# View response
cat response.json | jq .
```

### Check Dashboard
```bash
# Get dashboard URL
aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
  --output text

# Test dashboard (should return 200)
curl -I https://espresso.leozh.net
```

## Monitoring Deployments

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/la-marzocco-dashboard-updater \
  --follow \
  --profile leo \
  --region us-west-2

# View CodeBuild logs
aws logs tail /aws/codebuild/la-marzocco-deployment-pipeline-build \
  --follow \
  --profile leo \
  --region us-west-2

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "ERROR" \
  --profile leo \
  --region us-west-2
```

### Pipeline Monitoring
```bash
# Get pipeline URL
aws cloudformation describe-stacks \
  --stack-name la-marzocco-deployment-pipeline \
  --profile leo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`PipelineUrl`].OutputValue' \
  --output text
```

## Troubleshooting Deployments

### Pipeline Failures

#### Source Stage Failure
- **Cause**: GitHub connection not authorized
- **Fix**: Activate connection in AWS Console → Developer Tools → Connections

#### Build Stage Failure
```bash
# Check CodeBuild logs
aws logs filter-log-events \
  --log-group-name /aws/codebuild/la-marzocco-deployment-pipeline-build \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile leo \
  --region us-west-2
```

Common issues:
- Missing dependencies in requirements.txt
- Python version mismatch
- Build timeout (increase in buildspec.yml)

#### Deploy Stage Failure
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`]'
```

Common issues:
- IAM permission errors
- Resource naming conflicts
- Parameter validation errors
- Certificate validation timeout

### Lambda Function Issues

#### Function Not Updating
```bash
# Check Lambda function code SHA
aws lambda get-function \
  --function-name la-marzocco-dashboard-updater \
  --profile leo \
  --region us-west-2 \
  --query 'Configuration.CodeSha256'

# Manually update if needed (not recommended)
aws lambda update-function-code \
  --function-name la-marzocco-dashboard-updater \
  --zip-file fileb://lambda-deployment-package.zip \
  --profile leo \
  --region us-west-2
```

#### Function Execution Errors
```bash
# View recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile leo \
  --region us-west-2
```

Common issues:
- Missing environment variables
- Secrets Manager access denied
- S3 bucket permissions
- CloudFront invalidation permissions
- API authentication failures

### CloudFormation Stack Issues

#### Stack Stuck in UPDATE_IN_PROGRESS
```bash
# Cancel update (if safe)
aws cloudformation cancel-update-stack \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2
```

#### Stack Rollback
```bash
# View rollback reason
aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2 \
  --query 'StackEvents[?ResourceStatus==`UPDATE_ROLLBACK_IN_PROGRESS`]'
```

## Rollback Procedures

### Rollback via Git
```bash
# Revert to previous commit
git revert HEAD
git push origin main

# Pipeline will automatically deploy previous version
```

### Manual Rollback
```bash
# Get previous Lambda version
aws lambda list-versions-by-function \
  --function-name la-marzocco-dashboard-updater \
  --profile leo \
  --region us-west-2

# Update alias to previous version
aws lambda update-alias \
  --function-name la-marzocco-dashboard-updater \
  --name LIVE \
  --function-version <previous-version> \
  --profile leo \
  --region us-west-2
```

### CloudFormation Rollback
```bash
# Continue rollback if stuck
aws cloudformation continue-update-rollback \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2
```

## Cleanup and Teardown

### Delete Application Stack
```bash
# Delete via CloudFormation
aws cloudformation delete-stack \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2
```

### Delete Pipeline Stack
```bash
# Delete pipeline stack
aws cloudformation delete-stack \
  --stack-name la-marzocco-deployment-pipeline \
  --profile leo \
  --region us-west-2

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name la-marzocco-deployment-pipeline \
  --profile leo \
  --region us-west-2
```

### Complete Cleanup Script
```bash
# Use provided cleanup script
./cleanup.sh
```

This will delete:
- Application CloudFormation stack
- Pipeline CloudFormation stack
- S3 buckets (after emptying)
- CloudWatch log groups
- Secrets Manager secrets (optional)

## Best Practices

### Deployment Checklist
- [ ] AWS profile "leo" is configured and active
- [ ] .env file contains correct configuration
- [ ] Secrets Manager has valid credentials
- [ ] GitHub connection is authorized
- [ ] Code is tested locally
- [ ] Commit message is descriptive
- [ ] Changes are pushed to main branch
- [ ] Pipeline execution is monitored
- [ ] Dashboard is verified after deployment
- [ ] CloudWatch logs checked for errors

### Security Considerations
- Never commit credentials to Git
- Rotate Secrets Manager credentials regularly
- Review IAM permissions periodically
- Monitor CloudTrail for unusual activity
- Enable MFA on AWS account
- Use least privilege access

### Cost Management
- Monitor AWS billing dashboard
- Set up billing alerts
- Review CloudFront invalidation costs
- Optimize Lambda memory allocation
- Clean up old CloudWatch logs
- Delete unused resources

### Performance Optimization
- Monitor Lambda execution duration
- Check CloudFront cache hit ratio
- Optimize Lambda package size
- Use smart invalidation strategy
- Monitor S3 request costs
- Review EventBridge trigger frequency

## Emergency Procedures

### Dashboard Down
1. Check CloudFront distribution status
2. Verify S3 bucket has content
3. Check Route53 DNS records
4. Test Lambda function manually
5. Review CloudWatch logs for errors

### API Authentication Failure
1. Verify Secrets Manager credentials
2. Test credentials with La Marzocco app
3. Check for API changes or outages
4. Review Lambda logs for error details
5. Update credentials if needed

### Cost Spike
1. Check CloudWatch billing metrics
2. Review CloudFront invalidation count
3. Check Lambda invocation count
4. Verify EventBridge rule frequency
5. Review S3 request metrics

### Pipeline Failure
1. Check pipeline execution history
2. Review CodeBuild logs
3. Verify GitHub connection status
4. Check CloudFormation events
5. Test manual deployment if needed
