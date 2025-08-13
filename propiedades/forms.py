from django import forms
from .models import Propiedad

class PropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        fields = [
            'titulo', 'descripcion', 'tipo', 'tipo_operacion',
            'precio_usd', 'precio_pesos', 'direccion', 'localidad', 'provincia', 'pais',
            'metros_cuadrados_total', 'metros_cuadrados_cubierta', 'dormitorios', 'banios',
            'cocheras', 'antiguedad', 'amenidades', 'imagen_principal', 'is_destacada',
            'estado_publicacion', 'acepta_mascotas', 'tipo_mascota_permitida',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Título de la propiedad', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'placeholder': 'Descripción detallada', 'rows': 4, 'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Dirección completa', 'class': 'form-control'}),
            'localidad': forms.TextInput(attrs={'placeholder': 'Localidad', 'class': 'form-control'}),
            'provincia': forms.TextInput(attrs={'placeholder': 'Provincia', 'class': 'form-control'}),
            'pais': forms.TextInput(attrs={'placeholder': 'País', 'class': 'form-control'}),
            'amenidades': forms.Textarea(attrs={'placeholder': 'Separar amenidades con comas', 'rows': 3, 'class': 'form-control'}),
            'precio_usd': forms.NumberInput(attrs={'placeholder': 'Precio en USD', 'class': 'form-control'}),
            'precio_pesos': forms.NumberInput(attrs={'placeholder': 'Precio en Pesos', 'class': 'form-control'}),
            'metros_cuadrados_total': forms.NumberInput(attrs={'placeholder': 'Metros cuadrados total', 'class': 'form-control'}),
            'metros_cuadrados_cubierta': forms.NumberInput(attrs={'placeholder': 'Metros cuadrados cubierta', 'class': 'form-control'}),
            'dormitorios': forms.NumberInput(attrs={'placeholder': 'Cantidad de dormitorios', 'class': 'form-control'}),
            'banios': forms.NumberInput(attrs={'placeholder': 'Cantidad de baños', 'class': 'form-control'}),
            'cocheras': forms.NumberInput(attrs={'placeholder': 'Cantidad de cocheras', 'class': 'form-control'}),
            'antiguedad': forms.NumberInput(attrs={'placeholder': 'Años de antigüedad', 'class': 'form-control'}),
            # Los demás campos usarán select automáticamente para choices o checkbox para boolean
        }
