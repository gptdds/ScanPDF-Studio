# Third-Party Licenses

ScanPDF Studio 0.1.0 bundles or depends on the components below. This file is a practical inventory, not legal advice. Installed package metadata and the upstream license text are authoritative.

## Important Distribution Warnings

### PyMuPDF

- Version: 2.1
- License declared by the package: **GNU Affero General Public License 3.0 or Artifex Commercial License**
- Upstream: https://github.com/pymupdf/PyMuPDF
- License information: https://pymupdf.readthedocs.io/en/latest/about.html#license

PyMuPDF is used for PDF loading and page rendering. Redistributing this application, using it commercially, or exposing it as a network service may require full AGPL compliance or a commercial license from Artifex. Review this before distribution.

### PySide6 / Qt

- Versions: PySide6 6.12.0, shiboken6 6.12.0, Qt 6.12.0 runtime
- Package license expression: **LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only**
- Upstream: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt licensing: https://www.qt.io/licensing
- LGPL obligations: https://www.qt.io/licensing/open-source-lgpl-obligations

The portable build uses shared Qt/PySide6 DLLs. Distributors must preserve applicable notices and license texts and comply with LGPL requirements for replacement/relinking of the Qt libraries. Qt may include additional third-party components with their own notices.

## Direct Runtime Components

| Component | Version | Declared license | Upstream |
|---|---:|---|---|
| PySide6 | 6.12.0 | LGPL-3.0 / GPL-2.0 / GPL-3.0 / commercial | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| shiboken6 | 6.12.0 | LGPL-3.0 / GPL-2.0 / GPL-3.0 / commercial | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| PyMuPDF | 2.1 | AGPL-3.0 / Artifex commercial | https://github.com/pymupdf/PyMuPDF |
| PaddleOCR | 3.3.2 | Apache-2.0 | https://github.com/PaddlePaddle/PaddleOCR |
| PaddleX | 3.3.13 | Apache-2.0 | https://github.com/PaddlePaddle/PaddleX |
| PaddlePaddle | 3.2.2 | Apache-2.0 | https://github.com/PaddlePaddle/Paddle |
| opencv-contrib-python | 4.10.0.84 | Apache-2.0 | https://github.com/opencv/opencv |
| Pillow | 13.0.0 | HPND / PIL license | https://github.com/python-pillow/Pillow |
| NumPy | 2.2.6 | BSD-3-Clause and bundled notices | https://github.com/numpy/numpy |
| lxml | 6.1.3 | BSD-3-Clause | https://github.com/lxml/lxml |
| requests | 2.34.2 | Apache-2.0 | https://github.com/psf/requests |
| OpenCC Python | 0.1.7 | Apache-2.0 | https://github.com/yichen0831/opencc-python |

## Bundled Transitive Components

| Component | Version | Declared license | Upstream |
|---|---:|---|---|
| pandas | 3.1.1 | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| Shapely | 2.2.0 | BSD-3-Clause | https://github.com/shapely/shapely |
| pyclipper | 1.4.0 | MIT | https://github.com/fonttools/pyclipper |
| ujson | 6.1.0 | BSD-3-Clause / Apache-2.0 | https://github.com/ultrajson/ultrajson |
| pydantic | 2.14.3 | MIT | https://github.com/pydantic/pydantic |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| certifi | 2026.10.23 | MPL-2.0 | https://github.com/certifi/python-certifi |
| pypdfium2 | 5.15.2 | Apache-2.0 / BSD-3-Clause and dependency notices | https://github.com/pypdfium2-team/pypdfium2 |
| onnxruntime | 1.32.0 | MIT | https://github.com/microsoft/onnxruntime |
| modelscope | 1.40.3 | Apache-2.0 | https://github.com/modelscope/modelscope |
| huggingface-hub | 2.4.0 | Apache-2.0 | https://github.com/huggingface/huggingface_hub |
| safetensors | 0.8.0 | Apache-2.0 | https://github.com/huggingface/safetensors |
| tqdm | 4.70.1 | MPL-2.0 / MIT | https://github.com/tqdm/tqdm |
| filelock | 4.2.10 | Unlicense | https://github.com/tox-dev/filelock |
| networkx | 3.6.1 | BSD-3-Clause | https://github.com/networkx/networkx |
| ruamel-yaml | 0.19.1 | MIT | https://sourceforge.net/projects/ruamel-yaml/ |
| prettytable | 3.18.0 | BSD-3-Clause | https://github.com/jazzband/prettytable |
| protobuf | 7.36.2 | BSD-3-Clause | https://github.com/protocolbuffers/protobuf |

The portable bundle also contains transitive native and Python libraries required by these packages, including their own notices. See the `*.dist-info\licenses` folders in the source environment and the packaged `licenses` directory.

## Build and Validation Tools

| Component | Version | License | Upstream |
|---|---:|---|---|
| PyInstaller | 6.22.3 | GPL-2.0-or-later with bootloader exception | https://github.com/pyinstaller/pyinstaller |
| pyinstaller-hooks-contrib | 2026.10 | Apache-2.0 / GPL-2.0 with exceptions | https://github.com/pyinstaller/pyinstaller-hooks-contrib |
| EPUBCheck | 5.2.1 | BSD-3-Clause | https://github.com/w3c/epubcheck |
| pytest | test dependency only | MIT | https://github.com/pytest-dev/pytest |
| reportlab | test/sample generation only | BSD-3-Clause | https://github.com/MrBitBucket/reportlab-mirror |

EPUBCheck includes additional Java dependencies. Their notices are shipped in:

```text
tools\epubcheck\epubcheck-5.2.1\THIRD-PARTY.txt
tools\epubcheck\epubcheck-5.2.1\licenses\
```

Java itself is **not bundled**. EPUBCheck is an optional external validation step provided by the user's Java runtime.

## OCR Models

ScanPDF Studio downloads inference models from the official PaddleX model host on first use. The model weights are not included in the EXE or portable ZIP.

Model families:

- PP-OCRv5 detection and recognition
- EN PP-OCRv5 recognition
- PP-LCNet document orientation classification

Upstream projects and terms:

- https://github.com/PaddlePaddle/PaddleOCR
- https://github.com/PaddlePaddle/PaddleX
- https://www.paddlepaddle.org.cn/

Before redistributing downloaded model weights separately, verify the current upstream model license and notices. ScanPDF Studio itself does not relicense those weights.

## System Components

The application uses Windows system libraries and, through Qt, the Windows ICU forwarding DLLs. Windows system components are not licensed under this project and should not be extracted or redistributed independently of the operating system terms.

## No Additional Grant

This inventory does not grant rights beyond each component's own license. It also does not replace the complete license texts shipped with dependencies.
