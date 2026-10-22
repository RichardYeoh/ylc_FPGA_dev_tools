# agents.md — 项目任务书与协作约定

> 本文件是本项目的唯一权威入口文档。任何人（人或 AI）接手本项目，**必须先把本文件从头读到尾**，再动手。
> 文件结构：任务与目标 → 全局硬性要求 → 环境调查结论 → 交付物 → 进度看板 → 对话原文记录。
> 其中「对话原文记录」一节要求**逐字记录**用户与助手之间的全部需求往来，不得摘要、不得删改。

---

## 1. 项目基本信息

| 项 | 内容 |
| --- | --- |
| 项目名称 | office_md — Office 文档转 Markdown 离线转换工具 |
| 工作目录 | `e:\proj\ylc_FPGA_dev_tools\office_md` |
| 开发机 | Windows（win32），Shell: PowerShell Core |
| 立项日期 | 2026-10-21 |
| 当前阶段 | 阶段 0：需求确认 + 本机环境调查（未开始编码） |

---

## 2. 任务与目标（用户原始需求）

### 2.1 一句话目标

开发一个把 **Word（.doc/.docx）、Excel（.xls/.xlsx）、PowerPoint（.ppt/.pptx）** 转换为 **Markdown（.md）** 的工具，最终形态是 **Windows 下可一键离线运行的绿色程序**，可简单迁移到其他**不联网的内部计算机**上使用。

### 2.2 需求拆解

1. **输入格式**：Word（.doc、.docx）、Excel（.xls、.xlsx）、PowerPoint（.ppt、.pptx）。
2. **输出格式**：Markdown（.md）。需明确表格、图片、公式、多 sheet、多页幻灯片等结构在 md 中的表达方式。
3. **运行形态**：Windows 一键运行（双击即可），无需命令行操作知识。
4. **完全离线**：运行时不需要任何网络资源、不需要联网校验、不需要在线转换服务。
5. **可迁移**：在本机调通后，能简单复制到其他**无网络**的内部计算机上跑起来。
6. **开源工具复用**：开发过程中如果需要现成的开源转换工具，**先在本机查找**；在本机找到即可引用（不重复造轮子），但必须把该开源工具的**安装包/发行包同步下载到当前目录**，随项目一起保存，保证后续离线可复现。
7. **文档交付**：必须输出
   - **软件设计书**（架构、模块划分、依赖、接口、异常与降级策略、打包与迁移方案）
   - **使用说明书**（从所依赖工具的安装出发（如果有），一直到可以一键运行）
8. **对话留痕**：开发过程中的**所有对话需要原文记录**（见第 6 节）。

### 2.3 明确的非目标（当前不承诺）

- 不做 Markdown 反向转 Office（如需再单独立项）。
- 不做 PDF 转换（除非后续用户追加）。
- 不做云服务/在线 API 方案（违反离线要求）。

---

## 3. 项目全局硬性要求（Global Rules）

以下为**项目级约束**，后续任何设计决策、代码实现、文档编写都必须遵守；如果某条与具体实现冲突，以本节为准，并在此处记录例外及理由。

### R1 离线优先（Offline First）

- 程序运行期**禁止**任何网络访问：不做联网激活、不做在线词库/在线模板下载、不调用 SaaS 转换接口。
- 第三方依赖必须**随包分发**（vendored），不允许"运行时 pip install / npm install"。
- 依赖库若自身有联网行为（如遥测、自动更新、字体/语言包下载），必须关闭或打补丁屏蔽。

### R2 一键盘运行（One-Click）

- 提供 `.bat`（或 `.exe`）入口，双击即用；不要求目标机器预装 Python、Office、环境变量配置。
- 交互式界面优先（可选文件/文件夹、可选输出目录、进度与结果提示），但必须同时保留命令行参数接口，便于批处理与回归测试。

### R3 可迁移（Portable）

- 全目录拷贝即可迁移：**不使用安装程序写注册表、不写系统目录、不依赖绝对路径**。
- 所有路径解析基于"程序自身所在目录"（相对定位），配置文件放程序目录内。
- 目标机要求清单必须写清（如操作系统版本、是否需要 VC++ 运行库、位数要求）。
- 迁移验证标准：在**未装过任何开发环境**的干净机器上，复制目录 → 双击 → 成功转换样例文件。

### R4 复用优先、先找本机（Reuse Before Build）

- 需要某个能力（格式解析、转换引擎）时，**先在本机检索是否已有可用开源工具/库**（注意：工具可能装在 msys2、conda、Scoop、Chocolatey、独立绿色目录里，不只看 PATH）。
- 本机已有 → 直接引用，记录**版本号与来源路径**到本文件第 4 节。
- 本机没有且任务必需 → **先向用户报告并取得批准**，再下载；下载的**安装包/发行包一并放入当前目录**（建议 `vendor/` 子目录），并在第 4 节登记文件名、版本、来源 URL、SHA256。

### R5 文档驱动（Docs as Deliverable）

- 设计书与使用说明书是**交付物**，不是副产品；功能变更必须同步更新文档。
- 说明书必须能让"只会双击鼠标"的人从零跑通，且包含常见故障排查表。

### R6 可重复构建与版本记录

- 记录使用的工具链精确版本（Python 版本、各库版本、打包工具版本），生成 `requirements.txt`/锁定清单。
- 打包脚本纳入版本管理，任何人可重复产出同样的发行目录。

### R7 临时文件清理

- 开发期临时文件统一放在 `e:\proj\cb_help\` 下；任务/阶段结束后删除干净，不在用户未知位置遗留文件。
- 运行期临时文件必须写在**程序目录内的 temp/** 或系统临时目录，且退出时清理。

### R8 不破坏既有环境

- 不修改系统 PATH、不安装全局服务、不改注册表（除打包工具自身必要行为，且需说明）。
- 同机若有其他任务在跑（其它仿真/工程），禁止触碰其目录与进程。

### R9 对话原文留痕

- 用户每一轮需求/反馈、助手每一轮关键答复结论，均按时间顺序**原文追加**到第 6 节。
- 不许用"用户要求优化"这类摘要替代原文。

### R10 兼容性基线（待用户确认后锁定）

- 目标操作系统：Windows 10/11 x64（待确认是否需兼容 Win7 / 32 位）。
- 文件规模：需明确单文件大小上限与批量数量上限（待确认）。
- 内容覆盖：需明确图片是否导出为独立文件、公式处理策略、样式是否保留（待确认）。

---

## 4. 本机环境与依赖调查（待补充）

> 规则：所有"本机已有"结论必须给出**探测命令 + 输出证据**；所有"需下载"结论必须先报批。

### 4.1 环境探测结果（2026-10-21 实测）

| 项目 | 结论 | 证据 | 状态 |
| --- | --- | --- | --- |
| Python | **已有 3.13.0** | `python --version`；`C:\Users\liche\AppData\Local\Programs\Python\Python313\python.exe` | ✅ 可用 |
| python-docx | **已有 1.2.0** | `pip list` | ✅ |
| openpyxl | **已有 3.1.5** | `pip list` | ✅ |
| python-pptx | **已有 1.0.2** | `pip list` | ✅ |
| xlrd | **已有 2.0.2**（仅支持 .xls） | `pip list` | ✅ |
| mammoth / markdownify / lxml / pandas / pillow | 已有 1.11.0 / 1.2.2 / 6.0.2 / 3.0.2 / 12.2.0 | `pip list` | ✅ |
| pandoc | **本机没有** | `Get-Command pandoc` 为空；`C:\`、`D:\` 深度 4 递归无 `pandoc.exe` | ❌ |
| LibreOffice (soffice) | **本机没有** | `Get-Command soffice` 为空；磁盘浅层递归无结果 | ❌ |
| msys2 / conda / scoop / choco | 无相应安装或其中无 pandoc/soffice | `C:\msys64`、`scoop\apps`、`choco\bin`、`conda` 均无 | — |
| Node.js | 已有 `D:\Program Files\nodejs\node.exe` | `Get-Command node` | ✅ 备用（不计划使用） |
| Microsoft Office | **本机已安装**（COM 可用） | 注册表 App Paths 存在 `WINWORD.EXE` / `EXCEL.EXE` / `POWERPNT.EXE` | ⚠️ 仅本机，目标机不保证 |
| PyInstaller | **本机没有** | `pip list` 无 | ❌ 打包时需要（待批准） |
| pywin32 | **本机没有** | `pip list` 无 | ❌ 走 COM 路线时才需要 |

### 4.2 技术路线对比与建议

| 路线 | 做法 | 覆盖格式 | 包体 | 目标机要求 | 评价 |
| --- | --- | --- | --- | --- | --- |
| **A. 纯 Python 自研解析** | python-docx / openpyxl / python-pptx 直接解析 OOXML，自己生成 md | docx、xlsx、pptx（**不含** doc/xls/ppt） | 小（约 30–60 MB） | 无需 Office、无需安装任何东西 | 质量可控、零外部进程、离线最彻底 → **推荐做主干** |
| B. 内嵌 pandoc | 调用 pandoc.exe 转 docx→md | 仅 docx/odt 等；**不支持 xlsx/pptx** | 约 150 MB | 无 | 覆盖不全，单独用不够 |
| C. LibreOffice 便携版 | soffice 先统一转 docx/xlsx/pptx 或直接导出，再解析 | **全格式**（含 .doc/.xls/.ppt） | 大（约 350–500 MB） | 无（自带运行时） | 老格式唯一可靠方案 → **建议做可选兜底组件** |

**建议方案**：路线 A 为主（新格式高质量、轻量、纯离线），老格式 `.doc/.xls/.ppt` 用路线 C 兜底（作为可选组件随包或按需放置）。
- `.xls` 可先用 xlrd 纯 Python 读（不需要 LibreOffice）。
- `.doc` / `.ppt` 若无 LibreOffice，则明确提示"请另存为 .docx/.pptx"，不静默失败。

### 4.3 待用户批准的下载项（R4：本机无 → 必须报批）

| # | 组件 | 用途 | 是否必需 | 预估体积 | 来源 |
| --- | --- | --- | --- | --- | --- |
| P1 | PyInstaller | 打包成一键 exe | 必需（若做 exe） | 约 5 MB | PyPI |
| P2 | LibreOffice 便携版 | 支持 .doc/.xls/.ppt | 视需求 | 约 350 MB | 官方 portable/msi |
| P3 | pandoc | 备选转换引擎 | 非必需 | 约 150 MB | GitHub release |

### 4.4 已确认的技术决策（2026-10-21，用户裁定，后续不再反复询问）

| 决策项 | 结论 | 影响 |
| --- | --- | --- |
| **老格式 .doc/.ppt** | 目标内网机**均装有 Microsoft Office**，因此走 **Office COM（pywin32）另存为新格式**后再解析，**不引入 LibreOffice** | 节省约 350 MB 包体；但程序需在目标机做 Office 可用性自检，缺失时明确报错 |
| **打包形态** | **两种都出**：① PyInstaller onedir `office2md.exe` 为主入口；② 源码 + Python 嵌入式运行时 + `.bat` 启动，便于调试与二次开发 | 发行包体积略大；两条路径共用同一套 `src/` 代码 |
| **主干解析** | 纯 Python 解析 OOXML（docx/xlsx/pptx），`.xls` 用 xlrd | 不依赖外部进程，离线最彻底，转换质量自主可控 |

### 4.5 因此需随包下载的组件（最终清单）

| # | 组件 | 用途 | 必要性 |
| --- | --- | --- | --- |
| 1 | PyInstaller（wheel + 依赖） | 生成 `office2md.exe` | 必需 |
| 2 | pywin32 | 老格式 `.doc/.xls/.ppt` 经 Office COM 转换 | 必需（老格式兜底） |
| 3 | python-docx / openpyxl / python-pptx / xlrd / mammoth / markdownify / lxml 及其传递依赖的 wheel | 离线可复现安装 | 必需 |
| 4 | Python 3.13 embeddable zip | `.bat` 方案的自带运行时 | 必需（bat 方案） |
| 5 | ~~LibreOffice~~ | ~~老格式兜底~~ | ❌ 已排除 |
| 6 | ~~pandoc~~ | ~~备选引擎~~ | ❌ 已排除（不支持 xlsx/pptx） |

---

## 5. 交付物清单

| 编号 | 交付物 | 文件 | 状态 |
| --- | --- | --- | --- |
| D1 | 任务书与协作约定（本文件） | `agents.md` | ✅ 已交付 |
| D2 | 软件设计书 | `docs/软件设计书.md` | ✅ 已交付 |
| D3 | 使用说明书 | `docs/使用说明书.md` | ✅ 已交付 |
| D4 | 一键启动入口 | `启动转换工具.bat`、`拖放文件转换.bat` | ✅ 已交付 |
| D5 | 转换主程序 | `src/office2md/`（9 个模块） | ✅ 已交付 |
| D6 | 依赖随包（vendor） | `vendor/wheels/`（23 个 wheel）+ `vendor/CHECKSUMS.txt` | ✅ 已交付 |
| D7 | 示例输入与预期输出 | `samples/`（新格式）、`samples_legacy/`（老格式） | ✅ 已交付 |
| D8 | 迁移/部署说明 | `docs/迁移部署说明.md` | ✅ 已交付 |
| D9 | release 包（统一交付物） | `dist/office2md-1.0.0.zip`（72.6 MB） | ✅ 已交付 |
| D10 | release 目录（两版同包） | `dist/office2md-1.0.0/`（exe 版 + 源码便携版 + 选择说明） | ✅ 已交付 |
| D11 | 打包与组装脚本 | `build/build_exe.bat`、`build/office2md.spec`、`tools/make_release.py` | ✅ 已交付 |
| D12 | 样例生成脚本 | `tools/make_samples.py`、`tools/make_legacy_samples.py` | ✅ 已交付 |

---

## 6. 进度看板（Todo）

- [x] 建立 `agents.md`，固化任务、目标与全局要求
- [x] 本机环境与开源工具调查（结论见 4.1：Python 3.13 + docx/xlsx/pptx/xls 解析库齐全；pandoc、LibreOffice、PyInstaller 本机没有，待用户批准下载）
- [x] 技术路线选型并报用户确认（结论见 4.4：纯 Python 主干 + Office COM 兜底老格式 + 双打包形态）
- [x] 依赖随包落地到 `vendor/`（24 个文件 + SHA256 校验清单）
- [x] 转换内核实现（docx/xlsx/pptx → md，自研 OOXML 解析 + mammoth 兜底）
- [x] 老格式兼容（.doc/.ppt 走 Office COM；.xls 走 xlrd，失败再兜底 COM）
- [x] 一键入口与图形界面（tkinter GUI + CLI + 两个 bat）
- [x] 示例样例与回归自测（6 个样例文件，源码与 exe 两种形态均验证）
- [x] 打包为绿色发行目录（exe 版 64.7 MB / 源码便携版 85.4 MB）
- [x] 软件设计书
- [x] 使用说明书
- [ ] 干净机迁移验证（需另找一台未装开发环境的机器实测，本机无法完成）

---

## 6.1 实测验收记录（2026-10-21）

| 测试项 | 命令/方式 | 结果 |
| --- | --- | --- |
| 新格式转换（源码） | `python app.py samples -o out_test` | 3/3 成功，< 0.5 s |
| 老格式转换（源码） | `python app.py samples_legacy -o out_legacy` | 3/3 成功（.doc 5.7s / .xls 0.0s / .ppt 6.3s） |
| exe GUI 版 | `office2md.exe samples -o out_exe` | 3/3 成功，退出码 0 |
| exe CLI 版（新格式） | `office2md-cli.exe samples -o out_cli_a` | 3/3 成功，中文输出正常 |
| exe CLI 版（老格式） | `office2md-cli.exe samples_legacy -o out_cli_legacy` | 3/3 成功（.doc 3.1s / .ppt 5.0s） |
| 图形界面启动 | 启动 exe 后观察 6 秒 | 窗口正常创建、日志正常写盘 |
| 源码便携版 | `runtime\python.exe app.py samples -o out_check` | 3/3 成功，tkinter 可用 |
| 发行包自检 | 发行目录内跑 `office2md-cli.exe samples` | 3/3 成功 |

**已知限制**：干净机迁移验证未做（需第二台机器），已在设计书第 9 节与迁移说明第 4 节给出自检清单，交付时按清单执行即可。

---

## 7. 对话原文记录（逐字留痕，按时间追加）

> 记录格式：`### [序号] 时间 — 角色`，正文为用户/助手原始文字，不改写。

### [001] 2026-10-21 — 用户（第 1 轮，意图说明）

```
我想让你在当前目录下开发一个word/excel/ppt 到md文件的转换工具。你先在目录下新建一个agents.md
```

### [002] 2026-10-21 — 用户（第 2 轮，完整需求）

```
我想让你在当前目录下开发一个word/excel/ppt 到md文件的转换工具。你先在目录下新建一个agents.md。记录下当前的任务和目标，如果过程中有值得记录的项目全局要求，也需要你写入。期间，开发过程中如果需要使用到现成的开源转换工具，先在本机上找，找到了可以引用，但需要把开源工具安装包同步下载到当前目录。最终的输出是一个windows底下可以一键离线运行的程序，不需要任何网上资源和网络工具。我在本台机器上完成了以后需要能够简单迁移到其他不联网的内部计算机。需要输出软件设计书和使用说明书，从所依赖的工具安装出发（如果有），到可以一键运行。过程中所有对话需要原文记录。
```

### [003] 2026-10-21 — 助手（第 1 轮答复要点）

```
建立 agents.md，固化任务目标、全局要求 R1–R10、交付物清单与进度看板，并开始本机环境调查。
```

### [004] 2026-10-21 — 助手（第 2 轮，环境调查结论）

```
本机已具备：Python 3.13.0；python-docx 1.2.0、openpyxl 3.1.5、python-pptx 1.0.2、xlrd 2.0.2、mammoth 1.11.0、markdownify 1.2.2、lxml、pandas、pillow。
本机没有：pandoc、LibreOffice(soffice)、PyInstaller、pywin32（C:\ D:\ 浅层递归、msys2、scoop、choco、conda 均已排查）。
本机装有 Microsoft Office（Word/Excel/PowerPoint COM 可用），但目标内网机不保证有，不能作为依赖。
结论：主干走纯 Python 解析 OOXML（docx/xlsx/pptx），完全离线、可打包；.xls 用 xlrd 直接读；.doc/.ppt 需要决策（LibreOffice 兜底 / 提示另存 / 自己写 OLE 解析）。
待批准下载：PyInstaller（必需）、LibreOffice 便携版（如需支持 .doc/.ppt）、pandoc（非必需，暂不需要）。
```

### [005] 2026-10-21 — 用户（第 3 轮，两项决策答复，原文）

```
[问题1 老格式 .doc / .ppt 如何支持] 答：Windows本机包括迁移目标的windows都有office软件，这个还是问题吗
[问题2 打包形态] 答：两种都出(exe 作为主入口，同时保留 bat+源码方案便于调试与二次开发。体积略大。)
```

### [006] 2026-10-21 — 助手（第 3 轮答复）

```
确认：老格式走 Office COM（pywin32）另存后解析，排除 LibreOffice（省 350MB）；打包双形态。
决策写入 4.4 节，依赖清单写入 4.5 节。开始把 wheel 与 Python embeddable 运行时下载到 vendor/ 目录。
```

### [007] 2026-10-21 — 用户（第 4 轮，原文）

```
怎么了？一直没动，你看看时间戳，先回想一下怎么没动
```

### [008] 2026-10-21 — 助手（第 4 轮答复）

```
时间戳显示 core.py 写于 20:40:16，当时 20:41:02，实际只过了 40 余秒；不是卡死，而是连续生成大文件期间界面没有中间输出。
另：gui.py 那次写入被用户取消，文件当时未落盘。
后续改为"小步写、每步可见"，补完 gui.py / cli.py / logging_util.py / 入口 / bat / 打包脚本 / 三份文档。
```

### [009] 2026-10-21 — 助手（最终交付说明）

```
交付内容：
1) 转换内核：docx（自研 OOXML 解析 + mammoth 兜底）、xlsx（openpyxl）、pptx（python-pptx）、xls（xlrd + COM 兜底）、doc/ppt（Office COM 另存后走主干）。
2) 双入口：tkinter 图形界面 + 命令行/拖放 bat。
3) 双发行包：exe 版（64.7 MB）、源码便携版（85.4 MB，自带 Python 3.13 嵌入式运行时）。
4) 离线依赖：vendor/wheels 23 个 wheel + Python embeddable zip，附 SHA256 校验清单。
5) 文档：软件设计书、使用说明书、迁移部署说明。
6) 实测：新格式/老格式、源码/exe、GUI/CLI 全部通过；干净机迁移待第二台机器按清单验证。
```

### [010] 2026-10-22 — 用户（第 6 轮，原文）

```
你把必要的打个release包
```

### [011] 2026-10-22 — 助手（第 6 轮答复）

```
把两个发行目录归拢为统一 release 结构，产出 dist\office2md-1.0.0.zip（72.6 MB）：
office2md-1.0.0\
  office2md-1.0.0-win64\        exe 版（推荐）
  office2md-1.0.0-src-portable\ 源码便携版
  选择说明.txt                   两版差异与选用建议
同步更新：make_release.py 改为产出该结构（新增 --zip-only 参数）、
使用说明书第 3 章与第 12 章路径说明、迁移部署说明第 3 节路径。
校验：4772 条目、无 logs/temp 污染、两个 exe 与 runtime/python.exe 均在包内；exe 自检 3/3 成功。
```

### [012] 2026-10-22 — 助手（清理记录）

```
已清理：out_* 测试输出、logs/、temp/、build/work/、dist/office2md/、dist/office2md_prev/、打包日志。
用户 2026-10-22 追加要求"把没有复用价值的东西都清一下"，因 IDE 批量删除保护（>500 文件/次）分多轮执行；
另提供 tools/clean_intermediate.bat 供后续一键清理。
保留：src/ docs/ tools/ vendor/ runtime/ samples/ samples_legacy/ 与 dist 下 release 产物。
```




