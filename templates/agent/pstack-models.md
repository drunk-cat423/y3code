# Personal pstack model configuration. Missing roles inherit the parent.
# defaults: 3
# budget: medium

feature, refactoring: gpt-6.1-sol high
bug-fix: gpt-6.1-sol high
perf-issue: gpt-6.1-sol xhigh
hillclimb: gpt-6.1-sol high
judgment and prose: gpt-6.1-sol high
arena runners: gpt-6.1-sol high, deepseek-v4.1-flash-1017
arena cross-judge pool: deepseek-v4.1-flash-1017
swarm workers: gpt-6-luna xhigh
interrogate reviewers: gpt-6.1-sol xhigh, deepseek-v4.1-flash-1017

## Effective task policy

The role lines store starting levels in setup-pstack's format. Apply the medium budget once: high becomes medium and xhigh becomes high. Do not pass the stored starting level directly to a worker. Entries without an explicit effort keep the provider's own default; do not invent an effort setting for DeepSeek.

- Use Luna High for repository discovery, bounded implementation, mechanical edits and repetitive verification with clear acceptance checks. File lists, checksums and test execution should use deterministic tools when no model judgment is needed.
- Use Sol Medium for routine development, ordinary bug fixes and synthesis. The parent keeps product decisions and final integration.
- Use Sol High for ambiguous debugging, concurrency, data consistency, difficult cross-module changes and consequential review. Raise the ordinary Sol role one step when those risks are present; a difficult performance role already starts at High after the budget.
- Use Bailian DeepSeek for an independent design opinion, requirement comparison, stage review and cross-vendor judging. It is read-only unless the user explicitly assigns implementation. A staged review requested by the user remains mandatory; other tasks do not automatically acquire an extra review round.
- Terra is not a default developer or reviewer. Astra is not a default execution seat: it is read-only, Medium at most, and reserved for major architecture, system boundaries or substantive review disputes. If the host cannot express the cap, do not start that Astra task.
- Delegate when it saves context, time or provides a useful independent opinion. A Sol parent can handle a difficult task directly instead of spawning an identical worker. A failed check alone is not permission to retry an external or paid operation.

## Host routing

These preferences are read by the agent; they are not an enforced runtime router. Validate models and efforts against the current host before spawning. A project configuration overrides role choices, but cannot override the personal Astra cap or an explicit user instruction. Check named agent profiles so an old profile does not silently replace the selected model or effort.

GPT models use the official Codex provider. Use native overrides only when allowed by the host, keeping model and reasoning in separate fields and supplying a complete brief when a fresh context is required. Follow T3's delegation rules when it requires delegate_task for a requested setting. Do not route GPT through a third-party Claude endpoint.

In T3, deepseek-v4.1-flash-1017 uses delegate_task with this target:

```json
{"providerInstanceId":"bailian","driverKind":"claudeAgent","model":"deepseek-v4.1-flash-1017","options":{}}
```

The empty options object clears inherited Codex-only settings. claudeAgent is the transport driver, not the model vendor: this seat is DeepSeek and is eligible to judge an OpenAI parent. Follow the delegate's returned next instruction; every new review or re-check is a fresh delegation. Children do not delegate again.

The provider alias is a preference, not a provider installation or credential. If it or the requested model is unavailable, report the missing route and leave that seat unstarted; do not silently switch to deepseek_official, another model, or parent inheritance. Outside T3, discover an authorized equivalent delegation capability before using this seat. Do not modify provider credentials, the main session model, permissions or plugin cache to make it available.
