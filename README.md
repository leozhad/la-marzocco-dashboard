# La Marzocco Dashboard

A personal dashboard for a connected Linea Mini: machine status, recent espresso shots, and an interactive 3D model of the owner's white, stainless-steel, and walnut machine.

**[Open the dashboard](https://espresso.leozh.net/)** · [Machine snapshot](https://espresso.leozh.net/data.json) · [Release guide](docs/deployment.md) · [Changelog](CHANGELOG.md)

## What it does

- **The machine:** a photo-informed 3D model with white side panels, walnut controls, visible indicator lights, and a Connected Scale recessed into the drip tray. Orbit the model, switch camera views, or inspect its cutaway and exploded views.
- **Brew log:** lifetime shot and flush counters, seven-day activity in the machine's timezone, and up to five recent shots with duration, beverage yield, temperature target, and brew ratio.
- **Shot replay:** click the modeled paddle or press **Play selected shot**. Follow the extraction in the exterior or **Look inside** view, including the controller and ESP32 connectivity gateway. Playback supports pause, reset, and 1×/2×/4× speed.
- **Machine information:** boiler targets/readiness, power and cloud connection, scale connection/battery, brew-by-weight settings, standby settings, and firmware information when supplied by the cloud feed.
- **Mobile and Matrix mode:** responsive layouts, opt-in touch interaction with the 3D model, and an optional persistent Matrix background. Reduced-motion preferences are respected.

The collector refreshes the snapshot **every five minutes**. An open browser checks for new JSON **every minute while visible**, preserves the selected shot and camera, and warns when readings are delayed. This is a read-only dashboard; its paddle and playback controls simulate a shot without operating the physical machine.

### Understanding the readings

| Display | Meaning |
| --- | --- |
| Brew ratio | Dry coffee mass : beverage mass, normalized to 1:x. An 18g dose yielding 36g espresso is **1:2**. |
| Dry dose | The owner's **18g recipe default**, adjustable globally or per shot in Brew log. Saved in that browser's localStorage. |
| Shot yield / `dose_value` | Recorded beverage output in grams. The cloud's brew-by-weight “dose” setting refers to output, not dry grounds. |
| Temperature | Brew-boiler or shot **target**, expressed in °F; not a continuous measured temperature trace. |
| Replay | Uses the recorded duration and final yield. Intermediate flow, cup fill, gauge needles, and internal motion are illustrative. |
| Scale | Connection, battery, and related settings when available. This collector does not receive live mass or measured dry coffee dose. |

The classic Linea Mini paddle moves **right (OFF) → left (BREW)** around a central pivot; the broad walnut cover stays fixed. In brew-by-weight replay, flow stops at the recorded yield while the manual paddle stays left until returned. The model is a visual reconstruction, not service CAD or a wiring guide.

## Architecture

![Scheduled collection and browser delivery for the La Marzocco dashboard](generated-diagrams/application-architecture.png)

[Editable draw.io source](docs/application-architecture.drawio) · [Diagram previews and regeneration](docs/diagrams.md)

1. An EventBridge rule invokes the Python 3.12 Lambda collector every five minutes.
2. Lambda retrieves the La Marzocco login from Secrets Manager, reuses an installation key stored in S3, and reads the **first machine** returned by the cloud account.
3. The pinned `pylamarzocco==2.4.3` client collects dashboard, settings, schedule, and statistics. A small adapter preserves shot weights, temperature targets, and daily flush counts omitted by its typed statistics models.
4. Lambda renders the Jinja page shell and publishes a static frontend to S3. CloudFront serves it over HTTPS using an ACM certificate in `us-east-1`; Route 53 provides the domain alias. Collection and storage run in `us-west-2`.
5. The browser renders the vendored Three.js model, shot replay, and charts locally. `/data.json` is a generated snapshot, not a request-time machine API.

### Publication and caching

Every Lambda package includes `web/` beside `lambda_function.py`. The publisher hashes static file paths and contents and uploads assets to `assets/<hash>/`. It writes an asset completion marker only after that bundle is uploaded, then publishes **JSON followed by HTML**. Older bundles remain available for previously cached pages.

Static assets carry a one-year immutable browser cache header. HTML and JSON use `no-cache, must-revalidate`; CloudFront also applies the limits configured in its cache behaviors. Content comparison excludes refresh timestamps. Meaningful changes invalidate `/` and `/index.html`, `/data.json`, or both as appropriate.

Collection failures preserve the last published snapshot. Asset upload failures occur before JSON/HTML publication. The two snapshot objects are written sequentially, so publication is not a multi-object atomic transaction.

### Data and access boundaries

The site and `data.json` are publicly readable and have no viewer sign-in. The snapshot includes machine identifiers and settings; inspect the published schema before adapting this project for another machine. La Marzocco login credentials are retrieved server-side from Secrets Manager. The S3 origin blocks direct public access and permits CloudFront through Origin Access Control.

S3 also holds publisher state under `.cache/`, including the installation key. That prefix is an object naming convention, **not an access-control boundary**: the checked-in bucket policy grants the distribution reads across the bucket. Do not describe the cache as isolated from the serving origin.

There is no server-side shot-history database: recent shots and daily aggregates come from the machine cloud. Recipe overrides and Matrix preferences are local to each browser.

## Develop locally

Use **Python 3.12** and **Node.js 20 or later**. Node is needed for the JavaScript unit tests; there is no npm install or frontend bundler. Three.js 0.170.0 and its companion modules are vendored under `web/vendor/`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

curl -fsS https://espresso.leozh.net/data.json -o /tmp/espresso-data.json
python tools/preview.py --data /tmp/espresso-data.json
python -m http.server 8769 --bind 127.0.0.1 --directory build/preview
```

Open **http://127.0.0.1:8769/**. The preview tool uses the production renderer with an existing snapshot and makes no AWS or machine API calls. The `curl` command above only downloads the public snapshot; substitute your own JSON file if desired. Regenerate the preview after edits, then reload the page.

### Checks

```bash
python -m unittest discover -s tests -p '*_test.py' -v
node --test tests/*_test.mjs
```

The Python suite mocks cloud access and covers statistics parsing, timezone grouping, rendering, publication order, and failure handling. Node tests cover ratios, replay timing, and paddle states. CodeBuild runs both suites before packaging.

For visual changes, check desktop and mobile layouts, tab switching, paddle/playback interactions, cutaway/exploded views, and Matrix/reduced-motion behavior. In the browser console, `window.espressoDiagnostics()` reports data freshness, selected shot, model/replay state, and Matrix state.

### Where to make changes

| Path | Responsibility |
| --- | --- |
| `src/lambda_function.py` | Cloud collection, statistics adapter, rendering, S3 publication, invalidation |
| `web/index.html` | Jinja page shell and embedded initial snapshot |
| `web/dashboard.js`, `web/dashboard.css` | Tabs, telemetry, brew log, refresh behavior, responsive layout |
| `web/machine.js` | Procedural 3D model, materials, cameras, cutaway/exploded views |
| `web/paddle-kinematics.mjs`, `web/shot-replay.mjs` | Paddle movement and illustrative extraction playback |
| `web/espresso-ratio.mjs`, `web/matrix.js` | Recipe ratios and optional background animation |
| `web/vendor/` | Three.js modules and upstream license |
| `tools/preview.py` | Local staging of the production frontend |
| `tests/` | Python and Node regression suites |
| `buildspec.yml` | Linux build, tests, and Lambda packaging |
| `cloudformation/main.yaml`, `cloudformation/pipeline.yaml` | Application and retained pipeline infrastructure |
| `docs/`, `generated-diagrams/` | Release guide, editable architecture diagrams, and PNG previews |
| `tools/generate_architecture_diagrams.py` | Reproducible diagram XML generation |

The root deployment shell scripts, `src/lambda_function_optimized.py`, `cloudformation/cache-optimization.yaml`, and root `lambda_*test*.json` captures belong to earlier workflows. They are retained for reference; use the current buildspec, preview tool, and release guide. The original `.kiro/specs/` documents are historical design records.

## Deployment

Current application releases use **private GitLab → committed source archive → AWS CodeBuild → Lambda code update**. A GitLab push records the source revision; an operator starts the AWS build and deployment separately.

![Private GitLab source built in CodeBuild and released to the dashboard Lambda](generated-diagrams/cicd-pipeline-architecture.png)

[Editable draw.io source](docs/cicd-pipeline-architecture.drawio) · [Release and rollback procedure](docs/deployment.md)

The existing CodePipeline still watches GitHub through CodeConnections. It builds the source, applies a CloudFormation change set, and invokes a helper Lambda to update application code. It is a **separate retained path**, not an automatic continuation of a private GitLab push. See the [GitHub pipeline diagram](generated-diagrams/github-pipeline-architecture.png) and [editable source](docs/github-pipeline-architecture.drawio).

The current private path deploys application code only. Infrastructure edits require a reviewed CloudFormation change set. Changing `.env` or pushing to GitLab does not update the deployed domain, schedule, or stack configuration. The legacy `deploy-pipeline.sh` still asks for a GitHub PAT, which the current CodeConnections source action does not use.

### Deployment reference

Configuration checked **2026-09-12**; these identifiers describe this installation, not defaults for a new deployment.

| Resource | Value |
| --- | --- |
| Public site | `https://espresso.leozh.net/` |
| AWS account / region | `<account-id>` / `us-west-2` |
| Application stack | `la-marzocco-dashboard` |
| Collector Lambda | `la-marzocco-dashboard-updater` — Python 3.12, 512 MB, 300s timeout |
| Schedule | `la-marzocco-dashboard-schedule` — `rate(5 minutes)` |
| Website bucket | `la-marzocco-dashboard-exwneqtv` |
| CloudFront distribution | `E1CKKDNSRS9CLJ` |
| Build project | `la-marzocco-deployment-pipeline-build` |
| Retained pipeline | `la-marzocco-deployment-pipeline-pipeline` |

Lambda requires `S3_BUCKET_NAME` and `LAMARZOCCO_SECRET_NAME`; `CLOUDFRONT_DISTRIBUTION_ID` enables invalidation. The secret contains `username` and `password`. Previewing and unit testing do not require these settings.

For a new installation, adapt the CloudFormation templates and parameters, provide a registered cloud-connected machine and Secrets Manager credentials, and package the collector using the buildspec. Domain provisioning expects an existing Route 53 hosted zone and creates a CloudFront certificate in `us-east-1`. The legacy shell scripts are not a maintained one-command bootstrap.

## Operations

These examples use the owner's `leo` CLI profile and explicitly select `us-west-2`. Use the credentials for the intended account and confirm identity before making changes; the profile's default region may differ.

```bash
aws --profile leo --region us-west-2 sts get-caller-identity
aws --profile leo --region us-west-2 logs tail \
  /aws/lambda/la-marzocco-dashboard-updater --since 1h
aws --profile leo --region us-west-2 codebuild list-builds-for-project \
  --project-name la-marzocco-deployment-pipeline-build --sort-order DESCENDING
```

| Symptom | Check |
| --- | --- |
| Old readings, but page loads | Inspect `data.json`'s `timestamp`, the enabled EventBridge rule, and collector logs. A collection error leaves old data available. |
| Missing or broken 3D model | Confirm the Lambda ZIP includes `web/`, the referenced `assets/<hash>/` files exist, and the browser console has no module-load errors. |
| Cloud authentication fails | Check Secrets Manager configuration and cloud-account machine registration. The collector persists its installation key in S3. |
| Wrong ratio | Edit the dry-dose recipe or per-shot override in Brew log. Scale connection does not provide dry coffee dose. |
| GitLab push did not deploy | Start the private release procedure; there is no GitLab-triggered AWS pipeline. |
| Failed retained pipeline | Inspect CodePipeline stage status, CodeBuild logs, and application CloudFormation events. |

To refresh immediately, invoke the collector and inspect its returned `statusCode`. **This publishes to the live website**; it is not a read-only test.

```bash
aws --profile leo --region us-west-2 lambda invoke \
  --function-name la-marzocco-dashboard-updater \
  --payload '{}' /tmp/espresso-refresh.json
cat /tmp/espresso-refresh.json
```

Operating cost depends on traffic, collection duration, build frequency, storage, and invalidation volume. The repository does not establish a measured monthly total or a fixed percentage saving; use actual AWS billing data for those figures.

## References

- [pylamarzocco](https://github.com/zweckj/pylamarzocco) — cloud client.
- [Linea Mini parts catalog](https://lamarzoccousa.com/wp-content/uploads/2019/04/Lineamini_Parts_Catalog_V1.5COLOR.pdf) and [classic Linea Mini manual](https://home.lamarzoccousa.com/wp-content/uploads/2023/09/Linea-Mini-Manual.pdf) — mechanical layout and paddle operation.
- [Connected Scale](https://home.lamarzoccousa.com/product/connected-scale/), [brew-by-weight](https://home.lamarzoccousa.com/using-brew-by-weight-with-the-linea-mini/), and [brew ratios](https://home.lamarzoccousa.com/using-espresso-brew-ratios/) — scale and recipe semantics.
- [Connected-machine retrofit guide](https://home.lamarzoccousa.com/installation-guide-linea-mini-connected-machine-retrofit-kit/) — gateway/controller context. PCB placement in the visualization is illustrative.
- [Connected Scale Drain Tray](https://home.lamarzoccousa.com/product/linea-mini-connected-scale-drain-tray/) — flush-mount reference. Its listed MI-series compatibility does not identify the owner's LM-series tray SKU.
- [AWS architecture diagram skill](https://github.com/awslabs/agent-plugins/tree/main/plugins/deploy-on-aws/skills/aws-architecture-diagram) — official AWS4 icon styling and draw.io workflow used for the diagrams.

## License

[MIT](LICENSE). Vendored Three.js code retains its [upstream MIT license](web/vendor/THREE-LICENSE.txt).
