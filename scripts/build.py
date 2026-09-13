#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Royal Wellness - generador del sitio.

Lee  catalogo/productos.json  ->  escribe en docs/:
    index.html   catalogo + carrito + pedido por WhatsApp
    melos.html   "Gine Melos": alta como Miembro con tu Sponsor ID
    nomika.html  paginas legales (BORRADOR, hay que revisarlas)
    robots.txt   bloqueo de indexacion mientras indexable=false
    .nojekyll    para GitHub Pages
    CNAME        solo si cname_activo=true

Uso:
    bash actualizar.sh              (no llames a este script directamente:
    bash actualizar.sh --publicar    Windows bloquea que python escriba aqui,
                                     ver guia/ENTORNO.md)
Nunca edites docs/*.html a mano: se sobrescriben.
"""

import json
import csv
import sys
import html
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "catalogo" / "productos.json"
SITE = RAIZ / "docs"   # "docs" porque GitHub Pages publica esa carpeta sin configuracion extra
OPS = RAIZ / "ops"

PENDIENTE = ("PENDIENTE", "", None)


def cargar():
    with open(CATALOGO, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Validacion
# ---------------------------------------------------------------------------

def validar(data):
    """Devuelve (errores, avisos). Los errores bloquean el build."""
    errores, avisos = [], []
    t = data["tienda"]
    pago = data.get("pago", {})
    mi = data.get("miembro", {})

    if "X" in t["telefono_whatsapp"]:
        avisos.append("telefono_whatsapp es un placeholder -> el boton de pedido NO funciona")
    if t.get("gemi") in PENDIENTE:
        avisos.append("GEMI sin rellenar -> obligatorio por ley griega en el pie de un e-shop")
    if t.get("afm") in PENDIENTE:
        avisos.append("AFM sin rellenar -> obligatorio en las paginas legales")
    if t.get("cname_activo"):
        avisos.append("cname_activo=true -> la web solo respondera en " + t["dominio"] +
                      ". Comprueba que el DNS ya resuelve o quedara inaccesible")
    if t.get("indexable"):
        avisos.append("indexable=true -> Google PUEDE indexar la tienda. "
                      "Asegurate de que precios, telefono y paginas legales estan listos")

    if mi.get("activo"):
        if mi.get("sponsor_id") in PENDIENTE:
            avisos.append("miembro.sponsor_id sin rellenar -> la pagina Gine Melos "
                          "no puede registrar a nadie bajo tu codigo")
        if mi.get("url_registro") in PENDIENTE:
            avisos.append("miembro.url_registro sin rellenar -> pega tu enlace de alta "
                          "de MyHerbalife")

    if pago.get("iris") and pago.get("iris_id") in PENDIENTE:
        avisos.append("pago.iris=true pero iris_id esta vacio -> el cliente no sabra "
                      "a quien pagar. IRIS exige alta con AFM")
    if pago.get("transferencia") and pago.get("iban") in PENDIENTE:
        avisos.append("pago.transferencia=true pero el IBAN esta vacio -> quita la opcion "
                      "o pon el IBAN")

    skus = set()
    activos = 0
    for p in data["productos"]:
        if p["sku"] in skus:
            errores.append("SKU duplicado: " + p["sku"])
        skus.add(p["sku"])
        if not p.get("activo"):
            continue
        activos += 1
        if p["precio"] <= 0:
            errores.append(p["sku"] + ": precio 0.00 - rellena el precio real antes de publicar")
        elif not p.get("precio_verificado"):
            avisos.append(p["sku"] + ": precio sin verificar contra tu tarifa de Miembro")
        if p["stock"] <= 0 and not t.get("modo_catalogo"):
            avisos.append(p["sku"] + ": stock 0 -> se mostrara como agotado")

    if activos == 0:
        errores.append("No hay ningun producto activo")
    return errores, avisos


def escribir_inventario(data):
    OPS.mkdir(parents=True, exist_ok=True)
    ruta = OPS / "inventario.csv"
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["SKU", "Producto", "Categoria", "Precio", "Stock", "Valor stock", "Activo"])
        for p in data["productos"]:
            w.writerow([
                p["sku"], p["nombre_es"], p["categoria"],
                f'{p["precio"]:.2f}', p["stock"],
                f'{p["precio"] * p["stock"]:.2f}',
                "SI" if p.get("activo") else "NO",
            ])
    return ruta


# ---------------------------------------------------------------------------
# Imagenes
# ---------------------------------------------------------------------------

def buscar_imagen(p):
    """Ruta relativa de la foto si existe en docs/assets/, si no None.

    Acepta cualquier extension: da igual que el JSON diga .jpg y la foto que
    descargues de MyHerbalife sea .webp o .png. Solo importa el nombre base.
    """
    ref = p.get("imagen", "")
    if not ref:
        return None
    carpeta = RAIZ / "docs" / "assets"
    if not carpeta.is_dir():
        return None
    stem = Path(ref).stem
    for f in sorted(carpeta.glob(stem + ".*")):
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
            return "assets/" + f.name
    return None


# ---------------------------------------------------------------------------
# Esqueleto comun
# ---------------------------------------------------------------------------

CSS = """
/* Paleta tomada de royalwellness.gr: crema, verde salvia, tipografia Comfortaa.
   SOLO modo claro, a proposito: no hay bloque prefers-color-scheme dark. */
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --g:#5a7356;        /* salvia profundo: textos, precios, botones (4.9:1 sobre blanco) */
  --g2:#9faf9c;       /* salvia suave: fondos y detalles */
  --tan:#c7afa0;      /* arena calida */
  --ink:#232323;
  --mut:#6b6b6b;
  --bg:#f8f6f2;       /* crema */
  --card:#ffffff;
  --line:#e6e1d8;
  --tit:Comfortaa,"Trebuchet MS",system-ui,sans-serif;
}
html{background:var(--bg)}
body{font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,sans-serif;color:var(--ink);background:var(--bg);-webkit-text-size-adjust:100%}
h1,h2,h3,h4,.big,.price,.ph-t{font-family:var(--tit)}
header{background:linear-gradient(160deg,#fbfaf7,var(--bg));border-bottom:1px solid var(--line);color:var(--ink);padding:26px 18px 24px;text-align:center}
header h1{font-size:26px;letter-spacing:1.5px;font-weight:700;text-transform:uppercase}
header h1 a{color:var(--ink);text-decoration:none}
header p{color:var(--mut);font-size:13.5px;margin-top:7px;letter-spacing:.3px}
header .rule{width:52px;height:2px;background:var(--g2);margin:14px auto 0;border-radius:2px}
nav{background:var(--card);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:50}
nav ul{display:flex;flex-wrap:wrap;justify-content:center;gap:0 2px;list-style:none;max-width:1040px;margin:0 auto;padding:0 6px}
nav a{display:block;padding:12px 13px;color:var(--mut);text-decoration:none;font-size:13.5px;font-weight:600;white-space:nowrap;border-bottom:2px solid transparent}
nav a.on{color:var(--g);border-bottom-color:var(--g)}
@media(max-width:600px){
  header h1{font-size:21px;letter-spacing:1px}
  nav a{padding:10px 9px;font-size:12.5px}
}
.wrap{max-width:1040px;margin:0 auto;padding:18px}
.chips{display:flex;gap:8px;overflow-x:auto;padding:16px 0 6px;-webkit-overflow-scrolling:touch}
.chip{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:8px 15px;border-radius:999px;font-size:14px;cursor:pointer}
.chip.on{background:var(--g);border-color:var(--g);color:#fff}
.chip{transition:.15s}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;padding:10px 0 90px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 1px 2px rgba(35,35,35,.04);padding:14px;display:flex;flex-direction:column}
.card.out{opacity:.55}
.ph{position:relative;height:120px;border-radius:10px;background:linear-gradient(150deg,#f2efe8,#dfe6da);display:grid;place-items:center;margin-bottom:10px}
.ph-t{font-size:32px;font-weight:700;color:var(--g);opacity:.42;letter-spacing:1px}
.ph.has-img{background:#fff;overflow:hidden}
.ph.has-img img{width:100%;height:100%;object-fit:contain;display:block}
.badge{position:absolute;top:8px;left:8px;background:#a4483c;color:#fff;font-size:11px;padding:3px 8px;border-radius:6px}
.card h3{font-size:15px;line-height:1.35;margin-bottom:5px}
.desc{font-size:13px;color:var(--mut);flex:1;margin-bottom:10px}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px}
.price{font-weight:700;color:var(--g);font-size:17px}
.btn{background:var(--g);color:#fff;border:0;border-radius:8px;padding:9px 14px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block}
.btn:disabled{background:#98a79e;cursor:not-allowed}
.btn.big{padding:14px 26px;font-size:16px}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:11px 16px;display:none;align-items:center;justify-content:space-between;gap:12px;box-shadow:0 -6px 20px rgba(0,0,0,.10);z-index:60}
.bar.on{display:flex}
.bar .t{font-size:14px}
.bar .t b{display:block;font-size:17px;color:var(--g)}
dialog{border:0;border-radius:16px;padding:0;max-width:460px;width:92%;background:var(--card);color:var(--ink)}
dialog::backdrop{background:rgba(0,0,0,.5)}
.dh{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
.dh h2{font-size:17px}
.x{border:0;background:none;font-size:24px;line-height:1;cursor:pointer;color:var(--mut)}
.items{padding:8px 18px;max-height:34vh;overflow:auto}
.it{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px}
.it .nm{flex:1}
.qty{display:flex;align-items:center;gap:7px}
.qty button{width:27px;height:27px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:7px;cursor:pointer;font-size:15px}
.pagos{padding:12px 18px;border-top:1px solid var(--line)}
.pagos h4{font-size:13px;color:var(--mut);margin-bottom:8px;font-weight:600}
.pagos label{display:flex;align-items:center;gap:9px;padding:7px 0;font-size:14px;cursor:pointer}
.pagos small{color:var(--mut)}
.tot{padding:14px 18px;border-top:1px solid var(--line);font-size:14px}
.tot div{display:flex;justify-content:space-between;margin-bottom:6px}
.tot .g{font-size:19px;font-weight:800;color:var(--g)}
.send{display:block;width:calc(100% - 36px);margin:0 18px 18px;background:#25a55a;color:#fff;text-align:center;padding:13px;border-radius:11px;font-weight:700;text-decoration:none}
.hero{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:26px 22px;text-align:center;margin-bottom:18px}
.hero .big{font-size:40px;font-weight:800;color:var(--g);line-height:1.1}
.hero p{color:var(--mut);margin-top:8px}
.pasos{counter-reset:p;list-style:none;margin:18px 0}
.pasos li{counter-increment:p;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 16px 16px 56px;margin-bottom:10px;position:relative}
.pasos li::before{content:counter(p);position:absolute;left:16px;top:16px;width:26px;height:26px;border-radius:50%;background:var(--g);color:#fff;display:grid;place-items:center;font-weight:700;font-size:14px}
.pasos b{display:block;margin-bottom:3px}
.pasos small{color:var(--mut);display:block;margin-top:4px}
.codigo{display:inline-block;background:var(--bg);border:1px dashed var(--g);border-radius:8px;padding:6px 12px;font-family:ui-monospace,Consolas,monospace;font-weight:700;color:var(--g);font-size:16px;margin:4px 6px 4px 0;user-select:all}
.avisobox{background:#fbf5ec;border:1px solid var(--tan);color:#7a5a42;border-radius:10px;padding:12px 14px;font-size:14px;margin:14px 0}
.legal h2{font-size:19px;margin:26px 0 8px;color:var(--g)}
.legal h3{font-size:15px;margin:16px 0 5px}
.legal p,.legal li{font-size:14px;color:var(--ink);margin-bottom:8px}
.legal ul{padding-left:20px}
.legal .falta{background:#f7e4e0;color:#8c3a2c;border-radius:5px;padding:1px 7px;font-weight:700;font-size:13px}
.pieancho{background:var(--card);border-top:1px solid var(--line);padding:30px 18px 4px}
.pw{max-width:1040px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:26px}
.pw h4{font-size:13px;letter-spacing:.5px;text-transform:uppercase;color:var(--g);margin-bottom:10px}
.pw p{font-size:13px;color:var(--mut);margin-bottom:6px}
.pw a{color:var(--mut);text-decoration:none}
.pw a:hover{color:var(--g);text-decoration:underline}
.pb{display:inline-block;border:1px solid var(--line);border-radius:6px;padding:3px 9px;font-size:11px;margin:0 5px 5px 0;color:var(--ink)}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0;margin-bottom:9px;overflow:hidden}
.faq summary{padding:15px 16px;cursor:pointer;font-weight:600;font-size:15px;list-style:none}
.faq summary::-webkit-details-marker{display:none}
.faq summary::after{content:"+";float:right;color:var(--g);font-size:20px;line-height:1}
.faq details[open] summary::after{content:"\\2212"}
.faq .a{padding:0 16px 15px;font-size:14px;color:var(--mut)}
.ficha{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:14px}
.ficha h3{font-size:16px;margin-bottom:8px;color:var(--g)}
.ficha p{font-size:14px;color:var(--mut);margin-bottom:8px}
footer{background:var(--card);border-top:1px solid var(--line);padding:26px 18px 110px;text-align:center;font-size:12px;color:var(--mut)}
footer a{color:var(--g)}
.legalpie{max-width:640px;margin:12px auto 0;line-height:1.7}
"""


def nav(activa):
    it = [("index.html", "Κατάλογος", "tienda"),
          ("melos.html", "Γίνε Μέλος", "melos"),
          ("eukairia.html", "Επαγγελματική Ευκαιρία", "eukairia"),
          ("faq.html", "Συχνές Ερωτήσεις", "faq"),
          ("epikoinonia.html", "Επικοινωνία", "contacto"),
          ("nomika.html", "Πολιτικές", "legal")]
    return ("<nav><ul>" + "".join(
        f'<li><a href="{h}"{" class=\"on\"" if k == activa else ""}>{n}</a></li>'
        for h, n, k in it) + "</ul></nav>")


def pie_ancho(t):
    """Pie de pagina ancho, con las 4 columnas de informacion."""
    soc = []
    for k, n, u in (("instagram", "Instagram", "https://instagram.com/"),
                    ("tiktok", "TikTok", "https://tiktok.com/@"),
                    ("facebook", "Facebook", "https://facebook.com/")):
        v = t.get(k)
        if v and v not in PENDIENTE:
            soc.append(f'<a href="{u}{html.escape(v.lstrip("@"))}" target="_blank" rel="noopener">{n}</a>')
    soc_html = " · ".join(soc) if soc else '<span style="opacity:.5">—</span>'

    def d(campo, pre=""):
        v = t.get(campo)
        return (pre + html.escape(str(v))) if v and v not in PENDIENTE else \
               '<span style="opacity:.45">—</span>'

    return f"""
<div class="pieancho">
  <div class="pw">
    <div>
      <h4>Επικοινωνία</h4>
      <p>{d("horario")}</p>
      <p>{d("direccion")}</p>
      <p>{d("telefono_publico")}</p>
      <p><a href="mailto:{html.escape(t["email"])}">{html.escape(t["email"])}</a></p>
    </div>
    <div>
      <h4>Πληροφορίες</h4>
      <p><a href="melos.html">Γίνε Μέλος</a></p>
      <p><a href="eukairia.html">Επαγγελματική Ευκαιρία</a></p>
      <p><a href="faq.html">Συχνές Ερωτήσεις</a></p>
      <p><a href="epikoinonia.html">Ποιοι Είμαστε</a></p>
      <p><a href="epikoinonia.html#tracking">Παρακολούθηση Παραγγελίας</a></p>
    </div>
    <div>
      <h4>Πολιτικές Καταστήματος</h4>
      <p><a href="nomika.html#pliromes">Πολιτική Πληρωμών</a></p>
      <p><a href="nomika.html#apostoli">Πολιτική Αποστολής</a></p>
      <p><a href="nomika.html#epistrofes">Πολιτική Επιστροφών</a></p>
      <p><a href="nomika.html#oroi">Όροι Χρήσης</a></p>
      <p><a href="nomika.html#aporrito">Πολιτική Απορρήτου</a></p>
      <p><a href="nomika.html#apopoiisi">Αποποίηση Ευθυνών</a></p>
    </div>
    <div>
      <h4>Ακολουθήστε μας</h4>
      <p>{soc_html}</p>
      <h4 style="margin-top:16px">Τρόποι Πληρωμής</h4>
      <p class="pagoslogo">{pagos_badges(t)}</p>
    </div>
  </div>
</div>"""


def pagos_badges(t):
    p = t.get("_pago", {}) or {}
    b = []
    if p.get("iris"):
        b.append("IRIS")
    if p.get("antikatavoli"):
        b.append("Αντικαταβολή")
    if p.get("transferencia"):
        b.append("Τραπεζική κατάθεση")
    if p.get("efectivo"):
        b.append("Μετρητά")
    return "".join(f'<span class="pb">{x}</span>' for x in b) or "—"


def shell(t, titulo, desc, activa, cuerpo, extra_js=""):
    noindex = ("" if t.get("indexable")
               else '\n<meta name="robots" content="noindex,nofollow">')
    gemi = html.escape(str(t.get("gemi") or "—"))
    return f"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(desc)}">{noindex}
<meta name="theme-color" content="#f8f6f2">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;600;700&display=swap">
<style>{CSS}</style>
</head>
<body>
<header>
  <h1><a href="index.html">{html.escape(t["nombre"])}</a></h1>
  <p>Herbalife Nutrition · {html.escape(t["consultora"])}</p>
  <div class="rule"></div>
</header>
{nav(activa)}
{cuerpo}
{pie_ancho(t)}
<footer>
  <p><b>{html.escape(t["nombre"])}</b> · Ανεξάρτητο Μέλος Herbalife</p>
  <p>{html.escape(t["email"])} · ΓΕΜΗ: {gemi}</p>
  <div class="legalpie">
    <p>Τα προϊόντα Herbalife Nutrition δεν είναι φάρμακα και δεν προορίζονται για τη
    διάγνωση, θεραπεία ή πρόληψη ασθενειών. Τα αποτελέσματα διαφέρουν ανά άτομο.
    Συμβουλευτείτε τον γιατρό σας πριν από οποιοδήποτε πρόγραμμα διατροφής.</p>
    <p>Αυτή η ιστοσελίδα ανήκει σε Ανεξάρτητο Μέλος Herbalife και δεν ανήκει
    στη Herbalife Nutrition Ltd ούτε τη δεσμεύει.</p>
    <p>Δικαίωμα υπαναχώρησης 14 ημερών (Ν. 2251/1994) ·
    <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">Πλατφόρμα ΗΕΔ</a></p>
  </div>
  <p style="margin-top:14px;opacity:.6">&copy; {datetime.now().year} · Ενημερώθηκε {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
</footer>
{extra_js}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Pagina 1: la tienda
# ---------------------------------------------------------------------------

def tarjeta(p, sim, modo_catalogo=False, img=None):
    agotado = (not modo_catalogo) and p["stock"] <= 0
    nombre = html.escape(p["nombre_el"])
    desc = html.escape(p.get("descripcion_el", ""))
    precio = f'{p["precio"]:.2f}'.replace(".", ",")
    boton = ('<button class="btn" disabled>Εξαντλήθηκε</button>' if agotado else
             f'<button class="btn" onclick="add(\'{p["sku"]}\')">Προσθήκη</button>')
    badge = '<span class="badge">Εξαντλήθηκε</span>' if agotado else ""
    if img:
        media = f'<div class="ph has-img">{badge}<img src="{img}" alt="{nombre}" loading="lazy"></div>'
    else:
        media = f'<div class="ph">{badge}<span class="ph-t">{nombre[:2]}</span></div>'
    return f"""      <article class="card{' out' if agotado else ''}" data-cat="{p['categoria']}">
        {media}
        <h3>{nombre}</h3>
        <p class="desc">{desc}</p>
        <div class="row"><span class="price">{precio} {sim}</span>{boton}</div>
      </article>"""


def pagina_tienda(data):
    t, sim = data["tienda"], data["tienda"]["simbolo"]
    pago = data.get("pago", {})
    activos = [p for p in data["productos"] if p.get("activo")]
    cats = [c for c in data["categorias"] if any(p["categoria"] == c["id"] for p in activos)]

    chips = '<button class="chip on" onclick="filt(this,\'all\')">Όλα</button>' + "".join(
        f'<button class="chip" onclick="filt(this,\'{c["id"]}\')">{html.escape(c["nombre_el"])}</button>'
        for c in cats)
    fotos = {p["sku"]: buscar_imagen(p) for p in activos}
    cards = "\n".join(tarjeta(p, sim, t.get("modo_catalogo", False), fotos[p["sku"]])
                      for p in activos)
    con_foto = sum(1 for v in fotos.values() if v)

    # Metodos de pago ofrecidos en el carrito
    opciones = []
    if pago.get("iris"):
        opciones.append(('iris', 'IRIS άμεση πληρωμή',
                         ' <small>(άμεσα, χωρίς χρέωση για εσάς)</small>', 0))
    if pago.get("antikatavoli"):
        rec = pago.get("antikatavoli_coste", 0) or 0
        extra = (f" <small>(+{rec:.2f} {sim})</small>".replace(".", ",") if rec else
                 " <small>(χωρίς επιβάρυνση)</small>")
        opciones.append(('antikatavoli', 'Αντικαταβολή', extra, rec))
    if pago.get("transferencia"):
        opciones.append(('katathesi', 'Τραπεζική κατάθεση', '', 0))
    if pago.get("efectivo"):
        opciones.append(('metrita', 'Μετρητά με παράδοση στο χέρι', '', 0))
    if not opciones:
        opciones.append(('acordar', 'Συνεννόηση μέσω WhatsApp', '', 0))

    radios = "".join(
        f'<label><input type="radio" name="pg" value="{k}" data-rec="{r:.2f}"'
        f'{" checked" if i == 0 else ""} onchange="render()"> {n}{e}</label>'
        for i, (k, n, e, r) in enumerate(opciones))
    nombres_pago = {k: n for k, n, _, _ in opciones}

    cuerpo = f"""
<div class="wrap">
  <p style="text-align:center;color:var(--mut);font-size:14px;margin-bottom:4px">
    Αποστολή σε όλη την Ελλάδα · Δωρεάν άνω των {t["envio_gratis_desde"]:.2f} {sim}
  </p>
  <div class="chips">{chips}</div>
  <div class="grid" id="grid">
{cards}
  </div>
</div>

<div class="bar" id="bar">
  <div class="t"><span id="n">0 προϊόντα</span><b id="s">0,00 {sim}</b></div>
  <button class="btn" onclick="dlg.showModal();render()">Παραγγελία</button>
</div>

<dialog id="dlg">
  <div class="dh"><h2>Η παραγγελία σου</h2><button class="x" onclick="dlg.close()">&times;</button></div>
  <div class="items" id="items"></div>
  <div class="pagos"><h4>ΤΡΟΠΟΣ ΠΛΗΡΩΜΗΣ</h4>{radios}</div>
  <div class="tot">
    <div><span>Υποσύνολο</span><span id="sub">0,00 {sim}</span></div>
    <div><span>Μεταφορικά</span><span id="shp">0,00 {sim}</span></div>
    <div id="recRow" style="display:none"><span>Αντικαταβολή</span><span id="rec">0,00 {sim}</span></div>
    <div><span>Σύνολο</span><span class="g" id="grd">0,00 {sim}</span></div>
  </div>
  <a class="send" id="wa" href="#" target="_blank" rel="noopener">Αποστολή στο WhatsApp</a>
</dialog>
"""

    precios = {p["sku"]: {"n": p["nombre_el"], "p": p["precio"]} for p in activos}
    js = f"""<script>
var P = {json.dumps(precios, ensure_ascii=False)};
var PAGOS = {json.dumps(nombres_pago, ensure_ascii=False)};
var SHIP = {t["envio_coste"]:.2f}, FREE = {t["envio_gratis_desde"]:.2f};
var SIM = "{sim}", WA = "{t["telefono_whatsapp"]}";
var cart = {{}};
try {{ cart = JSON.parse(localStorage.getItem("rw_cart") || "{{}}"); }} catch(e) {{ cart = {{}}; }}
var dlg = document.getElementById("dlg");

function eur(n){{ return n.toFixed(2).replace(".", ",") + " " + SIM; }}
function save(){{ try{{ localStorage.setItem("rw_cart", JSON.stringify(cart)); }}catch(e){{}} }}
function count(){{ var c=0; for(var k in cart) c+=cart[k]; return c; }}
function sub(){{ var s=0; for(var k in cart) s += P[k].p * cart[k]; return s; }}
function ship(){{ var s=sub(); return (s<=0 || s>=FREE) ? 0 : SHIP; }}
function pg(){{ var r=document.querySelector('input[name=pg]:checked'); return r || null; }}
function rec(){{ var r=pg(); return (r && sub()>0) ? parseFloat(r.dataset.rec||0) : 0; }}
function tot(){{ return sub()+ship()+rec(); }}

function add(sku){{ cart[sku]=(cart[sku]||0)+1; save(); bar(); }}
function chg(sku,d){{ cart[sku]=(cart[sku]||0)+d; if(cart[sku]<=0) delete cart[sku]; save(); bar(); render(); }}

function bar(){{
  var b=document.getElementById("bar"), c=count();
  b.classList.toggle("on", c>0);
  document.getElementById("n").textContent = c + (c===1 ? " προϊόν" : " προϊόντα");
  document.getElementById("s").textContent = eur(tot());
}}

function render(){{
  var box=document.getElementById("items"), h="";
  for(var k in cart){{
    h += '<div class="it"><span class="nm">'+P[k].n+'</span>'
       + '<div class="qty"><button onclick="chg(\\''+k+'\\',-1)">-</button>'
       + '<span>'+cart[k]+'</span>'
       + '<button onclick="chg(\\''+k+'\\',1)">+</button></div>'
       + '<span>'+eur(P[k].p*cart[k])+'</span></div>';
  }}
  box.innerHTML = h || '<p style="padding:18px 0;color:var(--mut)">Το καλάθι είναι άδειο.</p>';
  document.getElementById("sub").textContent = eur(sub());
  document.getElementById("shp").textContent = ship()===0 ? "Δωρεάν" : eur(ship());
  var rr=document.getElementById("recRow");
  if(rec()>0){{ rr.style.display="flex"; document.getElementById("rec").textContent = eur(rec()); }}
  else {{ rr.style.display="none"; }}
  document.getElementById("grd").textContent = eur(tot());
  bar();

  var r=pg(), nombre = r ? (PAGOS[r.value]||r.value) : "-";
  var txt = "Γεια σας! Θέλω να παραγγείλω:\\n";
  for(var k in cart) txt += "\\u2022 " + cart[k] + "x " + P[k].n + " - " + eur(P[k].p*cart[k]) + "\\n";
  txt += "\\nΜεταφορικά: " + (ship()===0 ? "Δωρεάν" : eur(ship()));
  if(rec()>0) txt += "\\nΑντικαταβολή: " + eur(rec());
  txt += "\\nΤρόπος πληρωμής: " + nombre;
  txt += "\\nΣΥΝΟΛΟ: " + eur(tot());
  txt += "\\n\\nΟνοματεπώνυμο:\\nΔιεύθυνση:\\nΤ.Κ. / Πόλη:\\nΤηλέφωνο:";
  document.getElementById("wa").href = "https://wa.me/" + WA + "?text=" + encodeURIComponent(txt);
}}

function filt(btn, cat){{
  var cs=document.querySelectorAll(".chip");
  for(var i=0;i<cs.length;i++) cs[i].classList.remove("on");
  btn.classList.add("on");
  var cards=document.querySelectorAll(".card");
  for(var j=0;j<cards.length;j++){{
    cards[j].style.display = (cat==="all" || cards[j].dataset.cat===cat) ? "" : "none";
  }}
}}

for(var k in cart){{ if(!P[k]) delete cart[k]; }}
save(); bar();
</script>"""

    return shell(t, t["nombre"] + " | Herbalife Nutrition",
                 "Προϊόντα Herbalife Nutrition με προσωπική υποστήριξη. Αποστολή σε όλη την Ελλάδα.",
                 "tienda", cuerpo, js), len(activos), con_foto


# ---------------------------------------------------------------------------
# Pagina 2: Gine Melos
# ---------------------------------------------------------------------------

def pagina_melos(data):
    t, sim = data["tienda"], data["tienda"]["simbolo"]
    mi = data.get("miembro", {})
    sid = mi.get("sponsor_id") or "—"
    ape = mi.get("apellido_codigo") or "—"
    url = mi.get("url_registro") or ""
    falta = (mi.get("sponsor_id") in PENDIENTE) or (mi.get("url_registro") in PENDIENTE)

    aviso = ("""<div class="avisobox"><b>⚠ Σελίδα υπό κατασκευή.</b>
    Ο κωδικός συνεργάτη και ο σύνδεσμος εγγραφής δεν έχουν συμπληρωθεί ακόμη.
    Επικοινωνήστε μαζί μας απευθείας.</div>""" if falta else "")

    cta = (f'<a class="btn big" href="{html.escape(url)}" target="_blank" rel="noopener">Εγγραφή στη Herbalife</a>'
           if not falta else '<button class="btn big" disabled>Σύντομα διαθέσιμο</button>')

    cuerpo = f"""
<div class="wrap">
  {aviso}
  <div class="hero">
    <div class="big">{mi.get("descuento_min", 25)}% – {mi.get("descuento_max", 50)}%</div>
    <p>Μόνιμη έκπτωση σε όλα τα προϊόντα Herbalife Nutrition,<br>για πάντα, με μία μόνο εγγραφή.</p>
  </div>

  <h2 style="font-size:20px;margin:22px 0 6px">Τι είναι το Μέλος Herbalife;</h2>
  <p style="color:var(--mut);font-size:15px">
    Γίνεσαι επίσημο Μέλος της Herbalife Nutrition, παραγγέλνεις απευθείας από την εταιρεία
    σε τιμή Μέλους και κρατάς τη μόνιμη έκπτωση όσο παραμένεις εγγεγραμμένος.
    Δεν υπάρχει υποχρέωση ελάχιστης παραγγελίας ούτε υποχρέωση πώλησης.
  </p>

  <h2 style="font-size:20px;margin:24px 0 6px">Πώς γίνεται</h2>
  <ol class="pasos">
    <li><b>Πακέτο εγγραφής</b>
      Περιλαμβάνει Formula 1, shaker, δοσομετρητές, επίσημο τιμοκατάλογο Μέλους
      και πρόσβαση στην εφαρμογή.
      <small>{mi.get("kit_online", 0):.2f} {sim} online · {mi.get("kit_telefono", 0):.2f} {sim} τηλεφωνικά</small></li>
    <li><b>Εγγραφή στη Herbalife</b>
      Συμπληρώνεις τα στοιχεία σου στην επίσημη σελίδα της εταιρείας.
      <small>Η εγγραφή γίνεται απευθείας στη Herbalife, όχι σε αυτό το site.</small></li>
    <li><b>Στοιχεία Χορηγού</b>
      Στο πεδίο του χορηγού συμπληρώνεις:
      <span class="codigo">{html.escape(str(sid))}</span>
      <span class="codigo">{html.escape(str(ape))}</span>
      <small>Χωρίς αυτά τα στοιχεία δεν συνδέεσαι με την ομάδα μας και δεν έχεις υποστήριξη.</small></li>
    <li><b>Υποστήριξη</b>
      Προσωπική καθοδήγηση, πρόγραμμα στα μέτρα σου και παρακολούθηση.
      <small>Αυτό είναι που δεν αγοράζεται μόνο του.</small></li>
  </ol>

  <div style="text-align:center;margin:26px 0 40px">{cta}</div>

  <p style="color:var(--mut);font-size:13px;text-align:center;margin-bottom:60px">
    Η ιδιότητα του Μέλους δεν συνεπάγεται εισόδημα. Δείτε τη
    <a href="https://www.herbalife.com/content/dam/global-reusable-assets/documents/pd-statement-typical-distributor-earnings-el-gr.pdf" target="_blank" rel="noopener">Δήλωση Τυπικών Κερδών</a>
    της Herbalife.
  </p>
</div>
"""
    return shell(t, "Γίνε Μέλος | " + t["nombre"],
                 "Γίνε Μέλος Herbalife και απόκτησε μόνιμη έκπτωση σε όλα τα προϊόντα.",
                 "melos", cuerpo)


# ---------------------------------------------------------------------------
# Pagina 3: legal (BORRADOR)
# ---------------------------------------------------------------------------

def f(valor):
    """Marca en rojo lo que falta por rellenar."""
    if valor in PENDIENTE:
        return '<span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span>'
    return html.escape(str(valor))


def pagina_legal(data):
    t, sim = data["tienda"], data["tienda"]["simbolo"]
    pago = data.get("pago", {})

    metodos = []
    if pago.get("iris"):
        metodos.append(f"<li><b>IRIS άμεση πληρωμή</b> — άμεση μεταφορά από την "
                       f"τραπεζική σας εφαρμογή, χωρίς χρέωση για εσάς. "
                       f"Στοιχείο λήπτη: {f(pago.get('iris_id'))}.</li>")
    if pago.get("antikatavoli"):
        rec = pago.get("antikatavoli_coste", 0) or 0
        metodos.append("<li><b>Αντικαταβολή</b> — πληρωμή με την παράδοση, μόνο εντός Ελλάδας"
                       + (f" (επιβάρυνση {rec:.2f} {sim})".replace(".", ",") if rec else "")
                       + ".</li>")
    if pago.get("transferencia"):
        metodos.append(f"<li><b>Τραπεζική κατάθεση</b> — {f(pago.get('banco'))}, "
                       f"IBAN {f(pago.get('iban'))}, δικαιούχος {f(pago.get('titular'))}.</li>")
    if pago.get("efectivo"):
        metodos.append("<li><b>Μετρητά</b> — με παράδοση στο χέρι, κατόπιν συνεννόησης.</li>")
    if not metodos:
        metodos.append("<li>Κατόπιν συνεννόησης μέσω WhatsApp.</li>")

    cuerpo = f"""
<div class="wrap legal" style="padding-bottom:70px">
  <div class="avisobox"><b>⚠ ΠΡΟΣΧΕΔΙΟ.</b> Αυτό το κείμενο είναι πρότυπο και
  <b>δεν έχει ελεγχθεί από δικηγόρο</b>. Τα πεδία με την ένδειξη ΣΥΜΠΛΗΡΩΣΤΕ
  λείπουν. Μην δημοσιεύσετε το κατάστημα πριν ελεγχθεί.</div>

  <h2>Στοιχεία Επιχείρησης</h2>
  <ul>
    <li>Επωνυμία: {f(t.get("razon_social"))}</li>
    <li>Έδρα: {f(t.get("direccion"))}</li>
    <li>ΑΦΜ / ΔΟΥ: {f(t.get("afm"))} / {f(t.get("doy"))}</li>
    <li>ΓΕΜΗ: {f(t.get("gemi"))}</li>
    <li>Email: {html.escape(t["email"])}</li>
    <li>Τηλέφωνο: {f(t.get("telefono_publico"))}</li>
  </ul>
  <p>Ανεξάρτητο Μέλος Herbalife. Το παρόν κατάστημα δεν ανήκει στη Herbalife
  Nutrition και δεν τη δεσμεύει.</p>

  <h2 id="pliromes">Τρόποι Πληρωμής</h2>
  <ul>{"".join(metodos)}</ul>

  <h2 id="apostoli">Πολιτική Παράδοσης</h2>
  <p>Αποστολή σε όλη την Ελλάδα με courier. Κόστος αποστολής
  {t["envio_coste"]:.2f} {sim}, δωρεάν για παραγγελίες άνω των
  {t["envio_gratis_desde"]:.2f} {sim}. Χρόνος παράδοσης 1–3 εργάσιμες ημέρες,
  ανάλογα με την περιοχή.</p>

  <h2 id="epistrofes">Πολιτική Επιστροφών &amp; Υπαναχώρηση</h2>
  <p>Σύμφωνα με τον Ν. 2251/1994, έχετε δικαίωμα υπαναχώρησης εντός
  <b>14 ημερολογιακών ημερών</b> από την παραλαβή, χωρίς αιτιολόγηση.
  Τα προϊόντα πρέπει να επιστραφούν στην αρχική τους κατάσταση και συσκευασία,
  σφραγισμένα. Τα έξοδα επιστροφής βαρύνουν τον καταναλωτή, εκτός αν το προϊόν
  είναι ελαττωματικό ή εστάλη εκ παραδρομής.</p>
  <p>Η επιστροφή χρημάτων γίνεται εντός 14 ημερών από την παραλαβή της επιστροφής.</p>

  <h2 id="aporrito">Πολιτική Απορρήτου (GDPR)</h2>
  <p>Τα δεδομένα που μας δίνετε (όνομα, διεύθυνση, τηλέφωνο) χρησιμοποιούνται
  αποκλειστικά για την εκτέλεση της παραγγελίας σας και δεν διαβιβάζονται σε
  τρίτους, πέραν της εταιρείας courier.</p>
  <p>Η παραγγελία ολοκληρώνεται μέσω WhatsApp: η συνομιλία αποθηκεύεται στον
  λογαριασμό WhatsApp μας. Αυτός ο ιστότοπος <b>δεν χρησιμοποιεί cookies
  παρακολούθησης</b> ούτε εργαλεία αναλυτικών στοιχείων. Χρησιμοποιεί μόνο τοπική
  αποθήκευση (localStorage) στη συσκευή σας για να θυμάται το καλάθι σας· αυτά τα
  δεδομένα δεν φεύγουν ποτέ από τη συσκευή σας.</p>
  <p>Έχετε δικαίωμα πρόσβασης, διόρθωσης και διαγραφής των δεδομένων σας:
  {html.escape(t["email"])}. Εποπτική αρχή: Αρχή Προστασίας Δεδομένων
  Προσωπικού Χαρακτήρα (www.dpa.gr).</p>

  <h2 id="oroi">Όροι Χρήσης</h2>
  <p>Οι τιμές περιλαμβάνουν ΦΠΑ. Διατηρούμε το δικαίωμα αλλαγής τιμών χωρίς
  προειδοποίηση· η τιμή που ισχύει είναι αυτή τη στιγμή της επιβεβαίωσης της
  παραγγελίας.</p>
  <p>Τα προϊόντα Herbalife Nutrition είναι συμπληρώματα διατροφής και
  <b>δεν είναι φάρμακα</b>. Δεν προορίζονται για τη διάγνωση, θεραπεία ή πρόληψη
  ασθενειών. Δεν υποκαθιστούν μια ισορροπημένη διατροφή και έναν υγιεινό τρόπο
  ζωής. Τα αποτελέσματα διαφέρουν ανά άτομο.</p>

  <h2>Επίλυση Διαφορών</h2>
  <p>Για εξωδικαστική επίλυση μπορείτε να απευθυνθείτε στην πλατφόρμα ΗΕΔ της ΕΕ:
  <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">ec.europa.eu/consumers/odr</a></p>
</div>
"""
    return shell(t, "Πληροφορίες | " + t["nombre"],
                 "Όροι χρήσης, τρόποι πληρωμής, επιστροφές και πολιτική απορρήτου.",
                 "legal", cuerpo)


# ---------------------------------------------------------------------------

def pagina_faq(data):
    t = data["tienda"]
    items = data.get("faq", [])
    cuerpo = '<div class="wrap faq" style="padding-bottom:70px">' \
             '<h2 style="font-size:22px;margin:8px 0 16px">Συχνές Ερωτήσεις</h2>'
    for it in items:
        cuerpo += (f'<details><summary>{html.escape(it["q"])}</summary>'
                   f'<div class="a">{it["a"]}</div></details>')
    cuerpo += ('<p style="margin-top:24px;font-size:14px;color:var(--mut)">'
               'Δεν βρήκες αυτό που έψαχνες; '
               '<a href="epikoinonia.html" style="color:var(--g)">Γράψε μας</a>.</p></div>')
    return shell(t, "Συχνές Ερωτήσεις | " + t["nombre"],
                 "Απαντήσεις σε συχνές ερωτήσεις για τα προϊόντα Herbalife, "
                 "τις παραγγελίες, την αποστολή και την ιδιότητα του Μέλους.",
                 "faq", cuerpo)


def pagina_contacto(data):
    t = data["tienda"]

    def d(c):
        v = t.get(c)
        return html.escape(str(v)) if v and v not in PENDIENTE else \
               '<span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span>'

    wa = t["telefono_whatsapp"]
    boton_wa = (f'<a class="btn big" href="https://wa.me/{wa}" target="_blank" rel="noopener">'
                f'Γράψε μας στο WhatsApp</a>' if "X" not in wa else
                '<button class="btn big" disabled>WhatsApp σύντομα διαθέσιμο</button>')

    cuerpo = f"""
<div class="wrap legal" style="padding-bottom:70px">
  <h2 style="font-size:22px;margin:8px 0 14px">Ποιοι Είμαστε</h2>
  <div class="ficha">
    <h3>{html.escape(t["consultora"])}</h3>
    <p>Ανεξάρτητο Μέλος Herbalife Nutrition. Δεν πουλάμε απλώς προϊόντα:
    σχεδιάζουμε το πρόγραμμα μαζί, το προσαρμόζουμε στη ζωή σου και σε
    παρακολουθούμε κάθε εβδομάδα. Αυτό είναι που δεν αγοράζεται από ένα ράφι.</p>
    <p>Κάθε παραγγελία περνάει από εμάς προσωπικά. Δεν υπάρχει call center.</p>
  </div>

  <h2 style="font-size:22px;margin:26px 0 14px">Επικοινωνία</h2>
  <div class="ficha">
    <p><b>Ωράριο:</b> {d("horario")}</p>
    <p><b>Διεύθυνση:</b> {d("direccion")}</p>
    <p><b>Τηλέφωνο:</b> {d("telefono_publico")}</p>
    <p><b>Email:</b> <a href="mailto:{html.escape(t["email"])}" style="color:var(--g)">{html.escape(t["email"])}</a></p>
  </div>
  <div style="text-align:center;margin:22px 0">{boton_wa}</div>

  <h2 id="tracking" style="font-size:22px;margin:30px 0 14px">Παρακολούθηση Παραγγελίας</h2>
  <div class="ficha">
    <p>Μόλις σταλεί η παραγγελία σου, σου στέλνουμε τον αριθμό αποστολής
    (voucher) στο WhatsApp. Με αυτόν μπορείς να δεις πού βρίσκεται το δέμα σου
    απευθείας στην εταιρεία ταχυμεταφορών:</p>
    <p>
      <a href="https://www.acscourier.net/el/track-and-trace/" target="_blank" rel="noopener" style="color:var(--g)">ACS Courier</a> ·
      <a href="https://www.elta-courier.gr/search" target="_blank" rel="noopener" style="color:var(--g)">ΕΛΤΑ Courier</a> ·
      <a href="https://www.speedex.gr/isapohsi.asp" target="_blank" rel="noopener" style="color:var(--g)">Speedex</a> ·
      <a href="https://www.geniki.gr/el/track-trace" target="_blank" rel="noopener" style="color:var(--g)">Γενική Ταχυδρομική</a>
    </p>
    <p>Αν δεν έλαβες voucher μέσα σε 2 εργάσιμες, γράψε μας.</p>
  </div>
</div>
"""
    return shell(t, "Επικοινωνία | " + t["nombre"],
                 "Επικοινωνήστε μαζί μας. Ωράριο, διεύθυνση και παρακολούθηση παραγγελίας.",
                 "contacto", cuerpo)


def pagina_oportunidad(data):
    t = data["tienda"]
    mi = data.get("miembro", {})
    wa = t["telefono_whatsapp"]
    cta = (f'<a class="btn big" href="https://wa.me/{wa}?text='
           f'{("Γεια σας! Θα ήθελα πληροφορίες για την επαγγελματική ευκαιρία Herbalife.").replace(" ", "%20")}"'
           f' target="_blank" rel="noopener">Θέλω περισσότερες πληροφορίες</a>'
           if "X" not in wa else
           '<button class="btn big" disabled>Σύντομα διαθέσιμο</button>')

    cuerpo = f"""
<div class="wrap" style="padding-bottom:70px">
  <div class="hero">
    <div class="big" style="font-size:30px">Επαγγελματική Ευκαιρία</div>
    <p>Δούλεψε με δικούς σου ρυθμούς, από όπου θέλεις,<br>
    με μια εταιρεία που δραστηριοποιείται από το 1980.</p>
  </div>

  <h2 style="font-size:20px;margin:24px 0 10px">Τι σημαίνει στην πράξη</h2>
  <div class="ficha">
    <h3>Χωρίς υποχρεώσεις</h3>
    <p>Δεν υπάρχει ελάχιστη παραγγελία, ούτε υποχρέωση αγοράς εργαλείων πώλησης,
    ούτε στόχοι που πρέπει να πιάσεις.</p>
  </div>
  <div class="ficha">
    <h3>Δικό σου ωράριο</h3>
    <p>Μπορεί να είναι συμπληρωματικό εισόδημα δίπλα στη δουλειά σου, ή η κύρια
    ασχολία σου. Εσύ αποφασίζεις πόσο χρόνο βάζεις.</p>
  </div>
  <div class="ficha">
    <h3>Εκπαίδευση και ομάδα</h3>
    <p>Δεν ξεκινάς μόνος. Υπάρχει εκπαίδευση, υλικό και μια ομάδα που έχει ήδη
    περάσει από εκεί που είσαι τώρα.</p>
  </div>
  <div class="ficha">
    <h3>Έκπτωση Μέλους από την πρώτη μέρα</h3>
    <p>Ως Ανεξάρτητο Μέλος αγοράζεις τα προϊόντα με έκπτωση
    {mi.get("descuento_min", 25)}% και άνω, είτε τα χρησιμοποιήσεις μόνος σου
    είτε όχι. Δες τη σελίδα <a href="melos.html" style="color:var(--g)">Γίνε Μέλος</a>.</p>
  </div>

  <div style="text-align:center;margin:28px 0">{cta}</div>

  <div class="avisobox">
    <b>Σημαντική διευκρίνιση.</b> Η ιδιότητα του Ανεξάρτητου Μέλους
    <b>δεν εγγυάται κανένα εισόδημα</b>. Τα αποτελέσματα εξαρτώνται από τη δουλειά
    που θα κάνεις. Πριν πάρεις οποιαδήποτε απόφαση, διάβασε τη
    <a href="https://www.herbalife.com/content/dam/global-reusable-assets/documents/pd-statement-typical-distributor-earnings-el-gr.pdf" target="_blank" rel="noopener">Δήλωση Τυπικών Κερδών</a>
    που δημοσιεύει η ίδια η Herbalife. Δεν υποσχόμαστε ποσά και δεν θα σου
    ζητήσουμε να αγοράσεις απόθεμα.
  </div>
</div>
"""
    return shell(t, "Επαγγελματική Ευκαιρία | " + t["nombre"],
                 "Η επαγγελματική ευκαιρία Herbalife: πώς λειτουργεί, χωρίς υποσχέσεις.",
                 "eukairia", cuerpo)


def construir(data):
    t = data["tienda"]
    # el pie necesita saber que metodos de pago hay activos
    t["_pago"] = data.get("pago", {})
    SITE.mkdir(parents=True, exist_ok=True)

    tienda_html, n, con_foto = pagina_tienda(data)
    (SITE / "index.html").write_text(tienda_html, encoding="utf-8")
    (SITE / "melos.html").write_text(pagina_melos(data), encoding="utf-8")
    (SITE / "eukairia.html").write_text(pagina_oportunidad(data), encoding="utf-8")
    (SITE / "faq.html").write_text(pagina_faq(data), encoding="utf-8")
    (SITE / "epikoinonia.html").write_text(pagina_contacto(data), encoding="utf-8")
    (SITE / "nomika.html").write_text(pagina_legal(data), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    # Mientras la tienda no este lista (precios sin verificar, telefono falso,
    # sin GEMI), se bloquea la indexacion.
    (SITE / "robots.txt").write_text(
        "User-agent: *\n" + ("Allow: /\n" if t.get("indexable") else "Disallow: /\n"),
        encoding="utf-8")

    # CNAME solo cuando el DNS ya existe: si se activa antes, GitHub redirige
    # <usuario>.github.io al dominio que aun no resuelve y todo queda inaccesible.
    cname = SITE / "CNAME"
    if t.get("cname_activo"):
        cname.write_text(t["dominio"] + "\n", encoding="utf-8")
    elif cname.exists():
        cname.unlink()

    return SITE / "index.html", n, con_foto


def main():
    global SITE, OPS
    if "--out" in sys.argv:
        base = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
        SITE, OPS = base / "docs", base / "ops"
        print("  Salida redirigida -> " + str(base))

    data = cargar()
    errores, avisos = validar(data)
    for a in avisos:
        print("  AVISO   " + a)
    for e in errores:
        print("  ERROR   " + e)

    ruta, n, con_foto = construir(data)
    inv = escribir_inventario(data)

    def corto(p):
        try:
            return str(p.relative_to(RAIZ))
        except ValueError:
            return str(p)

    print("")
    print("  Paginas    -> index.html (" + str(n) + " productos), melos.html, nomika.html")
    print("  Carpeta    -> " + corto(ruta.parent))
    print("  Inventario -> " + corto(inv))
    print("  Fotos      -> " + str(con_foto) + " de " + str(n) + " con foto" +
          ("" if con_foto == n else "  <- faltan " + str(n - con_foto)))
    if errores:
        print("")
        print("  NO PUBLICAR: " + str(len(errores)) + " error(es) arriba.")
        return 1
    print("")
    print("  Listo para publicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
