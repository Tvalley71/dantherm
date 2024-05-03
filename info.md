# Dantherm 
Home Assistant integration for Dantherm ventilation units

Currently only support for Modbus over TCP/IP.

Known supported devices:
* HCV400 P2
* RCV320

> [!NOTE]
> The listed devices have been tested with the integration. Please don't hesitate to contact me, if you're aware of supported devices not included in the list.

### Controls and sensors

key | description
:--- | :---
operation_selection | Mode of operation selection
fan_level_selection | Fan level selection
week_program_selection | Week program selection[^1]
bypass_damper | Bypass damper cover[^1]
filter_lifetime | Input filter lifetime box
operation_mode | Operation mode sensor
alarm | Alarm sensor
fan_level | Fan level sensor
fan1_speed | Fan 1 speed sensor[^2]
fan2_speed | Fan 2 speed sensor[^2]
humidity | Humidity sensor[^1][^3]
air_quality | Air quality sensor[^1][^3]
exhaust_temperature | Exhaust temperature sensor
extract_temperature | Extract temperature sensor
supply_temperature | Supply temperature sensor
outdoor_temperature | Outdoor temperature sensor
filter_remain | Remaining filter time sensor
away_mode | Away mode switch
night_mode | Night mode switch
fireplace_mode | Fireplace mode switch
manual_bypass_mode | Manual bypass mode switch[^1]
summer_mode| Summer mode switch
filter_reset | Reset remain filter time button
alarm_reset | Reset alarm button

[^1]: The entity's existence hinges upon the support or installation of the particular sensor within the unit.
[^2]: Fan speeds 1 and 2 is the fan speed for either the extract or supply side, with the specific side varying across the different models.
[^3]: The humidity and air quality is measured in the extract side of the unit.

![Skærmbillede 2024-05-01 170232](https://github.com/Tvalley71/dantherm/assets/83084467/0f98cc7d-dbce-478c-836f-aecfe0bfb92c)

![Skærmbillede 2024-05-01 170253](https://github.com/Tvalley71/dantherm/assets/83084467/563a84f6-5158-411b-8ebb-13c68728b272)

![Skærmbillede 2024-05-01 170317](https://github.com/Tvalley71/dantherm/assets/83084467/2a56a4f0-0016-4797-a0ca-f352082f716c)

The bypass damper cover

![Skærmbillede 2024-05-01 170504](https://github.com/Tvalley71/dantherm/assets/83084467/1997bd58-a07a-4c32-b3f2-f96c16acda69)

> [!NOTE]
> The functions of the Preheater and HAC-module are currently unsupported due to lack of testing possibilities. If these functions are desired, please contact me, and we may provide support in collaboration.

### Languages

Currently supported languages:

Danish, English and French

> [!NOTE]
> Please feel free to grab one of the language files on Github [here](./custom_components/dantherm/translations) and translate it to your language and I will include .

Installation

HACS


