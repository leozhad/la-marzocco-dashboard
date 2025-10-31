# Requirements Document

## Introduction

The La Marzocco Dashboard is a serverless web application that provides real-time monitoring of La Marzocco espresso machines via the La Marzocco Cloud API. The system enables coffee shop owners and espresso enthusiasts to monitor their machine's status, usage statistics, and maintenance needs through a web-based dashboard accessible from any device.

## Glossary

- **Dashboard System**: The complete serverless application including Lambda function, S3 hosting, and CloudFront distribution
- **Lambda Function**: AWS Lambda function that collects data and generates dashboard HTML
- **Machine Data**: Comprehensive information from La Marzocco Cloud API including status, statistics, and settings
- **Smart Invalidation**: Content change detection system that only invalidates CloudFront when data actually changes
- **Installation Key**: Authentication token for La Marzocco Cloud API device registration
- **GitOps Pipeline**: Automated CI/CD pipeline using CodePipeline, CodeBuild, and CloudFormation

## Requirements

### Requirement 1: Real-Time Machine Monitoring

**User Story:** As a coffee shop owner, I want to view my espresso machine's current status in real-time, so that I can ensure it's operating correctly without being physically present.

#### Acceptance Criteria

1. WHEN THE Dashboard System collects data from La Marzocco Cloud API, THE Dashboard System SHALL retrieve machine power status, temperature readings, and boiler states
2. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display coffee boiler temperature in Fahrenheit with ready indicator
3. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display steam boiler status and enabled state
4. WHEN THE Dashboard System detects a connected scale, THE Dashboard System SHALL display scale connection status and battery level
5. THE Dashboard System SHALL refresh machine data every 5 minutes via EventBridge scheduled trigger

### Requirement 2: Usage Statistics Tracking

**User Story:** As a coffee shop manager, I want to track total shots and flushes over time, so that I can understand machine usage patterns and plan maintenance schedules.

#### Acceptance Criteria

1. WHEN THE Dashboard System collects statistics from La Marzocco Cloud API, THE Dashboard System SHALL extract lifetime total shots from COFFEE_AND_FLUSH_COUNTER widget
2. WHEN THE Dashboard System collects statistics from La Marzocco Cloud API, THE Dashboard System SHALL extract lifetime total flushes from COFFEE_AND_FLUSH_COUNTER widget
3. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display total shots and flushes with comma-separated formatting
4. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL render a pie chart visualization comparing shots to flushes
5. WHEN THE Dashboard System encounters API parsing errors, THE Dashboard System SHALL extract statistics from exception messages as fallback

### Requirement 3: Recent Shot History

**User Story:** As a barista, I want to see details of recent espresso shots, so that I can analyze extraction quality and adjust my technique.

#### Acceptance Criteria

1. WHEN THE Dashboard System collects statistics from La Marzocco Cloud API, THE Dashboard System SHALL extract the 5 most recent shots with dose data from LAST_COFFEE widget
2. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display extraction time, dose weight, and extraction ratio for each shot
3. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL convert Unix millisecond timestamps to user's local timezone with relative time formatting
4. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL render a bar chart comparing extraction times and dose weights across recent shots
5. WHEN THE Dashboard System has 5 or more recent shots, THE Dashboard System SHALL calculate and display average extraction time and dose weight

### Requirement 4: Machine Settings Display

**User Story:** As a machine owner, I want to view my machine's configuration settings, so that I can verify they match my preferences without using the mobile app.

#### Acceptance Criteria

1. WHEN THE Dashboard System collects settings from La Marzocco Cloud API, THE Dashboard System SHALL retrieve WiFi network name and signal strength
2. WHEN THE Dashboard System collects settings from La Marzocco Cloud API, THE Dashboard System SHALL retrieve water connection type (plumbed or tank)
3. WHEN THE Dashboard System collects settings from La Marzocco Cloud API, THE Dashboard System SHALL retrieve auto-update and smart standby settings
4. WHEN THE Dashboard System collects settings from La Marzocco Cloud API, THE Dashboard System SHALL retrieve brewing configuration including pre-brewing mode and dose settings
5. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display all settings in organized card layouts

### Requirement 5: Maintenance Alerts

**User Story:** As a coffee shop owner, I want to be notified of maintenance needs, so that I can keep my machine in optimal condition.

#### Acceptance Criteria

1. WHEN THE Dashboard System collects maintenance data from La Marzocco Cloud API, THE Dashboard System SHALL retrieve cleaning status and last cleaning date
2. WHEN THE Dashboard System collects maintenance data from La Marzocco Cloud API, THE Dashboard System SHALL retrieve firmware update requirements and availability
3. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display cleaning status with clear visual indicators
4. WHEN THE Dashboard System generates the dashboard HTML, THE Dashboard System SHALL display firmware version information
5. WHEN THE Dashboard System detects firmware updates available, THE Dashboard System SHALL display update availability status

### Requirement 6: Smart CloudFront Invalidation

**User Story:** As a project owner, I want to minimize CloudFront invalidation costs, so that the dashboard remains cost-effective to operate.

#### Acceptance Criteria

1. WHEN THE Dashboard System generates content, THE Dashboard System SHALL create normalized version of machine data excluding timestamp fields
2. WHEN THE Dashboard System compares content, THE Dashboard System SHALL compute SHA256 hash of normalized content
3. WHEN THE Dashboard System compares content, THE Dashboard System SHALL retrieve previously stored content hash from S3 cache folder
4. WHEN THE Dashboard System detects content has changed, THE Dashboard System SHALL invalidate only the changed CloudFront paths (HTML or JSON)
5. WHEN THE Dashboard System detects no content changes, THE Dashboard System SHALL skip CloudFront invalidation while still uploading to S3

### Requirement 7: Secure Credential Management

**User Story:** As a security-conscious user, I want my La Marzocco credentials stored securely, so that unauthorized users cannot access my machine data.

#### Acceptance Criteria

1. THE Dashboard System SHALL store La Marzocco credentials in AWS Secrets Manager with encryption at rest
2. WHEN THE Lambda Function requires credentials, THE Lambda Function SHALL retrieve credentials from Secrets Manager using IAM role permissions
3. THE Dashboard System SHALL use a single shared secret for both pipeline deployment and Lambda runtime
4. THE Dashboard System SHALL never log or expose credentials in CloudWatch logs or error messages
5. WHEN THE Dashboard System generates installation keys, THE Dashboard System SHALL persist keys in S3 cache folder for reuse across Lambda invocations

### Requirement 8: GitOps Deployment

**User Story:** As a developer, I want automated deployments when I push code to GitHub, so that I can deploy changes without manual intervention.

#### Acceptance Criteria

1. WHEN code is pushed to GitHub main branch, THE CodePipeline SHALL automatically detect changes and trigger deployment
2. WHEN THE CodeBuild project executes, THE CodeBuild project SHALL package Lambda function with all Python dependencies
3. WHEN THE CloudFormation deploy stage executes, THE CloudFormation deploy stage SHALL create or update application stack resources
4. WHEN THE Lambda update stage executes, THE Lambda update stage SHALL update dashboard Lambda function code with new deployment package
5. WHEN deployment completes, THE Dashboard System SHALL be accessible at configured custom domain with updated functionality

### Requirement 9: Mobile Responsive Design

**User Story:** As a mobile user, I want the dashboard to work well on my phone, so that I can monitor my machine while away from my computer.

#### Acceptance Criteria

1. WHEN THE Dashboard System generates HTML, THE Dashboard System SHALL include viewport meta tags for mobile optimization
2. WHEN THE Dashboard System renders on screens smaller than 768 pixels, THE Dashboard System SHALL use single-column grid layout
3. WHEN THE Dashboard System renders on mobile devices, THE Dashboard System SHALL adjust font sizes and spacing for readability
4. WHEN THE Dashboard System renders charts on mobile, THE Dashboard System SHALL reduce chart height and adjust legend font sizes
5. WHEN THE Dashboard System detects touch devices, THE Dashboard System SHALL implement touch-friendly interactions without hover effects

### Requirement 10: Visual Enhancements

**User Story:** As a dashboard user, I want an attractive and engaging interface, so that monitoring my machine is enjoyable.

#### Acceptance Criteria

1. WHEN THE Dashboard System generates HTML, THE Dashboard System SHALL include Matrix-style coffee emoji background animation with user toggle control
2. WHEN THE Dashboard System retrieves machine image URL from API, THE Dashboard System SHALL display machine image in header section with responsive styling
3. WHEN THE Dashboard System generates HTML, THE Dashboard System SHALL include coffee emoji favicon for browser tabs and bookmarks
4. WHEN THE Dashboard System renders the dashboard, THE Dashboard System SHALL use dark theme with brown gradient background optimized for coffee shops
5. WHEN THE user toggles Matrix effect off, THE Dashboard System SHALL remove all Matrix columns and hide background container
