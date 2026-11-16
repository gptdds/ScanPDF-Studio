import os
from contextlib import contextmanager
from os import PathLike
from pathlib import Path
from abc import ABC, abstractmethod

import cv2
import numpy as np

from scanpdf.models import Block
from scanpdf.core.text_normalizer import to_simplified_chinese
from scanpdf.services.model_manager import ensure_model
from scanpdf.services.paths import ascii_data_dir


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image, page_number):
        raise NotImplementedError

    def orientation(self, image):
        return 0


def serializable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, dict):
        return {key: serializable(item) for key, item in value.items()
                if key not in ("input_img", "output_img", "vis_fonts")}
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    if isinstance(value, (Path, PathLike)):
        return str(value)
    return str(value)


def parse_result(result, page_number, language=None):
    data = result.get("res", result)
    texts = data.get("rec_texts", [])
    scores = data.get("rec_scores", [])
    polygons = data.get("rec_polys", data.get("dt_polys", []))
    if not (len(texts) == len(scores) == len(polygons)):
        raise ValueError("OCR 返回的文本、坐标和置信度数量不一致。")
    return [
        Block(page_number=page_number,
              text=to_simplified_chinese(text) if language == "ch" else str(text),
              confidence=float(score),
              bounding_box=np.asarray(polygon, dtype=float).tolist(), reading_order=index)
        for index, (text, score, polygon) in enumerate(zip(texts, scores, polygons))
    ]


class PaddleEngine(OCREngine):
    def __init__(self, settings, progress=lambda message: None, cancel=lambda: False):
        self.language = settings.language
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "BOS")
        os.environ.setdefault("FLAGS_enable_pir_api", "1")
        tier = "server" if settings.quality == "high" else "mobile"
        detector = f"PP-OCRv5_{tier}_det"
        if settings.language == "en":
            recognizer = "en_PP-OCRv5_mobile_rec"
        elif settings.language == "chinese_cht":
            recognizer = "PP-OCRv5_server_rec"
        else:
            recognizer = f"PP-OCRv5_{tier}_rec"
        detection_dir = ensure_model(detector, progress, cancel)
        recognition_dir = ensure_model(recognizer, progress, cancel)
        orientation_dir = ensure_model("PP-LCNet_x1_0_doc_ori", progress, cancel) if settings.orientation else None
        progress("加载 PP-OCRv5 模型…")
        cache = ascii_data_dir() / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache / "paddlex")
        with paddlex_home(cache / "home"):
            import paddle
            from paddleocr import DocImgOrientationClassification, PaddleOCR
            device = settings.device
            if device.startswith("gpu") and not paddle.is_compiled_with_cuda():
                progress("当前推理运行库不支持 GPU，已明确降级为 CPU。")
                device = "cpu"
            self.pipeline = PaddleOCR(
                text_detection_model_name=detector,
                text_detection_model_dir=str(detection_dir),
                text_recognition_model_name=recognizer,
                text_recognition_model_dir=str(recognition_dir),
                use_doc_orientation_classify=False, use_doc_unwarping=False,
                use_textline_orientation=False, device=device, enable_mkldnn=False,
                cpu_threads=min(8, os.cpu_count() or 4),
            )
            self.classifier = DocImgOrientationClassification(
                model_name="PP-LCNet_x1_0_doc_ori", model_dir=str(orientation_dir),
                device=device, enable_mkldnn=False,
            ) if orientation_dir else None

    def orientation(self, image):
        if self.classifier is None:
            return 0
        result = next(iter(self.classifier.predict(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))))
        data = dict(result)
        label = data.get("label_names", ["0"])[0]
        return int(label)

    def recognize(self, image, page_number):
        results = list(self.pipeline.predict(
            cv2.cvtColor(image, cv2.COLOR_RGB2BGR), text_rec_score_thresh=0.0,
            text_det_limit_side_len=1600, text_det_limit_type="max"))
        if len(results) != 1:
            raise ValueError(f"OCR 单页结果数量异常: {len(results)}")
        raw = serializable(dict(results[0]))
        return parse_result(raw, page_number, self.language), raw


@contextmanager
def paddlex_home(directory):
    directory.mkdir(parents=True, exist_ok=True)
    previous = {key: os.environ.get(key) for key in ("USERPROFILE", "HOME")}
    os.environ["USERPROFILE"] = str(directory)
    os.environ["HOME"] = str(directory)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
