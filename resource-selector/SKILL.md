---
name: resource-selector
description: 学习资源候选筛选与用户选择 Skill。用于读取平台搜索的归一化原始结果，执行跨平台去重、业务过滤、统一质量评分和排序，向用户展示候选并保存最终选择。
---

# resource-selector

## 职责

本 Skill 是流水线 stage 4，也是搜索结果进入下载前唯一的业务筛选入口。

负责：

1. 跨平台和相似内容去重。
2. 相关性、安全性、语言、付费状态和资源完整性过滤。
3. 统一质量评分及 S/A/B/C 定级。
4. 按质量、相关性和下载可行性排序。
5. 结构化展示候选并解释过滤结果。
6. 接收用户选择并完整保留所选资源字段。

不负责执行平台搜索、下载资源或归档文件。

## 输入

从 flow 获取：

- `{session_dir}`：会话目录绝对路径。
- `{input_file}`：默认 `stage3_search_results.json`。
- `{output_file}`：默认 `stage4_selection.json`。

读取输入文件的 `data`：

- `intent_context`：其中包含 `core_topic`、`target_age`、`search_mode` 和用户约束。
- `resources`：平台层归一化后的原始有效结果。
- `platform_stats`、`errors`：用于向用户解释搜索覆盖情况。

输入资源可能缺少业务字段。缺失值不得凭空补造；可基于标题、描述和平台信号作有依据的推断，并把推断记录到 `assessment_notes`。

## 执行流程

### 1. 跨平台去重

按以下顺序识别重复：

1. `resource_id` 完全相同。
2. 规范化后的 `source_url` 相同。
3. 标题、作者、时长或内容指纹高度相似。

保守去重：无法确认时保留并标记 `possible_duplicate`。确认重复时优先保留信息更完整、质量更高、下载更可行的版本，并在 `dedup_stats` 中记录被合并项。

### 2. 前置业务过滤

直接过滤：

- 与 `intent_context.core_topic` 明显无关。
- 包含儿童不宜、安全风险、诈骗或恶意诱导内容。
- 只有广告、失效页面或空内容。
- 明确需要付费/VIP，且用户要求免费内容。
- 非目标语言，且需求不属于语言学习。

不要因为“质量一般”直接过滤；可用但一般的结果保留为 B/C 级。每个过滤结果记录 `resource_id`、`reason_code` 和简要原因。

### 3. 统一质量评分

按照 `references/quality-rubric.md` 评分。平台提供的热度和自评分只作为辅助证据，不能直接作为最终等级。

写入：

- `quality_score`：0-100。
- `quality_level`：S/A/B/C。
- `quality_dimensions`：各维度得分。
- `assessment_notes`：证据不足或推断说明。

### 4. 排序和候选控制

默认排序：

1. `quality_score` 降序。
2. 与主题和年龄的匹配度降序。
3. `download_feasibility`：高 → 中 → 低。
4. 信息完整度降序。

标准模式默认展示前 20 条，穷尽模式可分批展示。未展示的合格资源仍保留在 `qualified_resources` 中，用户要求“查看更多”时继续展示，不重新搜索。

### 5. 展示并等待用户选择

展示前先说明：原始结果数、去重数、过滤数、合格候选数和平台失败情况。每条候选至少显示：

- 编号、标题、平台、资源类型。
- 质量等级及简要理由。
- 下载可行性。
- 费用或登录要求（已知时）。

支持编号、全部、按平台、按类型、按质量等级和“查看更多”选择。下载前必须获得明确确认。

### 6. 写入选择结果

写入 `{session_dir}/stage4_selection.json`：

```json
{
  "_meta": {
    "stage": 4,
    "session_id": "继承上游",
    "skill": "resource-selector",
    "created_at": "ISO 8601",
    "input_from": "stage3_search_results.json"
  },
  "_summary": {
    "raw_count": 72,
    "candidate_count": 22,
    "selected_count": 5,
    "selection_mode": "manual",
    "quality_dist": {"S": 3, "A": 8, "B": 9, "C": 2},
    "filter_stats": {
      "duplicates_removed": 12,
      "business_filtered": 38
    }
  },
  "data": {
    "selected_count": 5,
    "selection_mode": "manual",
    "resources": [],
    "candidate_snapshot": {
      "raw_count": 72,
      "qualified_count": 22,
      "filter_stats": {},
      "platform_errors": []
    }
  }
}
```

`data.resources` 只包含用户最终确认的资源。每条所选资源必须完整保留 stage 3 的全部原始字段，并追加 selector 的评分、去重和展示字段；不得裁剪来源 URL、平台 ID 或下载所需信息。

## 无结果和取消

- 原始结果为零：说明各平台失败或无召回情况，通知 flow 回到 stage 2 调整计划。
- 全部被过滤：按过滤原因汇总，允许用户明确放宽条件后重跑本阶段。
- 用户未选择或取消：写入 `selected_count=0` 和取消方式，不调用 downloader。

## 参考资料

- `references/quality-rubric.md`：本 Skill 的最终质量评分与过滤标准。
- `references/display-templates.md`：候选展示格式。
