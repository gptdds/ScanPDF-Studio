import datetime as dt
import html
import re
import shutil
import os
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree


def _chapter_groups(paragraphs, title):
    groups = []
    current = None
    heading_levels = [
        max(1, min(3, paragraph.level or 1))
        for paragraph in paragraphs
        if paragraph.block_type == "heading" and paragraph.text.strip()
    ]
    split_level = min(heading_levels) if heading_levels else 0
    for paragraph in paragraphs:
        level = max(1, min(3, paragraph.level or 1))
        if paragraph.block_type == "heading" and level == split_level:
            current = {"title": paragraph.text, "level": level, "items": []}
            groups.append(current)
        else:
            if current is None:
                current = {"title": title or "正文", "level": 1, "items": []}
                groups.append(current)
            current["items"].append(paragraph)
    return groups or [{"title": title or "正文", "level": 1, "items": []}]


def _heading_tree(paragraphs):
    roots = []
    stack = []
    for paragraph in paragraphs:
        level = max(1, min(3, paragraph.level or 1))
        node = {"paragraph": paragraph, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            stack[-1][1]["children"].append(node)
        else:
            roots.append(node)
        stack.append((level, node))
    return roots


def _render_nav_nodes(nodes, file_name, anchors):
    items = []
    for node in nodes:
        paragraph = node["paragraph"]
        anchor = anchors[id(paragraph)]
        children = _render_nav_nodes(node["children"], file_name, anchors)
        items.append(
            f'<li><a href="{file_name}#{anchor}">{html.escape(paragraph.text)}</a>'
            f'{children}</li>'
        )
    return "<ol>" + "".join(items) + "</ol>" if items else ""


def _render(paragraph, settings, prefix="../", anchor=""):
    if paragraph.block_type == "image":
        return (f'<figure><img src="{prefix}{html.escape(paragraph.asset)}" alt="扫描书籍插图"/>'
                f'<figcaption>{html.escape(paragraph.text)}</figcaption></figure>')
    if paragraph.block_type == "table":
        if paragraph.cells:
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
                           for row in paragraph.cells)
            image = (f'<p class="table-note">识别可靠度不足，附原表图像：'
                     f'<img src="{prefix}{html.escape(paragraph.asset)}" alt="原表格"/></p>'
                     if paragraph.asset else "")
            return f'<table><tbody>{rows}</tbody></table>{image}'
        if paragraph.asset:
            return f'<figure class="table"><img src="{prefix}{html.escape(paragraph.asset)}" alt="表格"/><figcaption>表格图像</figcaption></figure>'
        return '<p class="table-warning">表格未能可靠重建，请在校对工作台查看原始页面。</p>'
    if paragraph.block_type == "formula" and paragraph.mathml:
        return f'<div class="formula">{paragraph.mathml}</div>'
    if paragraph.block_type == "formula" and paragraph.asset:
        return f'<figure class="formula"><img src="{prefix}{html.escape(paragraph.asset)}" alt="公式"/></figure>'
    if paragraph.block_type == "caption":
        return f'<p class="caption">{html.escape(paragraph.text)}</p>'
    if paragraph.block_type in ("footnote", "note"):
        return f'<aside class="note">{html.escape(paragraph.text)}</aside>'
    if paragraph.block_type == "heading":
        level = max(2, min(4, paragraph.level + 1))
        id_attr = f' id="{anchor}"' if anchor else ""
        return f"<h{level}{id_attr}>{html.escape(paragraph.text)}</h{level}>"
    return f"<p>{html.escape(paragraph.text)}</p>"


def _cover_image(title, author, path):
    from PIL import Image, ImageDraw, ImageFont
    width, height = 1200, 1800
    image = Image.new("RGB", (width, height), "#183d35")
    draw = ImageDraw.Draw(image)
    draw.rectangle((58, 58, width - 58, height - 58), outline="#6da698", width=2)
    draw.rectangle((78, 78, width - 78, height - 78), outline="#3c6d63", width=1)
    font_path = next((item for item in (
        r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttc") if Path(item).exists()), None)
    title_font = ImageFont.truetype(font_path, 78) if font_path else ImageFont.load_default()
    author_font = ImageFont.truetype(font_path, 34) if font_path else ImageFont.load_default()
    small_font = ImageFont.truetype(font_path, 23) if font_path else ImageFont.load_default()
    lines, current = [], ""
    for character in title:
        trial = current + character
        if draw.textlength(trial, font=title_font) > width - 260 and current:
            lines.append(current)
            current = character
        else:
            current = trial
    if current:
        lines.append(current)
    line_height = 112
    top = 470 - max(0, len(lines) - 1) * line_height // 2
    for index, line in enumerate(lines[:5]):
        length = draw.textlength(line, font=title_font)
        draw.text(((width - length) / 2, top + index * line_height), line,
                  font=title_font, fill="#f3f0e7")
    draw.line((420, 985, 780, 985), fill="#8bb9ad", width=2)
    author_text = author or "未知"
    length = draw.textlength(author_text, font=author_font)
    draw.text(((width - length) / 2, 1030), author_text, font=author_font, fill="#c7ddd7")
    mark = "SCANPDF STUDIO"
    length = draw.textlength(mark, font=small_font)
    draw.text(((width - length) / 2, 1515), mark, font=small_font, fill="#86a99f")
    image.save(path, "PNG")


def _xhtml(title, body, settings, extra="", body_class="", prefix=""):
    indent = "1.75em" if settings.indent else "0"
    family = "serif" if settings.font == "serif" else "sans-serif"
    section_attr = f' epub:type="{extra}"' if extra else ""
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh-CN" lang="zh-CN">
<head><meta charset="utf-8"/><title>{html.escape(title)}</title>
<link rel="stylesheet" type="text/css" href="{prefix}styles/style.css"/>
<style>:root{{--indent:{indent};--font-family:{family};--line-height:{settings.line_height}}}</style>
</head><body class="{body_class}"><section{section_attr}>
{body}
</section></body></html>'''


def build_epub(project, paragraphs, output, settings):
    output = Path(output)
    work = output.parent / f".{output.stem}-{uuid.uuid4().hex}"
    work.mkdir(parents=True)
    try:
        title = project.get("title") or "未命名书籍"
        author = project.get("author") or "未知"
        book_id = project.get("book_id") or f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, str(output))}"
        (work / "META-INF").mkdir()
        (work / "META-INF/container.xml").write_text(
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/package.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
            encoding="utf-8")
        content = work / "OEBPS"
        (content / "text").mkdir(parents=True)
        (content / "styles").mkdir()
        (content / "assets").mkdir()
        source = Path(project["directory"])
        for asset in (source / "assets").glob("*"):
            if asset.is_file():
                shutil.copy2(asset, content / "assets" / asset.name)
        (content / "styles/style.css").write_text("""
html { font-size: 100%; }
body { font-family: var(--font-family), "Songti SC", "Noto Serif CJK SC", serif;
  line-height: var(--line-height); margin: 1.6em 1.4em; color: #1d2328; }
p { margin: 0; text-indent: var(--indent); text-align: justify; }
p + p { margin-top: .35em; }
h1, h2, h3, h4 { line-height: 1.35; text-indent: 0; margin: 1.7em 0 .75em;
  break-after: avoid; page-break-after: avoid; }
h1 { font-size: 1.65em; } h2 { font-size: 1.35em; } h3 { font-size: 1.15em; }
figure { margin: 1.2em 0; text-align: center; break-inside: avoid; }
img { max-width: 100%; height: auto; }
figcaption, .caption { font-size: .9em; color: #59646d; text-indent: 0;
  text-align: center; margin-top: .5em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: .92em; }
td { border: 1px solid #a8b0b5; padding: .35em .5em; vertical-align: top; }
.table-note { margin-top: .6em; text-indent: 0; }
.note { font-size: .88em; border-left: 3px solid #aeb8be; padding-left: .8em;
  margin: .7em 0; color: #4d5961; }
.formula { text-align: center; margin: 1em 0; overflow-x: auto; }
.table-warning { background: #fff5df; padding: .7em; text-indent: 0; }
body.cover { margin: 0; padding: 0; background: #183d35; }
.cover-page { margin: 0; padding: 0; text-align: center; }
.cover-page img { display: block; width: 100%; height: auto; margin: 0 auto; }
""", encoding="utf-8")
        groups = _chapter_groups(paragraphs, title)
        anchors = {
            id(paragraph): f"heading-{index:04d}"
            for index, paragraph in enumerate(paragraphs, 1)
            if paragraph.block_type == "heading"
        }
        files = []
        nav_items = []
        for index, group in enumerate(groups, 1):
            file_name = f"text/chapter-{index:04d}.xhtml"
            body = "".join(
                _render(paragraph, settings, prefix="../", anchor=anchors.get(id(paragraph), ""))
                for paragraph in group["items"]
            )
            body = f"<h1>{html.escape(group['title'])}</h1>" + body
            (content / file_name).write_text(_xhtml(group["title"], body, settings, "chapter", prefix="../"),
                                              encoding="utf-8")
            files.append(file_name)
            nav_items.append((group["title"], file_name, group["items"]))
        nav_body = "<h1>目录</h1><nav epub:type=\"toc\" id=\"toc\"><ol>"
        for group_title, file_name, items in nav_items:
            nav_body += f'<li><a href="{file_name}">{html.escape(group_title)}</a>'
            subsections = [item for item in items if item.block_type == "heading"]
            nav_body += _render_nav_nodes(_heading_tree(subsections), file_name, anchors)
            nav_body += "</li>"
        nav_body += "</ol></nav>"
        if settings.toc:
            (content / "nav.xhtml").write_text(_xhtml("目录", nav_body, settings), encoding="utf-8")
        cover_meta = ""
        cover_manifest = ""
        cover_spine = ""
        cover = next((path for path in (source / "assets").glob("*")
                      if path.stem.lower().startswith("cover")), None)
        if cover:
            shutil.copy2(cover, content / f"cover{cover.suffix.lower()}")
            cover_name = f"cover{cover.suffix.lower()}"
        else:
            cover_name = "cover.png"
            _cover_image(title, author, content / cover_name)
        cover_meta = '<meta name="cover" content="cover-image"/>'
        cover_media = "image/png" if cover_name.lower().endswith(".png") else "image/jpeg"
        cover_manifest = f'<item id="cover-image" href="{cover_name}" media-type="{cover_media}"/>'
        cover_manifest += ('<item id="cover-page" href="cover.xhtml" '
                           'media-type="application/xhtml+xml"/>')
        (content / "cover.xhtml").write_text(
            _xhtml(title, f'<div class="cover-page"><img src="{cover_name}" '
                          f'alt="{html.escape(title)}"/></div>', settings, "cover", "cover"),
            encoding="utf-8")
        cover_spine = '<itemref idref="cover-page"/>'
        manifest_images = "".join(
            f'<item id="image-{index}" href="assets/{asset.name}" media-type="image/'
            f'{"png" if asset.suffix.lower() == ".png" else "jpeg"}"/>'
            for index, asset in enumerate(
                (asset for asset in (source / "assets").glob("*")
                 if (source / "assets").exists() and asset.name != cover_name), 1))
        manifest = cover_manifest + manifest_images + "".join(
            f'<item id="chapter-{index}" href="{file_name}" media-type="application/xhtml+xml"/>'
            for index, file_name in enumerate(files, 1))
        if settings.toc:
            manifest += '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        manifest += '<item id="css" href="styles/style.css" media-type="text/css"/>'
        spine_items = cover_spine + "".join(f'<itemref idref="chapter-{index}"/>'
                              for index in range(1, len(files) + 1))
        modified = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        package = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="zh-CN">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{html.escape(book_id)}</dc:identifier>
<dc:title>{html.escape(title)}</dc:title><dc:creator>{html.escape(author)}</dc:creator>
<dc:language>zh-CN</dc:language><dc:date>{modified}</dc:date>
{cover_meta}<meta property="dcterms:modified">{modified}</meta>
</metadata><manifest>{manifest}</manifest>
<spine>{spine_items}</spine></package>'''
        (content / "package.opf").write_text(package, encoding="utf-8")
        for relative in ("META-INF/container.xml", "OEBPS/package.opf"):
            ElementTree.parse(work / relative)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
            for path in sorted(work.rglob("*")):
                if path.is_file() and path.name != "mimetype":
                    archive.write(path, path.relative_to(work).as_posix())
        return output
    finally:
        shutil.rmtree(work, ignore_errors=True)


def validate_epub(path):
    errors, warnings = [], []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if not infos or infos[0].filename != "mimetype" or infos[0].compress_type != zipfile.ZIP_STORED:
            errors.append("EPUB 的 mimetype 必须是 ZIP 第一项且不压缩。")
        names = set(archive.namelist())
        for required in ("META-INF/container.xml", "OEBPS/package.opf"):
            if required not in names:
                errors.append(f"缺少 {required}")
        if errors:
            return {"ok": False, "errors": errors, "warnings": warnings}
        package = ElementTree.fromstring(archive.read("OEBPS/package.opf"))
        namespace = {"opf": "http://www.idpf.org/2007/opf"}
        manifest = {item.attrib["id"]: item.attrib for item in package.findall(".//opf:manifest/opf:item", namespace)}
        for item in manifest.values():
            if "OEBPS/" + item["href"] not in names:
                errors.append(f"manifest 文件缺失: {item['href']}")
        spine = [reference.attrib["idref"] for reference in package.findall(".//opf:spine/opf:itemref", namespace)]
        if not spine:
            errors.append("spine 为空。")
        if not any("nav" in item.get("properties", "") for item in manifest.values()):
            warnings.append("未生成 EPUB 导航文档。")
        for file_name in [item["href"] for item in manifest.values() if item["href"].endswith(".xhtml")]:
            ElementTree.fromstring(archive.read("OEBPS/" + file_name))
        for file_name in names:
            if file_name.endswith((".xhtml", ".opf", ".css", ".xml")):
                archive.read(file_name).decode("utf-8")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


def epubcheck(path, java="java", jar=None):
    import subprocess
    from scanpdf.services.paths import data_dir

    if jar is None:
        jar = locate_epubcheck()
    if not jar:
        return {"ok": None, "message": "未配置 EPUBCheck，已执行内置 EPUB 结构验证。"}
    if not shutil.which(java):
        return {"ok": None, "message": "已找到 EPUBCheck，但系统未安装 Java，内置结构验证仍已通过。"}
    temp = data_dir() / "tmp"
    temp.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([java, "-Djava.awt.headless=true",
                             f"-Djava.io.tmpdir={temp}", "-jar", str(jar), str(path)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"ok": result.returncode == 0, "message": (result.stdout + result.stderr)[-4000:]}


def locate_epubcheck():
    from scanpdf.services.paths import bundled_root
    candidates = []
    if os.environ.get("EPUBCHECK_JAR"):
        candidates.append(Path(os.environ["EPUBCHECK_JAR"]))
    for root in (bundled_root(), Path(__file__).resolve().parents[3]):
        candidates.extend((root / "tools" / "epubcheck").glob("**/epubcheck.jar"))
    return next((path for path in candidates if path.exists()), None)


def safe_filename(title):
    return re.sub(r'[\\/:*?"<>|]', "_", title).strip(" .") or "book"

