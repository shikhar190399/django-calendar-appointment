from django.urls import path

from apps.appointments.views import (
    AppointmentCollectionView,
    AppointmentDetailView,
    AvailableSlotsView,
)

app_name = "appointments"

urlpatterns = [
    path("appointments", AppointmentCollectionView.as_view(), name="appointment-collection"),
    path("appointments/available", AvailableSlotsView.as_view(), name="appointment-available"),
    path(
        "appointments/<int:appointment_id>",
        AppointmentDetailView.as_view(),
        name="appointment-detail",
    ),
]
