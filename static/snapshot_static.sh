#!/usr/bin/env bash
set -euo pipefail
OUT="static_snapshot_$(date +%Y%m%d_%H%M%S).txt"
have_tree=0
if command -v tree >/dev/null 2>&1; then have_tree=1; fi
{
  echo "=== STATIC SNAPSHOT ==="
  echo "pwd: $(pwd)"
  echo "date: $(date -Is)"
  echo
  echo "--- Summary (counts) ---"
  total_dirs=$(find . -type d ! -path "*/.git/*" | wc -l)
  total_files=$(find . -type f ! -path "*/.git/*" | wc -l)
  echo "directories: $total_dirs"
  echo "files:       $total_files"
  echo
  echo "--- By extension ---"
  find . -type f ! -path "*/.git/*" \
    | sed -E "s/.*\.([^.\/]+)$/\1/I" \
    | tr "[:upper:]" "[:lower:]" \
    | sort | uniq -c | sort -nr
  echo
  echo "--- Tree ---"
  if (( have_tree )); then
     tree -a -I ".git|__pycache__|*.map" -F
  else
    echo "(tree no está instalado; usando find)"
    find . -print | sed -e "s|[^/]*/|  |g" -e "s|/|/|g"
  fi
  echo
  echo "--- Files (size, mtime, path) ---"
  if find . -maxdepth 0 -printf "" 2>/dev/null; then
    find . -type f ! -path "*/.git/*" \
      -printf "%10s  %TY-%Tm-%Td %TH:%TM  %p\n" \
      | sort -k3,3 -k4,4
  else
    while IFS= read -r -d "" f; do
      sz=$(stat -c %s "$f" 2>/dev/null || wc -c < "$f")
      mt=$(date -r "$f" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "?")
      printf "%10s  %s  %s\n" "$sz" "$mt" "$f"
    done < <(find . -type f -print0)
  fi
  echo
  echo "--- Expected assets check ---"
  for p in "img/tu_logo.png" "img/favicon.png"; do
    if [[ -f "$p" ]]; then
      echo "[OK]   $p"
    else
      echo "[MISS] $p (no existe en esta carpeta)"
    fi
  done
} > "$OUT"
echo "Generado: $OUT"

