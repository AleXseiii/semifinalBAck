from rest_framework import serializers

from doctors.models import Kinesiologist
from users.models import Patient
from .models import Appointment, Availability


class KinesiologistSummarySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Kinesiologist
        fields = ['id', 'name', 'rut', 'email', 'specialty', 'phone_number', 'box', 'image_url']
        read_only_fields = ['id', 'name', 'rut', 'email', 'specialty', 'phone_number', 'box', 'image_url']


class PatientSummarySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'name', 'rut', 'email', 'diagnostic', 'phone_number']
        read_only_fields = ['id', 'name', 'rut', 'email', 'diagnostic', 'phone_number']


class AvailabilitySerializer(serializers.ModelSerializer):
    day_display = serializers.CharField(source='get_day_display', read_only=True)

    class Meta:
        model = Availability
        fields = ['id', 'day', 'day_display', 'start_time', 'end_time']
        read_only_fields = ['id', 'day_display']

    def validate(self, attrs):
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start >= end:
            raise serializers.ValidationError("La hora de inicio debe ser anterior a la hora de término.")

        kinesiologist = self.context.get('kinesiologist')
        if kinesiologist:
            overlaps = Availability.objects.filter(
                kinesiologist=kinesiologist,
                day=attrs.get('day'),
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance:
                overlaps = overlaps.exclude(id=self.instance.id)
            if overlaps.exists():
                raise serializers.ValidationError("El horario se sobrepone con otro ya registrado.")
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.select_related('user'),
        source='patient_name',
        write_only=True,
    )
    kinesiologist = KinesiologistSummarySerializer(read_only=True)
    patient = PatientSummarySerializer(source='patient_name', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'date', 'start_time', 'end_time', 'patient_id', 'patient', 'kinesiologist']
        read_only_fields = ['id', 'patient', 'kinesiologist']

    def validate(self, attrs):
        start = attrs.get('start_time')
        end = attrs.get('end_time')
        if start >= end:
            raise serializers.ValidationError("La hora de inicio debe ser anterior a la hora de término.")
        return attrs

    def create(self, validated_data):
        kinesiologist = self.context['kinesiologist']
        appointment = Appointment.objects.create(
            kinesiologist=kinesiologist,
            **validated_data,
        )
        return appointment
    

class TimeSlotSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    datetime = serializers.DateTimeField()
