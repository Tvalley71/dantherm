# Dantherm

Home Assistant integration for Dantherm ventilation units.

> [!TIP]
> The integration also exist in a version for Pluggit ventilation units [here](https://github.com/Tvalley71/pluggit).

<!-- START:shared-section -->

<a href="https://www.buymeacoffee.com/tvalley71" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

### ⚠️ Compatibility Notice

This custom integration requires:

- Home Assistant version **2025.1.0** or newer

Only support for Modbus over TCP/IP.

<!-- END:shared-section -->

Known supported units:

- HCV300 ALU
- HCV700 ALU
- HCV400 P2
- HCV460 P2/E1
- RCV320 P1/P2
- HCH5 MKII
- RCC220 P2

<!-- START:shared-section -->

<!-- START:shared-section no-replace -->
The listed units are known to work with this integration. Basically, all units compatible with the **_Dantherm Residential_** or **_Pluggit iFlow_** apps should work with the integration as well.
<!-- END:shared-section -->

> [!NOTE]  
> If you have a model not listed and are using this integration, please let me know by posting [here](https://github.com/Tvalley71/dantherm/discussions/new?category=general). Make sure to include both the model name and the unit type number.  
> The number can be found in the **Device Info** section on the integration page; if the unit is not recognized, it will be listed as "Unknown" followed by the number.


### Controls and sensors

#### Buttons Entities

| Entity            | Description       |
|-------------------|-------------------|
| `alarm_reset`     | Clears the active alarm and dismis the alarm notification |
| `filter_reset`    | Resets the filter remain timer and dismis the alarm notification |

#### Calendar Entity

| Entity         | Description              |
|----------------|--------------------------|
| ~~`calendar`~~ | ~~Controls scheduled operations based on Home Assistant calendar events~~  |

#### Cover Entity

| Entity           | Description              |
|------------------|--------------------------|
| `bypass_damper`  | Indicates and controls the manual bypass state of the bypass damper [[1]](#entity-notes) |

#### Number Entities

| Entity                      | Description                        |
|-----------------------------|------------------------------------|
| `boost_mode_timeout`        | Sets the duration for Boost Mode before it automatically turns off [[3]](#entity-notes) |
| `bypass_minimum_temperature`| Minimum outdoor temperature allowed for bypass damper to open [[2][5]](#entity-notes) |
| `bypass_maximum_temperature`| Maximum outdoor temperature allowed for bypass damper to open [[2][5]](#entity-notes) |
| `eco_mode_timeout`          | Sets the duration for Eco Mode before it automatically deactivates [[3]](#entity-notes) |
| `filter_lifetime`           | Expected lifetime of the filter before triggering a replacement notification [[2]](#entity-notes) |
| `home_mode_timeout`         | Sets how long Home Mode should remain active after being triggered [[3]](#entity-notes) |
| `manual_bypass_duration`    | Duration for which manual bypass remains active after user activation [[1][2][5]](#entity-notes) |

#### Select Entities

| Entity                      | Description                        |
|-----------------------------|------------------------------------|
| `boost_operation_selection` | Defines which mode to apply when Boost Mode is triggered [[3]](#entity-notes) |
| ~~`default_operation_selection`~~ | ~~Fallback mode used when no other mode is active~~ |
| `eco_operation_selection`   | Defines which mode to apply when Eco Mode is triggered [[3]](#entity-notes) |
| `fan_level_selection`       | Selects the current fan level (Level 0 to Level 4). _Level 0_ and _Level 4_ will timeout after a fixed period. |
| `home_operation_selection`  | Defines which mode to apply when Home Mode is triggered [[3]](#entity-notes) |
| `operation_selection`       | Selects the current mode of operation (Standby, Automatic, Manual, Week Program, Away Mode, Summer Mode, Fireplace Mode and Night Mode). _Night Mode_ is display only. _Standby_ and _Fireplace Mode_ will timeout after a fixed period. |
| `week_program_selection`    | Selects the active predefined week program (Week Program 1 to Week Program 11). _Week Program 11_ can be user defined but not through the integration. [[2]](#entity-notes) |

#### Sensor Entities

| Entity                        | Description                          |
|-------------------------------|--------------------------------------|
| `air_quality`                 | Measures air quality if the unit is equipped with a VOC or CO₂ sensor [[1]](#entity-notes) |
| `air_quality_level`           | Indicates the qualitative level of air quality (Clean, Polluted, etc.) [[2]](#entity-notes) |
| `alarm`                       | Reports active alarms such as fan or temperature alarms |
| `exhaust_temperature`         | Temperature of indoor air being exhausted after heat recovery |
| `extract_temperature`         | Temperature of indoor air being pulled out for heat recovery |
| `fan_level`                   | Current fan level (Level 0 to Level 4) |
| `fan1_speed`                  | Actual RPM of fan 1 [[2]](#entity-notes) |
| `fan2_speed`                  | Actual RPM of fan 2 [[2]](#entity-notes) |
| `filter_remain`               | Remaining filter life in days |
| `filter_remain_level`         | Qualitative status of remaining filter life (e.g. Good, Replace) [[2]](#entity-notes) |
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

![Skærmbillede 2024-05-04 090018](https://github.com/user-attachments/assets/a5c2faad-2b96-438b-a761-4e24075efbf3)
![Skærmbillede 2024-05-04 090125](https://github.com/user-attachments/assets/7869346c-04e0-4980-9536-bf2cdd27cbc0)

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

![new](https://github.com/user-attachments/assets/1b21d1a8-e2a1-4589-87b0-eccf9697678c)
The picture elements card has been updated with fresh images and options to include humidity and air quality sensors with changing level icons _(2025-6-29)_.

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

To integrate this into your dashboard, begin by downloading and extracting this <!-- END:shared-section -->[zip file](https://github.com/user-attachments/files/21031201/dantherm.zip)<!-- START:shared-section -->. Copy the contained files into the "www" folder within your configuration directory on Home Assistant. You can use the _Samba share_ add-on, the upload feature in the _Studio Code Server_ add-on, or other preferred methods.

Next, insert the following code into your dashboard. If your Home Assistant setup uses a language other than English, make sure to modify the entity names in the code accordingly. You also need to enable the `filter_remain_level`, `humidity_level` and `air_quality_level` sensors if these options are included.

#### The code

```yaml

type: picture-elements
image: /local/dantherm1.png
elements:
  - type: image
    entity: sensor.dantherm_filter_remain_level
    state_image:
      "0": /local/dantherm4.png
      "1": /local/dantherm5.png
      "2": /local/dantherm6.png
      "3": /local/dantherm7.png
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
          closed: /local/dantherm2.png
          closing: /local/dantherm2.png
          open: /local/dantherm3.png
          opening: /local/dantherm3.png
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
        image: /local/dantherm8.png
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
#      "0": /local/dantherm9.png
#      "1": /local/dantherm10.png
#      "2": /local/dantherm11.png
#      "3": /local/dantherm12.png
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
#      "0": /local/dantherm13.png
#      "1": /local/dantherm14.png
#      "2": /local/dantherm15.png
#      "3": /local/dantherm16.png
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
     - **Targets:** Choose the area, device, or entity to apply the action.
     - **Operation Selection:** Set the desired operating mode (e.g., Standby, Automatic, Manual, or Week Program).
     - **Fan Selection:** Choose the desired fan level (Level 0–4).
     - **Modes:** Toggle special modes like:
       - **Away Mode**: Enable or disable away mode.
       - **Summer Mode**: Turn summer mode on or off.
       - **Fireplace Mode**: Activate fireplace mode for a limited period.
       - **Manual Bypass Mode**: Enable or disable manual bypass.

![Skærmbillede fra 2025-02-09 14-46-28](https://github.com/user-attachments/assets/679f4582-4fcf-4adf-bb71-6042409aadb9)

5. **Save the Automation:**
   - Once configured, save the automation. The Dantherm unit will now respond to the specified trigger and perform the desired action.

The **Dantherm: Set configuration** action allows you to adjust various configuration settings of your Dantherm device directly from Home Assistant. This action can be used in automations, scripts, or manually through the Developer Tools.

![Skærmbillede fra 2025-02-09 14-49-25](https://github.com/user-attachments/assets/2fad1928-d028-45cb-9bea-147944adf2ab)


## Integration enhancements

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
![Skærmbillede 23-04-2025 kl  07 04 48 AM](https://github.com/user-attachments/assets/185aca8c-7d31-4f1b-925e-4088829e9e13)
3. Click the Configure button (gear icon) for your Dantherm integration instance.
4. The options dialog will open, where you can adjust the available settings.
![Skærmbillede 13-07-2025 kl  07 15 56 AM](https://github.com/user-attachments/assets/8e985613-1fb2-414c-b237-0f1d99256c93)

#### How to Set Up an Adaptive Trigger

1. Enter the trigger entity in the appropriate field.  
Use the field for the mode you want to configure (e.g., Boost Mode Trigger, Eco Mode Trigger, or Home Mode Trigger).  
Example values:  
`binary_sensor.kitchen_motion`, `binary_sensor.living_room_presence`, `binary_sensor.outdoor_temperature_low`
2. Click Submit to save your configuration.
3. Enable the corresponding mode in the Home Assistant UI to activate the trigger.

Once configured, the Dantherm unit will automatically switch to the selected **operation mode** whenever the **Adaptive Trigger** becomes active. ⚡

#### Disabling "Unknown" Temperatures in Bypass and Summer Mode
To prevent temperature sensors from being set to unknown during bypass or summer mode, enable the option "Disable setting temperatures to unknown in bypass/summer modes".
When this option is enabled, temperature sensors will always report their current value, even when the device is in bypass or summer mode.

#### Disabling Notifications
To disable all persistent notifications from the Dantherm integration, enable "Disable notifications".
When this option is enabled, the integration will not send any persistent notifications to Home Assistant’s notification area.


## ⏳ The following sections are a work in progress  
These features are planned for version **1.0.0**. The calendar function is currently still under development.


### Calendar Function 📅  
The Calendar Function allows precise scheduling of different operation modes, providing full automation of the ventilation system.  

- **Integration - Calendar Events**:  
  By entering an event word into the **summary** of a calendar event, the selected operation will take effect when the event starts, assuming it has a **higher priority** event words than an ongoing event. When the event ends, the system will revert to the **previously active event**. If no underlying event exists, the unit will revert to the **Default Operation Selection**.

- **Event Words**: You can schedule "**Level 1**", "**Level 2**", "**Level 3**", "**Automatic**", "**Away Mode**", "**Night Mode**", "**Boost Mode**", "**Home Mode**", "**Eco Mode**", and "**Week Program**". These terms will be translated according to the selected language in Home Assistant, assuming your language is supported by the integration.
  
  - If **Level 1** to **Level 3** is scheduled, the unit will run in Manual mode at the selected fan level.
  - If **Automatic** is scheduled, the unit will operate in Demand Mode.
  - If **Away Mode** is scheduled, Away Mode will be **enabled at the start** and **disabled at the end** of the event.
  - If **Night Mode** is scheduled, Night Mode will be **enabled at the start** and **disabled at the end** of the event.
  - If **Boost Mode**, **Home Mode**, or **Eco Mode** is scheduled, the respective mode’s trigger will be **enabled at the start** and **disabled at the end**, allowing the unit to switch modes dynamically.
  - If **Week Program** is scheduled, the unit will follow the selected program in **Week Program Selection**.

- **Priority System**: The following is the **priority order** for calendar scheduling:  
  1. **Away Mode** (highest priority)  
  2. **Boost Mode**  
  3. **Night Mode**  
  4. **Home Mode**  
  5. **Eco Mode**  
  6. **Level 3**  
  7. **Level 2**  
  8. **Level 1**  
  9. **Automatic**  
  10. **Week Program** (lowest priority)  

The available operations in **Default Operation Selection** are **Automatic**, **Level 3**, **Level 2**, **Level 1**, or **Week Program**.

> [!IMPORTANT]
> The Dantherm unit has built-in **Night Mode Start Time** and **Night Mode End Time**. Scheduling Night Mode outside of these times may not function as expected.

<img width="517" height="486" alt="Skærmbillede 2025-08-03 kl  17 25 42" src="https://github.com/user-attachments/assets/02a362f1-19c6-4fd0-94a9-e5be88ef986c" />

These features provide **seamless automation and intelligent airflow control**, ensuring the ventilation system adapts dynamically to both **planned schedules** and **real-time environmental conditions**. 🚀🏡🌱📅

<!-- END:shared-section -->

## Disclaimer

The trademark "Dantherm" is owned by Dantherm Group A/S.

The trademark "Pluggit" is owned by Pluggit GmbH.

All product names, trademarks, and registered trademarks mentioned in this repository are the property of their respective owners.

#### I am not affiliated with Dantherm or Pluggit, except as the owner of a Dantherm HCV400 P2 unit.

### The author does not guarantee the functionality of this integration and is not responsible for any damage.

_Tvalley71_
