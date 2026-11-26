# Example Home Assistant dashboard

An optional dashboard example using Bar Card and built-in Entities cards.

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
