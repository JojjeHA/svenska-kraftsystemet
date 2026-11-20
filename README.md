# Svenska kraftsystemet – Home Assistant

Unofficial Home Assistant integration for monitoring Sweden's electricity system using data from the **ENTSO-E Transparency Platform**.

The integration provides information about Swedish electricity generation, consumption, and cross-border electricity flows directly in Home Assistant.

**Current version: 0.1.1 (Experimental)**

> **Disclaimer:** This is an independent, community-developed integration. It is not affiliated with, maintained by, or endorsed by Svenska kraftnät, ENTSO-E, or Home Assistant.
>
> The data may be delayed, incomplete, or revised. Do not use this integration for safety-critical or operational decisions.

## Features

- Electricity generation by production type across Sweden's four bidding zones (SE1–SE4)
- Electricity consumption for SE1, SE2, SE3, SE4, and Sweden as a whole
- Physical electricity flows between Sweden and neighboring countries
- Total electricity import, export, and net export
- Optional sensors for individual cross-border connections
- Optional production sensors for less commonly reported generation types
- Automatic data updates
- Correct handling of ENTSO-E A01 and A03 time series
- Missing data reported as unavailable rather than incorrectly assumed to be zero
- Native Home Assistant sensor entities with measurement units in MW
- Configuration through the Home Assistant user interface
- Support for installation through HACS Marketplace as a custom repository

## Electricity generation

The integration retrieves reported electricity generation using the ENTSO-E Transparency Platform API.

Generation data is collected from all four Swedish bidding zones and combined by production type.

### Enabled by default

| Production type | ENTSO-E code |
|---|---|
| Nuclear | B14 |
| Reservoir hydro | B12 |
| Onshore wind | B19 |
| Solar | B16 |
| Natural gas | B04 |
| Other | B20 |

### Disabled by default

The following sensors are available but disabled by default to keep the integration's entity list manageable.

| Production type | ENTSO-E code |
|---|---|
| Biomass | B01 |
| Lignite | B02 |
| Coal-derived gas | B03 |
| Hard coal | B05 |
| Oil | B06 |
| Oil shale | B07 |
| Peat | B08 |
| Geothermal | B09 |
| Pumped storage | B10 |
| Run-of-river hydro | B11 |
| Marine | B13 |
| Other renewable | B15 |
| Waste | B17 |
| Offshore wind | B18 |

Users can manually enable any of these entities in Home Assistant.

**Important:** A production type that does not currently provide data may become available in the future. A missing production value does not necessarily mean zero generation.

Generation values represent the sum of reported data for a specific production category. They are not guaranteed to represent complete national generation statistics.

## Electricity consumption

The integration provides actual electricity consumption in MW for:

- SE1 – Luleå
- SE2 – Sundsvall
- SE3 – Stockholm
- SE4 – Malmö
- Sweden – National total

All consumption sensors are enabled by default.

The national total is retrieved independently from ENTSO-E rather than calculated exclusively from the four regional sensors.

## Electricity import and export

The integration monitors physical cross-border electricity flows between Sweden and neighboring countries.

Supported neighboring countries include:

- Norway
- Finland
- Denmark
- Germany
- Poland
- Lithuania

### Enabled by default

| Sensor | Description |
|---|---|
| Export Sweden | Total physical electricity export in MW |
| Import Sweden | Total physical electricity import in MW |
| Net export Sweden | Export minus import in MW |

A positive net export value indicates that Sweden exports more electricity than it imports.

A negative value indicates net import.

### Disabled by default

Individual connections are available as optional sensors, including:

- SE1 – FI
- SE1 – NO4
- SE2 – NO3
- SE2 – NO4
- SE3 – NO1
- SE3 – FI
- SE3 – DK1
- SE4 – DK2
- SE4 – DE
- SE4 – PL
- SE4 – LT

Each connection provides three optional sensors:

- Export
- Import
- Net export

These individual sensors are disabled by default.

The national import/export totals remain enabled.

National totals are only calculated when complete data is available for all configured cross-border connections. Missing data is never silently treated as zero.

Internal electricity transfers between SE1, SE2, SE3, and SE4 are not included in the national import/export totals.

## Managing optional sensors

Home Assistant allows users to enable or disable individual entities.

To enable an optional sensor:

1. Open **Settings → Devices & services**.
2. Select **Svenska kraftsystemet**.
3. Open the device **Sveriges elsystem**.
4. Open the entity list and display disabled entities.
5. Select the desired entity.
6. Enable the entity.

Entities disabled by default remain available for users who want more detailed monitoring.

**Note:** Default entity settings apply to newly registered entities. Updating an existing installation does not automatically change the enabled/disabled status of previously registered entities.

## Requirements

- Home Assistant 2026.11.0 or newer
- Internet connection
- ENTSO-E Transparency Platform account
- ENTSO-E REST API security token
- HACS Marketplace for installation through a custom repository

## Obtaining an ENTSO-E API token

1. Register an account at [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).
2. Verify your email address.
3. Request REST API access according to ENTSO-E's current instructions.
4. Once access is granted, generate a security token under your account settings.
5. Store your token securely.

Never publish your API token in GitHub, Home Assistant screenshots, logs, or issue reports.

## Installation

### HACS Marketplace – Custom repository

1. Open **HACS Marketplace** in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Enter the repository URL:

   `https://github.com/JojjeHA/svenska-kraftsystemet`

4. Select **Integration** as the repository type.
5. Add the repository.
6. Find **Svenska kraftsystemet** in Marketplace.
7. Download the integration.
8. Restart Home Assistant.

### Configure the integration

1. Go to **Settings → Devices & services**.
2. Click **Add integration**.
3. Search for **Svenska kraftsystemet**.
4. Enter your ENTSO-E API token.
5. Complete the configuration.

The integration creates a device named **Sveriges elsystem** containing the available sensors.

The initial setup may take some time because the integration retrieves multiple datasets from ENTSO-E.

### Manual installation

Alternatively, copy the directory:

`custom_components/svenska_kraftsystemet`

into your Home Assistant configuration directory:

`/config/custom_components/svenska_kraftsystemet`

Restart Home Assistant and configure the integration through **Settings → Devices & services**.

## Data sources and updates

All electricity generation, consumption, and cross-border flow data is retrieved from the ENTSO-E Transparency Platform REST API.

| Data | Document type |
|---|---|
| Actual generation per production type | A75 |
| Actual electricity consumption | A65 |
| Physical cross-border flows | A11 |

The integration currently refreshes its data every **60 minutes**.

Each refresh performs up to 31 API requests:

- 4 generation requests
- 5 consumption requests
- 22 cross-border flow requests

To account for publication delays, the integration currently selects the most recent full-hour timestamp at least three hours before the current time.

**This integration does not provide real-time data.**

Individual datasets may be updated at different intervals. Some readings may be delayed or unavailable.

The integration supports both:

- `A01` – Sequential fixed-interval time series
- `A03` – Variable-sized blocks, where a reported value can remain valid over multiple intervals

Sensors include a `data_time_utc` attribute identifying the selected reporting timestamp.

## Data accuracy and limitations

The following limitations should be considered:

- Generation data is based on reported ENTSO-E production categories.
- The absence of a production category does not automatically indicate zero production.
- Generation categories may differ in reporting frequency and completeness.
- Some production categories may contain data from multiple generation technologies or facilities.
- Electricity consumption and cross-border flows may be reported using different measurement and reporting methodologies.
- National physical import/export totals are dependent on complete reporting from all configured border connections.
- Individual ENTSO-E datasets may be delayed, revised, or temporarily unavailable.
- A valid value of 0 MW is different from missing data.
- Pumped-storage generation and consumption require additional validation.

### Reported electricity generation – important limitations

The integration calculates total reported electricity generation by summing the available generation categories across Sweden's four bidding zones (SE1–SE4).

**This is not an independently verified total of all electricity generation in Sweden.**

ENTSO-E may omit production categories or report data with delays. Missing categories are not automatically interpreted as zero generation. Consequently, the calculated total may underestimate actual Swedish electricity generation.

Generation shares (%) represent each production group's share of the **total reported generation included in the calculation**, not its share of national electricity consumption or electricity supply.

Electricity imports and exports are not included in the production shares.

The calculated value *Reported generation minus consumption* is an indicative difference between two reported datasets and must not be interpreted as a verified national electricity balance or physical net export.

## Integration icon

The integration includes its own branding files:

- `brand/icon.png` – 256 × 256 pixels
- `brand/icon@2x.png` – 512 × 512 pixels

These files are included in the integration directory for Home Assistant's custom integration branding support.

## Planned features

Future improvements may include:

### Grid frequency

A frequency sensor showing the frequency of the Nordic synchronous electricity system in Hz.

A suitable and reliable data source must be identified and verified before implementation.

### Individual nuclear reactor monitoring

Additional information about Swedish nuclear reactor availability, operational status, and production.

This would require a data source providing information at individual generating-unit level rather than only aggregated nuclear production.

### Verified total electricity generation

A national electricity generation sensor with additional validation of reporting completeness and consistency.

### Improved localization

Improved Swedish and English sensor names and descriptions, while preserving existing entity identifiers wherever possible.

### Additional improvements

- More flexible update settings
- Improved diagnostics and reporting completeness information
- Additional data quality indicators
- Further optimization of API requests
- Optional monitoring of additional electricity system statistics

These features are planned or under consideration and are not included in the current release.

## Version history

### v0.1.1

- Added default-disabled production sensors for less commonly reported generation types
- Added default-disabled sensors for individual cross-border connections
- Kept national import, export, and net export sensors enabled by default
- Preserved existing entity unique identifiers
- Added local integration branding files
- Updated documentation

### v0.1.0

- Initial experimental release
- ENTSO-E API token configuration
- Swedish electricity generation sensors
- Electricity consumption sensors
- Physical cross-border electricity flow sensors
- National import, export, and net export
- Support for A01 and A03 time series
- Automatic hourly updates

## Issues and feedback

Bug reports, feature requests, and suggestions are welcome.

Please use the [GitHub Issues page](https://github.com/JojjeHA/svenska-kraftsystemet/issues).

When reporting an issue, include:

- Home Assistant version
- Integration version
- Description of the issue
- Relevant error messages with sensitive information removed

**Never include your ENTSO-E API token.**

## Credits

Electricity system data is provided by the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).

This project is an independent Home Assistant custom integration.

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

ENTSO-E data usage remains subject to the applicable ENTSO-E terms and conditions.
