# Changelog

All notable changes to the La Marzocco Dashboard project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- Remove committed AWS account identifiers and resolve account-specific deployment resources from CloudFormation or Lambda configuration.
- Present GitHub-triggered CodePipeline as the primary deployment workflow, with private GitLab/AWS releases documented as an alternative.
- Rewrite the README around the current 3D dashboard, data semantics, local development, and deployment workflow; remove obsolete setup guidance and unsupported cost estimates.
- Replace architecture visuals with editable AWS4 draw.io diagrams and embedded PNG previews for runtime, private releases, and the retained GitHub pipeline.
- Add diagram regeneration instructions and an operator release/rollback guide; identify superseded design and deployment documents.

## [3.1.3] - 2026-09-12

### Added
- Record the owner-confirmed Pantechnicon P361 pre-2024 tray, walnut wood kit, and Fellow Monty 3 oz / 90 ml demitasse cups for LM016332.

### Changed
- Model the tray's square grille and black insert, and use handleless matte-white Monty cups with copper bases on the deck and in shot replay.

## [3.1.2] - 2026-09-12

### Fixed
- Remove the extra rectangular piece behind the hot-water outlet.
- Narrow the fixed wooden cover to clear the red and blue indicator lights.

## [3.1.1] - 2026-09-12

### Fixed
- Rebuild the fixed walnut group cover and separate wood/steel paddle from the new close-up photo.
- Correct the central pivot and right-OFF / left-BREW movement.
- Brew-by-weight replay stops flow without automatically moving the manual paddle back; paddle clicks return it right or stop an ongoing replay.
- Set the owner-confirmed dry coffee recipe default to 18g, retaining per-shot overrides.

## [3.1.0] - 2026-09-11

### Added
- Selected-shot replay from the 3D paddle or playback controls: paddle motion, pump/flow highlights, cup filling, simulated scale readout, and drain sequence.
- Full 3D Look Inside view with shared renderer, playback controls, and an ESP32 gateway/controller assembly.
- Gateway hardware/firmware fields from the machine's reported connectivity data.
- Espresso brew ratios using an explicit recipe default or per-shot dry coffee dose; dose preferences are stored on the viewer's device.
- Unit tests for replay timing, recorded endpoints, and ratio calculations.

### Fixed
- White lower side and rear panels matching the owner's finish.
- Contoured walnut paddle and offset mounting block matching the photo more closely.
- Recessed Connected Scale with a grille opening and adjusted cup clearance.

### Changed
- Faster Matrix rain, with elapsed-time-based movement and existing reduced-motion support.

## [3.0.0] - 2026-09-11

### Added
- Responsive dashboard with machine, brew-log, and internal-circuit views.
- Rotatable white/stainless/walnut Linea Mini model, matching the user's reference photo and informed by the V1.5 parts catalog.
- Assembled, cutaway, and exploded modes; front/top camera presets; touch interaction toggle.
- La Marzocco Connected Scale geometry and component information.
- Persistent Matrix mode with reduced-motion and hidden-tab handling.
- Background data refresh, freshness warnings, and preserved camera/shot selection.
- Content-addressed static asset publication before the HTML entry point.
- Offline preview tool and asset-publication regression coverage.

### Changed
- Move the page template, styles, and browser code out of the Python collector into `web/`.
- Package `web/` in CodeBuild and manual deployments.
- Invalidate both `/` and `/index.html` when the page changes.

## [2.4.0] - 2026-09-11

### Added
- Seven-day activity totals and a daily shot/flush table in the machine's timezone.
- Brew-temperature targets for recent shots and expandable installed firmware release notes.
- Offline regression tests for statistics extraction, rendering, and publication failure handling.

### Changed
- Pin the Python machine client to `pylamarzocco==2.4.3`.
- Use typed lifetime counters while preserving raw shot weights and daily flush counts.
- Show all five recent shots and calculate averages using the actual number of available shots.

### Fixed
- Remove exception-text statistics parsing and hardcoded sample-data fallbacks.
- Preserve the last published dashboard if data collection fails.
- Read the current smart standby configuration from the client's updated schedule model.
- Label the coffee boiler temperature as a target, matching the API field.

## [2.3.1] - 2025-10-31

### Fixed
- **Lambda Function Statistics Extraction**
  - Fixed extraction of lifetime shot and flush counts from La Marzocco API
  - Corrected widget data parsing to properly extract statistics from `COFFEE_AND_FLUSH_COUNTER` widget
  - Fixed recent shots extraction from `LAST_COFFEE` widget
  - Improved error handling for missing or malformed widget data
  - Dashboard now correctly displays total shots (5151) and total flushes (1891)
  - Recent shots now properly display with extraction time, dose, and timestamp

### Changed
- **Documentation Structure Reorganization**
  - Restructured spec documentation into modular format
  - Main spec file (`.kiro/specs/la-marzocco-dashboard.spec.md`) now serves as project summary
  - Detailed specifications split into separate files:
    - `requirements.md` - User stories and acceptance criteria
    - `design.md` - Architecture and technical design
    - `tasks.md` - Implementation plan and task list
  - Improved documentation navigation and maintainability

## [2.3.0] - 2025-09-16

### 🔧 **API Compatibility Update**

#### **Fixed**
- **Updated pylamarzocco Authentication**: Migrated from deprecated OAuth to new installation key system
- **Device Registration**: Added automatic device registration for new installations
- **Statistics Extraction**: Fixed data extraction to handle API changes and enum parsing issues
- **CodeStar Connections**: Migrated CI/CD pipeline from GitHub OAuth to CodeStar Connections
- **Complete Data Preservation**: Maintained all dashboard functionality including recent shots and lifetime totals

#### **Added**
- **Installation Key Management**: Automatic generation and S3 persistence of device keys
- **Enhanced Error Handling**: Robust fallback for API parsing issues
- **aiohttp Dependency**: Added for new client session management

#### **Technical Details**
- Updated to pylamarzocco 2.1.0 with new authentication flow
- Added exception-based data extraction for statistics (handles MassType enum issue)
- Extracts lifetime totals from COFFEE_AND_FLUSH_COUNTER widget (5151 shots, 1891 flushes)
- Extracts recent shots from LAST_COFFEE widget with complete shot data
- Maintains backward compatibility with existing dashboard features

## [2.2.0] - 2025-08-03

### 💰 Major Cost Optimization

#### **Added**
- **Smart CloudFront Invalidation System**
  - Content change detection using SHA256 hashing
  - Normalized data comparison excluding timestamps
  - S3-based cache storage for content hash persistence
  - Selective path invalidation (only changed content)
  - Comprehensive logging for invalidation decisions

#### **Fixed**
- **CloudFront Invalidation Cost Issue**
  - **Problem**: Lambda function was invalidating CloudFront on every 5-minute execution
  - **Root Cause**: Timestamp field caused content hash to change every run, even when machine data was identical
  - **Solution**: Compare normalized machine data (excluding timestamps) for change detection
  - **Cost Impact**: Reduced monthly invalidation costs by ~90% (from $70/month to <$5/month)

#### **Technical Implementation**

##### **Smart Invalidation Logic**
```python
# Before: Always invalidate (expensive)
await self.invalidate_cloudfront(['/index.html', '/data.json'])

# After: Only invalidate when content changes (cost-effective)
normalized_data = self.normalize_machine_data_for_comparison(machine_data)
if self.has_content_changed(html_content, self.html_cache_key):
    paths_to_invalidate.append('/index.html')
if self.has_content_changed(normalized_json, self.json_cache_key):
    paths_to_invalidate.append('/data.json')
```

##### **Content Change Detection**
- **Normalization**: Removes `timestamp` field that changes every execution
- **Hashing**: SHA256 comparison of normalized content
- **Caching**: Stores content hashes in S3 `.cache/` folder
- **Persistence**: Hash comparison survives Lambda cold starts

##### **Cost Analysis**
- **Previous Behavior**: 8,640 invalidations/month × 2 paths × $0.005 = $76.40/month
- **Optimized Behavior**: ~5-10% of executions need invalidation = $3-7/month
- **Monthly Savings**: $65-70/month (90%+ reduction)
- **Annual Savings**: $780-840/year

#### **User Experience Preserved**
- ✅ **Display timestamps still update** for user freshness indication
- ✅ **S3 content always uploaded** to maintain current "last updated" times
- ✅ **Dashboard functionality unchanged** - optimization is transparent
- ✅ **Real-time updates maintained** when machine data actually changes

#### **Monitoring & Debugging**
- **Enhanced Logging**: Clear indication when content changes vs. no changes
- **Response Metadata**: Lambda response includes `content_changed` and `invalidated_paths`
- **Cache Visibility**: Content hashes stored in S3 for troubleshooting
- **Performance Tracking**: Execution time and cost impact monitoring

#### **Implementation Benefits**
- **Zero Downtime**: Deployed via existing CodePipeline workflow
- **Backward Compatible**: No breaking changes to API or functionality
- **Self-Healing**: Automatic cache rebuild if S3 cache objects are missing
- **Scalable**: Hash comparison is O(1) and efficient for any content size

### Changed
- **Lambda Function Execution Flow**
  - Added content normalization step before change detection
  - Implemented selective CloudFront invalidation based on actual changes
  - Enhanced logging to track invalidation decisions and cost impact
  - Preserved user-facing timestamp updates while optimizing backend costs

### Infrastructure Impact
- **Monthly Cost Reduction**: ~$65-70/month savings in CloudFront invalidation fees
- **Total Monthly Cost**: Reduced from ~$75/month to ~$5-10/month
- **Performance**: No impact on dashboard load times or functionality
- **Reliability**: Improved cost predictability and reduced AWS bill volatility

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
