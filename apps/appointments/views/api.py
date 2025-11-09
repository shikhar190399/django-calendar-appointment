"""REST API views for managing appointment bookings."""

from datetime import datetime, timedelta
from typing import Set

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.appointments.tasks.appointments_tasks import (
    generate_business_slots,
    get_week_range,
    parse_start_time,
    serialize_appointment,
    validate_slot,
)


class AppointmentCollectionView(APIView):
    """List and create appointments scoped to a calendar week."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *args, **kwargs) -> Response:
        """Return appointments for the requested week (default: current)."""
        page_param = request.query_params.get("page", "0")
        try:
            week_offset = int(page_param)
        except (ValueError, TypeError):
            week_offset = 0
        week_offset = max(week_offset, 0)

        week_start, week_end = get_week_range(week_offset)

        appointments = (
            Appointment.objects.filter(start_time__gte=week_start, start_time__lt=week_end)
            .order_by("start_time")
        )
        data = [serialize_appointment(appt) for appt in appointments]

        week_start_local = timezone.localtime(week_start)
        week_end_local = timezone.localtime(week_end - timedelta(seconds=1))

        response_payload = {
            "page": week_offset,
            "week_start": week_start_local.date().isoformat(),
            "week_end": week_end_local.date().isoformat(),
            "appointments": data,
            "count": len(data),
            "has_previous": week_offset > 0,
            "previous_page": week_offset - 1 if week_offset > 0 else None,
            "next_page": week_offset + 1,
        }
        return Response(response_payload, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs) -> Response:
        """Create a new appointment enforcing validation rules."""
        try:
            payload = request.data or {}
            start_time_raw = payload.get("start_time")
            name = (payload.get("name") or "").strip()
            email = (payload.get("email") or "").strip()
            phone = (payload.get("phone") or "").strip()
            reason = (payload.get("reason") or "").strip()

            if not start_time_raw or not name or not email:
                raise ValidationError("start_time, name, and email are required fields.")

            validate_email(email)
            if len(reason) > 200:
                raise ValidationError("Reason cannot exceed 200 characters.")

            start_time = parse_start_time(start_time_raw)
            validate_slot(start_time)

            with transaction.atomic():
                appointment = Appointment.objects.create(
                    start_time=start_time,
                    name=name,
                    email=email,
                    phone=phone,
                    reason=reason,
                )

        except ValidationError as exc:
            message = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response(
                {"error": "This time slot has already been booked."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(serialize_appointment(appointment), status=status.HTTP_201_CREATED)


class AvailableSlotsView(APIView):
    """Expose paginated availability for booking slots."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *args, **kwargs) -> Response:
        """Return available slots for the specified week (default: current)."""
        page_param = request.query_params.get("page", "0")
        try:
            week_offset = int(page_param)
        except (ValueError, TypeError):
            week_offset = 0
        week_offset = max(week_offset, 0)

        week_start, week_end = get_week_range(week_offset)
        week_slots = generate_business_slots(week_start)

        booked_slots: Set[datetime] = set(
            Appointment.objects.filter(start_time__gte=week_start, start_time__lt=week_end).values_list(
                "start_time", flat=True
            )
        )

        now = timezone.now()
        is_current_week = week_offset == 0

        available_slots = []
        for slot in week_slots:
            if slot in booked_slots:
                continue
            if is_current_week and slot < now:
                continue
            available_slots.append(timezone.localtime(slot).isoformat())

        week_start_local = timezone.localtime(week_start)
        week_end_local = timezone.localtime(week_end - timedelta(seconds=1))

        response_payload = {
            "page": week_offset,
            "week_start": week_start_local.date().isoformat(),
            "week_end": week_end_local.date().isoformat(),
            "available_slots": available_slots,
            "count": len(available_slots),
            "has_previous": week_offset > 0,
            "previous_page": week_offset - 1 if week_offset > 0 else None,
            "next_page": week_offset + 1,
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class AppointmentDetailView(APIView):
    """Retrieve, update, or delete a single appointment."""

    authentication_classes: list = []
    permission_classes: list = []

    def get_object(self, appointment_id: int) -> Appointment:
        """Fetch an appointment or raise a validation error if missing."""
        try:
            return Appointment.objects.get(pk=appointment_id)
        except Appointment.DoesNotExist as exc:
            raise ValidationError("Appointment not found.") from exc

    def get(self, request, appointment_id: int, *args, **kwargs) -> Response:
        """Return serialized data for a single appointment."""
        try:
            appointment = self.get_object(appointment_id)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(serialize_appointment(appointment), status=status.HTTP_200_OK)

    def patch(self, request, appointment_id: int, *args, **kwargs) -> Response:
        """Partially update appointment details or reschedule to a free slot."""
        try:
            appointment = self.get_object(appointment_id)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data or {}
        allowed_fields = {"start_time", "name", "email", "phone", "reason"}
        unknown_keys = set(payload.keys()) - allowed_fields
        if unknown_keys:
            return Response(
                {"error": f"Unsupported fields supplied: {', '.join(sorted(unknown_keys))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_time_raw = payload.get("start_time")
        name = payload.get("name")
        email = payload.get("email")
        phone = payload.get("phone")
        reason = payload.get("reason")

        try:
            if start_time_raw is not None:
                parsed_time = parse_start_time(start_time_raw)
                validate_slot(parsed_time)
                conflicting = (
                    Appointment.objects.filter(start_time=parsed_time)
                    .exclude(pk=appointment.pk)
                    .exists()
                )
                if conflicting:
                    return Response(
                        {"error": "This time slot has already been booked."},
                        status=status.HTTP_409_CONFLICT,
                    )
                appointment.start_time = parsed_time

            if name is not None:
                name = name.strip()
                if not name:
                    raise ValidationError("Name cannot be blank.")
                appointment.name = name

            if email is not None:
                email = email.strip()
                if not email:
                    raise ValidationError("Email cannot be blank.")
                validate_email(email)
                appointment.email = email

            if phone is not None:
                appointment.phone = phone.strip()

            if reason is not None:
                reason = reason.strip()
                if len(reason) > 200:
                    raise ValidationError("Reason cannot exceed 200 characters.")
                appointment.reason = reason

            with transaction.atomic():
                appointment.save(update_fields=["start_time", "name", "email", "phone", "reason"])

        except ValidationError as exc:
            message = exc.messages[0] if hasattr(exc, "messages") else str(exc)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            return Response(
                {"error": "This time slot has already been booked."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(serialize_appointment(appointment), status=status.HTTP_200_OK)

    def delete(self, request, appointment_id: int, *args, **kwargs) -> Response:
        """Cancel an appointment."""
        try:
            appointment = self.get_object(appointment_id)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        appointment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
