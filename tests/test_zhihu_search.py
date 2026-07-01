#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "resource-platforms/scripts/zhihu/zhihu_search.py"
sys.path.insert(0, str(ROOT / "resource-platforms/scripts"))
SPEC = importlib.util.spec_from_file_location("zhihu_search", PATH)
zhihu_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(zhihu_search)


class TestZhihuSearch(unittest.TestCase):
    def test_cookie_is_not_misused_as_bearer_token(self) -> None:
        headers = zhihu_search._get_auth_headers("z_c0=secret", None)
        self.assertEqual(headers["Cookie"], "z_c0=secret")
        self.assertNotIn("Authorization", headers)

    def test_explicit_token_uses_bearer_header(self) -> None:
        headers = zhihu_search._get_auth_headers(None, "token-value")
        self.assertEqual(headers["Authorization"], "Bearer token-value")

    def test_parse_answer_result(self) -> None:
        item = {
            "type": "answer", "id": "123", "title": "四年级<em>数学</em>",
            "question": {"id": "456"}, "author": {"name": "老师"},
        }
        result = zhihu_search._parse_search_item(item, item)
        self.assertEqual(result["title"], "四年级数学")
        self.assertIn("question/456/answer/123", result["source_url"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
