# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from urllib.parse import urlencode

from .models import Propiedad
from .forms import PropiedadForm

from django.core.paginator import Paginator


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


# =========================
# Búsqueda avanzada
# =========================
def busqueda_propiedades(request):
    """
    Búsqueda avanzada combinable con paginación.
    - No muestra resultados por defecto (hasta que haya algún filtro).
    - 12 resultados por página.
    """
    base_qs = (
        Propiedad.objects
        .filter(estado_publicacion='publicada')
        .order_by('-fecha_actualizacion')
    )

    GET = request.GET.copy()
    chips = []

    # --- helpers ---
    def _qs_pop(qd, key):
        c = qd.copy()
        if key in c:
            c.pop(key)
        return c

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

    def _fmt_int(n):
        try:
            return f"{int(float(n)):,}".replace(",", ".")
        except Exception:
            return str(n)

    def _num(v):
        try:
            return float(v)
        except Exception:
            return None

    def _to_int(v):
        try:
            return int(v)
        except Exception:
            return None

    # --- detectar si hay filtros (para no mostrar nada por defecto) ---
    keys_to_check = (
        'q','tipo','tipo_operacion','localidad','provincia',
        'currency','price_min','price_max','usd_min','usd_max','ars_min','ars_max',
        'dormitorios','banios','cocheras'
    )
    has_any = any(GET.get(k) not in (None, '') for k in keys_to_check)

    qs = base_qs
    if has_any:
        # Texto libre
        q = GET.get('q')
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) |
                Q(direccion__icontains=q) |
                Q(localidad__icontains=q) |
                Q(provincia__icontains=q)
            )
            add_chip('q', f'“{q}”')

        # Selects
        tipo = GET.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
            add_chip('tipo', f"Tipo: {dict(Propiedad.TIPO_PROPIEDAD_CHOICES).get(tipo, tipo)}")

        tipo_operacion = GET.get('tipo_operacion')
        if tipo_operacion:
            qs = qs.filter(tipo_operacion=tipo_operacion)
            add_chip('tipo_operacion', f"Operación: {dict(Propiedad.TIPO_OPERACION_CHOICES).get(tipo_operacion, tipo_operacion)}")

        localidad = GET.get('localidad')
        if localidad:
            qs = qs.filter(localidad__icontains=localidad)
            add_chip('localidad', f"Localidad: {localidad}")

        provincia = GET.get('provincia')
        if provincia:
            qs = qs.filter(provincia__icontains=provincia)
            add_chip('provincia', f"Provincia: {provincia}")

        # Moneda + precio
        currency = GET.get('currency') or 'ars'
        price_min = _num(GET.get('price_min'))
        price_max = _num(GET.get('price_max'))
        usd_min = _num(GET.get('usd_min')); usd_max = _num(GET.get('usd_max'))
        ars_min = _num(GET.get('ars_min')); ars_max = _num(GET.get('ars_max'))

        # Filtrar por moneda (respetando el toggle, default ARS)
        if currency == 'usd':
            qs = qs.filter(precio_usd__isnull=False)
        else:
            qs = qs.filter(precio_pesos__isnull=False)

        # Rango preferente
        if price_min is not None or price_max is not None:
            if currency == 'usd':
                if price_min is not None: qs = qs.filter(precio_usd__gte=price_min)
                if price_max is not None: qs = qs.filter(precio_usd__lte=price_max)
                rango = f"USD {_fmt_int(price_min) if price_min is not None else '0'}–{_fmt_int(price_max) if price_max is not None else '∞'}"
                add_price_chip(rango)
            else:
                if price_min is not None: qs = qs.filter(precio_pesos__gte=price_min)
                if price_max is not None: qs = qs.filter(precio_pesos__lte=price_max)
                rango = f"$ {_fmt_int(price_min) if price_min is not None else '0'}–{_fmt_int(price_max) if price_max is not None else '∞'}"
                add_price_chip(rango)
        else:
            # legacy
            if usd_min is not None:
                qs = qs.filter(precio_usd__gte=usd_min); add_chip('usd_min', f"USD mín: {_fmt_int(usd_min)}")
            if usd_max is not None:
                qs = qs.filter(precio_usd__lte=usd_max); add_chip('usd_max', f"USD máx: {_fmt_int(usd_max)}")
            if ars_min is not None:
                qs = qs.filter(precio_pesos__gte=ars_min); add_chip('ars_min', f"$ mín: {_fmt_int(ars_min)}")
            if ars_max is not None:
                qs = qs.filter(precio_pesos__lte=ars_max); add_chip('ars_max', f"$ máx: {_fmt_int(ars_max)}")

        # Numéricos (>=)
        dormitorios = _to_int(GET.get('dormitorios'))
        if dormitorios is not None:
            qs = qs.filter(dormitorios__gte=dormitorios)
            add_chip('dormitorios', f"Dormitorios: {dormitorios}")

        banios = _to_int(GET.get('banios'))
        if banios is not None:
            qs = qs.filter(banios__gte=banios)
            add_chip('banios', f"Baños: {banios}")

        cocheras = _to_int(GET.get('cocheras'))
        if cocheras is not None:
            qs = qs.filter(cocheras__gte=cocheras)
            add_chip('cocheras', f"Cocheras: {cocheras}")

        # --- Paginación 12 por página ---
        paginator = Paginator(qs, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        is_paginated = page_obj.has_other_pages()

        # Querystring base (para mantener filtros en la paginación)
        base_params = GET.copy()
        if 'page' in base_params: base_params.pop('page')
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
    else:
        # Sin filtros => no mostrar resultados
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
