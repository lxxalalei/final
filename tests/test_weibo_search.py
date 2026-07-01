#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "resource-platforms/scripts/weibo/weibo_search.py"
SPEC = importlib.util.spec_from_file_location("weibo_search", PATH)
weibo_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(weibo_search)


class TestWeiboSearch(unittest.TestCase):
    def test_normalize_post(self) -> None:
        post = {
            "id": "123", "bid": "Abc", "text_raw": "四年级数学课程资料",
            "user": {"id": "9", "screen_name": "机构"},
            "attitudes_count": 10, "comments_count": 2, "reposts_count": 3,
        }
        result = weibo_search.normalize_post(post)
        self.assertEqual(result["source_url"], "https://weibo.com/9/Abc")
        self.assertEqual(result["platform_signals"]["likes"], 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
