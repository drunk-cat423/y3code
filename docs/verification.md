# 本次交付的验证记录

日期为 2026-11-17，环境为 Windows 和 Python 3.12.10。

## 已运行

```powershell
python -m unittest discover -s tests -v
python scripts/restore.py --help
python scripts/restore.py --doctor
python scripts/restore.py --with-agent-rules
git diff --cached --check
```

23 项测试全部通过。测试覆盖预览不写文件、目标路径替换、重复运行保持字节、无关字段与密钥保留、冲突时整体拒绝、显式覆盖前备份、测试密钥注入、错误端点及其他认证来源保护、symlink/junction 拒绝、非法 JSON、并发变更检查和 Windows 文本编码差异。

另以仓库中的真实模板在两个独立临时目录恢复，再次执行、注入合成密钥、检查新目录中的渠道及模型配置。测试密钥没有出现在 CLI 输出中。整个测试没有联网调用渠道或模型。

本机只读预览中，六项 T3 文件和三项 Agent 文件均显示 unchanged。doctor 识别到同版本记录、三个已有渠道的凭证存在，以及 Git、Codex、Claude、T3、Ego 和 Cua 的命令路径。没有在本机真实用户目录运行 apply。

发布前私下检查仓库文本不包含源机三个 API 渠道的实际密钥，并扫描常见 token 和私钥模式。公开模板测试检查凭证字段和旧用户绝对路径未导出。扫描通过不代表允许以后直接复制配置文件进 Git。

通过 `git ls-remote` 确认上游存在 tag `v0.1.10-nightly.20261116.4800`。没有下载或核对该 release 的平台安装器。

## 未验证

- 另一台实体电脑的真实安装和首次引导。
- macOS、Linux 的 GUI 与系统权限。
- T3 程序与官方二进制的逐文件一致性。
- 新电脑账号登录、API 密钥有效性、账户余额和模型额度。
- 任何付费推理或跨提供方模型审核任务。

独立用户目录测试验证文件恢复行为，不能替代这些现场检查。
