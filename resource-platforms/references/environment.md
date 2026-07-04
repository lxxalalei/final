# 环境与依赖

## 安装

在 `platform-search` 目录执行：

```bash
python scripts/install_dependencies.py
```

手动安装等价命令：

```bash
python -m pip install -r requirements.txt
npm install
python -m playwright install chromium
```

这些依赖就是当前脚本运行环境。没有安装完整依赖时，对应平台、浏览器会话、签名、解析或下载辅助脚本不可用。

本地凭证和 API Key 可放在当前目录、`platform-search/` 或项目根目录的 `.env` / `.env.local` 中。默认执行时先读取 `--env-file` 指定的文件（默认 `.env`），再补读 `.env.local`；已有环境变量不会被文件覆盖。

## 依赖分层

通用 HTTP、解析和配置：

- `httpx`
- `requests`
- `python-dotenv`
- `lxml`
- `beautifulsoup4`
- `PyYAML`

平台签名、浏览器会话和反自动化兼容：

- `f2`
- `gmssl`
- `playwright`
- `playwright-stealth`

平台 API 辅助：

- `bilibili-api-python`

SmartEdu 与归档链路常用解密兼容依赖：

- `pycryptodome`
- `cryptography`

`platform-search` 只执行搜索；下载、正文抽取、视频合并、Defuddle 等能力归 `resource-archive`。这些依赖仍可放在同一 Python 环境中，便于搜索后直接交给归档 skill 使用。

## Node

`wechat` 微信公众号搜索使用 Node.js 抓取搜狗微信搜索页，并依赖 `cheerio` 解析 HTML。安装：

```bash
cd platform-search
npm install
```

如果只安装 Python 依赖，`wechat` 会在 `doctor` 或执行搜索时返回 `SYSTEM_DEPENDENCY_MISSING`。其它平台仍按各自 registry 声明检查 Python 依赖、浏览器依赖或本地凭证。

## 运行检查

```bash
python scripts/search_cli.py doctor --pretty
python scripts/search_cli.py doctor --platforms generic zhihu douyin smartedu bilibili --pretty
```

`doctor` 会检查：

- 平台声明的 Python 模块是否存在；
- 必需凭证是否至少存在一个；
- 可选凭证哪些已配置、哪些未配置；
- Cookie 内容是否满足平台最低要求。

依赖缺失会返回 `SYSTEM_DEPENDENCY_MISSING`；必需凭证缺失会返回 `AUTH_REQUIRED`。搜索任务本身只携带查询参数，凭证、Cookie、Token 和请求头只从本地环境读取。
