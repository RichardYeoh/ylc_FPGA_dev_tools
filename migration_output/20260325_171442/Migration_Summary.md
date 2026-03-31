# Migration Summary

## Mode

- ApplyConfig: True
- GenerateExtensionInstallScript: False
- InstallExtensions: False
- IncludeExtensionArtifacts: False
- SkipBackups: False
- ProfileName (staging label): Antigravity Migration
- RunDir: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442
- StagedUserDataDir: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\staged_user_data_Antigravity_Migration
- StagedExtensionsDir: not-created
- PreviewScript: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\preview_staged_vscode.ps1

## Backups

- BackupDir: E:\proj\ylc_FPGA_dev_tools\.\migration_backups\20260325_171442
- Antigravity_settings.json: copied=True
- Antigravity_keybindings.json: copied=True
- Antigravity_snippets: copied=True
- Antigravity_extensions.json: copied=True
- VSCode_settings_before: copied=True
- VSCode_keybindings_before: copied=False
- VSCode_snippets_before: copied=True
- Lightweight backup mode was used: extension folders were not backed up.

## Staged Config

- settings.json: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\staged_user_data_Antigravity_Migration\User\settings.json
- keybindings.json: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\staged_user_data_Antigravity_Migration\User\keybindings.json
- snippets: copied=True -> E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\staged_user_data_Antigravity_Migration\User\snippets

## Staged Settings Review

- Removed key: agCockpit.groupingEnabled
- Removed key: agCockpit.statusBarFormat
- Updated item: Replaced verible formatter path / 已替换 Verible 格式化器路径: C:\Users\liche\.vscode\extensions\bmpenuelas.systemverilog-formatter-vscode-3.4.1\verible_release\win64.zip\verible-v0.0-3969-g6a70680a-win64\bin\verible-verilog-format.exe
- Warning: Formatter mshr-h.veriloghdl is not present in the current extension inventory / 当前扩展清单中未发现 mshr-h.veriloghdl

## Extension Handling

- Staged extension folders copied: 0
- Gallery install candidates: 25
- Manual fallback candidates: 3
- Manual install checklist: E:\proj\ylc_FPGA_dev_tools\.\migration_output\20260325_171442\VSCode_Extensions_Manual_Install.md

## Real Apply

- TargetUserDir: C:\Users\liche\AppData\Roaming\Code\User
- settings.json: copied=True
- keybindings.json: copied=True
- snippets: copied=True

## Suggested Next Actions

- Review Settings_Migration_Report.md for warnings.
- Run preview_staged_vscode.ps1 to inspect the isolated preview environment.
- If the preview is acceptable, re-run this script with -ApplyConfig.
- Use VSCode_Extensions_Manual_Install.md as the manual plugin checklist.
