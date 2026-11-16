from statistics import median


def _gaps(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(previous[1], current[0]) for previous, current in zip(merged, merged[1:])]


def reading_order(blocks, width, height, mode="auto"):
    if not blocks:
        return []
    typical_height = median(max(1, block.height) for block in blocks)
    vertical = mode == "vertical" or (mode == "auto" and
        sum(block.height > (block.rect[2] - block.rect[0]) * 1.8
            and len(block.text) > 3 for block in blocks) > len(blocks) * 0.55)
    if vertical:
        ordered = sorted(blocks, key=lambda block: (-round(block.rect[2] / max(typical_height / 4, 10)),
                                                  block.rect[1]))
        for index, block in enumerate(ordered):
            block.column = index
            block.reading_order = index
        return ordered
    column_counter = [0]

    def split(region, depth=0):
        if len(region) < 2 or depth > 20:
            for block in region:
                block.column = column_counter[0]
            return region
        horizontal_gaps = _gaps([(block.rect[0], block.rect[2]) for block in region])
        candidates = [gap for gap in horizontal_gaps if gap[1] - gap[0] > max(width * 0.015, 10)]
        if candidates:
            gap = max(candidates, key=lambda item: item[1] - item[0])
            cut = sum(gap) / 2
            left = [block for block in region if block.rect[2] <= cut]
            right = [block for block in region if block.rect[0] >= cut]
            left_span = max((block.rect[3] for block in left), default=0) - min(
                (block.rect[1] for block in left), default=0)
            right_span = max((block.rect[3] for block in right), default=0) - min(
                (block.rect[1] for block in right), default=0)
            substantial = ((len(left) >= 2 and len(right) >= 2) or
                           min(left_span, right_span) > typical_height * 2.2)
            if left and right and substantial and len(left) + len(right) == len(region):
                first = split(left, depth + 1)
                column_counter[0] += 1
                return first + split(right, depth + 1)
        vertical_gaps = _gaps([(block.rect[1], block.rect[3]) for block in region])
        candidates = [gap for gap in vertical_gaps if gap[1] - gap[0] > typical_height * 0.7]
        if candidates:
            gap = max(candidates, key=lambda item: item[1] - item[0])
            cut = sum(gap) / 2
            above = [block for block in region if block.rect[3] <= cut]
            below = [block for block in region if block.rect[1] >= cut]
            if above and below and len(above) + len(below) == len(region):
                return split(above, depth + 1) + split(below, depth + 1)
        ordered = sorted(region, key=lambda block: (round(block.rect[1] / max(typical_height * 0.5, 1)),
                                                    block.rect[0]))
        for block in ordered:
            block.column = column_counter[0]
        return ordered

    ordered = split(blocks)
    for index, block in enumerate(ordered):
        block.reading_order = index
    return ordered

