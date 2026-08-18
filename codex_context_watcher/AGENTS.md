# Repository Guidelines

## Project Structure

- `src/codex_context_watcher.py` contains the standard-library Python watcher, popup UI, process detection, and Codex state/rollout parsing.
- `scripts/start.ps1`, `scripts/stop.ps1`, and `scripts/status.ps1` are the supported Windows entry points.
- `scripts/resume_context.ps1` opens the Codex resume picker with a selected context window.
- `README.md` documents normal operation; `维护会话记录.md` records migration and design decisions.

## Build, Test, and Development Commands

This repository has no package manager or compilation step. Use PowerShell 7 when available:

```powershell
python -m compileall src
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
```

`compileall` performs a syntax check. The scripts start the detached watcher, report its PID, and stop it. For a direct foreground run while debugging, use `python src/codex_context_watcher.py run` and stop it with `Ctrl+C`.

## Coding Style and Naming

Follow standard Python formatting: four spaces, `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for constants, and type annotations for new public helpers. Keep the implementation Windows-compatible and use UTF-8 for text files. PowerShell scripts should use explicit paths derived from `$PSScriptRoot` and return the wrapped command's exit code. Keep comments short and bilingual (English/Chinese) when comments are necessary.

## Testing Guidelines

There is no automated test suite or coverage threshold yet. At minimum, run `python -m compileall src` after Python changes, then exercise `start`, `status`, and `stop` without leaving a watcher process behind. Changes to token parsing should also be checked against representative rollout JSONL data without accessing real credentials.

## Commits and Pull Requests

Use concise imperative commit subjects; the existing history contains short Chinese and English subjects. Keep each commit focused. Pull requests should explain behavior changes, list validation commands and results, identify Windows/Python assumptions, and include screenshots for popup/UI changes. Link the relevant issue or maintenance record when one exists.

## Security and Configuration

The watcher reads `%USERPROFILE%\.codex\state_5.sqlite`, rollout JSONL files, and writes PID/log files under `%USERPROFILE%\.codex`. Never copy, commit, or print OAuth tokens, state databases, rollout contents, or private logs. Preserve the existing `.gitignore` rules for Python caches.
