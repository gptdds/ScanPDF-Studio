import re
from xml.sax.saxutils import escape


def is_formula(text):
    return bool(re.search(r"[=∑∫√≠≈≤≥]", text) and
                len(re.findall(r"[\u3400-\u9fff]", text)) <= 2)


def simple_mathml(text):
    if not re.fullmatch(r"[A-Za-z0-9\s.+\-*/=()]+", text) or "=" not in text:
        return ""
    tokens = re.findall(r"\d+(?:\.\d+)?|[A-Za-z]+|[+\-*/=()]", text)
    contents = []
    for token in tokens:
        tag = "mn" if re.fullmatch(r"\d+(\.\d+)?", token) else ("mi" if token.isalpha() else "mo")
        contents.append(f"<{tag}>{escape(token)}</{tag}>")
    return '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>' + "".join(contents) + "</mrow></math>"

