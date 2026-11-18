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

## 2026-11-18 模型配置更新

已将本机 Codex、T3 默认模型和 Sol 角色更新为 `gpt-6.2-sol`，Astra 顾问更新为 `gpt-6.2-astra`。本机原文件已备份，解析比较确认权限、MCP、渠道和其他非目标字段保持不变。

pstack 保留 medium 预算，专项审查新增 Astra 席位，使用范围扩展到复杂方案比较、疑难 Bug 根因假设和关键变更风险。该审查席从 Medium 经预算换算为 Low，必要时可升至 Medium；独立顾问固定 Medium，所有 Astra 入口最高 Medium。Luna、DS 分工保留。

当前会话的配置已读回为官方 Codex `gpt-6.2-sol`、High、Priority。这表示后续运行使用的会话配置，不代表当前正在执行的这一轮已经换用新模型。能力目录列出两个新型号，但本次没有另发模型推理验证。

更新后 23 项恢复测试全部通过，本机只读恢复预览全部 unchanged。
