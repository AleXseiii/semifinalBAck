"""clinic_backend URL Configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('doctors.urls')),
    path('api/', include('users.urls')),
    path('api/', include('auth_user.urls')),
    path('api/', include('scheduling.urls')),
]
