#!/usr/bin/env python3
"""Bilibili search adapter. The legacy mixed CLI is used only through its search command."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shared.search_adapter import CLISearchAdapter, SCRIPTS_DIR


class BilibiliSearchAdapter(CLISearchAdapter):
    """Bilibili search-only entrypoint."""

    platform_name = "bilibili"

    search_script = SCRIPTS_DIR / "bilibili" / "bilibili_dl.py"

    def _build_search_cmd(self, query: str, max_results: int, params: dict[str, Any], output_file: Path) -> list[str] | None:
        """bilibili 搜索用 --max-pages 参数（非约定的 --max）。"""
        if self.search_script is None:
            return None
        # bilibili 每页约 20 条，max-pages 估算为 ceil(max/20)
        max_pages = max(1, (max_results + 19) // 20)
        return [
            sys.executable, str(self.search_script),
            "search", query,
            "--max-pages", str(max_pages),
            "-o", str(output_file),
        ]


ADAPTER = BilibiliSearchAdapter()
