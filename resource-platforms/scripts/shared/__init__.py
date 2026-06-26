"""shared — 全系统共享的 Python 工具包。

包含平台脚本所需的通用工具：
- utils.safe_filename — 安全文件名生成
- logger.getLogger — 统一日志
- wbi_sign — B站 WBI 签名
- platform_base — 平台 Skill 基类（CLIBasedPlatformSkill）
- config_loader — 统一配置加载器（ConfigLoader / get_config）
- dedup — 跨平台内容级去重引擎（DedupEngine / DedupConfig）
"""
