#!/usr/bin/env python3
"""SmartEdu 公开页面 URL 解析。

本模块集中复刻 basic.smartedu.cn 前端的资源跳转规则。对无法确认的非课程
资源不再伪造成 prepare/detail 链接，而是保持未解析，让调用方明确统计覆盖缺口。
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from _text_utils import first_value, norm


BASE_URL = "https://basic.smartedu.cn"
READING_BASE_URL = "https://reading.smartedu.cn"

COURSE_TAB_CODES = frozenset(
    {
        "classActivity",
        "examinationPapers",
        "prepareLesson",
        "qualityCourse",
        "teachingKnMicroLesson",
    }
)
COURSE_PREPARE_TYPES = frozenset(
    {
        "lesson_plandesign",
        "micro_lesson",
        "assets_teaching",
        "coursewares",
        "homework_assignment",
        "knowledge_micro_lesson",
    }
)
GENERIC_DETAIL_CATALOGS = frozenset(
    {
        "sedu",
        "family",
        "labourEdu",
        "schoolService",
        "eduReform",
        "topic",
        "technologyEdu",
        "AIEducation",
        "nationality",
        "childhoodEdu",
    }
)
COURSE_DETAIL_TABS = frozenset({"teacherTraining", "sport", "art"})
URL_CONTENT_TYPES = frozenset({"x_url", "assets_url", "x_smarturl"})

_LIBRARY_LOOKUP: dict[str, dict[str, str]] = {}


def set_library_lookup(lookup: dict[str, dict[str, str]] | None) -> None:
    """设置进程内 library_id 映射，供 detail_page_from_search_item 使用。"""
    global _LIBRARY_LOOKUP
    _LIBRARY_LOOKUP = lookup or {}


def build_library_lookup(data: Any) -> dict[str, dict[str, str]]:
    """从官方 librarylist JSON 构建 library_id -> 路由元数据映射。"""
    lookup: dict[str, dict[str, str]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        library_id = norm(node.get("id") or node.get("library_id") or node.get("libraryId"))
        if library_id:
            catalog = norm(node.get("catalog") or node.get("catalog_type") or node.get("tab_code"))
            row_type = norm(node.get("type") or node.get("code"))
            sub_catalog = norm(node.get("sub_catalog") or node.get("subCatalog")) or row_type
            lookup[library_id] = {
                "id": library_id,
                "catalog": catalog,
                "type": row_type,
                "sub_catalog": sub_catalog,
                "name": norm(node.get("name") or node.get("title") or node.get("catalog_name")),
            }
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    walk(data)
    return lookup


def is_supported_public_page_url(url: str) -> bool:
    """识别携带有效资源身份的 SmartEdu 公开前端路由。"""
    if not url.startswith(("http://", "https://")):
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc not in {"basic.smartedu.cn", "reading.smartedu.cn"}:
        return False
    query = urllib.parse.parse_qs(parsed.query)

    def has_any(*names: str) -> bool:
        return any(query.get(name) for name in names)

    if parsed.path == "/qualityCourse":
        return has_any("courseId", "course_id")
    if parsed.path == "/syncClassroom/prepare/detail":
        return has_any("resourceId", "resource_id", "lessonId", "lesson_id")
    if parsed.path == "/syncClassroom/classActivity":
        return has_any("activityId", "activity_id")
    if parsed.path == "/syncClassroom/teachingLesson":
        return has_any("courseId", "course_id")
    if parsed.path in {"/syncClassroom/examinationpapers", "/syncClassroom/homeworkExercise", "/syncClassroom/detail"}:
        return has_any("resourceId", "resource_id")
    if parsed.path in {"/syncClassroom/experimentLesson", "/specialEdu/courseDetail", "/specialEdu/yearQualityCourse"}:
        return has_any("courseId", "course_id")
    if parsed.path == "/syncClassroom/experiment/safety/detail":
        return has_any("contentId", "content_id")
    if parsed.path == "/lecturer":
        return has_any("lecturerId", "lecturer_id")
    if parsed.path.startswith("/questions/"):
        return len(parsed.path.split("/")) >= 3
    if parsed.path.startswith("/training/"):
        return len(parsed.path.split("/")) >= 3
    if parsed.path.startswith("/tResource/"):
        return len(parsed.path.split("/")) >= 3
    if parsed.path.startswith("/schSpace/"):
        return len(parsed.path.split("/")) >= 3
    if parsed.path.count("/") >= 2 and parsed.path.endswith("/courseDetail"):
        return has_any("courseId", "course_id")
    if parsed.path.count("/") >= 2 and parsed.path.endswith("/courseIndex"):
        return has_any("courseId", "course_id")
    if parsed.path.count("/") >= 2 and parsed.path.endswith("/micro/detail"):
        return has_any("contentId", "content_id")
    if parsed.path.count("/") >= 2 and parsed.path.endswith("/detail"):
        return has_any("contentId", "content_id")
    return False


def identity_from_detail_page_url(url: str) -> dict[str, str]:
    if not url.startswith(("http://", "https://")):
        return {}
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)

    def query_value(*names: str) -> str:
        for name in names:
            values = query.get(name)
            if values:
                return norm(values[0])
        return ""

    path_parts = [part for part in parsed.path.split("/") if part]
    catalog_from_path = path_parts[0] if path_parts else ""
    page_type = path_parts[1] if len(path_parts) > 1 else ""
    resource_id = query_value(
        "contentId",
        "content_id",
        "resourceId",
        "resource_id",
        "activityId",
        "activity_id",
        "courseId",
        "course_id",
        "lecturerId",
        "lecturer_id",
        "id",
    )
    if not resource_id and catalog_from_path in {"questions", "training", "tResource", "schSpace"} and len(path_parts) > 1:
        resource_id = norm(path_parts[1])
    content_type = query_value("contentType", "content_type", "resourceType", "resource_type", "resouceType")
    if catalog_from_path == "syncClassroom" and page_type == "classActivity" and not content_type:
        content_type = "national_lesson"
    if catalog_from_path == "qualityCourse" and not content_type:
        content_type = "elite_lesson"
    return {
        "resource_id": resource_id,
        "tab_code": query_value("tabCode", "tab_code", "catalogType", "catalog") or catalog_from_path,
        "catalog": query_value("catalogType", "catalog") or catalog_from_path,
        "sub_catalog": query_value("subCatalog", "sub_catalog"),
        "content_type": content_type,
    }


def detail_page_from_search_item(item: dict[str, Any], library_lookup: dict[str, dict[str, str]] | None = None) -> str:
    """为 SmartEdu 搜索项生成官方公开页面 URL。"""
    explicit = norm(first_value(item, ["url", "web_url", "webUrl", "href", "detail_url", "detailUrl", "share_url", "shareUrl"]))
    if is_supported_public_page_url(explicit):
        return explicit

    identity = search_item_route_identity(item, library_lookup)
    rid = identity["resource_id"]
    content_type = identity["content_type"]
    tab_code = identity["tab_code"]
    library_id = identity["library_id"]
    sub_catalog = identity["sub_catalog"]
    if not rid:
        return ""

    if content_type == "questions" and "colmres" not in library_id:
        return _absolute(_path_with_query(f"/questions/{_quote(rid)}", [("containerId", library_id)]))
    if tab_code in COURSE_TAB_CODES or content_type in COURSE_PREPARE_TYPES or content_type in {
        "national_lesson",
        "elite_lesson",
        "examinationpapers",
        "teaching_lesson",
        "homework_exercise",
        "prepare_lesson",
        "experiment_elite_lesson",
        "experiment_talk_lesson",
        "knowledge_micro_lesson_package",
    }:
        return _absolute(_sync_classroom_path(identity))
    if tab_code in COURSE_DETAIL_TABS:
        return _absolute(_course_detail_path(identity))
    if tab_code == "specialEdu":
        return _absolute(_special_edu_path(identity))
    if tab_code == "tchMaterial" or content_type == "tchMaterial":
        return _absolute(
            _path_with_query(
                "/tchMaterial/detail",
                [
                    ("contentType", content_type or "tchMaterial"),
                    ("contentId", rid),
                    ("catalogType", "tchMaterial"),
                    ("subCatalog", sub_catalog or "dzjc"),
                ],
            )
        )
    if tab_code == "lecturer":
        return _absolute(_path_with_query("/lecturer", [("lecturerId", rid)]))
    if tab_code in {"reading_youth", "reading_elder"}:
        catalog = tab_code.replace("reading_", "")
        return _with_base(
            READING_BASE_URL,
            _path_with_query(
                f"/{_quote(catalog)}/detail",
                [("contentType", content_type), ("contentId", rid), ("catalogType", catalog)],
            ),
        )
    if tab_code in {"school-space", "school-space-article", "school-space-res"}:
        return _absolute(_school_space_path(identity))
    if tab_code in {
        "studio-inst",
        "studio-inst-article",
        "studio-inst-res",
        "studio-inst-teachres",
        "studio-inst-spres",
        "studio-inst-exrc",
        "teach-studio",
        "expert-studio",
        "studio-ai",
        "studio-ai-xvideo",
        "studio-ai-xnews",
    }:
        return _absolute(_studio_path(identity))
    if tab_code == "areaSite":
        micro_type = identity["area_micro_type"] or "areaSite"
        return _absolute(
            _path_with_query(
                f"/{_quote(micro_type)}/micro/detail",
                [("contentType", content_type), ("contentId", rid), ("libraryId", library_id)],
            )
        )
    if tab_code in GENERIC_DETAIL_CATALOGS:
        return _absolute(_generic_detail_path(tab_code, content_type, rid, sub_catalog))
    if tab_code == "live" or tab_code == "portal_live":
        return _absolute(f"/publicLiveMiddle/{_quote(rid)}")
    return ""


def unresolved_reason(item: dict[str, Any], library_lookup: dict[str, dict[str, str]] | None = None) -> str:
    identity = search_item_route_identity(item, library_lookup)
    if not identity["resource_id"]:
        return "missing_resource_id"
    if not identity["tab_code"]:
        return "missing_tab_code"
    return f"unsupported_route:{identity['tab_code']}:{identity['content_type'] or 'unknown_type'}"


def search_item_route_identity(item: dict[str, Any], library_lookup: dict[str, dict[str, str]] | None = None) -> dict[str, str]:
    lookup = library_lookup if library_lookup is not None else _LIBRARY_LOOKUP
    library_id = norm(first_value(item, ["library_id", "libraryId", "container_id", "containerId"]))
    library = lookup.get(library_id, {}) if library_id else {}
    content_type = norm(
        first_value(item, ["resource_type_code", "resourceTypeCode", "content_type", "contentType", "resource_type", "resourceType"])
    )
    tab_code = norm(first_value(item, ["tab_code", "tabCode", "channel_code", "channelCode", "catalog", "catalog_type", "catalogType"]))
    if not tab_code:
        tab_code = norm(library.get("catalog"))
    if tab_code == "sedu" and norm(library.get("catalog")) == "specialEdu":
        tab_code = "specialEdu"
    sub_catalog = norm(
        first_value(item, ["subCatalog", "sub_catalog", "sub_catalog_code", "subCatalogCode", "topic_type", "topicType"])
    )
    if not sub_catalog:
        sub_catalog = norm(library.get("sub_catalog"))
    return {
        "resource_id": norm(first_value(item, ["id", "resource_id", "resourceId", "content_id", "contentId", "course_id", "courseId"])),
        "content_type": content_type,
        "tab_code": tab_code,
        "library_id": library_id,
        "sub_catalog": sub_catalog,
        "description": norm(item.get("description")),
        "prepare_resource_type_code": norm(item.get("prepare_resource_type_code") or item.get("prepareResourceTypeCode")),
        "area_micro_type": _area_micro_type(item, library),
        "scope_id": norm(first_value(item, ["scope_id", "scopeId"])) or _scope_from_library_id(library_id),
    }


def _sync_classroom_path(identity: dict[str, str]) -> str:
    rid = identity["resource_id"]
    content_type = identity["content_type"]
    sub_catalog = identity["sub_catalog"]
    common: list[tuple[str, str]] = []
    if identity["library_id"]:
        common.append(("libraryId", identity["library_id"]))

    if sub_catalog == "experimentSafety":
        return _path_with_query(
            "/syncClassroom/experiment/safety/detail",
            [("contentId", rid), ("contentType", content_type), ("catalogType", "syncClassroom"), ("subCatalog", "experimentSafety")] + common,
        )
    if content_type == "national_lesson":
        return _path_with_query("/syncClassroom/classActivity", [("activityId", rid)] + common)
    if content_type == "elite_lesson":
        return _path_with_query("/qualityCourse", [("courseId", rid)] + common)
    if content_type == "examinationpapers":
        return _path_with_query("/syncClassroom/examinationpapers", [("resourceId", rid)] + common)
    if content_type == "teaching_lesson":
        return _path_with_query("/syncClassroom/teachingLesson", [("courseId", rid)] + common)
    if content_type == "homework_exercise":
        return _path_with_query("/syncClassroom/homeworkExercise", [("resourceId", rid)] + common)
    if content_type == "prepare_lesson":
        return _path_with_query("/syncClassroom/prepare/detail", [("lessonId", rid)] + common)
    if content_type in {"experiment_elite_lesson", "experiment_talk_lesson"}:
        return _path_with_query("/syncClassroom/experimentLesson", [("courseId", rid)] + common)
    if identity["prepare_resource_type_code"] or content_type in COURSE_PREPARE_TYPES:
        return _path_with_query("/syncClassroom/prepare/detail", [("resourceId", rid)] + common)
    if content_type == "knowledge_micro_lesson_package":
        return _path_with_query("/syncClassroom/detail", [("resourceId", rid), ("resourceType", content_type)] + common)
    if content_type:
        return _path_with_query("/syncClassroom/detail", [("resourceId", rid), ("resourceType", content_type)] + common)
    return ""


def _course_detail_path(identity: dict[str, str]) -> str:
    tab_code = identity["tab_code"]
    rid = identity["resource_id"]
    content_type = identity["content_type"]
    description = identity["description"]
    if tab_code == "teacherTraining" and content_type == "auxo-train":
        return f"/training/{_quote(rid)}"
    if content_type in URL_CONTENT_TYPES and description.startswith(("http://", "https://")):
        return description
    page = "courseIndex" if tab_code == "teacherTraining" else "courseDetail"
    return _path_with_query(f"/{_quote(tab_code)}/{page}", [("courseId", rid)])


def _special_edu_path(identity: dict[str, str]) -> str:
    rid = identity["resource_id"]
    content_type = identity["content_type"]
    library_id = identity["library_id"]
    sub_catalog = identity["sub_catalog"]
    if content_type == "t_course":
        return _path_with_query("/specialEdu/courseDetail", [("courseId", rid), ("libraryId", library_id)])
    if content_type == "special_edu_lesson":
        return _path_with_query(
            "/specialEdu/yearQualityCourse",
            [("courseId", rid), ("libraryId", library_id), ("courseType", "special_edu_lesson")],
        )
    return _path_with_query(
        "/specialEdu/detail",
        [
            ("contentType", content_type),
            ("contentId", rid),
            ("catalogType", "specialEdu"),
            ("subCatalog", sub_catalog),
            ("libraryId", library_id),
        ],
    )


def _generic_detail_path(catalog: str, content_type: str, resource_id: str, sub_catalog: str) -> str:
    public_catalog = "sedu" if catalog == "specialEdu" else catalog
    return _path_with_query(
        f"/{_quote(public_catalog or 'content')}/detail",
        [
            ("contentType", content_type),
            ("contentId", resource_id),
            ("catalogType", public_catalog),
            ("subCatalog", sub_catalog),
            ("_xst_style", "true"),
        ],
    )


def _school_space_path(identity: dict[str, str]) -> str:
    tab_code = identity["tab_code"]
    rid = identity["resource_id"]
    scope_id = identity["scope_id"]
    if tab_code == "school-space-res" and scope_id:
        return _path_with_query(f"/schSpace/{_quote(scope_id)}", [("module", "resource"), ("contentId", rid)])
    if tab_code == "school-space-article" and scope_id:
        return _path_with_query(f"/schSpace/{_quote(scope_id)}", [("module", "news"), ("contentId", rid)])
    return f"/schSpace/{_quote(rid)}"


def _studio_path(identity: dict[str, str]) -> str:
    tab_code = identity["tab_code"]
    rid = identity["resource_id"]
    scope_id = identity["scope_id"]
    if tab_code == "studio-inst":
        return f"/tResource/{_quote(rid)}"
    if tab_code == "teach-studio":
        return f"/tStudio/{_quote(rid)}"
    if tab_code == "expert-studio":
        return f"/eStudio/{_quote(rid)}"
    if tab_code == "studio-ai":
        return f"/aStudio/{_quote(rid)}"
    prefix = {
        "studio-inst-article": "tResource",
        "studio-inst-res": "tResource",
        "studio-inst-teachres": "tResource",
        "studio-inst-spres": "tResource",
        "studio-inst-exrc": "tResource",
        "teach-studio-article": "tStudio",
        "teach-studio-res": "tStudio",
        "expert-studio-article": "eStudio",
        "expert-studio-res": "eStudio",
        "studio-ai-xvideo": "aStudio",
        "studio-ai-xnews": "aStudio",
    }.get(tab_code, "tResource")
    module = _studio_module(tab_code)
    if not scope_id:
        return f"/{prefix}/{_quote(rid)}"
    return _path_with_query(f"/{prefix}/{_quote(scope_id)}", [("module", module), ("contentId", rid)])


def _studio_module(tab_code: str) -> str:
    if tab_code.endswith("-article") or tab_code.endswith("-xnews"):
        return "news"
    if tab_code.endswith("-res"):
        return "resource"
    if tab_code == "studio-ai-xvideo":
        return "video"
    if tab_code in {"studio-inst-teachres", "studio-inst-spres", "studio-inst-exrc"}:
        return tab_code
    return "all"


def _area_micro_type(item: dict[str, Any], library: dict[str, str]) -> str:
    value = norm(item.get("catalog") or item.get("area_site") or library.get("catalog"))
    if value in {"hn", "hq"}:
        return value
    return ""


def _scope_from_library_id(library_id: str) -> str:
    return library_id.split("_", 1)[0] if "_" in library_id else ""


def _path_with_query(path: str, params: list[tuple[str, str]]) -> str:
    pairs = [(key, value) for key, value in params if value != ""]
    if not pairs:
        return path
    return f"{path}?{urllib.parse.urlencode(pairs, doseq=False, safe=':/')}"


def _absolute(path_or_url: str) -> str:
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return _with_base(BASE_URL, path_or_url)


def _with_base(base: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return base.rstrip("/") + path


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")
