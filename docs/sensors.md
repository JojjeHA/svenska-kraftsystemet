# Sensors and calculations

Detailed entity groups, default enabled sensors and calculated values.

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

Calculated values require production datasets from **all four Swedish bidding zones** and the presence, across Sweden as a whole, of each of these main generation groups: nuclear (`B14`), hydro (`B11` or `B12`), wind (`B18` or `B19`), and other (`B20`). These groups are **not** required individually in every bidding zone. A missing or ambiguous input makes the derived national generation totals and shares unavailable instead of allowing misleading percentages (such as 100% wind power when other data is missing).

This is a **conservative completeness heuristic**, not proof that every technology or plant is reported. A legitimate dataset without a separately reported `B20` category may be rejected. The reported sum is **not an independently verified total of all Swedish generation**. See [Data accuracy and limitations](#data-accuracy-and-limitations).

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
