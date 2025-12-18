from django.urls import path
from .views import (
    AppointmentCreateView,
    AvailabilityListCreateView,
    KinesiologistAvailableSlotsView,
    patient_appointments_history,
    KinesiologistUpcomingAppointmentsView,
    AppointmentStatusView,
    AppointmentCommentView,
)

app_name = "scheduling"

urlpatterns = [
    # Disponibilidad del kinesiólogo
    path(
        'kinesiologists/<int:kinesiologist_id>/availability/',
        AvailabilityListCreateView.as_view(),
        name='kinesiologist-availability',
    ),

    # Crear citas
    path(
        'kinesiologists/<int:kinesiologist_id>/appointments/',
        AppointmentCreateView.as_view(),
        name='kinesiologist-appointments',
    ),

    # Slots disponibles para pacientes
    path(
        'kinesiologists/<int:kinesiologist_id>/slots/',
        KinesiologistAvailableSlotsView.as_view(),
        name='kinesiologist-slots',
    ),

    # Historial del paciente (logueado)
    path(
        "patients/appointments/history/",
        patient_appointments_history,
        name="patient-history",
    ),

    # ✅ NUEVO: Panel kinesiólogo → próximas consultas
    path(
        "kinesiologist/appointments/upcoming/",
        KinesiologistUpcomingAppointmentsView.as_view(),
        name="kinesiologist-upcoming",
    ),

    # ✅ NUEVO: Confirmar / Cancelar cita
    path(
        "appointments/<int:appointment_id>/status/",
        AppointmentStatusView.as_view(),
        name="appointment-status",
    ),

    # ✅ NUEVO: Comentario → marca sesión como realizada
    path(
        "appointments/<int:appointment_id>/comment/",
        AppointmentCommentView.as_view(),
        name="appointment-comment",
    ),
]
