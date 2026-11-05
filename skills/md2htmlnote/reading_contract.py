"""Shared structural checks for term help and contextual figure/table placement."""
from html.parser import HTMLParser
import json
import re

FIGURE = re.compile(r'(?:图|Fig(?:ure)?\.?)\s*(\d+)', re.I)
TABLE = re.compile(r'(?:表|Table)\s*(\d+)', re.I)


class ReadingPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.terms = []
        self.has_key_terms = False
        self.scripts = {}
        self.script_types = {}
        self.tooltip = []
        self.tooltip_depth = 0
        self.tooltip_parts = set()
        self.tables = []
        self.uncaptioned_tables = []
        self.script_id = None
        self.in_script = False
        self.section = ''
        self.last_paragraph = ''
        self.paragraph = None
        self.caption = None
        self.visuals = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get('class', '').split()
        self.has_key_terms |= 'key-term' in classes
        if 'data-term' in attrs or 'term' in classes:
            self.terms.append(attrs)
        if attrs.get('id') == 'term-tooltip':
            self.tooltip.append(attrs)
            self.tooltip_depth = 1
        elif self.tooltip_depth:
            self.tooltip_parts.update(classes)
            if tag not in ('br', 'img', 'hr', 'input', 'meta', 'link'):
                self.tooltip_depth += 1
        if tag == 'table':
            self.tables.append({'caption': False, 'external': TABLE.findall(self.last_paragraph)})
        elif tag == 'caption' and self.tables:
            self.tables[-1]['caption'] = True
        if tag == 'script':
            self.in_script = True
            self.script_id = attrs.get('id')
            if self.script_id:
                self.scripts.setdefault(self.script_id, []).append('')
                self.script_types[self.script_id] = attrs.get('type')
        elif tag in ('h2', 'h3'):
            self.section = attrs.get('id', '')
            self.last_paragraph = ''
        elif tag == 'p':
            self.paragraph = []
        elif tag in ('caption', 'figcaption'):
            self.caption = (tag, [])

    def handle_data(self, data):
        if self.in_script:
            if self.script_id:
                self.scripts[self.script_id][-1] += data
            return
        if self.caption:
            self.caption[1].append(data)
        elif self.paragraph is not None:
            self.paragraph.append(data)

    def handle_endtag(self, tag):
        if self.tooltip_depth:
            self.tooltip_depth -= 1
        if tag == 'table' and self.tables:
            table = self.tables.pop()
            if not table['caption']:
                self.uncaptioned_tables.extend(table['external'])
        if tag == 'script':
            self.script_id = None
            self.in_script = False
        elif tag == 'p' and self.paragraph is not None:
            self.last_paragraph = ''.join(self.paragraph)
            self.paragraph = None
        elif tag in ('caption', 'figcaption') and self.caption:
            kind, text = self.caption
            self.visuals.append((kind, ''.join(text), self.section, self.last_paragraph))
            self.caption = None


def check_reading_experience(html: str) -> list[str]:
    page = ReadingPage()
    page.feed(html)
    errors = []
    if page.has_key_terms and not page.terms:
        errors.append('technical terms need .term[data-term] explanations')
    if page.terms:
        definitions = {}
        entries = page.scripts.get('term-definitions', [])
        if len(entries) != 1 or page.script_types.get('term-definitions') != 'application/json':
            errors.append('need one script#term-definitions[type="application/json"]')
        else:
            try:
                definitions = json.loads(entries[0])
                if not isinstance(definitions, dict):
                    raise ValueError('glossary must be an object')
            except (ValueError, TypeError):
                errors.append('invalid term-definitions JSON object')
                definitions = {}
        for term in page.terms:
            key = term.get('data-term', '')
            if 'term' not in term.get('class', '').split() or term.get('tabindex') != '0':
                errors.append(f'term {key!r} needs .term and tabindex="0"')
            definition = definitions.get(key)
            if not key or not isinstance(definition, dict) or not all(
                isinstance(definition.get(field), str) and definition[field].strip()
                for field in ('title', 'description')
            ):
                errors.append(f'term {key!r} needs a title and description')
        if len(page.tooltip) != 1 or page.tooltip[0].get('role') != 'tooltip' or 'hidden' not in page.tooltip[0]:
            errors.append('need one initially hidden #term-tooltip[role="tooltip"]')
        if not {'term-tooltip-title', 'term-tooltip-description'} <= page.tooltip_parts:
            errors.append('tooltip needs title and description child elements')
        runtime = page.scripts.get('term-tooltip-runtime', [])
        if len(runtime) != 1 or not runtime[0].strip() or page.script_types.get('term-tooltip-runtime') not in (None, 'text/javascript', 'application/javascript'):
            errors.append('need one nonempty executable term-tooltip-runtime')
    for number in page.uncaptioned_tables:
        errors.append(f'numbered table {number} needs an internal caption, not an external title paragraph')
    for kind, caption, section, paragraph in page.visuals:
        pattern = FIGURE if kind == 'figcaption' else TABLE
        for number in pattern.findall(caption):
            if number not in pattern.findall(paragraph):
                label = 'figure' if kind == 'figcaption' else 'table'
                errors.append(f'{label} {number} needs a preceding explanatory paragraph in section {section!r}')
    return list(dict.fromkeys(errors))
