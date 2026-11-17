# 在新电脑执行恢复

本流程供独立的 Codex 会话执行。读取仓库根目录 AGENTS.md 后再操作。

## 1. 检测环境

确认操作系统、真实用户目录、Python 3.11+、Git、T3 安装和目标 `T3CODE_HOME`。不要输出完整环境变量或配置文件。先检查已安装工具，再决定是否安装。

源机是 Windows。其他系统使用本机官方安装包和路径，不能把 Windows 路径改个前缀就视为完成验收。

T3 的[快照版本发布入口](https://github.com/pingdotgg/t3code/releases/tag/v0.1.10-nightly.20261116.4800)对应 `0.1.10-nightly.20261116.4800`。已通过上游 Git 确认该 tag 存在，未核对各平台安装包资产。优先寻找该版本的适配安装包。若该版本不可获取，明确记录实际版本，核对该版本仍支持 `providerInstances`、Claude 独立 `homePath` 和 `customModels`，再尝试导入。不要凭空拼接安装包 URL、关闭签名检查或静默降级。

通过 Ego Lite 读取发布页面和供应商指引。Ego 未安装时按 [工具指引](tools.md) 安装，无法使用时报告阻塞，不改用其他浏览器。Git 克隆和安装器的官方下载不需要网页控制器。

打开 T3 一次完成必要初始化，再由用户正常退出。若当前 Codex 就运行在需要修改的 T3 中，先准备预览，交给独立的 Codex CLI 或本地终端执行 apply，不终止当前任务。

## 2. 预览和恢复

在仓库根目录执行：

```powershell
python scripts/restore.py --with-agent-rules
```

根据输出核对目标路径、创建项和冲突项。没有冲突且已获本机恢复授权时直接应用：

```powershell
python scripts/restore.py --with-agent-rules --apply
```

JSON 字典逐字段合并，未管理的字段保持原值。数组整体比较，快捷键和模型列表有差异会报告冲突。文本规则文件有差异也会报告冲突。脚本不会打印含凭证的值。

冲突时整体停止，不先写其他文件。由 Codex 读取相关字段，在不输出敏感值的前提下说明需要保留或替换的设置。只有获得替换授权后才使用 `--overwrite`。该选项会保留原文件备份，不代表整份重置配置。不要用它绕过不同渠道端点的密钥保护或 symlink/junction 检查。

应用不是跨文件数据库事务。中途出现系统写入错误时保留现场和备份，先检查已经写入的文件，再按现有状态重新预览。不要盲目删除备份或重置整个目录。

重复执行同一预览。内容一致应显示 unchanged，不能把“命令退出成功”当作全部设置一致。

## 3. 配置模型和工具

`--with-agent-rules` 安装个人规则、模型角色偏好和 pstack 自动入口，不安装 pstack 插件、Ego、Cua Driver，也不修改 Codex 的 `config.toml`。

按 [工具指引](tools.md) 安装并逐项验证。若个人规则已经存在且有不同内容，先合并；不要用另一个仓库的旧规则覆盖本仓库的新模板。

读取 `templates/agent/model-preferences.toml`。如果用户要求匹配源机主模型，检查当前账号支持后，在保留其他设置的前提下合并这三个顶层值。备份原文件，不动权限、代理、MCP 或已存在的具名角色。已有不同模型设置先说明差异；不要让旧角色 TOML 覆盖 pstack 选定的模型和强度。

模型角色偏好只是约定，不是模型路由的技术保证。GPT 走官方 Codex；DS 审核席在 T3 走 `bailian`，不能因缺少密钥而改走 `deepseek_official`。Astra 仅只读且最高 Medium。

## 4. 登录和密钥

新电脑重新完成官方 Codex 登录。不要从旧机器复制 `.codex/auth.json`、Claude OAuth 文件或 T3 登录态。官方 Claude 渠道是否能用，单独检查。

退出 T3 后，以隐藏输入为三个 API 渠道分别补齐密钥：

```powershell
python scripts/restore.py --configure-provider redromance_claude --apply
python scripts/restore.py --configure-provider deepseek_official --apply
python scripts/restore.py --configure-provider bailian --apply
```

有私密输入设施时使用临时文件：

```powershell
python scripts/restore.py --configure-provider bailian --token-file /absolute/private/secret-file --apply
```

路径是示例，必须换成本机私密工具返回的文件路径。不要使用聊天、shell 历史里的明文、仓库目录或 Git 暂存区传递密钥。临时文件由其所属的私密输入设施按约定回收。脚本不删除用户提供的源文件。

注入前脚本检查提供方驱动、配置目录和端点。已有凭证绑定的端点与模板不同时停止，避免将旧凭证改绑到其他服务。新输入密钥属于哪个渠道、是否有效，仍需用户核对并单独鉴权。脚本不比较其他渠道的密钥，也不向服务发送请求。替换已有密钥需明确使用 `--overwrite`，该过程仍不输出密钥。

所有渠道密钥都可以稍后再补。没有密钥的 API 渠道保持禁用，不影响官方 Codex 的配置恢复。

## 5. 验收并交付

```powershell
python scripts/restore.py --doctor
python scripts/restore.py --with-agent-rules
```

再打开 T3，使用 Ego 检查 Web/Electron 页面，原生窗口及文件选择交给 Cua Driver。确认默认模型走官方 Codex，各渠道显示自己的模型，DeepSeek 与百炼不会混出 Claude 模型。

按以下层级记录结论：

- 文件恢复正确，重复运行没有变化，备份位置可定位。
- Python、Git、Codex、Claude 驱动、T3、Ego 和 Cua Driver 是否安装或可执行。
- 账户是否登录，三个 API 渠道是否已补密钥。doctor 只检查配置，不能证明密钥有效或账户有额度。
- T3 是否识别渠道和模型。需要鉴权验证时使用该渠道官方文档确认的只读接口，不自动发送模型推理。
- 真实模型任务是否实际运行。没有额外付费验证授权就标为未验证，不以“配置完成”代替“推理成功”。

用户首次引导、验证码、系统授权或工具不可用会阻塞相关步骤时，指出具体阻塞，继续不依赖它的工作。浏览完成后等待 `task.finish({keep: []})` 成功，清理本任务 Cua 会话，不关闭用户已有应用或共享服务。
