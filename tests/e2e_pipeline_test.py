#!/usr/bin/env python3
"""Offline simulation of the compact six-stage contract."""

from __future__ import annotations

import unittest


SESSION_ID = "20260630-1030-math-grade4"


def envelope(schema_version: str, data: dict, summary: dict | None = None) -> dict:
    document = {
        "_meta": {
            "schema_version": schema_version,
            "session_id": SESSION_ID,
            "created_at": "2026-06-30T10:30:00+08:00",
        },
        "data": data,
    }
    if summary is not None:
        document["_summary"] = summary
    return document


def run_pipeline() -> list[dict]:
    stage1 = envelope("intent-brief/v1", {
        "status": "ready",
        "raw_request": "四年级数学课程",
        "clarified_need": "为小学四年级孩子收集数学课程资源。用户没有限定教材版本、学习任务、资源形式、语言或费用。",
        "evidence": [
            {"statement": "资源适用于小学四年级数学", "quote": "四年级数学课程"},
        ],
        "requirements": [],
    }, {"status": "ready"})

    stage2 = envelope("search-plan/v1", {"search_tasks": [
        {
            "platform": "generic",
            "priority": "P0",
            "searches": [
                {"query": "小学四年级 数学 学习资源", "max_results": 15, "params": {"engines": ["baidu", "bing"]}},
                {"query": "四年级数学 概念理解 练习材料", "max_results": 15, "params": {"engines": ["baidu", "bing"]}},
            ],
        },
        {
            "platform": "smartedu",
            "priority": "P0",
            "searches": [
                {"query": "小学四年级 数学 同步课程", "max_results": 12},
                {"query": "四年级数学 单元课程", "max_results": 12},
            ],
        },
        {
            "platform": "bilibili",
            "priority": "P2",
            "searches": [
                {"query": "四年级数学 难点演示", "max_results": 8},
            ],
        },
    ]})

    resources = [
        {"resource_id": "smartedu:math-course-001", "platform": "smartedu", "title": "四年级数学同步课程", "source_url": "https://example.cn/math-course-001", "type": "课程", "language": "中文", "download_feasibility": "高", "platform_signals": {"official_source": True}},
        {"resource_id": "bilibili:video-001", "platform": "bilibili", "title": "四年级数学知识点讲解", "source_url": "https://example.com/video-001", "type": "视频", "platform_signals": {"views": 10000}},
        {"resource_id": "generic:web-001", "platform": "generic", "title": "四年级数学公开课程资源", "source_url": "https://example.org/math-course", "type": "网页"},
    ]
    stage3 = envelope(
        "platform-results/v1",
        {"resources": resources, "errors": []},
        {"resource_count": 3, "failed_platforms": []},
    )
    stage4 = envelope("selection/v1", {
        "status": "selected",
        "selected": [{"resource_id": "smartedu:math-course-001", "quality_score": 88}],
    }, {"status": "selected", "selected_count": 1})
    stage5 = envelope("download/v1", {"results": [{
        "resource_id": "smartedu:math-course-001",
        "download_status": "success",
        "files": ["/tmp/downloads/math-course-001.mp4"],
    }]}, {"success_count": 1, "degraded_count": 0, "failed_count": 0})
    stage6 = envelope("archive/v1", {"results": [{
        "resource_id": "smartedu:math-course-001",
        "archive_status": "archived",
        "library_paths": ["数学/小学四年级/math-course-001.mp4"],
    }]}, {"archived_count": 1, "skipped_count": 0, "failed_count": 0})
    return [stage1, stage2, stage3, stage4, stage5, stage6]


class TestSixStagePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stages = run_pipeline()

    def test_common_envelope_is_minimal(self) -> None:
        for index, stage in enumerate(self.stages):
            expected = {"_meta", "data"} if index == 1 else {"_meta", "_summary", "data"}
            self.assertEqual(set(stage), expected)
            self.assertEqual(set(stage["_meta"]), {"schema_version", "session_id", "created_at"})
            self.assertNotIn("schema_version", stage["data"])

    def test_flow_summaries_are_minimal_and_consistent(self) -> None:
        self.assertEqual(self.stages[0]["_summary"], {"status": "ready"})
        self.assertEqual(self.stages[2]["_summary"]["resource_count"], len(self.stages[2]["data"]["resources"]))
        self.assertEqual(self.stages[3]["_summary"]["selected_count"], len(self.stages[3]["data"]["selected"]))
        self.assertEqual(sum(self.stages[4]["_summary"].values()), len(self.stages[4]["data"]["results"]))
        self.assertEqual(sum(self.stages[5]["_summary"].values()), len(self.stages[5]["data"]["results"]))

    def test_intent_uses_semantic_brief_instead_of_slots(self) -> None:
        data = self.stages[0]["data"]
        self.assertEqual(
            set(data),
            {"status", "raw_request", "clarified_need", "evidence", "requirements"},
        )
        self.assertNotIn("slots", data)
        self.assertNotIn("search_concepts", data)

    def test_search_contains_only_executable_fields(self) -> None:
        for task in self.stages[1]["data"]["search_tasks"]:
            self.assertEqual(set(task), {"platform", "priority", "searches"})
            for search in task["searches"]:
                self.assertTrue({"query", "max_results"}.issubset(search))
        self.assertEqual(set(self.stages[1]["data"]), {"search_tasks"})

    def test_platform_output_has_no_intent_or_final_quality(self) -> None:
        self.assertEqual(set(self.stages[2]["data"]), {"resources", "errors"})
        for resource in self.stages[2]["data"]["resources"]:
            self.assertNotIn("quality_score", resource)
            self.assertNotIn("intent_context", resource)

    def test_later_stages_use_resource_references(self) -> None:
        selected = self.stages[3]["data"]["selected"][0]
        downloaded = self.stages[4]["data"]["results"][0]
        archived = self.stages[5]["data"]["results"][0]
        self.assertEqual(selected["resource_id"], downloaded["resource_id"])
        self.assertEqual(downloaded["resource_id"], archived["resource_id"])
        self.assertNotIn("title", selected)
        self.assertNotIn("source_url", downloaded)
        self.assertNotIn("files", archived)


if __name__ == "__main__":
    unittest.main(verbosity=2)
