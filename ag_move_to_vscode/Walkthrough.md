# Walkthrough

## 本次新增内容

- 增加了 `执行Antigravity迁移到VSCode.ps1`
- 增加了 `可自动完成程度评估.md`
- 保留了原先的 `Antigravity迁移到VSCode完整指南.md`

## 推荐你先看的顺序

1. 先看 `可自动完成程度评估.md`
2. 再看 `Antigravity迁移到VSCode完整指南.md`
3. 最后决定是否执行 `执行Antigravity迁移到VSCode.ps1`

## 推荐执行方式

先做一次只生成迁移包、不改 VS Code 配置的试运行：

```powershell
.\\执行Antigravity迁移到VSCode.ps1
```

确认输出无误后，再执行真实配置复制：

```powershell
.\\执行Antigravity迁移到VSCode.ps1 -ApplyConfig -GenerateExtensionInstallScript
```

## 我对“能不能帮你做完”的判断

- 能完成大部分
- 不能保证 100% 原样复制 Antigravity 专有能力
- 如果你允许我继续执行到真实用户目录层面，我可以继续把迁移往前推进
