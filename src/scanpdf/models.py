from dataclasses import asdict, dataclass, field
from uuid import uuid4


@dataclass
class Settings:
    language: str = "ch"
    quality: str = "standard"
    dpi: int = 220
    orientation: bool = True
    deskew: bool = True
    denoise: bool = False
    contrast: bool = False
    binarize: bool = False
    device: str = "cpu"
    reading_mode: str = "auto"
    chapters: bool = True
    paragraphs: bool = True
    merge_pages: bool = True
    clean_margins: bool = True
    clean_page_numbers: bool = True
    keep_images: bool = True
    toc: bool = True
    indent: bool = True
    font: str = "serif"
    line_height: float = 1.8
    low_confidence: float = 0.85


@dataclass
class Block:
    page_number: int
    text: str
    confidence: float
    bounding_box: list[list[float]]
    reading_order: int = 0
    paragraph_id: str = ""
    block_type: str = "body"
    id: str = field(default_factory=lambda: uuid4().hex)
    chapter_level: int = 0
    column: int = 0
    excluded: bool = False
    flagged: bool = False
    asset: str = ""
    cells: list[list[str]] = field(default_factory=list)
    mathml: str = ""
    join_previous: bool = False
    break_before: bool = False
    manual_type: bool = False

    @property
    def rect(self):
        horizontal = [point[0] for point in self.bounding_box]
        vertical = [point[1] for point in self.bounding_box]
        return min(horizontal), min(vertical), max(horizontal), max(vertical)

    @property
    def height(self):
        return self.rect[3] - self.rect[1]


@dataclass
class Page:
    number: int
    width: int
    height: int
    blocks: list[Block] = field(default_factory=list)
    image: str = ""
    original_image: str = ""
    warnings: list[str] = field(default_factory=list)
    seconds: float = 0
    rotation: int = 0
    skew: float = 0
    transform: list[list[float]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        return cls(**{**data, "blocks": [Block(**block) for block in data["blocks"]]})


@dataclass
class Paragraph:
    text: str
    block_type: str = "body"
    level: int = 0
    block_ids: list[str] = field(default_factory=list)
    asset: str = ""
    cells: list[list[str]] = field(default_factory=list)
    mathml: str = ""


def to_dict(value):
    return asdict(value)


def rectangle(left, top, right, bottom):
    return [[float(left), float(top)], [float(right), float(top)],
            [float(right), float(bottom)], [float(left), float(bottom)]]

