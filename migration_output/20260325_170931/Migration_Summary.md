# Migration Summary

## Mode

- ApplyConfig: False
- GenerateExtensionInstallScript: False
- InstallExtensions: False
- IncludeExtensionArtifacts: False
- SkipBackups: False
- ProfileName (staging label): Antigravity Migration
- RunDir: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931
- StagedUserDataDir: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\staged_user_data_Antigravity_Migration
- StagedExtensionsDir: not-created
- PreviewScript: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\preview_staged_vscode.ps1

## Backups

- BackupDir: E:\proj\ylc_FPGA_dev_tools\.\migration_backups\20260325_170931
- Antigravity_settings.json: copied=True
- Antigravity_keybindings.json: copied=True
- Antigravity_snippets: copied=True
- Antigravity_extensions.json: copied=True
- VSCode_settings_before: copied=True
- VSCode_keybindings_before: copied=False
- VSCode_snippets_before: copied=True
- Lightweight backup mode was used: extension folders were not backed up.

## Staged Config

- settings.json: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\staged_user_data_Antigravity_Migration\User\settings.json
- keybindings.json: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\staged_user_data_Antigravity_Migration\User\keybindings.json
- snippets: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\staged_user_data_Antigravity_Migration\User\snippets

## Staged Settings Review

- Removed key: agCockpit.groupingEnabled
- Removed key: agCockpit.statusBarFormat
- Warning: Formatter mshr-h.veriloghdl is not present in the current extension inventory / 当前扩展清单中未发现 mshr-h.veriloghdl
- Warning: Verible formatter path still points to Antigravity / Verible 路径仍指向 Antigravity: C:\\Users\\liche\\AppData\\Local\\Programs\\Antigravity\\bin\\verible-verilog-format.exe

## Extension Handling

- Staged extension folders copied: 0
- Gallery install candidates: 25
- Manual fallback candidates: 3
- Manual install checklist: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_170931\VSCode_Extensions_Manual_Install.md

## Real Apply

- No real VS Code user directory was modified in this run.
- Re-run with -ApplyConfig to write the sanitized config into a real target user directory.
- If you want a named VS Code profile, create it first, find its actual profile User directory, and pass it through -TargetUserDir.

## Suggested Next Actions

- Review Settings_Migration_Report.md for warnings.
- Run preview_staged_vscode.ps1 to inspect the isolated preview environment.
- If the preview is acceptable, re-run this script with -ApplyConfig.
- Use VSCode_Extensions_Manual_Install.md as the manual plugin checklist.
