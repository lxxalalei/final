#!/usr/bin/env python3
"""Offline six-stage contract simulation using intent-spec/v1 and search-plan/v1."""

from __future__ import annotations

import copy
import unittest


def envelope(stage: int, skill: str, input_from: str, schema_version: str, summary: dict, data: dict) -> dict:
    return {
        "_meta": {
            "stage": stage,
            "session_id": "20260630-1030-math-grade3",
            "skill": skill,
            "created_at": "2026-06-30T10:30:00+08:00",
            "input_from": input_from,
            "schema_version": schema_version,
        },
        "_summary": summary,
        "data": data,
    }


def string_slot(value, status="explicit", confidence=1.0, evidence=None):
    return {"value": value, "status": status, "confidence": confidence, "evidence": evidence or []}


def array_slot(value, status="explicit", confidence=1.0, evidence=None):
    return {"value": value, "status": status, "confidence": confidence, "evidence": evidence or []}


def run_pipeline() -> list[dict]:
    constraints = {"must": ["免费"], "prefer": ["可打印"], "exclude": []}
    slots = {
        "core_topic": string_slot("小学三年级数学练习题", evidence=["三年级数学练习题"]),
        "learning_domain": string_slot("数学", "inferred", 0.95, ["数学练习题"]),
        "target_age": string_slot("8-9岁", "inferred", 0.85, ["小学三年级"]),
        "grade_level": string_slot("小学三年级", evidence=["三年级"]),
        "learning_goal": string_slot("练习", "inferred", 0.9, ["练习题"]),
        "difficulty": string_slot("同步", "inferred", 0.8, ["三年级练习题"]),
        "resource_types": array_slot(["练习类"], "inferred", 0.9, ["数学练习题"]),
        "format_preferences": array_slot(["练习题"], "explicit", 1.0, ["数学练习题"]),
        "file_formats": array_slot([], "unknown", 0.0),
        "source_preferences": array_slot(["官方"], "defaulted", 0.5),
        "use_scenario": string_slot("课后练习", "inferred", 0.75, ["练习题"]),
        "version": string_slot(None, "unknown", 0.0),
        "language": string_slot("中文", "defaulted", 0.5),
        "search_mode": string_slot("standard", "defaulted", 0.5),
    }
    stage1 = envelope(
        1,
        "resource-intent",
        "request.json",
        "intent-spec/v1",
        {
            "status": "ready",
            "core_topic": "小学三年级数学练习题",
            "target_age": "8-9岁",
            "clarification_required": False,
            "clarification_question": None,
            "assumptions": ["默认优先官方中文资源", "使用标准搜索模式"],
        },
        {
            "schema_version": "intent-spec/v1",
            "status": "ready",
            "raw_request": "给三年级孩子找免费的数学练习题，最好可打印",
            "slots": slots,
            "constraints": constraints,
            "search_concepts": {
                "canonical_terms": ["小学三年级", "数学", "练习题"],
                "synonyms": ["同步练习", "课后练习"],
                "related_terms": ["带答案", "可打印"],
            },
            "ambiguities": [],
            "clarification": {"required": False, "question": None, "reason": None, "missing_information": []},
            "assumptions": ["默认优先官方中文资源", "使用标准搜索模式"],
        },
    )

    intent_context = {
        "core_topic": "小学三年级数学练习题",
        "target_age": "8-9岁",
        "grade_level": "小学三年级",
        "learning_goal": "练习",
        "resource_types": ["练习类"],
        "format_preferences": ["练习题"],
        "file_formats": [],
        "search_mode": "standard",
        "constraints": constraints,
    }
    tasks = [
        {
            "task_id": "task-smartedu-primary",
            "platform": "smartedu",
            "priority": "P0",
            "reason": "官方平台适合小学同步练习",
            "searches": [
                {
                    "query": "小学三年级 数学 同步练习",
                    "max_results": 15,
                    "params": {},
                },
                {
                    "query": "三年级数学 课后练习题",
                    "max_results": 15,
                    "params": {},
                },
            ],
        },
        {
            "task_id": "task-bilibili-explainer",
            "platform": "bilibili",
            "priority": "P1",
            "reason": "补充可视化讲解",
            "searches": [
                {
                    "query": "三年级数学 应用题 解题讲解",
                    "max_results": 15,
                    "params": {},
                },
                {
                    "query": "小学三年级数学 易错题讲解",
                    "max_results": 15,
                    "params": {},
                },
            ],
        },
        {
            "task_id": "task-generic-web",
            "platform": "generic",
            "priority": "P1",
            "reason": "固定全网补充，发现未接入站点和可打印长尾资料",
            "searches": [
                {
                    "query": "小学三年级 数学 免费练习题",
                    "max_results": 15,
                    "params": {"engines": ["baidu", "bing"]},
                },
                {
                    "query": "三年级数学 可打印练习 带答案",
                    "max_results": 15,
                    "params": {"engines": ["baidu", "bing"]},
                },
                {
                    "query": "三年级数学 应用题 计算题 练习",
                    "max_results": 15,
                    "params": {"engines": ["baidu", "bing"]},
                },
            ],
        },
    ]
    stage2 = envelope(
        2,
        "resource-search",
        "stage1_intent.json",
        "search-plan/v1",
        {
            "platform_count": 3,
            "platforms": ["smartedu", "bilibili", "generic"],
            "query_count": 7,
            "expected_results": 105,
        },
        {
            "schema_version": "search-plan/v1",
            "intent_ref": "stage1_intent.json",
            "strategy": "官方同步练习为主，视频平台搜索解题过程，百度与 Bing 补充免费、可打印和长尾练习。",
            "search_tasks": tasks,
        },
    )

    raw_resources = [
        {"resource_id": "smartedu:math-001", "platform": "smartedu", "title": "三年级数学同步练习", "source_url": "https://example.cn/math-001", "type": "练习题", "is_free": True, "language": "中文", "download_feasibility": "高", "platform_signals": {"native_score": 95}},
        {"resource_id": "bilibili:video-001", "platform": "bilibili", "title": "三年级数学同步练习讲解", "source_url": "https://example.com/video-001", "type": "视频", "is_free": True, "language": "中文", "download_feasibility": "中", "platform_signals": {"views": 10000}},
        {"resource_id": "bilibili:paid-001", "platform": "bilibili", "title": "三年级数学 VIP 课程", "source_url": "https://example.com/paid-001", "type": "视频", "is_free": False, "language": "中文", "download_feasibility": "低", "platform_signals": {"views": 90000}},
        {"resource_id": "generic:web-001", "platform": "generic", "title": "三年级数学可打印练习题", "source_url": "https://example.org/math-printable", "type": "练习题", "is_free": True, "language": "中文", "download_feasibility": "低", "platform_signals": {"engine": "bing", "rank": 1}},
    ]
    stage3 = envelope(
        3,
        "resource-platforms",
        "stage2_search_plan.json",
        "platform-results/v1",
        {"raw_count": 4, "success_platforms": ["smartedu", "bilibili", "generic"], "failed_platforms": [], "error_count": 0},
        {"schema_version": "platform-results/v1", "intent_ref": "stage1_intent.json", "intent_context": intent_context, "resources": raw_resources, "platform_stats": {"smartedu": {"status": "success", "task_count": 1, "query_count": 2, "returned_count": 1, "invalid_count": 0}, "bilibili": {"status": "success", "task_count": 1, "query_count": 2, "returned_count": 2, "invalid_count": 0}, "generic": {"status": "success", "task_count": 1, "query_count": 3, "returned_count": 1, "invalid_count": 0}}, "errors": []},
    )

    qualified = []
    for resource in stage3["data"]["resources"]:
        if resource["is_free"] is False:
            continue
        assessed = copy.deepcopy(resource)
        assessed.update({"quality_score": 88 if resource["platform"] == "smartedu" else 78, "quality_level": "A", "quality_dimensions": {"content": 4, "age": 4, "teaching": 4, "source": 4, "experience": 4}, "assessment_notes": [], "possible_duplicate": False})
        qualified.append(assessed)
    selected = qualified[:1]
    stage4 = envelope(
        4,
        "resource-selector",
        "stage3_search_results.json",
        "selection/v1",
        {"raw_count": 4, "candidate_count": 3, "selected_count": 1, "selection_mode": "manual", "quality_dist": {"S": 0, "A": 3, "B": 0, "C": 0}, "filter_stats": {"duplicates_removed": 0, "business_filtered": 1}},
        {"schema_version": "selection/v1", "intent_ref": "stage1_intent.json", "selected_count": 1, "selection_mode": "manual", "resources": selected, "candidate_snapshot": {"raw_count": 4, "qualified_count": 3, "filter_stats": {"duplicates_removed": 0, "business_filtered": 1}, "platform_errors": []}},
    )

    downloaded = copy.deepcopy(selected)
    downloaded[0].update({"download_status": "success", "degraded_level": "Level 0", "file_path": "/tmp/downloads/math-001.pdf", "file_size": 1024, "file_format": "pdf", "fetch_time": "2026-06-30T10:35:00+08:00", "fetch_method": "smartedu", "degraded_content": None, "error": None})
    stage5 = envelope(5, "resource-downloader", "stage4_selection.json", "download/v1", {"total_count": 1, "success_count": 1, "degraded_count": 0, "failed_count": 0}, {"schema_version": "download/v1", "total_count": 1, "success_count": 1, "degraded_count": 0, "failed_count": 0, "resources": downloaded})

    archived = copy.deepcopy(downloaded)
    archived[0].update({"archive_status": "archived", "library_path": "学习资料库/数学/小学三年级/math-001.pdf", "archive_time": "2026-06-30T10:36:00+08:00", "dedup_status": "new", "archive_error": None})
    stage6 = envelope(6, "library-manager", "stage5_download.json", "archive/v1", {"total_count": 1, "archived_count": 1, "skipped_count": 0, "failed_count": 0, "dedup_stats": {"new": 1, "duplicate": 0, "skipped": 0}}, {"schema_version": "archive/v1", "total_count": 1, "archived_count": 1, "skipped_count": 0, "failed_count": 0, "resources": archived})
    return [stage1, stage2, stage3, stage4, stage5, stage6]


class TestSixStagePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stages = run_pipeline()

    def test_stage_order(self) -> None:
        self.assertEqual([item["_meta"]["stage"] for item in self.stages], list(range(1, 7)))

    def test_intent_contains_no_executable_queries(self) -> None:
        data = self.stages[0]["data"]
        self.assertNotIn("queries", data)
        self.assertNotIn("search_tasks", data)
        self.assertEqual(data["slots"]["core_topic"]["status"], "explicit")
        self.assertEqual(data["slots"]["resource_types"]["value"], ["练习类"])
        self.assertEqual(data["slots"]["format_preferences"]["value"], ["练习题"])
        self.assertEqual(data["slots"]["file_formats"]["status"], "unknown")
        self.assertNotIn("资源形态默认", " ".join(data["assumptions"]))

    def test_search_outputs_directly_executable_calls(self) -> None:
        for task in self.stages[1]["data"]["search_tasks"]:
            self.assertTrue(task["searches"])
            for search in task["searches"]:
                self.assertTrue(search["query"])
                self.assertGreater(search["max_results"], 0)
                self.assertIsInstance(search["params"], dict)
        self.assertNotIn("coverage_plan", self.stages[1]["data"])
        self.assertNotIn("intent_context", self.stages[1]["data"])

    def test_platform_output_has_no_final_quality(self) -> None:
        for resource in self.stages[2]["data"]["resources"]:
            self.assertNotIn("quality_score", resource)
            self.assertNotIn("quality_level", resource)
            self.assertIn("platform_signals", resource)

    def test_selector_adds_final_quality_and_filters(self) -> None:
        summary = self.stages[3]["_summary"]
        self.assertEqual(summary["raw_count"], 4)
        self.assertEqual(summary["candidate_count"], 3)
        resource = self.stages[3]["data"]["resources"][0]
        self.assertEqual(resource["quality_level"], "A")

    def test_fields_survive_download_and_archive(self) -> None:
        selected = self.stages[3]["data"]["resources"][0]
        downloaded = self.stages[4]["data"]["resources"][0]
        archived = self.stages[5]["data"]["resources"][0]
        for key, value in selected.items():
            self.assertEqual(downloaded[key], value)
            self.assertEqual(archived[key], value)

    def test_file_size_is_bytes(self) -> None:
        self.assertIsInstance(self.stages[4]["data"]["resources"][0]["file_size"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
