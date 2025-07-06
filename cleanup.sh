#!/bin/bash

set -e

echo "🗑️  Cleaning up La Marzocco Dashboard..."

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

# Check if .env file exists for region
if [ -f .env ]; then
    source .env
    AWS_REGION=${AWS_REGION:-us-west-2}
else
    AWS_REGION="us-west-2"
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  AWS Region: $AWS_REGION"
echo "  Stack Name: $STACK_NAME"
echo ""

# Check if stack exists
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --profile leo --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${YELLOW}Stack '$STACK_NAME' does not exist or is already deleted.${NC}"
    exit 0
fi

# Get stack outputs before deletion
echo -e "${BLUE}Current stack resources:${NC}"
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile leo \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs' 2>/dev/null || echo "[]")

if [ "$OUTPUTS" != "[]" ] && [ "$OUTPUTS" != "null" ]; then
    DASHBOARD_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DashboardURL") | .OutputValue' 2>/dev/null || echo "N/A")
    S3_BUCKET_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="S3BucketName") | .OutputValue' 2>/dev/null || echo "N/A")
    LAMBDA_FUNCTION_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="LambdaFunctionName") | .OutputValue' 2>/dev/null || echo "N/A")
    
    echo "  Dashboard URL: $DASHBOARD_URL"
    echo "  S3 Bucket: $S3_BUCKET_NAME"
    echo "  Lambda Function: $LAMBDA_FUNCTION_NAME"
else
    echo "  No outputs available or stack in transition state"
fi

echo ""
echo -e "${YELLOW}⚠️  WARNING: This will permanently delete all resources created by the stack!${NC}"
echo "This includes:"
echo "  • Lambda function and logs"
echo "  • S3 bucket and all contents"
echo "  • CloudFront distribution"
echo "  • SSL certificate"
echo "  • Route53 DNS records"
echo "  • Secrets Manager secret"
echo "  • All associated IAM roles and policies"
echo ""

read -p "Are you sure you want to delete the stack? (type 'yes' to confirm): " -r
if [[ ! $REPLY == "yes" ]]; then
    echo "Deletion cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Emptying S3 bucket (if it exists)...${NC}"

# Try to empty S3 bucket first (CloudFormation can't delete non-empty buckets)
if [ "$S3_BUCKET_NAME" != "N/A" ] && [ -n "$S3_BUCKET_NAME" ]; then
    echo "Emptying S3 bucket: $S3_BUCKET_NAME"
    aws s3 rm s3://"$S3_BUCKET_NAME" --recursive --profile leo --region "$AWS_REGION" 2>/dev/null || echo "Bucket already empty or doesn't exist"
    echo -e "${GREEN}✅ S3 bucket emptied${NC}"
else
    echo "No S3 bucket to empty"
fi

echo -e "${YELLOW}Step 2: Deleting AWS infrastructure...${NC}"

# Delete the stack
aws cloudformation delete-stack \
    --stack-name "$STACK_NAME" \
    --profile leo \
    --region "$AWS_REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Stack deletion initiated${NC}"
    
    echo "Waiting for stack deletion to complete..."
    echo "This may take several minutes..."
    
    aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK_NAME" \
        --profile leo \
        --region "$AWS_REGION"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Stack deleted successfully${NC}"
    else
        echo -e "${RED}❌ Stack deletion failed or timed out${NC}"
        echo "Check the CloudFormation console for details:"
        echo "  https://console.aws.amazon.com/cloudformation/home?region=$AWS_REGION"
        exit 1
    fi
else
    echo -e "${RED}❌ Failed to initiate stack deletion${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Cleanup completed successfully!${NC}"
echo ""
echo -e "${BLUE}What was deleted:${NC}"
echo "  • CloudFormation stack: $STACK_NAME"
echo "  • All AWS resources created by the stack"
echo "  • Lambda function and CloudWatch logs"
echo "  • S3 bucket and all contents"
echo "  • CloudFront distribution"
echo "  • SSL certificate"
echo "  • Route53 DNS records"
echo "  • Secrets Manager secret with La Marzocco credentials"
echo "  • IAM roles and policies"
echo ""
echo -e "${YELLOW}Note: Your domain's hosted zone was preserved if it existed before stack creation.${NC}"
echo ""
echo -e "${BLUE}To redeploy:${NC}"
echo "  ./deploy-cloudformation.sh"
