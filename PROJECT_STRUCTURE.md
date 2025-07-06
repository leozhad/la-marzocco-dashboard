# Project Structure

```
la-marzocco-dashboard/
├── cloudformation/
│   ├── main.yaml              # Complete CloudFormation template
│   └── parameters.json        # Stack parameters
├── src/
│   └── lambda_function.py     # Python Lambda function
├── deploy.sh                  # One-command deployment
├── cleanup.sh                 # Complete cleanup
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── README.md                 # Main documentation
├── QUICKSTART.md             # 5-minute setup guide
└── PROJECT_STRUCTURE.md      # This file
```

## Key Files

### CloudFormation Infrastructure
- **`cloudformation/main.yaml`**: Complete AWS infrastructure definition
- **`cloudformation/parameters.json`**: Stack parameters (auto-generated)

### Application Code
- **`src/lambda_function.py`**: Main Lambda function with pylamarzocco integration
- **`requirements.txt`**: Python dependencies (pylamarzocco, jinja2, boto3)

### Deployment & Management
- **`deploy.sh`**: Single-command deployment script
- **`cleanup.sh`**: Complete resource cleanup script
- **`.env.example`**: Environment configuration template

### Documentation
- **`README.md`**: Complete project documentation
- **`QUICKSTART.md`**: 5-minute setup guide
- **`PROJECT_STRUCTURE.md`**: This structure overview

## Deployment Flow

1. **Setup**: Copy `.env.example` to `.env` and configure
2. **Deploy**: Run `./deploy.sh` (creates everything)
3. **Monitor**: Use AWS console or CLI commands
4. **Update**: Run `./deploy.sh` again (updates stack)
5. **Cleanup**: Run `./cleanup.sh` (removes everything)

## AWS Resources Created

All resources are defined in `cloudformation/main.yaml`:

- **AWS::Lambda::Function** - Data collection and HTML generation
- **AWS::Events::Rule** - Scheduled execution every 5 minutes  
- **AWS::SecretsManager::Secret** - Secure credential storage
- **AWS::S3::Bucket** - Static website hosting
- **AWS::CloudFront::Distribution** - Global CDN with SSL
- **AWS::Route53::RecordSet** - DNS management
- **AWS::CertificateManager::Certificate** - SSL certificate
- **AWS::IAM::Role** - Least privilege execution role
- **AWS::Logs::LogGroup** - CloudWatch logging

## Configuration

### Environment Variables (`.env`)
```bash
LAMARZOCCO_USERNAME=your_username    # La Marzocco Cloud username
LAMARZOCCO_PASSWORD=your_password    # La Marzocco Cloud password  
AWS_REGION=us-west-2                # AWS region for deployment
DOMAIN_NAME=espresso.leozh.net      # Your domain name
```

### AWS Profile
- Uses "leo" profile configured in AWS CLI
- Set in CloudFormation provider configuration
- Used by deployment scripts

## Architecture

```
EventBridge → Lambda → S3 → CloudFront → Users
     ↓           ↓
Secrets Manager  CloudWatch Logs
```

- **EventBridge**: Triggers Lambda every 5 minutes
- **Lambda**: Collects data from La Marzocco API, generates HTML
- **Secrets Manager**: Stores La Marzocco credentials securely
- **S3**: Hosts static HTML and JSON files
- **CloudFront**: Global CDN with SSL termination
- **Route53**: DNS management for custom domain
- **CloudWatch**: Logging and monitoring

## Development Workflow

1. **Modify Code**: Edit `src/lambda_function.py`
2. **Test Locally**: Run with environment variables set
3. **Deploy Changes**: Run `./deploy.sh`
4. **Monitor**: Check CloudWatch logs
5. **Iterate**: Repeat as needed

## Cost Optimization

- **Lambda**: Pay per execution (~$0.20/month)
- **S3**: Minimal storage costs (~$0.02/month)
- **CloudFront**: Pay per request (~$0.50/month)
- **Other Services**: Fixed minimal costs (~$1.00/month)
- **Total**: ~$1.70/month

## Security

- **Credentials**: Encrypted in AWS Secrets Manager
- **Network**: HTTPS only, no public S3 access
- **Access**: IAM roles with least privilege
- **Monitoring**: CloudTrail for audit logging
