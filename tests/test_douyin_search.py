#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "resource-platforms/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "douyin"))
PATH = SCRIPTS / "douyin/douyin_search.py"
SPEC = importlib.util.spec_from_file_location("douyin_search", PATH)
douyin_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(douyin_search)


class TestDouyinSearch(unittest.TestCase):
    def test_normalize_video(self) -> None:
        video = {
            "video_id": "123", "title": "数学技巧", "url": "https://www.douyin.com/video/123",
            "author": "老师", "duration": 30, "stats": {"play": 100, "like": 5},
        }
        result = douyin_search.normalize_video(video)
        self.assertEqual(result["source_platform"], "douyin")
        self.assertEqual(result["platform_signals"], {"views": 100, "likes": 5})


if __name__ == "__main__":
    unittest.main(verbosity=2)
