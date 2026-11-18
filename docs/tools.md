# 安装新电脑所需工具

先检查现有安装。下面的入口来自供应商或既有恢复仓库，不代表已经在目标电脑运行成功。安装命令和系统要求以当前官方指引为准。

## T3 和模型驱动

- T3 官方发布：https://github.com/pingdotgg/t3code/releases 。源机使用 Nightly `0.1.10-nightly.20261116.4800`，不把 `y3code` 当作 T3 程序源码或安装包。
- Codex 官方源码和 CLI 安装说明：https://github.com/openai/codex 。使用官方登录和提供方，不将 GPT 改走 Claude 转接渠道。
- Claude Code 官方安装说明：https://code.claude.com/docs/en/setup 。本仓库三个 API 渠道使用 T3 的 `claudeAgent` 驱动，因此需要此驱动能在 T3 中正常启动；驱动名不代表实际模型厂商。

先检查 T3 的 Setup 和本机命令，再按对应版本的官方说明补齐驱动。安装依赖涉及需要确认的项目清单或 CI 修改时停止，不为恢复工具修改项目依赖。不要复制旧机器的 npm 全局目录或 `.t3/bin/t3.cmd`，后者包含旧电脑绝对路径，由新安装生成。

## Ego Lite

官方入口：https://lite.ego.app/ 。安装与新电脑操作系统匹配的版本，完成首次引导。

验证命令：

```powershell
ego-browser skill
```

Windows 若当前终端未刷新 PATH，检查当前用户 `.local/share/ego/active_version_dir/ego-browser.exe`。不要固定版本子目录。先完整阅读安装版本返回的指引，再进行网页搜索、阅读或操作。

实际网页验收使用一个 TaskSpace，读取测试页后等待 `await task.finish({ keep: [] })` 成功。不要复制 profile、Cookie 或旧 Space。无法使用时报告，不能静默换浏览器。

## Cua Driver

官方安装：https://cua.ai/docs/how-to-guides/driver/install 。官方接入：https://cua.ai/docs/how-to-guides/driver/connect-your-agent 。

Windows 先下载官方安装脚本到任务目录并阅读，再按当前参数安装。不要直接执行未检查的网络响应，不绕过签名检查，不自动开启其他 agent 的连接或前台控制权限。

安装后先检查：

```powershell
cua-driver --version
cua-driver doctor --json
cua-driver connect --client codex --dry-run --json
```

确认计划后，仅连接 Codex：

```powershell
cua-driver connect --client codex --json
cua-driver skills status
```

Windows 稳定入口为当前用户 `%LOCALAPPDATA%/Programs/Cua/cua-driver/bin/cua-driver.exe`。由官方 connect 生成 MCP 和 Skill 路径，不复制源机 MCP 配置。重启 Codex 后加载连接。系统授权由用户在新电脑批准。

先读官方 `cua-driver` Skill 和平台指引，再以 `delivery_mode:"background"` 操作原生窗口，禁止自动前台回退。doctor、MCP 可用和一次真实桌面动作成功要分别验证。结束只清理本任务会话。

## pstack

本仓库的 `--with-agent-rules` 已复制 `pstack-auto` 和角色偏好，不复制插件缓存。官方 Codex port：https://github.com/pstack-ports/codex-pstack 。

先用本机 `codex plugin --help` 核实当前版本支持的命令。已核对的安装入口为：

```powershell
codex plugin marketplace add pstack-ports/codex-pstack
codex plugin add pstack@codex-pstack
codex plugin list --marketplace codex-pstack --json
```

如果插件已经启用，不重复安装或擅自升级。源机版本 `0.15.43` 只作参考。未安装成功时说明，不声称自动工作流已生效。

角色偏好位于新电脑的 `~/.agents/pstack-models.md`。2026-11-18 已将 Sol 更新为 `gpt-6.2-sol`，并在专项审查中增加 `gpt-6.2-astra`。Astra 仅只读，用于复杂方案、疑难根因与关键风险；独立顾问固定 Medium，审查席按 medium 预算从 Medium 降到 Low，按风险可升回 Medium，所有入口最高均为 Medium。它保留源机的 medium 预算换算、Sol/Luna 分工和百炼 DS 路由；插件安装不提供模型账户或额度。先核实提供方和模型可见，再执行真实任务。不要为验证自动发起额外模型调用。

## 复用已有环境恢复仓库

完整的工具安装背景和跨 agent 指引位于 https://github.com/drunk-cat423/skill-tool 。本次参考的提交为 `fc04efd9b288f0d574bfd041249e08f9b703fdd9`。

需要时在独立目录克隆并阅读 README 和当前 Skill。它与本仓库都可能安装个人规则，先预览差异，使用本仓库的现行模板作本次恢复目标，不连续用两个恢复器覆盖同一个文件。不要整份复制该仓库、旧机器的 `.codex` 或所有 Skills。
