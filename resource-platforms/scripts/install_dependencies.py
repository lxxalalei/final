#!/usr/bin/env python3
"""Install runtime dependencies for the platform-search skill."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None, dry_run: bool = False) -> None:
    print(f"+ {' '.join(cmd)}")
    if not dry_run:
        subprocess.check_call(cmd, cwd=str(cwd), env=env)


def node_env() -> dict[str, str]:
    env = dict(os.environ)
    options = env.get("NODE_OPTIONS", "")
    if "--use-system-ca" not in options:
        env["NODE_OPTIONS"] = f"{options} --use-system-ca".strip()
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="Install platform-search skill dependencies.")
    parser.add_argument("--skip-python", action="store_true", help="Do not install requirements.txt.")
    parser.add_argument("--skip-node", action="store_true", help="Do not install package.json dependencies.")
    parser.add_argument("--skip-playwright", action="store_true", help="Do not install Playwright Chromium.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    args = parser.parse_args()

    if not args.skip_python:
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], dry_run=args.dry_run)
    if not args.skip_node:
        run(["npm", "install"], env=node_env(), dry_run=args.dry_run)
    if not args.skip_playwright:
        run([sys.executable, "-m", "playwright", "install", "chromium"], dry_run=args.dry_run)
    print("platform-search dependencies are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
