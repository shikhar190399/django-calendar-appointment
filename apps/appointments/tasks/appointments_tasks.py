from datetime import datetime, time, timedelta
from typing import List

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.appointments.models import Appointment

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17
SLOT_INTERVAL = timedelta(minutes=30)
WEEKDAY_RANGE = range(0, 5)  # Monday (0) through Friday (4)


def _make_aware(dt: datetime, tz) -> datetime:
    return dt if timezone.is_aware(dt) else timezone.make_aware(dt, tz)


def get_current_week_range() -> tuple[datetime, datetime]:
    """Return the timezone-aware start and end datetimes for the current work week."""
    now = timezone.localtime(timezone.now())
    tz = now.tzinfo

    week_start_date = now.date() - timedelta(days=now.weekday())
    week_start = _make_aware(datetime.combine(week_start_date, time(hour=BUSINESS_START_HOUR)), tz)
    week_end_date = week_start_date + timedelta(days=5)
    week_end = _make_aware(datetime.combine(week_end_date, time(hour=0)), tz)
    return week_start, week_end


def get_week_range(offset_weeks: int = 0) -> tuple[datetime, datetime]:
    """Return the start/end datetimes for the week offset from the current week."""
    current_start, current_end = get_current_week_range()
    if offset_weeks == 0:
        return current_start, current_end

    tz = current_start.tzinfo
    week_start = current_start + timedelta(weeks=offset_weeks)
    week_end_date = week_start.date() + timedelta(days=5)
    week_end = _make_aware(datetime.combine(week_end_date, time(hour=0)), tz)
    return week_start, week_end


def generate_business_slots(week_start: datetime) -> List[datetime]:
    """Generate 30-minute slots for the work week starting at week_start."""
    slots: List[datetime] = []
    tz = week_start.tzinfo
    start_date = week_start.date()

    for weekday in WEEKDAY_RANGE:
        day_date = start_date + timedelta(days=weekday)
        day_start = _make_aware(datetime.combine(day_date, time(hour=BUSINESS_START_HOUR)), tz)
        current_slot = day_start
        closing_slot = _make_aware(datetime.combine(day_date, time(hour=BUSINESS_END_HOUR)), tz)

        while current_slot <= closing_slot:
            slots.append(current_slot)
            current_slot += SLOT_INTERVAL
    return slots


def serialize_appointment(appointment: Appointment) -> dict:
    start_time = timezone.localtime(appointment.start_time)
    created_at = timezone.localtime(appointment.created_at)
    return {
        "id": appointment.id,
        "start_time": start_time.isoformat(),
        "name": appointment.name,
        "email": appointment.email,
        "phone": appointment.phone or "",
        "reason": appointment.reason or "",
        "created_at": created_at.isoformat(),
    }


def validate_slot(slot: datetime) -> None:
    now = timezone.now()
    if slot < now:
        raise ValidationError("Cannot book an appointment in the past.")

    local_slot = timezone.localtime(slot)
    if local_slot.weekday() not in WEEKDAY_RANGE:
        raise ValidationError("Appointments are only available Monday through Friday.")

    if local_slot.minute not in {0, 30}:
        raise ValidationError("Appointments must start on the half-hour.")

    if local_slot.hour < BUSINESS_START_HOUR:
        raise ValidationError("Appointment must fall within business hours (9am-5pm).")

    if local_slot.hour > BUSINESS_END_HOUR:
        raise ValidationError("Appointment must fall within business hours (9am-5pm).")

    if local_slot.hour == BUSINESS_END_HOUR and local_slot.minute != 0:
        raise ValidationError("Appointment must fall within business hours (9am-5pm).")


def parse_start_time(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValidationError("Invalid datetime format. Use ISO 8601 (e.g. 2024-01-01T13:30:00Z).")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def get_future_slots(weeks_ahead: int = 2) -> List[datetime]:
    """Return combined slots for the current week and the following `weeks_ahead - 1` weeks."""
    slots: List[datetime] = []
    for offset in range(weeks_ahead):
        week_start, _ = get_week_range(offset)
        slots.extend(generate_business_slots(week_start))
    return slots


__all__ = [
    "BUSINESS_START_HOUR",
    "BUSINESS_END_HOUR",
    "SLOT_INTERVAL",
    "WEEKDAY_RANGE",
    "generate_business_slots",
    "get_current_week_range",
    "get_week_range",
    "get_future_slots",
    "parse_start_time",
    "serialize_appointment",
    "validate_slot",
]