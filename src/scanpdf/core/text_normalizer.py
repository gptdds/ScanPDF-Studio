import re

from opencc import OpenCC


CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
CONVERTER = OpenCC("t2s")


def to_simplified_chinese(text):
    text = str(text)
    if not text or not CJK.search(text):
        return text
    return CONVERTER.convert(text)


def normalize_cells(cells):
    return [[to_simplified_chinese(cell) for cell in row] for row in cells]
