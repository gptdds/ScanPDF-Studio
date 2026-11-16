# ScanPDF Studio 验收报告

- 版本：`0.1.1`
- 验收日期：2026-11-16
- 验收环境：Windows 10/11 x64、Python 3.11、OpenJDK 17.0.20.1
- 数据目录：`ScanPDFData`

## 0.1.1 变更

- 简体中文模式在 OCR 结果进入校对台前使用 OpenCC `t2s` 做词组级繁转简，原始模型输出仍保存在 `raw\`。
- 繁体中文模式保持原字形，不执行简繁转换。
- 导出旧项目时，正文与表格单元格也会按当前简体中文设置归一化，无需重新跑 OCR。
- 修复隔离构建环境下 `Compress-Archive` 不可用导致 ZIP 打包失败的问题，改用 Python 标准库生成便携包。

## 交付产物

| 产物 | 路径 | 结果 |
|---|---|---|
| 最终 EXE | `dist\ScanPDFStudio\ScanPDFStudio.exe` | 已启动并保持响应 |
| 便携目录 | `dist\ScanPDFStudio\` | 6,581 个文件，约 950.2 MiB |
| 便携 ZIP | `dist\ScanPDFStudio-portable.zip` | 406.6 MiB，7,574 个条目 |
| 真实验收 EPUB | `output\samples\ScanPDF-Studio-final.epub` | 1,222,892 字节 |

最终 EXE SHA-256：

```text
FBFA7BB4231DB3C2CADA5F181968178B4368BB6E3C345DE924F057E7B7D06D5E
```

真实验收 EPUB SHA-256：

```text
8AC331E3EAD8DD86A397437D2A3FE0B01E4CF2609CFD51810A8D161B280785C0
```

## 自动化测试

完整测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

结果：`19 passed, 1 skipped`，用时 43.58 秒。默认跳过项是真实 PaddleOCR 集成测试，避免普通回归测试重复下载或加载模型。

真实 PP-OCRv5 集成测试另行启用并通过：

```powershell
$env:RUN_OCR = "1"
.\.venv\Scripts\python.exe -m pytest -q tests\test_integration_ocr.py
```

结果：`1 passed`，用时 30.54 秒。覆盖真实 PaddlePaddle、PP-OCRv5 检测/识别链路及结构化 OCR 结果解析。

测试覆盖 PDF 加载与渲染、方向/倾斜预处理、OCR 置信度解析、简繁转换、原始 OCR 保留、正文/表格导出归一化、横排/竖排阅读顺序、跨页段落合并、章节与图注识别、重复页眉页脚清理、表格网格重建、EPUB 结构/中文编码/图片/表格、检查点续跑、失败页记录、历史数据、批量队列和 GUI 导航。

## 真实 OCR 验收

样本：`output\samples\chinese_scan.pdf`（5 页，58,001,107 字节）

项目：`ScanPDFData\projects\251195f6835e41f094aebd95ea38fa24`

结果：

- 5/5 页完成，项目状态为 `complete`。
- 共保存 35 个结构化文字框。
- 平均置信度为 98.0158%。
- 单框最低置信度约为 86.01%，最终校对记录显示“无低置信度”。
- 识别结果包含标题、正文、页码、图片、图注和表格块。
- 每页均生成检查点 JSON 和原始 OCR JSON；页面图片与处理后图片均已落盘。
- 处理期间未出现失败页，`error_pages` 为空。

## EPUB 3 验收

最终 EPUB 通过最终打包 EXE 的“转换工作台”重新导出。GUI 结果显示：

- 内置结构验证：通过。
- EPUBCheck：通过。

独立命令行复核：

```powershell
java -jar tools\epubcheck\epubcheck-5.2.1\epubcheck.jar output\samples\ScanPDF-Studio-final.epub
```

结果：

```text
Validating using EPUB version 3.3 rules.
No errors or warnings detected.
Messages: 0 fatals / 0 errors / 0 warnings / 0 infos
```

EPUB 内容抽查：

- 15 个 ZIP 条目，`mimetype` 为 `application/epub+zip`。
- 8 个 XHTML 文档，6 个导航链接，7 个一级至三级标题。
- 1 个封面、3 个图片引用、1 个图片块、1 个表格。
- 中文正文、章节锚点、导航目录、封面、CSS 与资源引用均可被 EPUBCheck 解析。
- 本次样本没有公式，因此真实样本未覆盖 MathML 输出；公式降级保留图片的路径由自动化测试覆盖。

## 最终 EXE 验收

- 最终 EXE 已通过界面验收，窗口标题为 `ScanPDF Studio`，界面显示 `0.1.1 · 本地处理`，窗口响应正常。
- 最终 EXE 从 `dist\ScanPDFStudio\ScanPDFStudio.exe` 启动，记录指向隔离数据目录 `ScanPDFData`。
- 便携 ZIP 已解压到独立临时目录；解压后的 `ScanPDFStudio.exe` 使用空数据目录启动并保持响应，成功创建 `history.sqlite3`。
- 已实际打开真实 5 页项目，工作台显示 5 页、98% 平均置信度和“已导出”状态。
- 已验证 GUI 导出到 `output\samples\ScanPDF-Studio-final.epub`。
- 已检查首页、转换工作台、OCR 校对台、转换历史、处理设置和深色主题；未见遮挡、溢出到窗口外或不可操作的主按钮。
- 历史页最新记录正确显示 5 页、98.1%、输出路径和“已导出”状态。
- 校对台可显示原始扫描页、结构化文字框、标题层级、合并/拆分/排序/标记错误等操作区。

构建包检查：

- 根目录未收集 Poppler 的 `icuuc.dll` / `icudt78.dll`，避免覆盖 Qt 使用的系统 ICU。
- `paddle\libs` 保留 12 个 Paddle 原生 DLL。
- PaddleX 及 OCR 依赖的包元数据已随包收集。
- OpenCC 配置与词典位于 `_internal\opencc\`；打包后已验证 `t2s` 可从该目录加载并输出简体结果。
- OpenCC Apache-2.0 许可证位于 `licenses\OpenCC-Apache-2.0.txt`。
- EPUBCheck 资源位于 `_internal\tools\epubcheck\epubcheck-5.2.1\`。
- 便携 ZIP 顶层直接包含 `ScanPDFStudio.exe`、README、测试报告、许可文件和 `licenses\`；未包含测试项目数据。

## 已知限制与未覆盖项

- 当前交付是 Windows 10/11 x64 便携版，不包含 macOS 或 Linux 构建。
- 本次真实验收样本为 5 页中文横排扫描书；尚未进行数百页、多栏古籍、竖排注疏、复杂脚注和低清晰度书籍的长时压力测试。
- 复杂公式只保证简单结构输出 MathML；复杂公式会降级为图片。本次真实样本不含公式。
- 无边框、合并单元格或手写表格可能降级为图片，仍需人工校对。
- 章节、阅读顺序和段落边界是本地启发式判断，复杂版式可能需要人工修正。
- CPU OCR 速度取决于硬件与 DPI；便携包包含 Qt、PaddlePaddle、PaddleOCR 和 PDF 运行库，因此体积约 950 MiB。
- EPUBCheck 需要系统 Java；没有 Java 时仍执行内置结构验证，但不会得到 EPUBCheck 第三方结论。
- GPU 选项存在，但当前默认 EXE 绑定 CPU 版 PaddlePaddle；使用 CUDA 需要另行安装匹配运行库并重新构建。
- 当前环境曾拒绝对桌面根目录的直接写入，因此最终导出验证写入项目内 `output\samples`；这属于运行环境权限限制，不是 EPUB 导出逻辑失败。

## 许可风险

项目直接依赖 **PyMuPDF**，其许可为 AGPL-3.0 或 Artifex 商业许可。对外分发、闭源商用或通过网络提供服务前，必须确认 AGPL 义务或取得商业许可。PySide6/Qt、PaddlePaddle、PaddleOCR、EPUBCheck 及其余组件的许可与声明见 `THIRD_PARTY_LICENSES.md` 和 `licenses\`。
