"""Test the Dantherm helpers module."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from config.custom_components.dantherm.helpers import (
    as_dt,
    duration_dt,
    has_single_loaded_instance,
    parse_dt_or_date,
    rrule_trim_until,
)


class TestDateTimeHelpers:
    """Test date and time helper functions."""

    def test_as_dt_with_datetime(self) -> None:
        """Test as_dt with datetime input."""
        dt = datetime(2023, 10, 27, 12, 0, 0, tzinfo=UTC)
        result = as_dt(dt)
        assert result == dt
        assert result.tzinfo == UTC

    def test_as_dt_with_naive_datetime(self) -> None:
        """Test as_dt with naive datetime input."""
        dt = datetime(2023, 10, 27, 12, 0, 0)
        result = as_dt(dt)
        assert result.tzinfo == UTC
        assert result.replace(tzinfo=None) == dt

    def test_as_dt_with_date(self) -> None:
        """Test as_dt with date input."""
        d = date(2023, 10, 27)
        result = as_dt(d)
        expected = datetime(2023, 10, 27, 0, 0, 0, tzinfo=UTC)
        assert result == expected

    def test_duration_dt(self) -> None:
        """Test duration_dt function."""
        start = datetime(2023, 10, 27, 12, 0, 0)
        end = datetime(2023, 10, 27, 14, 30, 0)
        result = duration_dt(start, end)
        expected = timedelta(hours=2, minutes=30)
        assert result == expected

    def test_duration_dt_with_dates(self) -> None:
        """Test duration_dt with date inputs."""
        start = date(2023, 10, 27)
        end = date(2023, 10, 29)
        result = duration_dt(start, end)
        expected = timedelta(days=2)
        assert result == expected

    def test_parse_dt_or_date_datetime_string(self) -> None:
        """Test parse_dt_or_date with datetime string."""
        with patch(
            "config.custom_components.dantherm.helpers.parse_datetime"
        ) as mock_parse:
            mock_dt = datetime(2023, 10, 27, 12, 0, 0, tzinfo=UTC)
            mock_parse.return_value = mock_dt

            result = parse_dt_or_date("2023-10-27T12:00:00Z")
            assert result == mock_dt

    def test_parse_dt_or_date_date_string(self) -> None:
        """Test parse_dt_or_date with date string."""
        result = parse_dt_or_date("2023-10-27")
        expected = date(2023, 10, 27)
        assert result == expected

    def test_parse_dt_or_date_already_datetime(self) -> None:
        """Test parse_dt_or_date with datetime object."""
        dt = datetime(2023, 10, 27, 12, 0, 0, tzinfo=UTC)
        result = parse_dt_or_date(dt)
        assert result == dt

    def test_parse_dt_or_date_already_date(self) -> None:
        """Test parse_dt_or_date with date object."""
        d = date(2023, 10, 27)
        result = parse_dt_or_date(d)
        assert result == d


class TestRRuleHelpers:
    """Test RRULE helper functions."""

    def test_rrule_trim_until(self) -> None:
        """Test rrule_trim_until function."""
        rrule = "FREQ=DAILY;COUNT=10"
        until_dt = datetime(2023, 10, 30, 12, 0, 0, tzinfo=UTC)

        result = rrule_trim_until(rrule, until_dt)
        assert "UNTIL=20231030T120000Z" in result
        assert "COUNT=10" not in result


class TestInstanceHelpers:
    """Test instance management helper functions."""

    def test_has_single_loaded_instance_true(self) -> None:
        """Test has_single_loaded_instance returns True."""
        with patch(
            "config.custom_components.dantherm.helpers.active_instance_count"
        ) as mock_count:
            mock_count.return_value = 1

            result = has_single_loaded_instance(MagicMock())
            assert result is True

    def test_has_single_loaded_instance_false(self) -> None:
        """Test has_single_loaded_instance returns False."""
        with patch(
            "config.custom_components.dantherm.helpers.active_instance_count"
        ) as mock_count:
            mock_count.return_value = 2

            result = has_single_loaded_instance(MagicMock())
            assert result is False
