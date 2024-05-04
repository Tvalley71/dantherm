# Dantherm 
Home Assistant integration for Dantherm ventilation units

Currently only support for Modbus over TCP/IP.

Known supported devices:
* HCV300 ALU
* HCV400 P2
* RCV320

> [!NOTE]
> The listed devices have been tested with the integration. Please don't hesitate to contact me, if you're aware of supported devices not included in the list.

### Controls and sensors

key | description
:--- | :---
operation_selection | Mode of operation selection
fan_level_selection | Fan level selection
week_program_selection | Week program selection<sup>*<sup>
bypass_damper | Bypass damper cover<sup>*<sup>
filter_lifetime | Input filter lifetime box
operation_mode | Operation mode sensor
alarm | Alarm sensor
fan_level | Fan level sensor
fan1_speed | Fan 1 speed sensor
fan2_speed | Fan 2 speed sensor
humidity | Humidity sensor<sup>*<sup>
air_quality | Air quality sensor<sup>*<sup>
exhaust_temperature | Exhaust temperature sensor
extract_temperature | Extract temperature sensor
supply_temperature | Supply temperature sensor
outdoor_temperature | Outdoor temperature sensor
filter_remain | Remaining filter time sensor
away_mode | Away mode switch
night_mode | Night mode switch
fireplace_mode | Fireplace mode switch
manual_bypass_mode | Manual bypass mode switch<sup>*<sup>
summer_mode| Summer mode switch
filter_reset | Reset remain filter time button
alarm_reset | Reset alarm button

_* Some of the entities may not install due to lack of support or installation in the particular unit._


### Installation

#### Installation via HACS (Home Assistant Community Store)

1. Ensure you have HACS installed and configured in your Home Assistant instance.
2. Open the HACS (Home Assistant Community Store) by navigating to **Configuration > Integrations > HACS.**
3. Click on **Integrations** and then click the **Explore & Add Repositories** button.
4. Search for "Dantherm" in the search bar.
5. Locate the "Dantherm Integration" repository and click on it.
6. Click the **Install** button.
7. Once installed, restart your Home Assistant instance.

#### Manual Installation

1. Navigate to your Home Assistant configuration directory.
* For most installations, this will be **'/config/'**.
2. Inside the configuration directory, create a new folder named **'custom_components'** if it does not already exist.
3. Inside the **'custom_components'** folder, create a new folder named **'dantherm'**.
4. Download the latest release of the Dantherm integration from the [releases page](./custom_components/dantherm) or clone the repository into the **'custom_components/dantherm'** directory:

```console
git clone https://github.com/Tvalley71/dantherm.git custom_components/dantherm
```
5. Once the files are in place, restart your Home Assistant instance.

### Configuration
After installation, add the Dantherm integration to your Home Assistant configuration.

1. In Home Assistant, go to **Configuration > Integrations.**
2. Click the **+** button to add a new integration.
3. Search for "Dantherm" and select it from the list of available integrations.
4. Follow the on-screen instructions to complete the integration setup.

![Skærmbillede 2024-05-04 090018](https://github.com/Tvalley71/dantherm/assets/83084467/f085a769-c55c-45f1-952e-6ee8884eaad1)
![Skærmbillede 2024-05-04 090125](https://github.com/Tvalley71/dantherm/assets/83084467/1a66e37c-3c0e-498d-995f-c2bb5c778f35)

### Support
If you encounter any issues or have questions regarding the Dantherm integration for Home Assistant, feel free to [open an issue](https://github.com/Tvalley71/dantherm/issues/new)
 on this repository. I welcome contributions and feedback from the community.

### Screenshots

![Skærmbillede 2024-05-04 090219](https://github.com/Tvalley71/dantherm/assets/83084467/fa9b31b6-5ec8-4c3b-a381-ef7061495560)
![Skærmbillede 2024-05-04 090422](https://github.com/Tvalley71/dantherm/assets/83084467/7e82d596-c97d-4c5f-af01-e005f9ee352c)

![Skærmbillede 2024-05-04 090259](https://github.com/Tvalley71/dantherm/assets/83084467/12caf89b-5431-4cde-8210-54c69022eb2f)
![Skærmbillede 2024-05-04 090321](https://github.com/Tvalley71/dantherm/assets/83084467/ba8a8a7c-daaf-4fb0-a9cc-e5997f6e98b3)

> [!NOTE]
> Preheater and HAC module functions are currently unsupported due to limited testing possibilities. If support for these functions are desired, please contact me for potential collaborative efforts to provide the support.

### Languages

Currently supported languages:

Danish, English and French.

> [!NOTE]
> Want to help translate? Grab a language file on GitHub [here](./custom_components/dantherm/translations) and I'll include it in future releases! 

### Dashboard card

This is a modified version of a dashboard card posted by [@cronner](https://www.github.com/cronner) on Home Assistant Community. This will show alarms, filter remain level and change according to the current bypass state. Kinda like the Dantherm app.

![Skærmbillede 2024-05-04 094821](https://github.com/Tvalley71/dantherm/assets/83084467/41410cd1-f8ae-4248-8efe-c193a54699ec)

![Skærmbillede 2024-05-04 094934](https://github.com/Tvalley71/dantherm/assets/83084467/9b8b8a14-1382-4a2e-b197-f7c7dfa2442e)

<details>

<summary>The details for the above dashboard card (challenging).</summary>

#### 

I might consider creating a custom card based on this in the future.

To integrate this into your dashboard, begin by downloading and extracting this [zip file](https://github.com/Tvalley71/dantherm/files/15209104/picture-elements-card.zip). Copy the contained files into the "www" folder within your configuration directory.

Next, insert the following code into your dashboard. If your Home Assistant setup uses a language other than English, make sure to modify the entity names in the code accordingly. You also need to create the below helper template sensor.

#### The code
```yaml

type: picture-elements
elements:
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
    entity: sensor.dantherm_operation_mode
    style:
      top: 45%
      left: 36%
      font-weight: bold
      text-align: center;
      font-size: 100%
  - type: state-label
    entity: sensor.dantherm_humidity
    style:
      top: 29%
      left: 48.5%
      font-size: 125%
  - type: state-label
    entity: sensor.dantherm_fan_level
    style:
      top: 29%
      left: 66.5%
      font-size: 125%
  - type: image
    entity: sensor.dantherm_filter_remain_level
    state_image:
      '0': /local/dantherm3.png
      '1': /local/dantherm4.png
      '2': /local/dantherm5.png
      '3': /local/dantherm6.png
    style:
      left: 0%
      top: 0%
      transform: scale(1,1)
  - type: conditional
    conditions:
      - entity: cover.dantherm_bypass_damper
        state:
          - closed
          - closing
    elements:
      - type: image
        image: /local/dantherm2.png
        style:
          left: 0%
          top: 0%
          transform: scale(1,1)
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
      - type: image
        image: /local/dantherm3.png
        style:
          left: 0%
          top: 0%
          transform: scale(1,1)
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
image: /local/dantherm1.png
```
#### Helper template sensor.
![Skærmbillede 2024-05-04 094747](https://github.com/Tvalley71/dantherm/assets/83084467/49b4e3b5-e419-458d-ada8-ffc3a92e0395)

</details>

Please be advised that the trademark "Dantherm" is owned by Dantherm Group A/S, a prominent supplier of climate control solutions.

I have no affiliation with Dantherm other than owning one of their units. The HCV400 P2.



Tvalley71


