# Releasing the dashboard

[Back to README](../README.md) · [Primary CodePipeline diagram](../generated-diagrams/github-pipeline-architecture.png) · [Alternative private release](../generated-diagrams/cicd-pipeline-architecture.png)

## Primary: GitHub and AWS CodePipeline

The primary deployment pipeline `la-marzocco-deployment-pipeline-pipeline` is defined in `cloudformation/pipeline.yaml`:

1. **Source:** GitHub `leozhad/la-marzocco-dashboard`, branch `main`, via `CodeStarSourceConnection` / CodeConnections. This action uses an authorized connection, not a GitHub PAT.
2. **Build:** CodeBuild reads the committed root `buildspec.yml`. Its default artifact export contains the source tree, CloudFormation template, and deployment ZIP.
3. **Deploy:** CloudFormation creates and executes the application change set at run orders 1 and 2. At run order 3, `la-marzocco-deployment-pipeline-update-lambda` extracts the build's Lambda ZIP and updates `la-marzocco-dashboard-updater`.

Push the tested, reviewed commit to GitHub `main`, monitor the pipeline execution, and verify the public snapshot after collection. This path watches GitHub; it does not consume private GitLab pushes. Scheduled EventBridge collection continues independently of either release path. Pipeline/stack update timestamps also do not describe the latest direct Lambda code release.

### Pipeline rollback

Revert the application change in Git and push the reviewed revert to GitHub `main` to run it through the same pipeline. Inspect any infrastructure changes in that revert before deployment; a Git revert does not undo external data changes. Verify the resulting pipeline execution and dashboard refresh.

## Alternative: private GitLab and AWS

The alternative manual release procedure uses committed source from the private `gitlab` remote, a per-build S3 source override on the existing CodeBuild project, and a direct Lambda code update. GitLab is source storage; it has no configured trigger for this AWS build. This procedure records the established operator-driven workflow; there is no checked-in end-to-end release command.

The existing installation uses region `us-west-2` and CLI profile `leo`. Resolve account-specific resource identifiers from AWS at deployment time rather than recording them in the repository. Explicitly verify the caller account. If a development environment redirects `AWS_CONFIG_FILE` or `AWS_SHARED_CREDENTIALS_FILE`, ensure the command uses the intended credential files; a profile name alone does not establish the account.

```bash
aws --profile leo --region us-west-2 sts get-caller-identity
git remote -v
git status --short
```

The `origin` remote has multiple push destinations, including GitHub. Use `git push gitlab main` for the private source path, and stage intended files explicitly: this checkout may contain untracked local captures or credential backups.

### Release sequence

1. **Test and commit.** Run both suites in the README, commit the reviewed files, and push that revision to `gitlab`. Record its full commit SHA. A documentation-only update does not require a Lambda deployment.
2. **Back up the current function.** Use `lambda get-function` to retrieve the deployed ZIP and configuration. Save the ZIP, `CodeSha256`, and `RevisionId` locally for comparison and rollback. Do not publish the temporary signed download URL.
3. **Archive committed source.** Use `git archive --format=zip <commit>` and upload the archive with AES256 server-side encryption to `manual-deployments/<commit>/source.zip` in the existing private artifact bucket. Do not zip the working directory.
4. **Start CodeBuild.** Use the project `la-marzocco-deployment-pipeline-build` with per-build overrides below. Wait for `SUCCEEDED`; inspect its CloudWatch log on failure. The buildspec runs Python and Node tests before producing `lambda-deployment-package.zip`.
5. **Inspect the artifact.** Download the outer build ZIP, extract `lambda-deployment-package.zip`, and compare the packaged `lambda_function.py` and every tracked `web/` file with the recorded commit. Confirm Python dependencies are present. Preserve the commit/build ID/artifact association.
6. **Update code.** Re-read the current function configuration and ensure its checksum still matches the backup. Call `lambda update-function-code` with the verified ZIP and current `--revision-id`, then wait with `lambda wait function-updated-v2`. Investigate a revision conflict rather than overwriting another deployment.
7. **Publish and verify.** Invoke the collector, check for `FunctionError` and a returned `statusCode` of 200, then inspect `/` and `/data.json`. Confirm the page references the new asset hash and exercise the relevant desktop/mobile interactions. A successful code upload alone does not prove successful collection or publication.

### CodeBuild overrides

Resolve the existing artifact bucket from the pipeline stack:

```bash
artifact_bucket=$(aws --profile leo --region us-west-2 cloudformation describe-stacks \
  --stack-name la-marzocco-deployment-pipeline \
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactsBucket'].OutputValue | [0]" \
  --output text)
```

Use `aws codebuild start-build --cli-input-json file://<request.json>` with an input object containing these fields. Replace `<commit>` with the recorded revision and `<artifact-bucket>` with the resolved bucket name:

```json
{
  "projectName": "la-marzocco-deployment-pipeline-build",
  "sourceTypeOverride": "S3",
  "sourceLocationOverride": "<artifact-bucket>/manual-deployments/<commit>/source.zip",
  "buildspecOverride": "<buildspec.yml contents with the artifact selection described below>",
  "artifactsOverride": {
    "type": "S3",
    "location": "<artifact-bucket>",
    "path": "manual-deployments/<commit>",
    "namespaceType": "NONE",
    "name": "build.zip",
    "packaging": "ZIP",
    "encryptionDisabled": false
  }
}
```

For `buildspecOverride`, preserve the committed build phases and replace only the artifact selection with:

```yaml
artifacts:
  files:
    - lambda-deployment-package.zip
```

Serialize this YAML as the JSON field's string value; the placeholder above is not executable input. The saved project's source and artifact types remain `CODEPIPELINE`. The per-build overrides do not reconfigure it or deploy CloudFormation changes.

### Manual release rollback

Use the previously downloaded Lambda ZIP, guarded by the current function `RevisionId`, to restore code. Wait for the update to finish, invoke the collector to republish the previous frontend, and verify the public page and JSON. Retained hashed asset bundles allow older HTML to keep loading its modules.

There is no documented `LIVE` alias or version-based release mechanism in these templates. A Git revert records a source change; it does not deploy automatically through the private path. If machine-cloud collection is unavailable during rollback, the last published snapshot remains until a successful refresh.

## Infrastructure and legacy tooling

Changes to the domain, schedule, resource configuration, or permissions require review and application of a CloudFormation change set. The private application-code procedure above does not apply these changes. `cloudformation/main.yaml` defines the app, while `cloudformation/pipeline.yaml` defines the build/deployment resources and shared login secret.

The old shell scripts need reconciliation before reuse:

- `deploy-pipeline.sh` still requires a GitHub token despite the connection-based source action.
- `deploy.sh` assembles a package locally and uses older credential parameters; it is not the current Linux/CodeBuild release procedure.
- `deploy-optimized.sh` targets the older alternate implementation in `src/lambda_function_optimized.py`.
- `cleanup.sh` performs destructive teardown; it is not part of a normal release or rollback.

See the README for local preview, tests, current resource identifiers, logs, and immediate refresh commands.
