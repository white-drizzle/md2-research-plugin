"""Build a four-view HTML note from a finished reader and a paper-specific guide spec."""
import argparse
import base64
import html
from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from urllib.parse import quote, unquote, urlsplit

ASSETS = Path(__file__).with_name("multiview")
VIEWS = ("overview", "flow", "depth")
TERM = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")


def embedded_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")


def image_uri(path):
    mime = mimetypes.guess_type(path.name)[0]
    if not mime or not mime.startswith("image/"):
        raise ValueError(f"expected an image file: {path.name}")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def file_href(path, directory):
    try:
        relative = os.path.relpath(path.resolve(), directory.resolve())
    except ValueError:  # Windows drive letters differ.
        return path.resolve().as_uri()
    return quote(Path(relative).as_posix(), safe="/")


class ReaderIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.headings = []
        self.heading = None
        self.definition_text = None
        self.in_definitions = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        ident = attrs.get("id")
        if ident:
            self.ids.add(ident)
        if ident and tag in ("h2", "h3"):
            self.heading = [ident, []]
        if tag == "script" and ident == "term-definitions":
            self.definition_text = []
            self.in_definitions = True

    def handle_data(self, data):
        if self.heading:
            self.heading[1].append(data)
        if self.in_definitions:
            self.definition_text.append(data)

    def handle_endtag(self, tag):
        if tag in ("h2", "h3") and self.heading:
            self.headings.append((self.heading[0], "".join(self.heading[1]).strip()))
            self.heading = None
        if tag == "script":
            self.in_definitions = False


def require_text(obj, fields, where):
    if not isinstance(obj, dict):
        raise ValueError(f"{where} must be an object")
    for field in fields.split():
        if not isinstance(obj.get(field), str) or not obj[field].strip():
            raise ValueError(f"{where}.{field} needs nonempty text")


def items(obj, key, where):
    value = obj.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{where}.{key} needs a nonempty array")
    return value


def text_terms(value, glossary):
    if isinstance(value, str):
        for key, _ in TERM.findall(value):
            if key not in glossary:
                raise ValueError(f"no reader glossary entry for {key!r}")
    elif isinstance(value, dict):
        for entry in value.values():
            text_terms(entry, glossary)
    elif isinstance(value, list):
        for entry in value:
            text_terms(entry, glossary)


def check_item(obj, fields, where, anchors, directory):
    require_text(obj, fields + " anchor", where)
    if obj["anchor"] not in anchors or obj["anchor"].startswith("view/"):
        raise ValueError(f"{where}.anchor does not identify a reader target: {obj['anchor']!r}")
    if "page" in obj and (type(obj["page"]) is not int or obj["page"] < 1):
        raise ValueError(f"{where}.page needs a positive PDF page number")
    if "table" in obj:
        table = obj["table"]
        require_text(table, "caption", where + ".table")
        cols = items(table, "columns", where + ".table")
        rows = items(table, "rows", where + ".table")
        if not all(isinstance(c, str) and c.strip() for c in cols):
            raise ValueError(f"{where}.table.columns needs labeled columns")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(cols) or not all(type(c) in (str, int, float) for c in row):
                raise ValueError(f"{where}.table row does not match its columns")
    if "figure" in obj:
        fig = obj["figure"]
        require_text(fig, "path caption", where + ".figure")
        path = directory / fig["path"]
        obj["figure"] = {"caption": fig["caption"], "src": image_uri(path)}


def prepare(spec, index, glossary, directory):
    require_text(spec, "title summary", "guide")
    for key in ("byline", "flow_label"):
        if key in spec:
            require_text(spec, key, "guide")
    text_terms(spec, glossary)
    graph = spec.get("overview")
    require_text(graph, "root", "overview")
    nodes = items(graph, "nodes", "overview")
    kinds = {}
    for i, node in enumerate(nodes):
        where = f"overview.nodes[{i}]"
        check_item(node, "id label kind summary detail", where, index.ids, directory)
        if node["id"] in kinds or node["kind"] not in ("root", "branch", "method", "shared", "evidence"):
            raise ValueError(f"{where} has a duplicate id or unknown kind")
        kinds[node["id"]] = node["kind"]
    if [k for k, kind in kinds.items() if kind == "root"] != [graph["root"]]:
        raise ValueError("overview.root must match the single root node")
    for node in nodes:
        group = node.get("group", "")
        kind = node["kind"]
        if kind in ("root", "shared") and group:
            raise ValueError(f"{node['id']} must have an empty group")
        if kind == "branch" and group != node["id"]:
            raise ValueError(f"{node['id']} must own its branch group")
        if kind in ("method", "evidence") and kinds.get(group) != "branch":
            raise ValueError(f"{node['id']} needs a declared branch group")
    if "branch" not in kinds.values():
        raise ValueError("overview needs a branch")
    neighbors = {k: set() for k in kinds}
    for edge in items(graph, "edges", "overview"):
        require_text(edge, "from to label", "overview.edges")
        a, b = edge["from"], edge["to"]
        if a not in kinds or b not in kinds or a == b:
            raise ValueError(f"invalid overview edge: {a!r} to {b!r}")
        neighbors[a].add(b)
        neighbors[b].add(a)
    pending = [graph["root"]]
    visited = set()
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(neighbors[node] - visited)
    if visited != kinds.keys():
        raise ValueError("overview contains a node disconnected from the paper")
    for key, fields in (("flow", "title input action output role"), ("depth", "title condition conclusion mechanism evidence")):
        for i, item in enumerate(items(spec, key, "guide")):
            check_item(item, fields, f"{key}[{i}]", index.ids, directory)


def render_frame(key, spec, pdf_url, glossary):
    fragment = (ASSETS / (key + ".html")).read_text(encoding="utf8")
    style = "\n".join(re.findall(r"<style>(.*?)</style>", fragment, flags=re.S))
    fragment = re.sub(r"<style>.*?</style>", "", fragment, flags=re.S)
    frame = (ASSETS / "guide.html").read_text(encoding="utf8")
    canonical = (ASSETS.parent / "template.html").read_text(encoding="utf8")
    start = canonical.index('<div id="term-tooltip"')
    end = canonical.index("</script>", canonical.index('<script id="term-tooltip-runtime">', start)) + len("</script>")
    tooltip = canonical[start:end]
    tooltip = re.sub(r"<!--.*?-->", "", tooltip, flags=re.S).replace('type="application/json">{}</script>', 'type="application/json">'+embedded_json(glossary)+'</script>')
    esc = lambda value: html.escape(value, quote=True)
    fields = {
        "TITLE": esc(spec["title"]), "SUMMARY": esc(spec["summary"]), "BYLINE": esc(spec.get("byline", "")),
        "CSS": style, "VIEW": fragment, "TOOLS": tooltip,
        "DATA": embedded_json(spec[key]), "PDF": embedded_json(pdf_url),
        "PDF_LINK": '<a href="'+esc(pdf_url)+'" rel="noopener">论文 PDF ↗</a>' if pdf_url else "",
    }
    return slots(frame, fields)


def slots(template, values):
    return re.sub(r"\[\[([A-Z_]+)\]\]", lambda m: values[m[1]], template)


def build(reader_path, spec_path, output, pdf=None):
    if output.resolve() in {reader_path.resolve(), spec_path.resolve()}:
        raise ValueError("output must be separate from the input files")
    note = reader_path.read_text(encoding="utf-8-sig")
    index = ReaderIndex()
    index.feed(note)
    if "guide-documents" in index.ids or "note-stage" in index.ids:
        raise ValueError("reader is already a multiview note; use the original reading body")
    shell = (ASSETS/"shell.html").read_text(encoding="utf8")
    reserved = set(re.findall(r'\bid="([^"]+)"', shell)) | {"pane-" + view for view in VIEWS}
    collisions = index.ids & reserved
    if collisions:
        raise ValueError(f"reader uses a navigation shell ID: {', '.join(sorted(collisions))}")
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    glossary = json.loads("".join(index.definition_text)) if index.definition_text is not None else {}
    if not isinstance(glossary, dict):
        raise ValueError("reader glossary must be an object")
    prepare(spec, index, glossary, spec_path.parent)
    pdf_url = ""
    if pdf:
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        pdf_url = file_href(pdf, output.parent)
    docs = {k: render_frame(k, spec, pdf_url, glossary) for k in VIEWS}
    body = re.search(r"<body\b[^>]*>(.*)</body\s*>", note, re.S | re.I)
    if not body or "</head>" not in note:
        raise ValueError("reader needs a complete HTML document")
    text = body[1]
    def rebase(link):
        parts = urlsplit(html.unescape(link["url"]))
        if not parts.path or parts.scheme or parts.netloc or parts.path.startswith("/"):
            return link[0]
        dest = reader_path.parent / unquote(parts.path)
        if link["tag"].lower() == "img":
            href = image_uri(dest)
        elif reader_path.parent.resolve() == output.parent.resolve():
            return link[0]
        else:
            href = file_href(dest, output.parent)
            if parts.query:
                href += "?" + parts.query
            if parts.fragment:
                href += "#" + parts.fragment
        return link["prefix"] + html.escape(href, quote=True) + link["quote"]

    text = re.sub(r'''(?P<prefix><(?P<tag>a|img)\b[^<>]*?\s(?:href|src)=(?P<quote>["']))(?P<url>(?!data:)[^"']+)(?P=quote)''', rebase, text, flags=re.I)
    names = {"overview":"文献鸟瞰", "flow":spec.get("flow_label","工艺流程图"), "depth":"分层精读", "reading":"精读解析"}
    tabs = "".join(f'<button type="button" data-mode="{k}" aria-controls="pane-{k}" aria-pressed="false">{html.escape(n)}</button>' for k,n in names.items())
    panels = "".join(f'<section class="note-pane" id="pane-{k}" aria-label="{html.escape(names[k],quote=True)}" inert aria-hidden="true"></section>' for k in VIEWS)
    options = "".join(f'<option value="{html.escape(k,quote=True)}">{html.escape(t)}</option>' for k,t in index.headings)
    style = re.search(r"<style>.*?</style>", shell, re.S)[0]
    result = (note[:body.start()].replace("</head>", style+"\n</head>")+
              '<body class="four-mode-note">'+slots(shell.replace(style,""), {
                  "TABS":tabs, "OPTIONS":options, "PANES":panels, "READER":text, "DOCUMENTS":embedded_json(docs)
              })+"</body></html>\n")
    output.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode="w",encoding="utf8",dir=output.parent,delete=False) as f:
        temp = Path(f.name)
        try:
            f.write(result)
        except BaseException:
            f.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("reader",type=Path)
    cli.add_argument("guides",type=Path)
    cli.add_argument("-o","--output",type=Path,required=True)
    cli.add_argument("--pdf",type=Path)
    args = cli.parse_args()
    try:
        build(args.reader,args.guides,args.output,args.pdf)
    except (OSError, ValueError) as exc:
        cli.exit(1,f"Cannot build note: {exc}\n")
    print(f"Built four reading views: {args.output}")


if __name__ == "__main__":
    main()
