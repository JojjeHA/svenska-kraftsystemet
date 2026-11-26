# Data sources, reliability and limitations

How reported ENTSO-E data is selected, validated, cached and interpreted.

## Data sources and updates

All generation, consumption, and cross-border flow data comes from the ENTSO-E Transparency Platform REST API.

| Dataset | Document type |
|---|---|
| Actual generation per production type | A75 |
| Actual consumption | A65 |
| Physical cross-border flows | A11 |

The integration requests updates every **15 minutes**. Each refresh issues up to **31 API requests** (4 generation, 5 consumption, and 22 cross-border-flow requests), with up to four requests running concurrently.

To account for ENTSO-E publication delays, the integration initially considers a reporting timestamp about **45 minutes** before the current time, rounded down to a quarter-hour. It searches backward in 15-minute steps over a window of up to **six hours**, using the datasets retrieved during that refresh rather than repeating the API requests for each candidate timestamp.

The integration prefers the newest reporting timestamp with generation datasets from all four Swedish bidding zones, all four required national generation groups, and Sweden-wide consumption. When that condition cannot be met, it first tries to reuse a previously collected complete snapshot. If no usable cached snapshot exists, partial same-timestamp data may be returned for independently available sensors, but derived national generation totals and shares remain unavailable unless their completeness check passes.

### Retries and fallback data

- Temporary HTTP failures (including `408`, `425`, `429`, `500`, `502`, `503`, `504` and `599`) and connection/time-out errors are retried. Generation requests have up to **3 attempts**, and other dataset requests have up to **2 attempts**, with a short increasing delay between attempts.
- Each individual API request has a **30-second timeout**. The client limits simultaneous requests to **4**; retries can increase the total number of requests beyond the initial 31.
- The last **complete** snapshot is cached **in memory**. If a later refresh is incomplete or the reporting timestamp has not advanced, the integration can reuse that snapshot for **less than 60 minutes** after its first successful collection. Re-reading the same reporting timestamp does **not** reset the timer.
- The snapshot is kept together: cached generation, consumption and cross-border-flow data are not mixed with measurements from another reporting timestamp. A complete generation snapshot can still have unavailable optional border-flow or regional-consumption readings.
- Once the fallback expires, old data is no longer published as fresh. Depending on what ENTSO-E returns, individual sensors may become unavailable until a newer complete snapshot is received. The fallback starts empty after a Home Assistant or integration restart.
- Sensor attributes include `data_time_utc` (the reported measurement timestamp), `using_cached_data`, `cache_age_minutes` and `last_successful_update_utc` (the time the last new complete reporting snapshot was accepted).
- Reusing an unchanged but complete reporting timestamp is logged at **DEBUG** rather than **WARNING**. Actual incomplete/failed refreshes can still produce warnings.

**This is reported data, not a real-time feed.** Values may remain unchanged across several refreshes, and ENTSO-E can publish or revise readings later.

The parser supports `A01` fixed-interval series and `A03` variable-length blocks. Sensors expose a `data_time_utc` attribute showing the selected UTC reporting timestamp. This is the timestamp chosen by the integration, not a guarantee that every upstream measurement has identical publication latency or methodology.

## Data accuracy and limitations

- ENTSO-E production categories may be delayed, incomplete, or absent.
- Validation requires nationally reported nuclear, hydro, wind and `B20` other-generation categories; this is intentionally conservative and may withhold totals even when the underlying report is otherwise useful.
- Complete-looking datasets can still omit individual production technologies; the validation is not an independent verification of national completeness.
- Cached values may be up to 60 minutes old by retrieval age and their reported measurement timestamp may be older still.
- A missing category does **not** establish zero production; a reported 0 MW is distinct from missing data.
- Generation categories may include multiple technologies or production facilities.
- Some datasets can be available while other datasets are unavailable at the same timestamp.
- A grouped reported-generation total depends on the reported categories and is not a verified country-wide generation total.
- Consumption and physical cross-border flows may use different reporting definitions or methodologies.
- Border-flow totals require readings from every configured international connection.
- Pumped-storage generation and consumption require additional validation.

### Reported electricity generation – important limitations

The integration calculates total reported electricity generation by summing the available generation categories across Sweden's four bidding zones (SE1–SE4).

**This is not an independently verified total of all electricity generation in Sweden.**

ENTSO-E may omit production categories or report data with delays. Missing categories are not automatically interpreted as zero generation. Consequently, the calculated total may underestimate actual Swedish electricity generation.

Generation shares (%) represent each production group's share of the **total reported generation included in the calculation**, not its share of national electricity consumption or electricity supply.

Electricity imports and exports are not included in the production shares.

The calculated value *Reported generation minus consumption* is an indicative difference between two reported datasets and must not be interpreted as a verified national electricity balance or physical net export.

## Planned features

Possible future improvements include grid frequency for the Nordic synchronous area, individual nuclear-reactor availability and production data, independently verified national generation totals, improved localization, configurable update settings, diagnostics and reporting-completeness indicators, and further API optimizations.

These features are planned or under consideration, not part of this release.
