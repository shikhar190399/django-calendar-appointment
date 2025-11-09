from django.core.validators import MaxLengthValidator
from django.db import models


class Appointment(models.Model):
    """Stores appointment bookings for 30-minute slots."""

    start_time = models.DateTimeField(unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    reason = models.CharField(
        max_length=200,
        blank=True,
        validators=[MaxLengthValidator(200)],
        help_text="Optional notes about the appointment.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.start_time:%Y-%m-%d %H:%M} - {self.name}"
