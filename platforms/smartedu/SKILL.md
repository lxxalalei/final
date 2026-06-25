---
name: smartedu
description: 国家中小学智慧教育平台资源站点。负责该平台的资源搜索和下载，实现平台 Skill 标准接口。
---

# SmartEdu 智慧教育平台

## 平台概况

- **域名**: basic.smartedu.cn
- **资源类型**: 教材、课件、视频（m3u8）、音频、习题、教案、白板、字幕
- **目标用户**: K12 学龄儿童（6-18 岁）
- **授权要求**: 源文件（PDF 原件、课件、视频等）需要 Access Token；部分资源公开可下载
- **权威级别**: 官方 — 国家级教育平台

## 标准接口实现

接口契约详见 `../../shared/schemas/platform-search-contract.md`（搜索）和 `../../shared/schemas/platform-download-contract.md`（下载）。

### search(intent) → candidates

接收 `resource-search` 广播的 intent 查询，在平台内搜索匹配资源。

**命令**:
```bash
python3 platforms/smartedu/scripts/smartedu_resources.py search-resources \
  --query "三年级 数学 上册 人教版" \
  --limit 12 \
  --output results.json
```

**可选参数**:
- `--task-json task.json` — 从任务 JSON 读取 filters（grade/subject/version 等）
- `--fetch-details` — 对候选继续追踪详情 JSON 并解析文件项
- `--cross-tenant` — 允许跨租户搜索（默认开启）
- `--access-token <token>` — SmartEdu access token（或环境变量 `SMARTEDU_ACCESS_TOKEN`）
- `--cookie <cookie>` — SmartEdu cookie（或环境变量 `SMARTEDU_COOKIE`）

**输出**（符合 platform-search-contract，由 platform_base 标准化层自动转换）：
```json
{
  "resource_id": "smartedu:edu_001",
  "title": "义务教育教科书 数学三年级上册",
  "type": "文档",
  "subject": "数学",
  "platform": "smartedu",
  "source_url": "https://basic.smartedu.cn/...",
  "source_name": "国家中小学智慧教育平台",
  "quality_level": "S",
  "platform_quality_score": 95,
  "download_feasibility": "中",
  "description": "人教版 | 三年级上册 | 可下载"
}
```

**无匹配时**: 返回空列表 `[]`

### download(candidate) → result

SmartEdu 平台有 **三条下载路径**，覆盖所有资源类型。

---

#### 路径 A（推荐）：全资源下载器 `smartedu_download.py`

**一条命令下载课程/教材的所有资源（视频、PDF、音频、图片等）。**

```bash
# 下载精品课全部资源（视频+课件+字幕+图片）
python3 platforms/smartedu/scripts/smartedu_download.py download \
  "https://basic.smartedu.cn/qualityCourse?courseId=xxx"

# 下载教材 PDF
python3 platforms/smartedu/scripts/smartedu_download.py download \
  "https://basic.smartedu.cn/tchMaterial/detail?contentType=assets_document&contentId=xxx"

# 下载同步课堂资源包
python3 platforms/smartedu/scripts/smartedu_download.py download \
  "https://basic.smartedu.cn/syncClassroom/classActivity?activityId=xxx"
```

**支持的 URL 类型**:

| URL 路径 | 资源类型 | 说明 |
|---------|---------|------|
| `/tchMaterial/detail` | 教材 PDF | 需要 `contentType=assets_document` |
| `/qualityCourse` | 精品课 | 视频(m3u8)+课件(PDF)+图片+字幕 |
| `/syncClassroom/classActivity` | 学生自主学习/课程包 | 视频(m3u8)+课件+教学设计 |
| `/syncClassroom/prepare/detail` | 教师备课 | 课件+教学设计 |

**子命令**:

| 子命令 | 用途 |
|-------|------|
| `download <url>` | 下载所有资源 |
| `list <url>` | 列出可用资源（不下载） |
| `formats <url>` | 查看某 URL 的所有可用格式 |

**常用参数**:
```bash
# 指定输出目录
python3 platforms/smartedu/scripts/smartedu_download.py \
  "https://..." --output-dir ./downloads

# 只下载特定格式
python3 platforms/smartedu/scripts/smartedu_download.py download "https://..." --formats pdf,m3u8

# 指定视频下载并发数
python3 platforms/smartedu/scripts/smartedu_download.py download "https://..." --video-concurrency 5

# 查看所有可用格式
python3 platforms/smartedu/scripts/smartedu_download.py formats "https://basic.smartedu.cn/qualityCourse?courseId=xxx"
```

**支持的格式**:

| 格式 | 说明 | 下载方式 |
|------|------|---------|
| `pdf` | PDF 文档（教材、课件、教学设计等） | 直接下载 |
| `m3u8` | HLS 视频（微课、课堂实录） | TS分片+AES解密+合并 |
| `mp3` | MP3 音频（课文朗读） | 直接下载 |
| `ogg` | OGG 音频 | 直接下载 |
| `jpg` | 图片（课件截图、封面） | 直接下载 |
| `whiteboard` | 电子白板 | 直接下载 |
| `srt` | 字幕文件 | 直接下载 |

**Token 配置**（下载源文件时需要）:
```bash
# 方法1：环境变量
export SMARTEDU_ACCESS_TOKEN="你的token"

# 方法2：.env.local 文件（推荐，自动加载）
echo 'SMARTEDU_ACCESS_TOKEN=你的token' > .env.local
```

**获取 Token**:
1. 浏览器打开 https://basic.smartedu.cn 并登录
2. F12 → Network → 找任意 API 请求 → 复制 `access-token` 或 `accessToken` 的值
3. 写入 `.env.local` 或设置环境变量

---

#### 路径 B：教材批量下载 `smartedu_tch_material.py`

适合批量下载某年级某学科的整套教材 PDF。

```bash
# 第一步：同步教材索引（首次运行需要）
python3 platforms/smartedu/scripts/smartedu_tch_material.py \
  --data-dir .smartedu-work/data sync

# 第二步：下载 PDF
python3 platforms/smartedu/scripts/smartedu_tch_material.py \
  --data-dir .smartedu-work/data \
  download-pdfs \
  --grade "三年级" --subject "数学" --version "人教版" --volume "上册" \
  --limit 1 -o .smartedu-work/downloads
```

**⚠️ 授权要求**: 源 PDF 文件存储在 `r*-ndr-private` 私有 CDN，需要 Access Token：
```bash
python3 platforms/smartedu/scripts/smartedu_tch_material.py \
  --data-dir .smartedu-work/data \
  download-pdfs \
  --grade "三年级" --subject "数学" --version "人教版" --volume "上册" \
  --limit 1 -o .smartedu-work/downloads \
  --access-token "你的SMARTEDU_ACCESS_TOKEN"
```

**降级方案**: 无 Token 时可下载预览图片：
```bash
python3 platforms/smartedu/scripts/smartedu_tch_material.py \
  --data-dir .smartedu-work/data \
  download-previews \
  --grade "三年级" --subject "数学" --version "人教版" --volume "上册" \
  --limit 1 -o .smartedu-work/previews
```

---

#### 路径 C：教材候选列表（不下载）

```bash
python3 platforms/smartedu/scripts/smartedu_resources.py \
  textbook-candidates \
  --grade "三年级" --subject "数学" --version "人教版" --volume "上册" \
  --show 10 --output candidates.json
```

只列出匹配的教材候选（含元数据），不执行下载。

## CDN 认证机制

SmartEdu 使用两套 CDN，认证方式不同：

| CDN 类型 | 主机名 | 认证方式 | 用途 |
|---------|--------|---------|------|
| 公开 CDN | `r*-ndr.ykt.cbern.com.cn` | 无需认证 | 部分公开资源 |
| 私有 CDN | `r*-ndr-private.ykt.cbern.com.cn` | `Authorization: Bearer <token>` + `accessToken: <token>` | 源文件（PDF、视频、课件） |
| 详情 JSON | `s-file-*.ykt.cbern.com.cn` | **裸 GET**（不加任何业务 header） | 资源元数据 JSON |
| 视频密钥 | `ndvideo-key.ykt.eduyun.cn` | **裸 GET**（不加任何业务 header） | m3u8 解密密钥交换 |

**关键技术细节**:
- 详情 JSON (`s-file-*`) 用裸 GET 可成功，加 `Content-Type`/`Origin`/`Referer` 等 header 反而触发 CDN WAF 403
- 文件下载（`r*-ndr-private`）必须同时携带 `Authorization: Bearer <token>` 和 `accessToken: <token>` 两个 header
- 视频密钥交换接口（`ndvideo-key`）不能用 auth header，否则 403
- 高并发下载 TS 分片时，单一 CDN 节点可能返回 400 InvalidArgument，需轮换 r1/r2/r3 主机

## 凭据管理

| 环境变量 | 用途 | 必需性 |
|---------|------|--------|
| `SMARTEDU_ACCESS_TOKEN` | 源文件下载授权 | 下载源文件（PDF、视频等）时必需 |
| `SMARTEDU_COOKIE` | 页面会话凭据 | 部分受限内容需要 |
| `SMARTEDU_HEADERS` | 额外请求头 | 高级用途 |

Token 通过 `.env.local` 自动加载（`load_local_env()`），无需手动 export。

会话过期检测：下载返回 403/401 → 标记 `needs_manual_assist`，引导用户重新获取 Token。

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 教材 | 教材、课本、人教版、苏教版、北师大版 |
| 课件 | 课件、PPT、教案、教学设计 |
| 视频 | 课堂实录、微课、教学视频 |
| 习题 | 练习、习题、试卷、测试 |

## 全部可用命令

| 脚本 | 命令 | 用途 |
|------|------|------|
| `smartedu_download.py` | `download <url>` | **全资源下载**（视频/PDF/音频/图片） |
| `smartedu_download.py` | `list <url>` | 列出可用资源（不下载） |
| `smartedu_download.py` | `formats <url>` | 查看所有可用格式 |
| `smartedu_resources.py` | `search-resources` | 搜索平台资源，输出标准候选 |
| `smartedu_resources.py` | `textbook-candidates` | 列出教材候选（不下载） |
| `smartedu_tch_material.py` | `sync` | 同步教材索引 |
| `smartedu_tch_material.py` | `download-pdfs` | 批量下载教材 PDF |
| `smartedu_tch_material.py` | `download-previews` | 下载教材预览图 |
| `smartedu_resources.py` | `site-profile` | 输出站点能力画像 |
| `smartedu_resources.py` | `list-catalogs` | 输出栏目画像 |
| `smartedu_resources.py` | `route-map` | 输出栏目路由图 |
| `smartedu_resources.py` | `site-index` | 输出全站 route 覆盖索引 |
| `smartedu_resources.py` | `page-profile` | 分析页面 HTML/JS 结构 |
| `smartedu_resources.py` | `scan-catalog` | 按栏目扫描资源候选 |
| `smartedu_resources.py` | `scan-site` | 批量扫描多栏目候选 |
| `smartedu_resources.py` | `candidates-from-detail` | 从详情 JSON 输出候选 |
| `smartedu_resources.py` | `detail-probe` | 探测候选能否展开详情 |

## m3u8 视频下载原理

SmartEdu 的视频使用 HLS (m3u8) 格式，流程如下：

1. **获取播放列表** — GET m3u8 URL → 得到 TS 分段列表
2. **密钥交换** — 从 m3u8 中提取 `EXT-X-KEY` URI →
   - GET `{key_url}/signs` → 获得 `nonce`
   - `sign = MD5(nonce + key_id)[:16]`
   - GET `{key_url}?nonce=...&sign=...` → 获得 base64 编码的加密 key
   - AES-ECB 解密（key=sign）→ 得到最终解密 key
3. **并发下载 TS 分片** — 从 r1/r2/r3 主机轮换下载（避免单节点限流）
4. **AES-CBC 解密** — 每个分片用解密 key + IV 解密
5. **合并** — 按顺序合并所有解密后的 TS → 输出 `.ts` 文件（可直接用 VLC/ffmpeg 播放）

## 质量自评维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 官方权威性 | 30% | 国家级官方教材，权威性满分 |
| 内容完整度 | 25% | 课时完整、配套齐全加分 |
| 年级覆盖 | 20% | 覆盖多个年级的加分 |
| 资源类型多样性 | 25% | 视频+课件+练习题全套加分 |

## 主题分类推断

根据搜索关键词和资源标题/标签推断资源所属品类：

| 品类 | 关键词 |
|------|--------|
| 学科同步 | 数学、语文、英语、课本、教材、同步、课堂 |
| 科普启蒙 | 科普、科学、宇宙、恐龙、动物、实验、百科 |
| 人文历史 | 古诗、诗词、国学、论语、历史、成语、绘本 |
| 语言表达 | 英语、单词、口语、听力、拼音、识字、写作 |
| 思维训练 | 思维、逻辑、奥数、编程、scratch、python、益智 |
| 艺术美育 | 画画、美术、音乐、钢琴、舞蹈、书法、手工 |
| 习惯品格 | 习惯、情绪、安全、礼仪、品格、社交、情商 |
| 兴趣拓展 | 棋、围棋、运动、体育、航模、机器人、乐高 |

## 深度搜索

搜索 API 有 200 条硬限制。启用 `--deep-search` 可自动分页 + 多维度交叉，突破限制：

```bash
python3 platforms/smartedu/scripts/smartedu_resources.py \
  search-resources --query "数学" --deep-search --max-results 5000 \
  -o results.json
```

三阶段策略：原始关键词全 tab 分页 → 按年级细分交叉 → 按学段 × tab 组合。

## 关键原则

1. **搜索不需要授权** — 公开搜索 API 可直接用
2. **源文件需要授权** — PDF、视频、课件等需要 Access Token（`Authorization: Bearer` + `accessToken`）
3. **详情 JSON 裸 GET** — `s-file-*` CDN 的 JSON 不能加业务 header，否则 403
4. **视频密钥裸 GET** — `ndvideo-key` 接口不能加 auth header
5. **TS 下载需轮换主机** — 高并发时单一 r* 节点返回 400，需切换 r1/r2/r3
6. **脚本不可用时标记跳过** — 不阻塞其他平台
7. **有授权要求不丢弃** — 标记 `requires_auth` 交由用户决定
8. **详细接口见** `references/smartedu-resource-schema.md`
9. **架构详情见** `references/architecture.md`（模块总览、下载流程图、错误处理策略、CDN 认证机制）
