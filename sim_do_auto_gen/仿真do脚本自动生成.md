# 仿真 TCL/BAT 自动生成说明

## 1. 工具放置位置
将以下文件放在任意工程的：

`<project>.srcs\sim_1\sim_do_auto_gen\`

- `gen_my_sim.ps1`
- `gen_my_sim.bat`
- 本说明文档

## 2. 使用前提
首次使用前，必须先在 Vivado 中至少运行一次仿真（Behavioral Simulation）。

原因：
- Vivado 会先生成 `*_compile.do`、`*_elaborate.do`、`*_simulate.do`、`simulate.bat`
- 本工具基于这些脚本生成新的 `my_sim.tcl` 和 `my_sim.bat`

## 3. 基本使用方式
在 `sim_do_auto_gen` 目录下执行：

```bat
.\gen_my_sim.bat
```

会弹出简洁 UI，手动选择要处理的 `questa` 或 `modelsim` 目录，例如：

`<project>.sim\sim_1\behav\questa`

## 4. 输出位置
生成结果放在所选目录的上一级：

`<project>.sim\sim_1\behav\`

输出文件：
- `my_sim.tcl`
- `my_sim.bat`

## 5. 运行位置
生成完成后，请在上一级输出目录执行：

```bat
.\my_sim.bat
```

重点：
- `my_sim.tcl` 和 `my_sim.bat` 必须继续放在 `behav` 这一层
- 不要把它们移动回 `questa/modelsim` 目录
- 新脚本会在运行时自动切换到 `questa/modelsim` 目录，以保证 Vivado 原始相对路径仍然正确

## 6. 保留与继承行为
重新生成时会尽量保留：
- 上一级已有 `my_sim.tcl` 中的用户波形块
- 上一级已有 `my_sim.tcl` 中最后一条 `run ...`

如果上一级还没有 `my_sim.tcl`，但目标 `questa/modelsim` 目录中已有同名 `my_sim.tcl`，则会继承其中的用户波形块后再生成新文件。

## 7. 已处理的问题
本版本同时修复了以下问题：
- Questa 安装路径包含空格时，启动 BAT 的命令引用问题
- Windows PowerShell 下回读 UTF-8 无 BOM 文件时，可能破坏中文用户区的问题
- 旧版本要求在 `questa` 目录内运行的问题，现已改为在上一级目录稳定运行
- `do xxx_wave.do` / `do "xxx_wave.do"` / `do {xxx_wave.do}` 等形式的兼容性问题
