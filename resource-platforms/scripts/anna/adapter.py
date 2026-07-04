#!/usr/bin/env python3
"""Anna's Archive search-only adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shared.search_adapter import CLISearchAdapter, SCRIPTS_DIR


class AnnaSearchAdapter(CLISearchAdapter):
    """Search Anna's Archive book and article metadata."""

    platform_name = "anna"
    search_script = SCRIPTS_DIR / "anna" / "anna_search.py"
    timeout_seconds = 75

    def _build_search_cmd(self, query: str, max_results: int, params: dict[str, Any], output_file: Path) -> list[str] | None:
        if self.search_script is None or not self.search_script.is_file():
            return None
        content = str(params.get("content") or params.get("type") or "book")
        cmd = [
            sys.executable,
            str(self.search_script),
            "search",
            query,
            "--max",
            str(max_results),
            "--content",
            content,
            "-o",
            str(output_file),
        ]
        if params.get("base_url"):
            cmd.extend(["--base-url", str(params["base_url"])])
        if self._truthy(params.get("auto_base_url") or params.get("auto_mirror")):
            cmd.append("--auto-base-url")
        if params.get("timeout"):
            cmd.extend(["--timeout", str(params["timeout"])])
        if params.get("fallback"):
            cmd.extend(["--fallback", str(params["fallback"])])
        if params.get("fallback_engines"):
            cmd.extend(["--fallback-engines", str(params["fallback_engines"])])
        return cmd

    @staticmethod
    def _compact_raw_metadata(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {}
        allowed = {
            "base_url", "content", "doi", "fallback", "format", "hash", "isbn",
            "meta", "query", "size", "source_engine", "source_rank",
        }
        return {
            key: value
            for key, value in raw.items()
            if key in allowed and isinstance(value, (str, int, float, bool))
        }

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)


ADAPTER = AnnaSearchAdapter()
