# 资源元数据规范

> 本规范定义了学习资源的元数据格式，所有 Skill 都应遵循此规范，确保数据互通。

## 概述

资源元数据是描述学习资源的结构化数据，用于资源的检索、排序、展示和管理。
所有 Skill 在处理资源时都应使用统一的元数据格式，确保：
- 数据可以在 Skill 之间传递
- 索引可以统一构建
- 展示格式可以统一
- 用户体验一致

---

## 核心字段

### 必选字段（所有阶段通用）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `resource_id` | string | 资源唯一标识，格式：`平台名:平台内ID` | `"bilibili:BV1xx411c7mD"` |
| `title` | string | 资源标题 | `"三年级四则混合运算练习题"` |
| `type` | string | 资源类型 | `"练习题"` |
| `subject` | string | 学科/领域 | `"数学"` |
| `platform` | string | 来源平台标识（英文，统一） | `"bilibili"` |
| `source_url` | string | 原始来源URL | `"https://www.bilibili.com/video/BV1xx411c7mD"` |
| `source_name` | string | 来源平台/网站显示名 | `"B站"` |
| `quality_level` | string | 最终质量等级（调度器校准后）：S/A/B/C | `"S"` |
| `download_feasibility` | string | 下载可行性预估：高/中/低 | `"高"` |

---

### 搜索阶段新增字段（search 返回时填充）

> **字段分级标记：** ✅必选（必须返回） / 🟡推荐（强烈建议返回，影响排序与展示） / ⚪可选（有则更好，无则跳过）

| 字段名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `platform_quality_score` | number | ✅必选 | 平台自评质量分（0-100） | `85` |
| `description` | string | ✅必选 | 内容简介（1-2句话） | `"包含50道脱式计算题，带详细答案"` |
| `age_range` | string | 🟡推荐 | 适龄范围 | `"6-8岁"` |
| `grade_level` | string | 🟡推荐 | 适用年级 | `"小学三年级"` |
| `tags` | array | 🟡推荐 | 标签列表 | `["四则运算", "脱式计算", "含答案"]` |
| `view_count` | number | 🟡推荐 | 播放/浏览量（如有） | `125000` |
| `like_count` | number | 🟡推荐 | 点赞/收藏量（如有） | `3200` |
| `duration` | string | 🟡推荐 | 时长（视频/音频） | `"30分钟"` |
| `file_format` | string | 🟡推荐 | 文件格式（已知时） | `"pdf"` |
| `language` | string | 🟡推荐 | 语言 | `"中文"` |
| `publish_time` | string | ⚪可选 | 发布时间（ISO格式） | `"2024-06-15T08:00:00Z"` |
| `thumbnail_url` | string | ⚪可选 | 封面图URL | `"https://i0.hdslb.com/bfs/archive/cover.jpg"` |
| `author` | string | ⚪可选 | 作者/UP主/主播名 | `"李老师课堂"` |

---

### 下载阶段新增字段（downloader 返回时填充）

> **字段分级标记：** ✅必选（必须返回） / 🟡推荐 / ⚪可选

| 字段名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `download_status` | string | ✅必选 | 下载状态：success/degraded/failed | `"success"` |
| `file_path` | string | ✅必选 | 本地文件路径 | `"数学/小学三年级/四则混合运算/BV1xx.mp4"` |
| `file_size` | number | ✅必选 | 文件大小（字节） | `1024000` |
| `fetch_time` | string | ✅必选 | 获取时间（ISO格式） | `"2024-01-01T12:00:00Z"` |
| `fetch_method` | string | ✅必选 | 获取方式：下载/转换/人工辅助 | `"下载"` |
| `error_code` | string | 🟡推荐 | 错误码（失败时），见统一错误码体系 | `"ANTI_CRAWL_BLOCKED"` |
| `error_message` | string | 🟡推荐 | 错误信息（失败时） | `"被反爬拦截，需要登录"` |
| `degraded_level` | string | 🟡推荐 | 降级等级：Level 0=完整，Level 1=预览，Level 2=摘要，Level 3=链接 | `"Level 0"` |
| `checksum` | string | ⚪可选 | 文件校验和（MD5/SHA256） | `"sha256:a1b2c3d4e5f6..."` |
| `resolution` | string | ⚪可选 | 分辨率（视频/图片） | `"1920x1080"` |
| `bitrate` | number | ⚪可选 | 比特率（kbps，视频/音频） | `4500` |

---

### 归档阶段新增字段（library-manager 归档时填充）

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `library_path` | string | 资料库内的完整路径 | `"数学/小学三年级/四则混合运算/"` |
| `archive_time` | string | 归档时间（ISO格式） | `"2024-01-01T13:00:00Z"` |
| `last_viewed` | string | 最后查看时间 | `"2024-01-15T10:00:00Z"` |
| `view_count` | number | 查看次数 | `10` |
| `favorite` | boolean | 是否收藏 | `false` |
| `is_duplicate` | boolean | 是否为重复资源（去重引擎标记） | `false` |
| `duplicate_of` | string | 重复的正本 resource_id（`is_duplicate` 为 true 时填充） | `"bilibili:BV1xx411c7mD"` |
| `dedup_match_type` | string | 去重匹配类型：exact/url/similar_title/resource_id | `"similar_title"` |

---

## 字段详细说明

### resource_id - 资源唯一标识

**格式：** `平台名:平台内ID`

**示例：**
- `bilibili:BV1xx411c7mD`
- `ximalaya:12345678`
- `baiduwenku:doc-abc123`
- `generic:url-hash`（通用兜底时用URL哈希）

**为什么用这种格式：**
- 一眼就能看出来自哪个平台
- 跨平台不会冲突
- 便于平台 skill 快速识别

---

### platform - 平台标识

**标准平台标识：**

| 标识 | 平台名称 | 说明 |
|------|---------|------|
| `bilibili` | B站（哔哩哔哩） | 视频平台 |
| `ximalaya` | 喜马拉雅 | 音频平台 |
| `smartedu` | 国家中小学智慧教育平台 | 官方教育平台 |
| `baiduwenku` | 百度文库 | 文档分享平台 |
| `zhihu` | 知乎 | 图文社区 |
| `xiaohongshu` | 小红书 | 图文社区 |
| `douyin` | 抖音 | 短视频平台 |
| `open163` | 网易公开课 | 公开课平台 |
| `cctv` | 央视网 | 官方视频平台 |
| `generic` | 通用/未知 | 通用兜底，没有对应 platform skill |

**命名规则：**
- 全小写英文
- 简短好记
- 保持一致性

---

### quality_level - 质量等级

**等级定义：**

| 等级 | 说明 | 标准 |
|------|------|------|
| `S` | 强烈推荐 | 官方权威、完全免费、内容完整、极易获取 |
| `A` | 优质推荐 | 内容质量好、免费或基础免费、获取较易 |
| `B` | 可用推荐 | 内容尚可、可能有广告或付费、获取有一定难度 |
| `C` | 谨慎推荐 | 质量一般、广告多或需付费、获取困难 |

**评估机制：两级评估**
1. **平台自评**：platform skill 对自己返回的结果先打分（`platform_quality_score`），最了解自己平台的情况
2. **调度器校准**：resource-search 再根据跨平台统一标准做校准，给出最终 `quality_level`

---

### download_feasibility - 下载可行性预估

**等级定义：**

| 等级 | 说明 | 典型场景 |
|------|------|---------|
| `高` | 基本可以成功下载 | 直链文件、公开视频、普通网页 |
| `中` | 可能需要重试或降级 | 有轻度反爬、需要登录、部分免费 |
| `低` | 大概率下不了，只能降级 | 付费内容、强反爬、DRM保护 |

**谁来填：**
- platform skill 在搜索阶段就给出预估（它最清楚自己平台哪些内容好下）
- 通用兜底的由 search 调度器根据经验判断

---

### type - 资源类型

**标准类型：**

| 类型 | 说明 | 示例 |
|------|------|------|
| `练习题` | 习题、试卷、练习册 | 口算题、应用题、期末试卷 |
| `视频` | 视频课程、动画、纪录片 | 教学视频、科普动画 |
| `音频` | 有声故事、儿歌、音频课 | 睡前故事、英文儿歌 |
| `绘本` | 图画书、故事书 | 中文绘本、英文绘本 |
| `课件` | 教学课件、PPT | 课堂课件、知识点总结 |
| `文档` | 文章、教程、资料 | 学习方法、知识点整理 |
| `图片` | 图片素材、卡片 | 识字卡片、思维导图 |
| `软件` | APP、软件、工具 | 学习APP、编程工具 |
| `活动` | 活动方案、手工教程 | 科学实验、手工制作 |
| `合集` | 多种类型的资源包 | 主题资源包、学习套装 |

---

### subject - 学科/领域

**标准学科：**

| 学科 | 包含内容 |
|------|---------|
| `数学` | 计算、几何、应用题、奥数、思维训练等 |
| `语文` | 拼音、识字、阅读、写作、古诗文等 |
| `英语` | 启蒙、单词、听说、阅读、语法等 |
| `科普` | 科学、自然、动物、宇宙、实验等 |
| `编程` | Scratch、Python、机器人、信息学等 |
| `艺术` | 美术、音乐、手工、舞蹈等 |
| `综合` | 跨学科、综合主题 |
| `其他` | 不属于以上分类的 |

---

### tags - 标签

**作用：**
- 多维度分类
- 模糊检索
- 个性化推荐

**标签类型：**
- **知识点标签**：四则运算、乘法口诀、拼音、识字...
- **难度标签**：入门、基础、进阶、提高、竞赛...
- **用途标签**：预习、复习、练习、拓展、启蒙...
- **形式标签**：打印版、电子版、视频、音频、互动...
- **特点标签**：含答案、带解析、游戏化、动画、趣味...

**标签管理：**
- 每个资源 3-8 个标签为宜
- 优先使用常用标签
- 避免意思重复的标签
- 保持标签的一致性

---

## 不同资源类型的特殊字段

### 练习题类

**额外字段：**
- `has_answer`：是否有答案
- `question_count`：题目数量
- `difficulty`：难度
- `has_explanation`：是否有解析

---

### 视频类

**额外字段：**
- `duration`：时长
- `resolution`：分辨率
- `has_subtitle`：是否有字幕
- `episode`：集数/讲数
- `author`：UP主/作者

---

### 音频类

**额外字段：**
- `duration`：时长
- `speaker`：主播/讲述者
- `episode`：集数
- `author`：主播/作者

---

### 绘本/图书类

**额外字段：**
- `author`：作者
- `publisher`：出版社
- `page_count`：页数
- `isbn`：ISBN（如果有）

---

## 完整示例

### 搜索结果完整示例（来自B站）

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "title": "小学三年级数学四则混合运算系统讲解",
  "type": "视频",
  "subject": "数学",
  "platform": "bilibili",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "source_name": "B站",
  "quality_level": "A",
  "download_feasibility": "中",
  "platform_quality_score": 82,
  "description": "系统讲解四则混合运算的顺序和技巧，共12集，动画形式，孩子容易理解",
  "age_range": "7-9岁",
  "grade_level": "小学三年级",
  "tags": ["四则运算", "混合运算", "动画讲解", "系统课程"],
  "view_count": 125000,
  "like_count": 3200,
  "duration": "120分钟（共12集）",
  "language": "中文"
}
```

---

### 下载完成后完整示例

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "title": "小学三年级数学四则混合运算系统讲解",
  "type": "视频",
  "subject": "数学",
  "platform": "bilibili",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "source_name": "B站",
  "quality_level": "A",
  "download_feasibility": "中",
  "platform_quality_score": 82,
  "description": "系统讲解四则混合运算的顺序和技巧，共12集，动画形式，孩子容易理解",
  "age_range": "7-9岁",
  "grade_level": "小学三年级",
  "tags": ["四则运算", "混合运算", "动画讲解", "系统课程"],
  "view_count": 125000,
  "like_count": 3200,
  "duration": "120分钟（共12集）",
  "language": "中文",
  "download_status": "success",
  "file_path": "下载/B站-四则混合运算讲解.mp4",
  "file_size": 256000000,
  "fetch_time": "2024-01-01T12:00:00Z",
  "fetch_method": "下载",
  "degraded_level": "Level 0"
}
```

---

## 索引格式

### 主索引

```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "total_count": 100,
  "resources": [
    { ... },
    { ... }
  ]
}
```

### 标签索引

```json
{
  "version": "2.1",
  "updated_at": "2024-01-01T12:00:00Z",
  "tags": {
    "四则运算": ["id1", "id2", "id3"],
    "恐龙": ["id4", "id5"],
    "..."
  }
}
```

---

## 设计原则

### 1. 够用就好
字段不要太多，满足核心需求即可。增加字段必须有明确的使用场景和消费者。

### 2. 向后兼容
新版本尽量兼容旧版本，新增字段都是可选的，不删除已有字段。

### 3. 统一标准
所有 Skill 都遵循同一套规范，确保数据可以互通。

### 4. 易于扩展
预留扩展空间，新的资源类型可以在不修改核心规范的情况下增加。

### 5. 用户价值导向
每个字段都应该对用户有价值，要么帮助检索，要么帮助选择，要么帮助使用。
