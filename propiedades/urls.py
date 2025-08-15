from django.urls import path
from . import views 
from propiedades.views import contacto_view

app_name = 'propiedades'

urlpatterns = [
    path('', views.home, name='home'),
    path('lista/', views.propiedad_list_view, name='lista'),
    path('<int:pk>/', views.detalle_propiedad, name='detalle'),
    path('busqueda/', views.busqueda_propiedades, name='busqueda'),
    path("contacto/", contacto_view, name="contacto"),
]
