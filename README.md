# Alternative Paths

**Paid apprenticeships and paid training, only from official sources. Nothing that charges job seekers.**

Live: https://theguysaccount.github.io/alternative-paths-opportunities/

- **Washington State registered apprenticeships:** every occupation in an active registered apprenticeship program that shows a registered starting wage, from the Department of Labor & Industries' datasets on data.wa.gov, refreshed daily (the state updates monthly). Searchable by field, county and starting wage, with one page per occupational field. Each listing links to the state's own record. Programs the state marks inactive drop off automatically; contact names, e-mails, phones and addresses are never published.
- **National programs that pay you to learn or serve:** Registered Apprenticeship, Job Corps, AmeriCorps State and National, U.S. Digital Corps, and help for laid-off workers (Rapid Response and American Job Centers). Every statement quotes the program's official page and is re-checked word for word weekly.

A listing means a program is registered and active, not that it is hiring today. Not affiliated with any program listed; no listing is paid for.

## Run, test, build

Python 3.9+ with no dependencies; Node 22+ and Google Chrome for the browser checks.

```bash
python3 -m unittest discover -s tests        # register, data, quote-check and build tests
python3 -m pipeline.wa                       # refresh Washington listings from data.wa.gov
python3 -m pipeline.check                    # re-read national program pages, verify every quote
python3 -m pipeline.build                    # build the site into dist/
python3 -m pipeline.og dist                  # share cards (needs Chrome)
node scripts/e2e.mjs                         # every page in headless Chrome, desktop and phone
python3 scripts/check_live.py https://theguysaccount.github.io/alternative-paths-opportunities
```

## Layout

| Path | What |
|---|---|
| `data/wa/listings.json` | Washington listings as published (no personal data), with the source datasets' update dates |
| `data/wa/changes.json` | Listings added and dropped at each state update |
| `data/programs/<program>.json` | National program pages: facts with quoted evidence |
| `data/state.json`, `data/sigs/`, `data/changes.json` | Written by the weekly program-page check |
| `pipeline/` | `wa.py` (state register), `fetch.py` and `check.py` (polite reader, quote checker), `build.py`, `og.py` |

Code MIT; this compilation CC BY 4.0.
