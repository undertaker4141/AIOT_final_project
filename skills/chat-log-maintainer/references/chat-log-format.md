# Chat Log Format

Use this file as the canonical structure for `chat_log.md`.

## File Header

```md
# Chat Log

本檔案用來維護本專案的重要對話紀錄、決策脈絡、文件調整與後續待辦。  
採用「新紀錄放前面」的方式追加，避免覆寫既有歷史。

## 記錄規則

- 每次重要請求或一組連續修改，新增一個 session 區塊。
- 記錄重點放在需求、決策、修改內容、驗證方式與未完成事項。
- 保持精簡，但要足夠讓後續接手的人快速理解背景。
- 若只是小幅修字，可併入最近一次尚未結案的 session。

## Session Log
```

## Session Template

```md
### YYYY-MM-DD Session NNN

**Request**  
簡述使用者這次的請求。

**Key Decisions**  
- 列出會影響後續工作的決策。

**Files Updated**  
- `path/to/file`

**Summary of Changes**  
- 簡述實際完成的工作。

**Validation**  
- 記錄測試、人工檢查，或明確寫出未驗證。

**Open Follow-ups**  
- 尚未完成或後續可延伸的事項。
```

## Maintenance Rules

- Newest session first.
- Keep previous sessions intact.
- Prefer concise summaries over transcript-style logging.
- Use factual wording that another agent can trust quickly.
