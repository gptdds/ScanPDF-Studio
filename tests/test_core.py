import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import cv2

from scanpdf.core.chapter_detector import detect_chapters
from scanpdf.core.epub_builder import build_epub, validate_epub
from scanpdf.core.image_preprocessor import preprocess
from scanpdf.core.layout_analyzer import analyze, clean_repeated_margins
from scanpdf.core.ocr_engine import parse_result
from scanpdf.core.paragraph_builder import build_paragraphs, join_text, normalize_text
from scanpdf.core.pdf_loader import PDFDocument
from scanpdf.core.reading_order import reading_order
from scanpdf.models import Block, Page, Paragraph, Settings, rectangle


def block(text, left, top, right, bottom, page=1, confidence=0.95):
    return Block(page, text, confidence, rectangle(left, top, right, bottom))


def test_pdf_loads_and_renders(sample_pdf):
    with PDFDocument(sample_pdf) as pdf:
        assert pdf.page_count == 5
        image = pdf.render(1, 150)
        assert image.shape[2] == 3
        assert image.shape[0] > 1000
        assert np.mean(image) > 180
    with pytest.raises(ValueError):
        with PDFDocument(sample_pdf) as pdf:
            pdf.render(1, 999)


def test_preprocess_rotation_and_transform():
    image = np.full((100, 200, 3), 255, np.uint8)
    settings = Settings(deskew=False, denoise=False, contrast=False, binarize=False)
    rotated, matrix, skew = preprocess(image, settings, 90)
    assert rotated.shape[:2] == (200, 100)
    assert skew == 0
    assert matrix.shape == (3, 3)


def test_ocr_result_parsing_and_confidence():
    raw = {"res": {
        "rec_texts": ["第一章", "正文内容"],
        "rec_scores": [0.97, 0.82],
        "rec_polys": [[[10, 20], [90, 20], [90, 50], [10, 50]],
                      [[10, 70], [180, 70], [180, 100], [10, 100]]],
    }}
    blocks = parse_result(raw, 3)
    assert [item.text for item in blocks] == ["第一章", "正文内容"]
    assert blocks[1].confidence == pytest.approx(0.82)
    assert blocks[0].page_number == 3
    assert blocks[0].rect == (10, 20, 90, 50)


def test_reading_order_is_column_aware():
    left_top = block("left top", 40, 40, 260, 80)
    left_bottom = block("left bottom", 40, 100, 260, 140)
    right_top = block("right top", 300, 40, 520, 80)
    right_bottom = block("right bottom", 300, 100, 520, 140)
    ordered = reading_order([right_bottom, left_bottom, right_top, left_top], 560, 800)
    assert [item.text for item in ordered] == [
        "left top", "left bottom", "right top", "right bottom"]
    assert len({item.column for item in ordered[:2]}) == 1
    assert ordered[0].reading_order == 0


def test_vertical_order():
    first = block("从右到左第一列", 420, 50, 470, 400)
    second = block("第二列", 330, 50, 380, 400)
    ordered = reading_order([second, first], 560, 800, "vertical")
    assert ordered[0] is first
    assert ordered[1] is second


def test_paragraph_reconstruction_and_cross_page():
    settings = Settings(merge_pages=True, clean_margins=False)
    page1 = Page(1, 560, 800, [
        block("　他沿着河岸慢慢往前走，看见", 48, 60, 500, 90),
        block("远处的渡船已经靠岸。", 500, 62, 512, 90),
        block("新的段落从这里开始，带有首行缩进。", 90, 130, 500, 160),
        block("12", 260, 760, 300, 780),
    ])
    analyze(page1, settings)
    paragraphs = build_paragraphs([page1], settings)
    assert paragraphs[0].text.startswith("他沿着河岸慢慢往前走")
    assert "远处" in paragraphs[0].text
    assert "新的段落" in paragraphs[1].text
    page2 = Page(2, 560, 800, [
        block("未完的句子继续延伸到下一页，", 48, 650, 510, 684),
    ])
    page3 = Page(3, 560, 800, [
        block("直到河面重新安静下来。", 48, 60, 500, 94),
    ])
    for page in (page2, page3):
        analyze(page, settings)
    cross = build_paragraphs([page2, page3], settings)
    assert len(cross) == 1
    assert cross[0].text.endswith("直到河面重新安静下来。")
    assert join_text("中文", "continue") == "中文continue"
    assert join_text("hello", "world") == "hello world"
    assert normalize_text("中 文 字　测试 ， 完成") == "中文字　测试，完成"


def test_chapter_detection_uses_geometry_and_pattern():
    page = Page(1, 560, 800, [
        block("第一章 山城的清晨", 170, 80, 390, 120),
        block("这是正文第一段，用来说明识别不能只看正则。", 60, 180, 500, 215),
        block("第二章", 190, 400, 370, 440),
    ])
    settings = Settings()
    detect_chapters(page)
    assert page.blocks[0].block_type == "heading"
    assert page.blocks[1].block_type == "body"
    assert page.blocks[2].block_type == "heading"


def test_margin_cleaning_is_repetition_based():
    settings = Settings(clean_margins=True, clean_page_numbers=True)
    pages = []
    for number in range(1, 5):
        page = Page(number, 560, 800, [
            block("山城旧事", 210, 20, 350, 40, number),
            block("正文内容。", 60, 100, 500, 130, number),
            block(str(number), 270, 760, 290, 780, number),
        ])
        pages.append(page)
    analyze(pages[0], settings)
    clean_repeated_margins(pages, settings)
    assert pages[0].blocks[0].excluded
    assert pages[0].blocks[0].block_type == "header"
    assert pages[0].blocks[2].excluded


def test_caption_parts_are_merged_without_losing_raw_result():
    page = Page(1, 560, 800, [
        block("图1", 230, 500, 300, 520),
        block("河岸边的旧码头", 180, 530, 380, 552),
        block("正文从这里继续。", 60, 600, 500, 630),
    ])
    analyze(page, Settings())
    assert page.blocks[0].block_type == "caption"
    assert page.blocks[0].text == "图1  河岸边的旧码头"
    assert page.blocks[1].excluded
    assert page.blocks[1].text == "河岸边的旧码头"


def test_caption_fragments_on_same_line_are_merged():
    page = Page(1, 560, 800, [
        block("图1", 110, 500, 165, 522),
        block("河岸边的旧码头", 178, 501, 390, 523),
        block("正文从这里继续。", 60, 600, 500, 630),
    ])
    analyze(page, Settings())
    assert page.blocks[0].block_type == "caption"
    assert page.blocks[0].text == "图1  河岸边的旧码头"
    assert page.blocks[1].excluded


def test_table_grid_and_cell_ocr_rebuild(tmp_path):
    from scanpdf.core.table_detector import detect_tables
    image = np.full((300, 600, 3), 255, np.uint8)
    for y in (20, 80, 140, 200, 260):
        cv2.line(image, (20, y), (580, y), (0, 0, 0), 2)
    for x in (20, 160, 300, 440, 580):
        cv2.line(image, (x, 20), (x, 260), (0, 0, 0), 2)
    values = [["月份", "船票", "货物"], ["七月", "126", "84"], ["八月", "143", "91"]]

    def ocr_crop(rect):
        cells = []
        for row, line in enumerate(values):
            for column, value in enumerate(line):
                left = 25 + column * 140
                top = 25 + row * 60
                cells.append(Block(1, value, 0.98,
                                   rectangle(left, top, left + 80, top + 30)))
        return cells, {"rec_texts": [cell.text for cell in cells]}

    def save_crop(rect, kind):
        path = tmp_path / f"{kind}.png"
        cv2.imwrite(str(path), image)
        return path.name

    tables = detect_tables(image, [], 1, save_crop, ocr_crop)
    assert len(tables) == 1
    assert tables[0].cells[0][0] == "月份"
    assert tables[0].cells[2][2] == "91"
    assert tables[0].asset == ""


def test_epub_structure_chinese_images_and_tables(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "assets").mkdir(parents=True)
    from PIL import Image
    Image.new("RGB", (100, 80), (190, 205, 200)).save(project_dir / "assets" / "figure.png")
    paragraphs = [
        Paragraph("第一章 山河", "heading", 1),
        Paragraph("中文正文包含特殊字符：<标签> & “引号”。", "body"),
        Paragraph("第一节 河岸", "heading", 2),
        Paragraph("河岸小节正文。", "body"),
        Paragraph("一、码头", "heading", 3),
        Paragraph("插图（第 2 页）", "image", asset="figure.png"),
        Paragraph("表格", "table", asset="figure.png",
                  cells=[["月份", "收入"], ["七月", "210"]]),
        Paragraph("第二章 归途", "heading", 1),
        Paragraph("最后一段。", "body"),
    ]
    output = tmp_path / "book.epub"
    build_epub({"title": "山城旧事", "author": "测试作者", "directory": str(project_dir)},
               paragraphs, output, Settings(indent=True))
    validation = validate_epub(output)
    assert validation["ok"], validation["errors"]
    with zipfile.ZipFile(output) as archive:
        assert archive.infolist()[0].filename == "mimetype"
        assert archive.infolist()[0].compress_type == zipfile.ZIP_STORED
        package = archive.read("OEBPS/package.opf").decode("utf-8")
        assert "山城旧事" in package and "zh-CN" in package
        chapter = archive.read("OEBPS/text/chapter-0001.xhtml").decode("utf-8")
        assert "&lt;标签&gt;" in chapter
        assert "<table>" in chapter
        assert '<h3 id="heading-0003">第一节 河岸</h3>' in chapter
        assert '<h4 id="heading-0005">一、码头</h4>' in chapter
        assert "OEBPS/text/chapter-0002.xhtml" in archive.namelist()
        assert "OEBPS/text/chapter-0003.xhtml" not in archive.namelist()
        nav = archive.read("OEBPS/nav.xhtml").decode("utf-8")
        assert 'href="text/chapter-0001.xhtml#heading-0003"' in nav
        assert 'href="text/chapter-0001.xhtml#heading-0005"' in nav
        assert any(name.endswith("figure.png") for name in archive.namelist())
        assert "OEBPS/cover.png" in archive.namelist()
        assert "OEBPS/cover.xhtml" in archive.namelist()
        assert 'name="cover" content="cover-image"' in package

