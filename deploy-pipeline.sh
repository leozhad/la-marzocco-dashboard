#!/bin/bash

# Deploy CodePipeline for La Marzocco Dashboard
# This script sets up the CI/CD pipeline that will automatically deploy changes from GitHub

set -e

# Configuration
STACK_NAME="la-marzocco-deployment-pipeline"
REGION="us-west-2"
PROFILE="leo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying CodePipeline for La Marzocco Dashboard...${NC}"

# Check if required files exist
if [ ! -f "cloudformation/pipeline.yaml" ]; then
    echo -e "${RED}❌ Error: cloudformation/pipeline.yaml not found${NC}"
    exit 1
fi

if [ ! -f "cloudformation/pipeline-parameters.json" ]; then
    echo -e "${RED}❌ Error: cloudformation/pipeline-parameters.json not found${NC}"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    echo -e "${YELLOW}📋 Loading environment variables...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ Error: .env file not found. Please create it with your configuration.${NC}"
    exit 1
fi

# Check if GitHub token is provided
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ Error: GITHUB_TOKEN not found in .env file${NC}"
    echo -e "${YELLOW}Please add your GitHub personal access token to .env:${NC}"
    echo "GITHUB_TOKEN=your_github_token_here"
    exit 1
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  AWS Region: $REGION"
echo "  Stack Name: $STACK_NAME"
echo "  Domain: $DOMAIN_NAME"
echo "  GitHub Repo: leozhad/la-marzocco-dashboard"

# Create temporary parameters file with actual values
TEMP_PARAMS=$(mktemp)
cat cloudformation/pipeline-parameters.json | \
    sed "s/REPLACE_WITH_YOUR_GITHUB_TOKEN/$GITHUB_TOKEN/g" | \
    sed "s/REPLACE_WITH_USERNAME/$LAMARZOCCO_USERNAME/g" | \
    sed "s/REPLACE_WITH_PASSWORD/$LAMARZOCCO_PASSWORD/g" > "$TEMP_PARAMS"

echo -e "${YELLOW}Step 1: Checking if pipeline stack exists...${NC}"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --profile "$PROFILE" --region "$REGION" >/dev/null 2>&1; then
    echo "Stack exists, updating..."
    aws cloudformation update-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://cloudformation/pipeline.yaml \
        --parameters file://"$TEMP_PARAMS" \
        --capabilities CAPABILITY_NAMED_IAM \
        --profile "$PROFILE" \
        --region "$REGION"
    
    echo -e "${YELLOW}Waiting for stack update to complete...${NC}"
    aws cloudformation wait stack-update-complete \
        --stack-name "$STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION"
else
    echo "Stack does not exist, creating..."
    aws cloudformation create-stack \
        --stack-name "$STACK_NAME" \
        --template-body file://cloudformation/pipeline.yaml \
        --parameters file://"$TEMP_PARAMS" \
        --capabilities CAPABILITY_NAMED_IAM \
        --profile "$PROFILE" \
        --region "$REGION"
    
    echo -e "${YELLOW}Waiting for stack creation to complete...${NC}"
    aws cloudformation wait stack-create-complete \
        --stack-name "$STACK_NAME" \
        --profile "$PROFILE" \
        --region "$REGION"
fi

# Clean up temporary file
rm "$TEMP_PARAMS"

echo -e "${GREEN}✅ Pipeline deployment completed successfully!${NC}"

# Get pipeline information
PIPELINE_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`PipelineName`].OutputValue' \
    --output text)

PIPELINE_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --profile "$PROFILE" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`PipelineUrl`].OutputValue' \
    --output text)

echo -e "${GREEN}🎉 CodePipeline Setup Complete!${NC}"
echo ""
echo -e "${BLUE}Pipeline Details:${NC}"
echo "  Pipeline Name: $PIPELINE_NAME"
echo "  Pipeline URL: $PIPELINE_URL"
echo ""
echo -e "${YELLOW}📋 What happens next:${NC}"
echo "  1. The pipeline will automatically trigger when you push to GitHub"
echo "  2. It will build your Lambda deployment package"
echo "  3. Deploy infrastructure changes via CloudFormation"
echo "  4. Update your Lambda function with new code"
echo ""
echo -e "${GREEN}🚀 To trigger a deployment, simply push changes to your GitHub repository!${NC}"
echo ""
echo -e "${BLUE}Monitor your pipeline at:${NC}"
echo "$PIPELINE_URL"
