# Antigravity 迁移到 VS Code 完整指南

## 1. 目标与结论

你的目标不是“部分迁移”，而是尽量把当前 Antigravity 的日常开发环境原样搬到 VS Code 中继续使用。

可以做到高保真迁移的部分：

- 用户设置 `settings.json`
- 快捷键 `keybindings.json`
- 用户代码片段 `snippets/`
- 大部分扩展列表
- 项目级 `.vscode/` 配置
- 终端、图标主题、语言包、Verilog/SystemVerilog 相关配置

不能 1:1 原样迁移的部分：

- Antigravity 专有能力，例如 Cockpit、Agent Inbox、内置 Browser、产品私有工作流
- 某些只在 Antigravity 内部打包的工具路径
- 某些通过 `.vsix` 手工安装且不在 VS Code Marketplace 上公开发布的扩展

结论：

- 你的主力开发工作完全可以迁到 VS Code。
- 真正需要手工处理的，主要是 `Antigravity 专有扩展` 和 `引用了 Antigravity 安装目录的工具路径`。

## 2. 截至本次整理时的版本与环境

### 官方与本机情况

- VS Code 官方 Release Notes Archive 当前已列出 `Visual Studio Code 1.111`，说明 `1.111` 已是正式稳定版本线。
- 本机 `code --version` 输出为 `1.111.0`。
- Antigravity 官方站点当前可见信息为 `2025-11 免费公测`。
- 本机 `antigravity --version` 输出为 `1.107.0`。

### 本机实际路径

- Antigravity 安装目录：`C:\Users\liche\AppData\Local\Programs\Antigravity`
- Antigravity 用户配置目录：`C:\Users\liche\AppData\Roaming\Antigravity\User`
- Antigravity 扩展目录：`C:\Users\liche\.antigravity\extensions`
- VS Code 用户配置目录：`C:\Users\liche\AppData\Roaming\Code\User`
- VS Code 扩展目录：`C:\Users\liche\.vscode\extensions`

## 3. 迁移前先备份

先完整备份 Antigravity 与 VS Code 当前配置，避免覆盖后回不去。

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bak = "E:\backup\ag_to_vscode_$ts"
New-Item -ItemType Directory -Force $bak | Out-Null

Copy-Item "$env:APPDATA\Antigravity\User" "$bak\Antigravity_User" -Recurse -Force
Copy-Item "$env:USERPROFILE\.antigravity\extensions" "$bak\Antigravity_extensions" -Recurse -Force

if (Test-Path "$env:APPDATA\Code\User") {
  Copy-Item "$env:APPDATA\Code\User" "$bak\VSCode_User_before" -Recurse -Force
}
if (Test-Path "$env:USERPROFILE\.vscode\extensions") {
  Copy-Item "$env:USERPROFILE\.vscode\extensions" "$bak\VSCode_extensions_before" -Recurse -Force
}
```

## 4. 推荐迁移方式

推荐使用 `VS Code Profile` 做迁移，而不是直接污染你现在的默认配置。

操作：

1. 打开 VS Code。
2. 进入 `File > Preferences > Profiles`。
3. 新建一个 Profile，例如命名为 `Antigravity Migration`。
4. 后续所有迁移动作都在这个 Profile 下完成。

这样如果效果不好，你可以随时切回默认 Profile。

## 5. 用户配置迁移

### 5.1 直接复制的文件

以下内容可以直接迁移：

- `C:\Users\liche\AppData\Roaming\Antigravity\User\settings.json`
- `C:\Users\liche\AppData\Roaming\Antigravity\User\keybindings.json`
- `C:\Users\liche\AppData\Roaming\Antigravity\User\snippets\`

建议做法不是“直接覆盖”，而是“先复制，再人工修正产品专有项”。

```powershell
Copy-Item "$env:APPDATA\Antigravity\User\settings.json" "$env:APPDATA\Code\User\settings.json" -Force
Copy-Item "$env:APPDATA\Antigravity\User\keybindings.json" "$env:APPDATA\Code\User\keybindings.json" -Force
Copy-Item "$env:APPDATA\Antigravity\User\snippets" "$env:APPDATA\Code\User\snippets" -Recurse -Force
```

### 5.2 你当前 Antigravity 设置里需要手工修正的项

你本机当前 Antigravity `settings.json` 中，以下项需要特别处理：

#### A. Antigravity 专有配置

以下配置在 VS Code 中没有意义，应删除：

```json
"agCockpit.groupingEnabled": true,
"agCockpit.statusBarFormat": "standard"
```

#### B. Verible 路径引用了 Antigravity 自带二进制

你当前设置中有：

```json
"verilog.formatting.veribleVerilogFormatter.path": "C:\\Users\\liche\\AppData\\Local\\Programs\\Antigravity\\bin\\verible-verilog-format.exe"
```

这在 VS Code 中不应继续引用 Antigravity 安装目录。你有两种做法：

1. 单独安装 `verible-verilog-format.exe`，然后把路径改到独立安装位置。
2. 如果你不再使用 Verible，改用其他 VS Code 中已安装且可用的 formatter。

推荐改法示例：

```json
"verilog.formatting.veribleVerilogFormatter.path": "D:\\tools\\verible\\verible-verilog-format.exe"
```

#### C. Formatter 扩展 ID 需要核对

你当前设置里出现了：

```json
"editor.defaultFormatter": "mshr-h.veriloghdl"
```

但你当前 Antigravity 扩展清单里没有看到 `mshr-h.veriloghdl`，说明至少有以下一种情况：

- 这是历史残留配置
- 扩展已经卸载
- 扩展未记录在当前扩展清单中

迁移时必须在 VS Code 里做一次确认：

- 如果你确实要继续用这个 formatter，就先在 VS Code 安装它
- 如果你不用它，就改成你当前真实安装的 formatter，例如：
  - `andrewnolte.vscode-system-verilog`
  - `bmpenuelas.systemverilog-formatter-vscode`

## 6. 扩展迁移

### 6.1 你的 Antigravity 当前扩展列表

从 `C:\Users\liche\.antigravity\extensions\extensions.json` 提取到的扩展 ID 如下：

- `andrewnolte.vscode-system-verilog`
- `bmpenuelas.systemverilog-formatter-vscode`
- `czh.czh-verilog-snippet`
- `davidanson.vscode-markdownlint`
- `devsense.phptools-vscode`
- `dglab.dglog`
- `golang.go`
- `hnw.vscode-auto-open-markdown-preview`
- `jlcodes.antigravity-cockpit`
- `llvm-vs-code-extensions.vscode-clangd`
- `meta.pyrefly`
- `ms-ceintl.vscode-language-pack-zh-hans`
- `ms-python.debugpy`
- `ms-python.python`
- `ms-python.vscode-python-envs`
- `ms-vscode.powershell`
- `openai.chatgpt`
- `pkief.material-icon-theme`
- `redhat.java`
- `scala-lang.scala`
- `scalameta.metals`
- `shopify.ruby-lsp`
- `truecrab.verilog-testbench-instance`
- `vscjava.vscode-gradle`
- `vscjava.vscode-java-debug`
- `vscjava.vscode-java-dependency`
- `vscjava.vscode-java-pack`
- `vscjava.vscode-java-test`
- `vscjava.vscode-maven`

### 6.2 不建议迁移的扩展

- `jlcodes.antigravity-cockpit`

原因：

- 这是 Antigravity 产品特定能力，不是标准 VS Code 使用场景的一部分。

### 6.3 优先直接安装到 VS Code 的扩展

先安装绝大多数通用扩展：

```powershell
$exts = @(
  "andrewnolte.vscode-system-verilog",
  "bmpenuelas.systemverilog-formatter-vscode",
  "czh.czh-verilog-snippet",
  "davidanson.vscode-markdownlint",
  "devsense.phptools-vscode",
  "dglab.dglog",
  "golang.go",
  "hnw.vscode-auto-open-markdown-preview",
  "llvm-vs-code-extensions.vscode-clangd",
  "meta.pyrefly",
  "ms-ceintl.vscode-language-pack-zh-hans",
  "ms-python.debugpy",
  "ms-python.python",
  "ms-python.vscode-python-envs",
  "ms-vscode.powershell",
  "openai.chatgpt",
  "pkief.material-icon-theme",
  "redhat.java",
  "scala-lang.scala",
  "scalameta.metals",
  "shopify.ruby-lsp",
  "truecrab.verilog-testbench-instance",
  "vscjava.vscode-gradle",
  "vscjava.vscode-java-debug",
  "vscjava.vscode-java-dependency",
  "vscjava.vscode-java-pack",
  "vscjava.vscode-java-test",
  "vscjava.vscode-maven"
)

foreach ($ext in $exts) {
  code --install-extension $ext
}
```

### 6.4 如果某些扩展安装失败

你当前 Antigravity 扩展中，有些很可能是通过 `.vsix` 手工装入的，例如：

- `truecrab.verilog-testbench-instance`
- `czh.czh-verilog-snippet`
- `hnw.vscode-auto-open-markdown-preview`

如果 `code --install-extension <id>` 失败，按这个顺序处理：

1. 先在 VS Code Marketplace 搜同名扩展。
2. 如果 Marketplace 没有，就使用你原来保存的 `.vsix` 文件安装。
3. 如果 `.vsix` 也没有，只剩扩展目录，则可临时复制扩展目录到 `C:\Users\liche\.vscode\extensions`，但这属于兜底方案，不如 `.vsix` 干净。

## 7. 快捷键与片段迁移

### 快捷键

你当前 Antigravity 的快捷键里主要有：

- `Ctrl+Alt+C` 切换查找大小写
- `Alt+C` 触发列选择

把 `keybindings.json` 复制到 VS Code 后即可生效。

### Snippets

如果你在 Antigravity `snippets/` 下维护了 Verilog、SystemVerilog、Scala、SpinalHDL 片段，直接复制到 VS Code 对应目录即可。

## 8. AI 能力迁移

### 你已经有的全局 AI 规则

你当前更关键的 AI 工作流，其实不在 Antigravity 里，而是在：

- `C:\Users\liche\.codex\AGENTS.md`
- `C:\Users\liche\.codex\memories\*`

这些本来就是 VS Code 中 Codex/ChatGPT 工作流更容易继续复用的配置，因此这部分不需要从 Antigravity 再迁一次。

### 在 VS Code 中建议保留

- `openai.chatgpt`
- 中文语言包
- Verilog/SystemVerilog 格式化与 lint 相关扩展

### Antigravity 专有 AI 能力的替代思路

Antigravity 的 `Cockpit / 多 Agent / Browser` 没有 VS Code 原生一键等价物。迁移到 VS Code 后，建议这样理解：

- 代码编辑：VS Code 本体
- 终端执行：VS Code Terminal
- AI 协助：OpenAI/ChatGPT/Codex 扩展
- 浏览器验证：改为系统浏览器或 VS Code 调试/任务流

也就是说，开发主链路可迁，Antigravity 的产品专有交互模式不能“完全原样”复制。

## 9. 建议的最终落地步骤

按下面顺序做，最稳：

1. 备份 Antigravity 和 VS Code 当前配置。
2. 升级或确认 VS Code 为当前稳定版。
3. 在 VS Code 新建 `Antigravity Migration` Profile。
4. 复制 `settings.json`、`keybindings.json`、`snippets/`。
5. 删除 `agCockpit.*` 等 Antigravity 专有设置。
6. 修正所有指向 Antigravity 安装目录的工具路径。
7. 用命令批量安装扩展。
8. 对安装失败的扩展改走 `.vsix` 或手工补装。
9. 打开你的 FPGA 项目，检查：
   - 图标主题
   - 中文界面
   - Verilog/SystemVerilog 高亮
   - formatter
   - lint
   - snippets
   - terminal profile
   - OpenAI/ChatGPT 可用性
10. 确认全部正常后，再考虑卸载 Antigravity。

## 10. 建议不要立刻删除 Antigravity

建议至少保留 1 到 2 周观察期。

观察期内你只做两件事：

- 主力开发切到 VS Code
- Antigravity 仅作为“对照环境”和“应急回退环境”保留

等你确认以下都正常后再卸载：

- 日常编辑无缺项
- Verilog/SystemVerilog 工具链正常
- AI 工作流能接受
- 习惯快捷键和片段都能用

## 11. 你这台机器上最值得优先检查的点

结合你当前配置，我认为最容易出问题的是这 4 项：

1. `verible-verilog-format.exe` 路径仍指向 Antigravity 安装目录
2. `mshr-h.veriloghdl` formatter 配置与当前扩展清单不一致
3. `jlcodes.antigravity-cockpit` 无法迁移
4. 个别 `.vsix` 来源扩展可能无法通过 Marketplace 直接重装

## 12. 参考来源

- VS Code Release Notes Archive: https://code.visualstudio.com/updates/archive
- VS Code Profiles: https://code.visualstudio.com/docs/configure/profiles
- VS Code Settings Sync: https://code.visualstudio.com/docs/editor/settings-sync
- Antigravity 官方站点: https://antigravity-ide.com/zh.html

## 13. 说明

关于 Antigravity 的“最新正式版本号”，公开站点当前可直接看到的是公测信息，但没有像 VS Code 那样清晰暴露版本归档页。因此本文对 Antigravity 的版本基线采用了你本机 `antigravity --version` 的实测值 `1.107.0`，这是我能确认的、对你当前迁移最有操作意义的依据。
