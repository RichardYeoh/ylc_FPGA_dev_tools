# Antigravity 卸载清理说明

## 1. 本机当前识别到的相关安装

### Antigravity IDE 主程序

- 显示名：`Antigravity (User)`
- 版本：`1.20.6`
- 安装目录：`C:\Users\liche\AppData\Local\Programs\Antigravity`
- 卸载程序：`C:\Users\liche\AppData\Local\Programs\Antigravity\unins000.exe`

### 单独存在的 Antigravity Tools

- 显示名：`Antigravity Tools`
- 版本：`4.1.30`
- 安装目录：`C:\Users\liche\AppData\Local\Antigravity Tools`
- 卸载程序：`C:\Users\liche\AppData\Local\Antigravity Tools\uninstall.exe`

注意：

- `Antigravity Tools` 和 `Antigravity (User)` 在当前机器上是 `两个独立卸载项`
- 如果你的目标只是卸载 IDE，本次优先处理 `Antigravity (User)`
- 只有在你确认 `Antigravity Tools` 也不再需要时，才一并卸载它

## 2. 本机当前可能留下的主要空间占用

- `C:\Users\liche\AppData\Local\Programs\Antigravity` 约 `771.50 MB`
- `C:\Users\liche\AppData\Roaming\Antigravity` 约 `435.69 MB`
- `C:\Users\liche\.antigravity` 约 `1086.99 MB`
- `C:\Users\liche\AppData\Local\Antigravity Tools` 约 `48.02 MB`

其中：

- `Programs\Antigravity` 是主程序安装目录
- `Roaming\Antigravity` 是用户配置与用户态数据
- `.antigravity` 主要是扩展与相关用户数据
- `Antigravity Tools` 是单独工具目录

## 3. 想卸得干净，推荐顺序

### 第一步：先确认 VS Code 迁移已经可用

至少确认下面几项已经正常：

- Verilog/SystemVerilog 高亮
- formatter
- snippets
- PowerShell / Scala / Python 扩展
- Codex / ChatGPT 工作流

在这些确认之前，不建议立刻删掉 Antigravity 用户数据目录。

### 第二步：关闭 Antigravity 相关进程

至少确认以下进程不在运行：

- `Antigravity.exe`
- `antigravity_tools.exe`

如果程序还开着，卸载和后续清理都可能不完整。

### 第三步：先卸载主 IDE

推荐优先使用主程序自带卸载器：

```powershell
& "C:\Users\liche\AppData\Local\Programs\Antigravity\unins000.exe"
```

更推荐使用 `带界面` 的正常卸载，而不是一开始就静默卸载。  
这样你可以更直观看到卸载器有没有报错。

### 第四步：卸载后检查主程序目录是否还在

重点检查：

- `C:\Users\liche\AppData\Local\Programs\Antigravity`

如果卸载完成后该目录仍然存在，并且你已经确认不再回退使用，可以手工删除残留目录。

### 第五步：清理用户数据残留

如果你已经确认不再需要保留 Antigravity 的历史配置、扩展和缓存，可以删除：

- `C:\Users\liche\AppData\Roaming\Antigravity`
- `C:\Users\liche\.antigravity`

这是“卸干净”最关键的一步，因为很多卸载器不会主动删掉用户数据目录。

### 第六步：按需决定是否卸载 Antigravity Tools

如果你确认这个工具也不再需要，再执行：

```powershell
& "C:\Users\liche\AppData\Local\Antigravity Tools\uninstall.exe"
```

然后检查：

- `C:\Users\liche\AppData\Local\Antigravity Tools`

如果仍有残留，再手工删除。

## 4. 如何判断算“卸干净”

至少同时满足下面几条：

1. `Antigravity (User)` 卸载入口在系统“已安装应用”里消失
2. `C:\Users\liche\AppData\Local\Programs\Antigravity` 不存在
3. `C:\Users\liche\AppData\Roaming\Antigravity` 不存在
4. `C:\Users\liche\.antigravity` 不存在
5. `where.exe antigravity` 查不到主程序
6. 如果你也卸了 `Antigravity Tools`，它对应目录和卸载项也消失

## 5. 推荐的最终核查命令

```powershell
where.exe antigravity
```

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Programs\Antigravity" -Force
```

```powershell
Get-ChildItem "$env:APPDATA\Antigravity" -Force
```

```powershell
Get-ChildItem "$env:USERPROFILE\.antigravity" -Force
```

如果这些路径都不存在，或者 `where.exe antigravity` 查不到结果，通常就已经算卸得比较干净了。

## 6. 风险提醒

- 不要在迁移尚未验证前就删除 `Roaming\Antigravity` 和 `.antigravity`
- `mshr-h.veriloghdl` 和 Verible 路径问题应先在 VS Code 侧确认，否则卸载后可能出现 formatter 失效
- `Antigravity Tools` 是单独组件，不要默认把它等同于主 IDE
