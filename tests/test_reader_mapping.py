"""Ensure each public story card resolves to one real section in the published HTML.

The approved UI reads an existing article section directly; no news is re-generated.
Uses the Python standard library and supports existing 2026-10-14/16/17/18 structures.
"""
import json
import re
import unittest
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "")).casefold()


class SectionHeadings(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section_stack = []
        self.current_heading = None
        self.headings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section":
            inherited = self.section_stack[-1] if self.section_stack else None
            self.section_stack.append(attrs.get("id") or inherited)
        if tag in ("h2", "h3") and self.current_heading is None:
            self.current_heading = [tag, self.section_stack[-1] if self.section_stack else None, ""]

    def handle_data(self, data):
        if self.current_heading is not None:
            self.current_heading[2] += data

    def handle_endtag(self, tag):
        if self.current_heading is not None and tag == self.current_heading[0]:
            self.headings.append((self.current_heading[1], normalize(self.current_heading[2])))
            self.current_heading = None
        if tag == "section" and self.section_stack:
            self.section_stack.pop()


class ReaderMappingTests(unittest.TestCase):
    def test_all_published_catalog_stories_have_one_article_section(self):
        catalog = json.loads((ROOT / "site/catalog.json").read_text(encoding="utf-8"))
        for issue in catalog["issues"]:
            source = ROOT / issue["html"]
            with self.subTest(issue=issue["date"]):
                self.assertTrue(source.is_file(), "Published HTML must exist")
                parser = SectionHeadings()
                parser.feed(source.read_text(encoding="utf-8"))
                for story in issue.get("stories", []):
                    with self.subTest(story=story["id"]):
                        hits = [section_id for section_id, title in parser.headings
                                if title == normalize(story["title"])]
                        self.assertEqual(len(hits), 1, "Story title must match one real heading")
                        self.assertTrue(hits[0], "Matched article must be in a named section")

    def test_approved_reader_requires_source_content_not_only_issue_link(self):
        script = (ROOT / "assets/app.js").read_text(encoding="utf-8")
        self.assertIn("findPublishedStory(doc,story)", script)
        self.assertIn("addPublishedDetails(reader,section,story,", script)
        self.assertIn("loadPublishedDocument(issue)", script)
        self.assertNotIn("正文请打开当天已发布的完整页面", script)


if __name__ == "__main__":
    unittest.main()
