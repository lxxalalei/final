#!/usr/bin/env python3
"""Weibo search adapter. The legacy mixed CLI is invoked only with search."""

from __future__ import annotations

from shared.search_adapter import CLISearchAdapter, SCRIPTS_DIR


class WeiboSearchAdapter(CLISearchAdapter):
    """微博平台 Skill。"""

    platform_name = "weibo"

    search_script = SCRIPTS_DIR / "weibo" / "weibo_dl.py"


ADAPTER = WeiboSearchAdapter()
