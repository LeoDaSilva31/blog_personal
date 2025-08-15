from django.db import migrations

SQL_ENABLE = """
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
"""

SQL_FN = """
CREATE OR REPLACE FUNCTION public.f_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT public.unaccent('public.unaccent', $1)
$$;
"""

SQL_INDEXES = """
-- Índice full-text (acento-insensible) sobre varios campos
CREATE INDEX IF NOT EXISTS propiedades_propiedad_search_gin
ON propiedades_propiedad
USING GIN (
  to_tsvector(
    'spanish',
    public.f_unaccent(
      coalesce(titulo,'') || ' ' ||
      coalesce(descripcion,'') || ' ' ||
      coalesce(localidad,'') || ' ' ||
      coalesce(provincia,'') || ' ' ||
      coalesce(amenidades,'')
    )
  )
);

-- Trigram para fuzzy en título, localidad y provincia (acento-insensible)
CREATE INDEX IF NOT EXISTS propiedades_propiedad_titulo_trgm
  ON propiedades_propiedad USING GIN (public.f_unaccent(lower(titulo)) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS propiedades_propiedad_localidad_trgm
  ON propiedades_propiedad USING GIN (public.f_unaccent(lower(localidad)) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS propiedades_propiedad_provincia_trgm
  ON propiedades_propiedad USING GIN (public.f_unaccent(lower(provincia)) gin_trgm_ops);
"""

SQL_DROP_INDEXES = """
DROP INDEX IF EXISTS propiedades_propiedad_provincia_trgm;
DROP INDEX IF EXISTS propiedades_propiedad_localidad_trgm;
DROP INDEX IF EXISTS propiedades_propiedad_titulo_trgm;
DROP INDEX IF EXISTS propiedades_propiedad_search_gin;
"""

class Migration(migrations.Migration):

    dependencies = [
        ('propiedades', '0005_propiedad_codigo_unico'),
    ]

    operations = [
        migrations.RunSQL(SQL_ENABLE, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(SQL_FN, reverse_sql="DROP FUNCTION IF EXISTS public.f_unaccent(text);"),
        migrations.RunSQL(SQL_INDEXES, reverse_sql=SQL_DROP_INDEXES),
    ]
