from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw


def _text_page(number):
    if number == 1:
        return [
            ("title", "第一章 山城的清晨"),
            ("body", "雾从江面升起，沿着石阶缓慢地爬进街巷。卖早点的铺子刚刚点亮灯，"
                     "蒸笼的白气在门楣下聚成一团，又散进微凉的空气里。"),
            ("body", "他沿着河岸往东走，听见远处传来第一班渡船的汽笛。城还没有完全醒来，"
                     "但石板路已经被许多双鞋磨得发亮。"),
            ("foot", "12"),
        ]
    if number == 2:
        return [
            ("title", "第二章 河岸"),
            ("body", "河岸的市场在午后最热闹。竹筐里堆着新摘的青菜，鱼贩把碎冰铺在木板上，"
                     "水珠沿着板缝一滴一滴落进河里。"),
            ("image", ""),
            ("caption", "图 1  河岸边的旧码头"),
            ("body", "她站在旧码头的尽头，看着对岸的屋脊一层层退向山里。那些屋顶被雨水洗过，"
                     "在阳光下显出深浅不一的青色。"),
            ("foot", "13"),
        ]
    if number == 3:
        return [
            ("title", "第三章 两封信"),
            ("columns", [
                "左栏的文字讲述旧信如何被保存在木箱里，纸张已经发黄，"
                "但墨迹仍然清楚。每一封信都像一扇很小的窗。",
                "右栏接着讲述收信人的迟疑。他没有立即拆开信封，"
                "而是把它放在窗边，让傍晚的光照亮纸上的折痕。",
            ]),
            ("foot", "14"),
        ]
    if number == 4:
        return [
            ("title", "第四章 账簿"),
            ("table", ""),
            ("body", "这张账簿记录了三个月里渡船的收支。数字并不整齐，"
                     "却在每一列下面留下了当时生活的痕迹。"),
            ("foot", "15"),
        ]
    return [
        ("title", "第五章 归来"),
        ("body", "多年以后，他再次回到这座城。石阶比记忆中更短，街巷也更窄。"
                 "那家卖早点的铺子已经不在了，原来的门面变成了一间安静的书店。"),
        ("body", "他从书架上抽出一本旧书。扉页留着一行褪色的字，正是当年那封信里的句子。"
                 "窗外的雨落下来，沿着玻璃缓慢地往下走。"),
        ("foot", "16"),
    ]


def _insert_wrapped(page, rect, text, font="china-s", size=12):
    return page.insert_textbox(rect, text, fontname=font, fontsize=size,
                               lineheight=1.65, align=fitz.TEXT_ALIGN_JUSTIFY,
                               color=(0.10, 0.12, 0.13))


def make_scanned_pdf(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = fitz.open()
    for number in range(1, 6):
        page = clean.new_page(width=595, height=842)
        page.insert_font(fontname="china-s")
        items = _text_page(number)
        top = 72
        for kind, value in items:
            if kind == "title":
                page.insert_textbox(fitz.Rect(90, top, 505, top + 50), value,
                                    fontname="china-s", fontsize=20,
                                    align=fitz.TEXT_ALIGN_CENTER, color=(0.08, 0.10, 0.11))
                top += 82
            elif kind == "body":
                _insert_wrapped(page, fitz.Rect(76, top, 519, top + 170), value)
                top += 144
            elif kind == "columns":
                _insert_wrapped(page, fitz.Rect(64, top, 286, top + 410), value[0], size=11)
                _insert_wrapped(page, fitz.Rect(309, top, 531, top + 410), value[1], size=11)
                top += 430
            elif kind == "image":
                shape = page.new_shape()
                shape.draw_rect(fitz.Rect(145, top + 10, 450, top + 175))
                shape.finish(color=(0.30, 0.36, 0.38), width=1.2,
                             fill=(0.88, 0.91, 0.90))
                shape.draw_line(fitz.Point(160, top + 155), fitz.Point(435, top + 155))
                shape.finish(color=(0.32, 0.44, 0.40), width=2)
                for offset in range(5):
                    shape.draw_circle(fitz.Point(210 + offset * 45, top + 135 - offset * 8), 7)
                    shape.finish(color=(0.38, 0.50, 0.46), fill=(0.55, 0.65, 0.61))
                shape.commit()
                page.insert_text((165, top + 62), "OLD WHARF / 1908", fontname="helv",
                                 fontsize=10, color=(0.25, 0.31, 0.32))
                top += 196
            elif kind == "caption":
                page.insert_textbox(fitz.Rect(120, top, 480, top + 26), value,
                                    fontname="china-s", fontsize=9,
                                    align=fitz.TEXT_ALIGN_CENTER, color=(0.34, 0.37, 0.38))
                top += 46
            elif kind == "table":
                x0, y0, x1, y1 = 120, top, 476, top + 150
                rows, cols = 4, 4
                shape = page.new_shape()
                for row in range(rows + 1):
                    y = y0 + (y1 - y0) * row / rows
                    shape.draw_line(fitz.Point(x0, y), fitz.Point(x1, y))
                for col in range(cols + 1):
                    x = x0 + (x1 - x0) * col / cols
                    shape.draw_line(fitz.Point(x, y0), fitz.Point(x, y1))
                shape.finish(color=(0.18, 0.22, 0.24), width=0.8)
                shape.commit()
                headers = ["月份", "船票", "货物", "合计"]
                values = [["七月", "126", "84", "210"], ["八月", "143", "91", "234"],
                          ["九月", "151", "88", "239"]]
                for column, header in enumerate(headers):
                    page.insert_text((x0 + 15 + column * 89, y0 + 24), header,
                                     fontname="china-s", fontsize=9)
                for row, line in enumerate(values):
                    for column, cell in enumerate(line):
                        page.insert_text((x0 + 15 + column * 89, y0 + 62 + row * 37),
                                         cell, fontname="china-s", fontsize=9)
                top += 180
            elif kind == "foot":
                page.insert_textbox(fitz.Rect(240, 800, 355, 822), value,
                                    fontname="china-s", fontsize=8,
                                    align=fitz.TEXT_ALIGN_CENTER, color=(0.36, 0.38, 0.39))
        clean.save(path.with_suffix(".clean.pdf"))
    source = fitz.open(path.with_suffix(".clean.pdf"))
    scanned = fitz.open()
    for index, page in enumerate(source):
        pixmap = page.get_pixmap(dpi=200, colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        canvas = Image.new("RGB", image.size, "white")
        canvas.paste(image.rotate(0.28, resample=Image.Resampling.BICUBIC, fillcolor="white"), (0, 0))
        array = np.asarray(canvas).astype(np.int16)
        rng = np.random.default_rng(42 + index)
        noise = rng.normal(0, 2.2, array.shape)
        array = np.clip(array + noise, 0, 255).astype(np.uint8)
        output = path.parent / f"scan-page-{index + 1}.png"
        Image.fromarray(array).save(output)
        target = scanned.new_page(width=page.rect.width, height=page.rect.height)
        target.insert_image(target.rect, filename=str(output))
    scanned.save(path)
    scanned.close()
    source.close()
    path.with_suffix(".clean.pdf").unlink(missing_ok=True)
    return path

