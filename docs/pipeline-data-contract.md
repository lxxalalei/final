# 学习资源六阶段数据输入输出契约

> 契约版本：`pipeline-data-contract/v1`
>
> 适用范围：`learning-resource-flow` 调度的 request、manifest 与六个阶段文件
> 本文只定义结构、字段、状态和传递规则，不定义各 Skill 的语义判断方法。

## 目录

1. [契约边界](#1-契约边界)
2. [文件与阶段总览](#2-文件与阶段总览)
3. [公共数据规范](#3-公共数据规范)
4. [request.json](#4-requestjson)
5. [manifest.json](#5-manifestjson)
6. [Stage 1：stage1_intent.json](#6-stage-1stage1_intentjson)
7. [Stage 2：stage2_search_plan.json](#7-stage-2stage2_search_planjson)
8. [公共资源对象](#8-公共资源对象)
9. [Stage 3：stage3_search_results.json](#9-stage-3stage3_search_resultsjson)
10. [Stage 4：stage4_selection.json](#10-stage-4stage4_selectionjson)
11. [Stage 5：stage5_download.json](#11-stage-5stage5_downloadjson)
12. [Stage 6：stage6_archive.json](#12-stage-6stage6_archivejson)
13. [统一错误对象](#13-统一错误对象)
14. [字段传递与计数不变量](#14-字段传递与计数不变量)
15. [失败、等待与重跑](#15-失败等待与重跑)
16. [版本兼容规则](#16-版本兼容规则)

## 1. 契约边界

本契约约束以下内容：

- Flow 创建的请求快照和会话状态。
- 六个阶段文件的名称、写入者和读取者。
- 每个阶段 `_meta`、`_summary`、`data` 的结构。
- 资源对象从搜索结果到归档结果的字段生命周期。
- 失败、空结果、用户等待和重跑时的数据表达。

本契约不约束：

- Intent 如何理解自然语言。
- Search 如何选择平台或生成关键词。
- Selector 如何计算质量分。
- Downloader 具体使用什么工具。
- Library Manager 如何确定资料库分类。

这些属于各 Skill 自己的语义或执行策略。

## 2. 文件与阶段总览

### 2.1 会话目录

```text
.learning-resource-work/sessions/{session_id}/
├── manifest.json
├── request.json
├── stage1_intent.json
├── stage2_search_plan.json
├── stage3_search_results.json
├── stage4_selection.json
├── stage5_download.json
├── stage6_archive.json
└── downloads/
```

### 2.2 文件责任

| 文件 | Schema | 唯一写入者 | 主要读取者 |
|---|---|---|---|
| `request.json` | `request/v1` | learning-resource-flow | resource-intent |
| `manifest.json` | `session-manifest/v1` | learning-resource-flow | 全部 Skill 只读 |
| `stage1_intent.json` | `intent-spec/v1` | resource-intent | resource-search、flow |
| `stage2_search_plan.json` | `search-plan/v1` | resource-search | resource-platforms、flow |
| `stage3_search_results.json` | `platform-results/v1` | resource-platforms | resource-selector、flow |
| `stage4_selection.json` | `selection/v1` | resource-selector | resource-downloader、flow |
| `stage5_download.json` | `download/v1` | resource-downloader | library-manager、flow |
| `stage6_archive.json` | `archive/v1` | library-manager | flow |

### 2.3 阶段交接

| 阶段 | 输入 | 输出 | 业务职责 |
|---|---|---|---|
| 1 | `request.json` | `stage1_intent.json` | 结构化需求或提出一个澄清问题 |
| 2 | `stage1_intent.json` | `stage2_search_plan.json` | 生成可执行搜索计划 |
| 3 | `stage2_search_plan.json` | `stage3_search_results.json` | 执行平台搜索并归一化原始结果 |
| 4 | `stage3_search_results.json` | `stage4_selection.json` | 去重、过滤、评分并保存用户选择 |
| 5 | `stage4_selection.json` | `stage5_download.json` | 下载、重试和降级 |
| 6 | `stage5_download.json` | `stage6_archive.json` | 入库、资料库去重和索引 |

## 3. 公共数据规范

### 3.1 阶段文件 envelope

Stage 1—6 统一使用三个顶层字段：

```json
{
  "_meta": {},
  "_summary": {},
  "data": {}
}
```

除各阶段明确声明的字段外，不增加其他顶层字段。

### 3.2 `_meta`

```json
{
  "stage": 3,
  "session_id": "20260630-1030-math-grade3",
  "skill": "resource-platforms",
  "created_at": "2026-06-30T10:33:00+08:00",
  "input_from": "stage2_search_plan.json",
  "schema_version": "platform-results/v1"
}
```

| 字段 | 类型 | 必填 | 规则 |
|---|---|:---:|---|
| `stage` | integer | 是 | 1—6，必须与文件阶段一致 |
| `session_id` | string | 是 | 必须与会话目录名、上游文件一致 |
| `skill` | string | 是 | 当前文件的唯一写入者 |
| `created_at` | string | 是 | ISO 8601，必须包含时区 |
| `input_from` | string | 是 | 直接上游文件名，不使用绝对路径 |
| `schema_version` | string | 是 | 当前阶段 data 契约版本 |

### 3.3 `_summary`

- 只保存 Flow 做调度所需的状态和计数。
- 不保存完整资源数组、搜索词列表或错误详情。
- 数量字段必须能够从 `data` 重新计算。
- Flow 可以把 `_summary` 复制到 manifest；不得改写其语义。

### 3.4 `data`

- 保存该阶段的完整业务数据。
- `data.schema_version` 必须与 `_meta.schema_version` 相同。
- 下游读取 `data`；Flow 正常调度只读取 `_summary`。

### 3.5 基础类型

| 内容 | 规范 |
|---|---|
| 时间 | ISO 8601 且包含时区，例如 `2026-06-30T10:30:00+08:00` |
| 文件大小 | integer，单位为字节 |
| 时长 | number，单位为秒；未知使用 `null` |
| URL | 完整 `http://` 或 `https://` 地址 |
| 本地文件路径 | 绝对路径 |
| 资料库路径 | 相对资料库根目录的路径 |
| 未知标量 | `null`，不使用空字符串代替 |
| 未知列表 | `[]` |
| 未知对象 | `{}` |
| 枚举 | 使用契约定义的小写值；展示层再转换为中文 |

### 3.6 ID

- `session_id`：`{YYYYMMDD}-{HHmm}-{topic-slug}`。
- `task_id`：`task-{语义化短标识}`，会话内唯一。
- `resource_id`：`{platform}:{platform_resource_id}`。
- generic 无平台 ID 时，使用规范化 URL 的稳定哈希作为 `platform_resource_id`。

## 4. request.json

`request.json` 是 Flow 写给 Intent 的原始证据快照，不使用阶段 envelope。

```json
{
  "_meta": {
    "session_id": "20260630-1030-math-grade3",
    "created_at": "2026-06-30T10:30:00+08:00",
    "skill": "learning-resource-flow"
  },
  "data": {
    "schema_version": "request/v1",
    "raw_request": "帮我找三年级数学练习题",
    "conversation_evidence": [
      {
        "role": "assistant",
        "content": "你希望练习题带答案吗？"
      },
      {
        "role": "user",
        "content": "需要带答案。"
      }
    ],
    "user_confirmed_facts": ["练习题需要带答案"]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `_meta.session_id` | string | 是 | 当前会话 ID |
| `_meta.created_at` | string | 是 | 首次创建时间；澄清追加时不修改 |
| `_meta.skill` | string | 是 | 固定 `learning-resource-flow` |
| `data.schema_version` | string | 是 | 固定 `request/v1` |
| `data.raw_request` | string | 是 | 用户最初请求原文，后续不得改写 |
| `data.conversation_evidence` | array | 是 | 与当前需求直接相关的用户/助手原话，按时间追加 |
| `data.user_confirmed_facts` | string[] | 否 | 用户明确确认的事实；不得写模型推断 |

`conversation_evidence[]` 每项只能包含：

| 字段 | 类型 | 枚举 |
|---|---|---|
| `role` | string | `user` / `assistant` |
| `content` | string | 非空原文 |

## 5. manifest.json

`manifest.json` 由 Flow 唯一写入，用于调度和断点恢复，不保存业务资源。

```json
{
  "schema_version": "session-manifest/v1",
  "session_id": "20260630-1030-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "created_at": "2026-06-30T10:30:00+08:00",
  "updated_at": "2026-06-30T10:35:00+08:00",
  "status": "in_progress",
  "current_stage": 3,
  "stages": {
    "stage1": {
      "owner": "resource-intent",
      "status": "completed",
      "input": "request.json",
      "output": "stage1_intent.json",
      "started_at": "2026-06-30T10:30:10+08:00",
      "completed_at": "2026-06-30T10:31:00+08:00",
      "summary": {},
      "error": null
    },
    "stage2": {
      "owner": "resource-search",
      "status": "completed",
      "input": "stage1_intent.json",
      "output": "stage2_search_plan.json",
      "started_at": "2026-06-30T10:31:10+08:00",
      "completed_at": "2026-06-30T10:32:00+08:00",
      "summary": {},
      "error": null
    },
    "stage3": {
      "owner": "resource-platforms",
      "status": "in_progress",
      "input": "stage2_search_plan.json",
      "output": "stage3_search_results.json",
      "started_at": "2026-06-30T10:32:10+08:00",
      "completed_at": null,
      "summary": null,
      "error": null
    },
    "stage4": {
      "owner": "resource-selector",
      "status": "pending",
      "input": "stage3_search_results.json",
      "output": "stage4_selection.json",
      "started_at": null,
      "completed_at": null,
      "summary": null,
      "error": null
    },
    "stage5": {
      "owner": "resource-downloader",
      "status": "pending",
      "input": "stage4_selection.json",
      "output": "stage5_download.json",
      "started_at": null,
      "completed_at": null,
      "summary": null,
      "error": null
    },
    "stage6": {
      "owner": "library-manager",
      "status": "pending",
      "input": "stage5_download.json",
      "output": "stage6_archive.json",
      "started_at": null,
      "completed_at": null,
      "summary": null,
      "error": null
    }
  }
}
```

### 5.1 会话状态

`status` 使用：

- `in_progress`
- `completed`
- `failed`
- `cancelled`

### 5.2 阶段状态

`stages.stageN.status` 使用：

- `pending`
- `in_progress`
- `waiting_user`
- `completed`
- `failed`
- `cancelled`

### 5.3 阶段状态对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `owner` | string | 是 | 阶段唯一写入 Skill |
| `status` | string | 是 | 阶段状态 |
| `input` | string | 是 | 输入文件名 |
| `output` | string | 是 | 输出文件名 |
| `started_at` | string/null | 是 | 第一次或本轮重跑开始时间 |
| `completed_at` | string/null | 是 | 完成时间 |
| `summary` | object/null | 是 | 阶段输出 `_summary` 的副本 |
| `error` | object/null | 是 | 失败时使用统一错误对象 |

`waiting_user` 时可以增加：

```json
{
  "clarification_round": 1,
  "question": "你希望练习题带答案吗？",
  "asked_at": "2026-06-30T10:31:00+08:00"
}
```

## 6. Stage 1：stage1_intent.json

### 6.1 输入

- 文件：`request.json`
- Schema：`request/v1`
- 前置条件：request 校验通过。

### 6.2 输出 envelope

```json
{
  "_meta": {
    "stage": 1,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-intent",
    "created_at": "2026-06-30T10:31:00+08:00",
    "input_from": "request.json",
    "schema_version": "intent-spec/v1"
  },
  "_summary": {
    "status": "ready",
    "core_topic": "小学三年级数学练习题",
    "target_age": "8-9岁",
    "clarification_required": false,
    "clarification_question": null,
    "assumptions": []
  },
  "data": {}
}
```

### 6.3 `_summary`

| 字段 | 类型 | 枚举/说明 |
|---|---|---|
| `status` | string | `ready` / `needs_clarification` |
| `core_topic` | string/null | 当前核心主题 |
| `target_age` | string/null | 当前适龄信息 |
| `clarification_required` | boolean | 是否需要 Flow 提问 |
| `clarification_question` | string/null | 单个用户问题 |
| `assumptions` | string[] | 本轮采用的可撤销假设 |

### 6.4 `data`

```json
{
  "schema_version": "intent-spec/v1",
  "status": "ready",
  "raw_request": "帮我找三年级数学练习题",
  "slots": {
    "core_topic": {
      "value": "小学三年级数学练习题",
      "status": "explicit",
      "confidence": 1.0,
      "evidence": ["三年级数学练习题"]
    },
    "learning_domain": {
      "value": "数学",
      "status": "inferred",
      "confidence": 0.95,
      "evidence": ["数学练习题"]
    },
    "target_age": {
      "value": "8-9岁",
      "status": "inferred",
      "confidence": 0.85,
      "evidence": ["三年级"]
    },
    "grade_level": {
      "value": "小学三年级",
      "status": "explicit",
      "confidence": 1.0,
      "evidence": ["三年级"]
    },
    "learning_goal": {
      "value": "练习",
      "status": "inferred",
      "confidence": 0.9,
      "evidence": ["练习题"]
    },
    "difficulty": {
      "value": null,
      "status": "unknown",
      "confidence": 0.0,
      "evidence": []
    },
    "resource_types": {
      "value": ["练习类"],
      "status": "inferred",
      "confidence": 0.9,
      "evidence": ["练习题"]
    },
    "format_preferences": {
      "value": ["练习题"],
      "status": "explicit",
      "confidence": 1.0,
      "evidence": ["练习题"]
    },
    "file_formats": {
      "value": [],
      "status": "unknown",
      "confidence": 0.0,
      "evidence": []
    },
    "source_preferences": {
      "value": [],
      "status": "unknown",
      "confidence": 0.0,
      "evidence": []
    },
    "use_scenario": {
      "value": null,
      "status": "unknown",
      "confidence": 0.0,
      "evidence": []
    },
    "version": {
      "value": null,
      "status": "unknown",
      "confidence": 0.0,
      "evidence": []
    },
    "language": {
      "value": "中文",
      "status": "defaulted",
      "confidence": 0.5,
      "evidence": []
    },
    "search_mode": {
      "value": "standard",
      "status": "defaulted",
      "confidence": 0.5,
      "evidence": []
    }
  },
  "constraints": {
    "must": [],
    "prefer": [],
    "exclude": []
  },
  "search_concepts": {
    "canonical_terms": ["小学三年级", "数学", "练习题"],
    "synonyms": ["同步练习", "课后练习"],
    "related_terms": ["应用题", "计算题"]
  },
  "ambiguities": [],
  "clarification": {
    "required": false,
    "question": null,
    "reason": null,
    "missing_information": []
  },
  "assumptions": []
}
```

每个 slot 统一包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `value` | string/null 或 string[] | 槽位值 |
| `status` | string | `explicit` / `inferred` / `defaulted` / `unknown` |
| `confidence` | number | 0—1 |
| `evidence` | string[] | 来自 request 的证据原文 |

`status=needs_clarification` 时仍写完整文件；`clarification.required=true`，且 `question` 为一个非空问题。此输出不会进入 Stage 2。

## 7. Stage 2：stage2_search_plan.json

### 7.1 输入

- 文件：`stage1_intent.json`
- Schema：`intent-spec/v1`
- 前置条件：`data.status=ready`。

### 7.2 输出

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-search",
    "created_at": "2026-06-30T10:32:00+08:00",
    "input_from": "stage1_intent.json",
    "schema_version": "search-plan/v1"
  },
  "_summary": {
    "platform_count": 2,
    "platforms": ["bilibili", "generic"],
    "query_count": 2,
    "expected_results": 30
  },
  "data": {
    "schema_version": "search-plan/v1",
    "intent_ref": "stage1_intent.json",
    "strategy": "视频讲解负责解题过程，全网搜索补充练习资料。",
    "search_tasks": [
      {
        "task_id": "task-bilibili-explainer",
        "platform": "bilibili",
        "priority": "P1",
        "reason": "补充解题过程讲解",
        "searches": [
          {
            "query": "三年级数学 应用题讲解",
            "max_results": 15,
            "params": {}
          }
        ]
      },
      {
        "task_id": "task-generic-web",
        "platform": "generic",
        "priority": "P1",
        "reason": "补充跨站点和可打印资料",
        "searches": [
          {
            "query": "三年级数学 可打印练习题",
            "max_results": 15,
            "params": {
              "engines": ["baidu", "bing"]
            }
          }
        ]
      }
    ]
  }
}
```

### 7.3 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `data.schema_version` | string | 是 | `search-plan/v1` |
| `data.intent_ref` | string | 是 | 固定指向 `stage1_intent.json` |
| `data.strategy` | string | 是 | 简明搜索分工说明 |
| `data.search_tasks` | array | 是 | 平台任务，至少一项 |
| `task_id` | string | 是 | 会话内唯一 |
| `platform` | string | 是 | 已注册且可执行的平台 ID |
| `priority` | string | 是 | `P0` / `P1` / `P2` |
| `reason` | string | 是 | 选择该平台的简短原因 |
| `searches` | array | 是 | 该平台的一次或多次搜索调用 |
| `searches[].query` | string | 是 | 直接传给平台的关键词 |
| `searches[].max_results` | integer | 是 | 单次返回上限，1—100 |
| `searches[].params` | object | 是 | 平台真实支持的参数；无参数使用 `{}` |

`_summary.expected_results` 等于所有 `searches[].max_results` 之和，是理论上限，不是实际召回数。

## 8. 公共资源对象

Stage 3 首次创建资源对象；Stage 4—6 在保留已有字段的基础上追加本阶段字段。

### 8.1 Stage 3 基础资源字段

```json
{
  "resource_id": "bilibili:BV1example",
  "platform_resource_id": "BV1example",
  "platform": "bilibili",
  "title": "三年级数学应用题讲解",
  "source_url": "https://www.bilibili.com/video/BV1example",
  "type": "视频",
  "description": null,
  "author": null,
  "duration": null,
  "publish_time": null,
  "is_free": null,
  "language": "中文",
  "thumbnail_url": null,
  "download_feasibility": "中",
  "platform_signals": {},
  "raw_metadata": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `resource_id` | string | 是 | 全流程稳定 ID |
| `platform_resource_id` | string/null | 否 | 平台内部 ID |
| `platform` | string | 是 | 平台 ID |
| `title` | string | 是 | 非空标题 |
| `source_url` | string | 是 | 原始来源地址 |
| `type` | string/null | 否 | 视频、音频、文档、练习题、网页等 |
| `description` | string/null | 否 | 简介或摘要 |
| `author` | string/null | 否 | 作者或发布者 |
| `duration` | number/null | 否 | 秒 |
| `publish_time` | string/null | 否 | ISO 8601；只有日期时可使用 `YYYY-MM-DD` |
| `is_free` | boolean/null | 否 | 免费状态未知时为 `null` |
| `language` | string/null | 否 | 内容语言 |
| `thumbnail_url` | string/null | 否 | 封面地址 |
| `download_feasibility` | string/null | 否 | `高` / `中` / `低` |
| `platform_signals` | object | 是 | 播放量、点赞、认证等平台原生信号 |
| `raw_metadata` | object | 是 | 未标准化但需要保留的平台字段 |

### 8.2 字段所有权

| 阶段 | 可以新增的资源字段 | 不得提前生成 |
|---|---|---|
| Stage 3 | 基础资源字段、`platform_signals`、`raw_metadata` | `quality_score`、下载和归档字段 |
| Stage 4 | 质量、过滤和去重判断字段 | 下载和归档字段 |
| Stage 5 | 下载、降级和下载错误字段 | 归档字段 |
| Stage 6 | 入库、资料库去重和归档错误字段 | 无 |

## 9. Stage 3：stage3_search_results.json

### 9.1 输入

- 文件：`stage2_search_plan.json`
- Schema：`search-plan/v1`

### 9.2 输出

```json
{
  "_meta": {
    "stage": 3,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-platforms",
    "created_at": "2026-06-30T10:35:00+08:00",
    "input_from": "stage2_search_plan.json",
    "schema_version": "platform-results/v1"
  },
  "_summary": {
    "raw_count": 38,
    "success_platforms": ["smartedu", "bilibili", "generic"],
    "failed_platforms": [],
    "error_count": 0,
    "invalid_count": 2
  },
  "data": {
    "schema_version": "platform-results/v1",
    "intent_ref": "stage1_intent.json",
    "intent_context": {
      "core_topic": "小学三年级数学练习题",
      "target_age": "8-9岁",
      "grade_level": "小学三年级",
      "learning_goal": "练习",
      "search_mode": "standard",
      "constraints": {
        "must": [],
        "prefer": [],
        "exclude": []
      }
    },
    "resources": [],
    "platform_stats": {
      "bilibili": {
        "status": "success",
        "task_count": 1,
        "query_count": 2,
        "returned_count": 14,
        "invalid_count": 1
      }
    },
    "errors": []
  }
}
```

### 9.3 `_summary`

| 字段 | 类型 | 说明 |
|---|---|---|
| `raw_count` | integer | `data.resources.length` |
| `success_platforms` | string[] | 至少一次搜索成功的平台 |
| `failed_platforms` | string[] | 所有搜索调用都失败的平台 |
| `error_count` | integer | `data.errors.length` |
| `invalid_count` | integer | 因缺少技术必填字段而剔除的记录数 |

### 9.4 `platform_stats`

每个平台统计对象包含：

| 字段 | 类型 | 枚举/说明 |
|---|---|---|
| `status` | string | `success` / `partial` / `failed` |
| `task_count` | integer | 平台任务数 |
| `query_count` | integer | 实际执行查询数 |
| `returned_count` | integer | 技术清洗后保留数 |
| `invalid_count` | integer | 技术无效数 |

### 9.5 搜索错误

`data.errors[]` 使用统一错误对象，并可附加：

```json
{
  "scope": "search",
  "platform": "generic",
  "task_id": "task-generic-web",
  "query": "三年级数学 可打印练习题",
  "error_code": "ANTI_CRAWL_CAPTCHA",
  "error_message": "搜索引擎返回安全验证页面",
  "can_retry": false,
  "suggested_action": "need_user_action",
  "details": {}
}
```

平台失败必须写入 error，不能只返回空资源数组。

## 10. Stage 4：stage4_selection.json

### 10.1 输入

- 文件：`stage3_search_results.json`
- Schema：`platform-results/v1`

### 10.2 Stage 4 追加的资源字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `quality_score` | number | 是 | 0—100 |
| `quality_level` | string | 是 | `S` / `A` / `B` / `C` |
| `quality_dimensions` | object | 是 | Selector 的分维度得分 |
| `assessment_notes` | string[] | 是 | 推断、风险和证据不足说明 |
| `possible_duplicate` | boolean | 是 | 未能确认合并的疑似重复标记 |

### 10.3 输出

```json
{
  "_meta": {
    "stage": 4,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-selector",
    "created_at": "2026-06-30T10:40:00+08:00",
    "input_from": "stage3_search_results.json",
    "schema_version": "selection/v1"
  },
  "_summary": {
    "raw_count": 38,
    "candidate_count": 16,
    "selected_count": 4,
    "selection_mode": "manual",
    "quality_dist": {
      "S": 2,
      "A": 6,
      "B": 7,
      "C": 1
    },
    "filter_stats": {
      "duplicates_removed": 5,
      "business_filtered": 17
    }
  },
  "data": {
    "schema_version": "selection/v1",
    "intent_ref": "stage1_intent.json",
    "selected_count": 4,
    "selection_mode": "manual",
    "resources": [],
    "candidate_snapshot": {
      "raw_count": 38,
      "qualified_count": 16,
      "filter_stats": {
        "duplicates_removed": 5,
        "business_filtered": 17
      },
      "platform_errors": []
    }
  }
}
```

### 10.4 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `selected_count` | integer | 必须等于 `resources.length` |
| `selection_mode` | string | `manual` / `all` / `by_platform` / `by_type` / `by_quality` / `cancelled` |
| `resources` | array | 只保存用户确认的资源；完整保留 Stage 3 字段并追加 Stage 4 字段 |
| `candidate_snapshot.raw_count` | integer | Stage 3 原始资源数 |
| `candidate_snapshot.qualified_count` | integer | 过滤和去重后可选资源数 |
| `candidate_snapshot.filter_stats` | object | 去重和业务过滤统计 |
| `candidate_snapshot.platform_errors` | array | 从 Stage 3 复制的平台错误摘要 |

用户取消时仍写文件：`selection_mode=cancelled`、`selected_count=0`、`resources=[]`。

## 11. Stage 5：stage5_download.json

### 11.1 输入

- 文件：`stage4_selection.json`
- Schema：`selection/v1`
- 前置条件：`selected_count > 0`。

### 11.2 Stage 5 追加的资源字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `download_status` | string | 是 | `success` / `degraded` / `failed` |
| `degraded_level` | string | 是 | `Level 0` / `Level 1` / `Level 2` / `Level 3` |
| `fetch_time` | string | 是 | ISO 8601 |
| `fetch_method` | string | 是 | `direct` / `api` / `browser` / `yt_dlp` / `scrape` / `other` |
| `file_path` | string/null | 是 | 成功或 Level 1 文件路径；否则 `null` |
| `file_size` | integer/null | 是 | 字节数 |
| `file_format` | string/null | 是 | 文件扩展名，不含点 |
| `degraded_content` | object/null | 是 | Level 2/3 保存内容 |
| `error` | object/null | 是 | 失败或降级原因 |

### 11.3 输出

```json
{
  "_meta": {
    "stage": 5,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-downloader",
    "created_at": "2026-06-30T10:50:00+08:00",
    "input_from": "stage4_selection.json",
    "schema_version": "download/v1"
  },
  "_summary": {
    "total_count": 4,
    "success_count": 3,
    "degraded_count": 1,
    "failed_count": 0
  },
  "data": {
    "schema_version": "download/v1",
    "total_count": 4,
    "success_count": 3,
    "degraded_count": 1,
    "failed_count": 0,
    "resources": []
  }
}
```

### 11.4 条件规则

- `success`：`degraded_level=Level 0`，`file_path`、`file_size`、`file_format` 非空，`error=null`。
- `degraded`：`degraded_level` 为 Level 1—3，必须提供 `error`；Level 1 提供预览文件，Level 2/3 提供 `degraded_content`。
- `failed`：文件字段为 `null`，必须提供 `error`。
- 无论成功、降级或失败，都保留 Stage 4 的全部资源字段。

## 12. Stage 6：stage6_archive.json

### 12.1 输入

- 文件：`stage5_download.json`
- Schema：`download/v1`

### 12.2 Stage 6 追加的资源字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `archive_status` | string | 是 | `archived` / `skipped` / `failed` |
| `library_path` | string/null | 是 | 成功归档后的资料库相对路径 |
| `archive_time` | string/null | 是 | ISO 8601 |
| `dedup_status` | string | 是 | `new` / `duplicate` / `skipped` |
| `archive_error` | object/null | 是 | 归档失败时的统一错误对象 |

### 12.3 输出

```json
{
  "_meta": {
    "stage": 6,
    "session_id": "20260630-1030-math-grade3",
    "skill": "library-manager",
    "created_at": "2026-06-30T11:00:00+08:00",
    "input_from": "stage5_download.json",
    "schema_version": "archive/v1"
  },
  "_summary": {
    "total_count": 4,
    "archived_count": 3,
    "skipped_count": 1,
    "failed_count": 0,
    "dedup_stats": {
      "new": 3,
      "duplicate": 1,
      "skipped": 0
    }
  },
  "data": {
    "schema_version": "archive/v1",
    "total_count": 4,
    "archived_count": 3,
    "skipped_count": 1,
    "failed_count": 0,
    "resources": []
  }
}
```

### 12.4 条件规则

- `archive_status=archived`：`library_path`、`archive_time` 非空，`archive_error=null`。
- `archive_status=skipped`：用于确认重复或明确不入库；允许 `library_path` 指向已有资源。
- `archive_status=failed`：`library_path=null`，必须提供 `archive_error`。
- Stage 5 的失败资源仍进入 Stage 6，由 Library Manager 决定保存来源链接、记录跳过或标记失败。

## 13. 统一错误对象

```json
{
  "error_code": "NETWORK_TIMEOUT",
  "error_message": "请求超时",
  "can_retry": true,
  "suggested_action": "retry_with_delay",
  "details": {
    "retry_count": 2
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `error_code` | string | 是 | 统一错误码 |
| `error_message` | string | 是 | 人类可读说明，不包含凭证 |
| `can_retry` | boolean | 是 | 当前错误是否值得重试 |
| `suggested_action` | string/null | 是 | `retry` / `retry_with_delay` / `change_strategy` / `need_user_action` / `skip` / `replan` / `degrade` |
| `details` | object | 是 | 可诊断信息；无内容使用 `{}` |

错误码前缀：

- `VALIDATION_`
- `NETWORK_`
- `ANTI_CRAWL_`
- `AUTH_`
- `CONTENT_`
- `PARSE_`
- `DOWNLOAD_`
- `ARCHIVE_`
- `SYSTEM_`

错误对象不得包含 Cookie、token、密码、完整请求头或其他认证秘密。

## 14. 字段传递与计数不变量

### 14.1 资源字段传递

1. Stage 3 创建基础资源对象。
2. Stage 4 可以移除未入选资源，但选中资源不得裁剪 Stage 3 字段。
3. Stage 5 对 Stage 4 的每条资源产生且只产生一条下载结果。
4. Stage 6 对 Stage 5 的每条资源产生且只产生一条归档结果。
5. 下游新增字段时不得覆盖同名上游字段；确需改变契约语义时升级 schema_version。

### 14.2 计数不变量

```text
stage3._summary.raw_count
  = len(stage3.data.resources)

stage4._summary.selected_count
  = stage4.data.selected_count
  = len(stage4.data.resources)

stage5.data.total_count
  = len(stage5.data.resources)
  = success_count + degraded_count + failed_count

stage6.data.total_count
  = len(stage6.data.resources)
  = archived_count + skipped_count + failed_count
```

### 14.3 引用不变量

- 所有阶段 `session_id` 相同。
- `_meta.input_from` 必须等于直接上游文件名。
- `data.intent_ref` 始终指向同会话的 `stage1_intent.json`。
- `resource_id` 从 Stage 3 到 Stage 6 不得变化。
- 本地下载成功后，Stage 6 归档可以移动文件；此时保留原 `file_path`，并用 `library_path` 表示最终位置。

## 15. 失败、等待与重跑

### 15.1 验证失败

- 不生成伪造的下游文件。
- 在 manifest 将当前阶段标记为 `failed`。
- `manifest.stages.stageN.error` 写统一错误对象。
- 下游阶段保持 `pending`。

### 15.2 Stage 1 等待用户

- `stage1_intent.json` 正常写入，状态为 `needs_clarification`。
- manifest Stage 1 标记 `waiting_user`。
- 用户回答追加到 `request.json` 后，Stage 1 回到 `in_progress` 并覆盖自己的输出。

### 15.3 部分平台失败

- Stage 3 仍可完成。
- 失败平台写入 `failed_platforms` 和 `data.errors`。
- 有有效资源时继续 Stage 4；所有平台均失败时由 Flow 决定重跑 Stage 2 或等待用户。

### 15.4 用户取消选择

- Stage 4 写 `selection_mode=cancelled` 的合法空选择文件。
- Stage 4 和会话标记 `cancelled`。
- 不创建 Stage 5、6 新输出。

### 15.5 重跑失效范围

| 重跑阶段 | 必须失效的下游阶段 |
|---|---|
| Stage 1 | Stage 2—6 |
| Stage 2 | Stage 3—6 |
| Stage 3 | Stage 4—6 |
| Stage 4 | Stage 5—6 |
| Stage 5 | Stage 6 |
| Stage 6 | 无 |

失效阶段在 manifest 重置为 `pending`，清空本轮 `started_at`、`completed_at`、`summary` 和 `error`。旧文件可以保留用于审计，但 Flow 不得继续把它当作有效输入。

## 16. 版本兼容规则

### 16.1 版本格式

使用 `{contract-name}/v{major}`，例如：

- `intent-spec/v1`
- `search-plan/v1`
- `platform-results/v1`
- `selection/v1`
- `download/v1`
- `archive/v1`

### 16.2 需要升级 major 的变化

- 删除必填字段。
- 修改字段类型或语义。
- 修改枚举值导致旧消费者不能读取。
- 改变资源字段的所有权阶段。

### 16.3 可以保持版本的变化

- 增加可选字段。
- 扩展 `details`、`platform_signals` 或 `raw_metadata`。
- 增加消费者可以忽略的新统计字段。

### 16.4 写入与读取

- 写入者只输出自己声明支持的一个版本。
- 读取者遇到不支持的 major 版本时必须停止，不得猜测字段。
- 版本升级时同时更新本文、对应 JSON Schema、生产者 Skill 和消费者 Skill。
