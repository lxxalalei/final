#!/usr/bin/env python3
"""Offline tests for the generic Baidu/Bing search adapter."""

from __future__ import annotations

import importlib.util
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "resource-platforms/scripts/generic/generic_search.py"
SPEC = importlib.util.spec_from_file_location("generic_search", MODULE_PATH)
generic_search = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generic_search)


class TestGenericSearch(unittest.TestCase):
    def test_parse_bing_result(self) -> None:
        page = """
        <ol><li class="b_algo"><h2><a href="https://school.example.org/math.pdf">
        四年级数学课程</a></h2><div><p>同步课程与知识点讲解。</p></div></li></ol>
        """
        results = generic_search.parse_bing_results(page, "四年级数学课程", 5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["platform"], "generic")
        self.assertEqual(results[0]["source_url"], "https://school.example.org/math.pdf")
        self.assertEqual(results[0]["platform_signals"]["engine"], "bing")

    def test_parse_baidu_prefers_direct_url(self) -> None:
        page = """
        <div class="result c-container" mu="https://edu.example.cn/paper">
          <h3><a href="https://www.baidu.com/link?url=redirect">小学数学试卷</a></h3>
          <div class="c-abstract">免费下载练习。</div>
        </div></div>
        """
        results = generic_search.parse_baidu_results(page, "小学数学试卷", 5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_url"], "https://edu.example.cn/paper")
        self.assertEqual(results[0]["platform_signals"]["engine"], "baidu")

    def test_search_merges_and_deduplicates_urls(self) -> None:
        original_fetch = generic_search._fetch
        try:
            generic_search._fetch = lambda url, timeout: (
                '<li class="b_algo"><h2><a href="https://same.example/a">A</a></h2><p>Bing</p></li>'
                if "bing.com" in url
                else '<div class="result" mu="https://same.example/a"><h3><a href="https://www.baidu.com/link">A</a></h3></div></div>'
            )
            result = generic_search.search("测试", ["baidu", "bing"], 10, 1)
        finally:
            generic_search._fetch = original_fetch
        self.assertEqual(result["search_method"], "baidu+bing")
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["results"][0]["source_url"], "https://same.example/a")

    def test_baidu_and_bing_run_in_parallel(self) -> None:
        original_fetch = generic_search._fetch
        try:
            def fake_fetch(url: str, timeout: float) -> str:
                time.sleep(0.12)
                if "bing.com" in url:
                    return '<li class="b_algo"><h2><a href="https://bing.example/a">B</a></h2></li>'
                return '<div class="result" mu="https://baidu.example/a"><h3><a href="#">A</a></h3></div></div>'

            generic_search._fetch = fake_fetch
            started = time.monotonic()
            result = generic_search.search("四年级数学课程", ["baidu", "bing"], 10, 1)
            elapsed = time.monotonic() - started
        finally:
            generic_search._fetch = original_fetch
        self.assertLess(elapsed, 0.22)
        self.assertEqual(result["returned_count"], 2)

    def test_engine_failure_does_not_discard_other_engine(self) -> None:
        original_fetch = generic_search._fetch
        try:
            def fake_fetch(url: str, timeout: float) -> str:
                if "baidu.com" in url:
                    raise TimeoutError("blocked")
                return '<li class="b_algo"><h2><a href="https://ok.example/r">R</a></h2></li>'

            generic_search._fetch = fake_fetch
            result = generic_search.search("测试", ["baidu", "bing"], 10, 1)
        finally:
            generic_search._fetch = original_fetch
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["errors"][0]["engine"], "baidu")

    def test_verification_page_is_reported_as_error(self) -> None:
        original_fetch = generic_search._fetch
        try:
            generic_search._fetch = lambda url, timeout: (
                '<html><title>百度安全验证</title></html>'
                if "baidu.com" in url
                else '<html><div class="captcha">Verify you are human</div></html>'
            )
            result = generic_search.search("测试", ["baidu", "bing"], 10, 1)
        finally:
            generic_search._fetch = original_fetch
        self.assertEqual(result["returned_count"], 0)
        self.assertEqual({item["engine"] for item in result["errors"]}, {"baidu", "bing"})
        self.assertTrue(all("SearchBlockedError" in item["message"] for item in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
