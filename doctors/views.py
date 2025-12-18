from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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