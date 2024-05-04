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

#### Installation
![Skærmbillede 2024-05-04 090018](https://github.com/Tvalley71/dantherm/assets/83084467/164fa28f-2fd6-40dc-99fd-7f94f9cb20a5)

#### Success and area assignment
![Skærmbillede 2024-05-04 090125](https://github.com/Tvalley71/dantherm/assets/83084467/dc00e751-08ce-40ca-b30b-6f60b73e9708)

#### Device Info
![Skærmbillede 2024-05-04 090219](https://github.com/Tvalley71/dantherm/assets/83084467/37ab062e-9239-4efa-b87c-7d823c576a8e)

#### Controls
![Skærmbillede 2024-05-04 090259](https://github.com/Tvalley71/dantherm/assets/83084467/6b9fd2e8-0ab6-48c2-8d2b-293d13f39ea2)

#### Sensors
![Skærmbillede 2024-05-04 090321](https://github.com/Tvalley71/dantherm/assets/83084467/4769978f-6f27-4768-8e58-5eb9c27ad59d)

#### Bypass damper cover
![Skærmbillede 2024-05-04 090422](https://github.com/Tvalley71/dantherm/assets/83084467/701b3ec5-98f8-4a78-bf3c-d06e1b8d7b25)


> [!NOTE]
> Preheater and HAC module functions are currently unsupported due to limited testing possibilities. If support for these functions are desired, please contact me for potential collaborative efforts to provide the support.


### Languages

Currently supported languages:

Danish, English and French.

> [!NOTE]
> Want to help translate? Grab a language file on GitHub [here](./custom_components/dantherm/translations) and I'll include it in future releases! 


### Installation

HACS

### Dashboard card

This is a modified version of a dashboard card posted by @cronner on Home Assistant Community. This will show alarms, filter remain level and change according to the current bypass state. Kinda like the Dantherm app.

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
![Skærmbillede 2024-05-04 094747](https://github.com/Tvalley71/dantherm/assets/83084467/f006ff96-9fd3-4b12-9b04-5d972830112c)

</details>


Tvalley71


