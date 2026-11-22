import html
import json
import os
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit

from pipeline import build as B
from pipeline import store as S

SITE = "https://theguysaccount.github.io/alternative-paths-opportunities"


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = tempfile.mkdtemp()
        cls.ctx = B.build(cls.out, site_url=SITE, env={})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out)

    def page(self, rel):
        return read(os.path.join(self.out, rel))

    def test_pages(self):
        for rel in ("index.html", "washington/index.html", "about/index.html", "404.html", "feed.xml", "sitemap.xml",
                    "robots.txt", "data/opportunities.json", "og/home.png", "og/washington.png"):
            self.assertTrue(os.path.exists(os.path.join(self.out, rel)), rel)
        for g in self.ctx.groups:
            self.assertTrue(os.path.exists(os.path.join(self.out, "washington", B.slug(g), "index.html")), g)
        for p in S.apps():
            page = self.page(f"programs/{p['slug']}/index.html")
            for _w, _f, ev in S.evidence(p):
                self.assertIn(html.escape(ev["quote"]), page)
            self.assertIn('class="correction"', page)

    def test_every_listing_is_shown_with_its_source(self):
        p = self.page("washington/index.html")
        self.assertIn(f'data-count="{len(self.ctx.listings)}"', p)
        self.assertEqual(p.count('<tr id="l'), len(self.ctx.listings))
        self.assertEqual(p.count('class="src"'), len(self.ctx.listings))
        total = sum(self.page(f"washington/{B.slug(g)}/index.html").count('<tr id="l') for g in self.ctx.groups)
        self.assertEqual(total, len(self.ctx.listings))

    def test_no_personal_data_and_no_job_claims(self):
        blob = self.page("data/opportunities.json") + self.page("washington/index.html")
        self.assertNotIn("contactemail", blob)
        self.assertNotRegex(blob, r"[\w.+-]+@[\w-]+\.[\w.]+")       # no e-mail addresses at all
        self.assertNotIn("openings registered", self.page("index.html"))

    def test_sitemap_canonicals_links_feed(self):
        locs = [el.text for el in ET.fromstring(self.page("sitemap.xml")).iter() if el.tag.endswith("loc")]
        self.assertEqual(len(locs), 3 + len(self.ctx.groups) + len(self.ctx.programs))
        for loc in locs:
            canon = re.search(r'<link rel="canonical" href="([^"]+)"', self.page(loc[len(SITE) + 1:] + "index.html")).group(1)
            self.assertEqual(canon, loc)
        ET.fromstring(self.page("feed.xml"))
        for root, _d, files in os.walk(self.out):
            for name in files:
                if name.endswith(".html") and name != "404.html":
                    rel = os.path.relpath(os.path.join(root, name), self.out)
                    for href in re.findall(r'(?:href|src)="([^"#]+)', read(os.path.join(root, name))):
                        href = html.unescape(href)
                        if re.match(r"^(https?:|mailto:|//)", href):
                            continue
                        target = urlsplit(urljoin("http://x/" + rel, href)).path.lstrip("/")
                        target += "index.html" if target == "" or target.endswith("/") else ""
                        self.assertTrue(os.path.exists(os.path.join(self.out, target)), f"{rel} -> {href}")

    def test_settings(self):
        out = tempfile.mkdtemp()
        try:
            B.build(out, site_url="https://paths.example.org", env={"SUPPORT_URL": "https://example.org/s"})
            home = read(os.path.join(out, "index.html"))
            self.assertIn('<link rel="canonical" href="https://paths.example.org/">', home)
            self.assertIn('href="https://example.org/s"', home)
            self.assertIn("Sitemap: https://paths.example.org/sitemap.xml", read(os.path.join(out, "robots.txt")))
        finally:
            shutil.rmtree(out)
        self.assertNotIn("example.org/s", self.page("index.html"))


if __name__ == "__main__":
    unittest.main()
