# Bilibili 平台

## 平台概况

- **域名**: bilibili.com
- **资源类型**: 视频、课程、科普、教育类UP主内容
- **目标用户**: 全年龄段
- **授权要求**: 搜索/排行/详情无需登录；字幕/收藏需登录
- **权威级别**: 创作者内容 — 质量因UP主而异

## 双引擎架构

| 引擎 | 脚本 | 擅长 | 依赖 |
|------|------|------|------|
| **bilibili-api** (推荐) | `bili_api.py` | 搜索、视频信息、字幕、排行榜、UP主列表 | `pip install bilibili-api-python httpx` |
| **CDP 下载器** | `bilibili_dl.py` | 视频文件下载（ffmpeg 合并 MP4） | CDP 浏览器(9222) / Playwright + ffmpeg |

**选择策略**：
- 搜索 → **bili_api.py**（无需浏览器，直接 API，速度快）
- 视频下载 → **bilibili_dl.py**（CDP 方式更稳定）
- 字幕 → **bili_api.py**
- 无 CDP 环境时 → 全部用 **bili_api.py**

## 标准接口

接口契约详见 `../schemas/platform-search-contract.md`（搜索）和 `../schemas/platform-download-contract.md`（下载）。

### search(intent) → candidates

#### 方法 A（推荐）：bilibili-api 搜索

**无需浏览器，直接 API 调用。**

```bash
python3 scripts/bilibili/bili_api.py search \
  "小学数学" --max 10 -o results.json
```

输出标准 `learning-resource-candidate/v1` 格式 JSON。

#### 方法 B：CDP 浏览器搜索（WBI 签名）

独立 headless 模式搜索返回空结果（B站 TLS 指纹检测），需通过 CDP 浏览器：

```bash
python3 scripts/bilibili/bilibili_dl.py search \
  "小学数学" --max-pages 2 -o results.json
```

### download(candidate) → result

视频文件下载（需 CDP 浏览器或 Playwright + ffmpeg）：

```bash
# 单个视频
python3 scripts/bilibili/bilibili_dl.py download BV1xxx -o ./downloads/

# 批量下载
python3 scripts/bilibili/bilibili_dl.py batch list.json -o ./downloads/

# UP主全部视频
python3 scripts/bilibili/bilibili_user_dl.py <空间URL或UID> -o ./downloads/
```

## bili_api.py 能力清单

```bash
# 搜索视频（无需登录）
python3 scripts/bilibili/bili_api.py search "小学数学" --max 10

# 视频详情
python3 scripts/bilibili/bili_api.py video BV1xxx

# 字幕获取（plain / srt 格式，部分视频需登录）
python3 scripts/bilibili/bili_api.py subtitle BV1xxx --format srt -o sub.srt

# 全站排行榜
python3 scripts/bilibili/bili_api.py rank --max 10

# UP主视频列表
python3 scripts/bilibili/bili_api.py user-videos 946974 --max 10
```

## 全部可用命令

### bili_api.py（bilibili-api-python 直调）

| 命令 | 用途 | 需登录 |
|------|------|--------|
| `search <keyword>` | 搜索视频 → 标准候选 JSON | 否 |
| `video <bvid>` | 视频详情（标题/UP主/播放量/标签） | 否 |
| `subtitle <bvid>` | 字幕获取（plain/srt） | 部分 |
| `rank` | 全站排行榜 | 否 |
| `user-videos <uid>` | UP主视频列表 | 否 |

### bilibili_dl.py（CDP 下载器）

| 命令 | 用途 | 需登录 |
|------|------|--------|
| `search <keyword>` | 搜索（WBI 签名 + CDP） | 否 |
| `download <bvid>` | 下载视频 → MP4 | 否 |
| `batch <list.json>` | 批量下载 | 否 |

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 教学视频 | 教学、讲解、课程、课堂、老师 |
| 科普视频 | 科普、百科、知识、原理、实验 |
| 儿歌/动画 | 儿歌、童谣、动画、启蒙、学龄前 |

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| `bilibili-api-python` | API 直调（搜索/信息/字幕/排行） | `pip install bilibili-api-python` |
| `httpx` | bilibili-api 的 HTTP 后端 | `pip install httpx` |
| ffmpeg | 视频合并（bilibili_dl.py） | 系统安装 |
| Playwright + CDP | 浏览器模式（bilibili_dl.py） | `pip install playwright` |

## 质量自评维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 播放量 | 40% | 500万+ S级，100万+ A级，10万+ B级 |
| 视频时长 | 25% | 30分钟以上系统课程加分 |
| 互动数据 | 15% | 弹幕数、评论数 |
| 制作质量 | 20% | 综合评估（画质、剪辑、字幕） |

## 主题分类推断

根据搜索关键词和视频标题/标签推断资源所属品类：

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

## 关键原则

1. **搜索优先用 bili_api.py** — 无需浏览器，直接 API，速度快
2. **视频下载用 CDP 方式** — ffmpeg 合并质量更可控
3. **脚本不可用时标记跳过** — 不阻塞其他平台

---

*文档版本：v1.0（resource-platforms 独立版）*
