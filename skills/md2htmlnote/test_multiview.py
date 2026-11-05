"""Offline CLI tests for the registered two-signal multiview example."""
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urldefrag, urljoin, urlsplit


SKILL = Path(__file__).resolve().parent
EXAMPLE = SKILL.parents[1] / "examples" / "registered-paper"
SIGNALS = Path("_tmp/P1/raw/images/signals.png")
READER_STYLE = ".content figcaption { font-style: italic; }"
BLANK_PDF = (
    b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
    b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
    b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 72 72]/Resources<<>>>>\nendobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000054 00000 n \n0000000105 00000 n \n"
    b"trailer\n<</Size 4/Root 1 0 R>>\nstartxref\n182\n%%EOF\n"
)


class Page(HTMLParser):
    """Inspect actual tags separately from HTML strings inside script data."""

    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.closed = set()
        self.main = []
        self.text = []
        self.guide_blocks = []
        self._in_main = False
        self._raw_tag = None
        self._guide_chunks = None
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "main" and "content" in attrs.get("class", "").split():
            self._in_main = True
        if self._in_main:
            self.main.append(("start", tag, attrs))
        if tag in ("script", "style"):
            self._raw_tag = tag
        if tag == "script" and attrs.get("id") == "guide-documents":
            self._guide_chunks = []
            self.guide_blocks.append((attrs, self._guide_chunks))

    def handle_endtag(self, tag):
        self.closed.add(tag)
        if self._in_main:
            self.main.append(("end", tag))
            if tag == "main":
                self._in_main = False
        if tag == self._raw_tag:
            self._raw_tag = self._guide_chunks = None

    def handle_data(self, data):
        if self._guide_chunks is not None:
            self._guide_chunks.append(data)
        if self._raw_tag is None and data.strip():
            self.text.append(data.strip())
            if self._in_main:
                self.main.append(("text", data.strip()))

    def attrs(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


class MultiviewCLI(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.guides = self.root / "guides" / "guide-example.json"
        image = self.guides.parent / SIGNALS
        image.parent.mkdir(parents=True)
        shutil.copyfile(EXAMPLE / SIGNALS, image)
        shutil.copyfile(EXAMPLE / self.guides.name, self.guides)
        self.spec = json.loads(self.guides.read_text(encoding="utf-8"))
        self.image_uri = "data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")

        self.reader = self.root / "reader" / "reading.html"
        self.reader.parent.mkdir()
        self.reader.write_text(f"""<!doctype html>
<html><head><style>{READER_STYLE}</style></head>
<body><main class="content"><h2 id="s1">Signal values</h2>
<p>Signal A is 1 arbitrary unit and signal B is 2. See <a href="#fig-1">Figure 1</a>.</p>
<figure id="fig-1"><img src="{self.image_uri}" alt="The two signal bars">
<figcaption>Figure 1. Upper bar A (1 unit), lower bar B (2 units).</figcaption></figure>
<h2 id="s2">Ratio</h2><p id="eq-1">Equation (1): r = 2 / 1 = 2.</p>
</main></body></html>""", encoding="utf-8")
        self.output = self.root / "export" / "v1" / "note.html"
        self.output.parent.mkdir(parents=True)

    def run_cli(self, *, reader=None, output=None, pdf=None):
        args = [
            sys.executable, "-B", "-X", "utf8", SKILL / "build_multiview.py",
            reader or self.reader, self.guides, "-o", output or self.output,
        ]
        if pdf is not None:
            args.extend(["--pdf", pdf])
        return subprocess.run(args, cwd=self.root, capture_output=True, encoding="utf-8", timeout=30)

    def build(self, *, pdf=None):
        result = self.run_cli(pdf=pdf)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return self.output.read_text(encoding="utf-8")

    def documents(self, shell):
        self.assertEqual(len(shell.guide_blocks), 1)
        attrs, chunks = shell.guide_blocks[0]
        self.assertEqual(attrs.get("type"), "application/json")
        docs = json.loads("".join(chunks))
        self.assertIsInstance(docs, dict)
        self.assertEqual(set(docs), {"overview", "flow", "depth"})
        return docs

    def test_one_portable_file_preserves_reader_and_contains_three_documents(self):
        html = self.build()
        shell = Page(html)
        self.assertEqual(list(self.output.parent.rglob("*")), [self.output])
        self.assertEqual(shell.main, Page(self.reader.read_text(encoding="utf-8")).main)
        self.assertEqual([f.get("id") for f in shell.attrs("figure")], ["fig-1"])
        self.assertIn(READER_STYLE, html)
        pages = {"reader": shell}
        for view, source in self.documents(shell).items():
            with self.subTest(view=view):
                self.assertIsInstance(source, str)
                page = pages[view] = Page(source)
                for tag in ("html", "head", "body"):
                    self.assertEqual(len(page.attrs(tag)), 1)
                    self.assertIn(tag, page.closed)
        for view, page in pages.items():
            with self.subTest(resources=view):
                for link in page.attrs("a"):
                    self.assertFalse(urlsplit(link.get("href", "")).path.endswith(".pdf"))
                for tag, attrs in page.tags:
                    url = attrs.get("src", "")
                    if tag == "link" and "stylesheet" in attrs.get("rel", "").split():
                        url = attrs.get("href", "")
                    if url:
                        self.assertTrue(url.startswith("data:") or url == "about:blank", url)

    def test_signal_labels_table_and_original_png_reach_the_guides(self):
        shell = Page(self.build())
        docs = self.documents(shell)
        self.assertIn(self.spec["flow_label"], shell.text)
        branches = [node for node in self.spec["overview"]["nodes"] if node["kind"] == "branch"]
        self.assertEqual(len(branches), 2)
        for branch in branches:
            self.assertIn(branch["label"], docs["overview"])
        for view in ("flow", "depth"):
            self.assertGreaterEqual(len(self.spec[view]), 2)
            for item in self.spec[view]:
                self.assertIn(item["title"], docs[view])
        self.assertIn(self.spec["flow"][0]["table"]["caption"], docs["flow"])
        self.assertIn("2 / 1 = 2", docs["flow"])
        self.assertIn(self.spec["depth"][0]["figure"]["caption"], docs["depth"])
        image_urls = re.findall(r"""["'](data:image/png;base64,[^"']+)["']""", docs["depth"])
        self.assertIn(self.image_uri, image_urls, "Depth guide needs the bytes of signals.png")
        for term in ("SMT", "锡膏"):
            self.assertNotIn(term, " ".join(shell.text) + "".join(docs.values()))

    def test_reader_and_guide_pdf_links_resolve_from_output(self):
        pdf = self.reader.parent / "docs" / "paper.pdf"
        pdf.parent.mkdir()
        pdf.write_bytes(BLANK_PDF)
        link = '<a href="docs/paper.pdf#page=1">Source PDF</a>'
        reader = self.reader.read_text(encoding="utf-8")
        self.reader.write_text(reader.replace("</main>", link + "</main>"), encoding="utf-8")
        for item in (self.spec["overview"]["nodes"][0], self.spec["flow"][0], self.spec["depth"][0]):
            item["page"] = 1
        self.guides.write_text(json.dumps(self.spec), encoding="utf-8")

        shell = Page(self.build(pdf=pdf))
        pages = {"reader": shell, **{view: Page(source) for view, source in self.documents(shell).items()}}
        for view, page in pages.items():
            with self.subTest(view=view):
                hrefs = [a["href"] for a in page.attrs("a")
                         if urlsplit(a.get("href", "")).path.endswith(".pdf")]
                self.assertTrue(hrefs, "Expected a link to docs/paper.pdf")
                for href in hrefs:
                    self.assertFalse(urlsplit(href).scheme or href.startswith(("/", "\\")), href)
                    target, fragment = urldefrag(urljoin(self.output.as_uri(), href))
                    self.assertEqual(target, pdf.as_uri())
                    if view == "reader":
                        self.assertEqual(fragment, "page=1")

    def test_invalid_anchors_and_edges_preserve_previous_output(self):
        self.build()
        previous = self.output.read_bytes()
        graph = self.spec["overview"]
        for location, item, field in (
            ("node", graph["nodes"][0], "anchor"), ("step", self.spec["flow"][0], "anchor"),
            ("topic", self.spec["depth"][0], "anchor"), ("edge", graph["edges"][0], "from"),
            ("edge", graph["edges"][0], "to"),
        ):
            with self.subTest(location=location, field=field):
                original = item[field]
                # Both names occur in the reader: a CSS class and a figure anchor.
                item[field] = "content" if field == "anchor" else "fig-1"
                self.guides.write_text(json.dumps(self.spec), encoding="utf-8")
                item[field] = original
                self.assertNotEqual(self.run_cli().returncode, 0)
                self.assertEqual(self.output.read_bytes(), previous)

    def test_rejects_a_reader_that_already_contains_guides(self):
        self.build()
        nested = self.output.with_name("nested.html")
        result = self.run_cli(reader=self.output, output=nested)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(nested.exists())

    def test_shell_id_collision_preserves_published_output(self):
        original = self.build()
        content = self.reader.read_text(encoding="utf-8")
        self.reader.write_text(content.replace("</main>", '<p id="pane-flow">A stage</p></main>'), encoding="utf-8")
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), original)

    def test_cross_drive_pdf_falls_back_to_file_url(self):
        from unittest.mock import patch
        from build_multiview import file_href
        pdf = self.root / "my paper.pdf"
        with patch("build_multiview.os.path.relpath", side_effect=ValueError("different drives")):
            self.assertEqual(file_href(pdf, self.output.parent), pdf.resolve().as_uri())


if __name__ == "__main__":
    unittest.main()
