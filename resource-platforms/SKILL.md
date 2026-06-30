---
name: resource-platforms
description: 搜索执行 Skill（阶段三）。当搜索策略阶段输出搜索任务清单后激活，按优先级调度各平台搜索脚本执行搜索，汇总原始结果并进行跨平台去重，输出标准化后的去重结果列表供下游质量筛选阶段使用。
agent_created: true
---

# resource-platforms · 搜索执行

**上游**：resource-search（读取 `stage2_search_plan.json` 的 data）
**下游**：resource-selector（写入 `stage3_candidates.json`）
**阶段编号**：stage 3

按搜索任务清单调度各平台搜索脚本，汇总原始结果、跨平台去重、标准化为统一格式后输出。不做质量评估、过滤精选和排序——这些由下游 selector 负责。

---

## 执行前准备

读取 `{session_dir}/manifest.json`，获取本阶段执行所需信息：

- `manifest.stages.stage2.output` → 上游输入文件名（通常是 `stage2_search_plan.json`）
- `manifest.stages.stage3.output` → 本阶段输出文件名（通常是 `stage3_candidates.json`）

读取 `{session_dir}/{上游输入文件}` 的 `data` 部分，提取以下字段：

- `search_tasks`：各平台搜索任务列表（数组，必选）
  - 每个任务包含：`platform_id`、`platform_name`、`priority`（P0/P1/P2）、`queries`（含 text/tier/format_hint）、`target_count`、`search_params`（可选）
- `core_topic`：核心主题（必选，透传下游）
- `target_age`：目标年龄范围（必选，透传下游）
- `search_mode`：搜索模式 standard / exhaustive（必选）

---

## 执行步骤

### 第一步：确认可用平台

根据搜索任务中的 `platform_id` 列表，确认每个平台的搜索脚本是否存在且可用。

**脚本查找规则**：
- 搜索脚本位于 `./scripts/{platform_id}/` 目录下
- 搜索脚本命名：`{platform_id}_search.py` 或 `adapter.py`（统一接口）
- generic 平台走通用搜索引擎，无专属脚本

**不可用平台处理**：跳过该平台，记录平台 ID 和跳过原因到 `skipped_platforms`，不影响其他平台执行。

**凭证管理**：部分平台（如知乎）需要登录态 Cookie 才能调用搜索 API。凭证查找优先级：CLI 参数 > 环境变量 > `scripts/{platform}/config/credentials.json`（随 skill 安装在用户本地）。用户首次使用时通过 `python scripts/{platform}/{platform}_search.py set-cookie "cookie值"` 写入配置文件，后续自动读取。当 API 返回 401/403 时，脚本输出 `CREDENTIAL_EXPIRED` 错误码，提示用户提供新 cookie。

> 📖 各平台的搜索能力、认证要求和反爬等级见 `./references/platforms/{platform_id}.md`

---

### 第二步：按优先级调度搜索

按平台优先级从高到低（P0 → P1 → P2 → generic），依次调度各平台搜索脚本。

**每个平台的执行流程**：
1. 读取该平台的查询列表（queries 数组）
2. 按查询优先级依次执行搜索（core → official → format → longtail）
3. 收集搜索结果，进行平台内初步去重
4. 将结果标准化为统一资源元数据格式

**错误容错**：某个平台或某个查询失败时记录错误，跳过继续，不影响整体流程。每个查询的执行结果（成功/失败/部分成功）记录到 `platform_stats`。

**平台脚本返回的每个资源对象包含**：
- 基本元数据：`resource_id`、`title`、`type`、`platform`、`source_url`、`source_name`
- 质量信号：`platform_quality_score`（0-100 分，平台脚本自评的原始分，供 selector 参考）
- 可选元数据：`description`、`age_range`、`grade_level`、`tags`、`view_count`、`duration`、`language`、`is_free`、`author`

> 📖 统一资源元数据字段规范见 `./references/schemas/resource-schema.md`

---

### 第三步：跨平台去重

对所有平台的原始结果进行跨平台去重。

**去重策略（按优先级依次检测）**：

1. **resource_id 完全一致**（最强信号）：同一平台的相同 ID 直接去重
2. **URL 结构化去重**：去除 URL 追踪参数（utm_*、spm、share_* 等）后比较
3. **标题相似度去重**：编辑距离 + TF-IDF 余弦相似度，超过阈值（0.85）视为重复

检测到重复时，保留 `platform_quality_score` 最高的版本。去重策略保守——宁留几个重复，不误删好资源。

> 📖 完整去重规则和算法见 `./scripts/shared/dedup.py`

**去重产出**：`deduped_results`（去重后列表）+ `dedup_stats`（原始数量/去重后数量/移除数）

---

### 第四步：写入输出文件

将去重后的结果写入 `{session_dir}/{manifest.stages.stage3.output}`（通常是 `stage3_candidates.json`）。

```json
{
  "_meta": {
    "stage": 3,
    "session_id": "从 manifest 继承",
    "skill": "resource-platforms",
    "created_at": "当前时间 ISO 8601",
    "input_from": "stage2_search_plan.json"
  },
  "_summary": {
    "total_count": 45,
    "raw_count": 72,
    "platforms": ["bilibili", "smartedu", "ximalaya", "zhihu", "generic"],
    "has_results": true
  },
  "data": {
    "total_count": 45,
    "search_summary": "搜索了5个平台，执行15个查询，原始召回72条，去重后45条",
    "resources": [
      {
        "resource_id": "bilibili:BV1xx411c7mD",
        "title": "小学必背古诗文动画（228集全）",
        "type": "视频",
        "platform": "bilibili",
        "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
        "source_name": "B站",
        "platform_quality_score": 90,
        "download_feasibility": "中",
        "description": "动画形式讲解小学必背古诗",
        "age_range": "6-12岁",
        "tags": ["古诗", "动画", "系统课程"],
        "view_count": 5000000,
        "duration": "共228集"
      }
    ],
    "search_stats": {
      "platforms_executed": 5,
      "queries_executed": 15,
      "raw_count": 72,
      "deduped_count": 45,
      "skipped_platforms": []
    },
    "intent_data": {}
  }
}
```

**_summary**（flow 只读这个做调度）：`total_count`（去重后总数）、`raw_count`（原始召回数）、`platforms`（执行平台列表）、`has_results`（是否有结果）

**data**（下游 selector 读这个）：`total_count`（必选）、`search_summary`（必选）、`resources`（必选，去重后的资源列表）、`search_stats`（可选）、`intent_data`（必选，原样透传 intent 的 data 供 selector 做质量评估）

> `platform_quality_score` 是粗筛信号，不是最终评分。selector 会基于五维体系重新评估。

---

## 完成后

### 1. 更新 manifest

将 `manifest.json` 中 `stages.stage3.status` 更新为 `completed`。

### 2. 返回摘要

只返回 `_summary`，不展开完整资源列表：

```
✅ 已完成搜索执行
📄 输出文件：stage3_candidates.json
📊 摘要：
- 去重后结果：{total_count} 个（原始召回 {raw_count} 个）
- 覆盖平台：{platforms 数量} 个
```

> 完整数据已写入文件，下游 selector 会去读、评估、过滤后展示给用户。不要在上下文中展开资源列表。

---

## 关键原则

- 按优先级执行，高优先级平台先搜，保证核心覆盖
- 结果标准化：各平台结果统一转为 resource-schema 规定的格式
- 错误容错：某个平台失败不影响整体，跳过继续
- 去重保守：宁留几个重复，不误删好资源
- 只做搜索和去重，不做质量评估、过滤精选和排序——输出原始结果，判断权交给 selector

---

## 参考资料

- `./references/schemas/resource-schema.md` — 统一资源元数据字段规范
- `./references/schemas/platform-search-contract.md` — 平台搜索接口规范
- `./references/platforms/{platform_id}.md` — 各平台搜索文档（bilibili/smartedu/ximalaya/open163/zhihu/douyin/weibo）
- `./scripts/shared/dedup.py` — 跨平台去重引擎（DedupEngine）
- `./scripts/shared/config_loader.py` — 统一配置加载器（ConfigLoader / get_config）
