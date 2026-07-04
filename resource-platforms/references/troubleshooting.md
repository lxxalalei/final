# 排障速查

## 凭证问题

`AUTH_REQUIRED` 通常表示缺少登录态、Cookie 失效或平台返回登录页。

处理：

- 复制 `platform-search/.env.example` 为 `.env`。
- 填入平台注册表中声明的 `auth_any_env` 或平台文档要求的变量。
- Cookie 文件路径使用绝对路径更稳。
- 微博 Cookie 需要包含 `SUB`。

## 依赖问题

`SYSTEM_DEPENDENCY_MISSING` 表示缺少平台声明的 Python 模块。

处理：

```bash
python -m pip install f2
```

其他平台如未声明 `python_all`，通常不需要额外安装。

## 网络与验证

`NETWORK_TIMEOUT`、`NETWORK_ERROR`、`SEARCH_BLOCKED`、`SEARCH_RATE_LIMITED` 常见于搜索引擎验证、平台风控、网络不稳定或请求过快。

处理：

- 降低 `--max-concurrency`。
- 减小 `--limit`。
- 等待后重试。
- 为搜索引擎补充可选 Cookie。
- 使用更窄的 `engines`，避免全引擎同时触发限制。
- Anna's Archive 可尝试 `base_url`、`auto_base_url=true` 或 `fallback=always`，但只返回可解析的详情页链接。

## 空结果

空结果不一定是失败，可能是查询过窄、平台页面结构变化、接口降级或引擎没有贡献结果。

处理：

- 先用 `generic` 的 `web` 预设确认公开网页能找到方向。
- 对开源/代码仓库资源使用 `engines=dev`。
- 对中文网页使用 `engines=china`。
- 对国际网页和语义补充使用 `engines=global`。
- Anna's Archive 返回 `SEARCH_NO_RESULTS` 时，表示直连和公开搜索兜底都没有拿到可解析详情页。

## 调试命令

```bash
python scripts/search_cli.py list --pretty
python scripts/search_cli.py doctor --pretty
python scripts/search_cli.py platform generic "初中物理 电学实验" --limit 5 --param engines=web --pretty
```
