# Svenska kraftsystemet – Home Assistant

Unofficial Home Assistant integration for monitoring Sweden's electricity system using data from the **ENTSO-E Transparency Platform**.

The integration provides information about Swedish electricity generation, consumption, and physical cross-border electricity flows directly in Home Assistant.

**Current stable version: v0.1.5.**

> **Disclaimer:** This is an independent, community-developed integration. It is not affiliated with, maintained by, or endorsed by Svenska kraftnät, ENTSO-E, or Home Assistant.
>
> The data may be delayed, incomplete, or revised. Do not use this integration for safety-critical or operational decisions.

## Features

- Reported electricity generation by production type across Sweden's four bidding zones (SE1–SE4)
- Four automatically calculated generation groups: nuclear, hydro, wind, and other
- Calculated shares (%) of total *reported* generation, and a reported-generation sum
- Reported generation minus national consumption (indicative difference only)
- Electricity consumption for SE1, SE2, SE3, SE4, and Sweden as a whole
- Physical electricity flows between Sweden and neighboring countries
- Total electricity import, export, and net export
- Optional individual cross-border and less commonly reported production sensors
- Updates every **15 minutes** with selection of a common reporting timestamp when available
- Support for ENTSO-E A01 and A03 time series
- Missing data represented as unavailable where completeness cannot be established
- Native Home Assistant sensor entities; configuration through the user interface
- Optional Bar Card dashboard example (no templates or helpers required)

## Electricity generation

The integration retrieves reported generation from ENTSO-E for SE1–SE4 and combines values from the same selected reporting timestamp.

### Production types enabled by default

| Production type | ENTSO-E code |
|---|---|
| Nuclear | B14 |
| Reservoir hydro | B12 |
| Onshore wind | B19 |
| Solar | B16 |
| Natural gas | B04 |
| Other | B20 |

### Production types disabled by default

The following sensors are available in the entity registry but are disabled by default to keep the entity list manageable.

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

A production type may be present in Sweden without being separately reported in this dataset. **An absent production value does not establish zero production.** Users can enable optional sensors through Home Assistant's entity registry.

### Calculated production sensors

The integration automatically creates the following calculated sensor groups. No user-defined helpers or template sensors are necessary.

| Production group | ENTSO-E categories |
|---|---|
| Nuclear | B14 |
| Hydro | B11 + B12 |
| Wind | B18 + B19 |
| Other reported generation | All other reported ENTSO-E generation categories |

Each group provides its **reported production in MW** and **percentage of the sum of reported generation**. There are also sensors for **Sum of reported generation (MW)** and **Reported generation minus consumption (MW)**.

Calculated values use the available production readings at the selected timestamp. If a Swedish bidding zone's production dataset is missing or ambiguous, calculated national production totals become unavailable; an absent production category is not silently turned into a confirmed zero. The reported sum is **not an independently verified total of all Swedish generation**. See [Data accuracy and limitations](#data-accuracy-and-limitations).

## Electricity consumption

The integration provides electricity consumption in MW for SE1, SE2, SE3, SE4, and Sweden as a whole.

The Sweden-wide consumption value is retrieved independently from ENTSO-E rather than calculated by summing the four regional consumption sensors.

## Electricity import and export

The integration monitors physical cross-border electricity flows between Sweden and neighboring countries: Norway, Finland, Denmark, Germany, Poland, and Lithuania.

### Enabled by default

| Sensor | Description |
|---|---|
| Export Sweden | Sum of configured physical exports in MW |
| Import Sweden | Sum of configured physical imports in MW |
| Net export Sweden | Export minus import in MW |

Positive net export means the reported physical export total exceeds the import total; negative net export means net import.

### Disabled by default

Individual connections are available as optional sensors:

- SE1 – FI; SE1 – NO4
- SE2 – NO3; SE2 – NO4
- SE3 – NO1; SE3 – FI; SE3 – DK1
- SE4 – DK2; SE4 – DE; SE4 – PL; SE4 – LT

Each configured connection provides Export, Import, and Net export sensors.

National import/export totals are available only when data is present for all configured connections. Missing border-flow data is not silently treated as zero. Transfers within Sweden between SE1–SE4 are **not** included in the international import/export totals.

**Important:** Physical net export and *reported generation minus consumption* are different calculations with different reporting methodologies. They should not be assumed to match, or treated as a verified national energy balance.

## Example Home Assistant dashboard

The following optional example displays all main production groups, their reported-generation shares, Sweden-wide consumption, the indicative production/consumption difference, and physical cross-border imports/exports.

It uses [Bar Card (maintained fork)](https://github.com/vogon1/bar-card) for the percentage bars, plus Home Assistant's built-in Entities cards. Install Bar Card through HACS Marketplace (add that repository as a **Dashboard** custom repository if necessary) before pasting this YAML into a **Manual card**.

The example requires no template entities, helpers, or changes to `configuration.yaml`. If your installation has customized entity IDs, adjust them to match your Home Assistant entity registry.

```yaml
type: vertical-stack
cards:
  - type: custom:bar-card
    title: ⚡ Sveriges elproduktion
    direction: right
    height: 34px
    decimal: 1
    min: 0
    max: 100
    animation:
      state: "on"
      speed: 2
    positions:
      icon: "off"
      name: outside
      value: inside
      indicator: "off"
      minmax: "off"
    entities:
      - entity: sensor.sveriges_elsystem_andel_rapporterad_produktion_karnkraft
        name: Kärnkraft
        color: "#8b7cf6"
      - entity: sensor.sveriges_elsystem_andel_rapporterad_produktion_vattenkraft
        name: Vattenkraft
        color: "#2196f3"
      - entity: sensor.sveriges_elsystem_andel_rapporterad_produktion_vindkraft
        name: Vindkraft
        color: "#42c78a"
      - entity: sensor.sveriges_elsystem_andel_rapporterad_produktion_ovrig
        name: Övrig produktion
        color: "#f4ad46"

  - type: entities
    title: 🏭 Produktion per kraftslag
    show_header_toggle: false
    entities:
      - entity: sensor.sveriges_elsystem_rapporterad_produktion_karnkraft_totalt
        name: Kärnkraft
        icon: mdi:atom
      - entity: sensor.sveriges_elsystem_rapporterad_produktion_vattenkraft_totalt
        name: Vattenkraft
        icon: mdi:hydro-power
      - entity: sensor.sveriges_elsystem_rapporterad_produktion_vindkraft_totalt
        name: Vindkraft
        icon: mdi:wind-turbine
      - entity: sensor.sveriges_elsystem_rapporterad_produktion_ovrig_totalt
        name: Övrig produktion
        icon: mdi:factory

  - type: entities
    title: 📊 Sveriges elbalans
    show_header_toggle: false
    entities:
      - entity: sensor.sveriges_elsystem_summa_rapporterad_produktion
        name: Rapporterad produktion
        icon: mdi:lightning-bolt
      - entity: sensor.sveriges_elsystem_elforbrukning_sverige
        name: Total förbrukning
        icon: mdi:home-lightning-bolt
      - entity: sensor.sveriges_elsystem_rapporterad_produktion_minus_forbrukning
        name: Produktion minus förbrukning
        icon: mdi:scale-balance

  - type: entities
    title: 🌍 Import och export
    show_header_toggle: false
    entities:
      - entity: sensor.sveriges_elsystem_import_sverige
        name: Import
        icon: mdi:arrow-collapse-right
      - entity: sensor.sveriges_elsystem_export_sverige
        name: Export
        icon: mdi:arrow-expand-right
      - entity: sensor.sveriges_elsystem_nettoexport_sverige
        name: Nettoexport
        icon: mdi:transmission-tower
```

**Reading the chart:** The four bar lengths show each group's share of *reported Swedish electricity generation*, **not** its share of installed capacity, electricity consumption, or supply including imports. The MW sensors provide the corresponding reported generation values. Generation reporting may be incomplete. These qualifications are documented here rather than adding a separate disclaimer panel to the dashboard.

## Managing optional sensors

To enable a disabled entity in Home Assistant:

1. Open **Settings → Devices & services**.
2. Select **Svenska kraftsystemet**, then the device **Sveriges elsystem**.
3. Open the entity list and include disabled entities.
4. Select an optional entity and enable it.

Default enabled/disabled settings apply to newly registered entities. Updating an existing installation preserves previous entity-registry preferences.

## Requirements

- Home Assistant 2026.11.0 or newer
- Internet connection
- ENTSO-E Transparency Platform account and REST API security token
- HACS Marketplace for installing through a custom repository
- Optional: Bar Card for the example dashboard only

## Obtaining an ENTSO-E API token

1. Register at [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).
2. Verify your email address.
3. Request REST API access according to ENTSO-E's current instructions.
4. After approval, generate a security token in your account settings.
5. Store the token securely.

**Never publish your API token in GitHub, Home Assistant screenshots, logs, or issue reports.**

## Installation

### HACS Marketplace – Custom repository

1. Open **HACS Marketplace**.
2. Open the menu and select **Custom repositories**.
3. Enter `https://github.com/JojjeHA/svenska-kraftsystemet` and select **Integration**.
4. Add the repository, find **Svenska kraftsystemet**, and download it.
5. Restart Home Assistant.

### Configure the integration

1. Open **Settings → Devices & services → Add integration**.
2. Search for **Svenska kraftsystemet**.
3. Enter your ENTSO-E API token.
4. Complete the configuration.

The integration creates a device named **Sveriges elsystem**. Sensors are registered immediately; the initial API collection runs in the background, so values can temporarily appear as `Unavailable` after startup.

### Manual installation

Copy `custom_components/svenska_kraftsystemet` into `/config/custom_components/svenska_kraftsystemet`, restart Home Assistant, and configure the integration through **Settings → Devices & services**.

## Data sources and updates

All generation, consumption, and cross-border flow data comes from the ENTSO-E Transparency Platform REST API.

| Dataset | Document type |
|---|---|
| Actual generation per production type | A75 |
| Actual consumption | A65 |
| Physical cross-border flows | A11 |

The integration requests updates every **15 minutes**. Each refresh issues up to **31 API requests** (4 generation, 5 consumption, and 22 cross-border-flow requests), with up to four requests running concurrently.

To account for ENTSO-E publication delays, the integration initially considers a reporting timestamp about **45 minutes** before the current time, rounded down to a quarter-hour. It searches backward in 15-minute steps over a window of up to **six hours**, using the datasets retrieved during that refresh rather than repeating the API requests for each candidate timestamp.

The integration prefers the newest reporting timestamp with generation readings for all four Swedish bidding zones and Sweden-wide consumption. When a fully complete timestamp is unavailable, it can expose a partial same-timestamp snapshot instead of making every sensor unavailable. Missing inputs remain unavailable; derived country-wide production totals cannot be computed if a bidding zone's production dataset is missing.

**This is reported data, not a real-time feed.** Values may remain unchanged across several refreshes, and ENTSO-E can publish or revise readings later.

The parser supports `A01` fixed-interval series and `A03` variable-length blocks. Sensors expose a `data_time_utc` attribute showing the selected UTC reporting timestamp. This is the timestamp chosen by the integration, not a guarantee that every upstream measurement has identical publication latency or methodology.

## Data accuracy and limitations

- ENTSO-E production categories may be delayed, incomplete, or absent.
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

## Integration icon

The integration includes local branding files:

- `brand/icon.png` – 256 × 256 pixels
- `brand/icon@2x.png` – 512 × 512 pixels

## Planned features

Possible future improvements include grid frequency for the Nordic synchronous area, individual nuclear-reactor availability and production data, independently verified national generation totals, improved localization, configurable update settings, diagnostics and reporting-completeness indicators, and further API optimizations.

These features are planned or under consideration, not part of this release.

## Version history

### v0.1.5
- First stable release with the new calculated production sensors and 15-minute updates
- Documentation and example dashboard for the tested v0.1.4 functionality
- No changes to the data-collection logic compared with v0.1.4

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

## Issues and feedback

Bug reports, feature requests, and suggestions are welcome at [GitHub Issues](https://github.com/JojjeHA/svenska-kraftsystemet/issues).

Include the Home Assistant version, integration version, a description, and relevant error messages with sensitive information removed. **Never include your ENTSO-E API token.**

## Credits

Electricity system data is provided by the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/). This project is an independent Home Assistant custom integration.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE). ENTSO-E data usage remains subject to the applicable ENTSO-E terms and conditions.
