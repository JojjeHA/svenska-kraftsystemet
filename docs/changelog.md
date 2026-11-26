# Version history

Release history for Svenska kraftsystemet.

### v0.1.11 – Stable release

- Consolidates reliability improvements from v0.1.6–v0.1.10.
- Same tested Python code as v0.1.10.
- Documentation updates.

### v0.1.10 (pre-release)

- Retry transient HTTP 599 errors in addition to existing retryable statuses
- Increase per-request timeout from 20 to 30 seconds
- Lower the log level for normal reuse of an unchanged complete timestamp from WARNING to DEBUG

### v0.1.9 (pre-release)

- Validate main national generation groups before publishing national production totals and percentages
- Avoid misleading 100% generation shares when major reported categories are missing
- Retain the most recent complete snapshot for less than 60 minutes during incomplete refreshes
- Prevent repeated old reporting timestamps from extending the fallback lifetime

### v0.1.8 (pre-release)

- Introduce an in-memory fallback snapshot and cache-related sensor attributes

### v0.1.7 (pre-release)

- Add more detailed logging of failed ENTSO-E requests and incomplete production snapshots

### v0.1.6 (pre-release)

- Add selective retry logic for transient API failures

### v0.1.5

- First stable release with the new calculated production sensors and 15-minute updates
- Updated documentation, data-quality disclaimers, and a complete optional Bar Card dashboard example
- Retained the tested v0.1.4 data-collection and fallback behavior

### v0.1.4 (pre-release)

- Restored partial-data availability when complete production/consumption snapshots cannot be obtained
- Improved diagnostics without logging API tokens
- Retained 15-minute polling and automatic selection of a recent reporting timestamp

### v0.1.3 (pre-release)

- Added four calculated generation groups and their percentage shares
- Added sum of reported generation and reported generation minus consumption
- Introduced 15-minute polling and recent common-timestamp selection
- Introduced a stricter common-timestamp check that was revised in v0.1.4

### v0.1.2

- Moved initial data collection into a background task to avoid blocking Home Assistant startup
- Added bounded parallel API requests and shorter individual request timeouts

### v0.1.1

- Disabled less commonly reported generation categories and individual border connections by default
- Preserved existing entity unique IDs and manual enabled/disabled preferences
- Added local integration branding files and expanded documentation

### v0.1.0

- Initial experimental release with ENTSO-E API token configuration
- Generation, consumption, physical cross-border flows, and national flow totals
- Support for A01/A03 data and automatic updates
