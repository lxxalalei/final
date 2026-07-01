#!/usr/bin/env python3
"""Focused tests for model-driven Intent and executable Search output."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from tests.e2e_pipeline_test import run_pipeline


ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


intent_validator = load_module("intent_validator", "resource-intent/scripts/validate_output.py")
search_validator = load_module("search_validator", "resource-search/scripts/validate_output.py")


class TestSemanticContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.intent, cls.search = run_pipeline()[:2]
        cls.catalog = json.loads((ROOT / "resource-search/config/platform-catalog.json").read_text(encoding="utf-8"))
        cls.platform_registry = json.loads((ROOT / "resource-platforms/config/search-registry.json").read_text(encoding="utf-8"))

    def test_json_schemas_parse(self) -> None:
        for relative in (
            "resource-intent/schemas/input.schema.json",
            "resource-intent/schemas/output.schema.json",
            "resource-search/schemas/input.schema.json",
            "resource-search/schemas/output.schema.json",
        ):
            self.assertIn("$schema", json.loads((ROOT / relative).read_text(encoding="utf-8")))

    def test_valid_intent_passes_manual_validator(self) -> None:
        self.assertEqual(intent_validator.validate(self.intent), [])

    def test_intent_evidence_requires_quote(self) -> None:
        broken = copy.deepcopy(self.intent)
        broken["data"]["evidence"][0]["quote"] = ""
        errors = intent_validator.validate(broken)
        self.assertTrue(any("quote" in error for error in errors))

    def test_ready_intent_requires_evidence(self) -> None:
        broken = copy.deepcopy(self.intent)
        broken["data"]["evidence"] = []
        errors = intent_validator.validate(broken)
        self.assertTrue(any("至少提供一条 evidence" in error for error in errors))

    def test_intent_rejects_executable_queries(self) -> None:
        broken = copy.deepcopy(self.intent)
        broken["data"]["queries"] = ["不应存在"]
        self.assertTrue(any("不得输出旧槽位或搜索执行字段" in error for error in intent_validator.validate(broken)))

    def test_intent_accepts_evidence_backed_requirement(self) -> None:
        intent = copy.deepcopy(self.intent)
        intent["data"]["requirements"] = [{
            "text": "资源必须免费",
            "strength": "must",
            "evidence": "只要免费的",
        }]
        self.assertEqual(intent_validator.validate(intent), [])

    def test_intent_carries_only_one_clarification_question(self) -> None:
        needs = copy.deepcopy(self.intent)
        question = "你想让孩子入门 Scratch、Python，还是机器人编程？"
        needs["_summary"] = {"status": "needs_clarification", "question": question}
        needs["data"]["status"] = "needs_clarification"
        needs["data"]["clarification"] = {
            "question": question,
            "reason": "两种方向会改变搜索形态",
        }
        self.assertEqual(intent_validator.validate(needs), [])

    def test_valid_search_plan_passes_manual_validator(self) -> None:
        self.assertEqual(search_validator.validate(self.search, self.catalog, self.intent), [])

    def test_search_plan_contains_only_execution_orchestration_fields(self) -> None:
        self.assertEqual(
            set(self.search["data"]),
            {"search_tasks"},
        )
        for task in self.search["data"]["search_tasks"]:
            self.assertEqual(set(task), {"platform", "priority", "searches"})
            for search in task["searches"]:
                self.assertTrue({"query", "max_results"}.issubset(search))
                self.assertTrue(set(search).issubset({"query", "max_results", "params"}))

    def test_search_rejects_planned_platform(self) -> None:
        broken = copy.deepcopy(self.search)
        broken["data"]["search_tasks"][0]["platform"] = "baiduwenku"
        self.assertTrue(any("不可执行" in error for error in search_validator.validate(broken, self.catalog, self.intent)))

    def test_search_requires_generic_task(self) -> None:
        broken = copy.deepcopy(self.search)
        broken["data"]["search_tasks"] = [
            task for task in broken["data"]["search_tasks"] if task["platform"] != "generic"
        ]
        self.assertTrue(any("恰好包含一个 generic" in error for error in search_validator.validate(broken, self.catalog, self.intent)))

    def test_generic_requires_baidu_and_bing(self) -> None:
        broken = copy.deepcopy(self.search)
        generic = next(task for task in broken["data"]["search_tasks"] if task["platform"] == "generic")
        generic["searches"][0]["params"]["engines"] = ["bing"]
        errors = search_validator.validate(broken, self.catalog, self.intent)
        self.assertTrue(any("必须包含" in error and "baidu" in error for error in errors))

    def test_search_rejects_parameter_not_supported_by_platform(self) -> None:
        broken = copy.deepcopy(self.search)
        broken["data"]["search_tasks"][0]["searches"][0]["params"] = {"free_only": True}
        errors = search_validator.validate(broken, self.catalog, self.intent)
        self.assertTrue(any("不支持的参数" in error for error in errors))

    def test_ximalaya_accepts_real_search_parameters(self) -> None:
        plan = copy.deepcopy(self.search)
        task = plan["data"]["search_tasks"][1]
        task["platform"] = "ximalaya"
        for search in task["searches"]:
            search["params"] = {"core": "album", "free_only": True, "sort": "relevance"}
        self.assertEqual(search_validator.validate(plan, self.catalog, self.intent), [])

    def test_search_rejects_duplicate_platform_task(self) -> None:
        broken = copy.deepcopy(self.search)
        broken["data"]["search_tasks"][2]["platform"] = "smartedu"
        errors = search_validator.validate(broken, self.catalog, self.intent)
        self.assertTrue(any("平台任务重复" in error for error in errors))

    def test_generic_must_be_first_and_p0(self) -> None:
        broken = copy.deepcopy(self.search)
        broken["data"]["search_tasks"][0], broken["data"]["search_tasks"][1] = (
            broken["data"]["search_tasks"][1], broken["data"]["search_tasks"][0]
        )
        errors = search_validator.validate(broken, self.catalog, self.intent)
        self.assertTrue(any("generic 必须" in error for error in errors))

    def test_search_rejects_duplicate_query_in_same_task(self) -> None:
        broken = copy.deepcopy(self.search)
        task = broken["data"]["search_tasks"][0]
        task["searches"][1]["query"] = task["searches"][0]["query"]
        errors = search_validator.validate(broken, self.catalog, self.intent)
        self.assertTrue(any("搜索词重复" in error for error in errors))

    def test_search_rejects_non_ready_intent(self) -> None:
        intent = copy.deepcopy(self.intent)
        intent["data"]["status"] = "needs_clarification"
        self.assertTrue(any("非 ready" in error for error in search_validator.validate(self.search, self.catalog, intent)))

    def test_platform_registry_available_entries_have_scripts(self) -> None:
        for platform, entry in self.platform_registry["platforms"].items():
            if entry["status"] == "available":
                self.assertTrue((ROOT / "resource-platforms" / entry["entry"]).is_file(), platform)

    def test_search_catalog_contains_only_execution_facts(self) -> None:
        for platform, entry in self.catalog["platforms"].items():
            self.assertNotIn("entry", entry, platform)
            self.assertEqual(set(entry), {"planning_status", "auth", "search_parameters"}, platform)

    def test_search_catalog_and_platform_registry_are_author_synced(self) -> None:
        catalog_platforms = self.catalog["platforms"]
        registry_platforms = self.platform_registry["platforms"]
        self.assertEqual(set(catalog_platforms), set(registry_platforms))
        for platform in catalog_platforms:
            self.assertEqual(catalog_platforms[platform]["planning_status"], registry_platforms[platform]["status"])

    def test_golden_case_sets_are_well_formed(self) -> None:
        intent_cases = json.loads((ROOT / "resource-intent/examples/golden-cases.json").read_text(encoding="utf-8"))
        routing_cases = json.loads((ROOT / "resource-search/examples/routing-cases.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(intent_cases["cases"]), 23)
        self.assertGreaterEqual(len(routing_cases["cases"]), 18)
        for suite in (intent_cases, routing_cases):
            ids = [case["id"] for case in suite["cases"]]
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
