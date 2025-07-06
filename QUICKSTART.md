# Quick Start Guide

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **La Marzocco Account** with machine registered
3. **Domain** in Route53 (or will be created)
4. **Python 3.11+** and **jq** installed

## 5-Minute Setup

### 1. Configure Credentials

```bash
cd ~/git/la-marzocco-dashboard
cp .env.example .env
```

Edit `.env`:
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
- ✅ Create Lambda deployment package
- ✅ Deploy CloudFormation stack
- ✅ Create all AWS resources
- ✅ Update Lambda function code
- ✅ Test the deployment
- ✅ Provide monitoring commands

### 3. Access Dashboard

Visit `https://espresso.leozh.net` (your domain)

## What Gets Created

### AWS Resources (via CloudFormation)
- **Lambda Function**: Data collection and HTML generation
- **EventBridge Rule**: Triggers every 5 minutes
- **S3 Bucket**: Static website hosting
- **CloudFront Distribution**: Global CDN with SSL
- **Route53 Records**: DNS management
- **ACM Certificate**: SSL certificate
- **Secrets Manager**: Secure credential storage
- **IAM Roles**: Least privilege access
- **CloudWatch Logs**: Function monitoring

### Cost: ~$1.70/month

## Management Commands

### View Stack Status
```bash
aws cloudformation describe-stacks \
  --stack-name la-marzocco-dashboard \
  \
  --region us-west-2
```

### Update Stack
```bash
./deploy.sh
```

### View Logs
```bash
aws logs tail /aws/lambda/la-marzocco-dashboard-updater \
  \
  --region us-west-2 \
  --follow
```

### Test Function
```bash
aws lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --payload '{}' \
  \
  --region us-west-2 \
  response.json && cat response.json | jq .
```

### Delete Everything
```bash
./cleanup.sh
```

## Troubleshooting

### Stack Deployment Failed
```bash
# Check what failed
aws cloudformation describe-stack-events \
  --stack-name la-marzocco-dashboard \
  \
  --region us-west-2 \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

### Lambda Function Not Working
```bash
# Check recent logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --start-time $(date -d '1 hour ago' +%s)000 \
  \
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

## Customization

### Change Update Frequency
Edit `cloudformation/main.yaml`:
```yaml
DashboardScheduleRule:
  Properties:
    ScheduleExpression: 'rate(10 minutes)'  # Change from 5 minutes
```

Then redeploy:
```bash
./deploy.sh
```

### Change Domain
1. Update `DOMAIN_NAME` in `.env`
2. Redeploy: `./deploy.sh`

### Modify Dashboard
1. Edit `src/lambda_function.py`
2. Redeploy: `./deploy.sh`

## Benefits

### Serverless Architecture
- ❌ No servers to manage
- ❌ No containers or infrastructure
- ✅ 99.95% uptime SLA
- ✅ Automatic scaling
- ✅ Professional security
- ✅ Global performance

### Cost Effective
- ✅ Pay only when function runs
- ✅ ~$1.70/month total cost
- ✅ No always-on infrastructure
- ✅ AWS Free Tier eligible

### Zero Maintenance
- ✅ AWS manages all infrastructure
- ✅ Automatic security updates
- ✅ Built-in monitoring and logging
- ✅ No patching or updates needed

## Next Steps

1. **Monitor**: Set up CloudWatch alarms
2. **Optimize**: Adjust Lambda memory/timeout if needed
3. **Secure**: Rotate credentials periodically
4. **Extend**: Add more machine data or features
5. **Scale**: Add multiple machines if needed

## Support

- **CloudFormation Console**: Monitor stack status
- **CloudWatch Logs**: Debug function issues
- **AWS Documentation**: [CloudFormation](https://docs.aws.amazon.com/cloudformation/) | [Lambda](https://docs.aws.amazon.com/lambda/)
- **La Marzocco API**: [pylamarzocco](https://github.com/zweckj/pylamarzocco)

---

**That's it!** Your serverless La Marzocco dashboard is now running on AWS with professional-grade infrastructure, automatic updates every 5 minutes, and costs less than $2/month.
