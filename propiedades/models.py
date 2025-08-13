from django.db import models

class Propiedad(models.Model):
    """
    Modelo para almacenar propiedades inmobiliarias.
    """

    # Tipos de propiedades más descriptivos para UI
    TIPO_PROPIEDAD_CHOICES = [
        ('casa', 'Casa'),
        ('apartamento', 'Apartamento'),
        ('terreno', 'Terreno'),
        ('local_comercial', 'Local Comercial'),
        ('oficina', 'Oficina'),
        ('galpon', 'Galpón'),
        ('deposito', 'Depósito'),
        ('otro', 'Otro'),
    ]

    TIPO_OPERACION_CHOICES = [
        ('venta', 'Venta'),
        ('alquiler', 'Alquiler'),
    ]

    titulo = models.CharField(
        max_length=200,
        help_text="Título descriptivo para la propiedad (Ej: Casa en zona céntrica)",
    )
    descripcion = models.TextField(
        help_text="Descripción completa de la propiedad."
    )
    tipo = models.CharField(
        max_length=50,
        choices=TIPO_PROPIEDAD_CHOICES,
        help_text="Selecciona el tipo de propiedad.",
    )
    tipo_operacion = models.CharField(
        max_length=50,
        choices=TIPO_OPERACION_CHOICES,
        help_text="Selecciona si es en venta o alquiler.",
    )

    precio_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio en dólares americanos (USD). Opcional.",
    )
    precio_pesos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio en pesos argentinos (ARS). Opcional.",
    )

    direccion = models.CharField(
        max_length=255,
        help_text="Dirección completa de la propiedad.",
    )
    localidad = models.CharField(
        max_length=100,
        help_text="Localidad o barrio donde se encuentra la propiedad.",
    )
    provincia = models.CharField(
        max_length=100,
        help_text="Provincia o estado.",
    )
    pais = models.CharField(
        max_length=100,
        default='Argentina',
        help_text="País donde está ubicada la propiedad.",
    )

    acepta_mascotas = models.BooleanField(
        default=False,
        help_text="Indica si la propiedad acepta mascotas.",
    )

    TIPO_MASCOTA_CHOICES = [
        ('no_especificado', 'No especificado'),
        ('perros', 'Perros'),
        ('gatos', 'Gatos'),
        ('otros', 'Otros'),
    ]

    tipo_mascota_permitida = models.CharField(
        max_length=20,
        choices=TIPO_MASCOTA_CHOICES,
        default='no_especificado',
        help_text="Tipo de mascota permitida en la propiedad.",
    )
    
    
    metros_cuadrados_total = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Metros cuadrados totales del terreno.",
    )
    metros_cuadrados_cubierta = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Metros cuadrados cubiertos (construidos).",
    )

    dormitorios = models.IntegerField(
        null=True,
        blank=True,
    )
    banios = models.IntegerField(
        null=True,
        blank=True,
    )
    cocheras = models.IntegerField(
        null=True,
        blank=True,
    )

    antiguedad = models.IntegerField(
        null=True,
        blank=True,
        help_text="Años de antigüedad de la propiedad.",
    )

    amenidades = models.TextField(
        blank=True,
        help_text="Lista de amenidades separadas por comas (Ej: pileta, parque, gimnasio).",
    )

    imagen_principal = models.ImageField(
        upload_to='propiedades/imagenes_principal/',
        null=True,
        blank=True,
        help_text="Imagen principal para mostrar en listados y detalle.",
    )

    is_destacada = models.BooleanField(
        default=False,
        help_text="Marcar para destacar esta propiedad en la página principal.",
    )

    ESTADO_PUBLICACION_CHOICES = [
        ('borrador', 'Borrador'),
        ('publicada', 'Publicada'),
        ('archivada', 'Archivada'),
    ]
    estado_publicacion = models.CharField(
        max_length=20,
        choices=ESTADO_PUBLICACION_CHOICES,
        default='borrador',
        help_text="Estado actual de publicación de la propiedad.",
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titulo} ({self.tipo}) - {self.localidad}"

class PropiedadImagen(models.Model):
    """
    Imágenes adicionales relacionadas a una propiedad.
    """
    propiedad = models.ForeignKey(
        Propiedad,
        on_delete=models.CASCADE,
        related_name='imagenes',
        help_text="Propiedad a la que pertenece esta imagen.",
    )
    imagen = models.ImageField(
        upload_to='propiedades/galeria/',
        help_text="Imagen adicional de la propiedad.",
    )
    descripcion_corta = models.CharField(
        max_length=100,
        blank=True,
        help_text="Breve descripción de la imagen.",
    )

    def __str__(self):
        return f"Imagen de {self.propiedad.titulo} (ID: {self.id})"
