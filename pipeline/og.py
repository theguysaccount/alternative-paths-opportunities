"""Render 1200x630 share cards (og/home.png, og/washington.png) into a built site with headless Chrome.

    python3 -m pipeline.og dist        # after pipeline.build
    python3 -m pipeline.og --default   # re-render site/og-default.png (committed fallback)
"""
from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMES = [os.environ.get("CHROME", ""), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
CSS = """*{box-sizing:border-box}html,body{margin:0;width:1200px;height:630px;overflow:hidden}
body{background:#f7f6f2;color:#1b232b;font-family:-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"DejaVu Sans",sans-serif;padding:60px 70px;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:16px;font-size:30px;font-weight:750;color:#2f6f4f}
h1{font-size:72px;line-height:1.04;letter-spacing:-1.5px;margin:36px 0 14px}
.sub{font-size:30px;color:#56626d;line-height:1.35}
.row{display:flex;gap:26px;margin-top:auto;align-items:flex-end}
.big{font-size:100px;font-weight:800;line-height:.9}.big small{font-size:34px;color:#56626d;font-weight:600}
.foot{font-size:24px;color:#56626d;margin-left:auto;text-align:right}"""
LOGO = ('<svg viewBox="0 0 32 32" width="52" height="52"><rect x="3" y="3" width="26" height="26" rx="7" fill="#2f6f4f"/>'
        '<path d="M8 23c4-1 6-5 8-9s4-6 8-6" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/><circle cx="24" cy="8" r="2.6" fill="#f4d35e"/></svg>')


def find_chrome():
    for c in CHROMES:
        if c and (os.path.exists(c) or shutil.which(c)):
            return shutil.which(c) or c
    return None


def render(chrome, body, out_png):
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "card.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>")
        try:
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1",
                            "--window-size=1200,630", f"--user-data-dir={os.path.join(d, 'profile')}", f"--screenshot={out_png}",
                            "file://" + src], check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.SubprocessError, OSError):
            return False
    return os.path.exists(out_png) and os.path.getsize(out_png) > 2000


def home():
    return (f'<div class="top">{LOGO}Alternative Paths</div><h1>Get paid while you learn a trade</h1>'
            f'<div class="sub">Registered apprenticeships and paid training, only from official sources. Nothing that charges job seekers.</div>'
            f'<div class="row"><span class="foot">Free · updated daily · open data</span></div>')


def washington(n, med):
    return (f'<div class="top">{LOGO}Alternative Paths</div><h1>Paid apprenticeships in Washington State</h1>'
            f'<div class="sub">From the state\'s official register: occupation, starting wage, length and where.</div>'
            f'<div class="row"><span class="big">{n}<small> occupations</small></span><span class="foot">median start ${med:,.2f}/hr</span></div>')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    chrome = find_chrome()
    if not chrome:
        print("og: Chrome not found; keeping the default cards")
        return 0
    if argv[:1] == ["--default"]:
        ok = render(chrome, home(), os.path.join(ROOT, "site", "og-default.png"))
        print("og-default.png", "ok" if ok else "FAILED")
        return 0 if ok else 1
    dist = argv[0] if argv else os.path.join(ROOT, "dist")
    with open(os.path.join(dist, "data", "opportunities.json"), encoding="utf-8") as f:
        data = json.load(f)
    L = data["washington"]["listings"]
    jobs = [("home", home())]
    if L:
        jobs.append(("washington", washington(len(L), statistics.median(x["start_wage"] for x in L))))
    done = 0
    for name, body in jobs:
        out = os.path.join(dist, "og", f"{name}.png")
        tmp = out + ".new.png"
        if render(chrome, body, tmp):
            os.replace(tmp, out)
            done += 1
    print(f"og: rendered {done} of {len(jobs)} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
