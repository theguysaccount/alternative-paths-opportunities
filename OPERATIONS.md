# Operations

Alternative Paths runs itself on GitHub: Pages for hosting, Actions for every recurring job.

- **Live:** https://theguysaccount.github.io/alternative-paths-opportunities/
- **Repo:** https://github.com/theguysaccount/alternative-paths-opportunities

## Automated jobs

| Job | Workflow | When (UTC) | What it does | How it fails safely |
|---|---|---|---|---|
| Refresh listings | `refresh.yml` | 06:29 and 18:29 daily | Reads Washington's three apprenticeship datasets through the data.wa.gov API (1.5 s between requests, identified reader), rebuilds listings (active programs, active occupations, with a starting wage, no pre-apprenticeship, no personal data), logs listings added and dropped, runs the tests, commits, starts `deploy.yml` | Any read error or a result under 100 listings keeps the last good data and records the error; failing tests stop the commit. Same data, same files: re-runs are harmless. |
| Program page check | `check.yml` | Wednesdays and Saturdays 09:13 | Re-reads each national program's official page (robots.txt respected; Internet Archive copy under 180 days old when a site refuses scripts, labelled), verifies every quote word for word, records changed text, commits, redeploys, lists changes in one `needs-review` issue | An unreadable page keeps its last good read for 14 days (a page read only from the archive: while its copy is under 180 days old), then the program page says it could not be read; a missing quote is flagged on the page. |
| Deploy | `deploy.yml` | every push to `main` (not docs-only), after each refresh or check, by hand | Tests, build, share cards, every page in headless Chrome at desktop and phone widths, deploy, live browser check, IndexNow | Any failure stops before the deploy; the last good site stays live. |
| Self-test | `selftest.yml` | Fridays 15:53 | Tests, live browser check, every sitemap URL, feed, open data; Washington data older than 3 days starts a refresh, older than 10 days fails | One `ops-alert` issue; GitHub emails the owner. |
| Keep-alive | in `refresh.yml`, `check.yml`, `selftest.yml` | every run | Re-enables scheduled workflows; empty commit after 45 quiet days | |

Temporary lines: `refresh.yml` and `selftest.yml` each carry one cron line marked `TEMPORARY` that fires only on 22-23 November; delete them once a scheduled run has passed.

## What to watch

- **`needs-review` issues**: a national program's official page changed. Re-read it (`python3 -m pipeline.grab --refresh --find "<word>" <url>`), update `data/programs/<program>.json`, change `status`/`status_label` if applications opened or closed, run the tests, push.
- **`problem` issues**: check against the official source. Washington listings are corrected at the source (the state's register); a listed program that charges job seekers should be reported to the state and excluded here.
- **AmeriCorps** (americorps.gov refuses scripts and hides its robots.txt from them) is read from the Internet Archive copy of 30 Jun 2026, shown with that date. A newer Archive copy is picked up automatically. If none appears, the copy passes 180 days on 27 Dec 2026 and the page will say it could not be read: re-check the official page by hand then and update `data/programs/americorps.json`.
- **The refresh run summary** says how many listings were added or dropped when the state publishes its monthly update.

## Keys Jack can turn later

### 1. Custom domain (the domain rollout session's job)

One setting, the repository variable `SITE_URL`, moves canonical URLs, sitemap, feed, cards and IndexNow; internal links are relative.

1. DNS. Subdomain: `CNAME <name> → theguysaccount.github.io`. Apex: `A @ → 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153`, `AAAA @ → 2606:50c0:8000::153, 2606:50c0:8001::153, 2606:50c0:8002::153, 2606:50c0:8003::153`, `CNAME www → theguysaccount.github.io`.
2. `gh api -X PUT repos/theguysaccount/alternative-paths-opportunities/pages -f cname=<domain>`, wait for the certificate, then `gh api -X PUT repos/theguysaccount/alternative-paths-opportunities/pages -F https_enforced=true`.
3. `gh variable set SITE_URL -R theguysaccount/alternative-paths-opportunities --body "https://<domain>"`.
4. `gh workflow run deploy.yml -R theguysaccount/alternative-paths-opportunities`.

### 2. Money

Never charge job seekers, and never sell listings. The slot is a "Support this project" link, hidden until `SUPPORT_URL` (and optionally `SUPPORT_LABEL`) is set. A display-ad account is the brief's optional key; it would need hosting other than GitHub Pages (non-commercial) and an ad account in Jack's name.

### 3. Weekly newsletter

The idea included a weekly e-mail of new openings. It needs an e-mail service account and a sender identity (a key for Jack). Until then the RSS feed (`/feed.xml`) carries the same updates and works with feed-to-email services.

### 4. More states and programs (routine)

Only Washington publishes its registered apprenticeship register with wages through an open API that allows automated reading; apprenticeship.gov's job listings ask automated readers not to collect them. A monthly Claude Code routine on this repository can extend coverage:

> In theguysaccount/alternative-paths-opportunities: look for official state or federal open-data sources (APIs or downloadable files whose terms and robots.txt allow automated use) listing registered apprenticeships or paid training with wages, and add a reader for one, following `pipeline/wa.py` (no personal data, link every listing to its source, keep the last good data on failure, tests). Then work through open `needs-review` and `problem` issues. Never add anything that charges job seekers or that you can't source. Run every test and push only if all pass. Never post anywhere else.

### 5. Analytics and Search Console

Off by default. With `GOATCOUNTER_URL` set the site counts `filter`, `share`, `source-click` and `apply-click` (activation: a visitor opens a program's official record or apply page). Google Search Console needs Jack's Google account; Bing and others get IndexNow pings.
