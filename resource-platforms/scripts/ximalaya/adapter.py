#!/usr/bin/env python3
"""喜马拉雅平台适配器 — 实现 PlatformSkill 接口。

搜索脚本：ximalaya_search.py（自动发现，CLI 约定 search --max -o）
下载脚本：已迁移至 resource-downloader
"""

from __future__ import annotations

from shared.platform_base import CLIBasedPlatformSkill


class XimalayaSkill(CLIBasedPlatformSkill):
    """喜马拉雅平台 Skill。

    基类自动发现 ximalaya_search.py（命名约定 *_search.py）。
    搜索接口公开，无需认证。
    """

    platform_name = "ximalaya"
