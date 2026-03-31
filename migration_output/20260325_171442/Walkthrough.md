# Walkthrough

## What this run generated

- A staged VS Code user-data directory for preview.
- A manual extension checklist.
- A preview launcher script.
- A migration summary and focused settings/extension reports.

## Suggested usage

1. Run this script once without -ApplyConfig.
2. Read Migration_Summary.md and Settings_Migration_Report.md.
3. Read VSCode_Extensions_Manual_Install.md and install the plugins you actually want by hand.
4. Run preview_staged_vscode.ps1 and open one of your FPGA projects in the staged environment.
5. Confirm formatter, snippets, terminal, language pack, and AI workflow behavior.
6. Re-run with -ApplyConfig only after the staged preview looks correct.
