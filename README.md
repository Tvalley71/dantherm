# Dantherm

Home Assistant integration for Dantherm ventilation units.

[![Installations](https://img.shields.io/endpoint?url=https://ha-analytics.vaskivskyi.com/badges/dantherm/total.json&style=for-the-badge&color=blue)](https://github.com/Tvalley71/dantherm)

> [!TIP]
> The integration also exist in a version for Pluggit ventilation units [here](https://github.com/Tvalley71/pluggit).

<!-- START:shared-section -->

<a href="https://www.buymeacoffee.com/tvalley71" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

### ⚠️ Compatibility Notice

This custom integration requires:

- Home Assistant version **2025.8.0** or newer

Only support for Modbus over TCP/IP.

<!-- END:shared-section -->

Known supported units:

- HCV300 ALU
- HCV500 ALU
- HCV700 ALU
- HCV400 P1-E1/P2
- HCV460 P2/E1
- RCV320 P1/P2
- HCH5 MKII
- RCC220 P2

<!-- START:shared-section -->

<!-- START:shared-section no-replace -->
The listed units are known to work with this integration. Basically, all units compatible with the **_Dantherm Residential_** or **_Pluggit iFlow_** apps should work with the integration as well.

Users have also reported compatibility with the following units:

- Bosch Vent 5000 C
- Fränkische Profi-Air Flex
- Fränkische Profi-Air 180 Flat

<!-- END:shared-section -->

> [!NOTE]
> If you have a model not listed and are using this integration, please let me know by posting [here](https://github.com/Tvalley71/dantherm/discussions/new?category=general). Make sure to include both the model name and the unit type number.
> The number can be found in the **Device Info** section on the integration page; if the unit is not recognized, it will be listed as "Unknown" followed by the number.

### Guide

If you prefer a video walkthrough, I recommend:

[Pluggit Lüftungsanlage 💨 mit Home Assistant smart machen 😍](https://www.youtube.com/watch?v=e4oRw25Emlo) — in German, up to date with version 1.0

Thanks to _Smartzeug_

### Controls and sensors

#### Buttons Entities

| Entity            | Description       |
|-------------------|-------------------|
| `alarm_reset`     | Clears the active alarm and dismis the alarm notification |
| `filter_reset`    | Resets the filter remain timer and dismis the alarm notification |

#### Calendar Entity

| Entity    | Description              |
|-----------|--------------------------|
| `calendar`| Controls scheduled operations based on Home Assistant calendar events |

#### Cover Entity

| Entity           | Description              |
|------------------|--------------------------|
| `bypass_damper`  | Indicates and controls the manual bypass state of the bypass damper [[1]](#entity-notes) |

#### Event Entities

| Entity         | Description |
|----------------|-------------|
| `alarm_event`  | Fires event notifications when the unit reports a new alarm. Supported event types: `alarm_exhaust_air_fan`, `alarm_supply_air_fan`, `alarm_bypass_damper`, `alarm_outdoor_air`, `alarm_supply_air`, `alarm_extract_air`, `alarm_exhaust_air`, `alarm_room_air`, `alarm_rh`, `alarm_outdoor_temperature`, `alarm_supply_temperature`, `alarm_overtemperature`, `alarm_communication_error`, `alarm_fire`, `alarm_high_waterlevel`, `alarm_fire_protection`. Alarm events include `alarm_code` and `alarm_text` attributes. |
| `filter_event` | Fires event notifications for filter lifecycle changes. Supported event types: `filter_warning`, `filter_expired`. |

#### Fan Entity
| Entity           | Description              |
|------------------|--------------------------|
| `ventilation`    | Indicates and controls the operation and fan level of the ventilation unit |

#### Number Entities

| Entity                              | Description                        |
|-------------------------------------|------------------------------------|
| `boost_mode_timeout`                | Sets the duration for Boost Mode before it automatically turns off [[3]](#entity-notes) |
| `bypass_minimum_temperature`        | Minimum outdoor temperature (winter[[6]](#entity-notes)) allowed for bypass damper to open [[2][5]](#entity-notes) |
| `bypass_maximum_temperature`        | Maximum outdoor temperature (winter[[6]](#entity-notes)) allowed for bypass damper to open [[2][5]](#entity-notes) |
| `bypass_minimum_temperature_summer` | Minimum outdoor temperature (summer) allowed for bypass damper to open [[2][5]](#entity-notes) |
| `bypass_maximum_temperature_summer` | Maximum outdoor temperature (summer) allowed for bypass damper to open [[2][5]](#entity-notes) |
| `eco_mode_timeout`                  | Sets the duration for Eco Mode before it automatically deactivates [[3]](#entity-notes) |
| `filter_lifetime`                   | Expected lifetime of the filter before triggering a replacement notification [[1][2]](#entity-notes) |
| `humidity_setpoint`                 | Humidity setpoint in % (winter[[6]](#entity-notes)) [[2][5]](#entity-notes) |
| `humidity_setpoint_summer`          | Humidity setpoint in % (summer) [[2][5]](#entity-notes) |
| `home_mode_timeout`                 | Sets how long Home Mode should remain active after being triggered [[3]](#entity-notes) |
| `manual_bypass_duration`            | Duration for which manual bypass remains active after user activation [[1][2][5]](#entity-notes) |
| `air_quality_low_threshold`         |  Set the low threshold for air quality sensitivity [[1][2]](#entity-notes) |
| `air_quality_middle_threshold`      |  Set the middle threshold for air quality sensitivity [[1][2]](#entity-notes) |
| `air_quality_high_threshold`        |  Set the high threshold for air quality sensitivity [[1][2]](#entity-notes) |

#### Select Entities

| Entity                      | Description                        |
|-----------------------------|------------------------------------|
| `boost_operation_selection` | Defines which mode to apply when Boost Mode is triggered [[3]](#entity-notes) |
| `eco_operation_selection`   | Defines which mode to apply when Eco Mode is triggered [[3]](#entity-notes) |
| `fan_level_selection`       | Selects the current fan level (Level 0 to Level 4). _Level 0_ and _Level 4_ will timeout after a fixed period. |
| `home_operation_selection`  | Defines which mode to apply when Home Mode is triggered [[3]](#entity-notes) |
| `operation_selection`       | Selects the current mode of operation (Standby, Automatic, Manual, Week Program, Away Mode, Summer Mode, Fireplace Mode and Night Mode). _Night Mode_ is display only. _Standby_ and _Fireplace Mode_ will timeout after a fixed period. |
| `week_program_selection`    | Selects the active predefined week program (Week Program 1 to Week Program 11). _Week Program 11_ can be user defined but not through the integration. [[2]](#entity-notes) |

#### Sensor Entities

| Entity                        | Description                          |
|-------------------------------|--------------------------------------|
| `actions_pending`             | Indicates whether one or more write actions are queued, in progress, or awaiting a follow-up refresh |
| `air_quality`                 | Measures air quality if the unit is equipped with a VOC or CO₂ sensor [[1]](#entity-notes) |
| `air_quality_level`           | Indicates the qualitative level of air quality (Clean, Polluted, etc.) [[2]](#entity-notes) |
| `alarm`                       | Reports active alarms such as fan or temperature alarms |
| `exhaust_temperature`         | Temperature of indoor air being exhausted after heat recovery |
| `extract_temperature`         | Temperature of indoor air being pulled out for heat recovery |
| `fan_level`                   | Current fan level (Level 0 to Level 4) |
| `fan1_speed`                  | Actual RPM of fan 1 [[2]](#entity-notes) |
| `fan2_speed`                  | Actual RPM of fan 2 [[2]](#entity-notes) |
| `filter_remain`               | Remaining filter life in days [[1]](#entity-notes) |
| `filter_remain_level`         | Qualitative status of the remaining filter lifetime (e.g. Good, Replace). If the unit supports ServoFlow, the status is based on the filter's dirtiness degree; otherwise, it is based on the filter's remaining lifetime in days. [[1][2]](#entity-notes) |
| `humidity`                    | Indoor relative humidity from internal sensor [[1]](#entity-notes) |
| `humidity_level`              | Qualitative level of humidity (e.g. Dry, Normal, Humid) [[2]](#entity-notes) |
| `adaptive_state`              | Shows which adaptive mode (Home, Eco, Boost) is currently active [[4]](#entity-notes) |
| `internal_preheater_dutycycle`| Percentage of power used by the internal electric preheater [[1][2]](#entity-notes) |
| `operation_mode`              | Current system mode: Automatic, Manual, Week Program, etc. |
| `outdoor_temperature`         | Temperature of fresh outdoor air being pulled in from outside the home |
| `room_temperature`            | Room air temperature from the Dantherm HRC/Pluggit APRC remote [[1][2]](#entity-notes) |
| `supply_temperature`          | Temperature of the supply air delivered to the home |
| `work_time`                   | Total operational runtime of the unit [[2]](#entity-notes) |

#### Switch Entities

| Entity                 | Description                     |
|------------------------|---------------------------------|
| `away_mode`            | Enables or disables Away Mode |
| `boost_mode`           | Enables or disables Boost Mode [[3]](#entity-notes) |
| `disable_bypass`       | Forces the bypass damper to remain closed [[2]](#entity-notes) |
| `eco_mode`             | Enables or disables Eco Mode [[3]](#entity-notes) |
| `fireplace_mode`       | Enables Fireplace Mode, increases supply air to compensate for fireplace draft |
| `home_mode`            | Enables or disables Home Mode [[3]](#entity-notes) |
| `manual_bypass_mode`   | Manually activates bypass regardless of conditions [[1]](#entity-notes) |
| `night_mode`           | Enables or disables Night Mode [[2]](#entity-notes) |
| `sensor_filtering`     | Enables or disables sensor value filtering for stability [[2]](#entity-notes) |
| `summer_mode`          | Enables or disables Summer Mode |

#### Text Entities

| Entity                   | Description                     |
|--------------------------|---------------------------------|
| `night_mode_end_time`    | Sets the end time for Night Mode [[2]](#entity-notes) |
| `night_mode_start_time`  | Sets the start time for Night Mode [[2]](#entity-notes) |

<h4 id="entity-notes">Notes</h4>

[1] The entity may not install due to lack of support or installation in the particular unit.
[2] The entity is disabled by default.
[3] The entity will be enabled or disabled depending on whether the corresponding adaptive trigger is configured.
[4] The entity can only be enabled if any of the adaptive triggers are configured.
[5] The entity may not install due to firmware limitation.
[6] Winter setting if summer setting is available (Firmware ≥ 3.14).

_~~Strikethrough~~ is a work in progress, planned for version 0.5.0._

### Installation

<!-- START:shared-section replace-all -->

#### Installation via HACS (Home Assistant Community Store)

1. Ensure you have HACS installed and configured in your Home Assistant instance.
2. Open the HACS (Home Assistant Community Store) by clicking **HACS** in the side menu.
3. Click on **Integrations** and then click the **Explore & Download Repositories** button.
4. Search for "Dantherm" in the search bar.
5. Locate the "Dantherm Integration" repository and click on it.
6. Click the **Install** button.
7. Once installed, restart your Home Assistant instance.

#### Manual Installation

1. Navigate to your Home Assistant configuration directory.
    - For most installations, this will be **'/config/'**.
2. Inside the configuration directory, create a new folder named **'custom_components'** if it does not already exist.
3. Inside the **'custom_components'** folder, create a new folder named **'dantherm'**.
4. Download the latest release of the Dantherm integration from the [releases page](https://github.com/Tvalley71/dantherm/releases/latest) into the **'custom_components/dantherm'** directory:
5. Once the files are in place, restart your Home Assistant instance.

<!-- END:shared-section -->

### Configuration

After installation, add the Dantherm integration to your Home Assistant configuration.

1. In Home Assistant, go to **Configuration > Integrations.**
2. Click the **+** button to add a new integration.
3. Search for "Dantherm" and select it from the list of available integrations.
4. Follow the on-screen instructions to complete the integration setup.

<img width="400" height="460" alt="Skærmbillede 02-11-2025 kl  12 24 10 PM" src="https://github.com/user-attachments/assets/2812e63a-9976-4ea7-9bad-58fb14dc1b03" />
<img width="400" height="364" alt="Skærmbillede 02-11-2025 kl  12 56 47 PM" src="https://github.com/user-attachments/assets/4f68ae3b-c719-4d3f-bdc7-304424b5ec62" />

<!-- END:shared-section -->

### Support

If you encounter any issues or have questions regarding the Dantherm integration for Home Assistant, feel free to [open an issue](https://github.com/Tvalley71/dantherm/issues/new) or [start a discussion](https://github.com/Tvalley71/dantherm/discussions) on this repository. I welcome any contributions or feedback.

<!-- START:shared-section -->

### Languages

Currently supported languages:

Danish, Dutch, English, German and French.

> [!NOTE]
> Want to help translate? Grab a language file on GitHub [here](./custom_components/dantherm/translations) and post it [here](https://github.com/Tvalley71/dantherm/discussions/new?category=general). You are also welcome to submit a PR.


## Screenshots

![Skærmbillede fra 2025-02-09 15-49-04](https://github.com/user-attachments/assets/81ded97a-ff08-41f6-8ac4-8042501e355d)

![Skærmbillede fra 2025-02-09 15-26-39](https://github.com/user-attachments/assets/f12ce875-5f48-47d2-a975-3872f6415c07)
![Skærmbillede fra 2025-02-09 15-27-48](https://github.com/user-attachments/assets/2ca03de0-a469-4b0e-b362-5f6d486d1f9e)

![Skærmbillede fra 2025-02-09 15-28-23](https://github.com/user-attachments/assets/0efe815a-51fb-4e4b-bee8-d62bea40d4a7)
![Skærmbillede fra 2025-02-09 15-28-58](https://github.com/user-attachments/assets/6c192224-03cf-4094-b944-942c7395cd5b)

![Skærmbillede fra 2025-02-09 15-31-03](https://github.com/user-attachments/assets/1d17f88b-c3f0-441a-917c-55bee87f287e)


> [!NOTE]
> The HAC module functions are currently unsupported due to limited testing possibilities. If support for these functions are desired, please contact me for potential collaborative efforts to provide the support.


## Examples

#### Picture-elements card

This picture-elements card provides a dynamic and intuitive interface for monitoring and controlling your Dantherm ventilation unit. Designed to resemble the Dantherm app, it visually adapts based on the unit’s bypass state while displaying key real-time data:

*	Alarms – Stay alerted to system issues.
*	Filter Remaining Level – Easily check when filter replacement is needed.
*	Ventilation Temperatures – View four key temperature readings: Supply, Extract, Outdoor, and Exhaust.
*	Humidity Level – Monitor indoor humidity for optimal air quality.
*	Air Quality – Monitor indoor air quality.

Clicking on any displayed entity allows you to adjust its state or explore detailed history graphs for deeper insights.

![Skærmbillede 2025-06-30 kl  05 39 01](https://github.com/user-attachments/assets/a6adac2d-c003-4bd4-a98a-44e03d808007)
![Skærmbillede 29-06-2025 kl  07 42 02 AM](https://github.com/user-attachments/assets/67f88f90-7bf5-402c-9158-340c4eaaf1a7)
![Skærmbillede 29-06-2025 kl  07 45 12 AM](https://github.com/user-attachments/assets/aa2a6860-7741-41e9-b9a0-f6f7816a8120)
![Skærmbillede 29-06-2025 kl  08 52 02 AM](https://github.com/user-attachments/assets/6c503ccf-38ca-435d-8819-ae4d40129dc3)

<details>

<summary>The details for the above picture-elements card 👈 Click to open</summary>

####

To integrate this into your dashboard, insert the following code into your dashboard. If your Home Assistant setup uses a language other than English, make sure to modify the entity names in the code accordingly. You also need to enable the `filter_remain_level`, `humidity_level` and `air_quality_level` sensors if these options are included.

#### The code

```yaml

type: picture-elements
image: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMzY3IiBoZWlnaHQ9Ijk5MiIgdmlld0JveD0iMCAwIDEzNjcgOTkyIiBmaWxsPSJub25lIj4KPHBhdGggZD0iTTEyMjcgODgyIFY5ODAgSDc3IFYyNzggSDIwIFYyNDQgTDI4MiAxNTEgVjUyIEgzNTkgVjEyMCBMNjUxIDE0IEwxMjgyIDI0NCBWMjc4IEgxMjI3IFY1ODQiIHN0cm9rZT0iI0M4OEQ0RCIgc3Ryb2tlLXdpZHRoPSIxOSIgc3Ryb2tlLWxpbmVqb2luPSJtaXRlciIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiIGZpbGw9Im5vbmUiLz4KPHBhdGggZD0iTTYwNyA1ODQgVjM5OCBIMTAwOCBWNTg0IiBzdHJva2U9IiNBNkE4QjYiIHN0cm9rZS13aWR0aD0iMTYiIHN0cm9rZS1saW5lam9pbj0ibWl0ZXIiIHN0cm9rZS1saW5lY2FwPSJidXR0IiBmaWxsPSJub25lIi8+CjxwYXRoIGQ9Ik02MDcgODgyIFY5MjcgSDEwMDggVjg4MiIgc3Ryb2tlPSIjQTZBOEI2IiBzdHJva2Utd2lkdGg9IjE2IiBzdHJva2UtbGluZWpvaW49Im1pdGVyIiBzdHJva2UtbGluZWNhcD0iYnV0dCIgZmlsbD0ibm9uZSIvPgo8L3N2Zz4=
elements:
  - type: image
    entity: sensor.dantherm_filter_remain_level
    state_image:
      "0": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNzIiIGhlaWdodD0iODEiIHZpZXdCb3g9IjAgMCAyNzIgODEiPjxwYXRoIGQ9Ik0gMjcwIDAgTCAxIDEgTCAxIDc5IEwgMjcwIDc5IFogTSAxNzggNzEgTCAxODQgNjQgTCAxODQgNjIgTCAxODcgNjAgTCAxODcgNTggTCAxOTIgNTMgTCAxOTIgNTEgTCAxOTUgNDkgTCAxOTYgNDYgTCAyMDEgNDEgTCAyMDEgMzkgTCAyMTMgMjQgTCAyMTMgMjIgTCAyMTggMTggTCAyMTkgMTUgTCAyMjMgMTUgTCAyMjUgMTcgTCAyMjUgMTkgTCAyMzAgMjQgTCAyMzAgMjYgTCAyMzMgMjggTCAyMzUgMzIgTCAyMzkgMzYgTCAyMzkgMzggTCAyNDcgNDcgTCAyNDcgNDkgTCAyNTYgNTkgTCAyNTYgNjEgTCAyNjEgNjYgTCAyNjIgNjkgTCAyNjQgNzAgTCAyNjQgNzMgTCAyNjMgNzQgTCAxNzkgNzQgWiBNIDk0IDcwIEwgMTAyIDYwIEwgMTAyIDU4IEwgMTA3IDUzIEwgMTA3IDUxIEwgMTEwIDQ5IEwgMTExIDQ2IEwgMTE2IDQxIEwgMTE2IDM5IEwgMTE4IDM4IEwgMTE5IDM1IEwgMTI0IDMwIEwgMTI0IDI4IEwgMTI3IDI2IEwgMTI4IDIzIEwgMTMzIDE4IEwgMTMzIDE2IEwgMTM2IDE1IEwgMTM5IDE4IEwgMTM5IDIwIEwgMTQ0IDI0IEwgMTQ0IDI2IEwgMTQ4IDMwIEwgMTQ4IDMyIEwgMTUzIDM2IEwgMTUzIDM4IEwgMTU2IDQxIEwgMTU2IDQzIEwgMTYxIDQ3IEwgMTYxIDQ5IEwgMTY1IDUzIEwgMTY1IDU1IEwgMTcwIDU5IEwgMTcwIDYxIEwgMTc4IDcxIEwgMTc2IDczIEwgOTYgNzMgWiBNIDcgNzEgTCAxMyA2NCBMIDEzIDYyIEwgMTYgNjAgTCAxNiA1OCBMIDIxIDUzIEwgMjEgNTEgTCAyNCA0OSBMIDI1IDQ2IEwgMzAgNDEgTCAzMCAzOSBMIDQyIDI0IEwgNDIgMjIgTCA0NyAxOCBMIDQ4IDE1IEwgNTIgMTUgTCA1NCAxNyBMIDU0IDE5IEwgNTkgMjQgTCA1OSAyNiBMIDYyIDI4IEwgNjQgMzIgTCA2OCAzNiBMIDY4IDM4IEwgNzYgNDcgTCA3NiA0OSBMIDg1IDU5IEwgODUgNjEgTCA5MCA2NiBMIDkxIDY5IEwgOTMgNzAgTCA5MyA3MyBMIDkyIDc0IEwgOCA3NCBaIE0gMjIyIDYgTCAyMjQgNSBMIDI2MyA1IEwgMjY1IDcgTCAyNjUgNjQgTCAyNjQgNjUgTCAyNjIgNjUgTCAyNjEgNjQgTCAyNjEgNjIgTCAyNTYgNTcgTCAyNTUgNTQgTCAyNTIgNTIgTCAyNTIgNTAgTCAyNDggNDYgTCAyNDkgNDUgTCAyNDggNDUgTCAyNDYgNDIgTCAyNDQgNDEgTCAyNDQgMzkgTCAyMzkgMzQgTCAyMzggMzEgTCAyMzUgMjkgTCAyMzUgMjcgTCAyMzIgMjQgTCAyMzIgMjIgTCAyMzEgMjIgTCAyMzAgMjAgTCAyMjcgMTggTCAyMjcgMTYgTCAyMjIgMTEgTCAyMjIgOSBMIDIyMSA4IFogTSA1MCA3IEwgNTMgNSBMIDIxOCA1IEwgMjIxIDcgTCAyMjEgMTAgTCAxOTkgMzcgTCAxODcgNTYgTCAxNzcgNjUgTCAxMzUgOSBMIDEwNCA1MyBMIDkxIDY1IEwgNzggNDUgTCA2NCAyOSBMIDYxIDIyIEwgNTEgMTEgWiBNIDUwIDcgTCA1MCAxMCBMIDQ4IDExIEwgNDcgMTQgTCA0MiAxOSBMIDQyIDIxIEwgNDAgMjIgTCAzOCAyNSBMIDM3IDI1IEwgMzcgMjcgTCAzMyAzMSBMIDMzIDMzIEwgMzEgMzQgTCAyOSAzNyBMIDI4IDM3IEwgMjggMzkgTCAyNSA0MiBMIDI1IDQ0IEwgMjMgNDUgTCAyMSA0OCBMIDIwIDQ4IEwgMjAgNTAgTCAxNiA1NCBMIDE2IDU2IEwgMTQgNTcgTCAxNCA1OCBMIDggNjUgTCA2IDY1IEwgNSA2NCBMIDUgNyBMIDggNSBMIDQ3IDUgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxMDcgNTQgTCAxMDMgNTggTCAxMDMgNTkgTCAxMDMgNTggWiBNIDExNiA0MiBMIDExMiA0NiBMIDExMSA0OCBMIDExMiA0NiBaIE0gMjA2IDM0IEwgMjA2IDM1IEwgMjAyIDM5IEwgMjA2IDM1IFogTSAzNSAzNCBMIDM1IDM1IEwgMzEgMzkgTCAzNSAzNSBaIE0gMjM0IDMxIEwgMjM0IDMyIEwgMjM4IDM2IEwgMjM0IDMyIFogTSA2MyAzMSBMIDYzIDMyIEwgNjcgMzYgTCA2MyAzMiBaIE0gMTI0IDI0IEwgMTIwIDI4IEwgMTIwIDI5IEwgMTIwIDI4IFogTSAyMjMgMTAgTCAyMjMgMTEgTCAyMjcgMTUgTCAyMjMgMTEgWiBNIDUyIDEwIEwgNTIgMTEgTCA1NiAxNSBMIDUyIDExIFoiIGZpbGw9IiM5QzlEQUIiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMCA3OSBMIDEgMCBMIDI2OSAwIEwgMSAwIFoiIGZpbGw9IiM5RkExQUYiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMTAgNjAgTCAxMCA2MiBMIDggNjQgTCA3IDY0IEwgOCA2NCBMIDEwIDYyIFogTSAxNzQgNTkgTCAxNzQgNjAgTCAxNzggNjQgTCAxNzkgNjQgTCAxODEgNjIgTCAxODEgNjAgTCAxODEgNjIgTCAxNzkgNjQgTCAxNzggNjQgTCAxNzQgNjAgWiBNIDI1OCA1OCBMIDI2MiA2MiBMIDI2MiA2MyBMIDI2NCA2NCBMIDI2MyA2NCBMIDI2MiA2MiBaIE0gODcgNTggTCA5MSA2MiBMIDkxIDYzIEwgOTMgNjQgTCA5MiA2NCBMIDkxIDYyIFogTSAxNjUgNTYgTCAxNjkgNjAgTCAxNjkgNjEgTCAxNjkgNjAgWiBNIDEwMiA1MyBMIDk4IDU3IEwgOTggNTkgTCA5OCA1NyBaIE0gMTkwIDUwIEwgMTg2IDU0IEwgMTg2IDU1IEwgMTg2IDU0IFogTSAxOSA1MCBMIDE1IDU0IEwgMTUgNTUgTCAxNSA1NCBaIE0gMTEyIDQ4IEwgMTA4IDUyIEwgMTA4IDUzIEwgMTA4IDUyIFogTSAxNjUgNDcgTCAxNjUgNDggTCAxNjkgNTIgTCAxNjUgNDggWiBNIDExMCA0MiBMIDEwNyA0NSBMIDEwNyA0NyBMIDEwNyA0NSBaIE0gMTU1IDQxIEwgMTU1IDQzIEwgMTU5IDQ3IEwgMTU1IDQzIFogTSAyMDIgNDAgTCAyMDIgNDEgTCAxOTggNDUgTCAyMDIgNDEgWiBNIDMxIDQwIEwgMzEgNDEgTCAyNyA0NSBMIDMxIDQxIFogTSAyMzggMzcgTCAyMzggMzggTCAyNDIgNDIgTCAyMzggMzggWiBNIDY3IDM3IEwgNjcgMzggTCA3MSA0MiBMIDY3IDM4IFogTSAxNTcgMzYgTCAxNTcgMzcgTCAxNjIgNDIgTCAxNjIgNDQgTCAxNjIgNDIgTCAxNTcgMzcgWiBNIDEyMCAzNiBMIDEyMCAzNyBMIDExNyA0MCBMIDExNyA0MSBMIDExNyA0MCBMIDEyMCAzNyBaIE0gMjAxIDM0IEwgMTk4IDM3IEwgMTk4IDM5IEwgMTk4IDM3IFogTSAzMCAzNCBMIDI3IDM3IEwgMjcgMzkgTCAyNyAzNyBaIE0gMTQ4IDMzIEwgMTUyIDM3IEwgMTUzIDM5IEwgMTUyIDM3IFogTSAxMTkgMzAgTCAxMTUgMzQgTCAxMTUgMzUgTCAxMTUgMzQgWiBNIDIyOSAyNSBMIDIyOSAyNiBMIDIzMyAzMCBMIDIyOSAyNiBaIE0gMTI5IDI1IEwgMTI1IDI5IEwgMTI1IDMwIEwgMTI1IDI5IFogTSA1OCAyNSBMIDU4IDI2IEwgNjIgMzAgTCA1OCAyNiBaIE0gMTQ4IDIzIEwgMTQ4IDI1IEwgMTUyIDI5IEwgMTQ4IDI1IFogTSAyMTggMTkgTCAyMTQgMjMgTCAyMTQgMjQgTCAyMTQgMjMgWiBNIDIxMiAxOSBMIDIxMiAyMCBMIDIwOCAyNCBMIDIxMiAyMCBaIE0gMTI3IDE5IEwgMTI0IDIyIEwgMTI0IDIzIEwgMTI0IDIyIFogTSA0NyAxOSBMIDQzIDIzIEwgNDMgMjQgTCA0MyAyMyBaIE0gNDEgMTkgTCA0MSAyMCBMIDM3IDI0IEwgNDEgMjAgWiBNIDIyOCAxNiBMIDIyOCAxNyBMIDIzMiAyMSBMIDIyOCAxNyBaIE0gMTMzIDE5IEwgMTM1IDE2IEwgMTM2IDE2IEwgMTM4IDE4IEwgMTM4IDIwIEwgMTM4IDE4IEwgMTM2IDE2IEwgMTM1IDE2IFogTSA1NyAxNiBMIDU3IDE3IEwgNjEgMjEgTCA1NyAxNyBaIE0gMTM1IDcgTCAxMzUgOCBMIDEzNiA4IEwgMTQwIDEyIEwgMTM2IDggTCAxMzYgNyBaIiBmaWxsPSIjODU4NjkxIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDEzOCA3IEwgMjE4IDcgTCAyMTkgOSBMIDIxOCAxMCBMIDIxOSA5IEwgMjE4IDcgWiBNIDUzIDcgTCAxMzMgNyBMIDEzNCA4IEwgMTMzIDcgWiBNIDggNyBMIDQ3IDcgTCA0OCA5IEwgNDcgMTAgTCA0OCA5IEwgNDcgNyBaIiBmaWxsPSIjNEQ0RDUzIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDE2OSA2MiBMIDE3MyA2NiBMIDE3MyA2NyBMIDE3MyA2NiBaIE0gMTcwIDUzIEwgMTcwIDU0IEwgMTc0IDU4IEwgMTcwIDU0IFogTSAxMTcgNDIgTCAxMTMgNDYgTCAxMTMgNDcgTCAxMTMgNDYgWiBNIDExNCAzNiBMIDExMCA0MCBMIDExMCA0MSBMIDExMCA0MCBaIE0gMjE0IDI1IEwgMjEwIDI5IEwgMjEwIDMwIEwgMjEwIDI5IFogTSA0MyAyNSBMIDM5IDI5IEwgMzkgMzAgTCAzOSAyOSBaIE0gMjMzIDIyIEwgMjMzIDIzIEwgMjM2IDI2IEwgMjM2IDI3IEwgMjM2IDI2IEwgMjMzIDIzIFogTSA2MiAyMiBMIDYyIDIzIEwgNjUgMjYgTCA2NSAyNyBMIDY1IDI2IEwgNjIgMjMgWiBNIDIyNCAxOSBMIDIyNCAyMCBMIDIyOCAyNCBMIDIyNCAyMCBaIE0gNTMgMTkgTCA1MyAyMCBMIDU3IDI0IEwgNTMgMjAgWiBNIDIxNiAxMyBMIDIxNiAxNCBMIDIxMiAxOCBMIDIxNiAxNCBaIE0gNDUgMTMgTCA0NSAxNCBMIDQxIDE4IEwgNDUgMTQgWiBNIDI2MyA3IEwgMjY0IDggTCAyNjQgNjMgTCAyNjQgOCBaIiBmaWxsPSIjNUI1QjYzIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48L3N2Zz4=
      "1": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNzIiIGhlaWdodD0iODEiIHZpZXdCb3g9IjAgMCAyNzIgODEiPjxwYXRoIGQ9Ik0gMjcwIDAgTCAxIDEgTCAxIDc5IEwgMjcwIDc5IFogTSAxNzggNzEgTCAxODQgNjQgTCAxODQgNjIgTCAxODcgNjAgTCAxODcgNTggTCAxOTIgNTMgTCAxOTIgNTEgTCAxOTUgNDkgTCAxOTYgNDYgTCAyMDEgNDEgTCAyMDEgMzkgTCAyMTMgMjQgTCAyMTMgMjIgTCAyMTggMTggTCAyMTkgMTUgTCAyMjMgMTUgTCAyMjUgMTcgTCAyMjUgMTkgTCAyMzAgMjQgTCAyMzAgMjYgTCAyMzMgMjggTCAyMzUgMzIgTCAyMzkgMzYgTCAyMzkgMzggTCAyNDcgNDcgTCAyNDcgNDkgTCAyNTYgNTkgTCAyNTYgNjEgTCAyNjEgNjYgTCAyNjIgNjkgTCAyNjQgNzAgTCAyNjQgNzMgTCAyNjMgNzQgTCAxNzkgNzQgWiBNIDk0IDcwIEwgMTAyIDYwIEwgMTAyIDU4IEwgMTA3IDUzIEwgMTA3IDUxIEwgMTEwIDQ5IEwgMTExIDQ2IEwgMTE2IDQxIEwgMTE2IDM5IEwgMTE4IDM4IEwgMTE5IDM1IEwgMTI0IDMwIEwgMTI0IDI4IEwgMTI3IDI2IEwgMTI4IDIzIEwgMTMzIDE4IEwgMTMzIDE2IEwgMTM2IDE1IEwgMTM5IDE4IEwgMTM5IDIwIEwgMTQ0IDI0IEwgMTQ0IDI2IEwgMTQ4IDMwIEwgMTQ4IDMyIEwgMTUzIDM2IEwgMTUzIDM4IEwgMTU2IDQxIEwgMTU2IDQzIEwgMTYxIDQ3IEwgMTYxIDQ5IEwgMTY1IDUzIEwgMTY1IDU1IEwgMTcwIDU5IEwgMTcwIDYxIEwgMTc4IDcxIEwgMTc2IDczIEwgOTYgNzMgWiBNIDcgNzEgTCAxMyA2NCBMIDEzIDYyIEwgMTYgNjAgTCAxNiA1OCBMIDIxIDUzIEwgMjEgNTEgTCAyNCA0OSBMIDI1IDQ2IEwgMzAgNDEgTCAzMCAzOSBMIDQyIDI0IEwgNDIgMjIgTCA0NyAxOCBMIDQ4IDE1IEwgNTIgMTUgTCA1NCAxNyBMIDU0IDE5IEwgNTkgMjQgTCA1OSAyNiBMIDYyIDI4IEwgNjQgMzIgTCA2OCAzNiBMIDY4IDM4IEwgNzYgNDcgTCA3NiA0OSBMIDg1IDU5IEwgODUgNjEgTCA5MCA2NiBMIDkxIDY5IEwgOTMgNzAgTCA5MyA3MyBMIDkyIDc0IEwgOCA3NCBaIE0gMjIyIDYgTCAyMjQgNSBMIDI2MyA1IEwgMjY1IDcgTCAyNjUgNjQgTCAyNjQgNjUgTCAyNjIgNjUgTCAyNjEgNjQgTCAyNjEgNjIgTCAyNTYgNTcgTCAyNTUgNTQgTCAyNTIgNTIgTCAyNTIgNTAgTCAyNDggNDYgTCAyNDkgNDUgTCAyNDggNDUgTCAyNDYgNDIgTCAyNDQgNDEgTCAyNDQgMzkgTCAyMzkgMzQgTCAyMzggMzEgTCAyMzUgMjkgTCAyMzUgMjcgTCAyMzIgMjQgTCAyMzIgMjIgTCAyMzEgMjIgTCAyMzAgMjAgTCAyMjcgMTggTCAyMjcgMTYgTCAyMjIgMTEgTCAyMjIgOSBMIDIyMSA4IFogTSA1MCA3IEwgNTMgNSBMIDIxOCA1IEwgMjIxIDcgTCAyMjEgMTAgTCAxOTkgMzcgTCAxODcgNTYgTCAxNzcgNjUgTCAxMzUgOSBMIDEwNCA1MyBMIDkxIDY1IEwgNzggNDUgTCA2NCAyOSBMIDYxIDIyIEwgNTEgMTEgWiBNIDUwIDcgTCA1MCAxMCBMIDQ4IDExIEwgNDcgMTQgTCA0MiAxOSBMIDQyIDIxIEwgNDAgMjIgTCAzOCAyNSBMIDM3IDI1IEwgMzcgMjcgTCAzMyAzMSBMIDMzIDMzIEwgMzEgMzQgTCAyOSAzNyBMIDI4IDM3IEwgMjggMzkgTCAyNSA0MiBMIDI1IDQ0IEwgMjMgNDUgTCAyMSA0OCBMIDIwIDQ4IEwgMjAgNTAgTCAxNiA1NCBMIDE2IDU2IEwgMTQgNTcgTCAxNCA1OCBMIDggNjUgTCA2IDY1IEwgNSA2NCBMIDUgNyBMIDggNSBMIDQ3IDUgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA5IDcyIEwgOTEgNzIgTCA5MSA3MSBMIDgzIDYyIEwgODMgNjAgTCA3NCA1MCBMIDc0IDQ4IEwgNjYgMzkgTCA2NiAzNyBMIDYxIDMyIEwgNjAgMjkgTCA1NyAyNyBMIDU3IDI1IEwgNTIgMjAgTCA1MiAxOCBMIDQ5IDE3IEwgNDkgMTkgTCA0NCAyMyBMIDQ0IDI1IEwgNDAgMjkgTCA0MCAzMSBMIDM4IDMyIEwgMzcgMzUgTCAzMiA0MCBMIDMyIDQyIEwgMjMgNTIgTCAyMyA1NCBMIDE1IDYzIEwgMTUgNjUgWiIgZmlsbD0iI0E2NjI0MSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxMDcgNTQgTCAxMDMgNTggTCAxMDMgNTkgTCAxMDMgNTggWiBNIDExNiA0MiBMIDExMiA0NiBMIDExMSA0OCBMIDExMiA0NiBaIE0gMjA2IDM0IEwgMjA2IDM1IEwgMjAyIDM5IEwgMjA2IDM1IFogTSAzNSAzNCBMIDM1IDM1IEwgMzEgMzkgTCAzNSAzNSBaIE0gMjM0IDMxIEwgMjM0IDMyIEwgMjM4IDM2IEwgMjM0IDMyIFogTSA2MyAzMSBMIDYzIDMyIEwgNjcgMzYgTCA2MyAzMiBaIE0gMTI0IDI0IEwgMTIwIDI4IEwgMTIwIDI5IEwgMTIwIDI4IFogTSAyMjMgMTAgTCAyMjMgMTEgTCAyMjcgMTUgTCAyMjMgMTEgWiBNIDUyIDEwIEwgNTIgMTEgTCA1NiAxNSBMIDUyIDExIFoiIGZpbGw9IiM5QzlEQUIiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMCA3OSBMIDEgMCBMIDI2OSAwIEwgMSAwIFoiIGZpbGw9IiM5RkExQUYiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMTAgNjAgTCAxMCA2MiBMIDggNjQgTCA3IDY0IEwgOCA2NCBMIDEwIDYyIFogTSAxNzQgNTkgTCAxNzQgNjAgTCAxNzggNjQgTCAxNzkgNjQgTCAxODEgNjIgTCAxODEgNjAgTCAxODEgNjIgTCAxNzkgNjQgTCAxNzggNjQgTCAxNzQgNjAgWiBNIDI1OCA1OCBMIDI2MiA2MiBMIDI2MiA2MyBMIDI2NCA2NCBMIDI2MyA2NCBMIDI2MiA2MiBaIE0gMTg4IDU4IEwgMTg4IDYwIEwgMTg1IDYzIEwgMTg1IDY0IEwgMTg1IDYzIEwgMTg4IDYwIFogTSA4NyA1OCBMIDkxIDYyIEwgOTEgNjMgTCA5MyA2NCBMIDkyIDY0IEwgOTEgNjIgWiBNIDE3IDU4IEwgMTcgNjAgTCAxNCA2MyBMIDE0IDY0IEwgMTQgNjMgTCAxNyA2MCBaIE0gMjUxIDU2IEwgMjU1IDYwIEwgMjU2IDYyIEwgMjU1IDYwIFogTSA4MCA1NiBMIDg0IDYwIEwgODUgNjIgTCA4NCA2MCBaIE0gMTY0IDUzIEwgMTY0IDU1IEwgMTY5IDYwIEwgMTY5IDYyIEwgMTY5IDYwIEwgMTY0IDU1IFogTSAxMDIgNTMgTCA5OCA1NyBMIDk4IDU5IEwgOTggNTcgWiBNIDE5MCA1MCBMIDE4NiA1NCBMIDE4NiA1NSBMIDE4NiA1NCBaIE0gMTkgNTAgTCAxNSA1NCBMIDE1IDU1IEwgMTUgNTQgWiBNIDExMiA0OCBMIDEwOCA1MiBMIDEwOCA1MyBMIDEwOCA1MiBaIE0gMTk3IDQ3IEwgMTk3IDQ4IEwgMTkzIDUyIEwgMTk3IDQ4IFogTSAyNiA0NyBMIDI2IDQ4IEwgMjIgNTIgTCAyNiA0OCBaIE0gMTY1IDQ2IEwgMTY1IDQ4IEwgMTY5IDUyIEwgMTY1IDQ4IFogTSAxMTAgNDIgTCAxMDcgNDUgTCAxMDcgNDcgTCAxMDcgNDUgWiBNIDE5NiA0MSBMIDE5NSA0MyBMIDE5MSA0NyBMIDE5NSA0MyBaIE0gMTU1IDQxIEwgMTU1IDQzIEwgMTU5IDQ3IEwgMTU1IDQzIFogTSAyNSA0MSBMIDI0IDQzIEwgMjAgNDcgTCAyNCA0MyBaIE0gMjAzIDM5IEwgMjAyIDQxIEwgMTk4IDQ1IEwgMjAyIDQxIFogTSAzMiAzOSBMIDMxIDQxIEwgMjcgNDUgTCAzMSA0MSBaIE0gMjQ0IDM4IEwgMjQ1IDQwIEwgMjQ5IDQ0IEwgMjQ1IDQwIFogTSA3MyAzOCBMIDc0IDQwIEwgNzggNDQgTCA3NCA0MCBaIE0gMjM4IDM3IEwgMjM4IDM4IEwgMjQyIDQyIEwgMjM4IDM4IFogTSA2NyAzNyBMIDY3IDM4IEwgNzEgNDIgTCA2NyAzOCBaIE0gMTIwIDM2IEwgMTIwIDM3IEwgMTE3IDQwIEwgMTE3IDQxIEwgMTE3IDQwIEwgMTIwIDM3IFogTSAxNTcgMzUgTCAxNTcgMzcgTCAxNjIgNDIgTCAxNjIgNDQgTCAxNjIgNDIgTCAxNTcgMzcgWiBNIDIwMiAzMyBMIDE5OCAzNyBMIDE5OCAzOSBMIDE5OCAzNyBaIE0gMTQ4IDMzIEwgMTUyIDM3IEwgMTUzIDM5IEwgMTUyIDM3IFogTSAzMSAzMyBMIDI3IDM3IEwgMjcgMzkgTCAyNyAzNyBaIE0gMTE5IDMwIEwgMTE1IDM0IEwgMTE1IDM1IEwgMTE1IDM0IFogTSAyMzYgMjcgTCAyMzYgMjggTCAyNDAgMzIgTCAyMzYgMjggWiBNIDY1IDI3IEwgNjUgMjggTCA2OSAzMiBMIDY1IDI4IFogTSAyMjkgMjUgTCAyMjkgMjYgTCAyMzMgMzAgTCAyMjkgMjYgWiBNIDEyOSAyNSBMIDEyNSAyOSBMIDEyNSAzMCBMIDEyNSAyOSBaIE0gNTggMjUgTCA1OCAyNiBMIDYyIDMwIEwgNTggMjYgWiBNIDE0OCAyMyBMIDE0OCAyNSBMIDE1MiAyOSBMIDE0OCAyNSBaIE0gMjEyIDE5IEwgMjEyIDIwIEwgMjA4IDI0IEwgMjEyIDIwIFogTSA0MSAxOSBMIDQxIDIwIEwgMzcgMjQgTCA0MSAyMCBaIE0gMTI3IDE4IEwgMTI3IDE5IEwgMTI0IDIyIEwgMTI0IDIzIEwgMTI0IDIyIEwgMTI3IDE5IFogTSAyMjggMTYgTCAyMjggMTcgTCAyMzIgMjEgTCAyMjggMTcgWiBNIDIyMCAxNiBMIDIxOSAxNiBMIDIxOSAxOCBMIDIxNCAyMyBMIDIxNCAyNSBMIDIxNCAyMyBMIDIxOSAxOCBaIE0gMTM1IDE2IEwgMTMzIDE5IEwgMTM0IDE3IEwgMTM2IDE2IEwgMTM4IDE4IEwgMTM4IDIwIEwgMTQyIDI0IEwgMTM4IDIwIEwgMTM4IDE4IEwgMTM2IDE2IFogTSA1NyAxNiBMIDU3IDE3IEwgNjEgMjEgTCA1NyAxNyBaIE0gNDkgMTYgTCA0OCAxNiBMIDQ4IDE4IEwgNDMgMjMgTCA0MyAyNSBMIDQzIDIzIEwgNDggMTggWiBNIDEzNSA3IEwgMTM1IDggTCAxMzYgOCBMIDE0MCAxMiBMIDEzNiA4IEwgMTM2IDcgWiIgZmlsbD0iIzg0ODY5MSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxOTMgNTMgTCAxOTMgNTQgTCAxODkgNTggTCAxOTMgNTQgWiBNIDIyIDUzIEwgMjIgNTQgTCAxOCA1OCBMIDIyIDU0IFogTSAxNzAgNTIgTCAxNzAgNTQgTCAxNzQgNTggTCAxNzAgNTQgWiBNIDI0NiA1MCBMIDI1MCA1NCBMIDI1MCA1NSBMIDI1MCA1NCBaIE0gNzUgNTAgTCA3OSA1NCBMIDc5IDU1IEwgNzkgNTQgWiBNIDE5MCA0OCBMIDE5MCA0OSBMIDE4NiA1MyBMIDE5MCA0OSBaIE0gMTkgNDggTCAxOSA0OSBMIDE1IDUzIEwgMTkgNDkgWiBNIDE1OCA0NyBMIDE1OSA0OSBMIDE2MyA1MyBMIDE1OSA0OSBaIE0gMTA2IDQ3IEwgMTAyIDUxIEwgMTAyIDUyIEwgMTAyIDUxIFogTSAyNTAgNDUgTCAyNTAgNDYgTCAyNTMgNDkgTCAyNTMgNTAgTCAyNTMgNDkgTCAyNTAgNDYgWiBNIDc5IDQ1IEwgNzkgNDYgTCA4MiA0OSBMIDgyIDUwIEwgODIgNDkgTCA3OSA0NiBaIE0gMTE3IDQyIEwgMTEzIDQ2IEwgMTEzIDQ4IEwgMTEzIDQ2IFogTSAxMTQgMzYgTCAxMTAgNDAgTCAxMTAgNDEgTCAxMTAgNDAgWiBNIDI0MSAzMyBMIDI0MSAzNCBMIDI0NSAzOCBMIDI0MSAzNCBaIE0gNzAgMzMgTCA3MCAzNCBMIDc0IDM4IEwgNzAgMzQgWiBNIDIwNyAyNSBMIDIwNyAyNiBMIDIwMyAzMCBMIDIwNyAyNiBaIE0gMTQ5IDI1IEwgMTUzIDI5IEwgMTUzIDMxIEwgMTUzIDI5IFogTSAxNDIgMjUgTCAxNDIgMjYgTCAxNDYgMzAgTCAxNDIgMjYgWiBNIDM2IDI1IEwgMzYgMjYgTCAzMiAzMCBMIDM2IDI2IFogTSAyMzMgMjEgTCAyMzMgMjMgTCAyMzYgMjYgTCAyMzMgMjMgWiBNIDYyIDIxIEwgNjIgMjMgTCA2NSAyNiBMIDYyIDIzIFogTSAyMjQgMTkgTCAyMjQgMjAgTCAyMjggMjQgTCAyMjQgMjAgWiBNIDEzNCAxOSBMIDEzMCAyMyBMIDEzMCAyNCBMIDEzMCAyMyBaIE0gNTMgMTkgTCA1MyAyMCBMIDU3IDI0IEwgNTMgMjAgWiBNIDQ1IDEzIEwgNDUgMTQgTCA0MSAxOCBMIDQ1IDE0IFogTSAyMTYgMTIgTCAyMTYgMTQgTCAyMTIgMTggTCAyMTYgMTQgWiBNIDIyNCAxMCBMIDIyNCAxMSBMIDIyOCAxNSBMIDIyNCAxMSBaIE0gNTMgMTAgTCA1MyAxMSBMIDU3IDE1IEwgNTMgMTEgWiBNIDIyMyA3IEwgMjYzIDcgTCAyNjQgOCBMIDI2NCA2MyBMIDI2NCA4IEwgMjYzIDcgWiBNIDEzNyA3IEwgMjE4IDcgTCAyMTkgOSBMIDIxOCAxMCBMIDIxOSA5IEwgMjE4IDcgWiBNIDUyIDcgTCAxMzMgNyBMIDEzNCA4IEwgMTMyIDEwIEwgMTM0IDggTCAxMzQgNyBaIE0gNyA3IEwgNDcgNyBMIDQ4IDkgTCA0NyAxMCBMIDQ4IDkgTCA0NyA3IFoiIGZpbGw9IiM1MTUyNUEiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
      "2": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNzIiIGhlaWdodD0iODEiIHZpZXdCb3g9IjAgMCAyNzIgODEiPjxwYXRoIGQ9Ik0gMjcwIDAgTCAxIDEgTCAxIDc5IEwgMjcwIDc5IFogTSAxNzggNzEgTCAxODQgNjQgTCAxODQgNjIgTCAxODcgNjAgTCAxODcgNTggTCAxOTIgNTMgTCAxOTIgNTEgTCAxOTUgNDkgTCAxOTYgNDYgTCAyMDEgNDEgTCAyMDEgMzkgTCAyMTMgMjQgTCAyMTMgMjIgTCAyMTggMTggTCAyMTkgMTUgTCAyMjMgMTUgTCAyMjUgMTcgTCAyMjUgMTkgTCAyMzAgMjQgTCAyMzAgMjYgTCAyMzMgMjggTCAyMzUgMzIgTCAyMzkgMzYgTCAyMzkgMzggTCAyNDcgNDcgTCAyNDcgNDkgTCAyNTYgNTkgTCAyNTYgNjEgTCAyNjEgNjYgTCAyNjIgNjkgTCAyNjQgNzAgTCAyNjQgNzMgTCAyNjMgNzQgTCAxNzkgNzQgWiBNIDk0IDcwIEwgMTAyIDYwIEwgMTAyIDU4IEwgMTA3IDUzIEwgMTA3IDUxIEwgMTEwIDQ5IEwgMTExIDQ2IEwgMTE2IDQxIEwgMTE2IDM5IEwgMTE4IDM4IEwgMTE5IDM1IEwgMTI0IDMwIEwgMTI0IDI4IEwgMTI3IDI2IEwgMTI4IDIzIEwgMTMzIDE4IEwgMTMzIDE2IEwgMTM2IDE1IEwgMTM5IDE4IEwgMTM5IDIwIEwgMTQ0IDI0IEwgMTQ0IDI2IEwgMTQ4IDMwIEwgMTQ4IDMyIEwgMTUzIDM2IEwgMTUzIDM4IEwgMTU2IDQxIEwgMTU2IDQzIEwgMTYxIDQ3IEwgMTYxIDQ5IEwgMTY1IDUzIEwgMTY1IDU1IEwgMTcwIDU5IEwgMTcwIDYxIEwgMTc4IDcxIEwgMTc2IDczIEwgOTYgNzMgWiBNIDcgNzEgTCAxMyA2NCBMIDEzIDYyIEwgMTYgNjAgTCAxNiA1OCBMIDIxIDUzIEwgMjEgNTEgTCAyNCA0OSBMIDI1IDQ2IEwgMzAgNDEgTCAzMCAzOSBMIDQyIDI0IEwgNDIgMjIgTCA0NyAxOCBMIDQ4IDE1IEwgNTIgMTUgTCA1NCAxNyBMIDU0IDE5IEwgNTkgMjQgTCA1OSAyNiBMIDYyIDI4IEwgNjQgMzIgTCA2OCAzNiBMIDY4IDM4IEwgNzYgNDcgTCA3NiA0OSBMIDg1IDU5IEwgODUgNjEgTCA5MCA2NiBMIDkxIDY5IEwgOTMgNzAgTCA5MyA3MyBMIDkyIDc0IEwgOCA3NCBaIE0gMjIyIDYgTCAyMjQgNSBMIDI2MyA1IEwgMjY1IDcgTCAyNjUgNjQgTCAyNjQgNjUgTCAyNjIgNjUgTCAyNjEgNjQgTCAyNjEgNjIgTCAyNTYgNTcgTCAyNTUgNTQgTCAyNTIgNTIgTCAyNTIgNTAgTCAyNDggNDYgTCAyNDkgNDUgTCAyNDggNDUgTCAyNDYgNDIgTCAyNDQgNDEgTCAyNDQgMzkgTCAyMzkgMzQgTCAyMzggMzEgTCAyMzUgMjkgTCAyMzUgMjcgTCAyMzIgMjQgTCAyMzIgMjIgTCAyMzEgMjIgTCAyMzAgMjAgTCAyMjcgMTggTCAyMjcgMTYgTCAyMjIgMTEgTCAyMjIgOSBMIDIyMSA4IFogTSA1MCA3IEwgNTMgNSBMIDIxOCA1IEwgMjIxIDcgTCAyMjEgMTAgTCAxOTkgMzcgTCAxODcgNTYgTCAxNzcgNjUgTCAxMzUgOSBMIDEwNCA1MyBMIDkxIDY1IEwgNzggNDUgTCA2NCAyOSBMIDYxIDIyIEwgNTEgMTEgWiBNIDUwIDcgTCA1MCAxMCBMIDQ4IDExIEwgNDcgMTQgTCA0MiAxOSBMIDQyIDIxIEwgNDAgMjIgTCAzOCAyNSBMIDM3IDI1IEwgMzcgMjcgTCAzMyAzMSBMIDMzIDMzIEwgMzEgMzQgTCAyOSAzNyBMIDI4IDM3IEwgMjggMzkgTCAyNSA0MiBMIDI1IDQ0IEwgMjMgNDUgTCAyMSA0OCBMIDIwIDQ4IEwgMjAgNTAgTCAxNiA1NCBMIDE2IDU2IEwgMTQgNTcgTCAxNCA1OCBMIDggNjUgTCA2IDY1IEwgNSA2NCBMIDUgNyBMIDggNSBMIDQ3IDUgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA5NyA2OSBMIDk3IDcxIEwgMTc1IDcxIEwgMTc0IDY5IEwgMTcyIDY4IEwgMTcyIDY2IEwgMTY4IDYyIEwgMTY4IDYwIEwgMTYzIDU2IEwgMTYzIDU0IEwgMTU4IDQ5IEwgMTU3IDQ2IEwgMTUxIDM5IEwgMTUxIDM3IEwgMTQxIDI2IEwgMTQxIDI0IEwgMTM1IDE3IEwgMTM1IDE5IEwgMTI2IDI5IEwgMTI2IDMxIEwgMTIxIDM2IEwgMTIwIDM5IEwgMTE4IDQwIEwgMTE4IDQyIEwgMTE0IDQ2IEwgMTE0IDQ4IEwgMTA5IDUyIEwgMTA5IDU0IEwgMTA0IDU5IEwgMTA0IDYxIEwgMTAxIDYzIEwgMTAwIDY2IFogTSA5IDcyIEwgOTEgNzIgTCA5MSA3MSBMIDgzIDYyIEwgODMgNjAgTCA3NCA1MCBMIDc0IDQ4IEwgNjYgMzkgTCA2NiAzNyBMIDYxIDMyIEwgNjAgMjkgTCA1NyAyNyBMIDU3IDI1IEwgNTIgMjAgTCA1MiAxOCBMIDQ5IDE3IEwgNDkgMTkgTCA0NCAyMyBMIDQ0IDI1IEwgNDAgMjkgTCA0MCAzMSBMIDM4IDMyIEwgMzcgMzUgTCAzMiA0MCBMIDMyIDQyIEwgMjMgNTIgTCAyMyA1NCBMIDE1IDYzIEwgMTUgNjUgWiIgZmlsbD0iI0E2NjI0MSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxMDcgNTQgTCAxMDMgNTggTCAxMDMgNTkgTCAxMDMgNTggWiBNIDExNiA0MiBMIDExMiA0NiBMIDExMSA0OCBMIDExMiA0NiBaIE0gMjA2IDM0IEwgMjA2IDM1IEwgMjAyIDM5IEwgMjA2IDM1IFogTSAzNSAzNCBMIDM1IDM1IEwgMzEgMzkgTCAzNSAzNSBaIE0gMjM0IDMxIEwgMjM0IDMyIEwgMjM4IDM2IEwgMjM0IDMyIFogTSA2MyAzMSBMIDYzIDMyIEwgNjcgMzYgTCA2MyAzMiBaIE0gMTI0IDI0IEwgMTIwIDI4IEwgMTIwIDI5IEwgMTIwIDI4IFogTSAyMjMgMTAgTCAyMjMgMTEgTCAyMjcgMTUgTCAyMjMgMTEgWiBNIDUyIDEwIEwgNTIgMTEgTCA1NiAxNSBMIDUyIDExIFoiIGZpbGw9IiM5QzlEQUIiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMCA3OSBMIDEgMCBMIDI2OSAwIEwgMSAwIFoiIGZpbGw9IiM5RkExQUYiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMTAgNjAgTCAxMCA2MiBMIDggNjQgTCA3IDY0IEwgOCA2NCBMIDEwIDYyIFogTSAxNzQgNTkgTCAxNzQgNjAgTCAxNzggNjQgTCAxNzkgNjQgTCAxODEgNjIgTCAxODEgNjAgTCAxODEgNjIgTCAxNzkgNjQgTCAxNzggNjQgTCAxNzQgNjAgWiBNIDI1OCA1OCBMIDI2MiA2MiBMIDI2MiA2MyBMIDI2NCA2NCBMIDI2MyA2NCBMIDI2MiA2MiBaIE0gMTg4IDU4IEwgMTg4IDYwIEwgMTg1IDYzIEwgMTg1IDY0IEwgMTg1IDYzIEwgMTg4IDYwIFogTSA4NyA1OCBMIDkxIDYyIEwgOTEgNjMgTCA5MyA2NCBMIDkyIDY0IEwgOTEgNjIgWiBNIDE3IDU4IEwgMTcgNjAgTCAxNCA2MyBMIDE0IDY0IEwgMTQgNjMgTCAxNyA2MCBaIE0gMjUxIDU2IEwgMjU1IDYwIEwgMjU2IDYyIEwgMjU1IDYwIFogTSA4MCA1NiBMIDg0IDYwIEwgODUgNjIgTCA4NCA2MCBaIE0gMTY0IDUzIEwgMTY0IDU1IEwgMTY5IDYwIEwgMTY5IDYyIEwgMTY5IDYwIEwgMTY0IDU1IFogTSAxMDIgNTMgTCA5OCA1NyBMIDk4IDU5IEwgOTggNTcgWiBNIDE5MCA1MCBMIDE4NiA1NCBMIDE4NiA1NSBMIDE4NiA1NCBaIE0gMTkgNTAgTCAxNSA1NCBMIDE1IDU1IEwgMTUgNTQgWiBNIDExMiA0OCBMIDEwOCA1MiBMIDEwOCA1MyBMIDEwOCA1MiBaIE0gMTk3IDQ3IEwgMTk3IDQ4IEwgMTkzIDUyIEwgMTk3IDQ4IFogTSAyNiA0NyBMIDI2IDQ4IEwgMjIgNTIgTCAyNiA0OCBaIE0gMTY1IDQ2IEwgMTY1IDQ4IEwgMTY5IDUyIEwgMTY1IDQ4IFogTSAxMTAgNDIgTCAxMDcgNDUgTCAxMDcgNDcgTCAxMDcgNDUgWiBNIDE5NiA0MSBMIDE5NSA0MyBMIDE5MSA0NyBMIDE5NSA0MyBaIE0gMTU1IDQxIEwgMTU1IDQzIEwgMTU5IDQ3IEwgMTU1IDQzIFogTSAyNSA0MSBMIDI0IDQzIEwgMjAgNDcgTCAyNCA0MyBaIE0gMjAzIDM5IEwgMjAyIDQxIEwgMTk4IDQ1IEwgMjAyIDQxIFogTSAzMiAzOSBMIDMxIDQxIEwgMjcgNDUgTCAzMSA0MSBaIE0gMjQ0IDM4IEwgMjQ1IDQwIEwgMjQ5IDQ0IEwgMjQ1IDQwIFogTSA3MyAzOCBMIDc0IDQwIEwgNzggNDQgTCA3NCA0MCBaIE0gMjM4IDM3IEwgMjM4IDM4IEwgMjQyIDQyIEwgMjM4IDM4IFogTSA2NyAzNyBMIDY3IDM4IEwgNzEgNDIgTCA2NyAzOCBaIE0gMTIwIDM2IEwgMTIwIDM3IEwgMTE3IDQwIEwgMTE3IDQxIEwgMTE3IDQwIEwgMTIwIDM3IFogTSAxNTcgMzUgTCAxNTcgMzcgTCAxNjIgNDIgTCAxNjIgNDQgTCAxNjIgNDIgTCAxNTcgMzcgWiBNIDIwMiAzMyBMIDE5OCAzNyBMIDE5OCAzOSBMIDE5OCAzNyBaIE0gMTQ4IDMzIEwgMTUyIDM3IEwgMTUzIDM5IEwgMTUyIDM3IFogTSAzMSAzMyBMIDI3IDM3IEwgMjcgMzkgTCAyNyAzNyBaIE0gMTE5IDMwIEwgMTE1IDM0IEwgMTE1IDM1IEwgMTE1IDM0IFogTSAyMzYgMjcgTCAyMzYgMjggTCAyNDAgMzIgTCAyMzYgMjggWiBNIDY1IDI3IEwgNjUgMjggTCA2OSAzMiBMIDY1IDI4IFogTSAyMjkgMjUgTCAyMjkgMjYgTCAyMzMgMzAgTCAyMjkgMjYgWiBNIDEyOSAyNSBMIDEyNSAyOSBMIDEyNSAzMCBMIDEyNSAyOSBaIE0gNTggMjUgTCA1OCAyNiBMIDYyIDMwIEwgNTggMjYgWiBNIDE0OCAyMyBMIDE0OCAyNSBMIDE1MiAyOSBMIDE0OCAyNSBaIE0gMjEyIDE5IEwgMjEyIDIwIEwgMjA4IDI0IEwgMjEyIDIwIFogTSA0MSAxOSBMIDQxIDIwIEwgMzcgMjQgTCA0MSAyMCBaIE0gMTI3IDE4IEwgMTI3IDE5IEwgMTI0IDIyIEwgMTI0IDIzIEwgMTI0IDIyIEwgMTI3IDE5IFogTSAyMjggMTYgTCAyMjggMTcgTCAyMzIgMjEgTCAyMjggMTcgWiBNIDIyMCAxNiBMIDIxOSAxNiBMIDIxOSAxOCBMIDIxNCAyMyBMIDIxNCAyNSBMIDIxNCAyMyBMIDIxOSAxOCBaIE0gMTM1IDE2IEwgMTMzIDE5IEwgMTM0IDE3IEwgMTM2IDE2IEwgMTM4IDE4IEwgMTM4IDIwIEwgMTQyIDI0IEwgMTM4IDIwIEwgMTM4IDE4IEwgMTM2IDE2IFogTSA1NyAxNiBMIDU3IDE3IEwgNjEgMjEgTCA1NyAxNyBaIE0gNDkgMTYgTCA0OCAxNiBMIDQ4IDE4IEwgNDMgMjMgTCA0MyAyNSBMIDQzIDIzIEwgNDggMTggWiBNIDEzNSA3IEwgMTM1IDggTCAxMzYgOCBMIDE0MCAxMiBMIDEzNiA4IEwgMTM2IDcgWiIgZmlsbD0iIzg0ODY5MSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxOTMgNTMgTCAxOTMgNTQgTCAxODkgNTggTCAxOTMgNTQgWiBNIDIyIDUzIEwgMjIgNTQgTCAxOCA1OCBMIDIyIDU0IFogTSAxNzAgNTIgTCAxNzAgNTQgTCAxNzQgNTggTCAxNzAgNTQgWiBNIDI0NiA1MCBMIDI1MCA1NCBMIDI1MCA1NSBMIDI1MCA1NCBaIE0gNzUgNTAgTCA3OSA1NCBMIDc5IDU1IEwgNzkgNTQgWiBNIDE5MCA0OCBMIDE5MCA0OSBMIDE4NiA1MyBMIDE5MCA0OSBaIE0gMTkgNDggTCAxOSA0OSBMIDE1IDUzIEwgMTkgNDkgWiBNIDE1OCA0NyBMIDE1OSA0OSBMIDE2MyA1MyBMIDE1OSA0OSBaIE0gMTA2IDQ3IEwgMTAyIDUxIEwgMTAyIDUyIEwgMTAyIDUxIFogTSAyNTAgNDUgTCAyNTAgNDYgTCAyNTMgNDkgTCAyNTMgNTAgTCAyNTMgNDkgTCAyNTAgNDYgWiBNIDc5IDQ1IEwgNzkgNDYgTCA4MiA0OSBMIDgyIDUwIEwgODIgNDkgTCA3OSA0NiBaIE0gMTE3IDQyIEwgMTEzIDQ2IEwgMTEzIDQ4IEwgMTEzIDQ2IFogTSAxMTQgMzYgTCAxMTAgNDAgTCAxMTAgNDEgTCAxMTAgNDAgWiBNIDI0MSAzMyBMIDI0MSAzNCBMIDI0NSAzOCBMIDI0MSAzNCBaIE0gNzAgMzMgTCA3MCAzNCBMIDc0IDM4IEwgNzAgMzQgWiBNIDIwNyAyNSBMIDIwNyAyNiBMIDIwMyAzMCBMIDIwNyAyNiBaIE0gMTQ5IDI1IEwgMTUzIDI5IEwgMTUzIDMxIEwgMTUzIDI5IFogTSAxNDIgMjUgTCAxNDIgMjYgTCAxNDYgMzAgTCAxNDIgMjYgWiBNIDM2IDI1IEwgMzYgMjYgTCAzMiAzMCBMIDM2IDI2IFogTSAyMzMgMjEgTCAyMzMgMjMgTCAyMzYgMjYgTCAyMzMgMjMgWiBNIDYyIDIxIEwgNjIgMjMgTCA2NSAyNiBMIDYyIDIzIFogTSAyMjQgMTkgTCAyMjQgMjAgTCAyMjggMjQgTCAyMjQgMjAgWiBNIDEzNCAxOSBMIDEzMCAyMyBMIDEzMCAyNCBMIDEzMCAyMyBaIE0gNTMgMTkgTCA1MyAyMCBMIDU3IDI0IEwgNTMgMjAgWiBNIDQ1IDEzIEwgNDUgMTQgTCA0MSAxOCBMIDQ1IDE0IFogTSAyMTYgMTIgTCAyMTYgMTQgTCAyMTIgMTggTCAyMTYgMTQgWiBNIDIyNCAxMCBMIDIyNCAxMSBMIDIyOCAxNSBMIDIyNCAxMSBaIE0gNTMgMTAgTCA1MyAxMSBMIDU3IDE1IEwgNTMgMTEgWiBNIDIyMyA3IEwgMjYzIDcgTCAyNjQgOCBMIDI2NCA2MyBMIDI2NCA4IEwgMjYzIDcgWiBNIDEzNyA3IEwgMjE4IDcgTCAyMTkgOSBMIDIxOCAxMCBMIDIxOSA5IEwgMjE4IDcgWiBNIDUyIDcgTCAxMzMgNyBMIDEzNCA4IEwgMTMyIDEwIEwgMTM0IDggTCAxMzQgNyBaIE0gNyA3IEwgNDcgNyBMIDQ4IDkgTCA0NyAxMCBMIDQ4IDkgTCA0NyA3IFoiIGZpbGw9IiM1MTUyNUEiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
      "3": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNzIiIGhlaWdodD0iODEiIHZpZXdCb3g9IjAgMCAyNzIgODEiPjxwYXRoIGQ9Ik0gMTgwIDcyIEwgMjYyIDcyIEwgMjYyIDcxIEwgMjU0IDYyIEwgMjU0IDYwIEwgMjQ1IDUwIEwgMjQ1IDQ4IEwgMjM3IDM5IEwgMjM3IDM3IEwgMjMyIDMyIEwgMjMxIDI5IEwgMjI4IDI3IEwgMjI4IDI1IEwgMjIzIDIwIEwgMjIzIDE4IEwgMjIwIDE3IEwgMjIwIDE5IEwgMjE1IDIzIEwgMjE1IDI1IEwgMjExIDI5IEwgMjExIDMxIEwgMjA5IDMyIEwgMjA4IDM1IEwgMjAzIDQwIEwgMjAzIDQyIEwgMTk0IDUyIEwgMTk0IDU0IEwgMTg2IDYzIEwgMTg2IDY1IFogTSA5NyA2OSBMIDk3IDcxIEwgMTc1IDcxIEwgMTc0IDY5IEwgMTcyIDY4IEwgMTcyIDY2IEwgMTY4IDYyIEwgMTY4IDYwIEwgMTYzIDU2IEwgMTYzIDU0IEwgMTU4IDQ5IEwgMTU3IDQ2IEwgMTUxIDM5IEwgMTUxIDM3IEwgMTQxIDI2IEwgMTQxIDI0IEwgMTM1IDE3IEwgMTM1IDE5IEwgMTI2IDI5IEwgMTI2IDMxIEwgMTIxIDM2IEwgMTIwIDM5IEwgMTE4IDQwIEwgMTE4IDQyIEwgMTE0IDQ2IEwgMTE0IDQ4IEwgMTA5IDUyIEwgMTA5IDU0IEwgMTA0IDU5IEwgMTA0IDYxIEwgMTAxIDYzIEwgMTAwIDY2IFogTSA5IDcyIEwgOTEgNzIgTCA5MSA3MSBMIDgzIDYyIEwgODMgNjAgTCA3NCA1MCBMIDc0IDQ4IEwgNjYgMzkgTCA2NiAzNyBMIDYxIDMyIEwgNjAgMjkgTCA1NyAyNyBMIDU3IDI1IEwgNTIgMjAgTCA1MiAxOCBMIDQ5IDE3IEwgNDkgMTkgTCA0NCAyMyBMIDQ0IDI1IEwgNDAgMjkgTCA0MCAzMSBMIDM4IDMyIEwgMzcgMzUgTCAzMiA0MCBMIDMyIDQyIEwgMjMgNTIgTCAyMyA1NCBMIDE1IDYzIEwgMTUgNjUgWiIgZmlsbD0iI0E2NjI0MSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAyNzAgMCBMIDEgMSBMIDEgNzkgTCAyNzAgNzkgWiBNIDE3OCA3MSBMIDE4NCA2NCBMIDE4NCA2MiBMIDE4NyA2MCBMIDE4NyA1OCBMIDE5MiA1MyBMIDE5MiA1MSBMIDE5NSA0OSBMIDE5NiA0NiBMIDIwMSA0MSBMIDIwMSAzOSBMIDIxMyAyNCBMIDIxMyAyMiBMIDIxOCAxOCBMIDIxOSAxNSBMIDIyMyAxNSBMIDIyNSAxNyBMIDIyNSAxOSBMIDIzMCAyNCBMIDIzMCAyNiBMIDIzMyAyOCBMIDIzNSAzMiBMIDIzOSAzNiBMIDIzOSAzOCBMIDI0NyA0NyBMIDI0NyA0OSBMIDI1NiA1OSBMIDI1NiA2MSBMIDI2MSA2NiBMIDI2MiA2OSBMIDI2NCA3MCBMIDI2NCA3MyBMIDI2MyA3NCBMIDE3OSA3NCBaIE0gOTQgNzAgTCAxMDIgNjAgTCAxMDIgNTggTCAxMDcgNTMgTCAxMDcgNTEgTCAxMTAgNDkgTCAxMTEgNDYgTCAxMTYgNDEgTCAxMTYgMzkgTCAxMTggMzggTCAxMTkgMzUgTCAxMjQgMzAgTCAxMjQgMjggTCAxMjcgMjYgTCAxMjggMjMgTCAxMzMgMTggTCAxMzMgMTYgTCAxMzYgMTUgTCAxMzkgMTggTCAxMzkgMjAgTCAxNDQgMjQgTCAxNDQgMjYgTCAxNDggMzAgTCAxNDggMzIgTCAxNTMgMzYgTCAxNTMgMzggTCAxNTYgNDEgTCAxNTYgNDMgTCAxNjEgNDcgTCAxNjEgNDkgTCAxNjUgNTMgTCAxNjUgNTUgTCAxNzAgNTkgTCAxNzAgNjEgTCAxNzggNzEgTCAxNzYgNzMgTCA5NiA3MyBaIE0gNyA3MSBMIDEzIDY0IEwgMTMgNjIgTCAxNiA2MCBMIDE2IDU4IEwgMjEgNTMgTCAyMSA1MSBMIDI0IDQ5IEwgMjUgNDYgTCAzMCA0MSBMIDMwIDM5IEwgNDIgMjQgTCA0MiAyMiBMIDQ3IDE4IEwgNDggMTUgTCA1MiAxNSBMIDU0IDE3IEwgNTQgMTkgTCA1OSAyNCBMIDU5IDI2IEwgNjIgMjggTCA2NCAzMiBMIDY4IDM2IEwgNjggMzggTCA3NiA0NyBMIDc2IDQ5IEwgODUgNTkgTCA4NSA2MSBMIDkwIDY2IEwgOTEgNjkgTCA5MyA3MCBMIDkzIDczIEwgOTIgNzQgTCA4IDc0IFogTSAyMjIgNiBMIDIyNCA1IEwgMjYzIDUgTCAyNjUgNyBMIDI2NSA2NCBMIDI2NCA2NSBMIDI2MiA2NSBMIDI2MSA2NCBMIDI2MSA2MiBMIDI1NiA1NyBMIDI1NSA1NCBMIDI1MiA1MiBMIDI1MiA1MCBMIDI0OCA0NiBMIDI0OSA0NSBMIDI0OCA0NSBMIDI0NiA0MiBMIDI0NCA0MSBMIDI0NCAzOSBMIDIzOSAzNCBMIDIzOCAzMSBMIDIzNSAyOSBMIDIzNSAyNyBMIDIzMiAyNCBMIDIzMiAyMiBMIDIzMSAyMiBMIDIzMCAyMCBMIDIyNyAxOCBMIDIyNyAxNiBMIDIyMiAxMSBMIDIyMiA5IEwgMjIxIDggWiBNIDUwIDcgTCA1MyA1IEwgMjE4IDUgTCAyMjEgNyBMIDIyMSAxMCBMIDE5OSAzNyBMIDE4NyA1NiBMIDE3NyA2NSBMIDEzNSA5IEwgMTA0IDUzIEwgOTEgNjUgTCA3OCA0NSBMIDY0IDI5IEwgNjEgMjIgTCA1MSAxMSBaIE0gNTAgNyBMIDUwIDEwIEwgNDggMTEgTCA0NyAxNCBMIDQyIDE5IEwgNDIgMjEgTCA0MCAyMiBMIDM4IDI1IEwgMzcgMjUgTCAzNyAyNyBMIDMzIDMxIEwgMzMgMzMgTCAzMSAzNCBMIDI5IDM3IEwgMjggMzcgTCAyOCAzOSBMIDI1IDQyIEwgMjUgNDQgTCAyMyA0NSBMIDIxIDQ4IEwgMjAgNDggTCAyMCA1MCBMIDE2IDU0IEwgMTYgNTYgTCAxNCA1NyBMIDE0IDU4IEwgOCA2NSBMIDYgNjUgTCA1IDY0IEwgNSA3IEwgOCA1IEwgNDcgNSBaIiBmaWxsPSIjQTZBOEI2IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDEwNyA1NCBMIDEwMyA1OCBMIDEwMyA1OSBMIDEwMyA1OCBaIE0gMTE2IDQyIEwgMTEyIDQ2IEwgMTExIDQ4IEwgMTEyIDQ2IFogTSAyMDYgMzQgTCAyMDYgMzUgTCAyMDIgMzkgTCAyMDYgMzUgWiBNIDM1IDM0IEwgMzUgMzUgTCAzMSAzOSBMIDM1IDM1IFogTSAyMzQgMzEgTCAyMzQgMzIgTCAyMzggMzYgTCAyMzQgMzIgWiBNIDYzIDMxIEwgNjMgMzIgTCA2NyAzNiBMIDYzIDMyIFogTSAxMjQgMjQgTCAxMjAgMjggTCAxMjAgMjkgTCAxMjAgMjggWiBNIDIyMyAxMCBMIDIyMyAxMSBMIDIyNyAxNSBMIDIyMyAxMSBaIE0gNTIgMTAgTCA1MiAxMSBMIDU2IDE1IEwgNTIgMTEgWiIgZmlsbD0iIzlDOURBQiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAwIDc5IEwgMSAwIEwgMjY5IDAgTCAxIDAgWiIgZmlsbD0iIzlGQTFBRiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSAxMCA2MCBMIDEwIDYyIEwgOCA2NCBMIDcgNjQgTCA4IDY0IEwgMTAgNjIgWiBNIDE3NCA1OSBMIDE3NCA2MCBMIDE3OCA2NCBMIDE3OSA2NCBMIDE4MSA2MiBMIDE4MSA2MCBMIDE4MSA2MiBMIDE3OSA2NCBMIDE3OCA2NCBMIDE3NCA2MCBaIE0gMjU4IDU4IEwgMjYyIDYyIEwgMjYyIDYzIEwgMjY0IDY0IEwgMjYzIDY0IEwgMjYyIDYyIFogTSAxODggNTggTCAxODggNjAgTCAxODUgNjMgTCAxODUgNjQgTCAxODUgNjMgTCAxODggNjAgWiBNIDg3IDU4IEwgOTEgNjIgTCA5MSA2MyBMIDkzIDY0IEwgOTIgNjQgTCA5MSA2MiBaIE0gMTcgNTggTCAxNyA2MCBMIDE0IDYzIEwgMTQgNjQgTCAxNCA2MyBMIDE3IDYwIFogTSAyNTEgNTYgTCAyNTUgNjAgTCAyNTYgNjIgTCAyNTUgNjAgWiBNIDgwIDU2IEwgODQgNjAgTCA4NSA2MiBMIDg0IDYwIFogTSAxNjQgNTMgTCAxNjQgNTUgTCAxNjkgNjAgTCAxNjkgNjIgTCAxNjkgNjAgTCAxNjQgNTUgWiBNIDEwMiA1MyBMIDk4IDU3IEwgOTggNTkgTCA5OCA1NyBaIE0gMTkwIDUwIEwgMTg2IDU0IEwgMTg2IDU1IEwgMTg2IDU0IFogTSAxOSA1MCBMIDE1IDU0IEwgMTUgNTUgTCAxNSA1NCBaIE0gMTEyIDQ4IEwgMTA4IDUyIEwgMTA4IDUzIEwgMTA4IDUyIFogTSAxOTcgNDcgTCAxOTcgNDggTCAxOTMgNTIgTCAxOTcgNDggWiBNIDI2IDQ3IEwgMjYgNDggTCAyMiA1MiBMIDI2IDQ4IFogTSAxNjUgNDYgTCAxNjUgNDggTCAxNjkgNTIgTCAxNjUgNDggWiBNIDExMCA0MiBMIDEwNyA0NSBMIDEwNyA0NyBMIDEwNyA0NSBaIE0gMTk2IDQxIEwgMTk1IDQzIEwgMTkxIDQ3IEwgMTk1IDQzIFogTSAxNTUgNDEgTCAxNTUgNDMgTCAxNTkgNDcgTCAxNTUgNDMgWiBNIDI1IDQxIEwgMjQgNDMgTCAyMCA0NyBMIDI0IDQzIFogTSAyMDMgMzkgTCAyMDIgNDEgTCAxOTggNDUgTCAyMDIgNDEgWiBNIDMyIDM5IEwgMzEgNDEgTCAyNyA0NSBMIDMxIDQxIFogTSAyNDQgMzggTCAyNDUgNDAgTCAyNDkgNDQgTCAyNDUgNDAgWiBNIDczIDM4IEwgNzQgNDAgTCA3OCA0NCBMIDc0IDQwIFogTSAyMzggMzcgTCAyMzggMzggTCAyNDIgNDIgTCAyMzggMzggWiBNIDY3IDM3IEwgNjcgMzggTCA3MSA0MiBMIDY3IDM4IFogTSAxMjAgMzYgTCAxMjAgMzcgTCAxMTcgNDAgTCAxMTcgNDEgTCAxMTcgNDAgTCAxMjAgMzcgWiBNIDE1NyAzNSBMIDE1NyAzNyBMIDE2MiA0MiBMIDE2MiA0NCBMIDE2MiA0MiBMIDE1NyAzNyBaIE0gMjAyIDMzIEwgMTk4IDM3IEwgMTk4IDM5IEwgMTk4IDM3IFogTSAxNDggMzMgTCAxNTIgMzcgTCAxNTMgMzkgTCAxNTIgMzcgWiBNIDMxIDMzIEwgMjcgMzcgTCAyNyAzOSBMIDI3IDM3IFogTSAxMTkgMzAgTCAxMTUgMzQgTCAxMTUgMzUgTCAxMTUgMzQgWiBNIDIzNiAyNyBMIDIzNiAyOCBMIDI0MCAzMiBMIDIzNiAyOCBaIE0gNjUgMjcgTCA2NSAyOCBMIDY5IDMyIEwgNjUgMjggWiBNIDIyOSAyNSBMIDIyOSAyNiBMIDIzMyAzMCBMIDIyOSAyNiBaIE0gMTI5IDI1IEwgMTI1IDI5IEwgMTI1IDMwIEwgMTI1IDI5IFogTSA1OCAyNSBMIDU4IDI2IEwgNjIgMzAgTCA1OCAyNiBaIE0gMTQ4IDIzIEwgMTQ4IDI1IEwgMTUyIDI5IEwgMTQ4IDI1IFogTSAyMTIgMTkgTCAyMTIgMjAgTCAyMDggMjQgTCAyMTIgMjAgWiBNIDQxIDE5IEwgNDEgMjAgTCAzNyAyNCBMIDQxIDIwIFogTSAxMjcgMTggTCAxMjcgMTkgTCAxMjQgMjIgTCAxMjQgMjMgTCAxMjQgMjIgTCAxMjcgMTkgWiBNIDIyOCAxNiBMIDIyOCAxNyBMIDIzMiAyMSBMIDIyOCAxNyBaIE0gMjIwIDE2IEwgMjE5IDE2IEwgMjE5IDE4IEwgMjE0IDIzIEwgMjE0IDI1IEwgMjE0IDIzIEwgMjE5IDE4IFogTSAxMzUgMTYgTCAxMzMgMTkgTCAxMzQgMTcgTCAxMzYgMTYgTCAxMzggMTggTCAxMzggMjAgTCAxNDIgMjQgTCAxMzggMjAgTCAxMzggMTggTCAxMzYgMTYgWiBNIDU3IDE2IEwgNTcgMTcgTCA2MSAyMSBMIDU3IDE3IFogTSA0OSAxNiBMIDQ4IDE2IEwgNDggMTggTCA0MyAyMyBMIDQzIDI1IEwgNDMgMjMgTCA0OCAxOCBaIE0gMTM1IDcgTCAxMzUgOCBMIDEzNiA4IEwgMTQwIDEyIEwgMTM2IDggTCAxMzYgNyBaIiBmaWxsPSIjODQ4NjkxIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDE5MyA1MyBMIDE5MyA1NCBMIDE4OSA1OCBMIDE5MyA1NCBaIE0gMjIgNTMgTCAyMiA1NCBMIDE4IDU4IEwgMjIgNTQgWiBNIDE3MCA1MiBMIDE3MCA1NCBMIDE3NCA1OCBMIDE3MCA1NCBaIE0gMjQ2IDUwIEwgMjUwIDU0IEwgMjUwIDU1IEwgMjUwIDU0IFogTSA3NSA1MCBMIDc5IDU0IEwgNzkgNTUgTCA3OSA1NCBaIE0gMTkwIDQ4IEwgMTkwIDQ5IEwgMTg2IDUzIEwgMTkwIDQ5IFogTSAxOSA0OCBMIDE5IDQ5IEwgMTUgNTMgTCAxOSA0OSBaIE0gMTU4IDQ3IEwgMTU5IDQ5IEwgMTYzIDUzIEwgMTU5IDQ5IFogTSAxMDYgNDcgTCAxMDIgNTEgTCAxMDIgNTIgTCAxMDIgNTEgWiBNIDI1MCA0NSBMIDI1MCA0NiBMIDI1MyA0OSBMIDI1MyA1MCBMIDI1MyA0OSBMIDI1MCA0NiBaIE0gNzkgNDUgTCA3OSA0NiBMIDgyIDQ5IEwgODIgNTAgTCA4MiA0OSBMIDc5IDQ2IFogTSAxMTcgNDIgTCAxMTMgNDYgTCAxMTMgNDggTCAxMTMgNDYgWiBNIDExNCAzNiBMIDExMCA0MCBMIDExMCA0MSBMIDExMCA0MCBaIE0gMjQxIDMzIEwgMjQxIDM0IEwgMjQ1IDM4IEwgMjQxIDM0IFogTSA3MCAzMyBMIDcwIDM0IEwgNzQgMzggTCA3MCAzNCBaIE0gMjA3IDI1IEwgMjA3IDI2IEwgMjAzIDMwIEwgMjA3IDI2IFogTSAxNDkgMjUgTCAxNTMgMjkgTCAxNTMgMzEgTCAxNTMgMjkgWiBNIDE0MiAyNSBMIDE0MiAyNiBMIDE0NiAzMCBMIDE0MiAyNiBaIE0gMzYgMjUgTCAzNiAyNiBMIDMyIDMwIEwgMzYgMjYgWiBNIDIzMyAyMSBMIDIzMyAyMyBMIDIzNiAyNiBMIDIzMyAyMyBaIE0gNjIgMjEgTCA2MiAyMyBMIDY1IDI2IEwgNjIgMjMgWiBNIDIyNCAxOSBMIDIyNCAyMCBMIDIyOCAyNCBMIDIyNCAyMCBaIE0gMTM0IDE5IEwgMTMwIDIzIEwgMTMwIDI0IEwgMTMwIDIzIFogTSA1MyAxOSBMIDUzIDIwIEwgNTcgMjQgTCA1MyAyMCBaIE0gNDUgMTMgTCA0NSAxNCBMIDQxIDE4IEwgNDUgMTQgWiBNIDIxNiAxMiBMIDIxNiAxNCBMIDIxMiAxOCBMIDIxNiAxNCBaIE0gMjI0IDEwIEwgMjI0IDExIEwgMjI4IDE1IEwgMjI0IDExIFogTSA1MyAxMCBMIDUzIDExIEwgNTcgMTUgTCA1MyAxMSBaIE0gMjIzIDcgTCAyNjMgNyBMIDI2NCA4IEwgMjY0IDYzIEwgMjY0IDggTCAyNjMgNyBaIE0gMTM3IDcgTCAyMTggNyBMIDIxOSA5IEwgMjE4IDEwIEwgMjE5IDkgTCAyMTggNyBaIE0gNTIgNyBMIDEzMyA3IEwgMTM0IDggTCAxMzIgMTAgTCAxMzQgOCBMIDEzNCA3IFogTSA3IDcgTCA0NyA3IEwgNDggOSBMIDQ3IDEwIEwgNDggOSBMIDQ3IDcgWiIgZmlsbD0iIzUxNTI1QSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+
    style:
      left: 59.5%
      top: 50%
      width: 20.04%
    tap_action:
      action: none
  - type: conditional
    conditions:
      - entity: sensor.dantherm_operation_mode
        state_not: "6"
    elements:
      - type: image
        entity: cover.dantherm_bypass_damper
        state_image:
          closed: &dantherm2 data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDgxIiBoZWlnaHQ9IjI5OCIgdmlld0JveD0iMCAwIDEwODEgMjk4Ij48cGF0aCBkPSJNIDQgMiBMIDY2IDY0IEwgNCAxMjkgTCAzMzQgMTMwIEwgMzMzIDE2OCBMIDY2IDE2OCBMIDMgMjMyIEwgNjcgMjk2IEwgNDEzIDI5NiBMIDU0MCAyMTUgTCA2NjkgMjk1IEwgMTAxNiAyOTUgTCAxMDc4IDIzNCBMIDEwMTUgMTY4IEwgNzQ4IDE2NiBMIDc1MCAxMzAgTCAxMDgwIDEzMCBMIDEwMTYgNjYgTCAxMDc4IDIgTCA2NzIgMiBMIDU0MiA4NSBMIDQxMiAyIFogTSA1MzEgMjA3IEwgNDEzIDI4NCBMIDY5IDI4NCBMIDE4IDIzMiBMIDcwIDE3OSBMIDQxMiAxNzkgTCA0NDkgMTU1IFogTSA2NDQgMTQ5IEwgNjUwIDE0NCBMIDY1MiAxNDQgTCA2NTUgMTQxIEwgNjU5IDE0MCBMIDY2MiAxMzcgTCA2NjcgMTM1IEwgNjc0IDEzMCBMIDczMyAxMzAgTCA3MzUgMTMzIEwgNzM1IDE2NiBMIDczMyAxNjggTCA2NzEgMTY4IEwgNjY0IDE2NCBMIDY2MyAxNjIgTCA2NjEgMTYyIEwgNjU4IDE1OSBMIDY1NiAxNTkgTCA2NTUgMTU3IEwgNjQ3IDE1MyBaIE0gMzQ4IDEzMCBMIDM0OSAxMjkgTCA0MTEgMTI5IEwgNDE0IDEzMiBMIDQxNiAxMzIgTCA0MTkgMTM1IEwgNDMwIDE0MSBMIDQzMSAxNDMgTCA0MzMgMTQzIEwgNDM5IDE0OCBMIDQzOSAxNTAgTCA0MjIgMTYwIEwgNDE2IDE2NSBMIDQxNCAxNjUgTCA0MTEgMTY4IEwgMzQ5IDE2OCBMIDM0OCAxNjcgWiBNIDU1NCA5MSBMIDY3NSAxMyBMIDEwNTAgMTQgTCAxMDAxIDY1IEwgMTA0OSAxMTcgTCA2NzUgMTE3IEwgNjMwIDE0MiBaIE0gMzEgMTQgTCA0MTEgMTMgTCA2NjggMTc4IEwgMTAxNCAxNzkgTCAxMDY0IDIzNSBMIDEwMTUgMjg0IEwgNjcwIDI4NCBMIDQxMSAxMTcgTCAzMiAxMTcgTCA4MCA2NSBaIiBmaWxsPSIjQTZBOEI2IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDUxMiAyMjAgTCA1MTEgMjIwIEwgNTA4IDIyMyBMIDUxMSAyMjAgWiBNIDUwMiAxODggTCA1MDUgMTkxIEwgNTA2IDE5MSBMIDUwNSAxOTEgWiBNIDY2MSAxNzQgTCA2NjIgMTc0IEwgNjY1IDE3NyBMIDY2NiAxNzcgTCA2NjUgMTc3IEwgNjYyIDE3NCBaIE0gNDUzIDE1NyBMIDQ1NCAxNTcgTCA0NTcgMTYwIEwgNDU4IDE2MCBMIDQ1NyAxNjAgTCA0NTQgMTU3IFogTSA2NDYgMTQ4IEwgNjQ1IDE1MCBMIDY0NyAxNTIgTCA2NDUgMTUwIFogTSA2MDQgMTM3IEwgNjA1IDEzNyBMIDYwOCAxNDAgTCA2MDkgMTQwIEwgNjA4IDE0MCBMIDYwNSAxMzcgWiBNIDU2NiAxMDAgTCA1NjcgMTAwIEwgNTcwIDEwMyBMIDU3MSAxMDMgTCA1NzAgMTAzIEwgNTY3IDEwMCBaIE0gNTEwIDc3IEwgNTExIDc3IEwgNTE0IDgwIEwgNTE1IDgwIEwgNTE0IDgwIEwgNTExIDc3IFogTSA1NzkgNzQgTCA1NzYgNzcgTCA1NzUgNzcgTCA1NzYgNzcgWiIgZmlsbD0iIzlCOURBQiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA5NTEgMTMyIEwgOTUxIDE2NiBMIDk2OSAxNjYgTCA5NjkgMTMyIFoiIGZpbGw9IiNDODhENEQiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
          closing: *dantherm2
          open: &dantherm3 data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDgxIiBoZWlnaHQ9IjI5OCIgdmlld0JveD0iMCAwIDEwODEgMjk4Ij48cGF0aCBkPSJNIDQgMiBMIDY2IDY0IEwgNCAxMjkgTCAzMzQgMTMwIEwgMzMzIDE2OCBMIDY2IDE2OCBMIDMgMjMxIEwgNjYgMjk1IEwgMTA3NyAyOTUgTCAxMDE1IDIzMyBMIDEwNzcgMTY4IEwgNzQ4IDE2NiBMIDc1MCAxMjkgTCAxMDE1IDEyOSBMIDEwNzggNjYgTCAxMDE1IDIgWiBNIDE4IDIzMSBMIDcwIDE3OSBMIDEwNDggMTc5IEwgMTAwMSAyMzIgTCAxMDUwIDI4MyBMIDY5IDI4NCBaIE0gMzQ4IDEzMCBMIDczMyAxMjkgTCA3MzUgMTY2IEwgMzQ5IDE2OCBaIE0gMzEgMTQgTCAxMDEyIDEzIEwgMTA2MyA2NiBMIDEwMTIgMTE3IEwgMzIgMTE3IEwgODAgNjUgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA5NTIgMTMxIEwgOTUyIDE2NiBMIDk2OCAxNjYgTCA5NjggMTMxIFoiIGZpbGw9IiNDODhDNEQiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
          opening: *dantherm3
        style:
          left: 59.4%
          top: 74.35%
          width: 79.66%
        tap_action:
          action: more-info
      - type: conditional
        conditions:
          - entity: cover.dantherm_bypass_damper
            state:
              - closed
              - closing
        elements:
          - type: state-label
            entity: sensor.dantherm_outdoor_temperature
            style:
              top: 66%
              left: 83%
          - type: state-label
            entity: sensor.dantherm_extract_temperature
            style:
              top: 66%
              left: 35%
          - type: state-label
            entity: sensor.dantherm_exhaust_temperature
            style:
              top: 83%
              left: 83%
          - type: state-label
            entity: sensor.dantherm_supply_temperature
            style:
              top: 83%
              left: 35%
      - type: conditional
        conditions:
          - entity: cover.dantherm_bypass_damper
            state:
              - open
              - opening
        elements:
          - type: state-label
            entity: sensor.dantherm_extract_temperature
            style:
              top: 66%
              left: 35%
          - type: state-label
            entity: sensor.dantherm_outdoor_temperature
            style:
              top: 83%
              left: 83%
  - type: conditional
    conditions:
      - entity: sensor.dantherm_operation_mode
        state: "6"
    elements:
      - type: image
        image: data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDgxIiBoZWlnaHQ9IjI5OCIgdmlld0JveD0iMCAwIDEwODEgMjk4Ij48cGF0aCBkPSJNIDQgMiBMIDY2IDY0IEwgNCAxMjkgTCAzMzMgMTI5IEwgMzM0IDI5NyBMIDM0OCAyOTcgTCAzNDkgMTI5IEwgNzMzIDEyOSBMIDczNSAyOTcgTCA3NDggMjk3IEwgNzUwIDEyOSBMIDEwMTUgMTI5IEwgMTA3OCA2NiBMIDEwMTUgMiBaIE0gMzEgMTQgTCAxMDEyIDEzIEwgMTA2MyA2NiBMIDEwMTIgMTE3IEwgMzIgMTE3IEwgODAgNjUgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA5NTIgMTMxIEwgOTUyIDI5NyBMIDk2OCAyOTcgTCA5NjggMTMxIFoiIGZpbGw9IiNDODhENEQiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
        style:
          left: 59.4%
          top: 74.35%
          width: 79.66%
        tap_action:
          action: none
      - type: state-label
        entity: sensor.dantherm_extract_temperature
        style:
          top: 65.5%
          left: 35%
  - type: conditional
    conditions:
      - entity: sensor.dantherm_alarm
        state_not: "0"
    elements:
      - type: state-label
        entity: sensor.dantherm_alarm
        style:
          top: 15%
          left: 50%
          width: 100%
          font-weight: bold
          text-align: center
          color: white
          background-color: red
          opacity: 70%
  - type: state-label
    entity: select.dantherm_operation_selection
    style:
      top: 47%
      left: 25.5%
      # font-size: 125%
  - type: state-label
    entity: select.dantherm_fan_selection
    style:
      top: 29%
      left: 60%
      # font-size: 125%
      transform: translate(0%,-50%)
#  - type: image
#    entity: sensor.dantherm_humidity_level
#    state_image:
#      "0": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1MSIgaGVpZ2h0PSI3NCIgdmlld0JveD0iMCAwIDUxIDc0Ij48cGF0aCBkPSJNIDI2IDEgTCAyMCA1IEwgMTMgMTUgTCAxMiAxOCBMIDEwIDIwIEwgOCAyNSBMIDUgMjkgTCA1IDMxIEwgMiAzNyBMIDIgNDEgTCAxIDQyIEwgMSA1NCBMIDIgNTUgTCAyIDU4IEwgNCA2MCBMIDUgNjMgTCAxMiA2OSBMIDIzIDczIEwgMzQgNzMgTCAzNyA3MSBMIDQxIDcwIEwgNDcgNjMgTCA0NyA2MSBMIDUwIDU0IEwgNTAgNDQgTCA0OSA0MyBMIDQ5IDM5IEwgNDggMzggTCA0NyAzMiBMIDQxIDE5IEwgMzAgMyBaIE0gMjQgNiBMIDI3IDYgTCAzMCA5IEwgMzAgMTAgTCAzOCAyMSBMIDM4IDIzIEwgNDAgMjUgTCA0NSAzNSBMIDQ1IDM4IEwgNDYgMzkgTCA0NiA0MiBMIDQ3IDQzIEwgNDcgNDggTCA0OCA0OSBMIDQ3IDUxIEwgNDcgNTUgTCA0NiA1NiBMIDQ1IDYwIEwgMzggNjcgTCAzNCA2OCBMIDMzIDY5IEwgMzEgNjkgTCAzMCA3MCBMIDIzIDcwIEwgMTQgNjYgTCA4IDYxIEwgNCA1NCBMIDQgNDEgTCA2IDM4IEwgNiAzNiBMIDggMzMgTCA4IDMxIEwgMTEgMjcgTCAxMSAyNSBMIDEzIDIzIEwgMTQgMjAgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+
#      "1": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1MSIgaGVpZ2h0PSI3NCIgdmlld0JveD0iMCAwIDUxIDc0Ij48cGF0aCBkPSJNIDI2IDEgTCAyMCA1IEwgMTMgMTUgTCAxMiAxOCBMIDEwIDIwIEwgOCAyNSBMIDUgMjkgTCA1IDMxIEwgMiAzNyBMIDIgNDEgTCAxIDQyIEwgMSA1NCBMIDIgNTUgTCAyIDU4IEwgNCA2MCBMIDUgNjMgTCAxMiA2OSBMIDIzIDczIEwgMzQgNzMgTCAzNyA3MSBMIDQxIDcwIEwgNDcgNjMgTCA0NyA2MSBMIDUwIDU0IEwgNTAgNDQgTCA0OSA0MyBMIDQ5IDM5IEwgNDggMzggTCA0NyAzMiBMIDQxIDE5IEwgMzAgMyBaIE0gMjQgNiBMIDI3IDYgTCAzMCA5IEwgMzAgMTAgTCAzOCAyMSBMIDM4IDIzIEwgNDAgMjUgTCA0NSAzNSBMIDQ1IDM4IEwgNDYgMzkgTCA0NiA0MiBMIDQ3IDQzIEwgNDcgNDggTCA0OCA0OSBMIDQ3IDUxIEwgNDcgNTUgTCA0NiA1NiBMIDQ1IDYwIEwgMzggNjcgTCAzNCA2OCBMIDMzIDY5IEwgMzEgNjkgTCAzMCA3MCBMIDIzIDcwIEwgMTQgNjYgTCA4IDYxIEwgNCA1NCBMIDQgNDEgTCA2IDM4IEwgNiAzNiBMIDggMzMgTCA4IDMxIEwgMTEgMjcgTCAxMSAyNSBMIDEzIDIzIEwgMTQgMjAgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA4IDQyIEwgOCA1MiBMIDExIDU2IEwgMTIgNTkgTCAxNCA2MSBMIDE4IDYzIEwgMjEgNjMgTCAyMiA2NCBMIDMzIDY0IEwgMzQgNjMgTCAzNiA2MyBMIDQxIDU4IEwgNDEgNTYgTCA0MCA1NSBMIDMzIDUyIEwgMzEgNTAgTCAzMCA1MSBMIDI5IDQ5IEwgMjggNTAgTCAyNyA0OCBMIDI2IDQ5IEwgMjIgNDYgTCAyMSA0NyBMIDIwIDQ1IEwgMTkgNDYgTCAxNSA0MyBMIDE0IDQ0IEwgMTMgNDIgTCAxMSA0MiBMIDEwIDQxIFoiIGZpbGw9IiNBQUE4RkEiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
#      "2": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1MSIgaGVpZ2h0PSI3NCIgdmlld0JveD0iMCAwIDUxIDc0Ij48cGF0aCBkPSJNIDggNDMgTCA4IDUwIEwgOSA1MSBMIDkgNTMgTCAxMiA1NyBMIDEyIDU4IEwgMTQgNjAgTCAxNSA2MCBMIDE2IDYyIEwgMTkgNjIgTCAyMiA2NCBMIDMzIDY0IEwgMzUgNjIgTCAzNyA2MiBMIDM4IDYwIEwgNDAgNTggTCA0MSA1OCBMIDQxIDU2IEwgMzYgNTQgTCAzNCA1MiBMIDMyIDUyIEwgMjAgNDYgTCAxOCA0NiBMIDE1IDQ0IEwgMTMgNDQgTCAxMiA0MiBMIDExIDQzIEwgMTAgNDIgWiBNIDE2IDI1IEwgMTEgMzQgTCAxMSAzNyBMIDEzIDM3IEwgMjAgNDEgTCAyMiA0MSBMIDIzIDQzIEwgMjQgNDIgTCAyNSA0NCBMIDI2IDQzIEwgMjkgNDUgTCAzMSA0NSBMIDMyIDQ3IEwgMzMgNDYgTCAzNCA0OCBMIDM1IDQ3IEwgMzkgNDkgTCA0MSA1MSBMIDQzIDUwIEwgNDIgNDkgTCA0MSAzOCBMIDM5IDM2IEwgMzIgMzIgTCAyOCAzMSBMIDI3IDI5IEwgMjUgMjggTCAyNCAyOSBMIDIwIDI2IEwgMTkgMjcgTCAxNyAyNSBaIiBmaWxsPSIjQUFBOEZBIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDI2IDEgTCAyMCA1IEwgMTMgMTUgTCAxMiAxOCBMIDEwIDIwIEwgOCAyNSBMIDUgMjkgTCA1IDMxIEwgMiAzNyBMIDIgNDEgTCAxIDQyIEwgMSA1NCBMIDIgNTUgTCAyIDU4IEwgNCA2MCBMIDUgNjMgTCAxMiA2OSBMIDIzIDczIEwgMzQgNzMgTCA0MSA3MCBMIDQ3IDYzIEwgNDkgNTggTCA0OSA1NSBMIDUwIDU0IEwgNTAgNDQgTCA0OSA0MyBMIDQ5IDM5IEwgNDggMzggTCA0NyAzMiBMIDQxIDE5IEwgMzAgMyBaIE0gMjQgNiBMIDI3IDYgTCAzMCA5IEwgMzAgMTAgTCAzNiAxOCBMIDM4IDIzIEwgNDAgMjUgTCA0NCAzMyBMIDQ0IDM1IEwgNDYgMzkgTCA0NiA0MiBMIDQ3IDQzIEwgNDcgNDggTCA0OCA0OSBMIDQ3IDUxIEwgNDcgNTUgTCA0NiA1NiBMIDQ1IDYwIEwgMzggNjcgTCAzNCA2OCBMIDMzIDY5IEwgMzEgNjkgTCAzMCA3MCBMIDIzIDcwIEwgMTQgNjYgTCA4IDYxIEwgNCA1NCBMIDQgNDIgTCA1IDQxIEwgNiAzNiBMIDggMzMgTCA4IDMxIEwgMTEgMjcgTCAxMSAyNSBMIDEzIDIzIEwgMTQgMjAgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+
#      "3": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI1MSIgaGVpZ2h0PSI3NCIgdmlld0JveD0iMCAwIDUxIDc0Ij48cGF0aCBkPSJNIDggNDMgTCA4IDUwIEwgOSA1MSBMIDkgNTMgTCAxMiA1NyBMIDEyIDU4IEwgMTQgNjAgTCAxNSA2MCBMIDE2IDYxIEwgMTYgNjIgTCAxOSA2MiBMIDIyIDY0IEwgMzMgNjQgTCAzNSA2MiBMIDM3IDYyIEwgMzggNjEgTCAzOCA2MCBMIDQwIDU4IEwgNDEgNTggTCA0MSA1NiBMIDM2IDU0IEwgMzQgNTIgTCAzMiA1MiBMIDMxIDUxIEwgMzAgNTEgTCAyNyA0OSBMIDI1IDQ5IEwgMjAgNDYgTCAxOCA0NiBMIDE1IDQ0IEwgMTMgNDQgTCAxMiA0MyBMIDEyIDQyIEwgMTEgNDMgTCAxMCA0MiBMIDkgNDIgWiBNIDE2IDI1IEwgMTYgMjYgTCAxNCAyOCBMIDE0IDI5IEwgMTEgMzQgTCAxMSAzNyBMIDEzIDM3IEwgMjAgNDEgTCAyMiA0MSBMIDIzIDQyIEwgMjMgNDMgTCAyNCA0MiBMIDI1IDQzIEwgMjUgNDQgTCAyNiA0MyBMIDI5IDQ1IEwgMzEgNDUgTCAzMiA0NiBMIDMyIDQ3IEwgMzMgNDYgTCAzNCA0NyBMIDM0IDQ4IEwgMzUgNDcgTCAzNiA0OCBMIDM5IDQ5IEwgNDEgNTEgTCA0MiA1MSBMIDQzIDUwIEwgNDIgNDkgTCA0MiA0NCBMIDQxIDQzIEwgNDEgMzggTCAzOSAzNiBMIDM4IDM2IEwgMzYgMzQgTCAzNSAzNCBMIDMyIDMyIEwgMzAgMzIgTCAyOSAzMSBMIDI4IDMxIEwgMjcgMzAgTCAyNyAyOSBMIDI2IDI5IEwgMjUgMjggTCAyNCAyOSBMIDIwIDI2IEwgMTkgMjcgTCAxNyAyNSBaIE0gMjYgMTAgTCAyMyAxMyBMIDIzIDE0IEwgMjAgMTggTCAxOSAyMSBMIDIxIDIxIEwgMjIgMjIgTCAyMyAyMiBMIDI0IDIzIEwgMjQgMjQgTCAyNSAyMyBMIDI4IDI1IEwgMzAgMjUgTCAzMSAyNiBMIDMxIDI3IEwgMzIgMjYgTCAzMyAyNyBMIDMzIDI4IEwgMzQgMjcgTCAzNyAyOCBMIDM0IDI0IEwgMzQgMjMgTCAzMiAyMSBMIDMwIDE2IEwgMjggMTQgTCAyOCAxMyBaIiBmaWxsPSIjQUFBOEZBIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDI2IDEgTCAyMiAzIEwgMjAgNSBMIDIwIDYgTCAxNyA5IEwgMTcgMTAgTCAxMyAxNSBMIDEyIDE4IEwgMTAgMjAgTCA4IDI1IEwgNSAyOSBMIDUgMzEgTCAyIDM3IEwgMiA0MSBMIDEgNDIgTCAxIDU0IEwgMiA1NSBMIDIgNTggTCA0IDYwIEwgNSA2MyBMIDEyIDY5IEwgMTYgNzEgTCAyMiA3MiBMIDIzIDczIEwgMzQgNzMgTCAzNSA3MiBMIDM3IDcyIEwgNDEgNzAgTCA0NyA2MyBMIDQ4IDU5IEwgNDkgNTggTCA0OSA1NSBMIDUwIDU0IEwgNTAgNDQgTCA0OSA0MyBMIDQ5IDM5IEwgNDggMzggTCA0NyAzMiBMIDQ1IDI5IEwgNDUgMjcgTCA0MSAxOSBMIDM3IDE0IEwgMzQgOCBMIDMwIDQgTCAzMCAzIFogTSAyNCA2IEwgMjcgNiBMIDMwIDkgTCAzMCAxMCBMIDM2IDE4IEwgMzggMjMgTCA0MCAyNSBMIDQwIDI2IEwgNDQgMzMgTCA0NCAzNSBMIDQ1IDM2IEwgNDUgMzggTCA0NiAzOSBMIDQ2IDQyIEwgNDcgNDMgTCA0NyA0OCBMIDQ4IDQ5IEwgNDggNTAgTCA0NyA1MSBMIDQ3IDU1IEwgNDYgNTYgTCA0NiA1OCBMIDQ1IDU5IEwgNDUgNjAgTCAzOCA2NyBMIDM3IDY3IEwgMzYgNjggTCAzNCA2OCBMIDMzIDY5IEwgMzEgNjkgTCAzMCA3MCBMIDIzIDcwIEwgMjIgNjkgTCAyMCA2OSBMIDE5IDY4IEwgMTQgNjYgTCA4IDYxIEwgOCA2MCBMIDYgNTggTCA2IDU3IEwgNCA1NCBMIDQgNDIgTCA1IDQxIEwgNiAzNiBMIDggMzMgTCA4IDMxIEwgMTEgMjcgTCAxMSAyNSBMIDEzIDIzIEwgMTQgMjAgTCAxNiAxOCBMIDE2IDE3IFoiIGZpbGw9IiNBNkE4QjYiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMzUgNDggTCAzNiA0OSBMIDM3IDQ5IEwgMzYgNDkgWiBNIDkgNDEgTCAxMCA0MSBMIDExIDQyIEwgMTAgNDEgWiBNIDEyIDM4IEwgMTMgMzggTCAxNiA0MCBMIDE1IDM5IFogTSAxMiAzMSBMIDExIDMyIEwgMTEgMzMgTCAxMSAzMiBaIiBmaWxsPSIjOUQ5QkU3IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDI4IDQ1IEwgMjkgNDYgTCAzMCA0NiBMIDI5IDQ2IFogTSAzMSAzMSBMIDMyIDMxIEwgMzMgMzIgTCAzMiAzMSBaIE0gMzggMjggTCAzNyAyOSBMIDM4IDI5IFoiIGZpbGw9IiM5NDkyRDkiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gMjQgNDcgTCAyNSA0NyBMIDI2IDQ4IEwgMjUgNDcgWiBNIDM5IDM1IEwgNDAgMzUgTCA0MSAzNiBMIDQwIDM1IFogTSAzNiAyOSBMIDM3IDMwIEwgMzggMzAgTCAzOSAyOSBMIDM4IDMwIEwgMzcgMzAgWiBNIDI4IDI5IEwgMjkgMzAgTCAzMCAzMCBMIDI5IDMwIFoiIGZpbGw9IiM4Njg0QzUiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
#    style:
#      top: 29%
#      left: 16%
#      width: 3.76%
#    tap_action:
#      action: none
#  - type: state-label
#    entity: sensor.dantherm_humidity
#    style:
#      top: 29%
#      left: 18%
#      # font-size: 125%
#      transform: translate(0%,-50%)
#  - type: image
#    entity: sensor.dantherm_air_quality_level
#    state_image:
#      "0": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI3NCIgaGVpZ2h0PSI0OCIgdmlld0JveD0iMCAwIDc0IDQ4Ij48cGF0aCBkPSJNIDcxIDE4IEwgNjkgMTQgTCA2MiA3IEwgNTYgNiBMIDU1IDUgTCA0OSA1IEwgNDIgMSBMIDM3IDEgTCAzNiAwIEwgMzUgMSBMIDMwIDEgTCAyOSAyIEwgMjcgMiBMIDIzIDQgTCAxOCA5IEwgMTYgMTMgTCAxNiAxNiBMIDE0IDE4IEwgMTAgMTggTCA5IDE5IEwgNyAxOSBMIDMgMjIgTCAxIDI2IEwgMSAyOCBMIDAgMjkgTCAwIDMzIEwgMSAzNCBMIDEgMzcgTCAzIDQxIEwgNiA0NCBMIDEwIDQ2IEwgNTcgNDYgTCA2MyA0MyBMIDY5IDM3IEwgNzEgMzMgTCA3MSAzMSBMIDcyIDMwIEwgNzIgMjEgTCA3MSAyMCBaIE0gMiAzMCBMIDMgMjkgTCA0IDI2IEwgOCAyMiBMIDkgMjIgTCAxMCAyMSBMIDE0IDIxIEwgMTUgMjAgTCA0MCAyMCBMIDQxIDIxIEwgNDMgMjEgTCA0OCAyNCBMIDQ4IDI1IEwgNTAgMjcgTCA1MCAyOSBMIDUxIDMwIEwgNTEgMzQgTCA1MCAzNSBMIDUwIDM3IEwgNDkgMzggTCA0OSAzOSBMIDQ2IDQyIEwgNDUgNDIgTCA0MiA0NCBMIDExIDQ0IEwgMTAgNDMgTCA3IDQyIEwgNCAzOSBMIDQgMzggTCAyIDM1IFogTSA0OCA4IEwgNTcgOCBMIDU4IDkgTCA2MyAxMSBMIDY4IDE3IEwgNjggMTggTCA2OSAxOSBMIDY5IDIxIEwgNzAgMjIgTCA3MCAzMCBMIDY5IDMxIEwgNjkgMzMgTCA2NyAzNSBMIDY3IDM2IEwgNjIgNDEgTCA2MSA0MSBMIDU4IDQzIEwgNTYgNDMgTCA1NSA0NCBMIDUxIDQ0IEwgNTAgNDMgTCA1MCA0MiBMIDUyIDM5IEwgNTIgMzcgTCA1MyAzNiBMIDUzIDI4IEwgNTIgMjcgTCA1MSAyNCBMIDQ3IDIwIEwgNDYgMjAgTCA0NSAxOSBMIDQzIDE5IEwgNDIgMTggTCA0MCAxOCBMIDM3IDE2IEwgMzcgMTUgTCA0MSAxMSBMIDQyIDExIEwgNDUgOSBMIDQ3IDkgWiBNIDQzIDUgTCA0MyA3IEwgNDIgOCBMIDQxIDggTCAzNCAxNSBMIDM0IDE2IEwgMzMgMTcgTCAxOSAxNyBMIDE4IDE2IEwgMTggMTQgTCAxOSAxMyBMIDE5IDEyIEwgMjUgNiBMIDI2IDYgTCAzMSAzIEwgNDAgMyBaIiBmaWxsPSIjQTZBOEI2IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48L3N2Zz4=
#      "1": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI3NCIgaGVpZ2h0PSI0OCIgdmlld0JveD0iMCAwIDc0IDQ4Ij48cGF0aCBkPSJNIDQgMjkgTCA0IDM2IEwgNSAzNyBMIDUgMzggTCA4IDQxIEwgOSA0MSBMIDEwIDQyIEwgMTggNDIgTCAxOSA0MyBMIDMzIDQzIEwgMzQgNDIgTCA0MyA0MiBMIDQ0IDQxIEwgNDUgNDEgTCA0OCAzOCBMIDQ4IDM3IEwgNDkgMzYgTCA0OSAzNCBMIDUwIDMzIEwgNDkgMjggTCA0NyAyNiBMIDQ3IDI1IEwgNDMgMjIgTCAxMSAyMiBMIDEwIDIzIEwgNyAyNCBaIiBmaWxsPSIjNDA2QUM5IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48cGF0aCBkPSJNIDcxIDE4IEwgNjkgMTQgTCA2MiA3IEwgNTYgNiBMIDU1IDUgTCA0OSA1IEwgNDIgMSBMIDM3IDEgTCAzNiAwIEwgMzUgMSBMIDMwIDEgTCAyOSAyIEwgMjcgMiBMIDIzIDQgTCAxOCA5IEwgMTYgMTMgTCAxNiAxNiBMIDE0IDE4IEwgMTAgMTggTCA5IDE5IEwgNyAxOSBMIDMgMjIgTCAxIDI2IEwgMSAyOCBMIDAgMjkgTCAwIDMzIEwgMSAzNCBMIDEgMzcgTCAzIDQxIEwgNiA0NCBMIDEwIDQ2IEwgNTcgNDYgTCA2MyA0MyBMIDY5IDM3IEwgNzEgMzMgTCA3MSAzMSBMIDcyIDMwIEwgNzIgMjEgTCA3MSAyMCBaIE0gMiAzMCBMIDMgMjkgTCA0IDI2IEwgOCAyMiBMIDkgMjIgTCAxMCAyMSBMIDE0IDIxIEwgMTUgMjAgTCA0MCAyMCBMIDQxIDIxIEwgNDMgMjEgTCA0OCAyNCBMIDQ4IDI1IEwgNTAgMjcgTCA1MCAyOSBMIDUxIDMwIEwgNTEgMzQgTCA1MCAzNSBMIDUwIDM3IEwgNDkgMzggTCA0OSAzOSBMIDQ2IDQyIEwgNDUgNDIgTCA0MiA0NCBMIDExIDQ0IEwgMTAgNDMgTCA3IDQyIEwgNCAzOSBMIDQgMzggTCAyIDM1IFogTSA0OCA4IEwgNTcgOCBMIDU4IDkgTCA2MyAxMSBMIDY4IDE3IEwgNjggMTggTCA2OSAxOSBMIDY5IDIxIEwgNzAgMjIgTCA3MCAzMCBMIDY5IDMxIEwgNjkgMzMgTCA2NyAzNSBMIDY3IDM2IEwgNjIgNDEgTCA2MSA0MSBMIDU4IDQzIEwgNTYgNDMgTCA1NSA0NCBMIDUxIDQ0IEwgNTAgNDMgTCA1MCA0MiBMIDUyIDM5IEwgNTIgMzcgTCA1MyAzNiBMIDUzIDI4IEwgNTIgMjcgTCA1MSAyNCBMIDQ3IDIwIEwgNDYgMjAgTCA0NSAxOSBMIDQzIDE5IEwgNDIgMTggTCA0MCAxOCBMIDM3IDE2IEwgMzcgMTUgTCA0MSAxMSBMIDQyIDExIEwgNDUgOSBMIDQ3IDkgWiBNIDQzIDUgTCA0MyA3IEwgNDIgOCBMIDQxIDggTCAzNCAxNSBMIDM0IDE2IEwgMzMgMTcgTCAxOSAxNyBMIDE4IDE2IEwgMTggMTQgTCAxOSAxMyBMIDE5IDEyIEwgMjUgNiBMIDI2IDYgTCAzMSAzIEwgNDAgMyBaIiBmaWxsPSIjQTZBOEI2IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48L3N2Zz4=
#      "2": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI3NCIgaGVpZ2h0PSI0OCIgdmlld0JveD0iMCAwIDc0IDQ4Ij48cGF0aCBkPSJNIDQgMjkgTCA0IDM2IEwgNSAzNyBMIDUgMzggTCA4IDQxIEwgOSA0MSBMIDEwIDQyIEwgMTggNDIgTCAxOSA0MyBMIDMzIDQzIEwgMzQgNDIgTCA0MyA0MiBMIDQ0IDQxIEwgNDUgNDEgTCA0OCAzOCBMIDQ4IDM3IEwgNDkgMzYgTCA0OSAzNCBMIDUwIDMzIEwgNDkgMjggTCA0NyAyNiBMIDQ3IDI1IEwgNDMgMjIgTCAxMSAyMiBMIDEwIDIzIEwgNyAyNCBaIE0gNTYgOSBMIDQ5IDkgTCA0OCAxMCBMIDQ2IDEwIEwgNDUgMTEgTCA0MiAxMiBMIDM4IDE2IEwgNDAgMTYgTCA0MSAxNyBMIDQ2IDE4IEwgNDggMjAgTCA0OSAyMCBMIDUzIDI1IEwgNTMgMjYgTCA1NSAyOSBMIDU1IDM2IEwgNTIgNDEgTCA1MiA0MyBMIDUzIDQyIEwgNTYgNDIgTCA1NyA0MSBMIDU5IDQxIEwgNjAgNDAgTCA2MSA0MCBMIDY3IDM0IEwgNjcgMzIgTCA2OCAzMSBMIDY4IDI3IEwgNjkgMjYgTCA2OCAyNSBMIDY4IDIxIEwgNjcgMjAgTCA2NyAxOCBMIDY2IDE3IEwgNjYgMTYgTCA2MiAxMiBMIDYxIDEyIFoiIGZpbGw9IiM0MDZBQzkiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjxwYXRoIGQ9Ik0gNzEgMTggTCA2OSAxNCBMIDYyIDcgTCA1NiA2IEwgNTUgNSBMIDQ5IDUgTCA0MiAxIEwgMzcgMSBMIDM2IDAgTCAzNSAxIEwgMzAgMSBMIDI5IDIgTCAyNyAyIEwgMjMgNCBMIDE4IDkgTCAxNiAxMyBMIDE2IDE2IEwgMTQgMTggTCAxMCAxOCBMIDkgMTkgTCA3IDE5IEwgMyAyMiBMIDEgMjYgTCAxIDI4IEwgMCAyOSBMIDAgMzMgTCAxIDM0IEwgMSAzNyBMIDMgNDEgTCA2IDQ0IEwgMTAgNDYgTCA1NyA0NiBMIDYzIDQzIEwgNjkgMzcgTCA3MSAzMyBMIDcxIDMxIEwgNzIgMzAgTCA3MiAyMSBMIDcxIDIwIFogTSAyIDMwIEwgMyAyOSBMIDQgMjYgTCA4IDIyIEwgOSAyMiBMIDEwIDIxIEwgMTQgMjEgTCAxNSAyMCBMIDQwIDIwIEwgNDEgMjEgTCA0MyAyMSBMIDQ4IDI0IEwgNDggMjUgTCA1MCAyNyBMIDUwIDI5IEwgNTEgMzAgTCA1MSAzNCBMIDUwIDM1IEwgNTAgMzcgTCA0OSAzOCBMIDQ5IDM5IEwgNDYgNDIgTCA0NSA0MiBMIDQyIDQ0IEwgMTEgNDQgTCAxMCA0MyBMIDcgNDIgTCA0IDM5IEwgNCAzOCBMIDIgMzUgWiBNIDQ4IDggTCA1NyA4IEwgNTggOSBMIDYzIDExIEwgNjggMTcgTCA2OCAxOCBMIDY5IDE5IEwgNjkgMjEgTCA3MCAyMiBMIDcwIDMwIEwgNjkgMzEgTCA2OSAzMyBMIDY3IDM1IEwgNjcgMzYgTCA2MiA0MSBMIDYxIDQxIEwgNTggNDMgTCA1NiA0MyBMIDU1IDQ0IEwgNTEgNDQgTCA1MCA0MyBMIDUwIDQyIEwgNTIgMzkgTCA1MiAzNyBMIDUzIDM2IEwgNTMgMjggTCA1MiAyNyBMIDUxIDI0IEwgNDcgMjAgTCA0NiAyMCBMIDQ1IDE5IEwgNDMgMTkgTCA0MiAxOCBMIDQwIDE4IEwgMzcgMTYgTCAzNyAxNSBMIDQxIDExIEwgNDIgMTEgTCA0NSA5IEwgNDcgOSBaIE0gNDMgNSBMIDQzIDcgTCA0MiA4IEwgNDEgOCBMIDM0IDE1IEwgMzQgMTYgTCAzMyAxNyBMIDE5IDE3IEwgMTggMTYgTCAxOCAxNCBMIDE5IDEzIEwgMTkgMTIgTCAyNSA2IEwgMjYgNiBMIDMxIDMgTCA0MCAzIFoiIGZpbGw9IiNBNkE4QjYiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==
#      "3": data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI3NCIgaGVpZ2h0PSI0OCIgdmlld0JveD0iMCAwIDc0IDQ4Ij48cGF0aCBkPSJNIDQgMjkgTCA0IDM2IEwgNSAzNyBMIDUgMzggTCA4IDQxIEwgOSA0MSBMIDEwIDQyIEwgMTggNDIgTCAxOSA0MyBMIDMzIDQzIEwgMzQgNDIgTCA0MyA0MiBMIDQ0IDQxIEwgNDUgNDEgTCA0OCAzOCBMIDQ4IDM3IEwgNDkgMzYgTCA0OSAzNCBMIDUwIDMzIEwgNDkgMjggTCA0NyAyNiBMIDQ3IDI1IEwgNDMgMjIgTCAxMSAyMiBMIDEwIDIzIEwgNyAyNCBaIE0gNTYgOSBMIDQ5IDkgTCA0OCAxMCBMIDQ2IDEwIEwgNDUgMTEgTCA0MiAxMiBMIDM4IDE2IEwgNDAgMTYgTCA0MSAxNyBMIDQ2IDE4IEwgNDggMjAgTCA0OSAyMCBMIDUzIDI1IEwgNTMgMjYgTCA1NSAyOSBMIDU1IDM2IEwgNTIgNDEgTCA1MiA0MyBMIDUzIDQyIEwgNTYgNDIgTCA1NyA0MSBMIDU5IDQxIEwgNjAgNDAgTCA2MSA0MCBMIDY3IDM0IEwgNjcgMzIgTCA2OCAzMSBMIDY4IDI3IEwgNjkgMjYgTCA2OCAyNSBMIDY4IDIxIEwgNjcgMjAgTCA2NyAxOCBMIDY2IDE3IEwgNjYgMTYgTCA2MiAxMiBMIDYxIDEyIFogTSA0MiA1IEwgMzcgNSBMIDM2IDQgTCAzNSA1IEwgMzAgNSBMIDI5IDYgTCAyNyA2IEwgMjEgMTEgTCAyMSAxMiBMIDIwIDEzIEwgMjAgMTYgTCAzMiAxNiBMIDMzIDE1IEwgMzMgMTQgTCA0MCA3IEwgNDEgNyBMIDQyIDYgWiIgZmlsbD0iIzQwNkFDOSIgZmlsbC1ydWxlPSJldmVub2RkIi8+PHBhdGggZD0iTSA3MSAxOCBMIDY5IDE0IEwgNjIgNyBMIDU2IDYgTCA1NSA1IEwgNDkgNSBMIDQyIDEgTCAzNyAxIEwgMzYgMCBMIDM1IDEgTCAzMCAxIEwgMjkgMiBMIDI3IDIgTCAyMyA0IEwgMTggOSBMIDE2IDEzIEwgMTYgMTYgTCAxNCAxOCBMIDEwIDE4IEwgOSAxOSBMIDcgMTkgTCAzIDIyIEwgMSAyNiBMIDEgMjggTCAwIDI5IEwgMCAzMyBMIDEgMzQgTCAxIDM3IEwgMyA0MSBMIDYgNDQgTCAxMCA0NiBMIDU3IDQ2IEwgNjMgNDMgTCA2OSAzNyBMIDcxIDMzIEwgNzEgMzEgTCA3MiAzMCBMIDcyIDIxIEwgNzEgMjAgWiBNIDIgMzAgTCAzIDI5IEwgNCAyNiBMIDggMjIgTCA5IDIyIEwgMTAgMjEgTCAxNCAyMSBMIDE1IDIwIEwgNDAgMjAgTCA0MSAyMSBMIDQzIDIxIEwgNDggMjQgTCA0OCAyNSBMIDUwIDI3IEwgNTAgMjkgTCA1MSAzMCBMIDUxIDM0IEwgNTAgMzUgTCA1MCAzNyBMIDQ5IDM4IEwgNDkgMzkgTCA0NiA0MiBMIDQ1IDQyIEwgNDIgNDQgTCAxMSA0NCBMIDEwIDQzIEwgNyA0MiBMIDQgMzkgTCA0IDM4IEwgMiAzNSBaIE0gNDggOCBMIDU3IDggTCA1OCA5IEwgNjMgMTEgTCA2OCAxNyBMIDY4IDE4IEwgNjkgMTkgTCA2OSAyMSBMIDcwIDIyIEwgNzAgMzAgTCA2OSAzMSBMIDY5IDMzIEwgNjcgMzUgTCA2NyAzNiBMIDYyIDQxIEwgNjEgNDEgTCA1OCA0MyBMIDU2IDQzIEwgNTUgNDQgTCA1MSA0NCBMIDUwIDQzIEwgNTAgNDIgTCA1MiAzOSBMIDUyIDM3IEwgNTMgMzYgTCA1MyAyOCBMIDUyIDI3IEwgNTEgMjQgTCA0NyAyMCBMIDQ2IDIwIEwgNDUgMTkgTCA0MyAxOSBMIDQyIDE4IEwgNDAgMTggTCAzNyAxNiBMIDM3IDE1IEwgNDEgMTEgTCA0MiAxMSBMIDQ1IDkgTCA0NyA5IFogTSA0MyA1IEwgNDMgNyBMIDQyIDggTCA0MSA4IEwgMzQgMTUgTCAzNCAxNiBMIDMzIDE3IEwgMTkgMTcgTCAxOCAxNiBMIDE4IDE0IEwgMTkgMTMgTCAxOSAxMiBMIDI1IDYgTCAyNiA2IEwgMzEgMyBMIDQwIDMgWiIgZmlsbD0iI0E2QThCNiIgZmlsbC1ydWxlPSJldmVub2RkIi8+PC9zdmc+
#    style:
#      top: 29%
#      left: 36%
#      width: 5.45%
#    tap_action:
#      action: none
#  - type: state-label
#    entity: sensor.dantherm_air_quality
#    style:
#      top: 29%
#      left: 39%
#      # font-size: 125%
#      transform: translate(0%,-50%)

```
</details>

#### Dashboard Badges

Here are some examples of badges added to the dashboard. The pop-up that appears when clicking on a badge will vary depending on the selected entities, either displaying information or enabling manipulation of the Dantherm unit.

![Skærmbillede badge example](https://github.com/user-attachments/assets/bbaac388-0e40-48cf-a0d1-7b42fb5a4234)


#### Apex-chart

![Skærmbillede 2025-06-23 092901](https://github.com/user-attachments/assets/29cabc96-54d5-42db-bedc-ae381c8f5c94)

<details>

<summary>The details for the above Apex-chart card (Can be found on HACS) 👈 Click to open</summary>

```yaml

type: custom:apexcharts-card
update_interval: 5min
apex_config:
  stroke:
    width: 2
    curve: smooth
graph_span: 24h
series:
  - entity: sensor.dantherm_extract_temperature
    name: Extract Temperature
    extend_to: false
    show:
      extremas: true
      legend_value: false
    group_by:
      duration: 5min
      func: avg
  - entity: sensor.dantherm_outdoor_temperature
    name: Outdoor Temperature
    extend_to: false
    show:
      extremas: true
      legend_value: false
    group_by:
      duration: 5min
      func: avg
  - entity: sensor.dantherm_exhaust_temperature
    name: Exhaust Temperature
    extend_to: false
    show:
      legend_value: false
    group_by:
      duration: 5min
      func: avg
  - entity: sensor.dantherm_supply_temperature
    name: Supply Temperature
    extend_to: false
    show:
      legend_value: false
    group_by:
      duration: 5min
      func: avg

```

</details>


## Sensor Filtering

To improve the stability and reliability of sensor readings, the integration now supports **sensor filtering** for key environmental data collected from the Dantherm unit. This filtering mechanism is applied to the following sensors:

- **Humidity**
- **Air Quality**
- **Exhaust Temperature**
- **Extract Temperature**
- **Supply Temperature**
- **Outdoor Temperature**
- **Room Temperature**

### Control via Home Assistant Switch

The filtering feature can be enabled or disabled via the **"Sensor Filtering"** switch entity. By default, the filtering is **disabled**, ensuring the system behaves as it did previously. When the switch is enabled, the filtering logic described below will be applied.

### How It Works

Each sensor is equipped with a sliding history buffer, storing the last 5 readings. The filter applies two techniques:

1. **Initialization Smoothing**
   For the first few readings (up to 5), the filter calculates a simple average. This helps the sensor start off with a stable baseline, preventing a single bad initial reading from influencing the system.

2. **Spike Filtering**
   After initialization, every new reading is compared to a rolling average of the last 5 readings.
   If the new reading changes more than a defined threshold (`max_change`) compared to the rolling average, the spike is rejected, and the system uses the current rolling average instead.

### Individual Thresholds per Sensor

Each sensor type has a predefined maximum allowed change per reading:

| Sensor      | Max Change |
|-------------|------------|
| Humidity    | 5% RH      |
| Air Quality | 50 PPM     |
| Temperatures| 2°C        |

This ensures the filtering logic fits the natural dynamics of each sensor type.

> This feature was inspired by [issue #68](https://github.com/Tvalley71/dantherm/issues/68), reported by a community user.

## Actions

### Using the "Dantherm: Set State" and "Dantherm: Set configuration" Actions

The **Dantherm: Set state** action allows you to control the state of your Dantherm ventilation unit directly from a Home Assistant automation. This action provides a wide range of options to customize the operation of your unit, making it suitable for various scenarios.

#### Steps to Use the "Set State" Action

1. **Create a New Automation:**
   - Navigate to `Settings` > `Automations & Scenes`.
   - Click on **Add Automation** and select **Start with an empty automation**.

2. **Configure a Trigger:**
   - Add a trigger that fits your use case. For example:
     - A time-based trigger to schedule changes.
     - A sensor-based trigger to react to environmental changes.
        - Air Quality Sensor: Trigger when CO2 levels exceed a threshold, e.g., 1000 ppm.
        - Humidity Sensor: Trigger when humidity exceeds, e.g., 70%.
        - Window Sensor: Trigger when a window opens.
        - Cooker Hood: Trigger when the smart plug detects power usage above a threshold.

3. **Add the "Dantherm: Set State" Action:**
   - Under the **Actions** section, click **Add Action**.
   - Search for `Dantherm: Set state` in the action picker and select it.

4. **Configure the Action:**
   - Use the options provided to control the Dantherm ventilation unit:
     - **Device:** Select the Dantherm device.
     - **Operation Selection:** Set the desired operating mode (e.g., Standby, Automatic, Manual, or Week Program).
     - **Fan Selection:** Choose the desired fan level (Level 0–4).
     - **Modes:** Toggle special modes like:
       - **Away Mode**: Enable or disable away mode.
       - **Summer Mode**: Turn summer mode on or off.
       - **Fireplace Mode**: Activate fireplace mode for a limited period.
       - **Manual Bypass Mode**: Enable or disable manual bypass.

<img width="1200" height="1100" alt="Skærmbillede 02-11-2025 kl  12 04 07 PM" src="https://github.com/user-attachments/assets/bd26f5f3-cc82-44e5-8e6f-0bf67afe25e7" />

5. **Save the Automation:**
   - Once configured, save the automation. The Dantherm unit will now respond to the specified trigger and perform the desired action.

The **Dantherm: Set configuration** action allows you to adjust various configuration settings of your Dantherm device directly from Home Assistant. This action can be used in automations, scripts, or manually through the Developer Tools.

Starting from version _0.4.17_ of the integration, the actions have been reorganized into multiple variants, because Home Assistant actions cannot dynamically add or remove fields. Therefore, you now have **Set configuration**, **Set configuration 2**, and **Set configuration 3**, each containing the fields supported by a specific firmware versions:

| Action               | Supported firmware         |
|----------------------|----------------------------|
| Set configuration    | All supported firmwares    |
| Set configuration 2  | 2.70 and newer             |
| Set configuration 3  | 3.14 and newer             |

<img width="1200" height="691" alt="Skærmbillede 02-11-2025 kl  12 04 30 PM" src="https://github.com/user-attachments/assets/4d1648bd-0ee2-4e77-89d2-ad827e336df4" />

<img width="1200" height="691" alt="Skærmbillede 02-11-2025 kl  12 04 43 PM" src="https://github.com/user-attachments/assets/ca4e8d39-523f-49b6-bb3a-d3c8ab703dfe" />

<img width="1200" height="513" alt="Skærmbillede 02-11-2025 kl  12 05 09 PM" src="https://github.com/user-attachments/assets/852e221d-5e8e-4dcb-9b15-632eaee4e9b9" />

### Pending write operations

The integration tracks pending write operations for supported entities, including direct writes from Home Assistant entities and changes made through the Dantherm actions.

- **`binary_sensor.dantherm_actions_pending`** is on while one or more write actions are queued, being processed, or awaiting a follow-up refresh.
- Supported entities expose an extra **`pending`** attribute:
  - `true` = a change has been requested, but the updated state is still awaiting a follow-up refresh
  - `false` = no pending change is currently tracked for that entity

This can be useful in automations, scripts, and dashboards where you want to distinguish between a requested change and a later refreshed state.

> [!NOTE]
> Pending is not cleared immediately after a write operation, but after a later refresh cycle.

https://github.com/user-attachments/assets/96a14937-46b2-47fa-ade3-e37c57028b56


## Integration enhancements

## Advanced Features 🚀

The integration enhances the control of Dantherm ventilation units by introducing **Boost Mode**, **Eco Mode**, **Home Mode**, and a **Calendar Function** for advanced scheduling and automation. These features ensure efficient operation based on both **schedules** and **various triggers**, providing a comfortable and energy-efficient environment.


### Boost Mode 🚀
Boost Mode is designed for short bursts of increased ventilation, useful after activities like cooking or showering.

- **Boost Mode Switch**: This must be **enabled** for Boost Mode to activate.
- **Trigger-Based Activation**: If Boost Mode is **enabled** and the **Boost Mode Trigger** is active, the unit switches to the **Boost Operation Selection**.
- **Timeout Handling**: [See Trigger Timeout](#trigger-timeout) for details on how long Boost Mode remains active after the trigger is deactivated.
- **Available Operations**: `Level 4`, `Level 3`, or `Level 2`.

> **Important**
> The Dantherm unit has a built-in **automatic setback** from `Level 4` to `Level 3` after a fixed time period. This may cause Boost Mode to behave unexpectedly if `Level 4` is used for longer periods.


### Eco Mode 🌱
Eco Mode is designed to **reduce fan speed** under specific environmental conditions, optimizing efficiency and supporting the unit’s **defrost mechanism** in cold weather.

- **Eco Mode Switch**: This must be **enabled** for Eco Mode to activate.
- **Trigger-Based Activation**: If Eco Mode is **enabled** and the **Eco Mode Trigger** is active, the unit switches to the **Eco Operation Selection**.
- **Timeout Handling**: [See Trigger Timeout](#trigger-timeout) for details on how long Eco Mode remains active after the trigger is deactivated.
- **Available Operations**: `Standby` and `Level 1`.

> **Important**
> The Dantherm unit has a built-in **automatic setback** from `Standby` to `Level 3` after a fixed time period. This may cause Eco Mode to behave unexpectedly if `Standby` is used for longer periods.


### Home Mode 🏡
Home Mode allows for automatic adjustments based on a **Home Mode Trigger**, ensuring efficient ventilation when you are at home.

- **Home Mode Switch**: This must be **enabled** for Home Mode to activate.
- **Trigger-Based Activation**: If Home Mode is **enabled** and the **Home Mode Trigger** is active, the unit switches to the **Home Operation Selection**.
- **Timeout Handling**: [See Trigger Timeout](#trigger-timeout) for details on how long Home Mode remains active after the trigger is deactivated.
- **Available Operations**: `Automatic`, `Level 3`, `Level 2`, `Level 1`, or `Week Program`.


<h3 id="trigger-timeout">Trigger Timeout ⏱️</h3>

Each mode trigger (Boost, Eco, Home) includes a configurable timeout that defines how long the mode remains active after the trigger is deactivated.

- **Timeout Behavior**: After the trigger turns off, the unit continues operating in the triggered mode for the remaining timeout period.
- **Reset on Re-trigger**: If the trigger is activated again *within the timeout window*, the countdown restarts.
- **Automatic Revert**: When the timeout expires without further trigger activity, the unit reverts to the operation mode that was active before the trigger event—unless this has been overridden by a calendar schedule.

This mechanism ensures that temporary conditions (e.g., presence, humidity, low temperature) cause a short-term mode change without disrupting long-term schedules.


### Adaptive Triggers ⚡

Boost, Eco, and Home Modes rely on **Adaptive Triggers** — binary sensors or helpers that determine **when a mode should activate**.

An **Adaptive Trigger** can be:

- A **motion sensor** (e.g., presence detection for Home Mode)
- A **humidity sensor** (e.g., high humidity after a shower for Boost Mode)
- A **power sensor** (e.g., detecting stove or shower fan usage)
- An **outdoor temperature sensor** (e.g., reducing fan speed in cold weather for Eco Mode)
- A **custom helper** combining multiple conditions

Adaptive Triggers are configured manually in the integration options and linked to each mode individually.

> ⚠️ **Note**
> Only entities of type `binary_sensor` or `input_boolean` are supported as Adaptive Triggers.
> Make sure the entity returns an `on` or `off` state.


### Trigger Entity Availability 🛑

Entities related to Boost, Eco, and Home Modes (e.g., mode switch, timeout, operation selection) are **disabled by default** unless a corresponding trigger is configured.

If you manually enable these entities via Home Assistant, they will be **automatically disabled again after a reload** of the integration unless a valid trigger is set in the integration options.


### Configuring the integration

#### How to Open the Integration Options
To change settings such as disabling temperature unknown values, disabling notifications, or configuring adaptive triggers:

1. Go to Home Assistant → Settings → Devices & Services → Integrations.
2. Find the Dantherm integration in the list.
3. Click the Configure button (gear icon) for your Dantherm integration instance.

<img width="707" height="306" alt="Skærmbillede 02-11-2025 kl  12 06 31 PM" src="https://github.com/user-attachments/assets/6e8ab25f-7ba3-45eb-9f21-7978d2a27acd" />

4. The options dialog will open, where you can adjust the available settings.

#### Network Settings

If device discovery does not find your unit, you can manually update the IP address and Port in the integration options dialog.

1. The Device IP address should be set to the unit’s current IP address.
2. The TCP port number  is typically the Modbus port used by your unit (default: 502).

<img width="421" height="552" alt="Skærmbillede 02-11-2025 kl  12 06 59 PM" src="https://github.com/user-attachments/assets/3599bc8a-c701-4f4d-8a0f-5ebb4cdfedd2" />

#### Adaptive Triggers & Scheduling

1. Enter the trigger entity in the appropriate field.
Use the field for the mode you want to configure (e.g., Boost Mode Trigger, Eco Mode Trigger, or Home Mode Trigger).
Example values:
`binary_sensor.kitchen_motion`, `binary_sensor.living_room_presence`, `binary_sensor.outdoor_temperature_low`
2. If you have more than one Dantherm unit, you can choose whether each device should share the same calendar as your primary unit or use its own.
The primary calendar is automatically created for the first configured device. For any additional units, an option appears to link to the primary calendar.
This option defaults to enabled, which is recommended — it ensures consistent scheduling across all units and keeps configuration simple.
If you disable this option, the unit will instead create its own separate calendar, allowing fully independent scheduling.
3. Click Submit to save your configuration.
4. Enable the corresponding mode in the Home Assistant UI to activate the trigger.

<img width="596" height="522" alt="Skærmbillede 02-11-2025 kl  13 12 04 PM" src="https://github.com/user-attachments/assets/8ca96468-8d26-40be-b19e-e37ae7d2dd9f" />

Once configured, the Dantherm unit will automatically switch to the selected **operation mode** whenever the **Adaptive Trigger** becomes active. ⚡

#### Advandced Options

1. Disabling "Unknown" Temperatures in Bypass and Summer Mode.
To prevent temperature sensors from being set to unknown during bypass or summer mode, enable the option "Disable setting temperatures to unknown in bypass/summer modes".
When this option is enabled, temperature sensors will always report their current value, even when the device is in bypass or summer mode.

2. Disabling Notifications.
To disable all persistent notifications from the Dantherm integration, enable "Disable notifications".
When this option is enabled, the integration will not send any persistent notifications to Home Assistant’s notification area.

<img width="584" height="362" alt="Skærmbillede 02-11-2025 kl  12 07 14 PM" src="https://github.com/user-attachments/assets/4643bd4f-f2de-4f8a-b9dc-4102012dcb1e" />


## ⏳ Advanced Scheduling Features

### Calendar Function 📅
The Calendar Function allows precise scheduling of different operation modes, providing full automation of the ventilation system.

#### How to Use the Calendar Function

1. **Enable Calendar Entity**: In your Home Assistant, go to **Settings > Devices & Services > Dantherm** and ensure the calendar entity is enabled.

2. **Create Calendar Events**: Use the Dantherm calendar entity to create events with specific keywords in the event **summary** (title).

3. **Supported Event Keywords**: Use these exact words in your calendar event summaries:
   - **Level 1**, **Level 2**, **Level 3** - Sets manual fan levels
   - **Automatic** - Switches to automatic demand mode
   - **Away Mode** - Activates away mode for the event duration
   - **Night Mode** - Activates night mode for the event duration
   - **Boost Mode** - Activates boost mode for the event duration
   - **Home Mode** - Activates home mode for the event duration
   - **Eco Mode** - Activates eco mode for the event duration
   - **Week Program** - Follows the selected week program

4. **Language Support**: Keywords are automatically translated based on your Home Assistant language settings (if the language is supported by the integration).

#### Example Calendar Usage

```
Summary: "Boost Mode"
Start: Today 07:00
End: Today 09:00
Result: Boost mode active from 7 AM to 9 AM
```

```
Summary: "Level 3"
Start: Today 19:00
End: Today 22:00
Result: Manual mode Level 3 from 7 PM to 10 PM
```

```
Summary: "Away Mode"
Start: Friday 08:00
End: Sunday 18:00
Result: Away mode active for the weekend
```

- **Integration - Calendar Events**:
  Calendar events control the ventilation system automatically. When an event starts, the system switches to the specified operation mode. When the event ends, it reverts to the previous active mode.

- **Event Behavior**:
  - **Manual Levels (Level 1-3)**: Unit runs in Manual mode at the specified fan level
  - **Automatic**: Unit operates in Demand Mode with automatic fan speed control
  - **Mode Toggles (Away, Night, Boost, Home, Eco)**: These modes are **enabled at event start** and **disabled at event end**
  - **Week Program**: Unit follows the predefined week program selected in **Week Program Selection**

- **Smart Scheduling**: The calendar respects the priority system below, so higher priority events override lower priority ones when they overlap.

#### Calendar Configuration Options

In the integration's **Configure** menu, you can find several calendar-related options:

- **Link to Primary Calendar**: When multiple Dantherm units are installed, link all calendar functions to the primary unit's calendar for centralized control.

#### Recurring Events and Advanced Scheduling

The calendar supports:
- **Single Events**: One-time scheduled operations
- **Recurring Events**: Daily, weekly, or custom recurring patterns
- **All-Day Events**: Events without specific times
- **Overlapping Events**: Higher priority events override lower priority ones

#### Troubleshooting Calendar Function

- **Events Not Working**: Ensure event keywords match exactly (case-sensitive)
- **Language Issues**: Check that your Home Assistant language is supported
- **Priority Conflicts**: Higher priority events will override lower ones
- **Night Mode Timing**: Built-in Night Mode times may conflict with scheduled events

  - If **Level 1** to **Level 3** is scheduled, the unit will run in Manual mode at the selected fan level.
  - If **Automatic** is scheduled, the unit will operate in Demand Mode.
  - If **Away Mode** is scheduled, Away Mode will be **enabled at the start** and **disabled at the end** of the event.
  - If **Night Mode** is scheduled, Night Mode will be **enabled at the start** and **disabled at the end** of the event.
  - If **Boost Mode**, **Home Mode**, or **Eco Mode** is scheduled, the respective mode's trigger will be **enabled at the start** and **disabled at the end**, allowing the unit to switch modes dynamically.
  - If **Week Program** is scheduled, the unit will follow the selected program in **Week Program Selection**.

#### Event Priority System

When multiple calendar events overlap, the system follows this priority order (highest to lowest):

- **Priority System**: The following is the **priority order** for calendar scheduling:
  1. 🚨 **Away Mode** (highest priority) - For vacation/extended absence
  2. ⚡ **Boost Mode** - For high ventilation needs
  3. 🌙 **Night Mode** - For quiet nighttime operation
  4. 🏠 **Home Mode** - For normal occupied periods
  5. 🍃 **Eco Mode** - For energy-saving operation
  6. 💨 **Level 3** - Maximum manual fan speed
  7. 💨 **Level 2** - Medium manual fan speed
  8. 💨 **Level 1** - Minimum manual fan speed
  9. 🤖 **Automatic** - Demand-based automatic control
  10. 📅 **Week Program** (lowest priority) - Predefined weekly schedules

**Example**: If you have "Eco Mode" scheduled from 8 AM-6 PM and "Boost Mode" from 12 PM-1 PM, Boost Mode will take priority during the lunch hour, then revert back to Eco Mode.

#### Step-by-Step: Creating Your First Calendar Event

1. **Access the Calendar**:
   - Go to **Calendar** in Home Assistant's sidebar
   - Find your "Dantherm Calendar" entity

2. **Create New Event**:
   - Click the **+** button or a time slot
   - Enter a **Title/Summary** with one of the supported keywords (e.g., "Boost Mode")
   - Set **Start** and **End** times
   - Save the event

3. **Verify Operation**:
   - Check that the event appears in the calendar
   - Monitor the ventilation unit at the scheduled time
   - Verify mode changes occur as expected

#### Best Practices for Calendar Scheduling

- **Morning Routine**: Schedule "Boost Mode" during morning activities (7-9 AM)
- **Work Hours**: Use "Eco Mode" when away during work hours (9 AM-5 PM)
- **Evening Comfort**: Schedule "Home Mode" for family time (6-10 PM)
- **Night Rest**: Use "Night Mode" for quiet overnight operation (10 PM-7 AM)
- **Weekend Away**: Schedule "Away Mode" for entire weekends when traveling
- **Cooking Events**: Create "Level 3" events during cooking times for extra ventilation

> [!TIP]
> Start with simple single events before creating complex recurring schedules. Test each event type to understand how your system responds.

> [!IMPORTANT]
> The Dantherm unit has built-in **Night Mode Start Time** and **Night Mode End Time**. Scheduling Night Mode outside of these times may not function as expected.

<img width="750" alt="Skærmbillede 2025-08-03 kl  17 25 42" src="https://github.com/user-attachments/assets/02a362f1-19c6-4fd0-94a9-e5be88ef986c" />

These features provide **seamless automation and intelligent airflow control**, ensuring the ventilation system adapts dynamically to both **planned schedules** and **real-time environmental conditions**. 🚀🏡🌱📅

#### Using Event Entities

The Dantherm event entities are useful when you want to react to discrete changes instead of continuously monitoring sensor values.

- **`alarm_event`** can be used to detect when a new alarm is raised.
- **`filter_event`** can be used to detect when the filter reaches warning level or needs replacement.

Each event entity stores the latest received event as its current state and exposes the event type as an attribute.

For `alarm_event`, event attributes include:
- `alarm_code` for the numeric alarm code
- `alarm_text` for the human-readable alarm description

The `event_type` attribute is still available for filtering automations by event category.

If Home Assistant **Recorder** is enabled, these event updates can also be reviewed later in the entity history, which makes them useful for tracking alarm occurrences and filter-related events over time.

Typical use cases include:

- Sending a notification when a new alarm is triggered
- Creating a maintenance reminder when the filter reaches warning or expired state
- Triggering automations only when a specific event type occurs
- Reviewing past alarm or filter events in Home Assistant history

#### Automation Examples

```yaml
automation:
  - alias: Dantherm alarm triggered
    triggers:
      - trigger: event.received
        target:
          entity_id: event.dantherm_alarm_event
        options:
          event_type:
            - alarm_exhaust_air
            - alarm_fire
            - alarm_fire_protection
            - alarm_bypass_damper
            - alarm_high_waterlevel
            - alarm_supply_air
            - alarm_supply_temperature
            - alarm_supply_air_fan
            - alarm_communication_error
            - alarm_overtemperature
            - alarm_rh
            - alarm_room_air
            - alarm_outdoor_air
            - alarm_outdoor_temperature
            - alarm_extract_air
            - alarm_exhaust_air_fan
    actions:
      - action: notify.notify
        data:
          title: Dantherm alarm
          message: >
            Dantherm: {{ trigger.to_state.attributes.alarm_text }} (code: {{
            trigger.to_state.attributes.alarm_code }})
```

```yaml
automation:
  - alias: Dantherm filter reminder
    triggers:
      - trigger: event.received
        target:
          entity_id: event.dantherm_filter_event
        options:
          event_type:
            - filter_warning
            - filter_expired
    actions:
      - action: notify.notify
        data:
          message: >
            {% if trigger.to_state.attributes.event_type == 'filter_warning' %}
              Dantherm filter is getting close to replacement time. Remember to order new filters.
            {% else %}
              Dantherm filter has expired. Replace the filter now.
            {% endif %}
```

<!-- END:shared-section -->

## Disclaimer

The trademark "Dantherm" is owned by Dantherm Group A/S.

The trademark "Pluggit" is owned by Pluggit GmbH.

All product names, trademarks, and registered trademarks mentioned in this repository are the property of their respective owners.

#### I am not affiliated with Dantherm or Pluggit, except as the owner of a Dantherm HCV400 P2 unit.

### The author does not guarantee the functionality of this integration and is not responsible for any damage.

_Tvalley71_
