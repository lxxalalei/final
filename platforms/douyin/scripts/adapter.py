#!/usr/bin/env python3
"""Douyin（抖音）平台适配器 — 实现 PlatformSkill 接口。

搜索：调用 douyin_dl.py search 子命令（T6 实现）
下载：调用 douyin_dl.py download 子命令
"""

from __future__ import annotations

from shared.platform_base import CLIBasedPlatformSkill, _platforms_base_dir


class DouyinSkill(CLIBasedPlatformSkill):
    """抖音平台 Skill。"""

    platform_name = "douyin"

    def __init__(self) -> None:
        super().__init__()
        # douyin 的搜索在 douyin_dl.py 中（非 *_search.py 约定），显式指定
        base = _platforms_base_dir()
        self._search_script = base / "douyin" / "scripts" / "douyin_dl.py"
