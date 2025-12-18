from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404

from .models import Kinesiologist
from .serializers import KinesiologistSerializer


class KinesiologistListCreateView(APIView):
    authentication_classes = [TokenAuthentication]

    def get_permissions(self):
        # GET público, resto privado
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        try:
            kinesiologists = Kinesiologist.objects.select_related('user').order_by('name')
            serializer = KinesiologistSerializer(kinesiologists, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {
                    "status": False,
                    "message": "No se pudo obtener la lista de kinesiólogos en este momento.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {"status": False, "message": "No tiene permisos para realizar esta acción."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = KinesiologistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                kinesiologist = serializer.save()
        except IntegrityError:
            return Response(
                {
                    "status": False,
                    "message": "Ocurrió un problema al crear el kinesiólogo. Intente nuevamente.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = KinesiologistSerializer(kinesiologist)
        return Response(
            {
                "status": True,
                "message": "Kinesiólogo creado correctamente.",
                "kinesiologist": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def kinesiologist_profile(request):
    """Perfil del kinesiólogo autenticado (igual a patient_profile, pero para kinesiólogos).

    GET  /api/kinesiologist/profile/
    PUT  /api/kinesiologist/profile/
    """
    kine = Kinesiologist.objects.filter(user=request.user).first()
    if not kine:
        return Response(
            {"status": False, "message": "El usuario no corresponde a un kinesiólogo."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "GET":
        # Serializador ya debería incluir email desde user (si no, lo agregamos)
        data = KinesiologistSerializer(kine).data
        # Asegurar campos mínimos que el front usa
        data.setdefault("email", getattr(request.user, "email", ""))
        return Response(data, status=status.HTTP_200_OK)

    # PUT (partial update)
    kine.name = request.data.get("name", kine.name)
    kine.phone_number = request.data.get("phone_number", kine.phone_number)
    kine.specialty = request.data.get("specialty", kine.specialty)
    kine.box = request.data.get("box", kine.box)
    kine.image_url = request.data.get("image_url", kine.image_url)
    kine.save()

    # También permitir actualizar el email del user
    new_email = request.data.get("email", None)
    if new_email is not None:
        request.user.email = new_email
        request.user.save(update_fields=["email"])

    data = KinesiologistSerializer(kine).data
    data.setdefault("email", getattr(request.user, "email", ""))
    return Response(data, status=status.HTTP_200_OK)
