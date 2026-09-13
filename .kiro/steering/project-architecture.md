# Project architecture

The [README](../../README.md) is the maintained architecture and development guide. Use these generated diagrams rather than creating additional text sketches:

- [Runtime and data flow](../../generated-diagrams/application-architecture.png) — [editable source](../../docs/application-architecture.drawio).
- [Current private release workflow](../../generated-diagrams/cicd-pipeline-architecture.png) — [editable source](../../docs/cicd-pipeline-architecture.drawio).
- [Retained GitHub pipeline](../../generated-diagrams/github-pipeline-architecture.png) — [editable source](../../docs/github-pipeline-architecture.drawio).

See [diagram maintenance](../../docs/diagrams.md) and the [release guide](../../docs/deployment.md).

## Implementation constraints

- Active collector: `src/lambda_function.py`, Python 3.12, pinned `pylamarzocco==2.4.3`. The optimized alternate module is legacy.
- `DashboardCloudClient` preserves raw statistics fields omitted by the client's typed models. The collector selects the first machine returned by the account.
- EventBridge collection runs every five minutes. A visible browser polls generated `data.json` every minute. There is no request-time machine API or machine-control endpoint.
- Package `web/` alongside `lambda_function.py`. Upload content-hashed static assets completely before JSON and HTML. Keep prior asset bundles for older pages.
- Collection failure leaves the last successful snapshot published. JSON and HTML writes are sequential, not atomic.
- Browser modules use vendored Three.js. Exterior and internal views share a renderer and preserve camera/replay state.
- Dry coffee dose defaults to the owner-provided 18g and can be overridden in browser localStorage. Cloud brew-by-weight doses are beverage outputs; do not infer dry mass from scale connection.
- Replay endpoints use recorded duration/yield. Intermediate flow, pressure gauges, and internal PCB geometry are illustrative. Paddle clicks do not control the real machine.
- The public site has no viewer authentication. A `.cache/` object prefix does not isolate objects from the CloudFront origin's bucket read permissions.

## Deployment constraints

- Current releases push committed source to the private `gitlab` remote, then explicitly run CodeBuild with per-build S3 overrides and update Lambda code. A GitLab push alone does not deploy.
- The retained CodePipeline watches GitHub through CodeConnections. Do not describe it as the private source path or instruct contributors to add a GitHub PAT.
- Application code updates do not apply CloudFormation changes. Use a reviewed change set for infrastructure changes.
- Verify the intended AWS account and specify the region explicitly. This installation uses account `<account-id>`, profile `leo`, and `us-west-2`; its CloudFront certificate is in `us-east-1`.
- Preserve user credential configuration. Preview and unit tests need no cloud credentials.
- Root captures, legacy scripts, and timestamped local backups are not release source. Stage intended files and build from the committed archive.
