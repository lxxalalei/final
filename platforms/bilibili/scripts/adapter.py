#!/usr/bin/env python3
"""Bilibili 平台适配器 — 实现 PlatformSkill 接口。

搜索：调用 bilibili_dl.py 的 search 子命令
下载：调用 bilibili_dl.py 的 download 子命令（提取 BV 号）

注意：bilibili 的搜索和下载在同一个脚本 bilibili_dl.py 中（有 search/download
子命令），不是分开的 *_search.py + *_dl.py，因此显式指定搜索脚本。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shared.platform_base import CLIBasedPlatformSkill, _platforms_base_dir


class BilibiliSkill(CLIBasedPlatformSkill):
    """B站平台 Skill。"""

    platform_name = "bilibili"

    def __init__(self) -> None:
        super().__init__()
        # bilibili 的搜索在 bilibili_dl.py 中（非 *_search.py 约定），显式指定
        base = _platforms_base_dir()
        self._search_script = base / "bilibili" / "scripts" / "bilibili_dl.py"

    def _build_search_cmd(self, intent: dict[str, Any], output_file: Path) -> list[str] | None:
        """bilibili 搜索用 --max-pages 参数（非约定的 --max）。"""
        if self._search_script is None:
            return None
        keywords = intent.get("keywords") or ""
        if not keywords:
            return None
        max_results = intent.get("max_results") or 20
        # bilibili 每页约 20 条，max-pages 估算为 ceil(max/20)
        max_pages = max(1, (max_results + 19) // 20)
        import sys as _sys
        return [
            _sys.executable, str(self._search_script),
            "search", keywords,
            "--max-pages", str(max_pages),
            "-o", str(output_file),
        ]

    def _transform_download_url(self, url: str) -> str:
        """bilibili 下载脚本需要 BV 号标识，从 URL 中提取。"""
        match = re.search(r"BV[\w]+", url)
        if not match:
            raise ValueError(f"无法从 bilibili URL 提取 BV 号: {url}")
        return match.group(0)
