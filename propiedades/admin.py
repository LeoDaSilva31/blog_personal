from django.contrib import admin
from .models import Propiedad, PropiedadImagen

class PropiedadImagenInline(admin.TabularInline):
    model = PropiedadImagen
    extra = 3
    max_num = 10
    verbose_name = "Imagen adicional"
    verbose_name_plural = "Imágenes adicionales"
    fields = ('imagen', 'descripcion_corta')
    readonly_fields = ()
    help_text = "Subí hasta 10 imágenes adicionales para la propiedad."

@admin.register(Propiedad)
class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'tipo_operacion', 'precio_usd', 'localidad', 'is_destacada', 'estado_publicacion')
    list_filter = ('tipo', 'tipo_operacion', 'is_destacada', 'estado_publicacion')
    search_fields = ('titulo', 'descripcion', 'direccion', 'localidad', 'provincia')
    ordering = ('-fecha_actualizacion',)
    inlines = [PropiedadImagenInline]

    fieldsets = (
        ("Información General", {
            'fields': ('titulo', 'descripcion', 'tipo', 'tipo_operacion', 'imagen_principal', 'is_destacada', 'estado_publicacion'),
            'description': "Datos principales para mostrar en el sitio."
        }),
        ("Detalles de la Propiedad", {
            'fields': ('precio_usd', 'precio_pesos', 'direccion', 'localidad', 'provincia', 'pais'),
            'description': "Ubicación y precios."
        }),
        ("Características", {
            'fields': ('metros_cuadrados_total', 'metros_cuadrados_cubierta', 'dormitorios', 'banios', 'cocheras', 'antiguedad', 'amenidades'),
            'description': "Datos técnicos y amenidades."
        }),
        ("Fechas", {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Agregar placeholders personalizados para que sea más claro para el usuario
        form.base_fields['titulo'].widget.attrs.update({'placeholder': 'Ejemplo: Casa en barrio Palermo'})
        form.base_fields['descripcion'].widget.attrs.update({'placeholder': 'Descripción detallada de la propiedad'})
        form.base_fields['direccion'].widget.attrs.update({'placeholder': 'Calle, número, piso, departamento'})
        form.base_fields['localidad'].widget.attrs.update({'placeholder': 'Ejemplo: Buenos Aires'})
        form.base_fields['provincia'].widget.attrs.update({'placeholder': 'Ejemplo: Ciudad Autónoma de Buenos Aires'})
        form.base_fields['precio_usd'].widget.attrs.update({'placeholder': 'Solo números, sin símbolos'})
        form.base_fields['precio_pesos'].widget.attrs.update({'placeholder': 'Solo números, sin símbolos'})
        form.base_fields['metros_cuadrados_total'].widget.attrs.update({'placeholder': 'Ejemplo: 120'})
        form.base_fields['metros_cuadrados_cubierta'].widget.attrs.update({'placeholder': 'Ejemplo: 90'})
        form.base_fields['dormitorios'].widget.attrs.update({'placeholder': 'Ejemplo: 3'})
        form.base_fields['banios'].widget.attrs.update({'placeholder': 'Ejemplo: 2'})
        form.base_fields['cocheras'].widget.attrs.update({'placeholder': 'Ejemplo: 1'})
        form.base_fields['antiguedad'].widget.attrs.update({'placeholder': 'Ejemplo: 10 años'})
        form.base_fields['amenidades'].widget.attrs.update({'placeholder': 'Ejemplo: pileta, gimnasio, parque'})
        return form
