import cv2
import numpy as np

from scanpdf.models import Block, rectangle


def _line_centers(values):
    groups = []
    for position in values:
        if groups and position - groups[-1][-1] <= 3:
            groups[-1].append(int(position))
        else:
            groups.append([int(position)])
    return [int(np.mean(group)) for group in groups]


def detect_tables(image, blocks, page_number, save_crop, ocr_crop=None):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    height, width = gray.shape
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(30, width // 25), 1)))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, height // 35))))
    grid = cv2.bitwise_or(horizontal, vertical)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tables = []
    for contour in contours:
        left, top, box_width, box_height = cv2.boundingRect(contour)
        if box_width < width * 0.12 or box_height < height * 0.025:
            continue
        horizontal_crop = horizontal[top:top + box_height, left:left + box_width]
        vertical_crop = vertical[top:top + box_height, left:left + box_width]
        rows = _line_centers(np.flatnonzero((horizontal_crop > 0).mean(axis=1) > 0.65))
        columns = _line_centers(np.flatnonzero((vertical_crop > 0).mean(axis=0) > 0.65))
        if len(rows) < 3 or len(columns) < 3:
            continue
        rect = (left, top, left + box_width, top + box_height)
        contained = []
        recognized = 0
        cells = [["" for _ in range(len(columns) - 1)] for _ in range(len(rows) - 1)]
        reliable = True
        source_blocks = list(blocks)
        if ocr_crop:
            crop_blocks, _ = ocr_crop(rect)
            for block in crop_blocks:
                block.bounding_box = [
                    [point[0] + left, point[1] + top] for point in block.bounding_box]
            source_blocks.extend(crop_blocks)
        for block in source_blocks:
            bleft, btop, bright, bbottom = block.rect
            center_x, center_y = (bleft + bright) / 2 - left, (btop + bbottom) / 2 - top
            if 0 <= center_x <= box_width and 0 <= center_y <= box_height:
                recognized += 1
                if block in blocks:
                    contained.append(block)
                row = int(np.searchsorted(rows, center_y) - 1)
                column = int(np.searchsorted(columns, center_x) - 1)
                if 0 <= row < len(cells) and 0 <= column < len(cells[0]):
                    cells[row][column] += (" " if cells[row][column] else "") + block.text
                    if block.confidence < 0.80:
                        reliable = False
                    if (bleft - left < columns[column] - 5 or
                            bright - left > columns[column + 1] + 5):
                        reliable = False
                else:
                    reliable = False
        asset = save_crop(rect, "table")
        if not recognized:
            reliable = False
        for block in contained:
            blocks.remove(block)
        tables.append(Block(page_number, "表格", 1.0, rectangle(*rect), block_type="table",
                            asset="" if reliable else asset,
                            cells=cells))
    return tables

