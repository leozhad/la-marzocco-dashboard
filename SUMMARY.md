# La Marzocco Dashboard - Project Summary

## What This Is

A **serverless web dashboard** for monitoring your La Marzocco Linea Mini espresso machine, built with:
- **AWS Lambda** for data collection
- **La Marzocco Cloud API** for direct machine access
- **CloudFormation** for infrastructure management
- **Python** with the `pylamarzocco` library

## Key Benefits

### 🚀 **Serverless Architecture**
- No servers or containers to manage
- Automatic scaling and high availability
- 99.95% uptime SLA from AWS
- Zero maintenance overhead

### 💰 **Cost Effective**
- **~$1.70/month** total cost
- Pay only when function executes
- No always-on infrastructure costs
- AWS Free Tier eligible

### 🔒 **Professional Security**
- Credentials encrypted in AWS Secrets Manager
- HTTPS-only access via CloudFront
- IAM roles with least privilege access
- No public S3 bucket access

### 📊 **Comprehensive Data**
- Real-time machine status (power, temperature, water level)
- Usage statistics (shots, flushes, timing)
- Machine settings (auto on/off, dosing)
- Maintenance alerts (descaling, cleaning)

## Quick Deployment

```bash
# 1. Configure credentials
cp .env.example .env
# Edit .env with your La Marzocco credentials

# 2. Deploy everything
./deploy.sh

# 3. Access dashboard
# Visit https://your-domain.com
```

**That's it!** One command deploys the entire infrastructure.

## What Gets Created

### AWS Resources (via CloudFormation)
- **Lambda Function**: Collects data every 5 minutes
- **S3 Bucket**: Hosts static HTML dashboard
- **CloudFront**: Global CDN with SSL certificate
- **Route53**: DNS management
- **Secrets Manager**: Secure credential storage
- **EventBridge**: Scheduled function execution
- **IAM Roles**: Least privilege access
- **CloudWatch**: Logging and monitoring

### Dashboard Features
- **Beautiful dark theme** optimized for coffee shops
- **Mobile responsive** design
- **Auto-refresh** every 5 minutes
- **JSON API** endpoint for integrations
- **Real-time data** from La Marzocco Cloud

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ EventBridge     │    │ Lambda Function │    │ S3 Bucket   │ │
│  │ (Every 5 min)   │───▶│ - pylamarzocco  │───▶│ Static Site │ │
│  └─────────────────┘    │ - Data Collect  │    │ JSON + HTML │ │
│                         │ - Generate HTML │    └─────────────┘ │
│                         └─────────────────┘           │        │
│                                  │                    │        │
│                         ┌─────────────────┐    ┌─────────────┐ │
│                         │ Secrets Manager │    │ CloudFront  │ │
│                         │ - LM Credentials│    │ CDN + SSL   │ │
│                         └─────────────────┘    └─────────────┘ │
│                                                       │        │
│  ┌─────────────────────────────────────────────────────────────┤
│  │                    Route53 DNS                              │
│  └─────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────┘
                                    │
                         ┌─────────────────┐
                         │     Users       │
                         │   Browser       │
                         │ Your Domain     │
                         └─────────────────┘
```

## Management

### View Status
```bash
aws cloudformation describe-stacks --stack-name la-marzocco-dashboard --profile leo
```

### View Logs
```bash
aws logs tail /aws/lambda/la-marzocco-dashboard-updater --follow
```

### Update Stack
```bash
./deploy.sh
```

### Delete Everything
```bash
./cleanup.sh
```

## Project Structure

```
la-marzocco-dashboard/
├── cloudformation/           # AWS infrastructure
│   ├── main.yaml            # Complete CloudFormation template
│   └── parameters.json      # Stack parameters
├── src/                     # Application code
│   └── lambda_function.py   # Python Lambda function
├── deploy.sh               # One-command deployment
├── cleanup.sh              # Complete cleanup
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── README.md              # Complete documentation
├── QUICKSTART.md          # 5-minute setup
└── PROJECT_STRUCTURE.md   # Project overview
```

## Why This Approach

### vs. Traditional Hosting
- **No servers** to patch, monitor, or scale
- **No infrastructure** costs when not in use
- **Professional reliability** with AWS SLA
- **Global performance** with CloudFront CDN

### vs. Container Solutions
- **No orchestration** complexity
- **No container** management overhead
- **Automatic scaling** without configuration
- **Built-in monitoring** with CloudWatch

### vs. Home-Based Solutions
- **No home network** dependency
- **No power/internet** outage impact
- **Professional security** standards
- **Global accessibility** from anywhere

## Data Source

Uses the **`pylamarzocco`** Python library to connect directly to the La Marzocco Cloud API, providing:
- Real-time machine status
- Historical usage statistics
- Machine configuration settings
- Maintenance scheduling information

## Security & Compliance

- **Encryption at rest** (Secrets Manager, S3)
- **Encryption in transit** (HTTPS only)
- **Access control** (IAM roles, CloudFront OAC)
- **Audit logging** (CloudTrail integration)
- **No public endpoints** (except CloudFront)

## Cost Breakdown

| Service | Monthly Cost |
|---------|-------------|
| Lambda | ~$0.20 |
| EventBridge | ~$0.09 |
| S3 | ~$0.02 |
| CloudFront | ~$0.50 |
| Secrets Manager | ~$0.40 |
| Route53 | ~$0.50 |
| **Total** | **~$1.71** |

## Getting Started

1. **Prerequisites**: AWS CLI configured, La Marzocco account
2. **Configure**: Copy `.env.example` to `.env` and add credentials
3. **Deploy**: Run `./deploy.sh`
4. **Access**: Visit your dashboard URL

**Documentation**: See `README.md` for complete details or `QUICKSTART.md` for rapid setup.

---

**Result**: A professional-grade, serverless espresso machine dashboard that costs less than $2/month and requires zero maintenance.
