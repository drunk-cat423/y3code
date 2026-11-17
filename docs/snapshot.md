# 快照来源与验证范围

本仓库的配置快照采集于 2026-11-17，源机为 Windows。`templates/manifest.json` 保存版本和三个 API 渠道的配置目录映射，不含机器 ID 或凭证。

## 已读取的本机事实

- 当前运行程序为 T3 Code Nightly。版本记录为 `0.1.10-nightly.20261116.4800`。
- 安装目录的 `resources/app-update.yml` 指向 GitHub 的 `pingdotgg/t3code`，Nightly 渠道。
- `userdata/settings.json` 当前有 `codex`、`claudeAgent`、`redromance_claude`、`deepseek_official`、`bailian` 五个提供方。
- 三个 API 渠道均有独立 `homePath`。模板保留安全环境变量和模型设置，排除 `ANTHROPIC_AUTH_TOKEN` 以及其他非白名单字段。
- 默认模型为官方 Codex `gpt-6.1-sol`，`reasoningEffort=high`、`serviceTier=priority`。
- Codex 主模型的独立参考片段是 `gpt-6.1-sol`、High、上下文 `1000000`。完整配置不在仓库中。
- pstack 角色偏好和个人入口取自当前用户配置，源机已安装 pstack `0.15.43`。

更新源指向官方发布不能证明安装目录未被修改。未做原版安装包逐文件比对，没有证据将此仓库称为定制 T3 程序的完整副本。

## 渠道快照

- `codex` 使用官方 Codex 驱动和目标电脑自己的登录。
- `claudeAgent` 使用官方 Claude 驱动和目标电脑自己的登录。
- `redromance_claude` 使用 `https://www.redromance.pro`，仅列出 Claude 系列。
- `deepseek_official` 使用 `https://api.deepseek.com/anthropic`，保留 DeepSeek Flash 1M 和 V4 Pro 列表。
- `bailian` 使用 `https://dashscope.aliyuncs.com/apps/anthropic`，保留三项 DeepSeek 模型和独立审核路由。

端点和模型列表是当前本机配置的事实，不证明供应商仍提供模型、密钥有效或账户有额度。API 渠道新装默认禁用，注入密钥后才启用。源机存在但当前未引用的旧渠道目录没有导出。

## 排除的数据

不导出 `auth.json`、OAuth、Cookie、API token、T3 的 `secrets/`、`clerk/`、浏览器 profile、环境 ID、匿名 ID、聊天数据库、附件、工作树、项目目录、任务失败记录、日志、扫描缓存、安装器或模型调用结果。

客户端偏好只取便携字段。窗口坐标、用户麦克风、项目收藏、浏览器 profile、首次引导完成时间和项目分组覆盖没有导出。渠道配置中的插件缓存及机器路径没有导出。

恢复器不会修改 `desktop-settings.json`、`config.toml`、代理、系统权限、依赖清单或 CI/CD。T3 若首次初始化后某个默认值与模板不同，会按正常冲突处理，需要审阅后决定。

## 交付前验证

通过临时用户目录验证实际模板的预览、恢复、重复运行、密钥注入和冲突保护。单元测试还覆盖无关字段保留、备份、symlink/junction 拒绝和凭证端点保护。交付记录见 [verification.md](verification.md)。

源机真实 T3 配置保持只读。没有安装第二份 T3，没有做另一台实体电脑的恢复，没有复制登录态，也没有发起模型推理或计费测试。macOS 和 Linux 的真实安装、GUI 和账户鉴权尚未验证。

## 更新快照

先读取现有配置，只将本仓库已管理的键写入模板。新字段必须逐项审查。禁止把 `settings.json`、整个 `provider-homes` 或 `.codex` 直接复制进 Git。

保持 `${T3_HOME}` 和 `${USER_HOME}` 占位符，不加入机器绝对路径。渠道 token 不得出现在模板中，包括空字符串占位符。更新模型时检查 ID、显示名称和对应渠道，不把官方 GPT 接入转接渠道。

更新后运行本仓库测试和隔离目录恢复，检查 `git diff --cached`，扫描本次文件是否包含凭证。只有用户授权同步该次更新时才 push，不自动创建 PR。
