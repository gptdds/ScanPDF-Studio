import re

from scanpdf.models import Paragraph

ENDING = re.compile(r"[。！？!?；;：:」』”’）)]$")
CJK = r"\u3400-\u9fff"


def join_text(first, second):
    first, second = first.rstrip(), second.lstrip()
    if not first:
        return second
    if not second:
        return first
    if re.search(r"[A-Za-z]-$", first) and re.match(r"[a-z]", second):
        return first[:-1] + second
    separator = " " if first[-1].isascii() and first[-1].isalnum() and second[0].isascii() and second[0].isalnum() else ""
    return first + separator + second


def normalize_text(text):
    text = re.sub(rf"(?<=[{CJK}]) +(?=[{CJK}])", "", text)
    text = re.sub(r"\s+([，。！？；：、])", r"\1", text)
    text = re.sub(rf"([，。！？；：、])\s+(?=[{CJK}])", r"\1", text)
    return text.strip()


def build_paragraphs(pages, settings):
    result = []
    previous_block = None
    previous_page = None
    for page in pages:
        columns = {}
        for block in page.blocks:
            if block.block_type == "body" and not block.excluded:
                columns.setdefault(block.column, []).append(block)
        bounds = {column: (min(block.rect[0] for block in blocks),
                           max(block.rect[2] for block in blocks))
                  for column, blocks in columns.items()}
        for block in page.blocks:
            if block.excluded:
                continue
            text = normalize_text(block.text)
            special = block.block_type not in ("body",)
            merge = False
            if result and previous_block and not special and result[-1].block_type == "body":
                left, top, right, bottom = block.rect
                previous_left, previous_top, previous_right, previous_bottom = previous_block.rect
                column_left, column_right = bounds.get(block.column, (left, right))
                indented = left - column_left > block.height * 0.9
                same_page = previous_page.number == page.number
                same_column = previous_block.column == block.column
                close = -block.height * 0.25 <= top - previous_bottom < block.height * 1.25
                full_line = previous_right >= column_right - previous_block.height * 1.5
                overlap = min(bottom, previous_bottom) - max(top, previous_top)
                same_line = (overlap > min(block.height, previous_block.height) * 0.45
                             and abs(top - previous_top) < block.height * 0.55
                             and left >= previous_right - 2)
                if same_page:
                    merge = (same_column and not ENDING.search(result[-1].text)
                             and ((not indented and close and full_line) or same_line))
                elif settings.merge_pages:
                    merge = (previous_page.number + 1 == page.number and
                             previous_bottom > previous_page.height * 0.72 and top < page.height * 0.28
                             and not indented and not ENDING.search(result[-1].text))
                merge = settings.paragraphs and merge
                if block.join_previous:
                    merge = True
            if block.break_before:
                merge = False
            if merge:
                result[-1].text = join_text(result[-1].text, text)
                result[-1].block_ids.append(block.id)
            else:
                result.append(Paragraph(text=text, block_type=block.block_type,
                                        level=block.chapter_level, block_ids=[block.id],
                                        asset=block.asset, cells=block.cells, mathml=block.mathml))
            block.paragraph_id = result[-1].block_ids[0]
            previous_block, previous_page = block, page
    return result

