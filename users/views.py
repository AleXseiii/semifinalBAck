from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import PatientRegisterSerializer, PatientLoginSerializer, PatientProfileSerializer
from users.models import Patient
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from .serializers import PatientProfileSerializer
from rest_framework import status
from rest_framework import serializers
from .models import Patient



from rest_framework.response import Response

class PatientRegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PatientRegisterSerializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            with transaction.atomic():
                patient = serializer.save()
                token, _ = Token.objects.get_or_create(user=patient.user)

                return Response({
                    "status": True,
                    "message": "Paciente Registrado Correctamente"
                }, status=status.HTTP_201_CREATED)
        
        return Response({
            "status":False,
            "errors":serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST)
    
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_patient_profile(request):
    patient = Patient.objects.get(user=request.user)

    patient.name = request.data.get("name", patient.name)
    patient.phone_number = request.data.get("phone_number", patient.phone_number)
    patient.save()

    request.user.email = request.data.get("email", request.user.email)
    request.user.save()

    return Response({
        "name": patient.name,
        "rut": patient.rut,
        "email": request.user.email,
        "phone_number": patient.phone_number,
    })


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def patient_profile(request):
    patient = Patient.objects.get(user=request.user)

    if request.method == "GET":
        serializer = PatientProfileSerializer(patient)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = PatientProfileSerializer(
            patient,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    

