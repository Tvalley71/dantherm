"""Test coverage for disabled entities in Dantherm integration."""

from config.custom_components.dantherm.device_map import (
    BUTTONS,
    COVERS,
    NUMBERS,
    SELECTS,
    SENSORS,
    SWITCHES,
    TIMETEXTS,
)

from homeassistant.const import EntityCategory


class TestDisabledEntityCoverage:
    """Test that disabled entities are properly defined and categorized."""

    def test_disabled_sensor_entities(self) -> None:
        """Test that disabled sensor entities are properly categorized."""
        disabled_sensors = [
            sensor.key
            for sensor in SENSORS
            if hasattr(sensor, "entity_registry_enabled_default")
            and not sensor.entity_registry_enabled_default
        ]

        expected_disabled_sensors = {
            "fan1_speed",
            "fan2_speed",
            "humidity_level",
            "air_quality_level",
            "room_temperature",
            "filter_remain_level",
            "work_time",
            "internal_preheater_dutycycle",
        }

        assert set(disabled_sensors) == expected_disabled_sensors, (
            f"Disabled sensors mismatch. Expected: {expected_disabled_sensors}, "
            f"Got: {set(disabled_sensors)}"
        )

        # Verify these are diagnostic/advanced sensors
        diagnostic_sensors = {
            "fan1_speed",
            "fan2_speed",
            "work_time",
            "internal_preheater_dutycycle",
            "filter_remain_level",
        }
        environmental_sensors = {
            "humidity_level",
            "air_quality_level",
            "room_temperature",
        }

        # All disabled sensors should be either diagnostic or environmental
        all_categorized = diagnostic_sensors | environmental_sensors
        assert set(disabled_sensors).issubset(all_categorized), (
            f"Uncategorized disabled sensors: {set(disabled_sensors) - all_categorized}"
        )

    def test_disabled_number_entities(self) -> None:
        """Test that disabled number entities are configuration settings."""
        disabled_numbers = [
            number.key
            for number in NUMBERS
            if hasattr(number, "entity_registry_enabled_default")
            and not number.entity_registry_enabled_default
        ]

        expected_disabled_numbers = {
            "filter_lifetime",
            "humidity_setpoint",
            "humidity_setpoint_summer",
            "bypass_minimum_temperature",
            "bypass_maximum_temperature",
            "manual_bypass_duration",
            "bypass_minimum_temperature_summer",
            "bypass_maximum_temperature_summer",
        }

        assert set(disabled_numbers) == expected_disabled_numbers, (
            f"Disabled numbers mismatch. Expected: {expected_disabled_numbers}, "
            f"Got: {set(disabled_numbers)}"
        )

        # These should all be advanced configuration settings
        config_categories = {
            "filter_": ["filter_lifetime"],
            "humidity_": ["humidity_setpoint", "humidity_setpoint_summer"],
            "bypass_": [
                "bypass_minimum_temperature",
                "bypass_maximum_temperature",
                "manual_bypass_duration",
                "bypass_minimum_temperature_summer",
                "bypass_maximum_temperature_summer",
            ],
        }

        categorized_numbers = set()
        for numbers in config_categories.values():
            categorized_numbers.update(numbers)

        assert set(disabled_numbers) == categorized_numbers, (
            "All disabled numbers should be categorized as config settings"
        )

    def test_disabled_select_entities(self) -> None:
        """Test that disabled select entities are advanced scheduling."""
        disabled_selects = [
            select.key
            for select in SELECTS
            if hasattr(select, "entity_registry_enabled_default")
            and not select.entity_registry_enabled_default
        ]

        expected_disabled_selects = {"week_program_selection"}

        assert set(disabled_selects) == expected_disabled_selects, (
            f"Disabled selects mismatch. Expected: {expected_disabled_selects}, "
            f"Got: {set(disabled_selects)}"
        )

        # This should be advanced scheduling
        assert "week_program_selection" in disabled_selects

    def test_disabled_timetext_entities(self) -> None:
        """Test that disabled timetext entities are scheduling related."""
        disabled_timetexts = [
            timetext.key
            for timetext in TIMETEXTS
            if hasattr(timetext, "entity_registry_enabled_default")
            and not timetext.entity_registry_enabled_default
        ]

        expected_disabled_timetexts = {
            "night_mode_start_time",
            "night_mode_end_time",
        }

        assert set(disabled_timetexts) == expected_disabled_timetexts, (
            f"Disabled timetexts mismatch. Expected: {expected_disabled_timetexts}, "
            f"Got: {set(disabled_timetexts)}"
        )

        # These should be night mode scheduling
        for timetext in disabled_timetexts:
            assert "night_mode" in timetext

    def test_disabled_switch_entities(self) -> None:
        """Test that disabled switch entities are advanced features."""
        disabled_switches = [
            switch.key
            for switch in SWITCHES
            if hasattr(switch, "entity_registry_enabled_default")
            and not switch.entity_registry_enabled_default
        ]

        expected_disabled_switches = {"disable_bypass"}

        assert set(disabled_switches) == expected_disabled_switches, (
            f"Disabled switches mismatch. Expected: {expected_disabled_switches}, "
            f"Got: {set(disabled_switches)}"
        )

        # This should be advanced bypass control
        assert "bypass" in disabled_switches[0]

    def test_no_disabled_buttons_or_covers(self) -> None:
        """Test that buttons and covers are not disabled by default."""
        disabled_buttons = [
            button.key
            for button in BUTTONS
            if hasattr(button, "entity_registry_enabled_default")
            and not button.entity_registry_enabled_default
        ]

        disabled_covers = [
            cover.key
            for cover in COVERS
            if hasattr(cover, "entity_registry_enabled_default")
            and not cover.entity_registry_enabled_default
        ]

        assert len(disabled_buttons) == 0, (
            f"Buttons should not be disabled by default: {disabled_buttons}"
        )
        assert len(disabled_covers) == 0, (
            f"Covers should not be disabled by default: {disabled_covers}"
        )

    def test_disabled_entity_percentages(self) -> None:
        """Test that disabled entity percentages are reasonable."""
        all_entities = (
            SENSORS + NUMBERS + SELECTS + TIMETEXTS + SWITCHES + BUTTONS + COVERS
        )

        total_disabled = 0
        platform_stats = {}

        for platform_name, entity_list in [
            ("sensors", SENSORS),
            ("numbers", NUMBERS),
            ("selects", SELECTS),
            ("timetexts", TIMETEXTS),
            ("switches", SWITCHES),
            ("buttons", BUTTONS),
            ("covers", COVERS),
        ]:
            disabled_count = sum(
                1
                for entity in entity_list
                if hasattr(entity, "entity_registry_enabled_default")
                and not entity.entity_registry_enabled_default
            )
            total_disabled += disabled_count
            platform_stats[platform_name] = {
                "total": len(entity_list),
                "disabled": disabled_count,
                "percentage": disabled_count / len(entity_list) * 100
                if entity_list
                else 0,
            }

        # Verify overall disabled percentage is reasonable (30-50%)
        total_entities = len(all_entities)
        overall_percentage = total_disabled / total_entities * 100

        assert 30 <= overall_percentage <= 50, (
            f"Overall disabled percentage should be 30-50%, got {overall_percentage:.1f}%"
        )

        # Verify that numbers and sensors have higher disabled percentages (config/diagnostic)
        assert platform_stats["numbers"]["percentage"] >= 50, (
            f"Numbers should have high disabled percentage (config), got {platform_stats['numbers']['percentage']:.1f}%"
        )

        assert platform_stats["sensors"]["percentage"] >= 30, (
            f"Sensors should have moderate disabled percentage (diagnostic), got {platform_stats['sensors']['percentage']:.1f}%"
        )

        # Verify that buttons and covers have low disabled percentages (user actions)
        assert platform_stats["buttons"]["percentage"] == 0, (
            "Buttons should not be disabled by default"
        )

        assert platform_stats["covers"]["percentage"] == 0, (
            "Covers should not be disabled by default"
        )

    def test_entity_category_consistency(self) -> None:
        """Test that disabled entities have appropriate entity categories."""
        # Check that diagnostic entities are properly categorized
        diagnostic_entities = []
        config_entities = []

        for entity_list in [
            SENSORS,
            NUMBERS,
            SELECTS,
            TIMETEXTS,
            SWITCHES,
            BUTTONS,
            COVERS,
        ]:
            for entity in entity_list:
                if (
                    hasattr(entity, "entity_registry_enabled_default")
                    and not entity.entity_registry_enabled_default
                ):
                    if hasattr(entity, "entity_category"):
                        if entity.entity_category == EntityCategory.DIAGNOSTIC:
                            diagnostic_entities.append(entity.key)
                        elif entity.entity_category == EntityCategory.CONFIG:
                            config_entities.append(entity.key)

        # Verify that diagnostic sensors are properly categorized
        expected_diagnostic = {
            "fan1_speed",
            "fan2_speed",
            "work_time",
            "internal_preheater_dutycycle",
            "filter_remain_level",
        }

        diagnostic_found = set(diagnostic_entities) & expected_diagnostic
        assert len(diagnostic_found) > 0, (
            f"Expected some diagnostic entities to be properly categorized, found: {diagnostic_entities}"
        )

        # Verify that config entities exist
        expected_config = {
            "filter_lifetime",
            "humidity_setpoint",
            "bypass_minimum_temperature",
            "week_program_selection",
            "night_mode_start_time",
            "disable_bypass",
        }

        config_found = set(config_entities) & expected_config
        assert len(config_found) > 0, (
            f"Expected some config entities to be properly categorized, found: {config_entities}"
        )
