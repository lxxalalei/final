# 跨 Skill 上下文传递契约

> 本文件定义各 Skill 之间数据传递的输入输出契约，确保字段在传递过程中不丢失、不变形。
> 所有 Skill 的输入输出都必须严格遵循此契约。字段语义见 `resource-schema.md`。

## 概述

完整工作流由 6 个阶段组成，相邻阶段通过结构化上下文（JSON）传递数据。
本契约规定：每个阶段的「必须传递字段」「可选传递字段」「禁止丢弃字段」。

### 契约总览

```
resource-intent  →  resource-search  →  resource-selector  →  resource-downloader  →  library-manager
   阶段一              阶段二               阶段三                阶段四                  阶段五
 (查询指令包)        (候选列表)           (选定列表)            (下载结果)             (归档结果)
```

---

## 阶段一 → 阶段二：intent → search

### 契约名称：查询指令包（Query Package）

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `summary` | string | ✅ | 一句话需求总结 |
| `core_topic` | string | ✅ | 核心主题 |
| `queries` | array&lt;object&gt; | ✅ | 分级查询列表（核心/官方/形态/长尾） |
| `queries[].text` | string | ✅ | 查询关键词 |
| `queries[].tier` | string | ✅ | 优先级：core/official/format/longtail |
| `queries[].format_hint` | string | ⚠️ | 形态定向时标注：视频/音频/文档/图文 |
| `target_age` | string | ✅ | 目标年龄范围（含是否为假设） |
| `grade_level` | string | ⚠️ | 年级（如明确） |
| `difficulty` | string | ⚠️ | 难度偏好：入门/进阶/系统 |
| `format_preferences` | array&lt;string&gt; | ⚠️ | 资源形态偏好 |
| `source_preference` | string | ⚠️ | 来源偏好：不限/官方优先/视频平台优先 |
| `search_mode` | string | ✅ | standard / exhaustive |
| `assumptions` | array&lt;string&gt; | ✅ | 默认假设清单（透明化） |

### 禁止丢弃
- `core_topic`、`queries`、`target_age`、`search_mode` 必须完整传递，search 依赖它们做路由和召回量控制。

---

## 阶段二 → 阶段三：search → selector

### 契约名称：候选资源列表（Candidate List）

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `total_count` | number | ✅ | 候选总数 |
| `search_summary` | string | ✅ | 召回账本（查询数/平台/召回/初筛/最终） |
| `resources` | array&lt;object&gt; | ✅ | 候选资源数组 |
| `resources[].resource_id` | string | ✅ | `平台名:平台内ID` |
| `resources[].title` | string | ✅ | 资源标题 |
| `resources[].type` | string | ✅ | 资源类型 |
| `resources[].subject` | string | ✅ | 学科/领域 |
| `resources[].platform` | string | ✅ | 平台标识 |
| `resources[].source_url` | string | ✅ | 来源URL |
| `resources[].source_name` | string | ✅ | 平台显示名 |
| `resources[].quality_level` | string | ✅ | S/A/B/C |
| `resources[].download_feasibility` | string | ✅ | 高/中/低 |
| `resources[].platform_quality_score` | number | ⚠️ | 平台自评分 0-100 |
| `resources[].description` | string | ⚠️ | 内容简介 |
| `resources[].age_range` | string | ⚠️ | 适龄范围 |
| `resources[].grade_level` | string | ⚠️ | 适用年级 |
| `resources[].tags` | array&lt;string&gt; | ⚠️ | 标签 |
| `resources[].view_count` | number | ⚠️ | 播放/浏览量 |
| `resources[].duration` | string | ⚠️ | 时长/集数 |
| `resources[].language` | string | ⚠️ | 语言 |

### 禁止丢弃
- `quality_level`、`download_feasibility`、`platform` 必须保留，selector 依赖它们做展示和分类。
- `source_url`、`resource_id` 必须保留，downloader 依赖它们执行下载。

---

## 阶段三 → 阶段四：selector → downloader

### 契约名称：选定资源列表（Selected List）

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `selected_count` | number | ✅ | 选中数量 |
| `selection_mode` | string | ✅ | manual/all/by_type/by_quality |
| `resources` | array&lt;object&gt; | ✅ | 用户选中的资源（完整透传阶段二字段） |

### 字段透传要求
- resources 数组中每个对象**必须完整透传**阶段二候选的全部字段，不得删减。
- downloader 需要其中的 `platform`、`source_url`、`type`、`resource_id` 才能正确路由。

### 禁止丢弃
- 任何上游字段都不得在此阶段删除。selector 只做筛选，不做字段裁剪。

---

## 阶段四 → 阶段五：downloader → library-manager

### 契约名称：下载结果列表（Download Result List）

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `total_count` | number | ✅ | 资源总数 |
| `success_count` | number | ✅ | 成功数 |
| `degraded_count` | number | ✅ | 降级数 |
| `failed_count` | number | ✅ | 失败数 |
| `resources` | array&lt;object&gt; | ✅ | 下载结果数组 |
| `resources[].*` | (上游全部字段) | ✅ | 透传所有上游字段 |
| `resources[].download_status` | string | ✅ | success/degraded/failed |
| `resources[].degraded_level` | string | ✅ | Level 0/1/2/3 |
| `resources[].file_path` | string | ⚠️ | 本地路径（成功时） |
| `resources[].file_size` | number | ⚠️ | 文件大小（字节） |
| `resources[].fetch_time` | string | ⚠️ | 获取时间 ISO |
| `resources[].fetch_method` | string | ⚠️ | 获取方式 |
| `resources[].error_code` | string | ⚠️ | 错误码（失败时） |
| `resources[].error_message` | string | ⚠️ | 错误信息（失败时） |
| `resources[].degraded_content` | string | ⚠️ | 降级内容说明 |
| `resources[].alternative_recommendations` | array | ⚠️ | 替代推荐（失败时） |

### 禁止丢弃
- 上游元数据（title/type/subject/platform/source_url/quality_level 等）必须透传，library-manager 依赖它们做分类归档。
- `download_status` 为 `failed` 的资源也要传递（library-manager 可将降级链接也归档）。

---

## 阶段五输出：library-manager → flow（最终归档）

### 契约名称：归档结果列表（Archive Result List）

| 字段 | 类型 | 必须 | 说明 |
|------|------|------|------|
| `archived_count` | number | ✅ | 归档成功数 |
| `skipped_count` | number | ✅ | 跳过数（重复等） |
| `resources` | array&lt;object&gt; | ✅ | 归档结果数组 |
| `resources[].*` | (上游全部字段) | ✅ | 透传 |
| `resources[].library_path` | string | ✅ | 资料库内路径 |
| `resources[].archive_time` | string | ✅ | 归档时间 ISO |
| `resources[].dedup_status` | string | ⚠️ | new/duplicate/skipped |

---

## 数据传递规范

### 1. 完整透传原则
上游传递下来的所有字段，下游必须原样保留，不得随意删除。即使下游暂时用不到，也要透传给再下游。

### 2. 只增不删原则
每个阶段只能**新增**本阶段产生的字段，不能删除上游字段。字段生命周期从产生到最终交付贯穿始终。

### 3. 字段语义一致
所有字段的语义以 `resource-schema.md` 为准，各 Skill 不得对同一字段做不同理解。

### 4. 向后兼容
新增字段必须可选，旧字段不删除不改变语义。规范版本变更时同步更新本契约和 schema。

---
