from pathlib import Path

import pytest

from fixtures import make_scanned_pdf


@pytest.fixture(scope="session", autouse=True)
def isolated_data_dir(tmp_path_factory):
    import os
    root = tmp_path_factory.mktemp("appdata")
    os.environ["SCANPDF_DATA_DIR"] = str(root)
    return root


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory):
    root = tmp_path_factory.mktemp("samples")
    return make_scanned_pdf(root / "chinese_scan.pdf")

