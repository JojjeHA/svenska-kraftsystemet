# Installation and setup

Installation through HACS or manually, plus configuration and optional sensors.

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

## Managing optional sensors

To enable a disabled entity in Home Assistant:

1. Open **Settings → Devices & services**.
2. Select **Svenska kraftsystemet**, then the device **Sveriges elsystem**.
3. Open the entity list and include disabled entities.
4. Select an optional entity and enable it.

Default enabled/disabled settings apply to newly registered entities. Updating an existing installation preserves previous entity-registry preferences.
