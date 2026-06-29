# 平台搜索接口契约（Platform Search Contract）

## 概述

本文档定义 **resource-search（搜索调度器）** 与 **platform-xxx（平台执行层 Skill）** 之间的搜索接口规范。

所有 platform skill 的搜索功能必须遵守本契约，确保调度层可以无差别调用所有平台。

---

## 一、调用方向

```
resource-search（调度器）
    ↓ 调用
platform-xxx（平台 Skill）
    ↓ 返回
resource-search（调度器）
```

---

## 二、输入参数（调度器 → 平台 Skill）

### 2.1 必填字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `query` | string | 搜索关键词 | `"小学古诗 动画"` |
| `platform` | string | 平台标识（与 platform-mapping.md 一致） | `"bilibili"` |

### 2.2 可选字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_results` | int | `10` | 期望返回的最大结果数量 |
| `age_range` | string | `null` | 目标年龄范围，如 `"6-10岁"`，用于平台内筛选或结果排序 |
| `grade_level` | string | `null` | 目标年级，如 `"小学三年级"` |
| `resource_type` | string | `null` | 资源类型过滤（中文，与 resource-schema 一致）：`视频` / `音频` / `文档` / `练习题` / `绘本` / `课件` / `图片` / `软件` / `活动` / `合集` |
| `sort_by` | string | `"relevance"` | 排序方式：`relevance`（相关性）/ `popularity`（热度）/ `newest`（最新） |
| `language` | string | `"zh"` | 语言过滤，默认只返回中文 |
| `free_only` | boolean | `true` | 是否只返回免费内容，默认是 |
| `extra_params` | object | `{}` | 平台专属扩展参数，调度器不解析，透传给平台 |

### 2.3 输入示例

```json
{
  "query": "小学必背古诗 动画",
  "platform": "bilibili",
  "max_results": 10,
  "age_range": "6-12岁",
  "resource_type": "video",
  "sort_by": "popularity",
  "free_only": true
}
```

---

## 三、输出结果（平台 Skill → 调度器）

### 3.1 顶层结构

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `platform` | string | ✅ | 平台标识 |
| `query` | string | ✅ | 实际执行的查询（可能和输入略有不同） |
| `total_found` | int | ✅ | 平台内找到的总结果数（估算值也可以） |
| `returned_count` | int | ✅ | 本次实际返回的结果数量 |
| `results` | array | ✅ | 搜索结果列表，每个元素符合资源元数据规范 |
| `search_method` | string | ✅ | 使用的搜索方法：`api` / `web_scrape` / `site_search` / `other` |
| `has_more` | boolean | ❌ | 是否还有更多结果 |
| `next_page_token` | string | ❌ | 翻页 token（如果平台支持） |
| `error` | object | ❌ | 搜索失败时的错误信息（见错误返回章节） |

### 3.2 results 数组元素规范

每个结果对象**必须包含** resource-schema.md 中定义的「搜索阶段字段」，其中：

**必填字段（每个结果都必须有）**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `resource_id` | string | 资源唯一 ID，格式：`平台名:平台内ID`，如 `bilibili:BV1xx411c7mD` |
| `title` | string | 资源标题 |
| `type` | string | 资源类型（中文），见 resource-schema 标准：`视频` / `音频` / `文档` / `练习题` / `绘本` / `课件` / `图片` / `软件` / `活动` / `合集` / `其他` |
| `subject` | string | 主题分类，参考 resource-schema 的 8 大品类 |
| `platform` | string | 平台标识（与 platform-mapping.md 一致） |
| `source_url` | string | 资源原始链接 |
| `source_name` | string | 来源平台显示名，如 `B站` / `知乎` / `国家中小学智慧教育平台` |
| `quality_level` | string | 平台自评质量等级：`S` / `A` / `B` / `C` |
| `platform_quality_score` | number | 平台自评质量分（0-100），调度器会据此做跨平台校准 |
| `download_feasibility` | string | 下载可行性预估：`高` / `中` / `低` |
| `description` | string | 内容简介或摘要 |

**推荐字段（平台有的话尽量返回）**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `age_range` | string | 适龄范围 |
| `grade_level` | string | 适用年级 |
| `tags` | array | 标签列表 |
| `view_count` | number | 播放/浏览量 |
| `like_count` | number | 点赞/收藏数 |
| `duration` | number | 时长（秒），视频/音频类 |
| `file_format` | string | 文件格式，如 `mp4` / `mp3` / `pdf` |
| `language` | string | 语言 |
| `publish_time` | string | 发布时间（ISO 格式） |
| `thumbnail_url` | string | 封面图 URL |

### 3.3 输出示例

```json
{
  "platform": "bilibili",
  "query": "小学必背古诗 动画",
  "total_found": 1250,
  "returned_count": 10,
  "search_method": "web_scrape",
  "has_more": true,
  "results": [
    {
      "resource_id": "bilibili:BV1xx411c7mD",
      "title": "【228集全】小学必背古诗文动画 孩子一看就懂",
      "type": "视频",
      "subject": "语文",
      "platform": "bilibili",
      "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "source_name": "B站",
      "quality_level": "S",
      "platform_quality_score": 95,
      "download_feasibility": "中",
      "description": "覆盖小学全部必背古诗，动画形式讲解，孩子容易接受...",
      "age_range": "6-12岁",
      "tags": ["古诗", "动画", "小学", "语文"],
      "view_count": 5230000,
      "like_count": 180000,
      "duration": 4560,
      "publish_time": "2024-03-15T00:00:00Z",
      "thumbnail_url": "https://example.com/cover.jpg"
    }
  ]
}
```

---

## 四、错误返回规范

搜索失败时，返回 error 对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `error_code` | string | ✅ | 统一错误码，见 error-codes.md |
| `error_message` | string | ✅ | 人类可读的错误描述 |
| `can_retry` | boolean | ✅ | 是否可以重试 |
| `suggested_action` | string | ❌ | 建议的下一步动作 |
| `error_details` | object | ❌ | 详细错误信息（平台专属） |

### 错误返回示例

```json
{
  "platform": "bilibili",
  "query": "小学必背古诗 动画",
  "total_found": 0,
  "returned_count": 0,
  "search_method": "web_scrape",
  "error": {
    "error_code": "ANTI_CRAWL_RATE_LIMITED",
    "error_message": "请求频率过高，被平台限流",
    "can_retry": true,
    "suggested_action": "等待 10 秒后重试，或降低请求频率"
  }
}
```

---

## 五、质量自评要求

平台 skill 必须对自己返回的结果进行质量自评，给出 `platform_quality_score`（0-100）和 `quality_level`（S/A/B/C）。

### 5.1 评分参考维度

> 📖 **全系统统一的质量评估标准见 `quality-rubric.md`（同目录），平台自评必须遵循该标准的维度和权重。**

平台自评采用五维评分（1-5 分制），加权后换算为 `platform_quality_score`（0-100）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 内容质量与完整性 | 25% | 是否系统完整、制作精良（对应原「内容完整性」+「制作质量」） |
| 适龄匹配度 | 25% | 是否适合儿童观看/收听（对应原「儿童友好度」+ 适龄标注） |
| 权威可信度 | 20% | 作者/机构的专业程度 |
| 可获取性 | 20% | 免费程度与获取难度 |
| 安全与体验 | 10% | 广告/安全/互动数据（播放量、点赞等作为辅助参考） |

> 完整的评分细则、加权公式、前置过滤规则见 [`quality-rubric.md`](quality-rubric.md)。

### 5.2 等级对应

| 等级 | 分数范围 | 加权总分 | 说明 |
|------|---------|---------|------|
| S | 90-100 | 4.5-5.0 | 强烈推荐，质量极高，系统完整 |
| A | 75-89 | 3.5-4.4 | 优质推荐，质量好，内容较完整 |
| B | 60-74 | 2.5-3.4 | 可用推荐，质量一般，内容尚可 |
| C | 30-59 | 1.5-2.4 | 谨慎推荐，质量较差或不完整 |

> **注意**：这是平台自评，调度器会根据跨平台统一标准再次校准。平台自评可以相对宽松，不要把自己平台的结果都评太低。

---

## 六、下载可行性预估要求

平台 skill 必须预估每个资源的下载难度，给出 `download_feasibility`。

| 等级 | 说明 | 典型场景 |
|------|------|---------|
| `high` → 高 | 基本可以成功下载 | 直链文件、普通网页、公开 API |
| `medium` → 中 | 可能需要重试或降级 | B站视频、喜马拉雅音频、有简单反爬 |
| `low` → 低 | 大概率下不了 | 付费内容、强 DRM、需要登录且无登录态 |

> **注意**：`download_feasibility` 字段值统一使用中文 `高`/`中`/`低`，与 `resource-schema.md` 保持一致。

---

## 七、注意事项

1. **返回数量**：尽量返回 `max_results` 条，但如果高质量结果不够，可以少返回，不要凑数
2. **去重**：平台内部先做一次去重，不要返回重复内容
3. **过滤**：默认只返回免费、中文的内容（`free_only=true`、`language=zh`）
4. **排序**：默认按相关性排序，用户指定 `sort_by` 时按指定方式排序
5. **ID 规范**：resource_id 必须使用 `平台名:平台内ID` 格式，确保全局唯一
6. **错误处理**：遇到错误不要直接抛异常，按错误返回规范返回 error 对象
7. **扩展字段**：平台专属字段可以放在 `extra_fields` 里，但核心字段必须按规范来

---

---
