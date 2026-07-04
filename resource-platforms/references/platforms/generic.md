# Generic 通用搜索

## 执行入口

- Adapter：`scripts/generic/adapter.py`
- 搜索脚本：`scripts/generic/generic_search.py`
- 第三方依赖：当前入口无强制依赖；推荐环境仍按 registry 安装可选 HTTP/解析依赖，便于后续增强站点解析
- 认证：通常不需要；可选 `BAIDU_COOKIE`、`BING_COOKIE`、`DUCKDUCKGO_COOKIE`、`JINA_API_KEY`、`GITHUB_TOKEN`、`GH_TOKEN`
- 计划参数：`engines`、`preset`、`site`、`site_pack`、`timeout`、`github_sort`、`github_order`

Adapter 把一条查询传给一个或多个通用搜索源。多个引擎并行执行，任一引擎失败不取消其他引擎；最终按规范化 URL 去重，并在合并后截取 `max_results`，不是每个引擎各返回 `max_results`。

`engines` 可直接写列表或逗号分隔字符串：`["bing","duckduckgo","baidu"]`、`"github,bing"`。也可以使用预设：

- `web`：`bing,duckduckgo,baidu`，默认公开网页发现。
- `global`：`duckduckgo,bing,jina`，偏全球网页和语义搜索补充。
- `china`：`baidu,bing`，偏中文网页。
- `dev`：`github,bing,duckduckgo`，偏开源项目、代码仓库和技术资源。
- `all`：`bing,duckduckgo,baidu,jina,github`，广覆盖兜底。

## 搜索路径

- 百度：请求 `https://www.baidu.com/s` 并解析结果页。
- Bing：先解析中文搜索 HTML；无结果或受阻时尝试 RSS 搜索。
- DuckDuckGo：请求 HTML 版本搜索页，解析结果跳转地址。
- Jina：请求 `https://s.jina.ai/` 的搜索接口；有 `JINA_API_KEY` 时带认证，无密钥时按接口可用性降级。
- GitHub：请求公开仓库搜索 API；有 `GITHUB_TOKEN` 或 `GH_TOKEN` 时带认证，主要返回仓库资源。
- `site` 参数会给网页类引擎追加 `site:` 限定，例如 `site=edu.cn`；GitHub 仓库搜索不使用该参数。
- `site_pack` 参数会展开为多站点定向查询；当前可用：`kepu`、`cctv`、`poetry`、`textbook`、`museum`、`library`。多个包可逗号分隔。
- `site_pack=kepu` 会额外解析科普中国站内搜索页、中国数字科技馆 JSearch 接口，并继续用搜索引擎定向发现 `cdstm.cn`、`cibst.cn` 等结果。
- `site_pack=cctv` 会额外解析央视网搜索页，优先返回 `tv.cctv.com`、`news.cctv.com` 等官方链接；搜索引擎定向发现仍作为兜底。
- 其它包当前走搜索引擎定向发现和结果域名硬过滤，后续可按站点公开搜索页或 sitemap 继续增强。
- 过滤搜索引擎自身跳转页，只保留可定位的外部 HTTP(S) 地址。

每条结果提供标题、链接、摘要，以及 `platform_signals.engine` 和该引擎中的排名。GitHub 仓库结果会补充 star、fork、语言、作者和更新时间等平台事实。通用搜索只负责发现，费用、适龄性、可信度和内容完整性留给调用方或人工判断。

## 数量和错误

- 直接脚本默认20条，统一 CLI 使用任务中的 `max_results`。
- CLI把数量限制在1–100。
- 安全验证页返回 `SEARCH_BLOCKED`；限流返回 `SEARCH_RATE_LIMITED`；单引擎失败允许结果和错误同时存在。
- 页面结构变化导致无可解析结果时，不应伪造结果。

## 当前验证状态

离线测试覆盖 Bing、百度、DuckDuckGo、Jina、GitHub 的解析与合并去重。真实网页搜索仍可能受搜索页结构、验证码、限流、网络和凭证影响；执行器应保留部分成功和错误，跑题网页留给后续调用方或人工过滤。
