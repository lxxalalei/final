#!/usr/bin/env python3
"""Generic public-web search adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shared.search_adapter import CLISearchAdapter, SCRIPTS_DIR


ENGINE_PRESETS = {
    "web": ["bing", "duckduckgo", "baidu"],
    "global": ["duckduckgo", "bing", "jina"],
    "china": ["baidu", "bing"],
    "dev": ["github", "bing", "duckduckgo"],
    "all": ["bing", "duckduckgo", "baidu", "jina", "github"],
}


def _coerce_engines(value: Any) -> list[str]:
    if value is None or value == "":
        return ENGINE_PRESETS["web"]
    if isinstance(value, str):
        tokens = [part.strip().lower() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        tokens = [str(part).strip().lower() for part in value if str(part).strip()]
    else:
        tokens = []
    output: list[str] = []
    for token in tokens:
        output.extend(ENGINE_PRESETS.get(token, [token]))
    return list(dict.fromkeys(output)) or ENGINE_PRESETS["web"]


class GenericSearchAdapter(CLISearchAdapter):
    platform_name = "generic"
    search_script = SCRIPTS_DIR / "generic" / "generic_search.py"

    def _build_search_cmd(self, query: str, max_results: int, params: dict[str, Any], output_file: Path) -> list[str] | None:
        if self.search_script is None or not self.search_script.exists():
            return None
        engines = _coerce_engines(params.get("engines") or params.get("preset"))
        cmd = [
            sys.executable,
            str(self.search_script),
            "search",
            query,
            "--max",
            str(max_results),
            "--engines",
            ",".join(engines),
            "-o",
            str(output_file),
        ]
        if params.get("site"):
            cmd.extend(["--site", str(params["site"])])
        if params.get("site_pack"):
            cmd.extend(["--site-pack", str(params["site_pack"])])
        if params.get("timeout"):
            cmd.extend(["--timeout", str(params["timeout"])])
        if params.get("github_sort"):
            cmd.extend(["--github-sort", str(params["github_sort"])])
        if params.get("github_order"):
            cmd.extend(["--github-order", str(params["github_order"])])
        return cmd


ADAPTER = GenericSearchAdapter()
