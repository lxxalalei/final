#!/usr/bin/env python3
"""Weibo（微博）平台适配器 — 实现 PlatformSkill 接口。

搜索：调用 weibo_dl.py search 子命令（T7 实现）
下载：调用 weibo_dl.py download 子命令
"""

from __future__ import annotations

from shared.platform_base import CLIBasedPlatformSkill, _platforms_base_dir


class WeiboSkill(CLIBasedPlatformSkill):
    """微博平台 Skill。"""

    platform_name = "weibo"

    def __init__(self) -> None:
        super().__init__()
        # weibo 的搜索在 weibo_dl.py 中（非 *_search.py 约定），显式指定
        base = _platforms_base_dir()
        self._search_script = base / "weibo" / "weibo_dl.py"
