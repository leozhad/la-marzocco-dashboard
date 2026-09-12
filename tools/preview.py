#!/usr/bin/env python3
"""Stage the production frontend locally using an existing machine-data snapshot."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lambda_function import LaMarzoccoDashboard, frontend_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Existing dashboard data.json")
    parser.add_argument("--output", type=Path, default=Path("build/preview"))
    args = parser.parse_args()
    data = json.loads(args.data.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    _, digest, assets = frontend_bundle()
    for name, content, _ in assets:
        destination = args.output / "assets" / digest / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    dashboard = object.__new__(LaMarzoccoDashboard)
    (args.output / "data.json").write_text(json.dumps(data, indent=2))
    (args.output / "index.html").write_text(dashboard.generate_dashboard_html(data))
    print(f"Preview staged at {args.output.resolve()} (assets: {digest})")


if __name__ == "__main__":
    main()
