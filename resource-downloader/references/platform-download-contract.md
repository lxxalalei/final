# 平台下载接口契约（Platform Download Contract）

## 概述

本文档定义 **resource-downloader（下载调度器）** 与 **platform-xxx（平台执行层 Skill）** 之间的下载接口规范。

所有 platform skill 的下载功能必须遵守本契约，确保调度层可以无差别调用所有平台。

---

## 一、调用方向

```
resource-downloader（调度器）
    ↓ 调用
platform-xxx（平台 Skill）
    ↓ 返回
resource-downloader（调度器）
```

---

## 二、输入参数（调度器 → 平台 Skill）

### 2.1 必填字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `resource_id` | string | 资源唯一 ID | `"bilibili:BV1xx411c7mD"` |
| `source_url` | string | 资源原始链接 | `"https://www.bilibili.com/video/BV1xx411c7mD"` |
| `platform` | string | 平台标识 | `"bilibili"` |

### 2.2 可选字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `download_dir` | string | 临时目录 | 下载保存目录 |
| `quality` | string | `"auto"` | 画质/音质偏好：`best` / `high` / `medium` / `low` / `auto` |
| `file_format` | string | `null` | 指定文件格式，如 `mp4` / `mp3` / `pdf` |
| `max_retries` | int | `3` | 最大重试次数 |
| `timeout` | int | `300` | 超时时间（秒） |
| `enable_degradation` | boolean | `true` | 是否允许降级保存 |
| `cookies` | string | `null` | 登录态 Cookie（如果有） |
| `extra_params` | object | `{}` | 平台专属扩展参数，调度器不解析，透传 |

### 2.3 输入示例

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "platform": "bilibili",
  "download_dir": "/tmp/downloads",
  "quality": "high",
  "max_retries": 3,
  "enable_degradation": true
}
```

---

## 三、输出结果（平台 Skill → 调度器）

### 3.1 顶层结构

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `resource_id` | string | ✅ | 资源唯一 ID |
| `platform` | string | ✅ | 平台标识 |
| `download_status` | string | ✅ | 下载状态：`success` / `degraded` / `failed` |
| `degraded_level` | string | ❌ | 降级级别：`Level 0` / `Level 1` / `Level 2` / `Level 3`（成功时为 Level 0） |
| `fetch_method` | string | ✅ | 使用的下载方法：`direct` / `yt_dlp` / `wget` / `api` / `scrape` / `other` |
| `fetch_time` | string | ✅ | 下载完成时间（ISO 格式） |
| `error` | object | ❌ | 下载失败或降级时的错误信息 |

### 3.2 成功时的额外字段（download_status = success）

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file_path` | string | ✅ | 本地文件完整路径 |
| `file_name` | string | ✅ | 文件名 |
| `file_size` | number | ✅ | 文件大小（字节） |
| `file_format` | string | ✅ | 文件格式，如 `mp4` / `mp3` / `pdf` |
| `duration` | number | ❌ | 时长（秒），视频/音频类 |
| `resolution` | string | ❌ | 分辨率，视频类，如 `1920x1080` |
| `bitrate` | number | ❌ | 比特率，音频类 |
| `checksum` | string | ❌ | 文件校验和（MD5 或 SHA256） |

### 3.3 降级时的额外字段（download_status = degraded）

> 注意：v10.1 将原 `partial` 状态合并入 `degraded`，用 `degraded_level` 和 `degraded_content` 区分具体降级形式。

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `degraded_level` | string | ✅ | 降级级别：`Level 1` / `Level 2` / `Level 3` |
| `degraded_content` | object | ✅ | 降级保存的内容（见下方子结构） |
| `degraded_reason` | string | ✅ | 降级的原因 |

**degraded_content 子结构**：

| 降级级别 | 包含字段 | 说明 |
|---------|---------|------|
| Level 1（预览版） | `preview_file_path` / `preview_file_size` / `preview_note` | 低清晰度/部分章节的预览版本 |
| Level 2（核心摘要） | `title` / `description` / `outline` / `key_points` / `duration` | 目录、简介、核心要点 |
| Level 3（来源链接） | `title` / `source_url` / `description` / `source_name` | 只保存标题、链接、简介 |

### 3.4 失败时的额外字段（download_status = failed）

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `error` | object | ✅ | 错误信息（见错误返回章节） |
| `can_retry` | boolean | ✅ | 是否可以重试 |
| `suggested_action` | string | ❌ | 建议的下一步动作 |
| `alternative_resources` | array | ❌ | 同主题的替代资源推荐（可选） |

---

## 四、四级降级体系

| 级别 | 名称 | 说明 | 信息完整度 | 典型场景 |
|------|------|------|-----------|---------|
| Level 0 | 完整版本 | 原始文件完整下载 | 100% | 直链文件、普通视频 |
| Level 1 | 预览版本 | 预览版/低清晰度/部分章节 | 60-80% | 只能下到 720p、只能下前 5 集 |
| Level 2 | 核心摘要 | 目录、简介、核心要点 | 20-40% | 无法下载，但能提取正文和目录 |
| Level 3 | 来源链接 | 只保存标题、链接、简介 | 5-10% | 完全无法下载，只能存个链接 |

**降级原则**：
1. 能拿完整不拿摘要，能拿原文件不拿转换格式
2. 降级内容必须明确标注「非完整版本」
3. 部分可用也输出，不直接放弃
4. 所有降级都必须说明降级原因

---

## 五、错误返回规范

下载失败或降级时，返回 error 对象：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `error_code` | string | ✅ | 统一错误码，见 error-codes.md |
| `error_message` | string | ✅ | 人类可读的错误描述 |
| `can_retry` | boolean | ✅ | 是否可以重试 |
| `suggested_action` | string | ❌ | 建议的下一步动作 |
| `error_details` | object | ❌ | 详细错误信息（平台专属） |

### 常见错误码参考

| 错误码 | 说明 | 是否可重试 | 建议处理 |
|--------|------|-----------|---------|
| `NETWORK_TIMEOUT` | 网络超时 | ✅ | 重试，增加延时 |
| `NETWORK_CONNECTION_FAILED` | 连接失败 | ✅ | 重试，检查网络 |
| `ANTI_CRAWL_RATE_LIMITED` | 频率限制 | ✅ | 等待后重试，降低频率 |
| `ANTI_CRAWL_BLOCKED` | 被拦截 | ⚠️ | 换策略后重试 1 次 |
| `AUTH_LOGIN_REQUIRED` | 需要登录 | ❌ | 提示用户登录 |
| `AUTH_PERMISSION_DENIED` | 权限不足 | ❌ | 降级处理 |
| `CONTENT_PREMIUM_ONLY` | 付费/会员专享 | ❌ | 降级处理 |
| `CONTENT_NOT_FOUND` | 内容不存在/已删除 | ❌ | 直接放弃 |
| `CONTENT_DRM_PROTECTED` | DRM 保护 | ❌ | 降级处理 |
| `DOWNLOAD_PARTIAL` | 部分下载 | ✅ | 断点续传重试 |
| `DOWNLOAD_FILE_CORRUPTED` | 文件损坏 | ✅ | 重新下载 |

> 完整错误码列表见 `error-codes.md`

---

## 六、输出示例

### 6.1 成功示例

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "platform": "bilibili",
  "download_status": "success",
  "degraded_level": "Level 0",
  "fetch_method": "yt_dlp",
  "fetch_time": "2026-06-24T15:30:00Z",
  "file_path": "/downloads/小学必背古诗文动画.mp4",
  "file_name": "小学必背古诗文动画.mp4",
  "file_size": 524288000,
  "file_format": "mp4",
  "duration": 4560,
  "resolution": "1920x1080"
}
```

### 6.2 降级示例（Level 2）

```json
{
  "resource_id": "baiduwenku:xxx123",
  "platform": "baiduwenku",
  "download_status": "degraded",
  "degraded_level": "Level 2",
  "fetch_method": "scrape",
  "fetch_time": "2026-06-24T15:30:00Z",
  "degraded_reason": "付费文档，无法下载原文件",
  "degraded_content": {
    "title": "小学三年级数学四则混合运算课件",
    "description": "人教版小学三年级数学四则混合运算教学课件，共25页...",
    "outline": ["一、运算顺序", "二、例题讲解", "三、课堂练习", "四、课后作业"],
    "key_points": ["先乘除后加减", "有括号先算括号里的", "同级运算从左到右"],
    "page_count": 25
  },
  "error": {
    "error_code": "CONTENT_PREMIUM_ONLY",
    "error_message": "该文档为付费内容，无法下载原文件",
    "can_retry": false,
    "suggested_action": "已降级保存为摘要，可考虑寻找免费替代资源"
  }
}
```

### 6.3 失败示例

```json
{
  "resource_id": "bilibili:BV1xx411c7mD",
  "platform": "bilibili",
  "download_status": "failed",
  "fetch_method": "yt_dlp",
  "fetch_time": "2026-06-24T15:30:00Z",
  "can_retry": false,
  "suggested_action": "内容已删除，建议选择其他资源",
  "error": {
    "error_code": "CONTENT_NOT_FOUND",
    "error_message": "视频不存在或已被删除",
    "can_retry": false
  },
  "alternative_resources": [
    {
      "title": "小学必背古诗动画（另一个版本）",
      "source_url": "https://www.bilibili.com/video/BV1yy...",
      "quality_level": "A"
    }
  ]
}
```

---

## 七、重试策略参考

平台 skill 内部应根据错误类型自动重试，参考策略：

| 错误类型 | 最大重试次数 | 初始延时 | 递增方式 |
|---------|-------------|---------|---------|
| 网络超时/连接失败 | 3 次 | 1 秒 | 指数递增（1s → 3s → 9s） |
| 频率限制（反爬） | 2 次 | 10 秒 | 线性递增（10s → 20s） |
| 部分下载/文件损坏 | 2 次 | 0 秒 | 立即重试（断点续传） |
| 内容为空/不完整 | 1 次 | 2 秒 | 固定延时 |
| 反爬拦截（验证码等） | 1 次 | 5 秒 | 换策略后重试 |
| 付费/DRM/权限不足 | 0 次 | - | 直接降级，不重试 |
| 内容已删除/不存在 | 0 次 | - | 直接放弃，不重试 |

> **注意**：这是平台 skill 内部的重试策略。调度器层面可能还有一层重试，两者不要叠加太多次。

---

## 八、注意事项

1. **文件命名**：文件名尽量使用中文标题，便于用户识别，注意处理特殊字符
2. **路径规范**：返回的 file_path 必须是绝对路径
3. **临时文件**：下载过程中的临时文件不要放在最终目录里
4. **断点续传**：支持断点续传的平台，下载中断后应支持续传
5. **校验完整性**：下载完成后尽量校验文件完整性（大小、校验和等）
6. **降级标注**：所有降级内容必须明确标注降级级别和原因
7. **错误码统一**：所有错误必须使用统一错误码，见 error-codes.md
8. **不破解付费墙**：不得破解付费墙、绕过登录授权、规避 DRM
9. **资源释放**：下载完成后及时释放连接、关闭文件句柄
10. **进度反馈**：长时间下载应支持进度回调（可选，后续扩展）

---

---
