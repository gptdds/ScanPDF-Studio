# ScanPDF Studio

ScanPDF Studio 是一款面向中文扫描书的 Windows 桌面工具。它在本地完成 PDF 页面渲染、PP-OCRv5 文字识别、版面与阅读顺序分析、段落/章节重建、图片与表格保留，并导出可重排的 EPUB 3。

程序不把扫描页整页塞进电子书。正文以流式 XHTML 输出，阅读器可以调整字号、字体、行距和背景色。

## 已实现功能

- Windows 10 / Windows 11 x64 便携版，终端用户无需安装 Python。
- PySide6 中文界面，支持浅色/深色主题。
- PP-OCRv5 Mobile / Server 两种质量模式。
- 简体中文、繁体中文、英文和中英混合选项。
- 页面方向检测、旋转纠正、倾斜校正、去噪、对比度增强和可选二值化。
- 单栏、双栏、多栏、横排和竖排启发式阅读顺序。
- 标题、正文、页眉、页脚、页码、图片、图注、表格、脚注和注释区域识别。
- 跨行段落、同页续行和跨页段落合并；页眉、页脚、页码可配置清理。
- 多级章节识别，纠正后可人工调整标题类型与 1–3 级层级。
- EPUB 3 的 `package.opf`、`nav.xhtml`、CSS、封面、图片、HTML 表格和基础 MathML。
- 图片区域在 EPUB 中保留原图，图注与图片分开记录。
- 表格网格可靠时重建 HTML table；不可靠时保留原表图片。
- 可视化 OCR 校对：点击文字定位原图区域、点击图片定位文字、编辑、合并、拆分、调整顺序、标记错误、撤销/重做和自动保存。
- 每页独立检查点和原始 OCR 结果；中断后只处理缺失页面。
- 批量队列、顺序处理、暂停、取消当前任务和停止队列。
- EPUBCheck 5.2.1（需要系统 Java）与内置 EPUB 结构检查。

## 便携版使用

1. 解压 `ScanPDFStudio-portable.zip`。
2. 双击 `ScanPDFStudio.exe`。
3. 在首页选择或拖入扫描版 PDF。
4. 在转换工作台确认设置并开始识别。
5. 识别完成后进入 OCR 校对，检查低置信度文字、图注、标题层级和表格。
6. 点击“导出校对后 EPUB”。

程序默认把项目和模型保存在：

```text
%APPDATA%\ScanPDFStudio
```

主要文件：

```text
history.sqlite3       转换历史
settings.json         界面与处理设置
projects\<uuid>\      项目目录
  project.json        项目元数据
  pages\*.json        每页结构化识别结果
  raw\*.json          原始 OCR 返回，不被校对覆盖
  pages\*.png         原始/预处理页面
  assets\             插图和表格图
models\               下载的 PP-OCRv5 模型
```

可以用环境变量覆盖数据目录：

```powershell
$env:SCANPDF_DATA_DIR = "D:\ScanPDFData"
.\ScanPDFStudio.exe
```

如果数据目录包含中文等非 ASCII 字符，程序会尝试使用现有盘符映射，或临时创建 `subst` 盘符供 Paddle 推理使用，退出时释放临时映射。

## 模型首次下载

模型没有伪装成已经打进 EXE。第一次开始识别时，程序按当前语言与质量模式下载所需模型：

- 标准简体中文：`PP-OCRv5_mobile_det`、`PP-OCRv5_mobile_rec`，方向检测开启时再下载 `PP-LCNet_x1_0_doc_ori`。
- 高质量模式：使用 `PP-OCRv5_server_det` 与 `PP-OCRv5_server_rec`。
- 英文：`en_PP-OCRv5_mobile_rec`。
- 繁体中文：使用 Server 识别模型。

下载来源为 PaddleX 官方模型托管地址：

```text
https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0
```

工作台显示真实下载进度；失败会自动重试 3 次。模型会缓存到数据目录，后续任务复用同一个模型实例和本地权重。标准中文首次下载约 30 MB 量级；Server 模型更大。

## 转换与续跑

- 转换在后台线程中运行，不阻塞界面。
- 每处理完一页，立刻写入 `pages\NNNNNN.json`，原始 OCR 单独写入 `raw\NNNNNN.json`。
- 取消、退出或崩溃后重新打开同一项目，只处理尚未完成的页面。
- 失败页会记录警告，不会静默跳过。
- 批量队列默认一次只跑一本 PDF，避免多个 OCR 模型同时占用内存。

## OCR 校对

校对台左栏显示原始扫描页，右栏显示结构化文字框。低置信度文字以橙色显示，手动标记的错误以红色显示。

可用操作：

- 点击文字框，左侧原图自动高亮对应区域。
- 点击原图区域，右侧列表自动定位对应文字。
- 修改文字后点“应用文字”。
- 合并上一段、在光标处拆分、上移、下移。
- 标记/取消错误标记。
- 用“结构”和“标题层级”把任意文字框改为正文、标题、图注、脚注等类型；标题可设为 1–3 级。
- `Ctrl+Z` 撤销、`Ctrl+Y` 重做、`Ctrl+S` 立即保存；正常操作本身会自动保存。

## EPUB 结构

- 只有最高一级识别标题会分章生成 XHTML 文件。
- 二级、三级标题保留在同一章内，并在目录中生成带锚点的嵌套列表。
- `nav.xhtml` 使用 EPUB 3 `epub:type="toc"`。
- 表格优先输出 HTML；可靠性不足时附原表图。
- 公式区域若有 MathML 则输出 MathML，否则保留公式图片。
- 封面优先使用项目 `assets` 中以 `cover` 开头的图片，否则自动生成封面。

## EPUBCheck

便携包内含 EPUBCheck 5.2.1。导出后若系统 `PATH` 中有 Java，程序会额外运行 EPUBCheck。Java 不是 OCR 或普通导出的必需依赖；没有 Java 时仍会执行内置 XML、manifest、spine、编码和资源检查。

手动验证：

```powershell
java -jar tools\epubcheck\epubcheck-5.2.1\epubcheck.jar output\samples\ScanPDF-Studio-sample.epub
```

## 源码安装

要求 Windows 10/11 x64、网络连接和 `uv`。

```powershell
.\INSTALL.bat
.\RUN.bat
```

等价命令：

```powershell
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -e . pytest reportlab pyinstaller
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scanpdf
```

## 构建便携版

```powershell
.\build.bat
```

产物：

```text
dist\ScanPDFStudio\ScanPDFStudio.exe
dist\ScanPDFStudio-portable.zip
```

构建使用 `ScanPDFStudio.spec`。spec 会排除不参与推理且会导致 PyInstaller 子进程崩溃的 `paddle.jit.sot`，并排除从外部 `PATH` 误收集的 Poppler ICU DLL，改用 Windows 系统 ICU 转发库。

`build.bat` 会把 `HOME`、`APPDATA`、`LOCALAPPDATA`、临时目录和 PaddleX 缓存指向仓库内的 `.build-home`。这样构建不依赖当前 Windows 用户目录的写权限；`.build-home` 可在构建完成后删除。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

真实 OCR 集成测试默认跳过，需显式启用：

```powershell
$env:RUN_OCR = "1"
.\.venv\Scripts\python.exe -m pytest -q tests\test_integration_ocr.py
```

测试覆盖 PDF 加载/渲染、预处理、OCR 结果解析、阅读顺序、段落重建、章节识别、图注合并、表格重建、EPUB 结构、中文编码、图片资源、检查点续跑、失败页记录、历史页数、队列和 GUI 导航。详细结果见 `TEST_REPORT.md`。

## GPU

界面提供 GPU 选项，但默认 EXE 捆绑的是 CPU 版 PaddlePaddle。若当前推理库不支持 CUDA，程序会明确提示并降级为 CPU，不会把 GPU 失败静默当成成功。启用 GPU 需要自行安装对应 CUDA/cuDNN 版本和 GPU 版 PaddlePaddle，并重新构建。

## 已知限制

- OCR 与版面分析是本地启发式流程，复杂古籍、竖排注疏、跨栏脚注和低清晰度扫描件仍可能需要较多人工校对。
- 复杂公式只保证结构简单时输出 MathML，复杂公式按图片保留。
- 表格检测依赖清晰直线网格；无边框、合并单元格和手写表格通常保留图片。
- 章节检测结合编号、字号、居中和留白，但仍可能误判；校对台可人工修正类型与层级。
- CPU OCR 有明显耗时，5 页 200 DPI 样本通常约需 1 分钟量级，具体取决于 CPU 和设置。
- 便携包体积较大，因为包含 Qt、PaddlePaddle、PaddleOCR、图像和 PDF 运行库。

## 许可与分发注意

本项目直接依赖中包含 **PyMuPDF，采用 AGPL-3.0 或 Artifex 商业许可**。对外分发、闭源商用或通过网络提供服务前，必须确认 AGPL 义务或购买商业许可。PySide6/Qt 采用 LGPL/GPL/商业多许可，分发时需要保留许可证与可替换共享库条件。其他第三方组件见 `THIRD_PARTY_LICENSES.md` 和 `licenses\`。

本 README 不构成法律意见。

## 目录结构

```text
src\scanpdf\
  app\            PySide6 界面、页面和主题
  core\           PDF、预处理、OCR、版面、段落、章节、表格、公式、EPUB
  services\       路径、模型、检查点、历史、设置和批量队列
  models.py       数据模型
  pipeline.py     单本转换与导出流程
tests\            自动化与真实 OCR 集成测试
tools\epubcheck\  EPUBCheck 5.2.1
resources\        应用图标
```
