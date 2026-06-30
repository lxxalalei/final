#!/usr/bin/env python3
"""SmartEdu（国家中小学智慧教育平台）平台适配器 — 纯搜索。

搜索：调用 smartedu_resources.py search-resources 子命令
（脚本命名和子命令名与统一约定有历史差异，需覆盖默认发现逻辑）
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from shared.platform_base import CLIBasedPlatformSkill, _platforms_base_dir


class SmartEduSkill(CLIBasedPlatformSkill):
    """SmartEdu 平台搜索 Skill。"""

    platform_name = "smartedu"

    def __init__(self) -> None:
        super().__init__()
        # SmartEdu 脚本命名不符合 *_search.py 约定，显式指定
        base = _platforms_base_dir()
        self._search_script = base / "smartedu" / "smartedu_resources.py"

    def _build_search_cmd(self, intent: dict[str, Any], output_file: Path) -> list[str] | None:
        """SmartEdu 用 search-resources 子命令（非约定的 search）。"""
        if self._search_script is None or not self._search_script.exists():
            return None
        keywords = intent.get("keywords") or ""
        if not keywords:
            return None
        max_results = intent.get("max_results") or 20
        return [
            sys.executable, str(self._search_script),
            "search-resources",
            "--query", keywords,
            "--max", str(max_results),
            "-o", str(output_file),
        ]
