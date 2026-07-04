# 国家中小学智慧教育平台搜索

## 执行入口

- Adapter：`scripts/smartedu/adapter.py`
- 搜索脚本：`scripts/smartedu/smartedu_resources.py search-resources`
- 计划参数：当前只使用关键词和 `max_results`
- Adapter超时：注册表配置90秒

Adapter固定以家长身份调用跨租户资源搜索，只传递查询词和结果上限。站点扫描、栏目画像、教材索引、详情探测等其他子命令是维护工具，不属于统一搜索入口。

## 认证

公开资源可在无登录态下尝试。受限栏目可使用：

- `SMARTEDU_ACCESS_TOKEN`
- `SMARTEDU_COOKIE`
- `SMARTEDU_AUTHORIZATION`
- `SMARTEDU_HEADERS`

脚本还会从项目或当前目录的 `.env.local` 加载这些变量。`SMARTEDU_ACCESS_TOKEN` 会同时作为 `Authorization: Bearer <token>` 和 `accessToken: <token>` 发送；公开搜索接口返回 401/403 时会自动重试一次无认证请求，避免可公开检索的资源被无关认证头拦住。认证值不得写入计划、结果或日志。

## 搜索路径

按顺序尝试三个资源聚合接口：

1. `x-search.ykt.eduyun.cn/v1/resources/combine/search`
2. `resource-gateway.ykt.eduyun.cn/resources/combine/search`
3. `resource-gateway.ykt.eduyun.cn/resources/aggregate`

正常Adapter不启用深度搜索，只取 `--limit max_results`。SmartEdu API单页上限100、offset和limit合计不超过200；深度分页功能只供维护命令显式启用。

## 输出和错误

搜索结果归一化为标题、官方详情页、资源类型、格式、学段、年级、学科、版本、册次、来源和访问量等字段。没有从接口获得的信息不得根据查询词补造。

接口全部失败、认证失效或返回结构变化时由脚本返回失败；Adapter不得降级到下载、教材同步或浏览器抓取流程。

## 当前验证状态

2026-07-02使用本地 `SMARTEDU_ACCESS_TOKEN` 真实搜索“小学古诗”“初中物理 电学实验”“小学英语启蒙”“三年级英语 上册 Unit 1”“一年级数学 认识钟表”成功，统一 Adapter 均返回标准化资源和官方详情页链接。未登录浏览器只能查看课程信息，微课视频、任务单和作业入口会要求登录。
