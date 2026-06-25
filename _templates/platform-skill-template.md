---
name: platform-{platform-id}
description: {平台名称}平台专属 Skill，封装该平台的搜索、下载、反爬应对、登录态管理四大能力，由 resource-search 和 resource-downloader 调度调用。
---

# platform-{platform-id} · {平台名称}

> **本文件是创建新 platform skill 的标准模板。**
> 复制本文件到 `platform-{platform-id}/SKILL.md`，将所有 `{占位符}` 替换为实际内容，
> 并删除模板中不适用于该平台的说明段（保留「必须包含」的模块）。

## 概述

本 Skill 是三层架构中的**平台执行层**，封装 {平台名称} 平台的完整能力：
搜索召回、内容下载、反爬应对、登录态管理，全部内聚于本 Skill。

**上游调用方**：
- `resource-search`（搜索调度器）→ 调用搜索模式
- `resource-downloader`（下载调度器）→ 调用下载模式

**不做什么**：
- 不负责跨平台路由（由调度器决定）
- 不负责质量校准（由 search 调度器统一做）
- 不负责用户选择和归档

---

## 平台信息

| 项目 | 说明 |
|------|------|
| **平台标识** | `{platform-id}` |
| **平台名称** | {平台名称} |
| **域名** | {平台域名} |
| **资源类型** | {视频/音频/文档/图文/综合} |
| **Skill 状态** | {规划中/开发中/可用} |
| **优先级** | {P0/P1/P2} |

---

## 必含模块一：🔍 搜索能力

### 搜索入口

{平台搜索的 URL、API 或页面入口}

### 搜索参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| {keyword} | 搜索关键词 | - |
| {sort} | 排序方式 | {平台默认排序} |
| {page} | 分页 | 1 |

### 搜索技巧

1. {该平台特有的搜索技巧，如关键词组合、过滤条件等}
2. {排序策略：儿童内容优先按播放量/热度}
3. {如何识别官方账号/优质 UP 主}

### 结果解析

从搜索结果页提取以下信息（映射到统一元数据）：

| 平台字段 | 统一字段 | 说明 |
|---------|---------|------|
| {标题} | `title` | - |
| {链接} | `source_url` | - |
| {播放量} | `view_count` | - |
| {时长} | `duration` | - |
| {UP主} | `author` | 扩展字段 |

### 搜索输出格式

必须符合统一元数据规范，且必须包含：
- `platform_quality_score`（平台自评质量分 0-100）
- `download_feasibility`（下载可行性预估 高/中/低）

```json
{
  "platform": "{platform-id}",
  "results": [
    {
      "resource_id": "{platform-id}:{平台内ID}",
      "title": "...",
      "platform_quality_score": 85,
      "download_feasibility": "中"
    }
  ]
}
```

---

## 必含模块二：⬇️ 下载能力

### 下载工具

| 工具 | 用途 | 配置要点 |
|------|------|---------|
| {yt-dlp/wget/自定义脚本} | {主下载工具} | {关键参数} |

### 下载流程

1. {第一步：解析资源真实地址}
2. {第二步：选择清晰度/质量}
3. {第三步：执行下载}
4. {第四步：验证文件完整性}

### 质量分级策略

| 优先级 | 策略 | 适用场景 |
|--------|------|---------|
| 默认 | {最佳质量} | 网络好、空间足 |
| 降级1 | {降低清晰度} | Level 1 降级 |
| 降级2 | {提取摘要/字幕} | Level 2 降级 |

### 下载输出格式

必须包含下载状态和降级信息，符合统一规范：

```json
{
  "download_status": "success",
  "degraded_level": "Level 0",
  "file_path": "...",
  "file_size": 1024000,
  "fetch_method": "下载"
}
```

---

## 必含模块三：🛡️ 反爬应对

### 平台反爬特点

{描述该平台的反爬机制：频率限制、验证码、签名校验、IP 封禁等}

### 应对策略

| 反爬类型 | 应对方法 | 对应错误码 |
|---------|---------|-----------|
| 频率限制 | {加延时、降并发} | `ANTI_CRAWL_RATE_LIMITED` |
| 验证码 | {换策略/提示用户} | `ANTI_CRAWL_CAPTCHA` |
| IP 封禁 | {换代理/降级} | `ANTI_CRAWL_IP_BANNED` |

### 请求规范

- User-Agent：{使用的 UA}
- 请求间隔：{建议间隔，如 2-3 秒}
- 最大并发：{如 2}
- Cookie：{是否需要、如何获取}

---

## 必含模块四：🔑 登录态管理

### 登录方式

{描述该平台的登录方式：账号密码、扫码、第三方等}

### Cookie / Token 管理

| 项目 | 说明 |
|------|------|
| 存储位置 | {Cookie 存储路径} |
| 有效期 | {Cookie 有效期} |
| 失效处理 | {检测失效后的流程} |

### 权限分级

| 权限级别 | 可访问内容 | 对应错误码 |
|---------|-----------|-----------|
| 未登录 | {可访问的范围} | - |
| 已登录 | {可访问的范围} | - |
| 会员/VIP | {会员专享内容} | `AUTH_MEMBER_ONLY`（不破解） |

---

## 必须遵守的规范

1. **统一元数据**：输出必须符合 `../shared/schemas/resource-schema.md`
2. **统一错误码**：错误必须返回 `../shared/schemas/error-codes.md` 中的标准码
3. **两级质量评估**：搜索结果必须包含 `platform_quality_score` 和 `download_feasibility`，评分遵循 `../shared/schemas/quality-rubric.md`
4. **上下文契约**：输入输出符合 `../shared/schemas/skill-contract.md`

---

## 参考资料

- `../shared/schemas/resource-schema.md` - 资源元数据规范
- `../shared/schemas/error-codes.md` - 统一错误码体系
- `../shared/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `../shared/config/platform-mapping.md` - 平台-Skill 映射表
- `../shared/config/platform-advantages.md` - 平台优势图谱

---

*Skill 版本：v1.0*
*架构版本：三层架构（平台执行层）*
