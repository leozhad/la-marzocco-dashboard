# Changelog

All notable changes to the La Marzocco Dashboard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-07-06

### 🎨 Major Frontend Enhancements

#### **Added**
- **Matrix-Style Coffee Background Animation**
  - Authentic Matrix-style scrolling background with coffee emojis (☕ 🫘 🥤 🧋 🍵 🫖)
  - Parallel columns falling at different speeds (8s, 10s, 12s, 15s, 18s)
  - Responsive design that adapts to screen width and orientation changes
  - Semi-transparent overlay that doesn't interfere with dashboard content

- **Matrix Effect Toggle Control**
  - User-controlled toggle switch positioned near "Last Updated" section
  - Default state: OFF (clean dashboard by default)
  - Professional toggle design with coffee-themed gold accent (#d4af37)
  - Status indicator shows "On" or "Off" state
  - Instant response with efficient cleanup when toggling off

- **Machine Image Display**
  - Display machine image from La Marzocco Cloud API in header section
  - Positioned below machine name and serial number
  - Responsive styling with rounded corners and drop shadow
  - Graceful error handling if image fails to load
  - Max dimensions: 200px × 150px with proper aspect ratio

- **Coffee Emoji Favicon**
  - Browser favicon using coffee emoji (☕) as SVG data URI
  - Apple touch icon with golden background for iOS devices
  - Cross-platform compatibility for all modern browsers and devices
  - Consistent with coffee theme and brand colors

- **Local Timestamp Display for Recent Shots**
  - Convert Unix timestamps to user's local timezone
  - Smart relative time formatting:
    - < 1 minute: "Just now"
    - < 1 hour: "15m ago", "45m ago"
    - < 1 day: "2h ago", "8h ago"
    - < 1 week: "1d ago", "3d ago"
    - > 1 week: Actual date/time ("Jan 15, 2:30 PM")
  - Automatic conversion on page load with error handling

#### **Fixed**
- **Mobile Background Color Issue**
  - Fixed white background appearing on mobile devices with Matrix effect
  - Forced brown gradient background on mobile with !important declarations
  - Ensured Matrix elements remain transparent on all devices
  - Added explicit z-index layering for proper content display

- **Architecture Diagram Text Overflow**
  - Fixed Secrets Manager text overflow in application architecture diagram
  - Shortened text to "Shared Credentials" for better visual fit
  - Maintained professional appearance and readability

#### **Technical Implementation**

##### **Matrix Animation System**
- **Performance Optimized**: Efficient DOM management with automatic cleanup
- **Responsive**: Column count based on screen width (25px spacing)
- **Continuous Effect**: Periodic regeneration for endless animation
- **Mobile Friendly**: Smaller font sizes and optimized performance on mobile

##### **Timestamp Processing**
- **Data Source**: Unix milliseconds from La Marzocco Cloud API
- **Client-Side Conversion**: JavaScript Date objects for local timezone
- **Error Handling**: Graceful fallback for invalid/missing timestamps
- **Performance**: No server-side processing required

##### **Mobile Compatibility**
- **Background Fixes**: Explicit transparent backgrounds for Matrix elements
- **CSS Improvements**: !important declarations to override conflicting styles
- **Responsive Design**: Maintains functionality across all device sizes
- **Touch Optimization**: Enhanced mobile user experience

#### **User Experience Improvements**
- **Visual Recognition**: Machine image helps users identify their specific model
- **Professional Branding**: Favicon appears in browser tabs and bookmarks
- **Contextual Information**: Timestamps provide brewing pattern insights
- **User Control**: Matrix toggle allows clean dashboard or visual flair
- **Mobile Optimization**: Consistent experience across all devices

#### **CSS Enhancements**
- **Matrix Styling**: Multiple color variations (gold, brown, saddle brown)
- **Toggle Design**: Professional switch with smooth transitions
- **Mobile Responsive**: Optimized layouts for different screen sizes
- **Visual Depth**: Different font sizes and opacity levels for Matrix effect

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
