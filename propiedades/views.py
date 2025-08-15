# views.py
from django.shortcuts import render, get_object_or_404, redirect
from urllib.parse import urlencode

from .models import Propiedad
from .forms import PropiedadForm

from django.core.paginator import Paginator
from django.db.models import Q, F, Func
from django.db.models.functions import Lower, Greatest
from django.contrib.postgres.search import TrigramSimilarity

# Importá sinónimos y la normalización canónica desde el config
from .search_config import SYNONYMS, norm as _norm


# =========================
# Vistas básicas existentes
# =========================
def home(request):
    """
    Home: muestra hasta 6 propiedades destacadas y publicadas.
    """
    propiedades_destacadas = (
        Propiedad.objects
        .filter(is_destacada=True, estado_publicacion='publicada')
        .order_by('-fecha_actualizacion')[:6]
    )
    return render(request, 'propiedades/home.html', {
        'propiedades_destacadas': propiedades_destacadas
    })


def propiedad_list_view(request):
    qs = (
        Propiedad.objects
        .filter(estado_publicacion='publicada')
        .order_by('-fecha_actualizacion')
    )
    paginator = Paginator(qs, 18)  # 18 por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'propiedades/lista.html', {
        'propiedades': page_obj,          # iterable en el for
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    })


def detalle_propiedad(request, pk):
    """
    Detalle de una propiedad por PK.
    """
    propiedad = get_object_or_404(Propiedad, pk=pk)
    return render(request, 'propiedades/detalle.html', {'propiedad': propiedad})


# =========================
# Helpers para la búsqueda
# =========================
def _qs_pop(qd, key):
    """
    Devuelve una copia de QueryDict sin la clave dada.
    Se usa para construir la URL de 'remover filtro' en los chips.
    """
    c = qd.copy()
    if key in c:
        c.pop(key)
    return c


def _fmt_int(n):
    """
    Formatea enteros con separador de miles estilo '10.000'.
    Si no puede castear, devuelve str(n).
    """
    try:
        return f"{int(float(n)):,}".replace(",", ".")
    except Exception:
        return str(n)


# Función DB para usar unaccent() en consultas
class Unaccent(Func):
    function = 'unaccent'
    template = '%(function)s(%(expressions)s)'


def _normalize_q(s: str) -> str:
    """
    Normaliza usando la misma función del config:
    - minúsculas
    - sin tildes
    - espacios colapsados
    """
    return _norm(s or "")


def _expand_tokens(q: str):
    """
    Expande tokens con sinónimos pre-normalizados.
    """
    # normaliza cada token con la MISMA función del config
    base = [_norm(t) for t in q.split()]
    out = set(base)
    for t in base:
        syn = SYNONYMS.get(t)
        if syn:
            out.add(syn)
    return list(out)


def _num(x):
    """
    Convierte strings de precios/filtros a número:
    soporta '$', 'ars', 'usd', puntos, comas y sufijos 'k'/'m'.
    """
    if not x:
        return None
    x = str(x).strip().lower().replace('.', '').replace(',', '')
    x = x.replace('$', '').replace('ars', '').replace('usd', '')
    if x.endswith('k'):
        x = x[:-1]
        try:
            return int(float(x) * 1000)
        except:
            return None
    if x.endswith('m'):
        x = x[:-1]
        try:
            return int(float(x) * 1_000_000)
        except:
            return None
    try:
        return int(float(x))
    except:
        return None


def _to_int(v):
    try:
        return int(v)
    except Exception:
        return None


# =========================
# Búsqueda avanzada
# =========================
def busqueda_propiedades(request):
    """
    Búsqueda avanzada combinable con paginación.
    - No muestra resultados por defecto (hasta que haya algún filtro).
    - 12 resultados por página.
    - Sin tildes (unaccent), sinónimos y fallback fuzzy (trigram).
    """
    base_qs = (
        Propiedad.objects
        .filter(estado_publicacion='publicada')
        .order_by('-fecha_actualizacion')
    )

    GET = request.GET.copy()
    chips = []

    def add_chip(key, label):
        params = _qs_pop(GET, key)
        remove_url = f"{request.path}?{urlencode(params, doseq=True)}" if params else request.path
        chips.append({'key': key, 'label': label, 'remove_url': remove_url})

    def add_price_chip(label):
        params = GET.copy()
        for k in ("price_min", "price_max", "usd_min", "usd_max", "ars_min", "ars_max"):
            if k in params:
                params.pop(k)
        remove_url = f"{request.path}?{urlencode(params, doseq=True)}" if params else request.path
        chips.append({'key': 'price_range', 'label': label, 'remove_url': remove_url})

    qs = base_qs
    applied_any = False

    # -------- Texto libre (q) --------
    q = (GET.get('q') or '').strip()
    if q:
        tokens = _expand_tokens(q)
        qs = qs.annotate(
            ntitulo=Lower(Unaccent(F('titulo'))),
            ndesc=Lower(Unaccent(F('descripcion'))),
            nloc=Lower(Unaccent(F('localidad'))),
            nprov=Lower(Unaccent(F('provincia'))),
            namen=Lower(Unaccent(F('amenidades'))),
            ncodigo=Lower(Unaccent(F('codigo_unico'))),
        )
        # AND de ORs: todos los tokens deben aparecer en algún campo
        for t in tokens:
            qs = qs.filter(
                Q(ntitulo__icontains=t) |
                Q(ndesc__icontains=t)   |
                Q(nloc__icontains=t)    |
                Q(nprov__icontains=t)   |
                Q(namen__icontains=t)   |
                Q(ncodigo__icontains=t)
            )
        add_chip('q', f'“{q}”')
        applied_any = True

    # -------- Selects --------
    tipo = GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)
        add_chip('tipo', f"Tipo: {dict(Propiedad.TIPO_PROPIEDAD_CHOICES).get(tipo, tipo)}")
        applied_any = True

    tipo_operacion = GET.get('tipo_operacion')
    if tipo_operacion:
        qs = qs.filter(tipo_operacion=tipo_operacion)
        add_chip('tipo_operacion', f"Operación: {dict(Propiedad.TIPO_OPERACION_CHOICES).get(tipo_operacion, tipo_operacion)}")
        applied_any = True

    localidad = _normalize_q(GET.get('localidad') or '')
    if localidad:
        qs = qs.annotate(nloc=Lower(Unaccent(F('localidad')))).filter(nloc__icontains=localidad)
        add_chip('localidad', f"Localidad: {GET.get('localidad')}")
        applied_any = True

    provincia = _normalize_q(GET.get('provincia') or '')
    if provincia:
        qs = qs.annotate(nprov=Lower(Unaccent(F('provincia')))).filter(nprov__icontains=provincia)
        add_chip('provincia', f"Provincia: {GET.get('provincia')}")
        applied_any = True

    # -------- Numéricos (>=) --------
    dormitorios = _to_int(GET.get('dormitorios'))
    if dormitorios is not None:
        qs = qs.filter(dormitorios__gte=dormitorios)
        add_chip('dormitorios', f"Dormitorios: {dormitorios}")
        applied_any = True

    banios = _to_int(GET.get('banios'))
    if banios is not None:
        qs = qs.filter(banios__gte=banios)
        add_chip('banios', f"Baños: {banios}")
        applied_any = True

    cocheras = _to_int(GET.get('cocheras'))
    if cocheras is not None:
        qs = qs.filter(cocheras__gte=cocheras)
        add_chip('cocheras', f"Cocheras: {cocheras}")
        applied_any = True

    # -------- Precio (solo si lo pidieron) --------
    currency = GET.get('currency') or 'ars'
    price_min = _num(GET.get('price_min'))
    price_max = _num(GET.get('price_max'))
    usd_min = _num(GET.get('usd_min')); usd_max = _num(GET.get('usd_max'))
    ars_min = _num(GET.get('ars_min')); ars_max = _num(GET.get('ars_max'))

    has_price_filters = any(v is not None for v in [price_min, price_max, usd_min, usd_max, ars_min, ars_max])

    if has_price_filters:
        if price_min is not None or price_max is not None:
            if currency == 'usd':
                if price_min is not None:
                    qs = qs.filter(precio_usd__gte=price_min)
                if price_max is not None:
                    qs = qs.filter(precio_usd__lte=price_max)
                add_price_chip(f"USD {price_min or 0}–{price_max or '∞'}")
            else:
                if price_min is not None:
                    qs = qs.filter(precio_pesos__gte=price_min)
                if price_max is not None:
                    qs = qs.filter(precio_pesos__lte=price_max)
                add_price_chip(f"$ {price_min or 0}–{price_max or '∞'}")
        else:
            if usd_min is not None:
                qs = qs.filter(precio_usd__gte=usd_min); add_chip('usd_min', f"USD mín: {_fmt_int(usd_min)}")
            if usd_max is not None:
                qs = qs.filter(precio_usd__lte=usd_max); add_chip('usd_max', f"USD máx: {_fmt_int(usd_max)}")
            if ars_min is not None:
                qs = qs.filter(precio_pesos__gte=ars_min); add_chip('ars_min', f"$ mín: {_fmt_int(ars_min)}")
            if ars_max is not None:
                qs = qs.filter(precio_pesos__lte=ars_max); add_chip('ars_max', f"$ máx: {_fmt_int(ars_max)}")
        applied_any = True
    # Si NO hay filtros de precio, no restringimos por moneda ni por campos no nulos.

    # -------- Fuzzy fallback si hubo texto y no hay resultados --------
    if q and not qs.exists():
        qn = _norm(q)  # usa la normalización canónica
        qs = base_qs.annotate(
            sim_t=TrigramSimilarity(Unaccent(F('titulo')), qn),
            sim_l=TrigramSimilarity(Unaccent(F('localidad')), qn),
            sim_p=TrigramSimilarity(Unaccent(F('provincia')), qn),
        ).annotate(
            sim=Greatest('sim_t', 'sim_l', 'sim_p')
        ).filter(
            sim__gte=0.20  # si querés más permisivo, bajá a 0.10
        ).order_by('-sim', '-fecha_actualizacion')
        add_chip('fuzzy', "Coincidencias aproximadas")
        applied_any = True

    # -------- Sin filtros => no mostrar resultados --------
    if not applied_any:
        contexto = {
            'show_results': False,
            'propiedades': None,
            'is_paginated': False,
            'page_obj': None,
            'base_query': '',
            'chips': [],
            'val': GET,
            'propiedad': Propiedad,
        }
        return render(request, 'propiedades/busqueda.html', contexto)

    # -------- Paginación --------
    paginator = Paginator(qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    is_paginated = page_obj.has_other_pages()

    base_params = GET.copy()
    if 'page' in base_params:
        base_params.pop('page')
    base_query = urlencode(base_params, doseq=True)

    contexto = {
        'show_results': True,
        'propiedades': page_obj,     # iterable en el for
        'is_paginated': is_paginated,
        'page_obj': page_obj,
        'base_query': base_query,
        'chips': chips,
        'val': GET,
        'propiedad': Propiedad,
    }
    return render(request, 'propiedades/busqueda.html', contexto)


# --- CONTACTO (EmailJS) ---
from django.shortcuts import render, get_object_or_404
from .models import Propiedad

def _precio_str(p: Propiedad) -> str:
    if p.precio_usd is not None:
        return f"USD {int(p.precio_usd):,}".replace(",", ".")
    if p.precio_pesos is not None:
        return f"$ {int(p.precio_pesos):,}".replace(",", ".")
    return "A consultar"

def contacto_view(request):
    """
    Si llega ?propiedad_id, precarga asunto + mensaje con datos reales desde la DB.
    """
    prop = None
    prefill = {}
    prop_id = request.GET.get("propiedad_id")
    if prop_id:
        # Sólo propiedades publicadas (ajustá si querés permitir otras)
        prop = get_object_or_404(Propiedad, pk=prop_id, estado_publicacion="publicada")
        precio = _precio_str(prop)
        desc = (prop.descripcion or "").strip()
        # recorte amable (no JSON, texto para humanos)
        desc_corta = (desc[:400] + "…") if len(desc) > 420 else desc

        prefill = {
            "asunto": f"Consulta por {prop.titulo}",
            "mensaje": (
                f"Hola, me interesa más información sobre la propiedad "
                f"{prop.codigo_unico} — {prop.titulo}.\n\n"
                f"• Precio: {precio}\n"
                f"• Ubicación: {prop.direccion}, {prop.localidad}, {prop.provincia}\n\n"
                f"Descripción breve: {desc_corta}\n\n"
                f"Quedo atento/a a más detalles. ¡Gracias!"
            ),
            "propiedad_id": prop.pk,
            "propiedad_titulo": prop.titulo,
            "propiedad_codigo": prop.codigo_unico,
            "propiedad_precio": precio,
        }

    return render(request, "propiedades/contacto.html", {"prefill": prefill})
