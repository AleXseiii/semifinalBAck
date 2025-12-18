from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes

from datetime import datetime, timedelta
from datetime import date

from users.models import Patient
from doctors.models import Kinesiologist
from .models import Appointment, Availability
from .serializers import (
    AppointmentSerializer,
    AvailabilitySerializer,
    KinesiologistSummarySerializer,
    TimeSlotSerializer,
)

SLOT_MINUTES = 45


class AvailabilityListCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, kinesiologist_id: int):
        kinesiologist = get_object_or_404(Kinesiologist.objects.select_related('user'), pk=kinesiologist_id)

        availability_qs = (
            Availability.objects.filter(kinesiologist=kinesiologist)
            .order_by('day', 'start_time')
        )
        appointments_qs = (
            Appointment.objects.filter(kinesiologist=kinesiologist)
            .select_related('patient_name__user', 'kinesiologist__user')
            .order_by('date', 'start_time')
        )

        availability = AvailabilitySerializer(availability_qs, many=True)
        appointments = AppointmentSerializer(appointments_qs, many=True)
        kinesiologist_data = KinesiologistSummarySerializer(kinesiologist)

        return Response(
            {
                "kinesiologist": kinesiologist_data.data,
                "availability": availability.data,
                "appointments": appointments.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, kinesiologist_id: int):
        kinesiologist = get_object_or_404(Kinesiologist.objects.select_related('user'), pk=kinesiologist_id)

        if not (request.user.is_superuser or request.user == kinesiologist.user):
            return Response(
                {
                    "status": False,
                    "message": "No tiene permisos para registrar este horario.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AvailabilitySerializer(
            data=request.data,
            context={'kinesiologist': kinesiologist},
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                availability = serializer.save(kinesiologist=kinesiologist)
        except ValidationError as exc:
            message = getattr(exc, 'message', None) or getattr(exc, 'messages', [str(exc)])[0]
            return Response(
                {
                    "status": False,
                    "message": message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    "status": False,
                    "message": "No fue posible guardar el horario. Intente nuevamente.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": True,
                "message": "Horario registrado correctamente.",
                "availability": AvailabilitySerializer(availability).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AppointmentCreateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kinesiologist_id: int):
        kinesiologist = get_object_or_404(Kinesiologist.objects.select_related('user'), pk=kinesiologist_id)

        serializer = AppointmentSerializer(
            data=request.data,
            context={'kinesiologist': kinesiologist},
        )
        serializer.is_valid(raise_exception=True)

        patient = serializer.validated_data['patient_name']
        is_authorized = request.user.is_superuser or request.user == patient.user or request.user == kinesiologist.user
        if not is_authorized:
            return Response(
                {
                    "status": False,
                    "message": "No tiene permisos para agendar esta hora médica.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                appointment = serializer.save()
        except ValidationError as exc:
            message = getattr(exc, 'message', None) or getattr(exc, 'messages', [str(exc)])[0]
            return Response(
                {
                    "status": False,
                    "message": message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {
                    "status": False,
                    "message": "No fue posible agendar la hora médica. Intente nuevamente.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        appointment_data = AppointmentSerializer(appointment).data
        return Response(
            {
                "status": True,
                "message": "Hora médica reservada correctamente.",
                "appointment": appointment_data,
            },
            status=status.HTTP_201_CREATED,
        )


class KinesiologistAvailableSlotsView(APIView):
    """
    Devuelve los horarios disponibles de un kinesiólogo para una fecha dada.
    GET /api/kinesiologists/<kinesiologist_id>/slots/?date=YYYY-MM-DD
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, kinesiologist_id):
        date_str = request.query_params.get("date")
        if not date_str:
            return Response(
                {"detail": "Parámetro 'date' es obligatorio (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato de fecha inválido. Usa YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        day_of_week = target_date.weekday()

        availability_qs = Availability.objects.filter(
            kinesiologist_id=kinesiologist_id,
            day=day_of_week,
        )

        if not availability_qs.exists():
            return Response([], status=status.HTTP_200_OK)

        existing_appointments = Appointment.objects.filter(
            kinesiologist_id=kinesiologist_id,
            date=target_date,
        )

        slot_length = timedelta(minutes=SLOT_MINUTES)
        slots = []

        for avail in availability_qs:
            current_start = datetime.combine(target_date, avail.start_time)
            avail_end_dt = datetime.combine(target_date, avail.end_time)

            while current_start + slot_length <= avail_end_dt:
                current_end = current_start + slot_length

                overlap = existing_appointments.filter(
                    start_time__lt=current_end.time(),
                    end_time__gt=current_start.time(),
                ).exists()

                # si está cancelada, la hora se podría volver a usar (opcional)
                # si quieres permitirlo, cambia existing_appointments arriba para excluir canceladas
                if not overlap:
                    slots.append(
                        {
                            "date": target_date,
                            "start_time": current_start.time(),
                            "end_time": current_end.time(),
                            "datetime": current_start,
                        }
                    )

                current_start += slot_length

        serializer = TimeSlotSerializer(slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ✅ NUEVO: Próximas consultas del kinesiólogo
class KinesiologistUpcomingAppointmentsView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        kine = Kinesiologist.objects.filter(user=request.user).first()
        if not kine:
            return Response(
                {"status": False, "message": "El usuario no corresponde a un kinesiólogo."},
                status=status.HTTP_403_FORBIDDEN
            )

        today = timezone.localdate()
        now_time = timezone.localtime().time()

        qs = Appointment.objects.filter(
            kinesiologist=kine
        ).filter(
            Q(date__gt=today) | Q(date=today, start_time__gte=now_time)
        ).select_related("patient_name__user").order_by("date", "start_time")

        data = []
        for a in qs:
            patient_full_name = ""
            if hasattr(a.patient_name, "user") and a.patient_name.user:
                first = getattr(a.patient_name.user, "first_name", "") or ""
                last = getattr(a.patient_name.user, "last_name", "") or ""
                patient_full_name = (first + " " + last).strip()

            data.append({
                "appointment_id": a.id,
                "patient_id": a.patient_name.id,
                "patient_name": patient_full_name if patient_full_name else str(a.patient_name),
                "date": a.date.strftime("%Y-%m-%d"),
                "start_time": a.start_time.strftime("%H:%M"),
                "end_time": a.end_time.strftime("%H:%M"),
                "status": a.status,
                "status_label": a.get_status_display(),
            })

        return Response({"status": True, "appointments": data}, status=status.HTTP_200_OK)


# ✅ NUEVO: Confirmar/Cancelar cita (solo kinesiólogo asignado)
class AppointmentStatusView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment.objects.select_related("kinesiologist__user"), id=appointment_id)

        if request.user != appointment.kinesiologist.user:
            return Response(
                {"status": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get("status")
        if new_status not in ["confirmed", "cancelled"]:
            return Response(
                {"status": False, "message": "Estado inválido. Use 'confirmed' o 'cancelled'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = new_status
        appointment.save(update_fields=["status"])

        return Response(
            {"status": True, "message": f"Cita {appointment.get_status_display()}"},
            status=status.HTTP_200_OK
        )


# ✅ NUEVO: Comentario por sesión => marca como completed automáticamente
class AppointmentCommentView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, appointment_id):
        appointment = get_object_or_404(Appointment.objects.select_related("kinesiologist__user"), id=appointment_id)

        if request.user != appointment.kinesiologist.user:
            return Response(
                {"status": False, "message": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN
            )

        comment = request.data.get("kine_comment")
        if not comment or not str(comment).strip():
            return Response(
                {"status": False, "message": "El comentario es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.kine_comment = str(comment).strip()
        appointment.status = "completed"
        appointment.comment_updated_at = timezone.now()
        appointment.save(update_fields=["kine_comment", "status", "comment_updated_at"])

        return Response(
            {"status": True, "message": "Sesión marcada como realizada y comentario guardado."},
            status=status.HTTP_200_OK
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def patient_appointments_history(request):
    patient = Patient.objects.get(user=request.user)

    qs = (
        Appointment.objects
        .filter(patient_name=patient)
        .select_related("kinesiologist__user")
        .order_by("-date", "-start_time")
    )

    data = []
    for a in qs:
        data.append({
            "id": a.id,
            "date": a.date.strftime("%Y-%m-%d"),
            "time": a.start_time.strftime("%H:%M"),
            "treatment": "Sesión de kinesiología",
            "kinesiologist": a.kinesiologist.user.get_full_name() or a.kinesiologist.user.username,
            "status": a.status,
            "status_label": a.get_status_display(),
            "kine_comment": a.kine_comment or "",
            "comment_updated_at": a.comment_updated_at,
        })

    return Response(data, status=status.HTTP_200_OK)
