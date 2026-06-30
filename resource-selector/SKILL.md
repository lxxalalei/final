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
3. 统一质量评分，并在展示时按评分区间计算 S/A/B/C 等级。
4. 按质量、相关性和下载可行性排序。
5. 结构化展示候选并解释过滤结果。
6. 接收用户选择并只保存资源引用和必要质量结论。

不负责执行平台搜索、下载资源或归档文件。

## 输入

Stage 3→4 的文件结构和字段规则以 `../docs/pipeline-data-contract.md` 为统一契约。

从 flow 获取：

- `{session_dir}`：会话目录绝对路径。
- `{output_file}`：默认 `stage4_selection.json`。

读取：

- `stage1_intent.json`：主题、适龄、目标、形态和用户约束。
- `stage3_search_results.json:data.resources`：平台层归一化后的原始有效结果。
- `stage3_search_results.json:data.errors`：用于解释平台失败情况。

输入资源可能缺少业务字段。缺失值不得凭空补造；可基于标题、描述和平台信号作有依据的推断，并把真正影响用户判断的内容记录到候选说明中。

## 执行流程

### 1. 跨平台去重

按以下顺序识别重复：

1. `resource_id` 完全相同。
2. 规范化后的 `source_url` 相同。
3. 标题、作者、时长或内容指纹高度相似。

保守去重：无法确认时保留，并在展示说明中标明“疑似重复”。确认重复时优先保留信息更完整、质量更高、下载更可行的版本。

### 2. 前置业务过滤

直接过滤：

- 与 Intent 的 `slots.core_topic` 明显无关。
- 包含儿童不宜、安全风险、诈骗或恶意诱导内容。
- 只有广告、失效页面或空内容。
- 明确需要付费/VIP，且用户要求免费内容。
- 非目标语言，且需求不属于语言学习。

不要因为“质量一般”直接过滤；可用但一般的结果保留为 B/C 级。过滤原因用于当次展示和解释，无需写入阶段输出。

### 3. 统一质量评分

按照 `references/quality-rubric.md` 评分。平台提供的热度和自评分只作为辅助证据，不能直接作为最终等级。

评分过程可以使用各维度分数，展示时可按区间显示 S/A/B/C；持久化时只保留最终 `quality_score`。确实会影响后续使用的风险或证据不足，写入所选资源的 `notes`。

### 4. 排序和候选控制

默认排序：

1. `quality_score` 降序。
2. 与主题和年龄的匹配度降序。
3. `download_feasibility`：高 → 中 → 低。
4. 信息完整度降序。

标准模式默认展示前 20 条，穷尽模式可分批展示。未展示的合格资源在本轮上下文中保留；用户要求“查看更多”时继续展示，不重新搜索。

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
    "schema_version": "selection/v1",
    "session_id": "继承上游",
    "created_at": "ISO 8601"
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

`data.selected` 只包含用户最终确认资源的 `resource_id`、最终评分和可选风险说明。`_summary.status` 与 `data.status` 一致，`selected_count` 等于选择数量。Downloader 通过 `resource_id` 回读 Stage 3 的平台、来源 URL 和下载信息，不复制完整资源对象。

## 无结果和取消

- 原始结果为零：说明各平台失败或无召回情况，通知 flow 回到 stage 2 调整计划。
- 全部被过滤：按过滤原因汇总，允许用户明确放宽条件后重跑本阶段。
- 用户未选择或取消：写入 `status=cancelled`、`selected=[]`，不调用 downloader。

## 参考资料

- `references/quality-rubric.md`：本 Skill 的最终质量评分与过滤标准。
- `references/display-templates.md`：候选展示格式。
