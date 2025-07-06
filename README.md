# La Marzocco Dashboard

A serverless web dashboard for monitoring your La Marzocco espresso machine, built with AWS Lambda and the La Marzocco Cloud API.

![Application Architecture](generated-diagrams/application-architecture.png)

## Features

- **Real-time machine status** (power, temperature, water level)
- **Usage statistics** (total shots, flushes, last activity)
- **Machine settings** (auto on/off, dosing preferences)
- **Maintenance alerts** (descaling, cleaning needed)
- **Beautiful dark theme** optimized for coffee shops
- **Auto-refresh** every 5 minutes
- **JSON API endpoint** for integrations
- **Mobile responsive** design

## Benefits

- **🚀 Serverless**: No servers to manage, scales automatically
- **💰 Cost Effective**: Pay only when function runs (~$2.75/month)
- **🔒 Secure**: Credentials in AWS Secrets Manager, HTTPS only
- **⚡ Fast**: Global CDN with CloudFront
- **🔄 Automated**: Updates every 5 minutes automatically via GitOps
- **📱 Responsive**: Works on desktop and mobile
- **🛠️ Zero Maintenance**: Fully AWS managed infrastructure

## Architecture

### Application Architecture

The dashboard uses a serverless architecture with the following components:

- **EventBridge**: Triggers Lambda function every 5 minutes
- **Lambda**: Collects data from La Marzocco API and generates HTML
- **S3**: Hosts static website files (HTML + JSON)
- **CloudFront**: Global CDN with SSL termination
- **Route53**: DNS management for custom domain
- **Secrets Manager**: Secure storage for La Marzocco credentials
- **CloudWatch**: Logging and monitoring

### CI/CD Pipeline Architecture

![CI/CD Pipeline Architecture](generated-diagrams/cicd-pipeline-architecture.png)

The project uses GitOps for deployment:

1. **Developer** commits code to GitHub
2. **CodePipeline** automatically detects changes
3. **CodeBuild** packages Lambda function with dependencies
4. **CloudFormation** updates infrastructure and Lambda code
5. **Dashboard** is automatically updated

## Quick Start

### Prerequisites

1. **Compatible La Marzocco Machine**: Any La Marzocco machine or grinder with cloud connectivity ([see compatibility list](https://support-iot.lamarzocco.com/faq/))
2. **La Marzocco Account**: Cloud account with machine registered
3. **AWS Account**: AWS account with appropriate permissions configured
4. **Domain**: Route53 hosted zone for your domain
5. **Tools**: AWS CLI, Python 3.11+, jq (for JSON parsing)

### 1. Setup Environment

```bash
cd ~/git/la-marzocco-dashboard
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
AWS_REGION=us-west-2
DOMAIN_NAME=espresso.leozh.net
```

**Note**: La Marzocco credentials are stored securely in AWS Secrets Manager, not in `.env` files.

### 2. Deploy CI/CD Pipeline

```bash
# Set your AWS profile
export AWS_PROFILE=<your-profile-name>

# Deploy the CodePipeline
./deploy-pipeline.sh
```

This creates the CI/CD pipeline that will automatically deploy your application from GitHub.

### 3. Configure La Marzocco Credentials

After the pipeline is deployed, you need to add your La Marzocco credentials to AWS Secrets Manager:

```bash
# Find your secret name (it will be something like la-marzocco-dashboard-credentials-xxxxx)
AWS_PROFILE=<your-profile-name> aws secretsmanager list-secrets \
  --region us-west-2 \
  --query 'SecretList[?contains(Name, `la-marzocco-dashboard-credentials`)].Name' \
  --output text

# Update the secret with your La Marzocco credentials
AWS_PROFILE=<your-profile-name> aws secretsmanager update-secret \
  --secret-id <secret-name-from-above> \
  --secret-string '{"username":"your-lamarzocco-username","password":"your-lamarzocco-password"}' \
  --region us-west-2
```

**Important**: Replace `<your-profile-name>` with your AWS CLI profile name and use your actual La Marzocco Cloud credentials.

### 4. Deploy Application (via Git)

```bash
# Make any changes to your code
git add .
git commit -m "Initial deployment"
git push origin main
```

The CodePipeline will automatically:
- Build the Lambda deployment package
- Deploy/update CloudFormation stack
- Update Lambda function code
- Refresh the dashboard

### 5. Access Dashboard

Visit `https://your-domain.com` (your configured domain)

## What Gets Created

### AWS Resources (via CloudFormation)
- **Lambda Function**: Data collection and HTML generation
- **EventBridge Rule**: Triggers function every 5 minutes
- **S3 Bucket**: Static website hosting
- **CloudFront Distribution**: Global CDN with SSL
- **Route53 Records**: DNS management
- **ACM Certificate**: SSL certificate
- **Secrets Manager**: Secure credential storage
- **IAM Roles**: Least privilege access
- **CloudWatch Logs**: Function monitoring

### CI/CD Resources
- **CodePipeline**: Automated deployment pipeline
- **CodeBuild**: Lambda package building
- **S3 Artifacts Bucket**: Build artifact storage
- **IAM Roles**: Pipeline execution permissions

### Monthly Cost: ~$2.75

## Management

### View Pipeline Status
```bash
AWS_PROFILE=<your-profile> aws codepipeline get-pipeline-state \
  --name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2
```

### View Application Logs
```bash
AWS_PROFILE=<your-profile> aws logs tail /aws/lambda/la-marzocco-dashboard-updater \
  --region us-west-2 \
  --follow
```

### Test Lambda Function
```bash
AWS_PROFILE=<your-profile> aws lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --payload '{}' \
  --region us-west-2 \
  response.json && cat response.json | jq .
```

### Manual Stack Operations (if needed)
```bash
# View stack status
AWS_PROFILE=<your-profile> aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --region us-west-2

# View stack resources
AWS_PROFILE=<your-profile> aws cloudformation list-stack-resources \
  --stack-name la-marzocco-dashboard \
  --region us-west-2
```

### Delete Everything
```bash
./cleanup.sh
```

## Project Structure

```
la-marzocco-dashboard/
├── cloudformation/
│   ├── main.yaml              # Application CloudFormation template
│   ├── pipeline.yaml          # CI/CD pipeline CloudFormation template
│   ├── parameters.json        # Application stack parameters
│   └── pipeline-parameters.json # Pipeline stack parameters
├── src/
│   └── lambda_function.py     # Python Lambda function
├── generated-diagrams/        # Architecture diagrams
│   ├── application-architecture.png
│   └── cicd-pipeline-architecture.png
├── deploy-pipeline.sh         # Deploy CI/CD pipeline
├── deploy.sh                  # Manual deployment (legacy)
├── cleanup.sh                 # Complete cleanup
├── buildspec.yml              # CodeBuild specification
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Customization

### Update Frequency
Edit the EventBridge rule in `cloudformation/main.yaml`:
```yaml
DashboardScheduleRule:
  Properties:
    ScheduleExpression: 'rate(10 minutes)'  # Change from 5 minutes
```

Then commit and push: `git push origin main`

### Dashboard Styling
Edit the HTML template in `src/lambda_function.py` in the `generate_dashboard_html` method.

### Domain Configuration
1. Update `DOMAIN_NAME` in `.env`
2. Commit and push: `git push origin main`

## Data Collected

The dashboard displays comprehensive machine information:

```json
{
  "machine_info": {
    "name": "Linea Mini",
    "model": "Linea Mini", 
    "serial_number": "LM123456",
    "firmware_version": "1.2.3"
  },
  "status": {
    "power_on": true,
    "water_tank_level": 85,
    "current_temp": 201.2,
    "target_temp": 201.6,
    "heating": false,
    "brewing": false
  },
  "statistics": {
    "total_shots": 5047,
    "total_flushes": 1835,
    "last_shot_time": "2025-07-05T10:30:00Z",
    "last_flush_time": "2025-07-05T09:15:00Z"
  },
  "settings": {
    "auto_on_off": true,
    "auto_on_time": "07:00",
    "auto_off_time": "18:00",
    "dose_hot_water": 5,
    "dose_tea_water": 8
  },
  "maintenance": {
    "descaling_needed": false,
    "cleaning_needed": false,
    "last_descaling": "2025-06-01",
    "last_cleaning": "2025-06-15"
  }
}
```

## Troubleshooting

### Pipeline Deployment Failed
```bash
# Check pipeline execution
AWS_PROFILE=<your-profile> aws codepipeline list-pipeline-executions \
  --pipeline-name la-marzocco-deployment-pipeline-pipeline \
  --region us-west-2

# Check CodeBuild logs
AWS_PROFILE=<your-profile> aws logs filter-log-events \
  --log-group-name /aws/codebuild/la-marzocco-deployment-pipeline-build \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region us-west-2
```

### Stack Deployment Failed
```bash
# Check what failed
AWS_PROFILE=<your-profile> aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  --region us-west-2 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

### Lambda Function Not Working
```bash
# Check recent logs
AWS_PROFILE=<your-profile> aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --region us-west-2
```

### Dashboard Not Loading
1. Wait 5-10 minutes for DNS/SSL propagation
2. Check CloudFront distribution status
3. Verify S3 bucket has content
4. Check Route53 DNS records

### Authentication Issues
1. Verify La Marzocco credentials in AWS Secrets Manager
2. Test credentials with La Marzocco mobile app
3. Check Secrets Manager console for credential updates

## Security

### Current Implementation
- ✅ Credentials stored in AWS Secrets Manager (encrypted at rest)
- ✅ HTTPS only via CloudFront and ACM
- ✅ S3 bucket not publicly accessible (CloudFront OAC)
- ✅ Lambda execution role with minimal permissions
- ✅ CloudFormation stack with least privilege IAM policies
- ✅ CodePipeline with secure artifact storage

### Security Best Practices
- Regularly rotate La Marzocco credentials in Secrets Manager
- Monitor CloudTrail for unusual API activity
- Enable AWS Config for compliance monitoring
- Set up billing alerts for cost anomalies
- Review IAM permissions in CloudFormation templates

## Cost Breakdown

### Monthly Costs (Approximate)
- **Lambda**: ~$0.20 (8,640 invocations × 2 seconds × $0.0000166667/GB-second)
- **EventBridge**: ~$0.09 (8,640 events × $1.00/million)
- **S3**: ~$0.02 (minimal storage and requests)
- **CloudFront**: ~$0.50 (assuming moderate traffic)
- **Secrets Manager**: ~$0.40 (1 secret)
- **Route53**: ~$0.50 (hosted zone)
- **CodePipeline**: ~$1.00 (1 active pipeline)
- **CodeBuild**: ~$0.05 (minimal build time)

**Total**: ~$2.76/month

## API Endpoints

### Dashboard
- **URL**: `https://your-domain.com/`
- **Content**: Full HTML dashboard

### JSON Data
- **URL**: `https://your-domain.com/data.json`
- **Content**: Raw machine data in JSON format
- **Cache**: 1 minute TTL

## Development

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export S3_BUCKET_NAME=your-bucket
export LAMARZOCCO_SECRET_NAME=your-secret
export CLOUDFRONT_DISTRIBUTION_ID=your-distribution

# Test function locally
python src/lambda_function.py
```

### GitOps Workflow
1. **Make Changes**: Edit code, templates, or configuration
2. **Commit**: `git add . && git commit -m "Description"`
3. **Deploy**: `git push origin main`
4. **Monitor**: Check CodePipeline execution
5. **Verify**: Test dashboard functionality

## AWS Profile Usage

This project supports any AWS CLI profile configuration:

### Environment Variable Method (Recommended)
```bash
export AWS_PROFILE=<your-profile-name>
./deploy-pipeline.sh
```

### Per-Command Method
```bash
AWS_PROFILE=<your-profile-name> ./deploy-pipeline.sh
```

### Default Profile
If no profile is specified, scripts use your default AWS CLI profile.

## Support

### AWS Documentation
- [CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/)
- [EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/)

### La Marzocco API
- [pylamarzocco Library](https://github.com/zweckj/pylamarzocco)

### Useful Commands
```bash
# Pipeline operations
AWS_PROFILE=<your-profile> aws codepipeline list-pipelines --region us-west-2
AWS_PROFILE=<your-profile> aws codepipeline get-pipeline-state --name pipeline-name --region us-west-2

# Stack operations
AWS_PROFILE=<your-profile> aws cloudformation list-stacks --region us-west-2
AWS_PROFILE=<your-profile> aws cloudformation validate-template --template-body file://cloudformation/main.yaml

# Resource inspection
AWS_PROFILE=<your-profile> aws cloudformation list-stack-resources --stack-name la-marzocco-dashboard --region us-west-2

# Monitoring
AWS_PROFILE=<your-profile> aws logs describe-log-groups --log-group-name-prefix /aws/lambda/la-marzocco --region us-west-2
AWS_PROFILE=<your-profile> aws events list-rules --name-prefix la-marzocco --region us-west-2
```

---

**Created by [Leo Zhadanovsky](https://github.com/leozhad/la-marzocco-dashboard)**

**Enjoy your serverless La Marzocco dashboard!** ☕️
