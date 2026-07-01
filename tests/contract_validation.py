#!/usr/bin/env python3
"""Validate the self-contained six-stage Skill pipeline contract."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

STAGES = [
    (1, "resource-intent", "stage1_intent.json"),
    (2, "resource-search", "stage2_search_plan.json"),
    (3, "resource-platforms", "stage3_search_results.json"),
    (4, "resource-selector", "stage4_selection.json"),
    (5, "resource-downloader", "stage5_download.json"),
    (6, "library-manager", "stage6_archive.json"),
]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class TestSkillPipelineContract(unittest.TestCase):
    def test_all_skill_entrypoints_exist(self) -> None:
        for _, skill, _ in STAGES:
            self.assertTrue((ROOT / skill / "SKILL.md").is_file(), skill)
        self.assertTrue((ROOT / "learning-resource-flow/SKILL.md").is_file())

    def test_frontmatter_names_match_directories(self) -> None:
        for _, skill, _ in STAGES:
            text = read(f"{skill}/SKILL.md")
            match = re.search(r"^---\s*\nname:\s*([^\n]+)", text)
            self.assertIsNotNone(match, skill)
            self.assertEqual(match.group(1).strip(), skill)

    def test_flow_declares_six_ordered_outputs(self) -> None:
        flow = read("learning-resource-flow/SKILL.md")
        self.assertIn("request.json", flow)
        positions = []
        for stage, skill, filename in STAGES:
            self.assertIn(f"stage {stage}", flow.lower())
            self.assertIn(skill, flow)
            self.assertIn(filename, flow)
            positions.append(flow.index(filename))
        self.assertEqual(positions, sorted(positions))

    def test_each_owner_declares_its_output(self) -> None:
        for _, skill, filename in STAGES:
            self.assertIn(filename, read(f"{skill}/SKILL.md"), skill)

    def test_adjacent_file_handoffs(self) -> None:
        for index in range(1, len(STAGES)):
            upstream_file = STAGES[index - 1][2]
            downstream_skill = STAGES[index][1]
            self.assertIn(upstream_file, read(f"{downstream_skill}/SKILL.md"))

    def test_platform_search_has_no_final_quality_fields_in_schema(self) -> None:
        stage3 = read("resource-platforms/references/search-interface.md")
        self.assertIn("质量评分由 Selector 完成", stage3)

    def test_selector_owns_business_filtering_and_scoring(self) -> None:
        selector = read("resource-selector/SKILL.md")
        for phrase in ("跨平台去重", "业务过滤", "统一质量评分", "用户选择"):
            self.assertIn(phrase, selector)

    def test_platform_role_is_execution_only(self) -> None:
        platforms = read("resource-platforms/SKILL.md")
        self.assertIn("不负责", platforms)
        self.assertIn("跨平台相似去重", platforms)
        self.assertIn("最终质量评分", platforms)

    def test_data_flow_uses_six_stage_files(self) -> None:
        contract = read("docs/pipeline-data-contract.md")
        self.assertIn("request.json", contract)
        for _, _, filename in STAGES:
            self.assertIn(filename, contract)

    def test_pipeline_data_contract_covers_every_handoff(self) -> None:
        contract_path = ROOT / "docs/pipeline-data-contract.md"
        self.assertTrue(contract_path.is_file())
        contract = contract_path.read_text(encoding="utf-8")
        for filename in ("manifest.json", "request.json", *(item[2] for item in STAGES)):
            self.assertIn(filename, contract)
        for version in (
            "request/v1",
            "session-manifest/v1",
            "intent-brief/v1",
            "search-plan/v1",
            "platform-results/v1",
            "selection/v1",
            "download/v1",
            "archive/v1",
        ):
            self.assertIn(version, contract)
        self.assertIn("引用与数量不变量", contract)
        self.assertIn("统一错误对象", contract)

    def test_flow_points_to_authoritative_data_contract(self) -> None:
        self.assertIn("docs/pipeline-data-contract.md", read("learning-resource-flow/SKILL.md"))

    def test_removed_duplicate_flow_draft_and_readme(self) -> None:
        self.assertFalse((ROOT / "learning-resource-flow/SKILL-建议版.md").exists())
        self.assertFalse((ROOT / "README.md").exists())

    def test_redundant_documents_are_removed(self) -> None:
        removed = [
            "docs/data-flow-guide.md",
            "resource-platforms/references/download-methods.md",
            "resource-platforms/references/test-cases.md",
            "resource-platforms/references/schemas/quality-rubric.md",
        ]
        for relative in removed:
            self.assertFalse((ROOT / relative).exists(), relative)
        self.assertIn("references/error-codes.md", read("resource-downloader/SKILL.md"))

    def test_archive_only_keeps_historical_architecture(self) -> None:
        archived_docs = {
            path.relative_to(ROOT / "_archive").as_posix()
            for path in (ROOT / "_archive").rglob("*.md")
        }
        self.assertEqual(archived_docs, {"系统架构说明.md"})

    def test_intent_and_search_have_versioned_contracts(self) -> None:
        required = [
            "learning-resource-flow/scripts/validate_request.py",
            "resource-intent/schemas/input.schema.json",
            "resource-intent/schemas/output.schema.json",
            "resource-intent/scripts/validate_output.py",
            "resource-search/schemas/input.schema.json",
            "resource-search/schemas/output.schema.json",
            "resource-search/scripts/validate_output.py",
            "resource-search/config/platform-catalog.json",
            "resource-platforms/config/search-registry.json",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_flow_owns_stage1_request_and_clarification_loop(self) -> None:
        flow = read("learning-resource-flow/SKILL.md")
        for phrase in (
            "执行 Flow 的模型必须先创建 `request.json`",
            "validate_request.py",
            "data.clarification.question",
            "waiting_user",
            "不得调用 Search",
        ):
            self.assertIn(phrase, flow)

    def test_intent_does_not_own_query_generation(self) -> None:
        intent = read("resource-intent/SKILL.md")
        self.assertIn("不选择平台", intent)
        self.assertIn("不生成可执行查询", intent)
        self.assertNotIn("至少生成 **10 个**", intent)

    def test_search_is_only_query_planner(self) -> None:
        search = read("resource-search/SKILL.md")
        self.assertIn("多平台搜索计划", search)
        self.assertIn("不执行搜索、筛选结果或下载资源", search)
        self.assertIn("config/platform-catalog.json", search)
        self.assertIn("references/routing-rules.md", search)
        self.assertNotIn("../resource-platforms/config/search-registry.json", search)
        self.assertIn("searches[]", search)
        self.assertNotIn("coverage_plan", search)
        self.assertNotIn("coverage_ids", search)

    def test_duplicate_search_references_removed(self) -> None:
        removed = [
            "resource-search/references/优质站点白名单.md",
            "resource-search/references/搜索执行规则.md",
            "resource-search/references/search-capabilities.md",
            "resource-search/references/guides/search-strategy.md",
            "resource-search/references/guides/platform-search-capabilities.md",
            "resource-search/references/config/platform-mapping.md",
        ]
        for relative in removed:
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
