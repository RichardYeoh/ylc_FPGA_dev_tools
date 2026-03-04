# 仿真 DO 脚本自动生成说明（通用版）

## 1. 目录结构
将以下 3 个文件放在任意工程的：

`<project>.srcs\sim_1\sim_do_auto_gen\`

- `gen_my_sim.ps1`：主生成脚本（PowerShell）
- `gen_my_sim.bat`：便捷启动脚本（Windows）
- `仿真do脚本自动生成.md`：本说明

## 2. 使用前提（必须）
首次使用前，必须先在 Vivado 中至少运行一次仿真（Behavioral Simulation）。

原因：
- Vivado 会先生成基础脚本：`*_compile.do`、`*_elaborate.do`、`*_simulate.do`
- 本工具是基于这些脚本自动拼接并生成 `my_sim.do` / `my_sim.bat`

如果未先跑一次仿真，脚本会提示找不到 `*_compile.do`。

## 3. 生成方法
在 `sim_do_auto_gen` 目录下执行：

```bat
.\gen_my_sim.bat
```

或：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\gen_my_sim.ps1
```

## 4. 默认路径自动识别规则
脚本会自动推断目标目录（无需写死工程名）：

1. 优先按同级结构推断：  
`<project>.srcs` -> `<project>.sim\sim_1\behav\questa`
2. 若同目录下存在多个 `*.sim`，会优先选同名工程；否则回退到最近更新的一个。

若自动识别失败，可手动指定：

```powershell
.\gen_my_sim.ps1 -QuestaDir "D:\path\to\<project>.sim\sim_1\behav\questa"
```

## 5. 输出位置
默认输出到：

`<project>.sim\sim_1\behav\questa\`

- `my_sim.do`
- `my_sim.bat`

## 6. 后续自动运行
生成完成后，在输出目录执行：

```bat
.\my_sim.bat
```

即可调用 Questa/ModelSim 按 `my_sim.do` 自动运行仿真。

## 7. 覆盖更新行为
该工具是幂等覆盖模式：每次执行都会重写 `my_sim.do` 和 `my_sim.bat`，用于同步最新 Vivado 生成脚本。

建议在以下情况重新生成：
- RTL/仿真文件列表变化
- Vivado 重新导出仿真脚本
- 你修改了波形配置或运行时长策略

## 8. 可保留的自定义内容
在 `my_sim.do` 中，以下内容会尽量保留：

- `#user wave-watch add here` 到 `#user wave-watch add here end` 之间的波形块
- 最后一条 `run ...` 运行时长设置

因此可长期维护自己的波形观察列表和仿真时长，不必每次手工回填。

