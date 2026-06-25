#!/usr/bin/env python3
"""Zhihu（知乎）平台适配器 — 实现 PlatformSkill 接口。

搜索：调用 zhihu_search.py search 子命令
下载：调用 zhihu_dl.py download 子命令
"""

from __future__ import annotations

from shared.platform_base import CLIBasedPlatformSkill


class ZhihuSkill(CLIBasedPlatformSkill):
    """知乎平台 Skill。"""

    platform_name = "zhihu"
