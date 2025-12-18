from django.contrib import admin
from doctors.models import Kinesiologist
from .models import Availability, Appointment

admin.site.register(Kinesiologist)


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ("id", "kinesiologist", "day", "start_time", "end_time")
    list_filter = ("kinesiologist", "day")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "kinesiologist", "patient_name", "date", "start_time", "end_time")
    list_filter = ("kinesiologist", "date")