# propiedades/context_processors.py
from django.conf import settings

def emailjs_keys(request):
    return {
        "EMAILJS_PUBLIC_KEY":  settings.EMAILJS_PUBLIC_KEY,
        "EMAILJS_SERVICE_ID":  settings.EMAILJS_SERVICE_ID,
        "EMAILJS_TEMPLATE_ID": settings.EMAILJS_TEMPLATE_ID,
    }
