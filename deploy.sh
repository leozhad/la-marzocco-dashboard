#!/bin/bash

set -e

echo "🚀 Deploying Serverless La Marzocco Dashboard..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Stack name
STACK_NAME="la-marzocco-dashboard"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found. Please create it with your La Marzocco credentials.${NC}"
    echo "Required variables:"
    echo "  LAMARZOCCO_USERNAME=your_username"
    echo "  LAMARZOCCO_PASSWORD=your_password"
    echo "  AWS_REGION=us-west-2"
    echo "  DOMAIN_NAME=espresso.leozh.net"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
required_vars=("LAMARZOCCO_USERNAME" "LAMARZOCCO_PASSWORD" "AWS_REGION" "DOMAIN_NAME")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set in .env file${NC}"
        exit 1
    fi
done

echo -e "${BLUE}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Domain: $DOMAIN_NAME"
echo "  La Marzocco User: $LAMARZOCCO_USERNAME"
echo "  Stack Name: $STACK_NAME"
echo ""

echo -e "${YELLOW}Step 1: Preparing Lambda deployment package...${NC}"

# Create temporary directory for Lambda package
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy Lambda function
cp src/lambda_function.py "$TEMP_DIR/"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt -t "$TEMP_DIR/" --quiet

# Create deployment package
cd "$TEMP_DIR"
zip -r lambda_function.zip . > /dev/null
LAMBDA_ZIP_PATH="$TEMP_DIR/lambda_function.zip"

# Go back to script directory
cd "$SCRIPT_DIR"

echo -e "${GREEN}✅ Lambda package created${NC}"

echo -e "${YELLOW}Step 2: Updating parameters file...${NC}"

# Create parameters file with actual values
cat > cloudformation/parameters.json << EOF
[
  {
    "ParameterKey": "ProjectName",
    "ParameterValue": "la-marzocco-dashboard"
  },
  {
    "ParameterKey": "DomainName",
    "ParameterValue": "$DOMAIN_NAME"
  },
  {
    "ParameterKey": "Environment",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "LaMarzoccoUsername",
    "ParameterValue": "$LAMARZOCCO_USERNAME"
  },
  {
    "ParameterKey": "LaMarzoccoPassword",
    "ParameterValue": "$LAMARZOCCO_PASSWORD"
  }
]
EOF

echo -e "${GREEN}✅ Parameters file updated${NC}"

echo -e "${YELLOW}Step 3: Deploying AWS infrastructure...${NC}"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "Stack exists, updating..."
    OPERATION="update-stack"
    WAIT_CONDITION="stack-update-complete"
else
    echo "Stack does not exist, creating..."
    OPERATION="create-stack"
    WAIT_CONDITION="stack-create-complete"
fi

# Deploy the stack
aws cloudformation $OPERATION \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation/main.yaml \
    --parameters file://cloudformation/parameters.json \
    --capabilities CAPABILITY_NAMED_IAM \
    \
    --region "$AWS_REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CloudFormation stack deployment initiated${NC}"
    
    echo "Waiting for stack deployment to complete..."
    aws cloudformation wait $WAIT_CONDITION \
        --stack-name "$STACK_NAME" \
        \
        --region "$AWS_REGION"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
    else
        echo -e "${RED}❌ Infrastructure deployment failed${NC}"
        echo "Check the CloudFormation console for details"
        exit 1
    fi
else
    echo -e "${RED}❌ Failed to initiate infrastructure deployment${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 4: Updating Lambda function code...${NC}"

# Get Lambda function name from stack outputs
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text)

if [ -n "$LAMBDA_FUNCTION_NAME" ]; then
    echo "Updating Lambda function: $LAMBDA_FUNCTION_NAME"
    
    # Update Lambda function code
    aws lambda update-function-code \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --zip-file fileb://"$LAMBDA_ZIP_PATH" \
        \
        --region "$AWS_REGION" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Lambda function code updated${NC}"
    else
        echo -e "${RED}❌ Failed to update Lambda function code${NC}"
    fi
else
    echo -e "${RED}❌ Could not retrieve Lambda function name from stack outputs${NC}"
fi

# Clean up temporary directory
rm -rf "$TEMP_DIR"

echo -e "${YELLOW}Step 5: Getting stack outputs...${NC}"

# Get all stack outputs
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs')

# Parse individual outputs
DASHBOARD_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DashboardURL") | .OutputValue')
S3_BUCKET_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="S3BucketName") | .OutputValue')
CLOUDFRONT_DISTRIBUTION_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionId") | .OutputValue')

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}Resources created:${NC}"
echo "  Lambda Function: $LAMBDA_FUNCTION_NAME"
echo "  S3 Bucket: $S3_BUCKET_NAME"
echo "  CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
echo "  Dashboard URL: $DASHBOARD_URL"
echo ""

echo -e "${YELLOW}Step 6: Testing the Lambda function...${NC}"

# Trigger the Lambda function manually for initial test
echo "Triggering initial dashboard update..."
aws lambda invoke \
    \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --payload '{}' \
    response.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Lambda function executed successfully${NC}"
    echo "Response:"
    cat response.json | jq .
    rm response.json
else
    echo -e "${RED}❌ Lambda function execution failed${NC}"
    echo "Check CloudWatch logs for details:"
    echo "  aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --region $AWS_REGION --follow"
fi

echo ""
echo -e "${GREEN}🎉 Serverless deployment completed!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Wait a few minutes for DNS and SSL certificate to propagate"
echo "2. Visit your dashboard: $DASHBOARD_URL"
echo "3. The dashboard will update automatically every 5 minutes"
echo ""
echo -e "${BLUE}Monitoring:${NC}"
echo "• CloudWatch Logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --region $AWS_REGION --follow"
echo "• Lambda Metrics: AWS Console → Lambda → $LAMBDA_FUNCTION_NAME"
echo "• S3 Bucket: AWS Console → S3 → $S3_BUCKET_NAME"
echo "• CloudFormation: AWS Console → CloudFormation → $STACK_NAME"
echo ""
echo -e "${BLUE}Management:${NC}"
echo "• Update stack: ./deploy-cloudformation.sh"
echo "• Delete stack: aws cloudformation delete-stack --stack-name $STACK_NAME --region $AWS_REGION"
echo ""
echo -e "${YELLOW}Note: The EventBridge rule will trigger the function every 5 minutes automatically.${NC}"
