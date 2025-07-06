# La Marzocco Dashboard

A serverless web dashboard for monitoring your La Marzocco Linea Mini espresso machine, built with AWS Lambda and the La Marzocco Cloud API.

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
                         │ espresso.leozh  │
                         │     .net        │
                         └─────────────────┘
```

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
- **💰 Cost Effective**: Pay only when function runs (~$1.70/month)
- **🔒 Secure**: Credentials in AWS Secrets Manager, HTTPS only
- **⚡ Fast**: Global CDN with CloudFront
- **🔄 Automated**: Updates every 5 minutes automatically
- **📱 Responsive**: Works on desktop and mobile
- **🛠️ Zero Maintenance**: Fully AWS managed infrastructure

## Quick Start

### Prerequisites

1. **La Marzocco Machine**: Linea Mini with cloud connectivity
2. **La Marzocco Account**: Cloud account with machine registered
3. **AWS Account**: Personal AWS account with "leo" profile configured
4. **Domain**: Route53 hosted zone for your domain
5. **Tools**: AWS CLI, Python 3.11+, jq (for JSON parsing)

### 1. Setup Environment

```bash
cd ~/git/la-marzocco-dashboard
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
LAMARZOCCO_USERNAME=your_lamarzocco_username
LAMARZOCCO_PASSWORD=your_lamarzocco_password
AWS_REGION=us-west-2
DOMAIN_NAME=espresso.leozh.net
```

### 2. Deploy Everything

```bash
./deploy.sh
```

This single command will:
- ✅ Create Lambda deployment package with dependencies
- ✅ Deploy CloudFormation stack with all AWS resources
- ✅ Update Lambda function code
- ✅ Test the deployment
- ✅ Provide monitoring and management commands

### 3. Access Dashboard

Visit `https://espresso.leozh.net` (or your configured domain)

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

### Monthly Cost: ~$1.70

## Management

### View Stack Status
```bash
aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2
```

### Update Stack
```bash
./deploy.sh
```

### View Logs
```bash
aws logs tail /aws/lambda/la-marzocco-dashboard-updater \
  --profile leo \
  --region us-west-2 \
  --follow
```

### Test Function
```bash
aws lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --payload '{}' \
  --profile leo \
  --region us-west-2 \
  response.json && cat response.json | jq .
```

### Delete Everything
```bash
./cleanup.sh
```

## Customization

### Update Frequency
Edit the EventBridge rule in `cloudformation/main.yaml`:
```yaml
DashboardScheduleRule:
  Properties:
    ScheduleExpression: 'rate(10 minutes)'  # Change from 5 minutes
```

Then redeploy: `./deploy.sh`

### Dashboard Styling
Edit the HTML template in `src/lambda_function.py` in the `generate_dashboard_html` method.

### Domain Configuration
1. Update `DOMAIN_NAME` in `.env`
2. Redeploy: `./deploy.sh`

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

### Stack Deployment Failed
```bash
# Check what failed
aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  --profile leo \
  --region us-west-2 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

### Lambda Function Not Working
```bash
# Check recent logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile leo \
  --region us-west-2
```

### Dashboard Not Loading
1. Wait 5-10 minutes for DNS/SSL propagation
2. Check CloudFront distribution status
3. Verify S3 bucket has content
4. Check Route53 DNS records

### Authentication Issues
1. Verify La Marzocco credentials in `.env`
2. Test credentials with La Marzocco mobile app
3. Check Secrets Manager in AWS console

## Security

### Current Implementation
- ✅ Credentials stored in AWS Secrets Manager (encrypted at rest)
- ✅ HTTPS only via CloudFront and ACM
- ✅ S3 bucket not publicly accessible (CloudFront OAC)
- ✅ Lambda execution role with minimal permissions
- ✅ CloudFormation stack with least privilege IAM policies

### Security Best Practices
- Regularly rotate La Marzocco credentials in Secrets Manager
- Monitor CloudTrail for unusual API activity
- Enable AWS Config for compliance monitoring
- Set up billing alerts for cost anomalies
- Review IAM permissions in CloudFormation template

## Cost Breakdown

### Monthly Costs (Approximate)
- **Lambda**: ~$0.20 (8,640 invocations × 2 seconds × $0.0000166667/GB-second)
- **EventBridge**: ~$0.09 (8,640 events × $1.00/million)
- **S3**: ~$0.02 (minimal storage and requests)
- **CloudFront**: ~$0.50 (assuming moderate traffic)
- **Secrets Manager**: ~$0.40 (1 secret)
- **Route53**: ~$0.50 (hosted zone)

**Total**: ~$1.71/month

## API Endpoints

### Dashboard
- **URL**: `https://espresso.leozh.net/`
- **Content**: Full HTML dashboard

### JSON Data
- **URL**: `https://espresso.leozh.net/data.json`
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

### Project Structure
```
la-marzocco-dashboard/
├── cloudformation/
│   ├── main.yaml              # CloudFormation template
│   └── parameters.json        # Stack parameters
├── src/
│   └── lambda_function.py     # Lambda function code
├── deploy.sh                  # Deployment script
├── cleanup.sh                 # Cleanup script
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

## Support

### AWS Documentation
- [CloudFormation User Guide](https://docs.aws.amazon.com/cloudformation/)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/)

### La Marzocco API
- [pylamarzocco Library](https://github.com/zweckj/pylamarzocco)

### Useful Commands
```bash
# Stack operations
aws cloudformation list-stacks --profile leo --region us-west-2
aws cloudformation validate-template --template-body file://cloudformation/main.yaml

# Resource inspection
aws cloudformation list-stack-resources --stack-name la-marzocco-dashboard --profile leo --region us-west-2

# Monitoring
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/la-marzocco --profile leo --region us-west-2
aws events list-rules --name-prefix la-marzocco --profile leo --region us-west-2
```

---

**Enjoy your serverless La Marzocco dashboard!** ☕️
