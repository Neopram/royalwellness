#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Royal Wellness - actualizar la tienda con UN comando.
#
#   bash actualizar.sh            -> reconstruye la web en site/
#   bash actualizar.sh --publicar -> ademas hace commit y push (web en vivo)
#
# Rodea el bloqueo de Windows "Controlled Folder Access": python.exe no puede
# escribir en Escritorio, asi que construimos en TEMP y copiamos con cp.
# Ver docs/ENTORNO.md si quieres quitar el bloqueo de raiz.
# ---------------------------------------------------------------------------
set -e
cd "$(dirname "$0")"

TMP="${TEMP:-/tmp}/royalwellness_build"
mkdir -p "$TMP"

echo ""
echo "  [1/3] Generando web desde catalogo/productos.json ..."
if command -v cygpath >/dev/null 2>&1; then
  OUT_WIN="$(cygpath -w "$TMP")"
else
  OUT_WIN="$TMP"
fi
python scripts/build.py --out "$OUT_WIN"

echo "  [2/3] Copiando al proyecto ..."
mkdir -p docs ops
cp "$TMP/docs/index.html" docs/index.html
if [ -f "$TMP/docs/CNAME" ]; then cp "$TMP/docs/CNAME" docs/CNAME; else rm -f docs/CNAME; fi
cp "$TMP/docs/.nojekyll" docs/.nojekyll
cp "$TMP/docs/robots.txt" docs/robots.txt
cp "$TMP/docs/melos.html" docs/melos.html
cp "$TMP/docs/nomika.html" docs/nomika.html
cp "$TMP/docs/faq.html" docs/faq.html
cp "$TMP/docs/epikoinonia.html" docs/epikoinonia.html
cp "$TMP/docs/eukairia.html" docs/eukairia.html
cp "$TMP/ops/inventario.csv" ops/inventario.csv
echo "         docs/index.html  ($(wc -c < docs/index.html) bytes)"
echo "         ops/inventario.csv"

if [ "$1" = "--publicar" ]; then
  echo "  [3/3] Publicando en GitHub Pages ..."
  if [ ! -d .git ]; then
    echo "         ERROR: esta carpeta aun no es un repo git."
    echo "         Ejecuta primero:  bash scripts/init_repo.sh"
    exit 1
  fi
  git add -A
  MSG="Actualizar tienda: $(date '+%d/%m/%Y %H:%M')

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
  git commit -q -m "$MSG" || echo "         (sin cambios que publicar)"
  git push
  echo "         Publicado. La web en vivo se actualiza en ~60 segundos."
else
  echo "  [3/3] Sin publicar (usa --publicar para subirlo a la web en vivo)."
fi

echo ""
echo "  Abre docs/index.html en el navegador para verlo."
echo ""
