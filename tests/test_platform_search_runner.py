#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "resource-platforms" / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("search_runner", SCRIPTS / "run_search_plan.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


class FakeAdapter:
    def __init__(self, platform: str, delay: float = 0.05, fail: bool = False):
        self.platform = platform
        self.delay = delay
        self.fail = fail

    def search(self, query: str, max_results: int, params: dict):
        time.sleep(self.delay)
        if self.fail:
            return {"results": [], "error": {"error_code": "NETWORK_TIMEOUT", "message": "timeout", "retryable": True}}
        return {"results": [{
            "resource_id": f"{self.platform}:{query}",
            "platform": self.platform,
            "title": query,
            "source_url": f"https://example.com/{self.platform}/{query}",
        }], "error": None}


class TestPlatformSearchRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.original_loader = runner.load_adapter

    def tearDown(self) -> None:
        runner.load_adapter = self.original_loader

    @staticmethod
    def plan(tasks: list[dict]) -> dict:
        return {"_meta": {"session_id": "s1"}, "data": {"search_tasks": tasks}}

    def test_platforms_run_in_parallel(self) -> None:
        adapters = {"a.py": FakeAdapter("a", 0.12), "b.py": FakeAdapter("b", 0.12)}
        runner.load_adapter = lambda entry: adapters[entry]
        registry = {"platforms": {
            "a": {"status": "available", "entry": "a.py", "timeout_seconds": 1},
            "b": {"status": "available", "entry": "b.py", "timeout_seconds": 1},
        }}
        tasks = [
            {"platform": "a", "searches": [{"query": "one", "max_results": 1}]},
            {"platform": "b", "searches": [{"query": "two", "max_results": 1}]},
        ]
        started = time.monotonic()
        result = asyncio.run(runner.run(self.plan(tasks), registry))
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.22)
        self.assertEqual(result["_summary"]["resource_count"], 2)

    def test_failure_is_isolated(self) -> None:
        adapters = {"ok.py": FakeAdapter("ok"), "bad.py": FakeAdapter("bad", fail=True)}
        runner.load_adapter = lambda entry: adapters[entry]
        registry = {"platforms": {
            "ok": {"status": "available", "entry": "ok.py", "timeout_seconds": 1},
            "bad": {"status": "available", "entry": "bad.py", "timeout_seconds": 1},
        }}
        tasks = [
            {"platform": "ok", "searches": [{"query": "course", "max_results": 1}]},
            {"platform": "bad", "searches": [{"query": "course", "max_results": 1}]},
        ]
        result = asyncio.run(runner.run(self.plan(tasks), registry))
        self.assertEqual(result["_summary"]["resource_count"], 1)
        self.assertEqual(result["_summary"]["failed_platforms"], ["bad"])
        self.assertEqual(result["data"]["errors"][0]["platform"], "bad")

    def test_registry_adapters_are_loadable(self) -> None:
        registry = json.loads((ROOT / "resource-platforms/config/search-registry.json").read_text(encoding="utf-8"))
        for platform, config in registry["platforms"].items():
            if config["status"] == "available":
                adapter = self.original_loader(config["entry"])
                self.assertEqual(adapter.platform_name, platform)

    def test_runtime_dependency_failure_is_structured(self) -> None:
        error = runner.check_runtime({"runtime": {"python_all": ["module_that_does_not_exist_lrs"]}})
        self.assertEqual(error["error_code"], "SYSTEM_DEPENDENCY_MISSING")

    def test_runtime_auth_failure_is_structured(self) -> None:
        name = "LRS_TEST_AUTH_THAT_IS_NOT_SET"
        old = os.environ.pop(name, None)
        try:
            error = runner.check_runtime({"runtime": {"auth_any_env": [name]}})
        finally:
            if old is not None:
                os.environ[name] = old
        self.assertEqual(error["error_code"], "AUTH_REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
