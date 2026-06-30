# 学习资源六阶段数据契约

> 契约版本：`pipeline-data-contract/v1`

本文件只定义阶段之间必须交换的数据。语义判断、平台选择、评分方法、下载策略和资料库分类分别由对应 Skill 负责。

## 1. 设计原则

1. 每个事实只保存一次。下游通过固定文件和 `resource_id` 读取上游数据，不复制整个资源对象。
2. 未知或不适用的可选字段直接省略，不输出大量 `null`、空数组或空对象。
3. 只保留有明确消费者的字段。Flow 需要的少量状态和计数放在 `_summary`；展示统计和模型思考过程不写入契约。
4. Intent 保留语义证据；Search 只输出可执行参数；Platform 只输出搜索事实；Selector 才输出质量判断。
5. 阶段文件的文件名已经表达阶段、写入者和直接上游，因此不再重复保存 `stage`、`skill`、`input_from`。

## 2. 文件与责任

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

| 文件 | Schema | 唯一写入者 | 读取者 |
|---|---|---|---|
| `request.json` | `request/v1` | learning-resource-flow | resource-intent |
| `manifest.json` | `session-manifest/v1` | learning-resource-flow | 全部 Skill 只读 |
| `stage1_intent.json` | `intent-spec/v1` | resource-intent | resource-search、resource-selector、library-manager |
| `stage2_search_plan.json` | `search-plan/v1` | resource-search | resource-platforms |
| `stage3_search_results.json` | `platform-results/v1` | resource-platforms | resource-selector、resource-downloader、library-manager |
| `stage4_selection.json` | `selection/v1` | resource-selector | resource-downloader、library-manager |
| `stage5_download.json` | `download/v1` | resource-downloader | library-manager |
| `stage6_archive.json` | `archive/v1` | library-manager | learning-resource-flow |

## 3. 公共 envelope

`request.json` 和 Stage 1—6 都使用 `_meta` 与 `data`。Flow 需要快速判断状态或结果数量的阶段额外使用 `_summary`：

```json
{
  "_meta": {
    "schema_version": "intent-spec/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:31:00+08:00"
  },
  "_summary": {
    "status": "ready"
  },
  "data": {}
}
```

`_meta` 只包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | 当前文件的 Schema 版本 |
| `session_id` | string | 必须与会话目录和其他阶段一致 |
| `created_at` | string | 本次写入时间，ISO 8601 且包含时区 |

不要在 `data` 内再次写 `schema_version`。`_summary` 只允许保存 Flow 会直接读取的状态或计数，不保存资源、搜索词、评分分布和过滤详情。Stage 2 没有 Flow 分支信息，因此不输出 `_summary`。

## 4. request.json

Flow 保存用户最初请求和后续澄清原话：

```json
{
  "_meta": {
    "schema_version": "request/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:30:00+08:00"
  },
  "data": {
    "raw_request": "四年级数学课程",
    "conversation_evidence": []
  }
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `raw_request` | 是 | 用户最初请求原文，后续不得改写 |
| `conversation_evidence` | 是 | 只追加与当前需求有关的澄清问题和用户回答 |

`conversation_evidence[]` 只包含 `role`（`user` / `assistant`）和非空 `content`。Flow 不再创建 `user_confirmed_facts`，避免在 Intent 之前提前概括用户语义。

## 5. manifest.json

Manifest 只服务调度和恢复，不复制业务数据、阶段文件名、写入者或阶段统计。

```json
{
  "schema_version": "session-manifest/v1",
  "session_id": "20260630-1030-math-grade4",
  "updated_at": "2026-06-30T10:35:00+08:00",
  "status": "in_progress",
  "current_stage": 3,
  "stages": {
    "stage1": {"status": "completed"},
    "stage2": {"status": "completed"},
    "stage3": {"status": "in_progress"},
    "stage4": {"status": "pending"},
    "stage5": {"status": "pending"},
    "stage6": {"status": "pending"}
  }
}
```

会话 `status`：`in_progress` / `completed` / `failed` / `cancelled`。

阶段 `status`：`pending` / `in_progress` / `waiting_user` / `completed` / `failed` / `cancelled`。

阶段失败时增加 `error`；Stage 1 等待澄清时不复制问题，问题直接读取 `stage1_intent.json:data.clarification`。

## 6. Stage 1：stage1_intent.json

### 6.1 输出

```json
{
  "_meta": {
    "schema_version": "intent-spec/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:31:00+08:00"
  },
  "_summary": {
    "status": "ready"
  },
  "data": {
    "status": "ready",
    "raw_request": "四年级数学课程",
    "slots": {
      "core_topic": {
        "value": "小学四年级数学课程",
        "status": "explicit",
        "evidence": ["四年级数学课程"]
      },
      "grade_level": {
        "value": "小学四年级",
        "status": "explicit",
        "evidence": ["四年级"]
      },
      "learning_goal": {
        "value": "系统学习",
        "status": "inferred",
        "evidence": ["课程"]
      },
      "format_preferences": {
        "value": ["课程"],
        "status": "explicit",
        "evidence": ["课程"]
      }
    },
    "constraints": {},
    "search_concepts": {
      "canonical_terms": ["小学四年级", "数学", "课程"],
      "synonyms": ["同步课程", "数学课"],
      "related_terms": ["知识点讲解", "单元课程"]
    }
  }
}
```

`_summary.status` 与 `data.status` 必须一致。需要澄清时 `_summary` 额外包含唯一的 `question`，使 Flow 无需读取完整 Intent 数据：

### 6.2 槽位

允许的槽位：

- `core_topic`
- `learning_domain`
- `target_age`
- `grade_level`
- `learning_goal`
- `difficulty`
- `resource_types`
- `format_preferences`
- `file_formats`
- `use_scenario`
- `version`
- `language`
- `search_mode`

只输出已有值或本轮确实采用了默认值的槽位。未知槽位直接省略，不创建 `status=unknown` 的空对象。

每个已输出槽位只包含：

| 字段 | 说明 |
|---|---|
| `value` | string 或 string[] |
| `status` | `explicit` / `inferred` / `defaulted` |
| `evidence` | 支持该值的用户原话；默认值可以使用空数组 |

不输出主观 `confidence`。准确性由 `status + evidence` 约束：`explicit` 必须有直接证据，`inferred` 必须有支持推断的原话，`defaulted` 必须可被用户后续覆盖。

来源偏好不再单设槽位，按强度写入 `constraints.must` 或 `constraints.prefer`。`constraints` 与 `search_concepts` 只保留非空子项。

### 6.3 澄清

需要澄清时：

```json
{
  "_summary": {
    "status": "needs_clarification",
    "question": "你想入门的是哪个主题？"
  },
  "data": {
    "status": "needs_clarification",
    "raw_request": "找一套入门资料",
    "slots": {},
    "constraints": {},
    "search_concepts": {},
    "clarification": {
      "question": "你想入门的是哪个主题？",
      "reason": "当前没有可用于搜索的核心主题"
    }
  }
}
```

`clarification` 只在 `needs_clarification` 时存在，只包含一个问题和原因。`ready` 时省略。无需另写 `clarification.required`、`missing_information` 或 `ambiguities`，它们都能由状态、问题和已有槽位表达。

采用了可撤销假设时增加 `assumptions: string[]`；没有假设时省略。

## 7. Stage 2：stage2_search_plan.json

Search 读取 Stage 1。只有 `data.status=ready` 时才能写入计划。

```json
{
  "_meta": {
    "schema_version": "search-plan/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:32:00+08:00"
  },
  "data": {
    "search_tasks": [
      {
        "platform": "smartedu",
        "priority": "P0",
        "searches": [
          {"query": "小学四年级 数学 同步课程", "max_results": 15}
        ]
      },
      {
        "platform": "bilibili",
        "priority": "P1",
        "searches": [
          {"query": "四年级数学 知识点讲解", "max_results": 15}
        ]
      },
      {
        "platform": "generic",
        "priority": "P1",
        "searches": [
          {
            "query": "四年级数学 公开课程",
            "max_results": 20,
            "params": {"engines": ["baidu", "bing"]}
          }
        ]
      }
    ]
  }
}
```

每个平台只创建一个任务：

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `platform` | 是 | 已注册且可执行的平台 ID |
| `priority` | 是 | `P0` / `P1` / `P2` |
| `searches` | 是 | 一次或多次真实搜索调用 |
| `searches[].query` | 是 | 直接交给平台的关键词 |
| `searches[].max_results` | 是 | 1—100，控制本次搜索深度 |
| `searches[].params` | 否 | 仅在平台真实接口需要额外参数时输出 |

`task_id`、顶层 `strategy`、逐任务 `reason`、`intent_ref` 和所有汇总计数均无执行消费者，删除。平台分工和关键词差异应体现在任务与查询本身，不保存模型思考过程。

## 8. Stage 3：stage3_search_results.json

```json
{
  "_meta": {
    "schema_version": "platform-results/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:35:00+08:00"
  },
  "_summary": {
    "resource_count": 1,
    "failed_platforms": []
  },
  "data": {
    "resources": [
      {
        "resource_id": "bilibili:BV1example",
        "platform": "bilibili",
        "title": "四年级数学知识点课程",
        "source_url": "https://www.bilibili.com/video/BV1example",
        "type": "视频",
        "description": "四年级数学知识点系统讲解",
        "author": "示例作者",
        "duration": 900,
        "is_free": true,
        "language": "中文",
        "download_feasibility": "中",
        "platform_signals": {"views": 12000}
      }
    ],
    "errors": []
  }
}
```

每条资源必填：`resource_id`、`platform`、`title`、`source_url`。

以下字段已知时才输出：`type`、`description`、`author`、`duration`、`publish_time`、`is_free`、`language`、`thumbnail_url`、`download_feasibility`、`platform_signals`、`raw_metadata`。

- `platform_signals` 只保存 Selector 可能使用的平台原生信号。
- `raw_metadata` 只保存后续平台下载确实需要、且没有标准字段承载的数据；不得倾倒完整平台响应或重复标准字段。
- `platform_resource_id` 已包含在稳定 `resource_id` 中，不再单独输出。
- 不复制 Stage 1 的 `intent_context`。Selector 直接读取同会话的 `stage1_intent.json`。
- 不输出 `platform_stats`、成功平台、无效数量或其他可计算统计。
- 有平台搜索失败时写入 `errors`；无错误时保留空数组，避免把“没有运行”和“运行成功”混淆。

`_summary.resource_count` 必须等于 `resources.length`。`failed_platforms` 只列出任务全部失败的平台，供 Flow 快速决定继续、重试或调整计划。

## 9. Stage 4：stage4_selection.json

Selector 同时读取 Stage 1 和 Stage 3。展示候选并得到用户选择后，只保存被选资源的引用和必要质量结论：

```json
{
  "_meta": {
    "schema_version": "selection/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:40:00+08:00"
  },
  "_summary": {
    "status": "selected",
    "selected_count": 1
  },
  "data": {
    "status": "selected",
    "selected": [
      {
        "resource_id": "bilibili:BV1example",
        "quality_score": 82,
        "notes": ["作者资质未确认"]
      }
    ]
  }
}
```

| 字段 | 说明 |
|---|---|
| `status` | `selected` / `cancelled` |
| `selected[].resource_id` | 必须能在 Stage 3 找到且不重复 |
| `selected[].quality_score` | 0—100，Selector 最终评分 |
| `selected[].notes` | 可选；只记录会影响使用判断的风险或证据不足 |

`quality_level` 可由分数区间计算，删除；分维度得分只用于 Selector 当次推理和展示，删除；疑似重复直接写进 `notes`，不单设布尔字段；候选快照、筛选统计和平台错误继续保留在 Stage 3 或当次用户展示中，不复制进输出。

用户取消时写 `status=cancelled`、`selected=[]`，不创建 Stage 5。

`_summary.status` 与 `data.status` 一致，`selected_count` 等于 `selected.length`。

## 10. Stage 5：stage5_download.json

Downloader 读取 Stage 3 获取来源信息，读取 Stage 4 获取选择和质量结论。每个选择产生一个同 ID 结果：

```json
{
  "_meta": {
    "schema_version": "download/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T10:50:00+08:00"
  },
  "_summary": {
    "success_count": 1,
    "degraded_count": 0,
    "failed_count": 0
  },
  "data": {
    "results": [
      {
        "resource_id": "bilibili:BV1example",
        "download_status": "success",
        "files": ["/absolute/session/downloads/example.mp4"]
      }
    ]
  }
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `resource_id` | 是 | 对应 Stage 4 的选择 |
| `download_status` | 是 | `success` / `degraded` / `failed` |
| `files` | 是 | 本次产生的绝对文件路径；失败时为 `[]` |
| `degraded_level` | 条件 | 仅 degraded，使用 `Level 1` / `Level 2` / `Level 3` |
| `error` | 条件 | degraded 或 failed 时必填 |

Level 2/3 的正文、摘要或链接记录也先保存成文件并写入 `files`，不把大段内容嵌入 JSON。`Level 0` 等同 success，不再重复写。文件大小、格式可从文件读取；抓取方式和逐资源时间没有下游消费者，因此删除。

Stage 5 的三个 summary 计数由 `results[].download_status` 计算，其和必须等于 `results.length`。

## 11. Stage 6：stage6_archive.json

Library Manager 读取 Stage 1、3、4、5，按 `resource_id` 组合归档所需的语义、来源、质量和下载结果：

```json
{
  "_meta": {
    "schema_version": "archive/v1",
    "session_id": "20260630-1030-math-grade4",
    "created_at": "2026-06-30T11:00:00+08:00"
  },
  "_summary": {
    "archived_count": 1,
    "skipped_count": 0,
    "failed_count": 0
  },
  "data": {
    "results": [
      {
        "resource_id": "bilibili:BV1example",
        "archive_status": "archived",
        "library_paths": ["数学/小学四年级/example.mp4"]
      }
    ]
  }
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `resource_id` | 是 | 对应 Stage 5 结果 |
| `archive_status` | 是 | `archived` / `skipped` / `failed` |
| `library_paths` | 是 | 资料库根目录下的相对路径；失败时为 `[]` |
| `duplicate_of` | 条件 | 因重复而跳过时，指向已有资源 ID |
| `archive_error` | 条件 | 归档失败时必填 |

归档时间使用文件级 `_meta.created_at`。`dedup_status` 与 `archive_status` 重叠，删除；重复关系只在发生时使用 `duplicate_of` 表达。Stage 6 不复制任何上游资源字段。

Stage 6 的三个 summary 计数由 `results[].archive_status` 计算，其和必须等于 `results.length`。

## 12. 统一错误对象

```json
{
  "error_code": "NETWORK_TIMEOUT",
  "message": "请求超时",
  "retryable": true,
  "details": {"retry_count": 2}
}
```

| 字段 | 必填 | 说明 |
|---|:---:|---|
| `error_code` | 是 | 统一错误码 |
| `message` | 是 | 不含认证秘密的人类可读说明 |
| `retryable` | 是 | 当前上下文是否值得重试 |
| `details` | 否 | 只有确实有诊断价值时才输出 |

搜索错误可以增加 `platform` 和 `query`。`suggested_action` 由处理错误的 Skill 根据错误码和当前阶段决定，不由生产者提前指定。

## 13. 引用与数量不变量

1. 所有文件的 `session_id` 相同。
2. Stage 3 的 `resource_id` 会话内唯一。
3. Stage 4 每个 `selected[].resource_id` 必须在 Stage 3 存在。
4. Stage 5 每个 Stage 4 选择恰好对应一个 `results[]`，且不得出现未选择 ID。
5. Stage 6 每个 Stage 5 结果恰好对应一个 `results[]`。
6. 下游需要上游字段时按 `resource_id` 回读固定阶段文件，不复制字段。
7. 所有 `_summary` 字段必须能由同一文件的 `data` 重新计算或核对。

## 14. 失败、等待与重跑

- 验证失败：不生成伪造下游文件，在 manifest 将当前阶段标记 `failed` 并写 `error`。
- Stage 1 等待：正常写 `stage1_intent.json`，manifest 标记 `waiting_user`；Flow 读取 `data.clarification.question` 提问。
- 部分平台失败：Stage 3 在 `data.errors` 保留错误；只要有有效资源即可继续 Stage 4。
- 用户取消：Stage 4 写合法取消结果，会话标记 `cancelled`，不创建 Stage 5、6。
- 重跑上游：其后所有阶段状态重置为 `pending`；旧输出不能继续作为有效输入。

## 15. 版本规则

版本格式为 `{contract-name}/v{major}`。删除字段、改变字段类型或语义时升级 major；增加可忽略的可选字段可以保持 major。当前契约仍处于分支内设计阶段，本次精简直接收敛到 v1，不保留尚未发布的旧结构。
