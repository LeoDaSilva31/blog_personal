# propiedades/management/commands/props_report.py
from __future__ import annotations

import csv
from typing import List
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone
from propiedades.models import Propiedad


def _print_env():
    from django.db import connection
    engine = connection.settings_dict.get("ENGINE")
    name = connection.settings_dict.get("NAME")
    print("=== ENTORNO ===")
    print(f"Fecha: {timezone.now().isoformat()} (TZ={settings.TIME_ZONE})")
    print(f"Base de datos: {engine} | NAME={name}")
    print(f"USE_S3_MEDIA={getattr(settings, 'USE_S3_MEDIA', False)} | STORAGE={default_storage.__class__.__name__}\n")


def _parse_ids(expr: str) -> List[int]:
    # "1,2,10-15" -> [1,2,10,11,12,13,14,15]
    out: List[int] = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            out.extend(range(min(a, b), max(a, b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


class Command(BaseCommand):
    help = "Muestra un reporte de Propiedades y sus imágenes (opcionalmente exporta CSV)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Máximo de propiedades a listar (si no usás --ids).")
        parser.add_argument("--ids", type=str, help='IDs puntuales, p.ej.: "1,2,10-20".')
        parser.add_argument("--related", action="store_true", help="Incluir imágenes relacionadas (galería).")
        parser.add_argument("--csv", type=str, help="Ruta a CSV para exportar filas (opcional).")

    def handle(self, *args, **opts):
        _print_env()

        qs = Propiedad.objects.all().order_by("id")
        if opts.get("ids"):
            ids = _parse_ids(opts["ids"])
            qs = qs.filter(id__in=ids)
        else:
            qs = qs[: opts["limit"]]

        if opts["related"]:
            qs = qs.prefetch_related("imagenes")

        props = list(qs)
        total_files = 0

        writer = None
        csvfile = None
        if opts.get("csv"):
            csvfile = open(opts["csv"], "w", newline="", encoding="utf-8")
            writer = csv.writer(csvfile)
            writer.writerow([
                "prop_id", "titulo", "es_principal",
                "file_name", "exists", "url_o_error"
            ])

        for p in props:
            print(f"Propiedad #{p.id} — {p.titulo}")
            # Imagen principal
            if p.imagen_principal:
                name = p.imagen_principal.name
                try:
                    exists = default_storage.exists(name)
                except Exception:
                    exists = False
                try:
                    url = default_storage.url(name)
                except Exception as e:
                    url = f"ERROR_URL: {e}"
                print(f"  - imagen_principal: name='{name}' | exists={exists} | url={url}")
                if writer:
                    writer.writerow([p.id, p.titulo, True, name, exists, url])
                total_files += 1
            else:
                print("  - imagen_principal: (sin asignar)")
                if writer:
                    writer.writerow([p.id, p.titulo, True, "", False, ""])

            # Relacionadas
            if opts["related"]:
                for rel in getattr(p, "imagenes").all():
                    name = rel.imagen.name
                    try:
                        exists = default_storage.exists(name)
                    except Exception:
                        exists = False
                    try:
                        url = default_storage.url(name)
                    except Exception as e:
                        url = f"ERROR_URL: {e}"
                    print(f"  - [rel:PropiedadImagen#{rel.id}] imagen: name='{name}' | exists={exists} | url={url}")
                    if writer:
                        writer.writerow([p.id, p.titulo, False, name, exists, url])
                    total_files += 1

            print()

        if writer:
            csvfile.close()
            print(f"CSV escrito en {opts['csv']} ({total_files} filas)")

        print(f"Propiedades listadas: {len(props)}")
        print(f"Registros de archivos inspeccionados: {total_files}")
