# 六阶段数据流转指南

## 1. 总览

```text
用户需求
  │
  ▼
request.json                  flow：固化原始请求与对话证据
  │
  ▼
stage1_intent.json            resource-intent：理解需求
  │
  ▼
stage2_search_plan.json       resource-search：制定平台搜索计划
  │
  ▼
stage3_search_results.json    resource-platforms：执行搜索并归一化原始结果
  │
  ▼
stage4_selection.json         resource-selector：去重、过滤、评分、展示、选择
  │
  ▼
stage5_download.json          resource-downloader：下载、重试、降级
  │
  ▼
stage6_archive.json           library-manager：归档、索引、库内去重
```

`learning-resource-flow` 负责创建会话、顺序调用、状态更新和异常恢复，不承担各阶段业务处理。

## 2. 会话目录

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

所有阶段使用绝对 `session_dir`，只通过文件传递完整数据。Flow 先把原始请求和相关对话证据写入 `request.json`；对话上下文只保留各阶段 `_summary`。

## 3. 统一文件包装

每个阶段文件都使用三层包装：

```json
{
  "_meta": {
    "stage": 1,
    "session_id": "20260630-1030-math-grade3",
    "skill": "resource-intent",
    "created_at": "2026-06-30T10:30:00+08:00",
    "input_from": "request.json",
    "schema_version": "intent-spec/v1"
  },
  "_summary": {},
  "data": {}
}
```

- `_meta`：来源、阶段和时间。
- `_summary`：flow 用于调度的精简信息。
- `data`：下游 Skill 使用的完整数据。

下游处理资源时遵循“只增不删”：除明确执行筛选的 stage 4 外，已有资源字段原样透传，新阶段只追加本阶段字段。Stage 4 可以移除未入选资源，但所选资源的字段不得裁剪。

## 4. Stage 1：需求理解

**Skill**：`resource-intent`

**输入**：`request.json`（`request/v1`），包含 `raw_request`、`conversation_evidence` 和 `user_confirmed_facts`。

该文件由 Flow 创建，不由用户或 Intent 创建。Flow 必须原样保存当前用户需求，写入后运行：

```bash
python3 learning-resource-flow/scripts/validate_request.py {session_dir}/request.json
```

校验通过后才能调用 Intent。

**输出**：`stage1_intent.json`

`data` 使用 `intent-spec/v1`，主要字段为：

- `slots`：每个槽位包含 value、explicit/inferred/defaulted/unknown 状态、置信度和证据；资料语义分别使用 `resource_types`（资料大类）、`format_preferences`（具体内容形态）和 `file_formats`（实际文件格式）。
- `constraints`：must、prefer、exclude。
- `search_concepts`：规范概念和同义词，不是可执行查询。
- `ambiguities`、`clarification`、`assumptions`。

本阶段不生成查询、不决定平台、不执行搜索。Intent 通过 `_summary.clarification_question` 把单个问题交还 Flow；Flow 将问题和用户回答依次追加到 `conversation_evidence`，等待期间把 stage 1 标记为 `waiting_user`，更新并校验 request.json 后重跑 Intent。

用户未指定资料类型或文件格式时，对应槽位保持 unknown；Intent 不默认视频、图文或文档，具体多形态覆盖由 Stage 2 决定。

## 5. Stage 2：搜索计划

**Skill**：`resource-search`

**输入**：`stage1_intent.json`

**输出**：`stage2_search_plan.json`

`data` 主要字段：

```json
{
  "schema_version": "search-plan/v1",
  "intent_ref": "stage1_intent.json",
  "strategy": "官方同步练习为主，视频讲解与全网长尾补充",
  "search_tasks": [
    {
      "task_id": "task-smartedu-primary",
      "platform": "smartedu",
      "priority": "P0",
      "reason": "用户需要三年级同步练习并偏好官方来源",
      "searches": [
        {
          "query": "小学三年级 数学 同步练习",
          "max_results": 20,
          "params": {}
        }
      ]
    }
  ]
}
```

本阶段只决定平台、关键词、单次返回数量和平台真实支持的参数，不执行平台请求，也不对结果评分。

## 6. Stage 3：平台搜索执行

**Skill**：`resource-platforms`，search 模式。

**输入**：`stage2_search_plan.json`

**输出**：`stage3_search_results.json`

允许执行：

- 平台请求和认证。
- 限速、重试和断路器。
- 响应解析及统一字段归一化。
- 剔除缺少资源 ID、标题或来源地址的技术无效记录。
- 同平台、同 ID 的完全重复响应合并。

禁止执行：

- 跨平台相似内容去重。
- 相关性、安全、语言、付费和质量过滤。
- 全局质量评分和最终排序。

输出 `data.resources` 是归一化原始结果，同时原样透传 `intent_context`，并保留 `platform_stats` 和 `errors`。平台热度或自评写入 `platform_signals`，不是最终质量等级。

## 7. Stage 4：筛选与选择

**Skill**：`resource-selector`

**输入**：`stage3_search_results.json`

**输出**：`stage4_selection.json`

按以下顺序处理：

1. 跨平台去重和相似资源合并。
2. 相关性、儿童安全、可用性、语言和费用过滤。
3. 使用 selector 自有质量规范统一评分和 S/A/B/C 定级。
4. 按质量、适龄性和下载可行性排序。
5. 分批展示候选并等待用户确认。
6. 将确认资源写入 `data.resources`。

`_summary` 至少包含：

```json
{
  "raw_count": 72,
  "candidate_count": 22,
  "selected_count": 5,
  "selection_mode": "manual",
  "quality_dist": {"S": 3, "A": 8, "B": 9, "C": 2},
  "filter_stats": {
    "duplicates_removed": 12,
    "business_filtered": 38
  }
}
```

这是搜索链路中唯一负责业务筛选的阶段。

## 8. Stage 5：下载

**Skill**：`resource-downloader`

**输入**：`stage4_selection.json`

**输出**：`stage5_download.json`

Downloader 根据资源的 `platform` 调用 `resource-platforms` 下载模式；没有专属下载能力时使用通用方式。负责：

- 路由、进度、重试和错误汇总。
- Level 0-3 降级。
- 将文件写入 `{session_dir}/downloads/`。
- 保留失败资源及其错误，不从输出中删除。

每条资源追加 `download_status`、`degraded_level`、`file_path`、`file_size`、`fetch_time` 和错误字段。

## 9. Stage 6：归档

**Skill**：`library-manager`

**输入**：`stage5_download.json`

**输出**：`stage6_archive.json`

负责资料库内去重、文件移动、分类、索引和元数据更新。这里的去重用于避免资料库重复入库，与 stage 4 的“候选列表去重”目的不同，二者都需要保留。

每条资源追加 `library_path`、`archive_time` 和 `dedup_status`。

## 10. 调用责任

| 调用方 | 被调用方 | 场景 |
|---|---|---|
| learning-resource-flow | resource-intent | stage 1 |
| learning-resource-flow | resource-search | stage 2 |
| learning-resource-flow | resource-platforms search | stage 3 |
| learning-resource-flow | resource-selector | stage 4 |
| learning-resource-flow | resource-downloader | stage 5 |
| resource-downloader | resource-platforms download | stage 5 内部 |
| learning-resource-flow | library-manager | stage 6 |

`resource-search` 不直接调用平台脚本。这样 flow 能准确持久化 stage 2 与 stage 3 的独立状态，并在平台搜索失败时单独恢复。

## 11. 重跑规则

- 重跑 stage 1：stage 2-6 全部失效。
- 重跑 stage 2：stage 3-6 全部失效。
- 重跑 stage 3：stage 4-6 全部失效。
- 仅查看更多或改变筛选条件：复用 stage 3，重跑 stage 4。
- 重试下载：复用 stage 4，重跑 stage 5，并使 stage 6 失效。
- 重试归档：复用 stage 5，仅重跑 stage 6。

失效阶段在 manifest 中重置为 `pending`，旧文件不得作为新结果继续流转。
