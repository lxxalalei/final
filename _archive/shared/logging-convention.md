# 日志使用规范（Logging Convention）

> **权威文档**：本文档是全系统唯一的日志规范，所有平台脚本和共享模块
> 必须遵守。实现见 `shared/logger.py`。

---

## 1. 统一日志格式

所有日志输出采用统一格式：

```
[时间] [级别] [模块] 消息内容
```

对应 logging.Formatter：

```
[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s
```

- **时间**：`%Y-%m-%d %H:%M:%S`（完整日期时间）
- **级别**：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`
- **模块**：`platform.<平台名>`（如 `platform.bilibili`、`platform.smartedu`）
- **消息内容**：具体描述，支持 `%s`/`%d` 等惰性格式化

### 示例输出

```
[2026-06-25 14:30:15] [INFO] [platform.bilibili] 搜索第 1 页...
[2026-06-25 14:30:18] [WARNING] [platform.bilibili] CDP 端口 9222 不可用 → 独立模式
[2026-06-25 14:30:22] [ERROR] [platform.douyin] [f2] API 错误: ABogus 签名过期
```

---

## 2. 日志级别使用规范

### DEBUG — 调试信息

**用途**：开发调试时需要的详细信息，生产环境默认关闭。

| 场景 | 示例 |
|------|------|
| 内部变量值 | `log.debug("WBI keys: mixin=%s, img=%s", mixin_key, img_key)` |
| 请求详情 | `log.debug("API 请求: url=%s, params=%s", url, params)` |
| 解析中间结果 | `log.debug("解析到 %d 个候选（去重前 %d）", after, before)` |
| Token 生成细节 | `log.debug("ttwid 已生成（前8位=%s）", ttwid[:8])` |

### INFO — 正常流程

**用途**：关键业务流程节点，帮助用户了解系统正在做什么。

| 场景 | 示例 |
|------|------|
| 流程启动 | `log.info("开始搜索: '%s' (max=%d)", keyword, max_results)` |
| 搜索完成 | `log.info("搜索 API 返回 %d 条候选", len(candidates))` |
| 下载开始 | `log.info("开始下载: %s → %s", url, output_path)` |
| 下载完成 | `log.info("下载完成: %s (%.1f MB)", filename, size_mb)` |
| 配置加载 | `log.info("配置加载完成: level=%s, output=%s", level, output)` |
| WBI 签名成功 | `log.info("WBI 密钥获取成功")` |

### WARNING — 降级 / 可恢复异常

**用途**：系统遇到问题但已自动恢复或降级处理，流程继续。

| 场景 | 示例 |
|------|------|
| 降级模式切换 | `log.warning("CDP 不可用 → 独立 stealth 模式")` |
| API 限流退避 | `log.warning("API 返回 412，等待 %.0fs 重试", wait)` |
| Token 获取失败但有降级 | `log.warning("msToken 获取失败，使用伪造版: %s", e)` |
| 签名过期降级 | `log.warning("[f2] 签名过期，降级到 CDP...")` |
| 页面抓取失败但可兜底 | `log.warning("页面抓取失败，降级搜索引擎兜底...")` |
| 连续空页 | `log.warning("连续 %d 页无数据，停止翻页", count)` |

### ERROR — 操作失败

**用途**：单个操作失败，流程继续（如批量下载中某条失败）。

| 场景 | 示例 |
|------|------|
| 单条下载失败 | `log.error("下载失败 (已重试 %d 次): %s", retries, e)` |
| API 请求异常 | `log.error("搜索 API 请求失败: %s", exc)` |
| 文件写入失败 | `log.error("文件写入失败: %s → %s", path, e)` |
| Cookie 过期 | `log.error("Cookie 已过期，分页中断")` |
| 解析错误 | `log.error("JSON 解析失败: %s", raw_text[:200])` |

### CRITICAL — 系统级故障

**用途**：核心依赖缺失或系统级故障，流程必须终止。

| 场景 | 示例 |
|------|------|
| 熔断触发 | `log.critical("连续失败 %d 次，断路器熔断！", fails)` |
| 核心依赖缺失 | `log.critical("缺少依赖: pip install f2 gmssl")` |
| 配置加载失败 | `log.critical("配置文件解析失败，无法启动")` |
| 凭证完全缺失 | `log.critical("所有认证方式均不可用，无法执行操作")` |

---

## 3. 敏感信息脱敏

### 自动脱敏

`shared/logger.py` 中的 `SanitizingFilter` 会自动检测并遮掩以下字段：

| 字段类型 | 示例 |
|----------|------|
| 通用 | `cookie`、`token`、`password`、`secret`、`api_key`、`authorization` |
| B站 | `SESSDATA`、`bili_jct`、`DedeUserID` |
| 微博 | `SUB`、`SUBP`、`sslvk` |
| 知乎 | `z_c0`、`d_c0` |
| 抖音 | `ttwid`、`msToken`、`webid` |
| smartedu | `access-token`、`ndvideo-key` |
| 通用 Token | `access_token`、`refresh_token`、`session_id` |

脱敏效果：

```
输入: Cookie: SESSDATA=abc123def456
输出: Cookie: ***REDACTED***

输入: token="secret_token_value"
输出: token="***REDACTED***"

输入: Authorization: Bearer xxx
输出: Authorization: ***REDACTED***
```

### 手动脱敏

在非 logging 场景（如写入文件、构建 stdout JSON）中使用 `sanitize()` 函数：

```python
from shared.logger import sanitize

safe_text = sanitize(f"配置内容: cookie={raw_cookie}")
```

### 最佳实践

- **永远不要**手动输出完整 Cookie/Token 值
- 需要确认 Token 是否存在时，只记录前几位：`log.info("ttwid: ...%s", ttwid[-8:])`
- 敏感信息通过环境变量或 `credentials.json` 传递，不写入日志

---

## 4. 日志轮转配置

### 配置位置

`config/settings.yaml` 的 `log` 段：

```yaml
log:
  level: INFO                    # DEBUG / INFO / WARNING / ERROR
  output: stderr                 # stderr / file / both
  file_path: ./logs/lrs.log      # 日志文件路径
  max_size_mb: 10                # 按大小轮转：单文件最大大小
  backup_count: 5                # 保留的轮转文件份数
  rotate_by: size                # size（按大小）/ time（按日期）
  rotate_when: midnight          # 按日期轮转时：midnight / h / d
  format: "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
  datefmt: "%Y-%m-%d %H:%M:%S"
```

### 环境变量覆盖

通过 `LRS_LOG__*` 前缀的环境变量覆盖（由 `config_loader.py` 处理）：

```bash
LRS_LOG__LEVEL=DEBUG              # 设置日志级别
LRS_LOG__OUTPUT=both              # 同时输出到 stderr 和文件
LRS_LOG__FILE_PATH=/var/log/lrs.log
LRS_LOG__MAX_SIZE_MB=50           # 50MB 轮转
LRS_LOG__BACKUP_COUNT=10          # 保留 10 份
LRS_LOG__ROTATE_BY=time           # 按日期轮转
```

### 轮转策略

| 策略 | 配置 | 适用场景 |
|------|------|----------|
| 按大小（默认） | `rotate_by: size`, `max_size_mb: 10` | 控制磁盘占用 |
| 按日期 | `rotate_by: time`, `rotate_when: midnight` | 按天归档，便于审计 |

轮转文件命名：
- 按大小：`lrs.log` → `lrs.log.1` → `lrs.log.2` → ...
- 按日期：`lrs.log` → `lrs.log.2026-06-25` → ...

---

## 5. 平台脚本迁移指南

### 必须替换的模式

所有平台 `scripts/` 下的 Python 脚本，必须将以下模式替换为统一日志接口：

| 旧模式 | 新模式 | 说明 |
|--------|--------|------|
| `print("诊断消息")` | `log.info("诊断消息")` | 诊断/状态消息 |
| `print("[ERROR] ...")` | `log.error("...")` | 错误消息 |
| `print("[WARN] ...")` | `log.warning("...")` | 警告消息 |
| `print("...", file=sys.stderr)` | `log.error/info("...")` | stderr 诊断 |
| `import logging` + 直接调用 | `from shared.logger import getLogger` | 统一入口 |

### 保留的模式

以下 `print()` 调用**不替换**（它们是 stdout 管道输出或 CLI 用户界面）：

| 保留模式 | 原因 |
|----------|------|
| `print(json.dumps(result))` | stdout JSON 结果输出（契约管道） |
| `print(output)` | stdout JSON 结果输出 |
| `print("...", file=sys.stderr)` 且为 CLI 交互提示 | 直接面向终端用户的交互提示 |
| argparse 的 `--help` 输出 | 框架标准行为 |

### 迁移步骤

1. 在文件头部添加导入（如尚未有）：
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
   from shared.logger import getLogger
   log = getLogger("<平台名>")
   ```

2. 将 `print("[ERROR] xxx")` → `log.error("xxx")`
3. 将 `print("[WARN] xxx")` → `log.warning("xxx")`
4. 将 `print("[INFO] xxx")` → `log.info("xxx")`
5. 将诊断性 `print("xxx", file=sys.stderr)` → 适当级别的 `log.xxx("xxx")`
6. 保留 `print(json.dumps(...))` 和 `print(output)`（stdout JSON 管道）

### 级别映射速查

| 原始消息特征 | 目标级别 |
|-------------|----------|
| `❌` / `[ERROR]` / `失败` / `无法` | `ERROR` |
| `⚠️` / `[WARN]` / `警告` / `降级` | `WARNING` |
| `✅` / `完成` / `成功` / `开始` | `INFO` |
| `📋` / `📁` / `🔍` / `进度` | `INFO` |
| `🚨` / `熔断` / `严重` | `CRITICAL` |
| 详细变量/调试 | `DEBUG` |

---

## 6. 获取 Logger 的标准方式

```python
# 平台脚本中（推荐）
from shared.logger import getLogger
log = getLogger("bilibili")    # → platform.bilibili

# 共享模块中
from shared.logger import getLogger
log = getLogger("dedup")       # → platform.dedup
log = getLogger("config")      # → platform.config
```

所有日志输出到 **stderr**，不影响 stdout 上的 JSON 结果管道。
