from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from rest_framework import serializers

from .models import Kinesiologist


class KinesiologistSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    generated_password = serializers.SerializerMethodField()

    class Meta:
        model = Kinesiologist
        fields = [
            'id',
            'name',
            'rut',
            'specialty',
            'phone_number',
            'box',
            'email',
            'description',
            'generated_password',
        ]
        read_only_fields = ['id', 'generated_password']

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado.")
        return value

    def validate_phone_number(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("El número de teléfono solo puede contener dígitos.")
        return value

    def validate_box(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("El box es obligatorio.")
        return value
    
    def validate_description(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("La Descripción es obligatorio.")
        return value

    def create(self, validated_data):
        email = validated_data.pop('email')
        name = validated_data['name']
        password = get_random_string(length=12)

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )

        kinesiologist = Kinesiologist.objects.create(user=user, **validated_data)
        kinesiologist.generated_password = password
        return kinesiologist

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['email'] = instance.user.email
        password = getattr(instance, 'generated_password', None)
        if password is None:
            data.pop('generated_password', None)
        return data

    def get_generated_password(self, obj):
        return getattr(obj, 'generated_password', None)
