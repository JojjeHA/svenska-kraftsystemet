# Svenska kraftsystemet – Home Assistant

Unofficial Home Assistant integration for Swedish electricity system data from the **ENTSO-E Transparency Platform**.

**Status: v0.1.0 experimental.** This is not affiliated with Svenska kraftnät or ENTSO-E. Do not use the readings for operational or safety-critical decisions.

## Features

- Reported electricity generation by production type (MW) across Sweden's SE1–SE4 bidding zones
- Actual load (MW) for SE1, SE2, SE3, SE4 and Sweden total
- Physical border flows in both directions for 11 Swedish cross-border links
- Total export, import and net export (MW), only if all 11 pairs have complete data
- Correct handling of ENTSO-E `A03` variable-size blocks and `A01` point series
- Data timestamp as entity attribute; missing values shown as **unavailable**, not 0

**Not included yet:** grid frequency and a verified nationwide total production sensor. ENTSO-E is not real-time; data is delayed. Categories absent from an area aren't assumed to be 0. Generation categories are sums of reported values, **not certified national total production**.

## Installation with Home Assistant Marketplace (2026.11+)

1. Publish all these files as a GitHub repository, keeping the `custom_components/svenska_kraftsystemet` path intact.
2. Update the GitHub URL placeholders in `manifest.json` to your actual repository URL.
3. In Home Assistant, open **Marketplace**, add your GitHub URL as a **Custom repository** of type **Integration**, and install it.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**, search for **Svenska kraftsystemet** and paste your ENTSO-E API token.

Never commit or share the token, or paste it into a GitHub issue.

## Data collection

Queries: [ENTSO-E Transparency API](https://transparency.entsoe.eu/), documentType `A75` (production), `A65` (load), `A11` (cross-border physical flow). Each refresh makes up to **31 requests** (4 production + 5 load + 22 border directions) and takes place once per hour. A fixed reading is selected at the most recent whole hour at least three hours old. It isn't a real-time sensor.

The integration parses XML `A03` step-change time series and `A01` regular point series. It never copies the API token to diagnostics or logs. Some ENTSO-E reporting can lag more than three hours: affected sensors become unavailable. Border totals are withheld unless all borders return both directions.

### Caveats

- The 11 borders were validated in a historical test on 2026-11-15; changes to ENTSO-E reporting, EIC domain codes, or link topology can affect results.
- Production categories may have reporting differences and should not be used to claim a complete Swedish production total. Pumped-storage generation/consumption requires further validation.
- Missing production types in an area cannot automatically be interpreted as zero.
- Some zero-value flows can be valid; an API error is **not** a zero.
- Refresh and lag will be tuned based on live operational testing.

## Development

Project is distributed as source code for a custom integration. See `custom_components/svenska_kraftsystemet` and basic parsing tests in `tests/`.

## Credits and license

ENTSO-E Transparency Platform is the upstream data provider. API access and data use are subject to ENTSO-E terms. Integration code is MIT licensed.
