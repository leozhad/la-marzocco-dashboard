# La Marzocco Dashboard - Coding Standards

## Python Code Style

### General Guidelines
- Follow PEP 8 style guide
- Use Python 3.12 features and syntax
- Prefer async/await for I/O operations
- Use type hints where appropriate
- Keep functions focused and single-purpose

### Naming Conventions
- Classes: `PascalCase` (e.g., `LaMarzoccoDashboard`)
- Functions/Methods: `snake_case` (e.g., `collect_machine_data`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `CLOUDFRONT_DISTRIBUTION_ID`)
- Private methods: prefix with `_` (e.g., `_parse_power_status`)

### Code Organization
- Group related functionality into classes
- Use async context managers for resource management
- Implement proper error handling with try/except blocks
- Log important events and errors using Python logging module

### Example Pattern from Project
```python
class LaMarzoccoDashboard:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.secrets_client = boto3.client('secretsmanager')
        self.cloudfront_client = boto3.client('cloudfront')
        
        # Environment variables
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        self.secret_name = os.environ['LAMARZOCCO_SECRET_NAME']
        
    async def collect_machine_data(self) -> Dict[str, Any]:
        """Collect data from La Marzocco Cloud API"""
        credentials = await self.get_credentials()
        # Implementation...
```

## AWS Lambda Best Practices

### Lambda Handler Pattern
- Keep handler function minimal
- Delegate to class methods for business logic
- Return proper status codes and responses
- Handle exceptions gracefully

### Environment Variables
- Use environment variables for configuration
- Never hardcode credentials or secrets
- Validate required environment variables on initialization

### Resource Management
- Initialize AWS clients in `__init__` (reused across invocations)
- Use async/await for API calls
- Implement proper cleanup in finally blocks

### Error Handling
```python
try:
    # Main logic
    result = await self.collect_machine_data()
except Exception as e:
    logger.error(f"Error collecting machine data: {e}")
    # Return fallback data or raise
```

## CloudFormation Standards

### Template Organization
- Use clear, descriptive resource names
- Group related resources together
- Add comprehensive comments for complex logic
- Use Parameters for configurable values

### Resource Naming
- Use `!Sub` for dynamic names with stack context
- Include project name in resource names
- Use consistent naming patterns across resources

### Custom Resources
- Implement proper error handling
- Use cfnresponse for CloudFormation signals
- Clean up resources on DELETE events
- Log all operations for debugging

### Example Pattern
```yaml
LambdaExecutionRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub '${ProjectName}-lambda-role'
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: lambda.amazonaws.com
          Action: sts:AssumeRole
```

## Jinja2 Template Standards

### HTML Template Organization
- Embed CSS and JavaScript in single file for Lambda deployment
- Use semantic HTML5 elements
- Implement responsive design with mobile-first approach
- Add accessibility attributes (alt text, ARIA labels)

### Template Variables
- Use clear, descriptive variable names
- Implement safe defaults with conditional checks
- Format data appropriately (dates, numbers, etc.)

### Example Pattern
```jinja2
{% if status.coffee_boiler_temp %}
<div class="stat-row">
    <span class="stat-label">Coffee Boiler</span>
    <span class="stat-value temperature">
        {{ "%.1f"|format(status.coffee_boiler_temp) }}°F
        {% if status.coffee_boiler_ready %}✓{% endif %}
    </span>
</div>
{% endif %}
```

## Git Commit Standards

### Commit Message Format
- Use clear, descriptive commit messages
- Start with a verb (Add, Update, Fix, Remove, etc.)
- Reference issues or features when applicable
- Keep first line under 72 characters

### Examples
```
Add smart CloudFront invalidation to reduce costs
Update Lambda function to use installation key authentication
Fix power status parsing for new API format
Remove deprecated GitHub OAuth configuration
```

### Branch Strategy
- Main branch: `main` (production-ready code)
- Feature branches: `feature/description`
- Bugfix branches: `fix/description`
- Always merge via pull requests when working in teams

## Documentation Standards

### Code Comments
- Document complex logic and algorithms
- Explain "why" not "what" (code shows what)
- Keep comments up-to-date with code changes
- Use docstrings for functions and classes

### Docstring Format
```python
async def collect_machine_data(self) -> Dict[str, Any]:
    """
    Collect data from La Marzocco Cloud API.
    
    Returns:
        Dict containing comprehensive machine data including status,
        statistics, settings, and recent shot information.
        
    Raises:
        Exception: If API authentication fails or data collection errors occur.
    """
```

### README Updates
- Keep README.md synchronized with code changes
- Document new features and configuration options
- Update troubleshooting section with common issues
- Maintain accurate cost estimates

## Security Standards

### Credentials Management
- **NEVER** commit credentials to Git
- Use AWS Secrets Manager for sensitive data
- Use environment variables for configuration
- Rotate credentials regularly

### IAM Permissions
- Follow principle of least privilege
- Grant only necessary permissions
- Use resource-specific ARNs when possible
- Document permission requirements

### Example IAM Policy
```yaml
Policies:
  - PolicyName: DashboardLambdaPolicy
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Action:
            - s3:PutObject
            - s3:GetObject
          Resource: !Sub '${DashboardBucket.Arn}/*'
```

## Testing Standards

### Local Testing
- Test Lambda function locally before deployment
- Verify CloudFormation templates with `validate-template`
- Test with sample data when API is unavailable
- Check responsive design on multiple devices

### Integration Testing
- Test full pipeline deployment in non-production environment
- Verify CloudFront invalidation behavior
- Test error handling and fallback scenarios
- Monitor CloudWatch logs for issues

### Manual Testing Checklist
- [ ] Lambda function executes successfully
- [ ] Dashboard HTML renders correctly
- [ ] JSON data endpoint is accessible
- [ ] CloudFront serves content with proper caching
- [ ] Mobile responsive design works
- [ ] Auto-refresh functions properly

## Performance Standards

### Lambda Optimization
- Minimize cold start time
- Reuse AWS client connections
- Implement efficient data processing
- Use appropriate memory allocation (512MB for this project)

### Content Optimization
- Compress HTML and JSON output
- Use CloudFront caching effectively
- Implement smart invalidation to reduce costs
- Minimize external dependencies

### Caching Strategy
```python
# Cache content hashes in S3 for comparison
def has_content_changed(self, content: str, cache_key: str) -> bool:
    current_hash = self.get_content_hash(content)
    cached_hash = self.get_cached_hash(cache_key)
    return current_hash != cached_hash
```

## Deployment Standards

### Pre-Deployment Checklist
- [ ] Code reviewed and tested locally
- [ ] CloudFormation templates validated
- [ ] Environment variables configured
- [ ] Secrets Manager credentials updated
- [ ] Git commit message is descriptive

### Deployment Process
1. Commit changes to Git
2. Push to GitHub main branch
3. Monitor CodePipeline execution
4. Verify Lambda function updated
5. Test dashboard functionality
6. Check CloudWatch logs for errors

### Post-Deployment Verification
- [ ] Dashboard loads successfully
- [ ] Data is current and accurate
- [ ] No errors in CloudWatch logs
- [ ] CloudFront serving content properly
- [ ] SSL certificate valid

## Error Handling Standards

### Logging Levels
- `ERROR`: Critical failures requiring attention
- `WARNING`: Issues that don't prevent execution
- `INFO`: Important operational events
- `DEBUG`: Detailed diagnostic information

### Error Response Pattern
```python
try:
    result = await self.collect_machine_data()
    return result
except Exception as e:
    logger.error(f"Error collecting machine data: {e}")
    # Return fallback data with error information
    return {
        'error': str(e),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'collection_method': 'Fallback Data (API Error)'
    }
```

### Fallback Strategies
- Provide sensible default values
- Return cached data when available
- Display user-friendly error messages
- Log detailed error information for debugging

## Monitoring Standards

### CloudWatch Metrics
- Monitor Lambda execution duration
- Track error rates and failures
- Monitor CloudFront cache hit ratio
- Track S3 storage and requests

### Alerting
- Set up CloudWatch alarms for critical failures
- Monitor Lambda error rates
- Alert on CloudFormation stack failures
- Track cost anomalies

### Log Analysis
```bash
# Search for errors in Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "ERROR"

# Monitor invalidation decisions
aws logs filter-log-events \
  --log-group-name /aws/lambda/la-marzocco-dashboard-updater \
  --filter-pattern "invalidation"
```

## Maintenance Standards

### Regular Maintenance Tasks
- Review and rotate credentials quarterly
- Update Python dependencies for security patches
- Monitor AWS service deprecations
- Review and optimize costs monthly
- Update documentation with changes

### Dependency Updates
```bash
# Update requirements.txt
pip list --outdated
pip install --upgrade package-name
pip freeze > requirements.txt
```

### Infrastructure Updates
- Review CloudFormation templates for best practices
- Update Lambda runtime when new versions available
- Optimize IAM policies periodically
- Review and update security groups

## Code Review Standards

### Review Checklist
- [ ] Code follows project style guidelines
- [ ] No hardcoded credentials or secrets
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate and informative
- [ ] Documentation is updated
- [ ] Tests pass successfully
- [ ] Performance impact is acceptable
- [ ] Security best practices followed

### Review Focus Areas
- Security vulnerabilities
- Performance bottlenecks
- Error handling gaps
- Documentation completeness
- Code maintainability
- AWS cost implications
