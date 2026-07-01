#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "resource-platforms/scripts/bilibili/bilibili_search.py"
sys.path.insert(0, str(PATH.parent))
SPEC = importlib.util.spec_from_file_location("bilibili_search", PATH)
bilibili_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(bilibili_search)


class TestBilibiliSearch(unittest.TestCase):
    def test_normalize_video_result(self) -> None:
        item = {
            "bvid": "BV1test", "title": "四年级<em>数学</em>课程",
            "description": "同步讲解", "author": "老师", "duration": "20:00",
            "play": 1000, "video_review": 20, "favorites": 30,
        }
        result = bilibili_search.normalize_item(item)
        self.assertEqual(result["title"], "四年级数学课程")
        self.assertEqual(result["source_url"], "https://www.bilibili.com/video/BV1test")
        self.assertEqual(result["platform_signals"]["views"], 1000)

    def test_count_value_preserves_human_readable_count(self) -> None:
        self.assertEqual(bilibili_search.count_value("1.2万"), "1.2万")


if __name__ == "__main__":
    unittest.main(verbosity=2)
