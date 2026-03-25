# Walkthrough

## 当前推荐模式

当前脚本已经改成“轻量配置模式”为主：

- 插件安装以 `手动处理` 为主
- 配置迁移以 `一键处理` 为主
- 默认不复制整包扩展目录
- 默认不备份整包扩展目录

这样做的目标是：

- 避免再生成 GB 级临时目录
- 保留配置一键迁移的便利性
- 把插件选择权留给你自己

## 推荐执行顺序

1. 先执行一次默认 dry-run：

```powershell
.\执行Antigravity迁移到VSCode.ps1
```

2. 打开生成目录中的：
   - `Migration_Summary.md`
   - `Settings_Migration_Report.md`
   - `VSCode_Extensions_Manual_Install.md`

3. 在 VS Code 中手动安装你真正需要的插件
4. 执行生成目录中的 `preview_staged_vscode.ps1`
5. 在预览环境中打开 FPGA 工程，检查：
   - Verilog/SystemVerilog 高亮
   - formatter
   - snippets
   - 中文界面
   - PowerShell / Scala / Python 扩展
   - Codex / ChatGPT 工作流

6. 确认预览效果可接受后，再执行真实写入：

```powershell
.\执行Antigravity迁移到VSCode.ps1 -ApplyConfig
```

## 如果你以后又想批量装插件

可以额外生成安装脚本：

```powershell
.\执行Antigravity迁移到VSCode.ps1 -GenerateExtensionInstallScript
```

它会给你：

- `install_gallery_extensions.ps1`
- `Manual_VSIX_Extensions.md`

但默认工作流仍然建议你手动安装插件。

## 这版脚本会做什么

- 备份最小必要配置
  - `settings.json`
  - `keybindings.json`
  - `snippets`
  - `extensions.json`
- 生成清洗后的 staged `settings.json`
- 自动移除 `agCockpit.*`
- 对仍指向 Antigravity 的 Verible 路径给出审查提示
- 对 `mshr-h.veriloghdl` 缺失问题给出审查提示
- 生成手动插件安装清单

## 这版脚本默认不会做什么

- 不会默认复制 Antigravity 扩展目录
- 不会默认备份 VS Code 扩展目录
- 不会默认联网安装扩展
- 不会默认改写真实 VS Code 用户目录

## 仅在你明确要求时才建议启用的模式

如果你以后确实要研究“完整复制扩展目录”的效果，可以显式加：

```powershell
.\执行Antigravity迁移到VSCode.ps1 -IncludeExtensionArtifacts
```

但这不是当前推荐路径，因为它会重新带来大体积目录和更高的不确定性。
