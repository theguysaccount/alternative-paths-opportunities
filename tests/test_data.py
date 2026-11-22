import json
import os
import re
import unittest

from pipeline import store as S

LOADED = re.compile(r"\b(guaranteed job|get rich|easy money|scam\w*|best|top-rated|amazing)\b", re.I)


class ProgramTests(unittest.TestCase):
    def test_programs(self):
        progs = S.apps()
        self.assertGreater(len(progs), 0)
        for p in progs:
            with self.subTest(p=p["slug"]):
                for k in ("slug", "name", "agency", "kind", "status", "status_label", "link", "reviewed", "documents", "facts"):
                    self.assertTrue(p.get(k), k)
                self.assertIn(p["status"], ("open", "closed"))
                self.assertTrue(p["link"].startswith("https://"))
                self.assertTrue("pay" in p["facts"] or "what" in p["facts"])
                used = set()
                for _w, fid, ev in S.evidence(p):
                    self.assertIn(ev["doc"], p["documents"])
                    self.assertTrue(ev["quote"].strip())
                    used.add(ev["doc"])
                self.assertEqual(used, set(p["documents"]), "every document is quoted")
                for f in p["facts"].values():
                    self.assertTrue(f["evidence"], "every fact cites a passage")
                    self.assertIsNone(LOADED.search(f["summary"]), f["summary"])


class WashingtonDataTests(unittest.TestCase):
    def test_listings_file(self):
        path = os.path.join(S.DATA, "wa", "listings.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreater(len(data["listings"]), 0)
        ids = [x["id"] for x in data["listings"]]
        self.assertEqual(len(ids), len(set(ids)))
        for x in data["listings"]:
            self.assertGreater(x["start_wage"], 0)
            self.assertTrue(x["source"].startswith("https://data.wa.gov/"))
            self.assertFalse({"contactname", "contactemail", "contactphone", "mailingaddress", "physicaladdress"} & set(x))
        self.assertTrue(data["datasets"]["occupations"]["updated"])


if __name__ == "__main__":
    unittest.main()
