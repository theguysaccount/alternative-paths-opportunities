"""Washington State's register of registered apprenticeship programs (Department of Labor & Industries),
read from its open-data API on data.wa.gov.

    python3 -m pipeline.wa            # refresh data/wa/ (daily job; the state updates the data monthly)

Kept: program and occupation names, occupation code, term and classroom hours, starting and
journey-level wages, and the counties a program serves. Never kept: contact names, e-mail
addresses, phone numbers or street addresses (they are in the state's data, but this site
publishes no personal data). Only active programs, active occupations and occupations with a
published starting wage are listed: a registered apprenticeship is paid work, and the starting
wage is the evidence. Pre-apprenticeship (preparatory) programs are left out because the
data does not show that they pay.

Fails safely: if any dataset can't be read or looks broken, the last good data is kept and the
run says so. Standard library only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "wa")
UA = "AlternativePathsBot/1.0 (+https://github.com/theguysaccount/alternative-paths-opportunities)"
API = "https://data.wa.gov"
DATASETS = {"programs": "4mxd-hz2q", "occupations": "6zih-i79k", "counties": "euks-5kq7"}
DELAY = 1.5          # data.wa.gov asks for a crawl delay of 1 second
MIN_LISTINGS = 100   # fewer active listings than this means a broken read, not a real change
_last = [0.0]


def get_json(url: str):
    for attempt in range(3):
        wait = _last[0] + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"{url}: {err}")


def rows(ds: str, where: str = "", select: str = "") -> list[dict]:
    out, offset = [], 0
    while True:
        q = {"$limit": 5000, "$offset": offset, "$order": ":id"}
        if where:
            q["$where"] = where
        if select:
            q["$select"] = select
        batch = get_json(f"{API}/resource/{ds}.json?" + urllib.parse.urlencode(q))
        out += batch
        if len(batch) < 5000:
            return out
        offset += 5000


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def money(s) -> float | None:
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v if 0 < v < 500 else None


def clean_url(u: str) -> str:
    u = (u or "").strip()
    if not u or " " in u or "@" in u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u if re.match(r"^https?://[a-z0-9.-]+\.[a-z]{2,}(/\S*)?$", u, re.I) else ""


def soc_title(desc: str, code: str) -> str:
    d = re.sub(r"\s+", " ", (desc or "").strip()).rstrip(".")
    return d or code or "Other"


def build_listings(programs, occupations, counties):
    prog = {p["programid"]: p for p in programs if p.get("programstatus") == "Active" and not p.get("preparatoryprogram")}
    where = {}
    for c in counties:
        if c.get("programid") in prog and c.get("statecode") == "WA" and c.get("countyname"):
            where.setdefault(c["programid"], set()).add(c["countyname"].title())
    listings = []
    for o in occupations:
        p = prog.get(o.get("programid"))
        start, journey = money(o.get("step1wage")), money(o.get("journeywage"))
        if not p or o.get("occupationstatus") != "Active" or start is None:
            continue
        hours = int(float(o.get("termhours") or 0)) or None
        listings.append({
            "id": o["programoccupationid"], "program_id": p["programid"], "program": p["programname"].strip(),
            "occupation": re.sub(r"\s+", " ", o.get("occupationname", "")).strip(), "soc": o.get("soccode", ""),
            "field": soc_title(o.get("socdescription"), o.get("soccode")), "term_hours": hours,
            "rsi_hours": int(float(o["rsihours"])) if o.get("rsihours") else None,
            "start_wage": start, "journey_wage": journey if journey and journey >= start else None,
            "shop": p.get("openshop") if p.get("openshop") in ("Union", "Non-Union") else None,
            "program_url": clean_url(p.get("programurl", "")), "program_approved": (p.get("approvaldate") or "")[:10],
            "occupation_added": (o.get("addeddate") or "")[:10], "counties": sorted(where.get(p["programid"], [])),
            "source": f"{API}/resource/{DATASETS['occupations']}.json?programoccupationid={o['programoccupationid']}",
        })
    listings.sort(key=lambda x: (x["field"], -x["start_wage"], x["program"]))
    return listings


def meta(ds: str) -> dict:
    m = get_json(f"{API}/api/views/{ds}.json")
    return {"id": ds, "name": m.get("name", ""), "updated": dt.datetime.fromtimestamp(m["rowsUpdatedAt"], dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "page": f"{API}/d/{ds}"}


def main(argv=None) -> int:
    os.makedirs(DATA, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = os.path.join(DATA, "listings.json")
    try:
        old = json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        old = {"listings": [], "datasets": {}}
    try:
        metas = {k: meta(ds) for k, ds in DATASETS.items()}
        programs = rows(DATASETS["programs"], select="programid,programname,programstatus,preparatoryprogram,openshop,programurl,approvaldate")
        occupations = rows(DATASETS["occupations"], where="occupationstatus='Active' AND programstatus='Active'")
        counties = rows(DATASETS["counties"])
        listings = build_listings(programs, occupations, counties)
        if len(listings) < MIN_LISTINGS:
            raise RuntimeError(f"only {len(listings)} active listings; keeping the last good data")
    except Exception as e:  # noqa: BLE001 - any failure keeps the last good data
        print(f"::warning::Washington register not refreshed: {e}")
        old["last_error"] = str(e)[:300]
        old["last_attempt"] = now
        json.dump(old, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0
    before = {x["id"]: x for x in old.get("listings", [])}
    after = {x["id"]: x for x in listings}
    added = [after[i] for i in after if i not in before]
    removed = [before[i] for i in before if i not in after]
    changes_path = os.path.join(DATA, "changes.json")
    try:
        changes = json.load(open(changes_path, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        changes = []
    if before and (added or removed):
        day = metas["occupations"]["updated"][:10]
        changes.append({"date": day, "detected": now[:10], "added": [{"id": x["id"], "program": x["program"], "occupation": x["occupation"]} for x in added],
                        "removed": [{"id": x["id"], "program": x["program"], "occupation": x["occupation"]} for x in removed]})
        changes = changes[-200:]
        json.dump(changes, open(changes_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out = {"checked": now, "datasets": metas, "listings": listings, "last_error": ""}
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Washington: {len(listings)} paid apprenticeship listings ({len(added)} new, {len(removed)} no longer active); "
          f"state data updated {metas['occupations']['updated'][:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
