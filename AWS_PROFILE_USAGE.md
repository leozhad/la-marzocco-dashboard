# AWS Profile Usage Guide

This project has been designed to work with any AWS CLI profile configuration. Here's how to use different profiles:

## Environment Variable Method (Recommended)

Set the `AWS_PROFILE` environment variable before running any scripts:

```bash
export AWS_PROFILE=your-profile-name
./deploy.sh
./deploy-pipeline.sh
./cleanup.sh
```

## Per-Command Method

Set the profile for individual commands:

```bash
AWS_PROFILE=your-profile-name ./deploy.sh
AWS_PROFILE=your-profile-name ./deploy-pipeline.sh
```

## Default Profile

If no profile is specified, the scripts will use your default AWS CLI profile.

## Examples

```bash
# Using a specific profile
export AWS_PROFILE=production
./deploy.sh

# Using default profile
./deploy.sh

# One-time profile usage
AWS_PROFILE=staging ./deploy-pipeline.sh
```

## Security Note

All sensitive credentials (La Marzocco API credentials and GitHub tokens) are now stored securely in AWS Secrets Manager:

- **La Marzocco Credentials**: `la-marzocco-pipeline-credentials`
- **GitHub Token**: `la-marzocco-github-token`

No sensitive information is stored in this repository or configuration files.
