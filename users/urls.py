from django.urls import path
from .views import PatientRegisterView
from .views import patient_profile
from .views import update_patient_profile

urlpatterns = [
    path('register', PatientRegisterView.as_view(), name="patient_register"),
    path("patient/profile/", patient_profile),
    path("api/patient/profile/", update_patient_profile),
    

]