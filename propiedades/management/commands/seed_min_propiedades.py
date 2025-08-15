# propiedades/management/commands/seed_min_propiedades.py
import random
import io
from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

from PIL import Image, ImageDraw, ImageFont

from propiedades.models import Propiedad, PropiedadImagen

# ======= Catálogos / constantes =======
TITULOS = [
    "Casa en zona residencial",
    "Departamento con balcón y luz natural",
    "Terreno ideal inversión",
    "Local comercial sobre avenida",
    "Oficina equipada en el centro",
    "Galpón con doble altura",
    "Depósito con dock de carga",
    "Casa quinta con pileta",
]

LOCALIDADES = [
    "Quilmes", "Bernal", "Ezpeleta", "Avellaneda", "Lanús",
    "Lomas de Zamora", "Temperley", "Banfield", "Adrogué"
]

PROVINCIAS = ["Buenos Aires"]

AMENIDADES = [
    "Pileta", "Parque", "Gimnasio", "Parrilla", "Terraza",
    "Seguridad 24hs", "Cochera cubierta", "SUM", "Laundry",
]

# % de publicaciones en USD
DEFAULT_USD_RATIO = 0.30

# Conversión aprox para simular ARS desde un “equivalente” USD
USD_ARS = Decimal("1300")


def _round_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Redondea 'value' al múltiplo más cercano de 'step'."""
    if step <= 0:
        return value.quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    q = (value / step).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return (q * step).quantize(Decimal('1'))

def _text_wh(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """
    Devuelve (ancho, alto) del texto usando textbbox (Pillow 10+).
    """
    # textbbox devuelve (left, top, right, bottom)
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return (r - l, b - t)



def _make_webp_image(w=1280, h=800, title="Propiedad", subtitle=""):
    """
    Genera una imagen WEBP simple (placeholder) con fondo y textos.
    Devuelve un ContentFile listo para ImageField.save().
    """
    bg_colors = [
        (30, 64, 175), (3, 105, 161), (6, 95, 70),
        (124, 45, 18), (88, 28, 135), (15, 23, 42)
    ]
    img = Image.new("RGB", (w, h), color=random.choice(bg_colors))
    draw = ImageDraw.Draw(img)

    # Tipos de fuente: intentamos una más grande; si no, default
    try:
        # DejaVu suele venir con Pillow; si no está, cae al default
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
        subtitle_font = ImageFont.truetype("DejaVuSans.ttf", 24)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Marco
    margin = 40
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(255, 255, 255), width=3)

    # Recorte básico
    t = title[:48] + ("…" if len(title) > 48 else "")
    s = subtitle[:70] + ("…" if len(subtitle) > 70 else "")

    # Centrados aproximados
    tw, th = _text_wh(draw, t, title_font)
    sw, sh = _text_wh(draw, s, subtitle_font)

    draw.text(((w - tw) / 2, (h - th) / 2 - 24), t, fill=(255, 255, 255), font=title_font)
    draw.text(((w - sw) / 2, (h - sh) / 2 + 18), s, fill=(229, 231, 235), font=subtitle_font)

    bio = io.BytesIO()
    img.save(bio, format="WEBP", quality=85)
    bio.seek(0)
    return ContentFile(bio.read())


class Command(BaseCommand):
    help = "Genera propiedades de prueba 'realistas' con imágenes WebP (sube a S3 si está configurado)."

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=20, help="Cantidad de propiedades (default 20)")
        parser.add_argument("--truncate", action="store_true", help="Borrar previamente todas las propiedades")
        parser.add_argument("--usd_ratio", type=float, default=DEFAULT_USD_RATIO,
                            help="Proporción en USD (0..1). Default 0.30")
        parser.add_argument("--seed", type=int, default=None, help="Semilla para aleatoriedad")

    def handle(self, *args, **opts):
        n = opts["n"]
        usd_ratio = float(opts["usd_ratio"])
        if opts.get("seed") is not None:
            random.seed(int(opts["seed"]))

        if opts["truncate"]:
            self.stdout.write(self.style.WARNING("Eliminando propiedades previas..."))
            Propiedad.objects.all().delete()  # cascada borra imágenes

        self.stdout.write(self.style.WARNING(f"Creando {n} propiedades..."))

        created_ids = []

        for i in range(n):
            titulo = random.choice(TITULOS)
            tipo = random.choice([t[0] for t in Propiedad.TIPO_PROPIEDAD_CHOICES])
            tipo_operacion = random.choice([t[0] for t in Propiedad.TIPO_OPERACION_CHOICES])
            localidad = random.choice(LOCALIDADES)

            # --- Precios según operación/moneda ---
            precio_usd = None
            precio_pesos = None
            use_usd = (random.random() < usd_ratio)

            if tipo_operacion == 'alquiler':
                if use_usd:
                    # Alquiler mensual en USD
                    precio_usd = Decimal(random.randint(250, 1500))
                else:
                    # ARS desde equivalente USD
                    usd_equiv = Decimal(random.randint(200, 1200))
                    pesos = usd_equiv * USD_ARS
                    precio_pesos = _round_to_step(pesos, Decimal("10000"))
            else:  # venta
                if use_usd:
                    precio_usd = Decimal(random.randint(25000, 350000))
                else:
                    usd_equiv = Decimal(random.randint(30000, 300000))
                    pesos = usd_equiv * USD_ARS
                    precio_pesos = _round_to_step(pesos, Decimal("1000000"))

            descripcion = (
                f"{titulo} ubicada/o en {localidad}, {PROVINCIAS[0]}. "
                f"Excelente oportunidad por su estado y ubicación, con accesos "
                f"rápidos, transporte público cercano y servicios completos. "
                f"Ideal para {'familias' if tipo == 'casa' else 'uso profesional'}. \n\n"
                f"— Este aviso es de prueba, con datos meramente ilustrativos."
            )

            propiedad = Propiedad.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                tipo=tipo,
                tipo_operacion=tipo_operacion,
                precio_usd=precio_usd,
                precio_pesos=precio_pesos,
                direccion=f"Calle {random.randint(100, 999)}",
                localidad=localidad,
                provincia=random.choice(PROVINCIAS),
                acepta_mascotas=random.choice([True, False]),
                tipo_mascota_permitida=random.choice([t[0] for t in Propiedad.TIPO_MASCOTA_CHOICES]),
                metros_cuadrados_total=Decimal(random.randint(120, 900)),
                metros_cuadrados_cubierta=Decimal(random.randint(40, 500)),
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

            # Imagen principal (placeholder WebP)
            main_img = _make_webp_image(
                title=propiedad.titulo,
                subtitle=f"{propiedad.localidad} • {propiedad.tipo_operacion.capitalize()}"
            )
            propiedad.imagen_principal.save(f"{propiedad.id}_principal.webp", main_img, save=True)

            # Galería (2–4 imágenes)
            for _ in range(random.randint(2, 4)):
                gimg = _make_webp_image(
                    title="Galería",
                    subtitle=f"ID {propiedad.id} • {propiedad.localidad}"
                )
                PropiedadImagen.objects.create(
                    propiedad=propiedad,
                    imagen=ContentFile(gimg.read(), name=f"{propiedad.id}_{random.randint(1,9999)}.webp"),
                    descripcion_corta="Imagen ilustrativa"
                )

            created_ids.append(propiedad.id)

        self.stdout.write(self.style.SUCCESS(
            f"✅ Listo. Creadas: {len(created_ids)} (ej: {created_ids[:5]}...)"
        ))
