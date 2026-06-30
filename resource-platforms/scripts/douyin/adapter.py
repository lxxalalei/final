#!/usr/bin/env python3
"""Douyin search adapter. The legacy mixed CLI is invoked only with search."""

from __future__ import annotations

from shared.search_adapter import CLISearchAdapter, SCRIPTS_DIR


class DouyinSearchAdapter(CLISearchAdapter):
    """抖音平台 Skill。"""

    platform_name = "douyin"

    search_script = SCRIPTS_DIR / "douyin" / "douyin_dl.py"


ADAPTER = DouyinSearchAdapter()
