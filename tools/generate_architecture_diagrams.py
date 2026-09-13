#!/usr/bin/env python3
"""Generate editable architecture diagrams; export previews with draw.io desktop.

Layout follows awslabs/agent-plugins' aws-architecture-diagram skill.
Uses only the Python standard library. See docs/diagrams.md for validation/export.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FONT = "fontFamily=Helvetica;"
INK = "light-dark(#232F3E,#F5F5F5)"
COLORS = {
    "compute": ("#FFF2E8", "#ED7100"),
    "network": ("#EDE7F6", "#8C4FFF"),
    "storage": ("#E8F5E9", "#3F8624"),
    "integration": ("#FCE4EC", "#E7157B"),
    "security": ("#FFEBEE", "#DD344C"),
    "developer": ("#EDE7F6", "#8C4FFF"),
    "management": ("#F5E6F7", "#C925D1"),
}


class Diagram:
    def __init__(self, name, title, subtitle, height=1100):
        self.name = name
        self.height = height
        self.file = ET.Element("mxfile", host="Electron", version="29.6.1")
        diagram = ET.SubElement(self.file, "diagram", name=title, id=name)
        model = ET.SubElement(
            diagram, "mxGraphModel", dx="2040", dy=str(height), grid="0",
            gridSize="10", guides="1", tooltips="1", connect="1", arrows="1",
            fold="1", page="0", pageScale="1", pageWidth="2040",
            pageHeight=str(height), math="0", shadow="0",
        )
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")
        self.text("title", title, 30, 25, 1280, 42, size=30, bold=True)
        self.text("subtitle", subtitle, 30, 70, 1280, 30, size=16)
        self.box("separator", "", 30, 105, 1280, 2,
                 "shape=line;strokeWidth=2;strokeColor=#FF9900;")
        self.box("aws-cloud", "AWS Cloud", 250, 140, 1060, height - 180,
                 "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud;"
                 "container=1;pointerEvents=0;collapsible=0;verticalAlign=top;"
                 "align=left;spacingLeft=30;fontSize=14;fontStyle=1;"
                 "fillColor=light-dark(#232F3E0D,#232F3E0D);fillStyle=auto;"
                 f"strokeColor=#232F3E;fontColor={INK};")
        self.box("legend-bg", "", 1350, 30, 650, height - 50,
                 "rounded=1;arcSize=3;fillColor=light-dark(#EDF3FF,#305363);"
                 "fillStyle=auto;strokeColor=#AABBD4;")
        self.text("legend-title", "How it works", 1380, 55, 580, 35, size=22, bold=True)

    def box(self, key, value, x, y, w, h, style, parent="1"):
        cell = ET.SubElement(self.root, "mxCell", id=key, value=value,
                             style=FONT + "html=1;" + style, vertex="1", parent=parent)
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w),
                      height=str(h), attrib={"as": "geometry"})
        return cell

    def text(self, key, value, x, y, w, h=40, size=14, bold=False):
        return self.box(key, value, x, y, w, h,
                        "text;whiteSpace=wrap;strokeColor=none;fillColor=none;"
                        f"fontColor={INK};align=left;verticalAlign=top;"
                        f"fontSize={size};fontStyle={int(bold)};")

    def region(self, key, label, x, y, w, h):
        self.box(key, label, x, y, w, h,
                 "shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_region;"
                 "container=0;pointerEvents=0;collapsible=0;"
                 "fillColor=light-dark(#0C7B7D0D,#0C7B7D0D);fillStyle=auto;"
                 "strokeColor=#00A4A6;fontColor=#00A4A6;dashed=1;"
                 "fontSize=14;fontStyle=1;align=left;verticalAlign=top;spacingLeft=30;")

    def service(self, key, category, label, sub, shape, color, x, y):
        tint, stroke = COLORS[color]
        self.box("container-" + key, category, x, y, 120, 120,
                 f"fillColor=light-dark({tint},#29333F);fillStyle=auto;"
                 f"strokeColor={stroke};fontColor={stroke};"
                 "rounded=1;arcSize=10;whiteSpace=wrap;verticalAlign=top;fontStyle=1;"
                 "fontSize=12;container=1;pointerEvents=0;collapsible=0;strokeWidth=1.5;")
        self.box(key, f"{label}<div><i>{sub}</i></div>", 36, 30, 48, 48,
                 "sketch=0;outlineConnect=0;shape=mxgraph.aws4.resourceIcon;"
                 f"resIcon=mxgraph.aws4.{shape};fillColor={stroke};strokeColor=#FFFFFF;"
                 f"fontColor={INK};fontSize=10;fontStyle=0;"
                 "verticalLabelPosition=bottom;verticalAlign=top;align=center;"
                 "labelWidth=116;whiteSpace=wrap;aspect=fixed;",
                 parent="container-" + key)

    def actor(self, key, label, shape, x, y):
        self.box(key, label, x, y, 140, 120,
                 "rounded=1;whiteSpace=wrap;verticalAlign=top;spacingTop=8;"
                 "fontStyle=1;fontSize=12;container=1;pointerEvents=0;collapsible=0;"
                 "fillColor=light-dark(#F5F5F5,#29333F);fillStyle=auto;"
                 f"strokeColor=light-dark(#666666,#D4D4D4);fontColor={INK};")
        self.box(key + "-icon", "", 46, 48, 48, 48,
                 "shape=mxgraph.aws4.resourceIcon;"
                 f"resIcon=mxgraph.aws4.{shape};fillColor=#545B64;strokeColor=#FFFFFF;",
                 parent=key)

    def edge(self, key, source, target, label="", ports=(1, .5, 0, .5),
             points=(), label_pos=0, label_offset=16):
        ex, ey, ix, iy = ports
        cell = ET.SubElement(
            self.root, "mxCell", id=key, edge="1", parent="1", source=source, target=target,
            style=FONT + "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
            "endArrow=block;endFill=1;strokeWidth=1.5;"
            "strokeColor=light-dark(#545B64,#D4D4D4);"
            f"exitX={ex};exitY={ey};entryX={ix};entryY={iy};",
        )
        geom = ET.SubElement(cell, "mxGeometry", relative="1", attrib={"as": "geometry"})
        if points:
            arr = ET.SubElement(geom, "Array", attrib={"as": "points"})
            for x, y in points:
                ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
        if label:
            child = ET.SubElement(
                self.root, "mxCell", id=key + "-label", value=label,
                style=FONT + "edgeLabel;html=1;align=center;verticalAlign=middle;"
                f"fontColor={INK};fontSize=11;labelBackgroundColor=none;",
                vertex="1", connectable="0", parent=key,
            )
            ET.SubElement(child, "mxGeometry", relative="1", x=str(label_pos),
                          y=str(label_offset), attrib={"as": "geometry"})

    def step(self, n, title, description, x, y, legend_y):
        style = ("rounded=1;fillColor=#007CBD;strokeColor=default;"
                 "strokeWidth=2;shadow=1;glass=0;fontColor=#FFFFFF;"
                 "fontStyle=1;align=center;verticalAlign=middle;")
        self.box(f"step-{n}", str(n), x, y, 28, 28, style + "fontSize=16;")
        self.box(f"legend-badge-{n}", str(n), 1380, legend_y, 40, 38,
                 style + "fontSize=22;")
        self.text(f"legend-copy-{n}",
                  f"<b>{title}</b><div><span style=\"color: light-dark(rgb(0,0,0), "
                  f"rgb(255,255,255));\">{description}</span></div>",
                  1432, legend_y, 538, 90)

    def save(self):
        path = ROOT / "docs" / (self.name + ".drawio")
        path.parent.mkdir(exist_ok=True)
        ET.indent(self.file)
        ET.ElementTree(self.file).write(path, encoding="unicode")
        print(path.relative_to(ROOT))


def application():
    d = Diagram("application-architecture", "La Marzocco dashboard",
                "Scheduled cloud snapshots · static delivery · interactive 3D in the browser", 1140)
    d.region("region-west", "us-west-2 · collection and storage", 280, 600, 1000, 490)
    d.actor("browser", "Web browser", "users", 30, 400)
    d.actor("lm-cloud", "La Marzocco<br>Cloud API", "internet", 30, 880)
    d.text("machine-note", "Linea Mini + ESP32 gateway<br>and Connected Scale<br><br>"
           "Machine telemetry reaches<br>La Marzocco's cloud.", 30, 730, 185, 125)
    d.text("browser-note", "Three.js model + shot replay<br>Recipe doses and Matrix<br>"
           "preferences stay in<br>browser localStorage.", 30, 550, 190, 100)
    d.service("dns", "DNS", "Amazon Route 53", "Domain alias", "route_53", "network", 320, 220)
    d.service("cdn", "Delivery", "Amazon CloudFront", "HTTPS + OAC", "cloudfront", "network", 620, 400)
    d.service("cert", "TLS certificate", "ACM", "us-east-1", "certificate_manager_3", "security", 920, 220)
    d.service("schedule", "Schedule", "Amazon EventBridge", "Every 5 minutes", "eventbridge", "integration", 320, 660)
    d.service("collector", "Compute", "AWS Lambda", "Collect + render", "lambda", "compute", 620, 660)
    d.service("site", "Storage", "Amazon S3", "Site + state", "s3", "storage", 920, 660)
    d.service("secret", "Credentials", "Secrets Manager", "Cloud login", "secrets_manager", "security", 620, 920)
    d.edge("schedule-collect", "schedule", "collector", "invoke")
    d.edge("collect-secret", "collector", "secret", "read credentials", (.5, 1, .5, 0))
    d.edge("collect-api", "collector", "lm-cloud", "HTTPS reads", (0, .8, 1, .5),
           [(570, 728), (570, 934), (220, 934)], label_pos=.1)
    d.edge("collect-site", "collector", "site", "assets → JSON → HTML")
    d.edge("dns-browser", "dns", "browser", "DNS lookup / alias", (0, .5, .5, 0),
           [(240, 274), (100, 274)], label_pos=.1)
    d.edge("cert-cdn", "cert", "cdn", "TLS certificate", (.5, 1, .5, 0),
           [(980, 370), (680, 370)])
    d.edge("browser-cdn", "browser", "cdn", "HTTPS · JSON poll every 60s", (1, .45, 0, .5))
    d.edge("cdn-site", "cdn", "site", "S3 origin reads · OAC", (1, .5, .5, 0),
           [(980, 454)], label_pos=-.3)
    d.edge("collect-invalidate", "collector", "cdn", "invalidate changed paths", (.75, 0, .75, 1),
           [(692, 560)], label_offset=-80)
    d.text("state-note", "S3 state: installation key, content hashes, asset completion markers.<br>"
           "Site objects: index.html, data.json, assets/&lt;hash&gt;/*.<br>"
           "Collection errors leave the last published snapshot available.",
           870, 875, 370, 120)
    steps = [
        ("Collect on a schedule", "EventBridge invokes the Python 3.12 collector every five minutes.", 470, 675),
        ("Authenticate the collector", "Lambda reads the cloud login from Secrets Manager and reuses the installation key stored in S3.", 735, 812),
        ("Read the machine snapshot", "pylamarzocco queries La Marzocco's cloud. The dashboard does not connect directly to the machine or scale.", 510, 815),
        ("Publish a complete frontend", "Upload hashed assets first, then data.json, then index.html. Reuse existing asset bundles on later refreshes.", 770, 620),
        ("Resolve the public domain", "Route 53 points espresso.leozh.net to CloudFront. DNS is separate from the HTTP request path.", 265, 225),
        ("Provide HTTPS", "CloudFront uses an ACM certificate issued in us-east-1. The collection workload runs in us-west-2.", 1055, 345),
        ("Read and explore", "CloudFront serves the S3 content. The browser polls JSON every minute while visible; replay and 3D controls run locally.", 205, 415),
        ("Refresh changed content", "Lambda invalidates /, /index.html and /data.json as needed. Timestamp-only changes do not trigger invalidations.", 735, 550),
    ]
    for n, (title, desc, x, y) in enumerate(steps, 1):
        d.step(n, title, desc, x, y, 115 + (n - 1) * 117)
    d.save()


def release():
    d = Diagram("cicd-pipeline-architecture", "Private-source release workflow",
                "Current application releases · private GitLab source · AWS CodeBuild packaging", 980)
    d.region("region-west", "us-west-2", 280, 210, 1000, 680)
    d.actor("gitlab", "Private GitLab<br>repository", "internet", 30, 260)
    d.actor("operator", "Release operator<br>local Git + AWS CLI", "generic_application", 30, 640)
    d.service("source", "Build input", "Amazon S3", "Committed archive", "s3", "storage", 340, 300)
    d.service("build", "Build + test", "AWS CodeBuild", "buildspec.yml", "codebuild", "developer", 640, 300)
    d.service("artifact", "Build output", "Amazon S3", "Lambda ZIP", "s3", "storage", 940, 300)
    d.service("target", "Application", "AWS Lambda", "Dashboard updater", "lambda", "compute", 640, 680)
    d.edge("gitlab-operator", "gitlab", "operator", "same committed revision", (.5, 1, .5, 0))
    d.edge("operator-source", "operator", "source", "git archive → S3", (1, .2, 0, .5),
           [(230, 664), (230, 354)])
    d.edge("source-build", "source", "build", "S3 source override")
    d.edge("build-artifact", "build", "artifact", "tests pass → ZIP")
    d.edge("artifact-operator", "artifact", "operator", "download + verify", (.5, 1, 1, .4),
           [(1000, 520), (210, 520), (210, 688)], label_pos=-.2)
    d.edge("operator-target", "operator", "target", "UpdateFunctionCode + invoke", (1, .8, 0, .5),
           [(450, 736), (450, 734)])
    d.text("artifact-note", "Input and output use separate keys<br>in the existing private artifact bucket.",
           890, 570, 340, 65)
    d.text("publish-note", "After code update: invoke the collector,<br>then verify the public dashboard.<br>"
           "See the application architecture for publishing.", 850, 720, 385, 100)
    d.text("no-trigger-note", "GitLab stores source.<br>A push alone does not<br>start an AWS deployment.",
           30, 805, 190, 80)
    steps = [
        ("Record the source revision", "Commit and push to the private gitlab remote. Archive that exact committed revision; exclude local untracked files.", 135, 420),
        ("Stage the build input", "Upload source.zip under manual-deployments/&lt;commit&gt;/ in the existing private S3 artifact bucket.", 260, 480),
        ("Start the managed build", "An operator starts CodeBuild with per-build S3 source/artifact overrides. The saved project remains CodePipeline-backed.", 490, 260),
        ("Test and package", "CodeBuild runs Python and Node tests and packages the Python module, dependencies and web/ in lambda-deployment-package.zip.", 790, 260),
        ("Check the release artifact", "Download the output and compare the packaged application files with the committed source. Retain the prior Lambda ZIP for rollback.", 1070, 440),
        ("Update and verify", "Use the Lambda revision ID to guard the code update, invoke the collector, and verify its response plus the public HTML and JSON.", 270, 745),
    ]
    for n, (title, desc, x, y) in enumerate(steps, 1):
        d.step(n, title, desc, x, y, 120 + (n - 1) * 125)
    d.text("legend-scope", "<b>Application code releases only</b><br>"
           "This path does not execute a CloudFormation change set.<br>"
           "The retained GitHub pipeline is documented separately.",
           1380, 875, 580, 80)
    d.save()


def retained_pipeline():
    d = Diagram("github-pipeline-architecture", "Retained GitHub deployment pipeline",
                "Configured infrastructure path · distinct from the current private-source release workflow", 980)
    d.region("region-west", "us-west-2 · CodePipeline orchestration", 280, 210, 1000, 680)
    d.actor("github", "GitHub repository<br>main branch", "internet", 30, 300)
    d.service("pipeline", "Orchestration", "AWS CodePipeline", "Source → build", "codepipeline", "developer", 340, 300)
    d.service("build", "Build + test", "AWS CodeBuild", "buildspec.yml", "codebuild", "developer", 640, 300)
    d.service("artifacts", "Artifacts", "Amazon S3", "Source + build", "s3", "storage", 940, 300)
    d.service("stack", "Infrastructure", "AWS CloudFormation", "App change set", "cloudformation", "management", 940, 680)
    d.service("updater", "Code delivery", "AWS Lambda", "Pipeline updater", "lambda", "compute", 640, 680)
    d.service("target", "Application", "AWS Lambda", "Dashboard updater", "lambda", "compute", 340, 680)
    d.edge("github-pipeline", "github", "pipeline", "CodeConnections", (1, .45, 0, .5))
    d.edge("pipeline-build", "pipeline", "build", "Build stage")
    d.edge("build-artifacts", "build", "artifacts", "BuildOutput")
    d.edge("artifacts-stack", "artifacts", "stack", "template + parameters", (.5, 1, .5, 0))
    d.edge("stack-updater", "stack", "updater", "Deploy · run order 3", (0, .5, 1, .5))
    d.edge("artifacts-updater", "artifacts", "updater", "read packaged ZIP", (.2, 1, .5, 0),
           [(966, 550), (700, 550)])
    d.edge("updater-target", "updater", "target", "UpdateFunctionCode", (0, .5, 1, .5))
    d.text("pipeline-scope", "Arrows show pipeline stage order and artifact flow.<br>"
           "CodePipeline starts the CloudFormation and updater actions.", 390, 830, 820, 45)
    d.text("github-note", "This configuration watches<br>GitHub, not GitLab.<br>"
           "Current releases use the<br>private workflow diagram.", 30, 485, 190, 100)
    steps = [
        ("Fetch GitHub source", "The configured source action watches leozhad/la-marzocco-dashboard:main through a CodeStarSourceConnection action.", 205, 280),
        ("Build the source artifact", "CodePipeline starts the same CodeBuild project used by private releases. This path uses its default CODEPIPELINE source.", 490, 260),
        ("Store build artifacts", "The default buildspec exports the build tree, including cloudformation/main.yaml and the Lambda deployment ZIP.", 790, 260),
        ("Apply infrastructure changes", "Deploy run orders 1 and 2 create and execute the application CloudFormation change set.", 1070, 495),
        ("Deliver application code", "After the change set completes, CodePipeline invokes the helper Lambda at run order 3. It extracts the ZIP from BuildOutput.", 790, 685),
        ("Resume scheduled collection", "The helper updates the dashboard Lambda's code. EventBridge continues invoking the collector every five minutes.", 490, 685),
    ]
    for n, (title, desc, x, y) in enumerate(steps, 1):
        d.step(n, title, desc, x, y, 120 + (n - 1) * 125)
    d.text("legend-scope", "<b>Configured, not the current release route</b><br>"
           "A private GitLab push does not trigger this pipeline.<br>"
           "No GitHub personal access token is used by its source action.",
           1380, 875, 580, 80)
    d.save()


if __name__ == "__main__":
    application()
    release()
    retained_pipeline()
