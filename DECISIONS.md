# Decisions

1. **A neutral directory, not a funnel into Persist programs.** The evaluator flagged trust as the risk. v1 lists no Persist programs at all; if one is ever added it must meet the same sourcing rule and be labelled as Jack's.
2. **Official sources only, and "paid" must be sourced.** Washington listings need a registered starting wage; national programs need a quoted statement of pay or a living allowance (Rapid Response is listed under "help after a layoff", not as paid).
3. **Washington first.** It is the only state found that publishes its registered apprenticeship register, with wages and counties, through an open API (data.wa.gov, refreshed monthly by the state). apprenticeship.gov's job listings are excluded because its robots.txt asks automated readers not to collect them; its search is linked instead. The DOL dashboards are Tableau embeds with no download.
4. **No personal data.** The state's data includes contact names, e-mails, phones and addresses; none is kept or published. People reach programs through their own sites or the state's record.
5. **Honest wording.** A listing means a program is registered and active, not that it is hiring. Pages say so.
6. **Grouping by the federal occupational classification** (SOC major groups, 20 pages) rather than 150 near-duplicate occupation names, so every page is substantial; full search and county filters are on the main directory page.
7. **Expiry is automatic.** Inactive programs drop off at the next refresh and are logged; national pages are re-checked weekly and flag changes.
8. **Same site toolkit as the sibling sites** (quote checker, browser checks, keep-alive, IndexNow, one `SITE_URL` setting).

## Open questions for Jack (none blocks the site)

- A neutral hub or the front door to Persist programs? Built neutral (see 1).
- Does Jack own alternativepaths.com? Not in the portfolio audit; the domain rollout session owns domains.
