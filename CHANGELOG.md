# Changelog

All notable changes to the La Marzocco Dashboard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-07-06

### 🚀 Major Changes

#### **BREAKING CHANGE: Consolidated Secrets Management**
- **Consolidated La Marzocco credentials into single shared secret**
- Pipeline template now creates shared secret used by both deployment and runtime
- Reduced Secrets Manager costs by 50% (1 secret instead of 2)
- **Migration Required**: Existing deployments need to update their secrets after this change

### Added
- **Comprehensive Documentation**
  - Consolidated all markdown files into single comprehensive README.md
  - Added visual architecture diagrams for both application and CI/CD pipeline
  - Added CHANGELOG.md for tracking project changes
  - Updated documentation to reflect consolidated secrets management

- **Architecture Diagrams**
  - Application architecture diagram showing serverless components and shared secrets
  - CI/CD pipeline architecture diagram showing GitOps workflow with consolidated secrets
  - Both diagrams generated using AWS architecture diagram MCP

- **Enhanced Secret Management**
  - Single shared secret for La Marzocco credentials (`la-marzocco-deployment-pipeline-lamarzocco-credentials`)
  - GitHub token stored in Secrets Manager (`la-marzocco-github-token`)
  - Proper documentation of both secrets and their setup requirements

### Changed
- **CloudFormation Templates**
  - **Pipeline Template**: Now creates shared La Marzocco credentials secret
  - **Main Template**: Accepts secret name as parameter instead of creating duplicate secret
  - Updated IAM permissions to reference shared secret
  - Simplified parameter passing between templates

- **Documentation Structure**
  - Removed redundant markdown files: `PROJECT_STRUCTURE.md`, `SUMMARY.md`, `QUICKSTART.md`, `AWS_PROFILE_USAGE.md`
  - Consolidated all information into comprehensive README.md
  - Added machine compatibility information (works with various La Marzocco machines/grinders)
  - Updated cost breakdown to reflect accurate pricing (~$2.75/month)

- **Environment Variable Consistency**
  - Added `AWS_REGION` export to setup instructions
  - Use environment variables consistently throughout all commands (`$AWS_PROFILE`, `$AWS_REGION`)
  - Replaced hardcoded regions with configurable variables
  - Added brackets around CLI profile placeholders for clarity (`<your-profile>`)

- **Data Collection Accuracy**
  - Updated "Data Collected" section to match actual Lambda function output
  - Added comprehensive machine info, brewing settings, recent shots, and maintenance data
  - Reflects real API response structure from La Marzocco Cloud API

### Fixed
- **Cost Consistency**: Standardized cost references to ~$2.75/month throughout documentation
- **Region Flexibility**: Made AWS region configurable instead of hardcoded to us-west-2
- **Secret Management**: Eliminated duplicate credential storage and management complexity
- **Footer Links**: Added clickable links to AWS Lambda and pylamarzocco GitHub repository

### Technical Details

#### **Secret Management Architecture**
```
Pipeline Stack (Creates Secret) → Main Stack (Uses Secret) → Lambda (Reads Secret)
```

#### **Required Secrets**
1. **La Marzocco Credentials** (`la-marzocco-deployment-pipeline-lamarzocco-credentials`)
   - Format: `{"username": "your-email", "password": "your-password"}`
   - Used by: Pipeline deployment and Lambda function
   - Created by: Pipeline CloudFormation template

2. **GitHub Token** (`la-marzocco-github-token`)
   - Format: `{"token": "your-github-token"}`
   - Used by: CodePipeline for GitHub integration
   - Created by: Manual setup (pre-existing)

#### **Cost Optimization**
- **Before**: 2 secrets × $0.40/month = $0.80/month
- **After**: 1 secret × $0.40/month = $0.40/month
- **Savings**: $0.40/month (50% reduction in secret costs)

#### **Migration Guide**
For existing deployments:
1. Deploy updated pipeline template (creates shared secret)
2. Update shared secret with La Marzocco credentials
3. Pipeline will automatically deploy updated main template
4. Old duplicate secrets can be cleaned up manually

### Infrastructure
- **AWS Services**: Lambda, EventBridge, S3, CloudFront, Route53, Secrets Manager, CodePipeline, CodeBuild
- **Runtime**: Python 3.11+ with pylamarzocco library
- **Deployment**: GitOps via AWS CodePipeline
- **Monitoring**: CloudWatch Logs and metrics

---

## [1.0.0] - 2025-07-05

### Added
- Initial release of La Marzocco Dashboard
- Serverless architecture with AWS Lambda and EventBridge
- Real-time machine monitoring via La Marzocco Cloud API
- Static website hosting with S3 and CloudFront
- CI/CD pipeline with CodePipeline and CodeBuild
- Comprehensive documentation and setup guides
- Mobile-responsive dark theme dashboard
- JSON API endpoint for integrations
- Automatic updates every 5 minutes

### Features
- **Real-time machine status** (power, temperature, water level)
- **Usage statistics** (total shots, flushes, last activity)
- **Machine settings** (auto on/off, dosing preferences)
- **Maintenance alerts** (descaling, cleaning needed)
- **Beautiful dark theme** optimized for coffee shops
- **Auto-refresh** every 5 minutes
- **JSON API endpoint** for integrations
- **Mobile responsive** design

### Infrastructure
- **Cost**: ~$2.75/month
- **Uptime**: 99.95% SLA (AWS managed)
- **Security**: HTTPS only, credentials in Secrets Manager
- **Performance**: Global CDN with CloudFront
- **Maintenance**: Zero maintenance required
