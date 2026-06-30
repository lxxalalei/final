#!/usr/bin/env python3
"""Generic public-web search adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shared.platform_base import CLIBasedPlatformSkill


class GenericSkill(CLIBasedPlatformSkill):
    platform_name = "generic"

    def _build_search_cmd(self, intent: dict[str, Any], output_file: Path) -> list[str] | None:
        if self._search_script is None or not self._search_script.exists():
            return None
        keywords = intent.get("keywords") or intent.get("query") or ""
        if not keywords:
            return None
        params = intent.get("params") if isinstance(intent.get("params"), dict) else {}
        if not params and isinstance(intent.get("search_params"), dict):
            params = intent["search_params"]
        engines = intent.get("engines") or params.get("engines") or ["baidu", "bing"]
        if not isinstance(engines, list):
            engines = ["baidu", "bing"]
        max_results = intent.get("max_results") or 20
        return [
            sys.executable,
            str(self._search_script),
            "search",
            keywords,
            "--max",
            str(max_results),
            "--engines",
            ",".join(engines),
            "-o",
            str(output_file),
        ]
