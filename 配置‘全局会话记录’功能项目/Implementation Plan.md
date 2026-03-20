# Implementation Plan

## Topic

OpenClaw 对标的全局记忆体系重构。

## Goals

- 保留项目本地全文会话记录。
- 保留全局索引与经验卡。
- 引入 OpenClaw 风格的核心记忆与每日记忆流水。
- 将旧 `GLOBAL_SESSION_LOG.md` 调整为兼容层。

## Planned Changes

1. 新增项目方案文档，明确新架构与迁移路径。
2. 更新 `GLOBAL_SESSION_POLICY.md`，把新分层正式写成策略。
3. 新增 `C:\Users\liche\.codex\memories\MEMORY.md`。
4. 新增 `C:\Users\liche\.codex\memories\memory\YYYY-MM-DD.md`。
5. 更新 `GLOBAL_SESSION_INDEX.md`，登记这次架构重构。
6. 更新 `GLOBAL_EXPERIENCE_CARDS.md`，增加 OpenClaw 对标经验卡。
7. 追加项目本地会话记录，保留本次决策过程。

## Notes

- 若后续需要让运行时默认优先读取 `MEMORY.md`，再考虑同步更新 `C:\Users\liche\.codex\AGENTS.md`。
- 现阶段先完成数据层与策略层重构，不强依赖宿主钩子。
