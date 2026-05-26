---
name: chat-log-maintainer
description: Maintain `chat_log.md` for this repository in a consistent, append-only Markdown format. Use when Codex, Cloud Code, Claude Code, or any repo-aware coding agent needs to summarize a user request, record decisions, log changed files, capture validation results, or preserve handoff context after meaningful work.
---

# Chat Log Maintainer

Maintain project conversation history in a way that another agent can continue the work without rereading the full chat transcript.

For Codex, this skill can be invoked as `$chat-log-maintainer`. For Cloud Code or Claude Code, open this `SKILL.md` directly and follow the same workflow.

## Workflow

### 1. Inspect before writing

- Read `chat_log.md` first.
- Preserve all existing history.
- If `chat_log.md` is empty or malformed, rebuild it from the template in [references/chat-log-format.md](references/chat-log-format.md).

### 2. Decide whether to append or update

- Append a new session when the user starts a new task, a new objective, or a clearly separate batch of edits.
- Update the latest open session when the current work is a continuation of the same request.
- Prefer fewer, fuller entries over many tiny entries.

### 3. Record the minimum durable context

Each session entry should capture:

- `Request`: what the user asked for
- `Key Decisions`: architectural or process choices that affect future work
- `Files Updated`: files created, edited, or intentionally reviewed
- `Summary of Changes`: what actually changed
- `Validation`: tests, checks, or manual verification performed
- `Open Follow-ups`: unresolved items, risks, or next steps

Keep entries concise and factual. Do not paste long transcripts.

### 4. Preserve formatting

- Use Markdown headings exactly as defined in the reference template.
- Keep entries append-only and place the newest session first.
- Use plain language and short paragraphs or flat bullets.
- Keep file paths in backticks.
- Do not delete older sessions unless the user explicitly asks for pruning.

### 5. Prefer repository truth over memory

- When summarizing changes, verify against the current workspace.
- If a decision changed during implementation, record the final decision, not the initial guess.
- If validation was not run, say so explicitly.

## Content Rules

- Record outcomes, not internal chain-of-thought.
- Note assumptions only when they affect future work.
- Mention blockers only if they remain relevant after the turn.
- If the user asks for detailed logging, be a bit more explicit in `Key Decisions` and `Open Follow-ups`.
- If the user asks for a lightweight update, compress `Summary of Changes` and `Validation`.

## Reference

Use [references/chat-log-format.md](references/chat-log-format.md) as the canonical format for initializing or repairing `chat_log.md`.
