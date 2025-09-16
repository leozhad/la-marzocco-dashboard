#!/bin/bash

# Deploy optimized version of La Marzocco Dashboard
# This version only invalidates CloudFront when content actually changes

set -e

echo "🚀 Deploying Optimized La Marzocco Dashboard..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set AWS profile and region
export AWS_PROFILE=leo
export AWS_REGION=us-west-2

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Stack name
STACK_NAME="la-marzocco-dashboard"

echo -e "${BLUE}Configuration:${NC}"
echo "  AWS Profile: $AWS_PROFILE"
echo "  AWS Region: $AWS_REGION"
echo "  Stack Name: $STACK_NAME"
echo ""

echo -e "${YELLOW}Step 1: Backing up current Lambda function...${NC}"

# Get current Lambda function
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text)

if [ -n "$LAMBDA_FUNCTION_NAME" ]; then
    echo "Backing up current function: $LAMBDA_FUNCTION_NAME"
    
    # Download current function code
    aws lambda get-function \
        --function-name "$LAMBDA_FUNCTION_NAME" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" \
        --query 'Code.Location' \
        --output text | xargs curl -o lambda_backup.zip
    
    echo -e "${GREEN}✅ Current function backed up to lambda_backup.zip${NC}"
else
    echo -e "${RED}❌ Could not retrieve Lambda function name${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 2: Preparing optimized Lambda deployment package...${NC}"

# Create temporary directory for Lambda package
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Copy optimized Lambda function
cp src/lambda_function_optimized.py "$TEMP_DIR/lambda_function.py"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt -t "$TEMP_DIR/" --quiet

# Create deployment package
cd "$TEMP_DIR"
zip -r lambda_function_optimized.zip . > /dev/null
LAMBDA_ZIP_PATH="$TEMP_DIR/lambda_function_optimized.zip"

# Go back to script directory
cd "$SCRIPT_DIR"

echo -e "${GREEN}✅ Optimized Lambda package created${NC}"

echo -e "${YELLOW}Step 3: Updating Lambda function code...${NC}"

# Update Lambda function code
aws lambda update-function-code \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --zip-file fileb://"$LAMBDA_ZIP_PATH" \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Lambda function code updated with optimized version${NC}"
else
    echo -e "${RED}❌ Failed to update Lambda function code${NC}"
    exit 1
fi

# Clean up temporary directory
rm -rf "$TEMP_DIR"

echo -e "${YELLOW}Step 4: Testing the optimized function...${NC}"

# Trigger the Lambda function manually for initial test
echo "Triggering optimized function..."
aws lambda invoke \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --function-name "$LAMBDA_FUNCTION_NAME" \
    --payload '{}' \
    response_optimized.json

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Optimized Lambda function executed successfully${NC}"
    echo "Response:"
    cat response_optimized.json | jq .
    rm response_optimized.json
else
    echo -e "${RED}❌ Optimized Lambda function execution failed${NC}"
    echo "Check CloudWatch logs for details:"
    echo "  aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --profile $AWS_PROFILE --region $AWS_REGION --follow"
fi

echo ""
echo -e "${GREEN}🎉 Optimized deployment completed!${NC}"
echo ""
echo -e "${BLUE}What changed:${NC}"
echo "• ✅ Smart invalidation: Only invalidates when content changes"
echo "• ✅ Content hashing: SHA256 comparison to detect changes"
echo "• ✅ Cache storage: Stores content hashes in S3 for comparison"
echo "• ✅ Selective invalidation: Only invalidates changed paths"
echo ""
echo -e "${BLUE}Expected cost reduction:${NC}"
echo "• 🔥 From ~$70/month to ~$5/month (90%+ reduction)"
echo "• 💰 Saves ~$65/month in CloudFront invalidation costs"
echo "• 📊 Invalidations only when machine data actually changes"
echo ""
echo -e "${BLUE}Monitoring:${NC}"
echo "• CloudWatch Logs: aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --profile $AWS_PROFILE --region $AWS_REGION --follow"
echo "• Check invalidation count in Lambda response logs"
echo "• Monitor S3 .cache/ folder for hash storage"
echo ""
echo -e "${YELLOW}Note: The function will now only invalidate CloudFront when machine data changes!${NC}"
echo -e "${YELLOW}First run may still invalidate as it establishes baseline hashes.${NC}"
