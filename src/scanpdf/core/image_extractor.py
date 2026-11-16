from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from scanpdf.core.formula_handler import is_formula, simple_mathml
from scanpdf.core.table_detector import detect_tables
from scanpdf.models import Block, rectangle


def retain_regions(image, page, project_directory, settings, engine=None):
    directory = Path(project_directory)
    assets = directory / "assets"
    assets.mkdir(exist_ok=True)
    counter = [0]

    def save_crop(rect, kind):
        counter[0] += 1
        left, top, right, bottom = [int(value) for value in rect]
        left, top = max(0, left - 4), max(0, top - 4)
        right, bottom = min(page.width, right + 4), min(page.height, bottom + 4)
        path = assets / f"p{page.number:05d}-{kind}-{counter[0]:03d}.png"
        Image.fromarray(image[top:bottom, left:right]).save(path)
        return path.relative_to(directory).as_posix()

    def ocr_crop(rect):
        if engine is None:
            return [], None
        left, top, right, bottom = [int(value) for value in rect]
        crop = image[max(0, top):min(page.height, bottom), max(0, left):min(page.width, right)]
        return engine.recognize(crop, page.number)

    tables = detect_tables(image, page.blocks, page.number, save_crop,
                           ocr_crop if engine is not None else None)
    page.blocks.extend(tables)
    for block in page.blocks:
        if block.block_type == "body" and is_formula(block.text):
            block.block_type = "formula"
            block.mathml = simple_mathml(block.text)
            block.asset = save_crop(block.rect, "formula")
            if not block.mathml:
                page.warnings.append("复杂公式保留为图像，请校对公式区域。")
    if not settings.keep_images:
        return
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    mask = (gray < 215).astype(np.uint8) * 255
    for block in page.blocks:
        left, top, right, bottom = [int(value) for value in block.rect]
        cv2.rectangle(mask, (max(0, left - 8), max(0, top - 8)),
                      (min(page.width - 1, right + 8), min(page.height - 1, bottom + 8)), 0, -1)
    kernel = max(5, int(min(page.width, page.height) * 0.008))
    joined = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((kernel, kernel), np.uint8))
    contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        left, top, width, height = cv2.boundingRect(contour)
        area = width * height
        if area < page.width * page.height * 0.002 or width < 35 or height < 35:
            continue
        density = np.count_nonzero(mask[top:top + height, left:left + width]) / area
        if density < 0.04:
            continue
        if area > page.width * page.height * 0.8:
            page.warnings.append("存在大面积未识别区域，已保留区域图像供校对；可能是复杂版面或识别失败。")
        rect = (left, top, left + width, top + height)
        asset = save_crop(rect, "figure")
        page.blocks.append(Block(page.number, f"插图（第 {page.number} 页）", 1.0,
                                  rectangle(*rect), block_type="image", asset=asset))
        for block in page.blocks:
            if block.block_type == "body":
                centre_x = (block.rect[0] + block.rect[2]) / 2
                centre_y = (block.rect[1] + block.rect[3]) / 2
                if left <= centre_x <= left + width and top <= centre_y <= top + height:
                    block.block_type = "image_text"
                    block.excluded = True
    if tables:
        page.warnings.append("检测到表格：规则网格尝试重建；合并单元格或低可靠度结构以图像保留。")
