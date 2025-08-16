# propiedades/management/commands/reset_and_seed_props.py
from __future__ import annotations

import os
import re
import random
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction, DataError, connection
from django.utils import timezone

from propiedades.models import Propiedad, PropiedadImagen


IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def _print_env(src: Path):
    engine = settings.DATABASES["default"]["ENGINE"]
    name = settings.DATABASES["default"].get("NAME", "")
    try:
        name = connection.settings_dict.get("NAME", name)
    except Exception:
        pass

    print("=== ENTORNO ===")
    print(f"Fecha: {timezone.now().isoformat()} (TZ={settings.TIME_ZONE})")
    print(f"DB ENGINE: {engine} | NAME={name}")
    print(f"USE_S3_MEDIA={getattr(settings, 'USE_S3_MEDIA', False)} | STORAGE={default_storage.__class__.__name__}")
    print(f"Origen: {str(src)}")


def _walk_media_prefix(prefix: str) -> List[str]:
    """
    Lista (recursivo) de archivos bajo un prefijo dentro del storage por defecto.
    Funciona tanto con FileSystemStorage como con S3Boto3Storage.
    """
    files: List[str] = []
    pending: List[str] = [prefix.rstrip("/") + "/"]
    while pending:
        base = pending.pop()
        try:
            dirs, fls = default_storage.listdir(base)
        except Exception:
            # Si el directorio no existe, salir silenciosamente
            continue
        for d in dirs:
            pending.append(f"{base}{d}/")
        for f in fls:
            files.append(f"{base}{f}")
    return files


def _purge_media_under_propiedades() -> int:
    """Elimina TODO archivo bajo 'propiedades/' del storage."""
    prefix = "propiedades"
    files = _walk_media_prefix(prefix)
    deleted = 0
    for f in files:
        try:
            default_storage.delete(f)
            deleted += 1
        except Exception:
            pass
    return deleted


def _copy_file_to_storage(src_file: Path, dest_relpath: str) -> str:
    """
    Copia un archivo desde el filesystem local (src_file) al storage por defecto,
    guardándolo con la ruta relativa dest_relpath. Retorna la ruta final guardada.
    """
    with src_file.open("rb") as fh:
        data = fh.read()
    # default_storage.save devuelve el nombre final (puede variar si existe)
    final_name = default_storage.save(dest_relpath, ContentFile(data))
    return final_name


def _chunked(lst: List[Path], size: int) -> List[List[Path]]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def _group_by_prefix(files: List[Path]) -> Dict[str, List[Path]]:
    """
    Agrupa por prefijo numérico NN_ o NN- (antes del primer '_' o '-') si existe.
    Si no hay prefijo numérico, usa el 'stem' completo como clave individual.
    """
    groups: Dict[str, List[Path]] = {}
    for p in files:
        m = re.match(r"^(\d+)[_\-\.].*$", p.stem)
        key = m.group(1) if m else p.stem
        groups.setdefault(key, []).append(p)
    # ordenar por clave numérica cuando aplique
    def keyfunc(k: str):
        try:
            return (0, int(k))
        except ValueError:
            return (1, k)
    out = dict(sorted(groups.items(), key=lambda kv: keyfunc(kv[0])))
    # dentro de cada grupo, ordenar por nombre
    for k in out:
        out[k] = sorted(out[k])
    return out


def _discover_groups(src: Path, mode: str, chunk: int) -> List[List[Path]]:
    """
    Devuelve una lista de grupos de imágenes.
    - subdirs: cada subcarpeta directa = un grupo (toma todas sus imágenes)
    - prefix : agrupa por prefijo numérico NN_... (o por nombre base)
    - chunk  : arma grupos de tamaño fijo `chunk` con el listado plano
    - auto   : si hay subcarpetas usa subdirs; si no, intenta prefix; sino chunk.
    """
    # ¿hay subcarpetas con imágenes?
    subdirs = [d for d in src.iterdir() if d.is_dir()]
    has_images_in_subdirs = any(any((f.suffix.lower() in IMG_EXTS) for f in d.iterdir() if f.is_file()) for d in subdirs)

    if mode == "subdirs" or (mode == "auto" and subdirs and has_images_in_subdirs):
        groups: List[List[Path]] = []
        for d in sorted(subdirs):
            files = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]
            if files:
                groups.append(sorted(files))
        return groups

    # plano
    flat = [p for p in src.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]
    flat = sorted(flat)

    if mode == "prefix" or mode == "auto":
        grouped = _group_by_prefix(flat)
        if grouped and any(len(v) > 0 for v in grouped.values()):
            return list(grouped.values())

    # chunk fijo
    if chunk < 1:
        chunk = 4
    return _chunked(flat, chunk)


def _rand_bool(p_true: float = 0.5) -> bool:
    return random.random() < p_true


def _rand_price(min_val: int, max_val: int, step: int = 1000) -> Decimal:
    val = random.randrange(min_val, max_val + step, step)
    return Decimal(val)


def _choose(seq: List[str]) -> str:
    return random.choice(seq)


class Command(BaseCommand):
    help = "Borra propiedades existentes y vuelve a cargarlas a partir de imágenes locales (copiando al storage)."

    def add_arguments(self, parser):
        parser.add_argument("--src", required=True, help="Carpeta de origen con imágenes (puede contener subcarpetas).")
        parser.add_argument("--yes", action="store_true", help="Confirma el borrado/creación (si no, solo muestra).")
        parser.add_argument("--purge-media", action="store_true", help="Borra archivos bajo 'propiedades/' del storage.")
        parser.add_argument("--limit", type=int, default=50, help="Cantidad máxima de grupos a procesar.")
        parser.add_argument("--chunk", type=int, default=4, help="Tamaño de grupo cuando se usa modo 'chunk'.")
        parser.add_argument("--mode", choices=["auto", "subdirs", "prefix", "chunk"], default="auto",
                            help="Estrategia de agrupación. Por defecto 'auto'.")

    def handle(self, *args, **opts):
        src = Path(opts["src"]).expanduser()
        if not src.exists() or not src.is_dir():
            self.stderr.write(self.style.ERROR(f"Origen no válido: {src}"))
            return

        _print_env(src)

        groups = _discover_groups(src, mode=opts["mode"], chunk=opts["chunk"])
        total_imgs = sum(len(g) for g in groups)
        print(f"Agrupación: {opts['mode']}")
        print(f"Total grupos detectados: {len(groups)} (se usarán {min(opts['limit'], len(groups))})")
        print(f"Total imágenes consideradas: {total_imgs}")
        print(f"Galería: usando modelo {PropiedadImagen.__module__}.{PropiedadImagen.__name__}")

        if not opts["yes"]:
            print("\nModo vista previa (no se borra ni crea nada). Añadí --yes para ejecutar.")
            if groups:
                sample = groups[0][:min(3, len(groups[0]))]
                print(f"Ejemplo primer grupo ({len(groups[0])} archivos):")
                for p in sample:
                    print("  -", p.name)
            return

        to_use = groups[:opts["limit"]]

        # Purga media opcional
        if opts["purge_media"]:
            print("Eliminando archivos bajo 'propiedades/' en storage…")
            deleted = _purge_media_under_propiedades()
            print(f"Archivos eliminados: {deleted}")

        # Borrado de datos
        with transaction.atomic():
            # Borrar Propiedad elimina en cascada PropiedadImagen
            deleted, _ = Propiedad.objects.all().delete()
            print(f"Propiedades eliminadas: {deleted}")

        # Datos base para seeding
        localidades = ["Posadas", "Oberá", "Garupá", "Eldorado", "Iguazú", "Encarnación"]
        provincias = ["Misiones", "Buenos Aires", "Córdoba", "Santa Fe", "Mendoza"]
        amen_pool = ["pileta", "parrilla", "cochera", "parque", "gimnasio", "sum", "seguridad 24h"]

        tipos = [c[0] for c in Propiedad.TIPO_PROPIEDAD_CHOICES]
        tipos_oper = [c[0] for c in Propiedad.TIPO_OPERACION_CHOICES]
        tipos_masc = [c[0] for c in Propiedad.TIPO_MASCOTA_CHOICES]
        estados_pub = [c[0] for c in Propiedad.ESTADO_PUBLICACION_CHOICES]

        created_props = 0
        created_imgs = 0

        for idx, group in enumerate(to_use, start=1):
            if not group:
                continue

            # Datos sintéticos
            tipo = _choose(tipos)
            tipo_op = _choose(tipos_oper)
            acepta = _rand_bool(0.4)
            tipo_masc = "no_especificado" if not acepta else _choose([x for x in tipos_masc if x != "no_especificado"])
            estado = _choose(estados_pub)

            titulo = f"Propiedad #{idx} — {_choose(['Casa luminosa', 'Depto con balcón', 'Galpón', 'Terreno ideal', 'Local sobre avenida'])}"
            descripcion = "Propiedad de prueba generada automáticamente para verificación de flujo."
            direccion = f"Calle {random.choice(list('ABCDE'))} {random.randint(100, 999)}"
            localidad = _choose(localidades)
            provincia = _choose(provincias)

            precio_usd = None
            precio_pesos = None
            if tipo_op == "venta":
                precio_usd = _rand_price(25000, 250000, 5000)
            else:
                precio_pesos = _rand_price(120000, 1500000, 10000)

            kwargs = dict(
                titulo=titulo[:200],
                descripcion=descripcion,
                tipo=tipo,                       # <= 50
                tipo_operacion=tipo_op,          # <= 50
                precio_usd=precio_usd,
                precio_pesos=precio_pesos,
                direccion=direccion[:255],
                localidad=localidad[:100],
                provincia=provincia[:100],
                pais="Argentina",
                acepta_mascotas=acepta,
                tipo_mascota_permitida=tipo_masc,    # <= 20
                metros_cuadrados_total=Decimal(random.randint(100, 800)),
                metros_cuadrados_cubierta=Decimal(random.randint(30, 400)),
                dormitorios=random.choice([1, 2, 3, 4, None]),
                banios=random.choice([1, 2, 3, None]),
                cocheras=random.choice([0, 1, 2, None]),
                antiguedad=random.choice([0, 2, 5, 10, 20, None]),
                amenidades=", ".join(sorted(set(random.sample(amen_pool, k=random.randint(2, 4))))),
                is_destacada=_rand_bool(0.2),
                estado_publicacion=estado,           # <= 20
            )

            try:
                with transaction.atomic():
                    prop = Propiedad.objects.create(**kwargs)
                    created_props += 1

                    # imagen principal = primer archivo del grupo
                    first = group[0]
                    ext = first.suffix.lower()
                    dest_main = f"propiedades/imagenes_principal/{prop.pk}_principal{ext}"
                    saved_main = _copy_file_to_storage(first, dest_main)
                    # asignar al ImageField (guardar sólo el path relativo)
                    prop.imagen_principal.name = saved_main
                    prop.save(update_fields=["imagen_principal"])

                    # resto a galería
                    for pic in group[1:]:
                        ext2 = pic.suffix.lower()
                        dest_gal = f"propiedades/galeria/{prop.pk}_{random.randint(1000,9999)}{ext2}"
                        saved_gal = _copy_file_to_storage(pic, dest_gal)
                        PropiedadImagen.objects.create(
                            propiedad=prop,
                            imagen=saved_gal,
                            descripcion_corta=""
                        )
                        created_imgs += 1

            except DataError as e:
                # Mensaje claro si vuelve a pasar varchar(6), mostrando longitudes
                print("ERROR DataError al crear Propiedad. Valores que se intentaron grabar:")
                for k, v in kwargs.items():
                    if isinstance(v, str):
                        print(f" - {k}: '{v}' (len={len(v)})")
                    else:
                        print(f" - {k}: {v}")
                print("Excepción:", e)
                continue

        print(f"\nPropiedades creadas: {created_props}")
        print(f"Imágenes de galería creadas: {created_imgs}")
        print("Listo ✅")
