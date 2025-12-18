from django.urls import path

from .views import KinesiologistListCreateView, kinesiologist_profile

urlpatterns = [
    path('kinesiologists', KinesiologistListCreateView.as_view(), name='doctor-list'),
    # Perfil del kinesiólogo autenticado
    path('kinesiologist/profile/', kinesiologist_profile, name='kinesiologist-profile'),
]
