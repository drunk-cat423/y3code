---
name: pstack-auto
description: 为复杂开发、Bug 修复、重构、架构、性能和工程验证加载已安装的 pstack。普通问答、网页摘要、翻译、媒体处理及简单局部修改不触发。
---

# Personal pstack entry for Codex

先确认用户没有指定其他工作流。从当前技能目录定位 `pstack:poteto-mode` 的入口；若未列出，用 `codex plugin list --marketplace codex-pstack --json` 确认启用版本，再在本机 Codex home 的 `plugins/cache/codex-pstack/pstack/<version>/` 核对 manifest 和入口。不得固定版本目录或使用临时源码。

完整读取 poteto-mode 与其 Codex adapter，在当前主线程执行匹配 playbook。完整读取项目 `.agents/pstack-models.md`，没有时读用户 `~/.agents/pstack-models.md`，包括角色行之后的任务策略和宿主路由。未配置的角色才继承父会话；委派前解析预算一次，再按任务风险选择实际强度，检查宿主默认项和具名角色不会覆盖选择。报告实际使用的模型和强度，不把配置偏好声称为技术硬锁。

当前个人分工为 Luna High 承担边界明确的工作，Sol Medium 处理常规开发，Sol High 处理复杂问题，Astra 在复杂方案比较、疑难根因和关键风险问题上提供适量只读分析，百炼 DS 提供跨厂商独立意见和审核；具体模型 ID、预算换算及 T3 target 以模型配置为准，不在这里维护第二份映射。GPT 使用官方 Codex。DS 经 T3 delegate_task 指向配置中的百炼提供方，清空继承的 Codex 专用 options；claudeAgent 驱动不代表 Claude 模型。遵从返回的 next，每次新审核/复审新建委派；子 Agent 不再委派。路由不可用时说明并暂停该席位，不静默换成其他 DS 提供方或父模型。原生覆盖与跨提供方委派遵守当前宿主规则，不另建顶层线程。

网页继续 Ego Lite，原生桌面使用 Cua Driver；pstack 不授权改用真实鼠标、前台输入或静默换工具。任务的范围、权限、个人限制优先，不自动部署、合并、发消息或付费。

Astra 默认及最高 Medium，继承到更高强度时也必须显式封顶；工具不能表达该限制就不启动相应 Astra 子 Agent。不通过角色、CLI/API 或再委派规避。遵守当前宿主的并发和嵌套上限，不声称不同上下文就是不同模型。

插件缺失时说明并继续能做的常规工作，不声称 pstack 已启用，不自行安装或改全局模型。非 Codex 环境应使用相应 port，不直接安装此入口。
