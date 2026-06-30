#!/usr/bin/env python3
"""Validate resource-intent output using only the Python standard library."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SLOT_NAMES = {
    "core_topic", "learning_domain", "target_age", "grade_level",
    "learning_goal", "difficulty", "resource_types", "format_preferences",
    "file_formats",
    "source_preferences", "use_scenario", "version", "language",
    "search_mode",
}
ARRAY_SLOTS = {"resource_types", "format_preferences", "file_formats", "source_preferences"}
STATUSES = {"explicit", "inferred", "defaulted", "unknown"}
DIFFICULTIES = {"启蒙", "基础", "同步", "进阶", "竞赛", "不限"}
RESOURCE_TYPES = {"视频类", "音频类", "文档类", "练习类", "图文类", "图片类", "互动类", "活动类", "不限"}
FORMATS = {
    "视频", "教程", "讲解", "课程", "纪录片", "动画", "讲座", "公开课", "短视频",
    "音频", "故事", "朗诵", "儿歌", "听书", "音频课", "播客", "专辑",
    "文档", "课件", "教案", "讲义", "电子书", "知识点整理", "学习资料",
    "练习题", "习题", "试卷", "作业", "测试题", "练习册", "题卡",
    "百科", "指南", "图文教程", "文章", "知识点", "经验", "方法",
    "挂图", "插画", "思维导图", "手抄报", "范画", "图集", "卡片",
    "软件", "应用", "游戏", "题库", "互动课程", "模拟实验",
    "实验", "手工", "活动方案", "亲子游戏", "实践任务", "绘本", "合集",
}
FILE_FORMATS = {
    "PDF", "DOC", "DOCX", "PPT", "PPTX", "XLS", "XLSX", "TXT", "CSV",
    "EPUB", "MOBI", "MP3", "M4A", "WAV", "MP4", "WEBM", "ZIP",
}
SEARCH_MODES = {"standard", "exhaustive"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("根节点必须是 object")
    return value


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    meta = document.get("_meta")
    summary = document.get("_summary")
    data = document.get("data")
    if not isinstance(meta, dict):
        return ["缺少 object: _meta"]
    if not isinstance(summary, dict):
        return ["缺少 object: _summary"]
    if not isinstance(data, dict):
        return ["缺少 object: data"]

    expected_meta = {
        "stage": 1,
        "skill": "resource-intent",
        "input_from": "request.json",
        "schema_version": "intent-spec/v1",
    }
    for key, expected in expected_meta.items():
        if meta.get(key) != expected:
            errors.append(f"_meta.{key} 必须为 {expected!r}")
    for key in ("session_id", "created_at"):
        if not isinstance(meta.get(key), str) or not meta[key].strip():
            errors.append(f"_meta.{key} 必须是非空字符串")

    if data.get("schema_version") != "intent-spec/v1":
        errors.append("data.schema_version 必须为 intent-spec/v1")
    status = data.get("status")
    if status not in {"ready", "needs_clarification"}:
        errors.append("data.status 必须为 ready 或 needs_clarification")
    if not isinstance(data.get("raw_request"), str) or not data["raw_request"].strip():
        errors.append("data.raw_request 必须是非空字符串")

    slots = data.get("slots")
    if not isinstance(slots, dict):
        errors.append("data.slots 必须是 object")
        slots = {}
    missing_slots = SLOT_NAMES - set(slots)
    extra_slots = set(slots) - SLOT_NAMES
    if missing_slots:
        errors.append(f"data.slots 缺少字段: {sorted(missing_slots)}")
    if extra_slots:
        errors.append(f"data.slots 存在未定义字段: {sorted(extra_slots)}")

    for name in sorted(SLOT_NAMES & set(slots)):
        slot = slots[name]
        if not isinstance(slot, dict):
            errors.append(f"slots.{name} 必须是 object")
            continue
        slot_status = slot.get("status")
        confidence = slot.get("confidence")
        evidence = slot.get("evidence")
        value = slot.get("value")
        if slot_status not in STATUSES:
            errors.append(f"slots.{name}.status 非法")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"slots.{name}.confidence 必须在 0-1")
        if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
            errors.append(f"slots.{name}.evidence 必须是字符串数组")
            evidence = []
        if name in ARRAY_SLOTS:
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"slots.{name}.value 必须是字符串数组")
        elif value is not None and not isinstance(value, str):
            errors.append(f"slots.{name}.value 必须是字符串或 null")
        if slot_status == "explicit" and not evidence:
            errors.append(f"slots.{name} 标为 explicit 时必须提供 evidence")
        if slot_status == "unknown" and value not in (None, []):
            errors.append(f"slots.{name} 标为 unknown 时 value 必须为空")

    difficulty = slots.get("difficulty", {}).get("value") if isinstance(slots.get("difficulty"), dict) else None
    if difficulty is not None and difficulty not in DIFFICULTIES:
        errors.append(f"difficulty 非法: {difficulty!r}")
    resource_types = slots.get("resource_types", {}).get("value", []) if isinstance(slots.get("resource_types"), dict) else []
    if isinstance(resource_types, list) and set(resource_types) - RESOURCE_TYPES:
        errors.append(f"resource_types 含非法值: {sorted(set(resource_types) - RESOURCE_TYPES)}")
    formats = slots.get("format_preferences", {}).get("value", []) if isinstance(slots.get("format_preferences"), dict) else []
    if isinstance(formats, list) and set(formats) - FORMATS:
        errors.append(f"format_preferences 含非法值: {sorted(set(formats) - FORMATS)}")
    file_formats = slots.get("file_formats", {}).get("value", []) if isinstance(slots.get("file_formats"), dict) else []
    if isinstance(file_formats, list):
        noncanonical = [item for item in file_formats if isinstance(item, str) and item != item.upper()]
        if noncanonical:
            errors.append(f"file_formats 必须使用大写规范值: {sorted(noncanonical)}")
        if set(file_formats) - FILE_FORMATS:
            errors.append(f"file_formats 含非法值: {sorted(set(file_formats) - FILE_FORMATS)}")
        if "可打印" in file_formats or "电子版" in file_formats:
            errors.append("可打印/电子版是约束或形态，不是 file_formats")
    search_mode = slots.get("search_mode", {}).get("value") if isinstance(slots.get("search_mode"), dict) else None
    if search_mode is not None and search_mode not in SEARCH_MODES:
        errors.append(f"search_mode 非法: {search_mode!r}")

    constraints = data.get("constraints")
    if not isinstance(constraints, dict):
        errors.append("data.constraints 必须是 object")
        constraints = {}
    for key in ("must", "prefer", "exclude"):
        value = constraints.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"constraints.{key} 必须是非空字符串数组")
    must = set(constraints.get("must", [])) if isinstance(constraints.get("must"), list) else set()
    excluded = set(constraints.get("exclude", [])) if isinstance(constraints.get("exclude"), list) else set()
    if must & excluded:
        errors.append(f"must 与 exclude 冲突: {sorted(must & excluded)}")

    concepts = data.get("search_concepts")
    if not isinstance(concepts, dict):
        errors.append("data.search_concepts 必须是 object")
    else:
        for key in ("canonical_terms", "synonyms", "related_terms"):
            value = concepts.get(key)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"search_concepts.{key} 必须是字符串数组")

    clarification = data.get("clarification")
    if not isinstance(clarification, dict):
        errors.append("data.clarification 必须是 object")
        clarification = {}
    required = clarification.get("required")
    question = clarification.get("question")
    if not isinstance(required, bool):
        errors.append("clarification.required 必须是 boolean")
    if status == "needs_clarification":
        if required is not True:
            errors.append("needs_clarification 状态要求 clarification.required=true")
        if not isinstance(question, str) or not question.strip():
            errors.append("needs_clarification 状态必须提供 question")
    if status == "ready" and required is not False:
        errors.append("ready 状态要求 clarification.required=false")

    assumptions = data.get("assumptions")
    if not isinstance(assumptions, list) or any(not isinstance(item, str) for item in assumptions):
        errors.append("data.assumptions 必须是字符串数组")
        assumptions = []

    if summary.get("status") != status:
        errors.append("_summary.status 必须与 data.status 一致")
    if summary.get("clarification_required") != required:
        errors.append("_summary.clarification_required 必须与 data.clarification.required 一致")
    if summary.get("clarification_question") != question:
        errors.append("_summary.clarification_question 必须与 data.clarification.question 一致")
    if status == "ready" and summary.get("clarification_question") is not None:
        errors.append("ready 状态要求 _summary.clarification_question=null")
    if status == "needs_clarification" and (
        not isinstance(summary.get("clarification_question"), str)
        or not summary["clarification_question"].strip()
    ):
        errors.append("needs_clarification 状态要求 _summary.clarification_question 为非空字符串")
    if summary.get("assumptions") != assumptions:
        errors.append("_summary.assumptions 必须与 data.assumptions 一致")
    core_topic = slots.get("core_topic", {}).get("value") if isinstance(slots.get("core_topic"), dict) else None
    target_age = slots.get("target_age", {}).get("value") if isinstance(slots.get("target_age"), dict) else None
    if summary.get("core_topic") != core_topic:
        errors.append("_summary.core_topic 必须与 slots.core_topic.value 一致")
    if summary.get("target_age") != target_age:
        errors.append("_summary.target_age 必须与 slots.target_age.value 一致")
    if status == "ready" and not core_topic:
        errors.append("ready 状态必须有 core_topic")

    for forbidden in ("queries", "search_tasks", "selected_platforms"):
        if forbidden in data:
            errors.append(f"Intent 不得输出搜索执行字段: data.{forbidden}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 intent-spec/v1 输出")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(load_json(args.file))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
