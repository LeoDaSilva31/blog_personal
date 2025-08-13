from django.urls import path
from . import views

urlpatterns = [
    path('', views.landingpage_home, name='landingpage_home'),
]
