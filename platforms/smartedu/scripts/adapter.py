#!/usr/bin/env python3
"""SmartEdu（国家中小学智慧教育平台）平台适配器 — 实现 PlatformSkill 接口。

搜索：调用 smartedu_resources.py search-resources 子命令
下载：调用 smartedu_download.py download 子命令

注意：SmartEdu 的搜索脚本命名和命令与统一约定有历史差异
（search-resources 而非 search，smartedu_resources.py 而非 *_search.py），
因此本适配器覆盖默认的脚本发现和命令构建逻辑。

架构详情、CDN 认证机制、错误处理策略见 ``../references/architecture.md``。
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from shared.platform_base import CLIBasedPlatformSkill, _platforms_base_dir


class SmartEduSkill(CLIBasedPlatformSkill):
    """SmartEdu 平台 Skill。"""

    platform_name = "smartedu"

    def __init__(self) -> None:
        super().__init__()
        # SmartEdu 脚本命名与统一约定有历史差异，显式指定
        base = _platforms_base_dir()
        self._search_script = base / "smartedu" / "scripts" / "smartedu_resources.py"
        self._download_script = base / "smartedu" / "scripts" / "smartedu_download.py"

    def _build_search_cmd(self, intent: dict[str, Any], output_file: Path) -> list[str] | None:
        """SmartEdu 用 search-resources 子命令（非约定的 search）。"""
        if self._search_script is None or not self._search_script.exists():
            return None
        keywords = intent.get("keywords") or ""
        if not keywords:
            return None
        max_results = intent.get("max_results") or 20
        cmd: list[str] = [
            sys.executable, str(self._search_script),
            "search-resources",
            "--query", keywords,
            "--max", str(max_results),
            "-o", str(output_file),
        ]
        return cmd
