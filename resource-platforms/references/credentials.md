# 凭证与登录态

## 保存位置

真实凭证只放本地环境变量或 `.env` 文件，不写入任务 JSON、搜索结果或平台文档。

推荐位置：

- `platform-search/.env`：随 skill 独立使用时优先。
- 项目根 `.env`：三个 skill 共用同一套本地凭证时使用。
- 显式 `--env-file <path>`：临时指定其他凭证文件。

模板文件：`platform-search/.env.example`。复制后填入真实值。

## 通用搜索

- `GITHUB_TOKEN` 或 `GH_TOKEN`：GitHub 公共仓库搜索可不填；填入后提高速率限制。
- `JINA_API_KEY`：Jina 可不填；填入后通常有更高限额。
- `BING_COOKIE`、`BAIDU_COOKIE`、`DUCKDUCKGO_COOKIE`：可选，用于降低搜索引擎验证页概率。

## 平台搜索

- Bilibili：`BILIBILI_COOKIE` 或 `BILIBILI_COOKIE_FILE`，公开搜索通常可不填。
- 喜马拉雅：`XIMALAYA_COOKIE`，通常可不填。
- 网易公开课：`OPEN163_COOKIE`，通常可不填。
- Anna's Archive：搜索通常不需要凭证；可用 `ANNAS_BASE_URL` 指定镜像，`ANNAS_AUTO_BASE_URL=true` 自动发现镜像，`ANNAS_FALLBACK` 和 `ANNAS_FALLBACK_ENGINES` 控制公开搜索兜底。
- 国家智慧教育平台：`SMARTEDU_COOKIE`、`SMARTEDU_AUTHORIZATION`、`SMARTEDU_HEADERS` 或 `SMARTEDU_ACCESS_TOKEN`。
- 知乎：`ZHIHU_COOKIE`、`ZHIHU_COOKIE_FILE` 或 `ZHIHU_TOKEN`。优先复制浏览器请求头里的整段 Cookie；直连知乎搜索 API 至少需要 `z_c0` 和 `d_c0`。单独 `z_c0` 会在 `doctor` 中被判定为不完整。
- 抖音：`DOUYIN_COOKIE` 或 `DOUYIN_COOKIE_FILE`，并需要 `f2` 依赖。
- 微博：`WEIBO_COOKIE` 或 `WEIBO_COOKIE_FILE`，Cookie 需要包含 `SUB`。

## 安全约束

- 不提交 `.env`、Cookie 文件或浏览器导出的请求头。
- 不把 Cookie/Token 放进 `params`。
- 不在日志或错误消息里输出完整凭证。
- Cookie 失效时重新登录平台获取，不在代码中硬编码。
