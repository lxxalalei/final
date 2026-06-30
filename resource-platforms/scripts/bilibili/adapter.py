#!/usr/bin/env python3
"""Bilibili 平台适配器 — 实现 PlatformSkill 接口。

搜索脚本：bilibili_search.py（自动发现，CLI 约定 search --max -o）
下载脚本：已迁移至 resource-downloader/scripts/bilibili/
"""

from __future__ import annotations

from shared.platform_base import CLIBasedPlatformSkill


class BilibiliSkill(CLIBasedPlatformSkill):
    """B站平台 Skill。

    基类自动发现 bilibili_search.py（命名约定 *_search.py）。
    CLI 参数完全匹配基类默认约定：
      bilibili_search.py search {keyword} --max {N} -o {output_file}
    因此无需覆盖任何方法。
    """

    platform_name = "bilibili"
