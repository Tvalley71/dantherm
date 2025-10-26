"""Tests for Dantherm calendar priority system."""

from config.custom_components.dantherm.device_map import STATE_PRIORITIES


def test_priority_order_matches_documentation() -> None:
    """Test that priority system matches documentation order."""
    # Expected priority order from documentation (highest to lowest)
    expected_order = [
        "away",  # 1. Away Mode (highest priority)
        "boost",  # 2. Boost Mode
        "night",  # 3. Night Mode
        "home",  # 4. Home Mode
        "eco",  # 5. Eco Mode
        "level_3",  # 6. Level 3
        "level_2",  # 7. Level 2
        "level_1",  # 8. Level 1
        "automatic",  # 9. Automatic
        "week_program",  # 10. Week Program (lowest priority)
    ]

    # Get actual priorities from code
    priorities_by_value = {
        priority: state
        for state, priority in STATE_PRIORITIES.items()
        if state in expected_order
    }

    # Sort by priority value (highest to lowest)
    actual_order = [
        priorities_by_value[priority]
        for priority in sorted(priorities_by_value.keys(), reverse=True)
    ]

    assert actual_order == expected_order, (
        f"Priority order mismatch!\n"
        f"Expected: {expected_order}\n"
        f"Actual:   {actual_order}\n"
        f"STATE_PRIORITIES: {STATE_PRIORITIES}"
    )


def test_all_documented_states_have_priorities() -> None:
    """Test that all states mentioned in documentation have priorities defined."""
    documented_states = [
        "away",
        "boost",
        "night",
        "home",
        "eco",
        "level_3",
        "level_2",
        "level_1",
        "automatic",
        "week_program",
    ]

    for state in documented_states:
        assert state in STATE_PRIORITIES, (
            f"State '{state}' mentioned in documentation but not found in STATE_PRIORITIES"
        )


def test_priority_values_are_unique() -> None:
    """Test that priority values are unique (except for ties like standby/level_0)."""
    documented_states = [
        "away",
        "boost",
        "night",
        "home",
        "eco",
        "level_3",
        "level_2",
        "level_1",
        "automatic",
        "week_program",
    ]

    priorities = [STATE_PRIORITIES[state] for state in documented_states]

    assert len(priorities) == len(set(priorities)), (
        f"Priority values should be unique but found duplicates: {priorities}"
    )


def test_away_mode_has_highest_priority() -> None:
    """Test that Away Mode has the highest priority value."""
    away_priority = STATE_PRIORITIES["away"]

    for state, priority in STATE_PRIORITIES.items():
        if state != "away":
            assert priority < away_priority, (
                f"Away Mode should have highest priority, but '{state}' "
                f"has priority {priority} >= {away_priority}"
            )


def test_week_program_has_lowest_priority() -> None:
    """Test that Week Program has the lowest priority among documented states."""
    documented_states = [
        "away",
        "boost",
        "night",
        "home",
        "eco",
        "level_3",
        "level_2",
        "level_1",
        "automatic",
        "week_program",
    ]

    week_program_priority = STATE_PRIORITIES["week_program"]

    for state in documented_states:
        if state != "week_program":
            priority = STATE_PRIORITIES[state]
            assert priority > week_program_priority, (
                f"Week Program should have lowest priority, but '{state}' "
                f"has priority {priority} <= {week_program_priority}"
            )


def test_boost_mode_higher_than_eco_mode() -> None:
    """Test specific priority relationship mentioned in documentation example."""
    boost_priority = STATE_PRIORITIES["boost"]
    eco_priority = STATE_PRIORITIES["eco"]

    assert boost_priority > eco_priority, (
        f"Boost Mode (priority {boost_priority}) should have higher priority "
        f"than Eco Mode (priority {eco_priority}) as mentioned in documentation example"
    )
