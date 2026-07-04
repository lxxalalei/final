---
name: resource-platforms
description: 学习资源平台搜索执行层。读取 resource-search 生成的多平台搜索计划，并行调用可用平台及百度、Bing、DuckDuckGo、GitHub、Jina 通用搜索接口，归一化原始结果并写入 Stage 3。用于执行搜索，不负责理解需求、生成关键词、筛选评分或下载资源。
---

# resource-platforms

## 铁律（不可违反）

**Iterate until the output is complete and well-formed. Before declaring done, run a self-check — if any part feels half-baked, keep going.**

输出搜索结果前，自检这份搜索结果真的达标了吗。

## 安装后依赖

用户安装或复制本 skill 后，先在本 skill 目录运行：

```bash
python scripts/install_dependencies.py
```

该脚本会安装 `requirements.txt` 中的 Python 依赖、`package.json` 中的 Node 依赖，并安装 Playwright Chromium。只需要部分依赖时可使用 `--skip-python`、`--skip-node` 或 `--skip-playwright`。

`wechat` 微信公众号搜索依赖 Node.js 和 `cheerio`；缺少时 `doctor` 或搜索执行会返回 `SYSTEM_DEPENDENCY_MISSING`。

## 常用命令

在本 skill 目录下运行：

```bash
python scripts/search_cli.py list --pretty
python scripts/search_cli.py doctor --pretty
python scripts/search_cli.py platform generic "初中物理 电学实验" --limit 5 --param engines=web --pretty
python scripts/search_cli.py platform generic "小学科学 公开课" --limit 5 --param engines=global --param site=edu.cn --pretty
python scripts/search_cli.py platform generic "月亮 为什么会变圆变缺" --limit 5 --param engines=china --param site_pack=kepu --pretty
python scripts/search_cli.py platform generic "汉字 纪录片 儿童" --limit 5 --param engines=china --param site_pack=cctv --pretty
python scripts/search_cli.py platform generic "children learning resources" --limit 5 --param engines=dev --param github_sort=stars --pretty
python scripts/search_cli.py platform anna "calculus" --limit 5 --param content=book --pretty
python scripts/search_cli.py platform wechat "小学语文 阅读理解" --limit 5 --pretty
python scripts/search_cli.py search "初中物理 电学实验" --group learning --limit 5 --pretty
python scripts/search_cli.py run-tasks tasks.json --pretty
```

如果 API Key 或 Cookie 存在本地环境文件中，使用 `--env-file .env`。相对路径会依次查找当前目录、`resource-platforms/.env` 和项目根 `.env`，并自动补读同一查找范围内的 `.env.local`。真实密钥不要提交到仓库，使用 `.env.example` 复制成本地环境文件或直接设置环境变量。

## 任务

把 `{session_dir}/stage2_search_plan.json` 交给统一执行器，生成 `{session_dir}/stage3_search_results.json`。

本 Skill 只负责：

- 根据私有搜索注册表加载平台 adapter。
- 并行执行不同平台的任务。
- 在同一平台内按顺序执行多条查询，避免并发触发限流。
- 让 generic adapter 同时搜索百度、Bing、DuckDuckGo、GitHub 和 Jina（可选）。
- 处理平台超时、失败和部分成功。
- 归一化平台原始字段。
- 合并同平台、同 `resource_id` 的完全重复响应。

不要重新读取 Intent 生成关键词，不做跨平台相似去重、业务过滤、最终质量评分、候选展示或下载。

## 执行

### 方式一：流水线集成

```bash
python3 resource-platforms/scripts/run_search_plan.py \
  {session_dir}/stage2_search_plan.json \
  {session_dir}/stage3_search_results.json
```

### 方式二：独立 CLI

```bash
python3 resource-platforms/scripts/search_cli.py run-tasks {session_dir}/stage2_search_plan.json --pretty
```

执行器读取 `config/search-registry.json`。只有 `status=available` 且 adapter 可加载的平台才能执行；planned 或不可用平台写入结构化错误，不得伪造成零结果。

### 并行规则

1. 不同平台使用独立 worker 并行执行，并由注册表的 `max_concurrency` 限制总并发。
2. 同一平台的 `searches[]` 默认串行。
3. generic 内部并行请求多个搜索引擎（百度/Bing/DuckDuckGo/GitHub/Jina），再按规范化 URL 合并。
4. 单个平台失败不得取消其他 worker。
5. 并发触发风控的平台，在第一轮失败后自动串行重试一次。
6. 所有 worker 完成或超时后一次性原子写入 Stage 3。

### Adapter 规则

每个 available 平台必须由注册表指向一个 `adapter.py`，模块导出 `ADAPTER`，并实现：

```python
search(query: str, max_results: int, params: dict) -> {
    "results": [...],
    "error": None
}
```

adapter 负责把统一参数转换为平台真实调用，并把平台响应转换为公共搜索资源。认证只能从运行环境、配置或浏览器会话读取，不能写入搜索计划、结果或日志。

Cookie、Token、浏览器状态路径和 CDP 地址只使用注册表及平台文档声明的环境变量。不得把认证信息放进 `searches[].params` 或命令行中的明文参数。缺少依赖或必需认证时，必须在联网前返回结构化错误。

## 当前支持的平台

| 平台 | 状态 | 认证 | 资源类型 |
|------|------|------|---------|
| generic | available | 可选 | 网页/文档/代码（百度/Bing/DuckDuckGo/GitHub/Jina） |
| bilibili | available | 可选 | 视频 |
| ximalaya | available | 可选 | 音频 |
| smartedu | available | 可选 | 课程/教材/练习 |
| zhihu | available | 必需 | 问答/文章 |
| douyin | available | 必需 | 视频 |
| weibo | available | 必需 | 社交 |
| open163 | available | 可选 | 课程/视频 |
| wechat | available | 可选 | 文章（微信公众号） |
| anna | available | 可选 | 图书/文章（Anna's Archive） |
| baiduwenku | planned | — | — |
| xiaohongshu | planned | — | — |
| cctv | planned | — | — |

## 结果边界

每条有效资源至少提供：

- `resource_id`
- `platform`
- `title`
- `source_url`

类型、简介、作者、时长、费用、语言、封面、下载可行性和平台原生信号只在平台能够确定时输出。未知字段省略，不编造。

平台热度、认证和原生评分只能放入 `platform_signals`，不得输出 Selector 的最终 `quality_score`。

失败调用写入 `data.errors`，包括平台、查询、错误码、说明和是否可重试。只要其他平台有有效结果，Stage 3 仍然可以完成。

## 完成检查

- `_summary.resource_count` 等于 `data.resources` 数量。
- `_summary.failed_platforms` 只包含完全没有成功结果且存在错误的平台。
- 每个计划任务都有结果或错误记录。
- 输出不包含搜索计划改写、跨平台筛选或下载结果。
- 只向 Flow 返回 `_summary` 和输出路径。

## 按需读取

- `config/search-registry.json`：平台状态、adapter、认证方式、超时和平台组。
- `references/search-interface.md`：adapter 与 Stage 3 的搜索数据说明。
- `references/search-errors.md`：搜索错误及重试边界。
- `references/troubleshooting.md`：`AUTH_REQUIRED`、`SEARCH_BLOCKED`、`SEARCH_RATE_LIMITED`、`NETWORK_TIMEOUT` 或空结果时的诊断流程。
- `references/credentials.md`：Cookie、Token、API Key 或登录态配置说明。
- `references/environment.md`：依赖安装和运行环境判断。
- `references/platforms/{platform}.md`：正常批量搜索不预加载。某个平台认证失败、连续空结果、接口或解析异常时，读取对应文件后诊断；测试、修改或新增该平台搜索实现前也必须读取。不要为一个平台的问题加载其他平台文档。

## 新增或更新平台

每个可执行平台都指向一个 adapter 模块，并导出 `ADAPTER.search(query, max_results, params)`。

Adapter 应当：

- 把通用搜索参数转换为平台调用；
- 只从环境变量、配置或运行态读取凭证；
- 把平台输出标准化为资源字典；
- 尽量返回结构化错误，而不是直接抛出异常。
