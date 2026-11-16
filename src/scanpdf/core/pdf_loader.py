from pathlib import Path

import fitz
import numpy as np


class PDFDocument:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.document = fitz.open(self.path)
        if not self.document.is_pdf:
            self.document.close()
            raise ValueError("请选择 PDF 文件。")
        if self.document.needs_pass:
            self.document.close()
            raise ValueError("PDF 已加密，请先用 PDF 阅读器解密后导入。")
        if not len(self.document):
            self.document.close()
            raise ValueError("PDF 不包含页面。")

    @property
    def page_count(self):
        return len(self.document)

    def render(self, number, dpi=220):
        if dpi not in (150, 200, 220, 300, 400):
            raise ValueError("不支持的 DPI。")
        page = self.document[number - 1]
        pixel_count = page.rect.width * page.rect.height * (dpi / 72) ** 2
        if pixel_count > 65_000_000:
            raise ValueError("页面过大（超过 6500 万像素），请降低 DPI。")
        pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
        return np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, 3).copy()

    def extract_images(self, number, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        page = self.document[number - 1]
        results = []
        for image in page.get_images(full=True):
            xref = image[0]
            extracted = self.document.extract_image(xref)
            path = directory / f"page-{number:05d}-xref-{xref}.{extracted['ext']}"
            path.write_bytes(extracted["image"])
            for rect in page.get_image_rects(xref):
                results.append({"path": str(path), "rect": list(rect),
                                "page_rect": list(page.rect)})
        return results

    def close(self):
        self.document.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

