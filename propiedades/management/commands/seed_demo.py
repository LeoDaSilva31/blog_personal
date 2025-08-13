# propiedades/management/commands/seed_demo.py
import os
import io
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from propiedades.models import Propiedad, PropiedadImagen


# =========================
# Configuración general
# =========================

# Conversión aproximada solicitada
USD_ARS = Decimal("1300")
# % de publicaciones en USD
USD_RATIO = 0.30  # 30%

# Fallback de imágenes dentro del repo (commiteables)
DEFAULT_DEMO_DIR = (
    Path(settings.BASE_DIR)
    / "propiedades"
    / "static"
    / "propiedades"
    / "demo_images"
)

# Directorios donde BUSCAR imágenes (en orden de prioridad)
BASE_IMAGE_DIRS = [
    Path(settings.MEDIA_ROOT) / "propiedades" / "imagenes_principal",
    Path(settings.MEDIA_ROOT) / "propiedades" / "galeria",
    Path(os.getenv("DEMO_IMAGE_DIR", str(DEFAULT_DEMO_DIR))).resolve(),
]

# Extensiones aceptadas
EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# ==== DATOS BASE (texto) ====
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


class Command(BaseCommand):
    help = (
        "Genera 50 propiedades de prueba con imágenes WebP. "
        "Usa MEDIA/propiedades/{imagenes_principal,galeria}, luego static/propiedades/demo_images/, "
        "y si no hay, crea placeholders."
    )

    # ============== Helpers ==============

    def _collect_demo_images(self):
        """Busca imágenes en MEDIA primero y luego en static demo_images."""
        files = []
        for d in BASE_IMAGE_DIRS:
            if d.exists():
                files.extend(
                    [p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in EXTS]
                )
        return files

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """
        Redondea 'value' al múltiplo más cercano de 'step' (500 o 1000).
        """
        if step <= 0:
            return value.quantize(Decimal("1."), rounding=ROUND_HALF_UP)
        q = (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (q * step).quantize(Decimal("1"))

    def convert_to_webp_content(self, img: Image.Image, quality: int = 85) -> ContentFile:
        """
        Convierte una PIL.Image a WebP y devuelve ContentFile listo para guardar.
        """
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="WEBP", quality=quality)
        buf.seek(0)
        return ContentFile(buf.read())

    def convert_path_to_webp_content(self, path: Path, quality: int = 85) -> ContentFile:
        """
        Abre la imagen desde 'path', la convierte a WebP y devuelve ContentFile.
        """
        img = Image.open(path).convert("RGB")
        return self.convert_to_webp_content(img, quality=quality)

    def make_placeholder(self, w=1280, h=720, text="DEMO"):
        """
        Genera una imagen placeholder con degradé y texto.
        """
        # degradé simple azul
        base = Image.new("RGB", (w, h), (10, 70, 140))
        top = Image.new("RGB", (w, h), (30, 150, 220))
        mask = Image.linear_gradient("L").resize((w, h))
        img = Image.composite(top, base, mask)

        draw = ImageDraw.Draw(img)
        # Intento de tipografía del sistema; si falla, usa default
        try:
            font = ImageFont.truetype("arial.ttf", size=int(h * 0.08))
        except Exception:
            font = ImageFont.load_default()

        tw, th = draw.textbbox((0, 0), text, font=font)[2:]
        draw.text(((w - tw) / 2, (h - th) / 2), text, fill=(255, 255, 255), font=font)
        return img

    # ============== Handler principal ==============

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Buscando imágenes de demo..."))
        imagenes_archivos = self._collect_demo_images()
        if imagenes_archivos:
            self.stdout.write(self.style.SUCCESS(f"Se encontraron {len(imagenes_archivos)} imágenes de demo."))
        else:
            self.stdout.write(self.style.WARNING("No se encontraron imágenes. Se usarán placeholders."))

        self.stdout.write(self.style.WARNING("Eliminando propiedades previas..."))
        Propiedad.objects.all().delete()

        self.stdout.write(self.style.WARNING("Cargando 50 propiedades de prueba..."))

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
                # USD enteros entre 400 y 2000
                precio_usd = Decimal(random.randint(400, 2000))
                precio_pesos = None
            else:
                # ARS desde un equivalente en USD * 1300
                if tipo_operacion == "alquiler":
                    usd_equivalente = Decimal(random.randint(200, 1200))
                else:
                    usd_equivalente = Decimal(random.randint(30000, 250000))

                pesos = usd_equivalente * USD_ARS
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
                pais="Argentina",
                acepta_mascotas=random.choice([True, False]),
                tipo_mascota_permitida=random.choice([t[0] for t in Propiedad.TIPO_MASCOTA_CHOICES]),
                metros_cuadrados_total=Decimal(random.randint(120, 900)),    # enteros
                metros_cuadrados_cubierta=Decimal(random.randint(40, 500)),  # enteros
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

            # -------- Imagen principal --------
            if imagenes_archivos:
                src = random.choice(imagenes_archivos)
                webp_cf = self.convert_path_to_webp_content(src)
                propiedad.imagen_principal.save(
                    f"{propiedad.id}_principal.webp", webp_cf, save=True
                )
            else:
                # Placeholder
                img = self.make_placeholder(text="PROPIEDAD")
                webp_cf = self.convert_to_webp_content(img)
                propiedad.imagen_principal.save(
                    f"{propiedad.id}_principal.webp", webp_cf, save=True
                )

            # -------- Imágenes adicionales (2 a 4) --------
            add_count = random.randint(2, 4)
            for _ in range(add_count):
                if imagenes_archivos:
                    src = random.choice(imagenes_archivos)
                    webp_cf = self.convert_path_to_webp_content(src)
                else:
                    img = self.make_placeholder(w=1024, h=600, text="GALERÍA")
                    webp_cf = self.convert_to_webp_content(img)

                PropiedadImagen.objects.create(
                    propiedad=propiedad,
                    imagen=webp_cf,
                    descripcion_corta="Imagen ilustrativa",
                )

        self.stdout.write(self.style.SUCCESS("✅ 50 propiedades de prueba cargadas con imágenes y precios."))

