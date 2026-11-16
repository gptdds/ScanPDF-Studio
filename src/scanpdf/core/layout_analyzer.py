import re
from collections import defaultdict
from statistics import median

from scanpdf.core.chapter_detector import detect_chapters
from scanpdf.core.reading_order import reading_order


def analyze(page, settings):
    if settings.chapters:
        detect_chapters(page)
    typical = median([block.height for block in page.blocks if block.text]) if page.blocks else 1
    for block in page.blocks:
        if block.block_type != "body" or block.manual_type:
            continue
        left, top, right, bottom = block.rect
        text = block.text.strip()
        if re.match(r"^[图表圖]\s*[零一二三四五六七八九十\d]+", text) and block.height <= typical * 1.45:
            block.block_type = "caption"
        elif top > page.height * 0.70 and block.height < typical * 0.80 and re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩*†]|^\[\d+\]", text):
            block.block_type = "footnote"
        elif re.match(r"^(注[:：]|注释[:：]|註[:：])", text):
            block.block_type = "note"
        elif (top < page.height * 0.07 or bottom > page.height * 0.93) and re.fullmatch(r"[-—·\s]*\d{1,5}[-—·\s]*", text):
            block.block_type = "page_number"
            block.excluded = settings.clean_page_numbers
    page.blocks = reading_order(page.blocks, page.width, page.height, settings.reading_mode)
    _merge_caption_parts(page)
    return page


def _merge_caption_parts(page):
    ordered = sorted(page.blocks, key=lambda item: item.reading_order)
    pairs = list(zip(ordered, ordered[1:]))
    for block, following in reversed(pairs):
        if block.block_type != "caption" or following.block_type != "body":
            continue
        if len(block.text.strip()) > 16 or len(following.text.strip()) > 40:
            continue
        if following.excluded or block.excluded:
            continue
        vertical_gap = following.rect[1] - block.rect[3]
        horizontal_overlap = (min(block.rect[2], following.rect[2]) -
                              max(block.rect[0], following.rect[0]))
        vertical_overlap = (min(block.rect[3], following.rect[3]) -
                            max(block.rect[1], following.rect[1]))
        horizontal_gap = following.rect[0] - block.rect[2]
        same_line = (vertical_overlap > min(block.height, following.height) * 0.45 and
                     abs(block.rect[1] - following.rect[1]) < block.height * 0.55)
        next_line = (-block.height * 0.5 <= vertical_gap <= block.height * 1.4 and
                     horizontal_overlap > 0)
        if next_line or (same_line and horizontal_gap <= max(block.height, following.height) * 1.2):
            block.text = block.text.rstrip() + "  " + following.text.lstrip()
            following.excluded = True
            following.block_type = "caption"


def clean_repeated_margins(pages, settings):
    occurrences = defaultdict(set)
    candidates = []
    for page in pages:
        for block in page.blocks:
            if block.manual_type or block.block_type not in ("body", "header", "footer"):
                continue
            left, top, right, bottom = block.rect
            kind = "header" if bottom < page.height * 0.10 else (
                "footer" if top > page.height * 0.90 else "")
            if kind and block.text.strip():
                normalized = re.sub(r"\d+", "#", re.sub(r"\s", "", block.text))
                key = (kind, normalized)
                occurrences[key].add(page.number)
                candidates.append((block, key))
    minimum = max(2, min(4, len(pages) // 3))
    for block, key in candidates:
        if len(occurrences[key]) >= minimum:
            block.block_type = key[0]
            block.excluded = settings.clean_margins
        elif block.block_type in ("header", "footer"):
            block.block_type = "body"
            block.excluded = False

