# 在新电脑恢复我的 T3 Code 配置

把本仓库交给新电脑上的 Codex，恢复渠道、模型列表、快捷键、界面偏好和个人 Agent 规则。仓库不含 API 密钥、账号登录态或聊天记录。

## 给新电脑上的 Codex

复制这段话：

> 请克隆 https://github.com/drunk-cat423/y3code.git，完整阅读 AGENTS.md 和 docs/bootstrap-codex.md，帮我恢复这套 T3 Code 配置。本次授权在本机安装所需的官方工具、预览并应用没有冲突的配置。先检测系统和已有安装，已有配置冲突时保留并说明，不自行覆盖。按文档恢复官方 Codex、红浪漫 Claude、DeepSeek 官方和百炼渠道，以及个人规则和 pstack。密钥用私密输入补齐，官方账号重新登录。网页用 Ego Lite，原生桌面用 cua.ai Cua Driver，禁止自动前台回退。不要迁移历史数据库、旧机器登录态或修改代理，不自动执行付费模型验证。完成后分别报告配置、工具、鉴权和真实任务的验证状态。

如果已经克隆，在该目录启动 Codex，发送上面去掉“请克隆”的内容。

## 手动恢复配置

需要 Git、Python 3.11+ 和 T3 Code。先启动 T3 一次完成初始化，再正常退出。不要从仍在运行的目标 T3 会话中修改它自己的配置。

```powershell
git clone https://github.com/drunk-cat423/y3code.git
cd y3code
python scripts/restore.py --with-agent-rules
```

预览没有冲突后，应用配置：

```powershell
python scripts/restore.py --with-agent-rules --apply
python scripts/restore.py --with-agent-rules
python scripts/restore.py --doctor
```

第二次预览应全部为 unchanged。已有同名设置不同会拒绝写入，未管理的字段和其他渠道会保留。需要合并时先让 Codex检查冲突。只有明确决定用仓库值替换后才加 `--overwrite`，它会备份被修改的文件。

配置目录默认是当前用户的 `.t3`，也识别 `T3CODE_HOME`。可用 `--home` 和 `--t3-home` 显式指定目标，路径不能放在本仓库内。

## 补齐渠道密钥

三个 API 渠道初次恢复时禁用。退出 T3，在本地终端逐项运行，按隐藏输入填写对应密钥：

```powershell
python scripts/restore.py --configure-provider redromance_claude --apply
python scripts/restore.py --configure-provider deepseek_official --apply
python scripts/restore.py --configure-provider bailian --apply
```

也可由真正的私密输入工具提供临时文件，再传入 `--token-file`。不要把密钥作为命令参数或聊天消息。脚本写入该渠道的本地配置后启用渠道，不发送网络请求。密钥在本地配置中是明文，按凭证文件保护，勿上传或共享。

官方 GPT 使用新电脑自己的 Codex 官方登录。官方 Claude 如需使用，也重新登录。密钥、模型列表、账号额度和实际可用性是不同的检查，见 [恢复与验收流程](docs/bootstrap-codex.md)。

## 恢复范围

- T3 的五个提供方定义、各自模型列表和显示顺序。默认模型为官方 Codex `gpt-6.2-sol`，High，Priority。
- 便携的界面偏好和快捷键。保留源机英文界面偏好，不复制窗口位置、麦克风、浏览器 profile 和项目收藏。
- 可选个人 `AGENTS.md`、pstack 模型分工和 `pstack-auto` 入口。Ego、Cua Driver、pstack 插件按 [工具安装指引](docs/tools.md) 在新电脑安装。
- Codex 主模型配置提供 [单独的参考片段](templates/agent/model-preferences.toml)，由 Codex 检查后合并。恢复器不复制完整 `config.toml`，不修改 MCP、权限、可信项目列表或旧角色 TOML。

基础配置采集于 2026-11-17，模型配置已于 2026-11-18 更新为 GPT-6.2，源机版本为 `0.1.10-nightly.20261116.4800`。模型名称和额度必须按新电脑实际账户确认。Priority 是源机设置，不保证账号支持或价格相同。Windows 已进行隔离目录恢复验证，macOS 和 Linux 尚未实机验证。

程序的更新源指向官方 `pingdotgg/t3code` Nightly。尚未比对程序文件与原版是否一致，本仓库不分发或声称还原未知的二进制改造。详情见 [快照来源与限制](docs/snapshot.md)。

## 检查本仓库

```powershell
python -m unittest discover -s tests -v
```

测试只写临时目录，不访问渠道、不启动 GUI、不产生模型费用。
