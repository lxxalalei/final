---
name: learning-resource-flow
description: 儿童学习资源获取与归档的总调度入口。用于接收自然语言需求，创建并校验 request.json，处理 Intent 澄清循环，并按六阶段顺序调度需求理解、搜索计划、平台搜索、筛选选择、下载和归档。
---

# learning-resource-flow

## 职责

作为套件唯一总入口，维护会话状态并调度六个阶段。不要在本 Skill 中实现平台搜索、质量筛选、下载或归档逻辑。

```text
用户需求
  -> stage 1 resource-intent
  -> stage 2 resource-search
  -> stage 3 resource-platforms（搜索模式）
  -> stage 4 resource-selector
  -> stage 5 resource-downloader
  -> stage 6 library-manager
```

下载阶段由 `resource-downloader` 调用 `resource-platforms` 的下载模式；这属于 stage 5 的内部执行，不新增流水线阶段。

## 会话目录

所有请求、manifest 和阶段文件的结构以 `../docs/pipeline-data-contract.md` 为统一契约；本 Skill 只负责按该契约创建、调度和更新状态。

为每个新需求创建：

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

`session_id` 使用 `{YYYYMMDD}-{HHmm}-{topic-slug}`。上下文中只保留 `session_id`、当前阶段和各阶段 `_summary`；完整数据通过文件传递。

## 初始化 Stage 1 输入

执行 Flow 的模型必须先创建 `request.json`，再调用 Intent。不得把聊天消息直接作为未持久化参数传给 Intent。

按以下步骤初始化：

1. 原样复制当前用户需求到 `data.raw_request`，不得总结、纠错或补充模型理解。
2. 只把与当前需求直接有关的历史话语写入 `conversation_evidence`；每条必须包含 `role` 和原文 `content`。
3. 只把用户已经明确确认的事实写入 `user_confirmed_facts`；不确定时留空，交给 Intent 判断。
4. 创建 `{session_dir}` 和初始 `manifest.json`，将 stage 1 设为 `pending`，其余阶段也设为 `pending`。
5. 创建 `{session_dir}/request.json`：

```json
{
  "_meta": {
    "session_id": "20260630-1030-math-grade3",
    "created_at": "ISO 8601",
    "skill": "learning-resource-flow"
  },
  "data": {
    "schema_version": "request/v1",
    "raw_request": "帮我找三年级数学练习题",
    "conversation_evidence": [],
    "user_confirmed_facts": []
  }
}
```

6. 运行输入校验：

```bash
python3 learning-resource-flow/scripts/validate_request.py {session_dir}/request.json
```

7. 只有校验退出码为 0 时，才把 stage 1 设为 `in_progress` 并调用 `resource-intent`。校验失败时修复 `request.json` 一次；仍失败则在 manifest 中将 stage 1 标记为 `failed`，不得继续。

Stage 1 只能读取该快照，不依赖未持久化的聊天上下文。Flow 后续更新请求时保留 `raw_request` 原文，只追加对话证据和明确确认事实。

## manifest

创建会话时写入：

```json
{
  "schema_version": "session-manifest/v1",
  "session_id": "20260630-1030-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "status": "in_progress",
  "current_stage": 1,
  "stages": {
    "stage1": {"owner": "resource-intent", "status": "pending", "input": "request.json", "output": "stage1_intent.json", "started_at": null, "completed_at": null, "summary": null, "error": null},
    "stage2": {"owner": "resource-search", "status": "pending", "input": "stage1_intent.json", "output": "stage2_search_plan.json", "started_at": null, "completed_at": null, "summary": null, "error": null},
    "stage3": {"owner": "resource-platforms", "status": "pending", "input": "stage2_search_plan.json", "output": "stage3_search_results.json", "started_at": null, "completed_at": null, "summary": null, "error": null},
    "stage4": {"owner": "resource-selector", "status": "pending", "input": "stage3_search_results.json", "output": "stage4_selection.json", "started_at": null, "completed_at": null, "summary": null, "error": null},
    "stage5": {"owner": "resource-downloader", "status": "pending", "input": "stage4_selection.json", "output": "stage5_download.json", "started_at": null, "completed_at": null, "summary": null, "error": null},
    "stage6": {"owner": "library-manager", "status": "pending", "input": "stage5_download.json", "output": "stage6_archive.json", "started_at": null, "completed_at": null, "summary": null, "error": null}
  }
}
```

阶段状态只使用 `pending`、`in_progress`、`waiting_user`、`completed`、`failed`、`cancelled`。`waiting_user` 表示阶段已产生明确问题，正在等待用户回答。调用前标记 `in_progress`；成功后写入输出文件名和 `_summary`；失败时记录错误码、原因及可重试性。

## 六阶段调度

### Stage 1：理解需求

1. 确认 `{session_dir}/request.json` 已通过输入校验；否则停止。
2. 将 manifest 的 `current_stage` 设为 1，`stages.stage1.status` 设为 `in_progress`。
3. 调用 `resource-intent`，只传递绝对 `{session_dir}`；Intent 固定读取 `request.json`，输出 `stage1_intent.json`（`intent-spec/v1`）。
4. 确认输出文件存在，并运行 `resource-intent/scripts/validate_output.py`。输出缺失或校验失败时将 stage 1 标记为 `failed`，不得继续。
5. 读取 `_summary.status`、`core_topic`、`target_age`、`clarification_required`、`clarification_question` 和 `assumptions`。
6. `_summary.status=ready` 时，将 stage 1 标记为 `completed`，保存 `_summary`，再进入 stage 2。
7. `_summary.status=needs_clarification` 时，进入下面的澄清交接；不得调用 Search。

### Stage 1：澄清交接

1. 确认 `clarification_question` 是非空字符串，且当前澄清轮数小于 2；否则将 stage 1 标记为 `failed`，错误码使用 `INVALID_CLARIFICATION` 或 `CLARIFICATION_EXHAUSTED`。
2. 将该问题原文以 `{"role":"assistant","content":"..."}` 追加到 `request.json:data.conversation_evidence`，不得由 Flow 改写、扩展或追加第二个问题。
3. 重新校验 `request.json`，将 `stages.stage1.status` 设为 `waiting_user`，记录 `clarification_round`、`question` 和 `asked_at`，然后只向用户展示该问题并结束当前轮次。
4. 用户回答后，将回答原文以 `{"role":"user","content":"..."}` 追加到 `conversation_evidence`。只有回答直接确认了事实时才同步追加到 `user_confirmed_facts`；拿不准时不要概括。
5. 保留最初的 `raw_request`，重新校验 `request.json`，把 stage 1 设回 `in_progress`，再次调用 Intent。
6. 最多执行两轮澄清。第二轮后仍为 `needs_clarification` 时停止会话，不得进入 stage 2。

### Stage 2：生成搜索计划

- 调用 `resource-search`。
- 输入 `stage1_intent.json`，输出 `stage2_search_plan.json`。
- 读取 `platform_count`、`platforms`、`query_count` 和 `expected_results`。
- 本阶段只决定去哪里搜、搜什么、搜多少，不执行搜索。

### Stage 3：执行平台搜索

- 直接调用 `resource-platforms` 的搜索模式。
- 输入 `stage2_search_plan.json`，输出 `stage3_search_results.json`。
- 读取 `raw_count`、`success_platforms`、`failed_platforms` 和 `error_count`。
- 本阶段只执行平台任务、归一化字段和记录错误，不做跨平台筛选或最终质量评分。

### Stage 4：筛选并让用户选择

- 调用 `resource-selector`。
- 输入 `stage3_search_results.json`，输出 `stage4_selection.json`。
- Selector 负责跨平台去重、业务过滤、质量评分、排序、展示和用户选择。
- 读取 `candidate_count`、`selected_count`、`quality_dist`、`selection_mode` 和 `filter_stats`。
- 没有合格候选时，提供放宽条件、换关键词或扩大平台范围的选项；不要进入下载阶段。
- 用户没有选择时，将会话标记为 `cancelled`。

### Stage 5：下载

- 调用 `resource-downloader`。
- 输入 `stage4_selection.json`，输出 `stage5_download.json`。
- 读取 `success_count`、`degraded_count` 和 `failed_count`。
- Downloader 根据平台调用 `resource-platforms` 下载模式或通用下载方式，并负责重试和降级。

### Stage 6：归档

- 调用 `library-manager`。
- 输入 `stage5_download.json`，输出 `stage6_archive.json`。
- 读取 `archived_count`、`skipped_count` 和 `dedup_stats`。
- 汇总成功、降级、失败和归档位置，将会话标记为 `completed`。

## 恢复与分支

收到消息后先判断：

| 类型 | 处理 |
|---|---|
| 新需求 | 创建新会话，从 stage 1 开始 |
| 修改需求事实或约束 | 更新 `request.json`，从 stage 1 重跑，并使后续阶段失效 |
| 仅调整搜索范围或平台策略 | 复用已验证 Intent，从 stage 2 重跑 |
| 查看更多现有候选 | 复用 `stage3_search_results.json`，重跑 stage 4 |
| 继续未完成下载 | 从 manifest 中首个未完成阶段恢复 |
| 查询已归档资源 | 直接调用 `library-manager` 检索模式，不创建搜索会话 |

重跑任一阶段时，将其所有下游阶段重置为 `pending`，避免读取旧输出。

## 异常处理

- 用户取消：将当前阶段及会话标记为 `cancelled`。
- 阶段失败：记录错误；根据 `retryable` 决定重试，不静默跳过。
- 部分平台失败：stage 3 保留成功平台结果，并将失败平台写入摘要。
- 下载全部失败：保留来源链接及明确的降级结果，再询问是否更换资源。
- 不破解付费墙、不绕过访问控制、不下载用户未确认的资源。

## 参考资料

- `references/workflow-guide.md`：恢复、异常和用户交互规则。
- `references/output-templates.md`：候选展示、下载进度和最终结果模板。
