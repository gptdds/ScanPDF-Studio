import re
from statistics import median

CHAPTER = re.compile(r"^第[零〇一二三四五六七八九十百千万两\d]+[章卷部篇]")
SECTION = re.compile(r"^第[零〇一二三四五六七八九十百千万两\d]+节")
SPECIAL = re.compile(r"^(序言|前言|引言|目录|后记|附录|参考文献|致谢)(?:\s.*)?$")
NUMBERED = re.compile(r"^(\d+(?:\.\d+){1,2})[、.\s]\s*\S")


def detect_chapters(page):
    text_blocks = [block for block in page.blocks if block.text and block.block_type == "body"]
    typical = median([block.height for block in text_blocks]) if text_blocks else 1
    for block in text_blocks:
        if block.manual_type:
            continue
        text = block.text.strip()
        left, top, right, bottom = block.rect
        if not text or len(text) > 60:
            continue
        centered = abs((left + right) / 2 - page.width / 2) < page.width * 0.14
        large = block.height > typical * 1.25
        above = [other.rect[3] for other in text_blocks if other.rect[3] < top]
        whitespace = top - max(above, default=0) > typical * 1.2
        numbered = NUMBERED.match(text)
        pattern = bool(CHAPTER.match(text) or SECTION.match(text) or SPECIAL.match(text) or numbered)
        score = (2.0 if pattern else 0) + (1 if centered else 0) + (1.5 if large else 0) + (0.8 if whitespace else 0)
        if score >= 2.8 and not re.search(r"[，。；！？]$", text):
            block.block_type = "heading"
            block.chapter_level = 2 if SECTION.match(text) else (
                min(3, numbered.group(1).count(".") + 1) if numbered else 1)

