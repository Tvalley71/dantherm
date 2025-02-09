# Dantherm

Home Assistant integration for Dantherm ventilation units

> [!TIP]
> The integration also exist in a version for Pluggit ventilation units [here](https://github.com/Tvalley71/pluggit).

Currently only support for Modbus over TCP/IP.

Known supported units:

- HCV300 ALU
- HCV700 ALU
- HCV400 P2
- HCV460 P2
- RCV320 P1/P2

> [!NOTE]
> The listed units are known to have been used with the integration. Basicly all units that use the _Dantherm Residential_ app ought to work with the integration
> ([Google Play](https://play.google.com/store/apps/details?id=com.dantherm.ventilation) or [Apple Store](https://apps.apple.com/dk/app/dantherm-residential/id1368468353)).
> If you know of any not included in the list, please feel free to contact me [here](https://github.com/Tvalley71/dantherm/discussions/new?category=general).

### Controls and sensors

| entity                       | description                           |
| :--------------------------- | :------------------------------------ |
| operation_selection          | Mode of operation selection           |
| fan_level_selection          | Fan level selection                   |
| week_program_selection       | Week program selection<sup>\* &dagger;<sup> |
| bypass_damper                | Bypass damper cover<sup>\*<sup>       |
| filter_lifetime              | Input filter lifetime box<sup>&dagger;<sup> |
| bypass_minimum_temperature   | Bypass minimum temperature slider<sup>&dagger;<sup> |
| bypass_maximum_temperature   | Bypass maximum temperature slider<sup>&dagger;<sup> |
| manual_bypass_duration       | Manual bypass duration slider<sup>\* &dagger;<sup> |
| operation_mode               | Operation mode sensor                 |
| alarm                        | Alarm sensor                          |
| fan_level                    | Fan level sensor                      |
| fan1_speed                   | Fan 1 speed sensor<sup>&dagger;<sup>  |
| fan2_speed                   | Fan 2 speed sensor<sup>&dagger;<sup>  |
| humidity                     | Humidity sensor<sup>\*<sup>           |
| air_quality                  | Air quality sensor<sup>\*<sup>        |
| exhaust_temperature          | Exhaust temperature sensor            |
| extract_temperature          | Extract temperature sensor            |
| supply_temperature           | Supply temperature sensor             |
| outdoor_temperature          | Outdoor temperature sensor            |
| room_temperature             | Room temperature sensor<sup>\* &dagger;<sup> |
| filter_remain                | Remaining filter time sensor          |
| filter_remain_level          | Remaining filter time sensor level<sup>&dagger;<sup> |
| work_time                    | Work time sensor<sup>&dagger;<sup>    |
| internal_preheater_dutycycle | Preheater power dutycycle<sup>\* &dagger;<sup> |
| away_mode                    | Away mode switch                      |
| night_mode                   | Night mode switch<sup>&dagger;<sup> |
| fireplace_mode               | Fireplace mode switch                 |
| manual_bypass_mode           | Manual bypass mode switch<sup>\*<sup> |
| summer_mode                  | Summer mode switch                    |
| filter_reset                 | Reset remain filter time button       |
| alarm_reset                  | Reset alarm button                    |
| night_mode_start_time        | Night mode start time text<sup>&dagger;<sup> |
| night_mode_end_time          | Night mode end time text<sup>&dagger;<sup> |

_\* Some of the entities may not install due to lack of support or installation in the particular unit._

_&dagger; The entity is disabled by default._

### Installation

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

### Configuration

After installation, add the Dantherm integration to your Home Assistant configuration.

1. In Home Assistant, go to **Configuration > Integrations.**
2. Click the **+** button to add a new integration.
3. Search for "Dantherm" and select it from the list of available integrations.
4. Follow the on-screen instructions to complete the integration setup.

![Skærmbillede 2024-05-04 090018](https://github.com/user-attachments/assets/a5c2faad-2b96-438b-a761-4e24075efbf3)
![Skærmbillede 2024-05-04 090125](https://github.com/user-attachments/assets/7869346c-04e0-4980-9536-bf2cdd27cbc0)


### Support

If you encounter any issues or have questions regarding the Dantherm integration for Home Assistant, feel free to [open an issue](https://github.com/Tvalley71/dantherm/issues/new) or [start a discussion](https://github.com/Tvalley71/dantherm/discussions) on this repository. I welcome any contributions or feedback.


### Screenshots

![Skærmbillede fra 2025-02-09 15-49-04](https://github.com/user-attachments/assets/81ded97a-ff08-41f6-8ac4-8042501e355d)

![Skærmbillede fra 2025-02-09 15-26-39](https://github.com/user-attachments/assets/f12ce875-5f48-47d2-a975-3872f6415c07)
![Skærmbillede fra 2025-02-09 15-27-48](https://github.com/user-attachments/assets/2ca03de0-a469-4b0e-b362-5f6d486d1f9e)

![Skærmbillede fra 2025-02-09 15-28-23](https://github.com/user-attachments/assets/0efe815a-51fb-4e4b-bee8-d62bea40d4a7)
![Skærmbillede fra 2025-02-09 15-28-58](https://github.com/user-attachments/assets/6c192224-03cf-4094-b944-942c7395cd5b)

![Skærmbillede fra 2025-02-09 15-31-03](https://github.com/user-attachments/assets/1d17f88b-c3f0-441a-917c-55bee87f287e)



> [!NOTE]
> The HAC module functions are currently unsupported due to limited testing possibilities. If support for these functions are desired, please contact me for potential collaborative efforts to provide the support.

### Languages

Currently supported languages:

Danish, Dutch, English, German and French.

> [!NOTE]
> Want to help translate? Grab a language file on GitHub [here](./custom_components/dantherm/translations) and post it [here](https://github.com/Tvalley71/dantherm/discussions/new?category=general). You are also welcome to submit a PR.

### Examples of use

#### Picture-elements card

This is a modified version of a dashboard card posted by [@cronner](https://www.github.com/cronner) on Home Assistant Community. This will show alarms, filter remain level and change according to the current bypass state. Kinda like the Dantherm app.

![Skærmbillede 2024-05-21 182357](https://github.com/Tvalley71/dantherm/assets/83084467/220edf94-71aa-4c29-abd4-c9ed191abd32)

![Skærmbillede 2024-05-21 182443](https://github.com/Tvalley71/dantherm/assets/83084467/91ab4cf7-d7cb-4df9-a602-0d8955203b70)

![Skærmbillede 2024-05-21 182154](https://github.com/Tvalley71/dantherm/assets/83084467/66fc2c18-7db1-403e-ae2b-fc32a4734d6d)


<details>

<summary>The details for the above picture-elements card (challenging).</summary>

####

I might consider creating a custom card based on this in the future.

To integrate this into your dashboard, begin by downloading and extracting this [zip file](https://github.com/Tvalley71/dantherm/files/15397672/picture-elements-card.zip). Copy the contained files into the "www" folder within your configuration directory on Home Assistant. You can use the _Samba share_ add-on, the upload feature in the _Studio Code Server_ add-on, or other preferred methods.

Next, insert the following code into your dashboard. If your Home Assistant setup uses a language other than English, make sure to modify the entity names in the code accordingly. You also need to enable the filter_remain_level sensor.

#### The code

```yaml

  - type: picture-elements
    image: /local/dantherm1.png
    elements:
      - type: image
        entity: sensor.dantherm_filter_remain_level
        state_image:
          '0': /local/dantherm4.png
          '1': /local/dantherm5.png
          '2': /local/dantherm6.png
          '3': /local/dantherm7.png
        style:
          transform: scale(1,1)
          left: 0%
          top: 0%
        tap_action:
          action: more-info
      - type: conditional
        conditions:
          - entity: switch.dantherm_summer_mode
            state: 'off'
        elements:
          - type: image
            entity: cover.dantherm_bypass_damper
            state_image:
              closed: /local/dantherm2.png
              closing: /local/dantherm2.png
              open: /local/dantherm3.png
              opening: /local/dantherm3.png
            style:
              left: 26.6%
              top: 50%
              transform: scale(0.693,0.693)
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
                  top: 64.5%
                  left: 78%
              - type: state-label
                entity: sensor.dantherm_extract_temperature
                style:
                  top: 64.5%
                  left: 49%
              - type: state-label
                entity: sensor.dantherm_exhaust_temperature
                style:
                  top: 81%
                  left: 78%
              - type: state-label
                entity: sensor.dantherm_supply_temperature
                style:
                  top: 81%
                  left: 49%
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
                  top: 64.5%
                  left: 49%
              - type: state-label
                entity: sensor.dantherm_outdoor_temperature
                style:
                  top: 81%
                  left: 78%
      - type: conditional
        conditions:
          - entity: switch.dantherm_summer_mode
            state: 'on'
        elements:
          - type: image
            image: /local/dantherm8.png
            style:
              left: 26.6%
              top: 50%
              transform: scale(0.693,0.693)
            tap_action:
              action: none
          - type: state-label
            entity: sensor.dantherm_extract_temperature
            style:
              top: 64.5%
              left: 49%
      - type: conditional
        conditions:
          - entity: sensor.dantherm_alarm
            state_not: '0'
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
          top: 45%
          left: 36%
          font-weight: bold
          font-style: italic
          text-align: center
          font-size: 100%
      - type: state-label
        entity: sensor.dantherm_humidity
        style:
          top: 29%
          left: 38%
          font-size: 100%
      - type: state-label
        entity: select.dantherm_fan_selection
        style:
          top: 29%
          left: 63%
          font-weight: bold
          font-style: italic
          font-size: 100%

```
</details>

#### Mushroom-chips card

An example of a Mushroom-chips card showing the current state of operation and fan level in a single display. This can also be achieved with many of the other entities.

![Skærmbillede 2024-05-21 104804](https://github.com/user-attachments/assets/2e35c5f9-46cf-4a77-a13c-56992ecccf3e)

<details>

<summary>Mushroom-chips card details.</summary>

####

The following cards need the _Mushroom_ frontend repository installed under HACS.

#### Mode of operation and fan level chips card (shown above)

```yaml

  - type: custom:mushroom-chips-card
    chips:
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.dantherm_fan_level
            state_not: unavailable
        chip:
          type: entity
          entity: sensor.dantherm_fan_level
          icon_color: blue

```

#### Alert chips card

Alert chip displaying any current alert along with its descriptions. A hold action is available to attempt resetting the alarm.

```yaml

  - type: custom:mushroom-chips-card
    chips:
      - type: conditional
        conditions:
          - condition: state
            entity: sensor.dantherm_alarm
            state_not: unavailable
          - condition: state
            entity: sensor.dantherm_alarm
            state_not: '0'
        chip:
          type: entity
          entity: sensor.dantherm_alarm
          icon_color: red
          hold_action:
            action: call-service
            service: button.press
            data: {}
            target:
              entity_id: button.dantherm_reset_alarm

```

</details>

> [!NOTE]
> Starting from version 2024.8 of Home Assistant, the new badges can be used to achieve same results as the Mushroom chips card.

#### Dashboard Badges

Here are some examples of badges added to the dashboard. The pop-up that appears when clicking on a badge will vary depending on the selected entities, either displaying information or enabling manipulation of the Dantherm unit.

![Skærmbillede badge example](https://github.com/user-attachments/assets/bbaac388-0e40-48cf-a0d1-7b42fb5a4234)

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

## Disclaimer

The trademark "Dantherm" is owned by Dantherm Group A/S.

The trademark "Pluggit" is owned by Pluggit GmbH.

All product names, trademarks, and registered trademarks mentioned in this repository are the property of their respective owners.

#### I am not affiliated with Dantherm or Pluggit, except as the owner of a Dantherm HCV400 P2 unit.

### The author does not guarantee the functionality of this integration and is not responsible for any damage.

_Tvalley71_
