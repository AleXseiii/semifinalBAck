from django.urls import path

from .views import KinesiologistListCreateView

urlpatterns = [
    path('kinesiologists', KinesiologistListCreateView.as_view(), name='doctor-list'),
]
