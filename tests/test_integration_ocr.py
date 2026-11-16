import os
from pathlib import Path

import pytest

from scanpdf.core.image_preprocessor import preprocess
from scanpdf.core.layout_analyzer import analyze
from scanpdf.core.ocr_engine import PaddleEngine
from scanpdf.core.pdf_loader import PDFDocument
from scanpdf.models import Settings


@pytest.mark.skipif(os.environ.get("RUN_OCR") != "1",
                    reason="设置 RUN_OCR=1 后运行真实 PP-OCRv5 集成测试")
def test_real_paddle_ocr_structured_result(sample_pdf):
    settings = Settings(orientation=False, dpi=200, quality="standard")
    engine = PaddleEngine(settings)
    with PDFDocument(sample_pdf) as pdf:
        image = pdf.render(1, 200)
    processed, matrix, skew = preprocess(image, settings)
    blocks, raw = engine.recognize(processed, 1)
    assert len(blocks) >= 4
    assert all(block.bounding_box and block.page_number == 1 for block in blocks)
    assert any("第一章" in block.text for block in blocks)
    assert any(block.confidence > 0.9 for block in blocks)
    assert raw.get("rec_texts")
    from scanpdf.models import Page
    page = Page(1, processed.shape[1], processed.shape[0], blocks)
    analyze(page, settings)
    assert any(block.block_type == "heading" for block in page.blocks)
