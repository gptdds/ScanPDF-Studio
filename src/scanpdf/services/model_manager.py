import hashlib
import json
import shutil
import tarfile
from pathlib import Path

import requests

from scanpdf.services.paths import model_dir

BASE_URL = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0"
MODEL_NAMES = (
    "PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec",
    "PP-OCRv5_server_det", "PP-OCRv5_server_rec",
    "en_PP-OCRv5_mobile_rec",
    "PP-LCNet_x1_0_doc_ori",
)


def ensure_model(name, progress=lambda message: None, cancel=lambda: False, root=None):
    if name not in MODEL_NAMES:
        raise ValueError(f"未知模型: {name}")
    root = Path(root or model_dir())
    root.mkdir(parents=True, exist_ok=True)
    destination = root / name
    if (destination / "inference.json").exists() and (destination / "inference.pdiparams").exists():
        return destination
    archive = root / f"{name}.tar.partial"
    staging = root / f".{name}-extract"
    for attempt in range(3):
        try:
            digest = hashlib.sha256()
            with requests.get(f"{BASE_URL}/{name}_infer.tar", stream=True,
                              timeout=(20, 60)) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0))
                done = 0
                with archive.open("wb") as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        if cancel():
                            raise InterruptedError("已取消模型下载。")
                        stream.write(chunk)
                        digest.update(chunk)
                        done += len(chunk)
                        suffix = f"/{total / 1048576:.1f} MB" if total else " MB"
                        progress(f"下载 {name} · {done / 1048576:.1f}{suffix}")
                if total and done != total:
                    raise OSError("模型下载不完整。")
            staging.mkdir(exist_ok=True)
            with tarfile.open(archive) as package:
                for member in package.getmembers():
                    resolved = (staging / member.name).resolve()
                    if not resolved.is_relative_to(staging.resolve()) or member.issym() or member.islnk():
                        raise ValueError("模型包包含不安全路径。")
                package.extractall(staging, filter="data")
            inference = next(staging.rglob("inference.pdiparams"))
            if destination.exists():
                shutil.rmtree(destination)
            shutil.move(str(inference.parent), destination)
            (destination / "download.json").write_text(json.dumps(
                {"url": f"{BASE_URL}/{name}_infer.tar", "sha256": digest.hexdigest()},
                indent=2), encoding="utf-8")
            return destination
        except InterruptedError:
            raise
        except Exception:
            if attempt == 2:
                raise
            progress(f"{name} 下载失败，重试 {attempt + 2}/3")
        finally:
            archive.unlink(missing_ok=True)
            if staging.exists():
                shutil.rmtree(staging)

