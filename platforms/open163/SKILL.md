---
name: open163
description: 网易公开课资源站点。负责网易公开课课程搜索（视频/公开课/TED/纪录片），实现平台 Skill 标准搜索接口。下载能力规划中。基于搜索结果页 HTML 解析。
---

# 网易公开课平台

## 平台概况

- **域名**: open.163.com
- **资源类型**: 视频（公开课、TED 演讲、纪录片、名校课程、科普）
- **目标用户**: 高年级儿童及以上（科普、人文历史、纪录片为主）
- **授权要求**: 搜索无需登录（服务端渲染 HTML，直接 requests 解析）；部分付费课需 VIP
- **权威级别**: 平台内容 — 名校课程权威性高，UGC 内容质量因上传者而异

## 标准接口

接口契约详见 `../../shared/schemas/platform-search-contract.md`（搜索）和 `../../shared/schemas/platform-download-contract.md`（下载）。

### search(intent) → candidates ✅ 已实现

**无需登录，无需 Cookie，无需浏览器。** 直接抓取搜索结果页 HTML 并解析。

脚本路径：`platforms/open163/scripts/open163_search.py`

```bash
# 搜索课程
python3 platforms/open163/scripts/open163_search.py search \
  "小学数学" --max 20 -o results.json

# 搜索 TED 演讲
python3 platforms/open163/scripts/open163_search.py search \
  "TED演讲" --max 15

# 搜索科普纪录片
python3 platforms/open163/scripts/open163_search.py search \
  "科普纪录片" --max 10
```

**输出标准 candidate JSON**（符合 platform-search-contract），必填字段：`resource_id`（格式 `open163:{pid}`）/ `title` / `source_url` / `platform`。

### download(candidate) → result 🔲 规划中

下载能力尚未实现。网易公开课视频为 m3u8 流，项目已有 ffmpeg 能力（smartedu 平台验证过），接入成本较低。

当前建议：
- 搜索阶段获取课程的 `pid` 和 `source_url`，用户可直接访问网易公开课网页版观看
- 下载能力规划：解析课程 pid → 获取 m3u8 地址 → ffmpeg 下载（参考开源项目 Open163-Downloader）

---

## 搜索方法

### 搜索接口

**搜索 URL**（服务端渲染）：
```
GET https://open.163.com/newview/search/{关键词}
```

无需任何 API key、签名或认证。搜索结果为完整 HTML 页面，直接解析。

### 解析策略

网易公开课搜索结果页为**服务端渲染 HTML**，每个课程块结构：
```html
<a href="/newview/movie/free?pid=XXX">
  <img src="封面URL" alt="课程标题">
</a>
课程标题文本（搜索词高亮用 _xxx_ 标记）
N课时
N万次播放
```

脚本采用**正则分块提取**策略：
1. 找到所有 `pid=XXX` 链接位置作为锚点
2. 以每个 pid 为分界，截取到下一个 pid 之间的 HTML 片段
3. 在片段中提取封面/标题/课时/播放量

### 搜索参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--max` | 最大返回数 | 20 |
| `--cookie` | 可选 Cookie | 无 |
| `-o` | 输出 JSON 文件路径 | stdout |

### 课程详情页 URL 格式

| 格式 | URL 模板 | 说明 |
|------|---------|------|
| PC 免费课 | `https://open.163.com/newview/movie/free?pid={PID}` | 主流格式 |
| 课程介绍 | `https://open.163.com/newview/movie/courseintro?newurl={NEWURL}` | 课程合集页 |
| 移动端 | `https://c.open.163.com/mob/video.htm?plid={PLID}` | 移动端播放 |

---

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 学科课程 | 小学数学、小学语文、初中英语、高中物理 |
| 科普纪录片 | 科普、纪录片、BBC、NASA、自然 |
| 名校公开课 | 哈佛、耶鲁、斯坦福、清华、北大 |
| TED 演讲 | TED、演讲、TEDx |
| 人文历史 | 历史、哲学、文学、艺术 |
| 通识课程 | 公开课、名校、经典、通识 |

---

## 结果字段映射

从网易公开课 HTML 提取字段映射到统一元数据规范：

| 网易公开课字段 | 统一字段 | 说明 |
|---------------|---------|------|
| `pid` | `resource_id` | 格式：`open163:{pid}` |
| img alt / 标题文本 | `title` | 清理高亮标记 `_xxx_` |
| `href` | `source_url` | 规范化为完整 https 链接 |
| img src | `cover_url` / `thumbnail_url` | 课程封面图 |
| N课时 | `lessons_count` | 课程总课时数 |
| N万次播放 | `play_count` / `view_count` | 播放量（自动解析万/亿单位） |
| 付费标记 | `is_paid` | 是否付费课程 |

---

## 质量评分策略

遵循 `shared/schemas/quality-rubric.md` 评分标准。网易公开课**无评分系统**，主要依据播放量和课时数：

| 维度 | 评分依据 | 加分规则 |
|------|---------|---------|
| 内容质量与完整性 | 课时数 | ≥50(+10) / ≥20(+7) / ≥10(+5) / ≥3(+3) |
| 可获取性 | 免费内容 | 免费(+5) |
| 安全与体验 | 播放量 | 百万(+20) / 十万(+15) / 万(+10) / 千(+5) |

基础分 55，满分 100。等级映射：S(≥85) / A(≥70) / B(≥55) / C(<55)。

> 注意：网易公开课无评分和认证体系，质量分整体低于喜马拉雅（有评分+认证主播），这是平台特性决定的。

---

## 反爬应对

### 平台反爬特点

网易公开课搜索接口**几乎没有反爬**：
- 搜索结果为服务端渲染 HTML，无需 JS 执行
- 无需登录/Cookie/签名
- 无频率限制（合理使用即可）
- 无验证码
- 无 IP 封禁

### 请求规范

- User-Agent：标准浏览器 UA（Chrome 131）
- 请求间隔：无需特别控制（单次请求即可获取全部结果）
- 最大并发：1（单页返回所有结果，无需分页）
- Cookie：可选（无 Cookie 也能完整搜索）

---

## 登录态管理

### 登录方式

**搜索功能无需登录。** 网易公开课搜索是公开页面。

登录仅在以下场景需要：
- 观看付费课程
- 收藏/记录播放历史
- 获取个性化推荐

### 权限分级

| 权限级别 | 可访问内容 | 对应错误码 |
|---------|-----------|-----------|
| 未登录 | 所有公开搜索结果、免费课程视频 | - |
| 已登录 | 上述 + 播放记录、收藏功能 | - |
| VIP 会员 | 上述 + 付费课程 | `AUTH_MEMBER_ONLY`（不破解） |

---

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python 3.10+ | 运行环境 | - |
| `shared.logger` | 统一日志 | 内置（项目共享） |

**无需浏览器、无需 Playwright、无需 ffmpeg（搜索阶段）、无需第三方 HTTP 库。**

---

## 平台优势

> 📖 完整优势分析见 `../../shared/config/platform-advantages.md`

- **纪录片/公开课首选**：BBC 纪录片、TED 演讲、名校公开课
- **质量高**：成体系、有深度，适合高年级科普和人文启蒙
- **免费多**：大量免费课程可直接观看
- **技术友好**：服务端渲染，无反爬，接入成本极低（⭐极易）
- **形态互补**：补齐"纪录片/公开课"形态空白（与 bilibili 的动画视频、喜马拉雅的音频互补）

---

## 参考资料

- `../../shared/schemas/resource-schema.md` - 资源元数据规范
- `../../shared/schemas/error-codes.md` - 统一错误码体系
- `../../shared/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `../../shared/schemas/platform-search-contract.md` - 平台搜索接口契约
- `../../shared/schemas/quality-rubric.md` - 质量评估标准
- `../../shared/config/platform-mapping.md` - 平台-Skill 映射表
- `../../shared/config/platform-advantages.md` - 平台优势图谱

---

*Skill 版本：v1.0（搜索能力）*
*架构版本：三层架构（平台执行层）*
