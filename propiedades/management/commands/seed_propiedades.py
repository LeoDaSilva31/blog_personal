import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image
import io

from propiedades.models import Propiedad, PropiedadImagen

# ==== DATOS BASE ====
TITULOS = [
    "Casa en zona céntrica",
    "Departamento moderno con balcón",
    "Terreno ideal para inversión",
    "Local comercial sobre avenida principal",
    "Oficina amoblada en el centro",
    "Galpón industrial",
    "Depósito amplio",
    "Casa quinta con pileta",
]
LOCALIDADES = ["Quilmes", "Bernal", "Ezpeleta", "Avellaneda", "Lanús", "Lomas de Zamora"]
PROVINCIAS = ["Buenos Aires"]
AMENIDADES = [
    "Pileta", "Parque", "Gimnasio", "Parrilla", "Terraza", "Seguridad 24hs", "Cochera cubierta"
]

# Carpeta con las imágenes de ejemplo (ajustá si cambia)
IMAGENES_DIR = Path(r"C:\Users\ldasi\Pictures\ejemplo")

# Conversión aproximada solicitada
USD_ARS = Decimal("1300")

# % de publicaciones en USD
USD_RATIO = 0.30  # 30%


class Command(BaseCommand):
    help = "Genera 50 propiedades de prueba, con imágenes WebP y precios según reglas (ARS 70% / USD 30%)."

    def handle(self, *args, **kwargs):
        if not IMAGENES_DIR.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró la carpeta: {IMAGENES_DIR}"))
            return

        self.stdout.write(self.style.WARNING("Eliminando propiedades previas..."))
        Propiedad.objects.all().delete()

        self.stdout.write(self.style.WARNING("Cargando 50 propiedades de prueba..."))

        imagenes_archivos = list(IMAGENES_DIR.glob("foto*"))
        if not imagenes_archivos:
            self.stderr.write(self.style.ERROR("No se encontraron imágenes que empiecen con 'foto'"))
            return

        for i in range(50):
            titulo = random.choice(TITULOS)
            tipo = random.choice([t[0] for t in Propiedad.TIPO_PROPIEDAD_CHOICES])
            tipo_operacion = random.choice([t[0] for t in Propiedad.TIPO_OPERACION_CHOICES])  # venta/alquiler
            localidad = random.choice(LOCALIDADES)

            # --- Generación de precios ---
            precio_usd = None
            precio_pesos = None

            use_usd = random.random() < USD_RATIO  # 30% en USD

            if use_usd:
                # USD enteros entre 400 y 2000 (según tu pedido)
                precio_usd = Decimal(random.randint(400, 2000))
                precio_pesos = None
            else:
                # ARS a partir de un "equivalente USD" y conversión ~1300 ARS/USD
                # Rango razonable según operación:
                if tipo_operacion == 'alquiler':
                    usd_equivalente = Decimal(random.randint(200, 1200))  # alquiler mensual en USD "de referencia"
                else:
                    usd_equivalente = Decimal(random.randint(30000, 250000))  # venta en USD "de referencia"

                pesos = usd_equivalente * USD_ARS  # conversión aprox
                # Redondeo a múltiplos de 500 o 1000 (aleatorio)
                step = Decimal(random.choice([500, 1000]))
                precio_pesos = self._round_to_step(pesos, step)
                precio_usd = None

            propiedad = Propiedad.objects.create(
                titulo=titulo,
                descripcion=(
                    f"{titulo}. Los datos mostrados son ilustrativos y solo para pruebas. "
                    f"Esta publicación es de ejemplo."
                ),
                tipo=tipo,
                tipo_operacion=tipo_operacion,
                precio_usd=precio_usd,
                precio_pesos=precio_pesos,
                direccion=f"Calle {random.randint(1, 999)}",
                localidad=localidad,
                provincia=random.choice(PROVINCIAS),
                acepta_mascotas=random.choice([True, False]),
                tipo_mascota_permitida=random.choice(
                    [t[0] for t in Propiedad.TIPO_MASCOTA_CHOICES]
                ),
                metros_cuadrados_total=Decimal(random.randint(120, 900)),     # enteros por ahora
                metros_cuadrados_cubierta=Decimal(random.randint(40, 500)),   # enteros por ahora
                dormitorios=random.randint(1, 5),
                banios=random.randint(1, 3),
                cocheras=random.randint(0, 3),
                antiguedad=random.randint(0, 50),
                amenidades=", ".join(random.sample(AMENIDADES, random.randint(2, 5))),
                is_destacada=random.choice([True, False]),
                estado_publicacion="publicada",
                fecha_creacion=timezone.now(),
                fecha_actualizacion=timezone.now(),
            )

            # Imagen principal (convertir a WebP antes de guardar)
            img_path = random.choice(imagenes_archivos)
            webp_image = self.convert_to_webp(img_path)
            propiedad.imagen_principal.save(f"{propiedad.id}_principal.webp", webp_image, save=True)

            # Imágenes adicionales
            for _ in range(random.randint(2, 4)):
                img_path = random.choice(imagenes_archivos)
                webp_image = self.convert_to_webp(img_path)
                PropiedadImagen.objects.create(
                    propiedad=propiedad,
                    imagen=ContentFile(webp_image.read(), name=f"{propiedad.id}_{random.randint(1,9999)}.webp"),
                    descripcion_corta="Imagen ilustrativa"
                )

        self.stdout.write(self.style.SUCCESS("✅ 50 propiedades de prueba cargadas con reglas de precios actualizadas."))

    # ============== Helpers ==============

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """
        Redondea 'value' al múltiplo más cercano de 'step' (500 o 1000).
        """
        if step <= 0:
            return value.quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        # dividir por step, redondear al entero más cercano y volver a multiplicar
        q = (value / step).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return (q * step).quantize(Decimal('1'))

    def convert_to_webp(self, img_path):
        """Convierte una imagen a formato WebP y devuelve un ContentFile listo para guardar."""
        img = Image.open(img_path).convert("RGB")
        img_io = io.BytesIO()
        img.save(img_io, format="WEBP", quality=85)
        img_io.seek(0)
        return ContentFile(img_io.read(), name=f"{img_path.stem}.webp")
