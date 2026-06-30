# SmartEdu 智慧教育平台

## 平台概况

- **域名**: basic.smartedu.cn
- **资源类型**: 教材、课件、视频（m3u8）、音频、习题、教案、白板、字幕
- **目标用户**: K12 学龄儿童（6-18 岁）
- **授权要求**: 搜索不需要授权；源文件下载需要 Access Token
- **权威级别**: 官方 — 国家级教育平台

## 搜索命令

```bash
python3 scripts/smartedu/smartedu_resources.py search-resources \
  --query "三年级 数学 上册 人教版" \
  --max 12 \
  -o results.json
```

**可选参数**:
- `--task-json task.json` — 从任务 JSON 读取 filters（grade/subject/version 等）
- `--fetch-details` — 对候选继续追踪详情 JSON 并解析文件项
- `--deep-search` — 突破 200 条硬限制，多维度交叉搜索
- `--cross-tenant` — 允许跨租户搜索（默认开启）
- `--access-token <token>` — SmartEdu access token（或环境变量 `SMARTEDU_ACCESS_TOKEN`）

## 搜索 API

- **端点**: `https://x-search.ykt.eduyun.cn/v1/resources/combine/search`
- **请求头**: `sdp-app-id` + `Origin` + `Referer` + 浏览器 `User-Agent`
- **搜索不需要 `Authorization`** — 公开搜索 API 可直接用
- 标题中的 HTML 高亮标签会被清理，年级/学科/版本/册次/格式/provider 从 tags/extra 中提取

## 输出格式（platform-search-contract）

```json
{
  "platform": "smartedu",
  "query": "三年级数学",
  "results": [
    {
      "resource_id": "smartedu:2746f8d9-197c-29a8-959a-4af35b73003f",
      "title": "义务教育教科书 数学三年级上册",
      "type": "文档",
      "platform": "smartedu",
      "source_url": "https://basic.smartedu.cn/...",
      "source_name": "国家中小学智慧教育平台",
      "quality_level": "S",
      "platform_quality_score": 90,
      "download_feasibility": "未知",
      "description": "人教版 | 三年级 | 上册 | 数学"
    }
  ]
}
```

### 质量评分规则

- 官方资源（official=true）: +30 分
- 可下载格式（pdf/mp4/m3u8）: +10 分
- 元数据完整度: +0~10 分
- 基础分: 50 分
- S(≥85) / A(≥70) / B(≥50) / C(<50)

### 资源类型映射

| 原始格式 | 映射到 type |
|---------|------------|
| `m3u8`、`mp4`、`video/*` | `视频` |
| `mp3`、`wav`、`m4a`、`audio/*` | `音频` |
| `pdf` | `文档` |
| `ppt`、`pptx` | `课件` |
| `doc`、`docx`、`txt` | `文档` |
| `jpg`、`png`、`webp`、`image/*` | `图片` |

## 深度搜索

搜索 API 有硬性限制：单次请求最多返回 200 条（offset + limit ≤ 200）。`--deep-search` 可突破此限制：

| 阶段 | 策略 | 触发条件 |
|------|------|---------|
| Phase 1 | 原始关键词 + 全 tab 自动分页 | 默认 |
| Phase 2 | 按年级细分交叉搜索 | Phase 1 结果 ≥ 180 条 |
| Phase 3 | 按学段 × tab 组合搜索 | Phase 2 结果仍 ≥ 180 条 |

全局去重使用 `resource_id:title` 指纹，确保跨阶段不重复。

## 搜索模块依赖

```
smartedu_resources.py (主入口，命令处理)
    ├── _constants.py     (纯数据，无依赖)
    ├── _text_utils.py    (纯工具，仅依赖标准库)
    ├── _auth_http.py     (传输层，依赖 _text_utils)
    ├── _page_profile.py  (页面分析，依赖 _auth_http)
    ├── _catalog.py       (栏目处理，依赖 _constants, _text_utils)
    ├── _search.py        (搜索域，依赖 _catalog, _constants, _text_utils)
    └── _detail.py        (详情域，依赖 _auth_http, _catalog, _search)
```

依赖方向严格单向：`_detail → _search → _catalog → _constants / _text_utils`，无循环依赖。

> 下载脚本（smartedu_download.py 等）仍在 smartedu/ 目录下，后续迁移到 downloader。

## CDN 认证（搜索相关）

| CDN / 接口 | 主机名 | 认证方式 | 用途 |
|-----------|--------|---------|------|
| 详情 JSON | `s-file-*.ykt.cbern.com.cn` | **裸 GET** | 资源元数据 JSON |
| 搜索 API | `x-search.ykt.eduyun.cn` | `sdp-app-id` + 可选 Authorization | 站内搜索 |

> ⚠️ 详情 JSON (`s-file-*`) 用裸 GET 可成功，加 `Content-Type`/`Origin`/`Referer` 等 header 反而触发 CDN WAF 403

## 凭据管理

| 环境变量 | 用途 | 必需性 |
|---------|------|--------|
| `SMARTEDU_ACCESS_TOKEN` | 详情追踪（可选） | 搜索不需要 |
| `SMARTEDU_COOKIE` | 页面会话凭据 | 部分受限内容需要 |

Token 通过 `.env.local` 自动加载（`load_local_env()`），无需手动 export。

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 教材 | 教材、课本、人教版、苏教版、北师大版 |
| 课件 | 课件、PPT、教案、教学设计 |
| 视频 | 课堂实录、微课、教学视频 |
| 习题 | 练习、习题、试卷、测试 |

## 关键原则

1. **搜索不需要授权** — 公开搜索 API 可直接用
2. **详情追踪可选** — `--fetch-details` 能获取更多文件项信息，但不影响搜索
3. **adapter 非标准覆盖** — 脚本名为 `smartedu_resources.py`（非 `*_search.py`），子命令为 `search-resources`（非 `search`），adapter 显式指定
