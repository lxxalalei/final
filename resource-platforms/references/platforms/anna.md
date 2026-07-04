# Anna's Archive 搜索

## 执行入口

- Adapter：`scripts/anna/adapter.py`
- 搜索脚本：`scripts/anna/anna_search.py`
- 第三方依赖：无新增运行依赖，使用 Python 标准库；公开搜索兜底复用本 skill 的 `generic` 搜索模块
- 认证：搜索不需要 API key
- 可选环境变量：`ANNAS_BASE_URL`、`ANNAS_AUTO_BASE_URL`、`ANNAS_FALLBACK`、`ANNAS_FALLBACK_ENGINES`、`BING_COOKIE`、`DUCKDUCKGO_COOKIE`、`JINA_API_KEY`
- 计划参数：`content`、`base_url`、`auto_base_url`、`fallback`、`fallback_engines`、`timeout`

该平台只做 Anna's Archive 元数据搜索，发现图书或论文的详情页、标题、作者、出版方、格式、大小和 MD5 hash。它不下载文件，不调用 fast-download API，不读取 `ANNAS_SECRET_KEY`。

## 参数

- `content=book`：搜索图书，优先请求 Anna 的通用 `/search?q=...`，再尝试 `content=book_any` 备用路径。
- `content=article`：搜索论文，优先请求 `/search?index=articles&q=...`，再尝试 `content=journal` 备用路径；Anna 页面可能混入图书结果，类型以页面元数据再推断。
- `content=all`：同时搜索图书和论文，再按 URL 去重。
- `base_url=annas-archive.gl`：指定 Anna 镜像域名，也可用 `ANNAS_BASE_URL`。
- `auto_base_url=true`：从公开 SLUM 状态页发现可用 Anna 镜像；失败时回退到 `base_url`。
- `fallback=auto`：直连 Anna 被拦或无结果时，限定 Anna 域名执行公开搜索兜底；可设为 `always` 或 `never`。
- `fallback_engines=bing,duckduckgo`：指定兜底搜索引擎；配置 `JINA_API_KEY` 后可加入 `jina`。
- `timeout=30`：HTTP 请求超时秒数。

## 输出

每条结果标准化为：

- `platform=anna`
- `type=图书` 或 `type=论文`
- `title`
- `source_url`：Anna 详情页 `/md5/<hash>`
- `description`：搜索结果摘要
- `author`
- `provider`：出版社、期刊或来源
- `language`
- `thumbnail_url`
- `platform_signals.engine=anna-book_any|anna-journal`
- `platform_signals.rank`
- `raw_metadata.hash`
- `raw_metadata.format`
- `raw_metadata.size`
- `raw_metadata.fallback=generic-public-web`：表示该结果来自公开搜索兜底。

## 错误

- 镜像访问失败、DNS 或证书问题：`NETWORK_ERROR`
- 请求超时：`NETWORK_TIMEOUT`
- 反爬或验证码页面：`SEARCH_BLOCKED`
- 公开搜索兜底无结果：`SEARCH_NO_RESULTS`
- 页面结构变化导致无可解析结果：返回空结果，不伪造资源

下载、正文抽取和归档交给 `resource-archive` 或后续专门能力处理。
