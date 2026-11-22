"""Build the static site into dist/ from data/.

    python3 -m pipeline.build

Settings (environment variables; repository variables in Actions):
  SITE_URL         public base URL, no trailing slash: the one setting that moves the site to a custom domain
  SUPPORT_URL, SUPPORT_LABEL   optional money slot (hidden when empty); never a charge to job seekers
  GOATCOUNTER_URL  optional cookieless page counts
  GITHUB_REPOSITORY  owner/name for correction links
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import shutil
import statistics
import sys
from email.utils import format_datetime
from urllib.parse import quote as urlquote

from . import store as S
from . import textutil as T

ROOT = S.ROOT
DEFAULT_SITE_URL = "https://theguysaccount.github.io/alternative-paths-opportunities"
DEFAULT_REPO = "theguysaccount/alternative-paths-opportunities"
BRAND = "Alternative Paths"
CSS_VERSION = "1"
WA_COUNTIES = 39
E = lambda s: html.escape(str(s), quote=True)  # noqa: E731

# 2018 Standard Occupational Classification major groups (U.S. Bureau of Labor Statistics).
SOC_GROUPS = {
    "11": "Management", "13": "Business and Financial Operations", "15": "Computer and Mathematical",
    "17": "Architecture and Engineering", "19": "Life, Physical, and Social Science", "21": "Community and Social Service",
    "23": "Legal", "25": "Educational Instruction and Library", "27": "Arts, Design, Entertainment, Sports, and Media",
    "29": "Healthcare Practitioners and Technical", "31": "Healthcare Support", "33": "Protective Service",
    "35": "Food Preparation and Serving", "37": "Building and Grounds Cleaning and Maintenance",
    "39": "Personal Care and Service", "41": "Sales", "43": "Office and Administrative Support",
    "45": "Farming, Fishing, and Forestry", "47": "Construction and Extraction", "49": "Installation, Maintenance, and Repair",
    "51": "Production", "53": "Transportation and Material Moving", "55": "Military Specific",
}


def slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fmt_day(iso: str) -> str:
    try:
        d = dt.date.fromisoformat((iso or "")[:10])
    except ValueError:
        return ""
    return f"{d.day} {d.strftime('%b')} {d.year}"


def tday(iso: str) -> str:
    return f'<time datetime="{E(iso[:10])}">{fmt_day(iso)}</time>' if iso else ""


def usd(v) -> str:
    return f"${v:,.2f}" if v is not None else ""


def years(hours) -> str:
    if not hours:
        return ""
    y = hours / 2000
    return f"{hours:,} hours (about {y:.0f} year{'s' if round(y) != 1 else ''})" if y >= 0.75 else f"{hours:,} hours"


class Ctx:
    def __init__(self, data, site_url, repo, now, env):
        self.data, self.site, self.repo, self.now = data, site_url.rstrip("/"), repo, now
        self.repo_url = f"https://github.com/{repo}"
        self.support_url = env.get("SUPPORT_URL", "").strip()
        self.support_label = env.get("SUPPORT_LABEL", "").strip() or "Support this project"
        self.goatcounter = env.get("GOATCOUNTER_URL", "").strip()
        wa = S._read(os.path.join(data, "wa", "listings.json"), {"listings": [], "datasets": {}})
        self.wa = wa
        self.listings = wa.get("listings", [])
        for x in self.listings:
            g = (x.get("soc") or "")[:2]
            x["group"] = SOC_GROUPS.get(g, "Other")
            x["group_slug"] = slug(x["group"])
            x["statewide"] = len(x.get("counties", [])) >= WA_COUNTIES
        self.groups = {}
        for x in self.listings:
            self.groups.setdefault(x["group"], []).append(x)
        self.wa_changes = S._read(os.path.join(data, "wa", "changes.json"), [])
        self.wa_updated = (wa.get("datasets", {}).get("occupations") or {}).get("updated", "")
        self.wa_checked = wa.get("checked", "")
        self.state = S.state(data)
        self.programs = []
        for p in sorted(S.apps(data), key=lambda p: (p["kind"] != "Paid while you learn", p["name"])):
            self.programs.append(self.program_view(p))

    def url(self, path=""):
        return f"{self.site}/{path}"

    def program_view(self, p):
        docs = {}
        for d, doc in p["documents"].items():
            st = self.state["docs"].get(f"{p['slug']}/{d}", {})
            docs[d] = {"id": d, "title": doc["title"], "url": doc["url"], "via": st.get("via", ""),
                       "capture": (st.get("capture") or "")[:8], "archive_url": st.get("archive_url", ""),
                       "last_ok": (st.get("last_ok") or "")[:10], "status": st.get("status", "")}
        facts = []
        for fid, f in p["facts"].items():
            evs = []
            for e in f["evidence"]:
                q = self.state["quotes"].get(S.quote_id(p["slug"], e["doc"], e["quote"]), {})
                evs.append({"doc": docs[e["doc"]], "quote": e["quote"], "found": q.get("found", True)})
            facts.append({"id": fid, "summary": f["summary"], "evidence": evs})
        used = {e["doc"]["id"] for f in facts for e in f["evidence"]}
        asof = min((docs[d]["last_ok"] or p["reviewed"]) for d in used) if used else p["reviewed"]
        return dict(p, docs=docs, fact_list=facts, asof=asof, missing=sum(1 for f in facts for e in f["evidence"] if not e["found"]))


# ---------------------------------------------------------------------------------------------

def head(ctx, title, desc, path, depth, og, jsonld, noindex=False):
    pre = "../" * depth
    canon = ctx.url(path)
    ld = "".join('<script type="application/ld+json">' + json.dumps(j, ensure_ascii=False).replace("</", "<\\/")
                 + "</script>" for j in jsonld)
    gc = (f'<script data-goatcounter="{E(ctx.goatcounter)}" async src="//gc.zgo.at/count.js"></script>' if ctx.goatcounter else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(canon)}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(canon)}">
<meta property="og:image" content="{E(ctx.url(og))}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="{BRAND}: new programs and changes" href="{E(ctx.url('feed.xml'))}">
<link rel="stylesheet" href="{pre}assets/site.css?v={CSS_VERSION}">
{ld}{gc}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap">
<a class="brand" href="{pre or './'}"><svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true"><rect x="3" y="3" width="26" height="26" rx="7" fill="#2f6f4f"/><path d="M8 23c4-1 6-5 8-9s4-6 8-6" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><circle cx="24" cy="8" r="2.6" fill="#f4d35e"/></svg>{BRAND}</a>
<nav aria-label="Main"><a href="{pre or './'}">Home</a><a href="{pre}washington/">Washington apprenticeships</a><a href="{pre}about/">About</a></nav>
</div></header>
<main id="main" class="wrap">
"""


def foot(ctx, depth):
    pre = "../" * depth
    support = f'<a href="{E(ctx.support_url)}" rel="noopener">{E(ctx.support_label)}</a> · ' if ctx.support_url else ""
    privacy = "Page counts are cookieless (GoatCounter)." if ctx.goatcounter else "No cookies, no tracking."
    return f"""</main>
<footer class="foot"><div class="wrap">
<p>{BRAND} lists paid training only from official sources, each linked with its date. Nothing listed charges job seekers, and no listing is sponsored. Not affiliated with any program listed.</p>
<p><a href="{ctx.repo_url}/issues/new/choose" rel="noopener">Report a problem</a> · <a href="{pre}feed.xml">New programs (RSS)</a> · <a href="{pre}data/opportunities.json">Open data</a> · <a href="{ctx.repo_url}" rel="noopener">Source code</a> · {support}{privacy}</p>
<p class="small">Built {tday(ctx.now.strftime('%Y-%m-%d'))}. Not career, legal or financial advice: check each program's own page before applying.</p>
</div></footer>
<pre id="selftest" hidden></pre>
<script src="{pre}assets/site.js?v={CSS_VERSION}" defer></script>
</body>
</html>
"""


def how_read(d):
    if d["via"] == "wayback" and d["capture"]:
        return (f'Internet Archive copy of {fmt_day(d["capture"][:4] + "-" + d["capture"][4:6] + "-" + d["capture"][6:8])} '
                f'(<a href="{E(d["archive_url"])}" rel="nofollow noopener">open the copy</a>)')
    return f"read {tday(d['last_ok'])}" if d["last_ok"] else "quoted from the reviewed version"


def quote_html(e):
    d = e["doc"]
    miss = "" if e["found"] else '<p class="missing" role="note">Not found word for word in the latest text; waiting for re-review.</p>'
    return (f'<blockquote class="q{"" if e["found"] else " q-missing"}" cite="{E(d["url"])}"><p>“{E(e["quote"])}”</p>{miss}'
            f'<footer><a class="src" href="{E(d["url"] + T.text_fragment(e["quote"]))}" rel="nofollow noopener">{E(d["title"])}</a> · '
            f'<span class="how">{how_read(d)}</span></footer></blockquote>')


def listing_rows(ctx, items, pre):
    out = []
    for x in items:
        where = "Statewide" if x["statewide"] else (", ".join(x["counties"][:4]) + (f" and {len(x['counties']) - 4} more" if len(x["counties"]) > 4 else "") or "Not listed")
        links = [f'<a class="src" href="{E(x["source"])}" rel="nofollow noopener">official record</a>']
        if x.get("program_url"):
            links.insert(0, f'<a href="{E(x["program_url"])}" rel="nofollow noopener">program site</a>')
        out.append(f"""<tr id="l{E(x['id'])}" data-group="{E(x['group_slug'])}" data-counties="|{E('|'.join(x['counties']))}|" data-wage="{x['start_wage']}" data-text="{E((x['occupation'] + ' ' + x['program'] + ' ' + x['field']).lower())}">
<th scope="row">{E(x['occupation'])}<br><span class="small">{E(x['program'])}</span></th>
<td class="num">{usd(x['start_wage'])}<span class="small"> /hr</span>{('<br><span class="small">to ' + usd(x['journey_wage']) + ' /hr</span>') if x.get('journey_wage') else ''}</td>
<td>{E(years(x.get('term_hours')))}</td><td>{E(where)}</td><td class="links">{' · '.join(links)}</td></tr>""")
    return "".join(out)


def table(ctx, items, pre, caption=""):
    return f"""<div class="scroll" tabindex="0" role="region" aria-label="Apprenticeships, scroll sideways">
<table class="list" id="list" data-count="{len(items)}"><thead><tr><th scope="col">Occupation and program</th><th scope="col">Starting wage</th><th scope="col">Length</th><th scope="col">Where</th><th scope="col">Links</th></tr></thead>
<tbody>{listing_rows(ctx, items, pre)}</tbody></table></div>
<p class="small">Wages and lengths as registered with Washington State's Department of Labor & Industries, from its data updated {tday(ctx.wa_updated)} (checked {tday(ctx.wa_checked)}). "Official record" opens the state's own record for that occupation. Apply through the program, not through this site.</p>"""


def page_home(ctx):
    starts = [x["start_wage"] for x in ctx.listings]
    med = statistics.median(starts) if starts else None
    groups = sorted(ctx.groups.items(), key=lambda kv: -len(kv[1]))
    cards = "".join(f"""<a class="card tile" href="washington/{slug(g)}/"><h3>{E(g)}</h3><p><strong>{len(items)}</strong> apprenticeship occupation{'s' if len(items) != 1 else ''} · starting {usd(min(i['start_wage'] for i in items))} to {usd(max(i['start_wage'] for i in items))} /hr</p></a>"""
                    for g, items in groups)
    progs = "".join(f"""<article class="card"><h3><a href="programs/{p['slug']}/">{E(p['name'])}</a></h3><p class="maker">{E(p['agency'])} · {E(p['kind'])}</p>
<p>{E(p['facts'].get('pay', p['facts'].get('what'))['summary'])}</p><p class="asof"><span class="chip {'warn' if p['status'] == 'closed' else ''}">{E(p['status_label'])}</span> · as of {tday(p['asof'])}</p></article>"""
                    for p in ctx.programs)
    desc = (f"Paid apprenticeships and paid training from official sources: {len(ctx.listings)} registered apprenticeship "
            "occupations in Washington State with starting wages, plus national programs like Job Corps and AmeriCorps. Nothing that charges job seekers.")
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": ctx.url(""), "description": desc},
          {"@context": "https://schema.org", "@type": "Dataset", "name": f"{BRAND}: paid apprenticeships and training", "description": desc,
           "url": ctx.url(""), "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
           "creator": {"@type": "Organization", "name": BRAND, "url": ctx.repo_url}, "dateModified": (ctx.wa_checked or ctx.now.isoformat())[:10],
           "isBasedOn": [d["page"] for d in ctx.wa.get("datasets", {}).values()],
           "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": ctx.url("data/opportunities.json")}]}]
    body = f"""<section class="hero">
<h1>Get paid while you learn a trade</h1>
<p class="lede">Registered apprenticeships and paid training programs, taken only from official government sources and linked to them. Laid off, skipping college, or changing careers: these are paths that pay you, not the other way round.</p>
<p class="stats"><strong>{len(ctx.listings)}</strong> occupations in active registered apprenticeship programs in Washington State{', median starting wage ' + usd(med) + ' an hour' if med else ''} · <strong>{len(ctx.programs)}</strong> national programs. Checked daily against the source.</p>
<p><a class="button" href="washington/">Search Washington apprenticeships</a> <button type="button" class="share" data-share>Share</button></p>
</section>
<section class="section"><h2>Washington State apprenticeships by field</h2>
<p>From the state's register of active registered apprenticeship programs. Registered apprentices are paid while they learn (<a href="programs/registered-apprenticeship/">see the federal program page</a>); each listing shows its registered starting wage. A listing means the program is registered and active, not that it is hiring today: ask the program about openings.</p>
<div class="cards">{cards}</div></section>
<section class="section"><h2>National programs that pay you to learn or serve</h2>
<div class="cards">{progs}</div></section>
<section class="section"><h2>How listings are chosen</h2>
<ul><li><strong>Official sources only.</strong> State and federal registers and program pages, each linked with the date it was read.</li>
<li><strong>Paid, and never charging you.</strong> A listing needs a source that shows pay or a living allowance. Fee-based courses and "opportunities" that cost money are never listed.</li>
<li><strong>Expired listings drop off.</strong> Programs the state marks inactive disappear on the next daily update; national program pages are re-checked weekly.</li></ul>
<p><a href="about/">More about sources and what is left out</a>.</p></section>"""
    return head(ctx, f"Paid apprenticeships and paid training, from official sources | {BRAND}", desc, "", 0, "og/home.png", ld) + body + foot(ctx, 0)


def filters_html(ctx, with_group=True):
    groups = "".join(f'<option value="{slug(g)}">{E(g)} ({len(v)})</option>' for g, v in sorted(ctx.groups.items()))
    counties = sorted({c for x in ctx.listings for c in x["counties"]})
    county_opts = "".join(f'<option value="{E(c)}">{E(c)}</option>' for c in counties)
    return f"""<form class="filterbar" role="search" onsubmit="return false">
<label>Search <input type="search" id="q" placeholder="electrician, medical assistant…" autocomplete="off"></label>
{'<label>Field <select id="group"><option value="">All fields</option>' + groups + '</select></label>' if with_group else ''}
<label>County <select id="county"><option value="">Any county</option>{county_opts}</select></label>
<label>Starting wage at least <select id="minwage"><option value="0">Any</option><option value="18">$18/hr</option><option value="20">$20/hr</option><option value="25">$25/hr</option><option value="30">$30/hr</option></select></label>
<p class="small" id="shown" aria-live="polite"></p></form>"""


def page_wa(ctx):
    depth, pre = 1, "../"
    items = sorted(ctx.listings, key=lambda x: (-x["start_wage"], x["occupation"]))
    desc = (f"Search {len(items)} paid registered apprenticeship occupations in Washington State by field, county and starting wage, "
            "from the Department of Labor & Industries' official register. Updated daily.")
    body = f"""<nav class="crumbs" aria-label="Breadcrumb"><a href="{pre}">Home</a> › Washington</nav>
<h1>Paid apprenticeships in Washington State</h1>
<p class="lede">Every active registered apprenticeship occupation in the state's register that shows a starting wage. Registered apprentices are paid from day one and earn more as they progress (<a href="{pre}programs/registered-apprenticeship/">source</a>). A listing means the program is registered and active, not that it is hiring today: ask the program about openings.</p>
{filters_html(ctx)}
{table(ctx, items, pre)}
<section class="section"><h2>Source</h2><p>Washington State Department of Labor & Industries, apprenticeship datasets on data.wa.gov: {' · '.join(f'<a href="{E(d["page"])}" rel="nofollow noopener">{E(d["name"])}</a> (updated {tday(d["updated"])})' for d in ctx.wa.get("datasets", {}).values())}.</p></section>"""
    return head(ctx, f"Paid apprenticeships in Washington State: starting wages | {BRAND}", desc, "washington/", depth, "og/washington.png", []) + body + foot(ctx, depth)


def page_group(ctx, group, items):
    depth, pre = 2, "../../"
    path = f"washington/{slug(group)}/"
    items = sorted(items, key=lambda x: (-x["start_wage"], x["occupation"]))
    starts = [x["start_wage"] for x in items]
    occs = {}
    for x in items:
        occs.setdefault(x["field"], 0)
        occs[x["field"]] += 1
    top = ", ".join(f"{E(k)} ({v})" for k, v in sorted(occs.items(), key=lambda kv: -kv[1])[:6])
    desc = (f"{len(items)} paid {group.lower()} apprenticeships in Washington State, starting at {usd(min(starts))} to {usd(max(starts))} an hour, "
            "from the state's official register.")
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": f"Paid {group.lower()} apprenticeships in Washington State",
           "numberOfItems": len(items), "itemListElement": [
               {"@type": "ListItem", "position": i + 1, "item": {
                   "@type": "EducationalOccupationalProgram", "name": f"{x['occupation']} apprenticeship ({x['program']})",
                   "programType": "Registered apprenticeship", "occupationalCategory": x["soc"],
                   "provider": {"@type": "Organization", "name": x["program"]},
                   "url": ctx.url(path) + f"#l{x['id']}",
                   **({"timeToComplete": f"PT{x['term_hours']}H"} if x.get("term_hours") else {})}}
               for i, x in enumerate(items[:100])]},
          {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": ctx.url("")},
              {"@type": "ListItem", "position": 2, "name": "Washington", "item": ctx.url("washington/")},
              {"@type": "ListItem", "position": 3, "name": group, "item": ctx.url(path)}]}]
    body = f"""<nav class="crumbs" aria-label="Breadcrumb"><a href="{pre}">Home</a> › <a href="{pre}washington/">Washington</a> › {E(group)}</nav>
<h1>Paid {E(group.lower())} apprenticeships in Washington</h1>
<p class="lede">{len(items)} occupation{'s' if len(items) != 1 else ''} in active registered apprenticeship programs in the state's register, starting at {usd(min(starts))} to {usd(max(starts))} an hour (median {usd(statistics.median(starts))}). Most common: {top}.</p>
{filters_html(ctx, with_group=False)}
{table(ctx, items, pre)}
<p class="small">A listing means the program is registered and active, not that it is hiring today: ask the program about openings.</p>
<p><button type="button" class="share" data-share>Share this list</button></p>"""
    return head(ctx, f"Paid {group.lower()} apprenticeships in Washington: wages and programs | {BRAND}", desc, path, depth, "og/washington.png", ld) + body + foot(ctx, depth)


def page_program(ctx, p):
    depth, pre = 2, "../../"
    path = f"programs/{p['slug']}/"
    labels = {"pay": "What it pays", "what": "What it is", "who": "Who can apply", "apply": "How to apply", "status": "Applications"}
    sections = "".join(f'<section class="crit" id="{f["id"]}"><h2>{E(labels.get(f["id"], f["id"].title()))}</h2><p>{E(f["summary"])}</p>'
                       f'{"".join(quote_html(e) for e in f["evidence"])}</section>' for f in p["fact_list"])
    problem = f"{ctx.repo_url}/issues/new?template=problem.yml&title={urlquote('Problem: ' + p['name'])}"
    desc = f"{p['name']} ({p['agency']}): {p['facts'].get('pay', p['facts'].get('what'))['summary']} Quoted from the official page, re-checked weekly."
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": f"{p['name']}: pay, eligibility and how to apply",
           "datePublished": p["reviewed"], "dateModified": p["asof"], "mainEntityOfPage": ctx.url(path),
           "author": {"@type": "Organization", "name": BRAND, "url": ctx.url("")},
           "about": {"@type": "Organization", "name": p["agency"]}}]
    flag = ('<div class="flag" role="status"><p>Some quoted text was not found in the latest version of the official page; this page is waiting for re-review.</p></div>'
            if p["missing"] else "")
    body = f"""<nav class="crumbs" aria-label="Breadcrumb"><a href="{pre}">Home</a> › {E(p['name'])}</nav>
<h1>{E(p['name'])}</h1>
<p class="lede">{E(p['agency'])} · {E(p['kind'])}</p>
{flag}
<section class="scorebox"><p><span class="chip {'warn' if p['status'] == 'closed' else ''}">{E(p['status_label'])}</span></p>
<p class="asof">As of {tday(p['asof'])}; quotes re-checked weekly against the official page.</p>
<p><a class="button" href="{E(p['link'])}" rel="noopener">{E(p['link_label'])}</a> <button type="button" class="share" data-share>Share</button></p></section>
{sections}
<section class="section corr"><h2>Something wrong?</h2><p>Every statement here should match the official page it quotes. <a class="correction" href="{E(problem)}" rel="noopener">Report a problem</a>.</p></section>"""
    return head(ctx, f"{p['name']}: pay, eligibility and how to apply | {BRAND}", desc, path, depth, "og/home.png", ld) + body + foot(ctx, depth)


def page_about(ctx):
    depth, pre = 1, "../"
    support = (f'<p><a href="{E(ctx.support_url)}" rel="noopener">{E(ctx.support_label)}</a>. Support never comes from job seekers and never buys a listing.</p>'
               if ctx.support_url else "<p>Free to use, no advertising, no sponsored listings.</p>")
    body = f"""<h1>About</h1>
<p class="lede">{BRAND} is an open, automated directory of training that pays you, built only from official sources.</p>
<section class="section"><h2>Sources</h2><ul>
<li><strong>Washington State registered apprenticeships:</strong> the Department of Labor & Industries' apprenticeship datasets on data.wa.gov (programs, occupations and counties), read daily through the state's open-data API. The state updates them monthly.</li>
<li><strong>National programs:</strong> each program's own official page, quoted word for word and re-checked weekly.</li></ul></section>
<section class="section"><h2>What is left out, and why</h2><ul>
<li>Programs and occupations the state marks cancelled or inactive, and occupations without a registered starting wage.</li>
<li>Pre-apprenticeship (preparatory) programs, because the data does not show that they pay.</li>
<li>Contact names, e-mail addresses, phone numbers and street addresses: they are in the state's data, but this site publishes no personal data. Contact the program through its own site or the official record.</li>
<li>Anything that charges job seekers, and any "money-making opportunity" without an official source.</li>
<li>Individual job postings on apprenticeship.gov: that site asks automated readers not to collect them. Its search is linked instead.</li></ul></section>
<section class="section"><h2>Independence</h2><p>Not affiliated with any program or agency listed, and no listing is paid for. The code and data are public at <a href="{ctx.repo_url}" rel="noopener">{E(ctx.repo)}</a>.</p></section>
<section class="section"><h2>Problems and corrections</h2><p><a href="{ctx.repo_url}/issues/new?template=problem.yml" rel="noopener">Report a problem</a> as a public GitHub issue. Washington listings come straight from the state's register; errors there are corrected at the source.</p></section>
<section class="section"><h2>This site's own privacy</h2><p>{'Page counts are collected without cookies by GoatCounter.' if ctx.goatcounter else 'This site sets no cookies and runs no tracking or analytics.'} It is hosted on GitHub Pages, which keeps standard server logs.</p></section>
<section class="section"><h2>Funding</h2>{support}</section>"""
    return head(ctx, f"About and sources | {BRAND}", "Where Alternative Paths' listings come from, what it leaves out and why, and how to report a problem.", "about/", depth, "og/home.png", []) + body + foot(ctx, depth)


def page_404(ctx):
    h = head(ctx, f"Not found | {BRAND}", "Page not found.", "404.html", 0, "og/home.png", [], noindex=True)
    for a, b in (('href="assets/', 'href="' + ctx.url("assets/")), ('href="favicon.svg"', 'href="' + ctx.url("favicon.svg") + '"'),
                 ('href="./"', 'href="' + ctx.url("") + '"'), ('href="washington/"', 'href="' + ctx.url("washington/") + '"'),
                 ('href="about/"', 'href="' + ctx.url("about/") + '"')):
        h = h.replace(a, b)
    f = foot(ctx, 0)
    for a, b in (('src="assets/', 'src="' + ctx.url("assets/")), ('href="feed.xml"', 'href="' + ctx.url("feed.xml") + '"'),
                 ('href="data/', 'href="' + ctx.url("data/"))):
        f = f.replace(a, b)
    return h + f'<h1>Page not found</h1><p><a href="{E(ctx.url(""))}">Go to the home page</a>.</p>' + f


def feed_xml(ctx):
    items = []
    by_id = {x["id"]: x for x in ctx.listings}
    for c in ctx.wa_changes:
        if c.get("added"):
            names = "; ".join(f"{a['occupation']} ({a['program']})" for a in c["added"][:30])
            items.append((c["date"], f"wa-added-{c['date']}-{len(c['added'])}", f"{len(c['added'])} new paid apprenticeship occupation(s) in Washington",
                          "washington/", f"<p>Newly registered in the state's data updated {E(c['date'])}: {E(names)}.</p>"))
        if c.get("removed"):
            names = "; ".join(f"{a['occupation']} ({a['program']})" for a in c["removed"][:30])
            items.append((c["date"], f"wa-removed-{c['date']}-{len(c['removed'])}", f"{len(c['removed'])} Washington apprenticeship occupation(s) no longer active",
                          "washington/", f"<p>No longer active in the state's data updated {E(c['date'])}: {E(names)}.</p>"))
    for p in ctx.programs:
        items.append((p["reviewed"], f"program-{p['slug']}", f"Listed: {p['name']}", f"programs/{p['slug']}/", f"<p>{E(p['agency'])}. {E(p['status_label'])}.</p>"))
    items.sort(key=lambda x: (x[0], x[1]), reverse=True)
    out = "".join(f"<item><title>{E(t)}</title><link>{E(ctx.url(link))}</link><guid isPermaLink=\"false\">{E(g)}</guid>"
                  f"<pubDate>{format_datetime(dt.datetime.fromisoformat(d[:10]).replace(hour=12, tzinfo=dt.timezone.utc))}</pubDate>"
                  f"<description>{E(b)}</description></item>" for d, g, t, link, b in items[:100])
    del by_id
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
<title>{BRAND}: new programs and changes</title><link>{E(ctx.url(''))}</link>
<description>Newly registered and expired paid apprenticeship occupations from official registers, and national paid training programs.</description>
<language>en</language><lastBuildDate>{format_datetime(ctx.now)}</lastBuildDate>
<atom:link href="{E(ctx.url('feed.xml'))}" rel="self" type="application/rss+xml"/>
{out}
</channel></rss>
"""


def open_data(ctx):
    return {"name": BRAND, "url": ctx.url(""), "license": "CC BY 4.0 (this compilation); source data from Washington State L&I and program pages",
            "built": ctx.now.strftime("%Y-%m-%dT%H:%M:%SZ"), "washington": {"checked": ctx.wa_checked or None, "source_updated": ctx.wa_updated or None,
            "datasets": ctx.wa.get("datasets", {}), "listings": [{k: v for k, v in x.items() if k not in ("group_slug",)} for x in ctx.listings]},
            "apps": [{"slug": p["slug"], "name": p["name"], "agency": p["agency"], "kind": p["kind"], "status": p["status"],
                      "link": p["link"], "as_of": p["asof"], "url": ctx.url(f"programs/{p['slug']}/"),
                      "facts": {f["id"]: f["summary"] for f in p["fact_list"]}} for p in ctx.programs]}


def write(out, rel, text):
    path = os.path.join(out, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def build(out, *, data=S.DATA, site_url="", repo="", now=None, env=None):
    env = dict(os.environ if env is None else env)
    site_url = (site_url or env.get("SITE_URL") or DEFAULT_SITE_URL).rstrip("/")
    repo = repo or env.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    now = now or dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    ctx = Ctx(data, site_url, repo, now, env)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    static = os.path.join(ROOT, "site")
    for name in os.listdir(static):
        src = os.path.join(static, name)
        if name == "indexnow-key.txt":
            with open(src, encoding="utf-8") as f:
                key = f.read().strip()
            write(out, f"{key}.txt", key + "\n")
        elif os.path.isdir(src):
            shutil.copytree(src, os.path.join(out, name))
        elif not name.startswith(".") and name != "og-default.png":
            shutil.copy2(src, os.path.join(out, name))
    day = (ctx.wa_updated or now.isoformat())[:10]
    pages = [("", day), ("washington/", day), ("about/", "2026-11-22")]
    write(out, "index.html", page_home(ctx))
    write(out, "washington/index.html", page_wa(ctx))
    for g, items in sorted(ctx.groups.items()):
        write(out, f"washington/{slug(g)}/index.html", page_group(ctx, g, items))
        pages.append((f"washington/{slug(g)}/", day))
    for p in ctx.programs:
        write(out, f"programs/{p['slug']}/index.html", page_program(ctx, p))
        pages.append((f"programs/{p['slug']}/", p["asof"]))
    write(out, "about/index.html", page_about(ctx))
    write(out, "404.html", page_404(ctx))
    write(out, "feed.xml", feed_xml(ctx))
    write(out, "data/opportunities.json", json.dumps(open_data(ctx), ensure_ascii=False, indent=1) + "\n")
    og_default = os.path.join(static, "og-default.png")
    os.makedirs(os.path.join(out, "og"), exist_ok=True)
    for name in ("home", "washington"):
        if os.path.exists(og_default):
            shutil.copy2(og_default, os.path.join(out, "og", f"{name}.png"))
    write(out, "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{E(ctx.url(p))}</loc><lastmod>{m}</lastmod></url>" for p, m in pages) + "</urlset>\n")
    write(out, "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {ctx.url('sitemap.xml')}\n")
    write(out, "urls.txt", "\n".join(ctx.url(p) for p, _ in pages) + "\n")
    write(out, ".nojekyll", "")
    return ctx


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--data", default=S.DATA)
    args = ap.parse_args(argv)
    ctx = build(args.out, data=args.data)
    print(f"built {len(ctx.listings)} Washington listings in {len(ctx.groups)} fields and {len(ctx.programs)} programs into {args.out} for {ctx.site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
