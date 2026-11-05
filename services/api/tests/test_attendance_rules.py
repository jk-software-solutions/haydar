from datetime import UTC, datetime, time
from uuid import uuid4

from app.api.v1.attendance import remote_period_is_closed
from app.models.organization import Shift


def make_shift(location_policy: str | None) -> Shift:
    return Shift(
        id=uuid4(),
        company_id=uuid4(),
        code="REMOTE",
        name="Remote shift",
        start_time=time(9, 0),
        end_time=time(17, 0),
        is_overnight=False,
        working_days=[0, 1, 2, 3, 4, 5, 6],
        grace_period_minutes=15,
        break_duration_minutes=0,
        effective_from=datetime.now(UTC).date(),
        recurrence={"location_policy": location_policy} if location_policy else {},
    )


def test_remote_period_closes_at_scheduled_end() -> None:
    scheduled_end = datetime(2026, 9, 24, 14, 0, tzinfo=UTC)
    assert remote_period_is_closed(
        make_shift("location_not_required"), scheduled_end, scheduled_end
    )
    assert not remote_period_is_closed(
        make_shift("location_not_required"),
        datetime(2026, 9, 24, 13, 59, tzinfo=UTC),
        scheduled_end,
    )


def test_location_required_shift_is_not_closed_by_remote_rule() -> None:
    scheduled_end = datetime(2026, 9, 24, 14, 0, tzinfo=UTC)
    assert not remote_period_is_closed(
        make_shift("branch_geofence"),
        datetime(2026, 9, 24, 15, 0, tzinfo=UTC),
        scheduled_end,
    )
