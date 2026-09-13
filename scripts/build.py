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
header{background:#1e2221;border-bottom:1px solid #333;color:#f8f6f2;padding:18px 18px 16px;text-align:center}
header h1{font-size:0;margin:0;line-height:0}
header h1 a{display:inline-block;line-height:0}
header .logo-img{height:54px;max-width:220px;object-fit:contain}
header p{color:#9faf9c;font-size:12px;margin-top:8px;letter-spacing:.6px;text-transform:uppercase}
header .rule{width:44px;height:1px;background:#9faf9c;margin:10px auto 0;opacity:.7}
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
.ph{position:relative;height:180px;border-radius:10px;background:linear-gradient(150deg,#f2efe8,#dfe6da);display:grid;place-items:center;margin-bottom:10px}
.ph-t{font-size:36px;font-weight:700;color:var(--g);opacity:.42;letter-spacing:1px}
.ph.has-img{background:#fff;overflow:hidden}
.ph.has-img img{width:100%;height:100%;object-fit:contain;display:block;padding:6px}
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
.badge-encargo{position:absolute;top:8px;right:8px;background:rgba(90,115,86,.85);color:#fff;font-size:10px;padding:3px 7px;border-radius:6px;font-weight:600;letter-spacing:.3px}
.search-wrap{padding:10px 0 0;display:flex;gap:8px;align-items:center}
.search-box{flex:1;border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:15px;background:var(--card);color:var(--ink);outline:none}
.search-box:focus{border-color:var(--g);box-shadow:0 0 0 2px rgba(90,115,86,.15)}
.card{transition:box-shadow .2s,transform .2s}
.card:hover{box-shadow:0 4px 16px rgba(90,115,86,.15);transform:translateY(-1px)}
.kratisi-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:14px}
.kratisi-card h3{font-size:17px;color:var(--g);margin-bottom:8px}
.kratisi-card p{font-size:14px;color:var(--mut);margin-bottom:8px}
.kratisi-card .price-range{font-size:17px;font-weight:700;color:var(--g);margin-bottom:12px}
.step-pill{display:inline-block;background:var(--g);color:#fff;border-radius:6px;padding:3px 10px;font-size:12px;font-weight:600;margin-bottom:8px}
.ficha{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:14px}
.ficha h3{font-size:16px;margin-bottom:8px;color:var(--g)}
.ficha p{font-size:14px;color:var(--mut);margin-bottom:8px}
footer{background:var(--card);border-top:1px solid var(--line);padding:26px 18px 110px;text-align:center;font-size:12px;color:var(--mut)}
footer a{color:var(--g)}
.legalpie{max-width:640px;margin:12px auto 0;line-height:1.7}
"""


def nav(activa):
    it = [("index.html", "Κατάλογος", "tienda"),
          ("kratisi.html", "Κρατήσεις", "kratisi"),
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
    _og_base = ("https://" + t["dominio"] if t.get("cname_activo")
               else "https://neopram.github.io/royalwellness")
    _pmap = {"tienda": "index.html", "kratisi": "kratisi.html",
             "melos": "melos.html", "eukairia": "eukairia.html",
             "faq": "faq.html", "contacto": "epikoinonia.html",
             "legal": "nomika.html"}
    _og_url   = _og_base + "/" + _pmap.get(activa, "index.html")
    _og_img   = _og_base + "/assets/icon-512.png"
    _og_title = html.escape(titulo)
    _og_desc  = html.escape(desc)
    _og_name  = html.escape(t["nombre"])
    _faq  = t.get("_faq", [])
    _faq_js = json.dumps([{"q": f["q"], "a": f["a"]} for f in _faq],
                         ensure_ascii=False, separators=(",", ":"))
    _wa_num = str(t.get("telefono_whatsapp", "") or "")
    _wa_href = ("https://wa.me/" + _wa_num) if (_wa_num and "PENDIENTE" not in _wa_num and "XXXXXXXXXX" not in _wa_num) else "#"
    return f"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(desc)}">{noindex}
<meta property="og:title" content="{_og_title}">
<meta property="og:description" content="{_og_desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{_og_name}">
<meta property="og:locale" content="el_GR">
<meta property="og:image" content="{_og_img}">
<meta property="og:url" content="{_og_url}">
<meta name="twitter:card" content="summary">
<link rel="canonical" href="{_og_url}">
<meta name="theme-color" content="#f8f6f2">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;600;700&display=swap">
<link rel="apple-touch-icon" href="assets/icon-192.png">
<link rel="manifest" href="manifest.json">
<style>{CSS}</style>
</head>
<body>
<header>
  <h1><a href="index.html"><img class="logo-img" src="assets/logo-white.png" alt="{html.escape(t["nombre"])}"></a></h1>
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

<style>
#cw-btn{{position:fixed;bottom:22px;right:22px;width:52px;height:52px;background:var(--g);color:#fff;border-radius:50%;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 14px rgba(90,115,86,.45);z-index:1001;display:flex;align-items:center;justify-content:center;transition:transform .15s}}
#cw-btn:hover{{transform:scale(1.09)}}
#cw-panel{{position:fixed;bottom:84px;right:22px;width:320px;max-height:460px;background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.18);display:flex;flex-direction:column;z-index:1000;overflow:hidden}}
#cw-panel[hidden]{{display:none!important}}
#cw-head{{background:var(--g);color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:14px}}
#cw-x{{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0;line-height:1}}
#cw-msgs{{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;min-height:120px}}
.cw-b,.cw-u{{max-width:85%;padding:9px 12px;border-radius:12px;font-size:13.5px;line-height:1.45}}
.cw-b{{background:var(--bg);border:1px solid var(--line);align-self:flex-start;border-bottom-left-radius:4px}}
.cw-u{{background:var(--g);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}}
.cw-b a{{color:var(--g);font-weight:600}}
#cw-chips{{display:flex;flex-wrap:wrap;gap:6px;padding:0 10px 8px}}
.cw-chip{{background:var(--bg);border:1px solid var(--g);color:var(--g);border-radius:20px;padding:5px 11px;font-size:12px;cursor:pointer;white-space:nowrap}}
.cw-chip:hover{{background:var(--g);color:#fff}}
#cw-bar{{display:flex;gap:6px;padding:8px 10px;border-top:1px solid var(--line)}}
#cw-in{{flex:1;border:1px solid var(--line);border-radius:20px;padding:8px 13px;font-size:13.5px;background:var(--bg);color:var(--ink);outline:none}}
#cw-in:focus{{border-color:var(--g)}}
#cw-go{{background:var(--g);color:#fff;border:none;border-radius:50%;width:36px;height:36px;font-size:18px;cursor:pointer;flex-shrink:0}}
@media(max-width:380px){{#cw-panel{{width:calc(100vw - 20px);right:10px}}}}
</style>
<button id="cw-btn" type="button" aria-label="Βοήθεια">💬</button>
<div id="cw-panel" hidden>
  <div id="cw-head">Royal Wellness — Βοήθεια<button id="cw-x" type="button">×</button></div>
  <div id="cw-msgs"></div>
  <div id="cw-chips">
    <button class="cw-chip">Αποστολή</button>
    <button class="cw-chip">Επιστροφές</button>
    <button class="cw-chip">Γίνε Μέλος</button>
    <button class="cw-chip">Παραγγελία</button>
  </div>
  <div id="cw-bar">
    <input id="cw-in" type="text" placeholder="Ρώτα κάτι…" autocomplete="off">
    <button id="cw-go">→</button>
  </div>
</div>
<script>
(function(){{
var FAQ={_faq_js};
var WA="{_wa_href}";
var btn=document.getElementById("cw-btn");
var panel=document.getElementById("cw-panel");
var msgs=document.getElementById("cw-msgs");
var inp=document.getElementById("cw-in");
function norm(s){{return s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"");}}
function findAnswer(q){{
  var nq=norm(q);
  var best=null,top=0;
  for(var i=0;i<FAQ.length;i++){{
    var words=norm(FAQ[i].q).split(/\s+/);
    var sc=0;
    words.forEach(function(w){{if(w.length>2&&nq.indexOf(w)>=0)sc++;}});
    if(sc>top){{top=sc;best=FAQ[i];}}
  }}
  return top>0?best.a:null;
}}
function addMsg(html,cls){{
  var d=document.createElement("div");
  d.className=cls;
  d.innerHTML=html;
  msgs.appendChild(d);
  msgs.scrollTop=msgs.scrollHeight;
}}
function send(q){{
  q=q.trim();if(!q)return;
  addMsg(q,"cw-u");
  inp.value="";
  var a=findAnswer(q);
  setTimeout(function(){{
    addMsg(a||(WA!="#"?'Δεν βρήκα απάντηση. <a href="'+WA+'" target="_blank" rel="noopener">Γράψε μας στο WhatsApp →</a>':'Δεν βρήκα απάντηση. Επικοινώνησε μαζί μας.'),
      "cw-b");
  }},280);
}}
btn.addEventListener("click",function(){{
  panel.hidden=!panel.hidden;
  if(!panel.hidden&&!msgs.children.length){{
    addMsg("Γεια! 👋 Πες μου τι θέλεις να ξέρεις — για προϊόντα, αποστολή ή παραγγελίες.","cw-b");
  }}
}});
document.getElementById("cw-x").addEventListener("click",function(){{panel.hidden=true;}});
document.getElementById("cw-go").addEventListener("click",function(){{send(inp.value);}});
inp.addEventListener("keydown",function(e){{if(e.key==="Enter")send(inp.value);}});
document.querySelectorAll(".cw-chip").forEach(function(c){{
  c.addEventListener("click",function(){{send(c.textContent);}});
}});
}})();
</script>
{extra_js}
<script>if("serviceWorker"in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{{}})</script>
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
    encargo = '<span class="badge-encargo">\u03ba\u03b1\u03c4\u0027 \u03b5\u03bd\u03c4\u03bf\u03bb\u03ae</span>' if (modo_catalogo and p.get("stock", 0) <= 0) else ""
    if img:
        media = f'<div class="ph has-img">{badge}{encargo}<img src="{img}" alt="{nombre}" loading="lazy"></div>'
    else:
        media = f'<div class="ph">{badge}{encargo}<span class="ph-t">{nombre[:2]}</span></div>'
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
  <div class="search-wrap">
    <input class="search-box" type="search" id="srch" placeholder="\u0391\u03bd\u03b1\u03b6\u03ae\u03c4\u03b7\u03c3\u03b7 \u03c0\u03c1\u03bf\u03b9\u03cc\u03bd\u03c4\u03bf\u03c2\u2026" oninput="buscar(this.value)" autocomplete="off">
  </div>
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

function buscar(q){{
  var cards=document.querySelectorAll(".card");
  q=q.toLowerCase().trim();
  for(var j=0;j<cards.length;j++){{
    var el=cards[j];
    var t2=(el.querySelector("h3")||{{}}).textContent||"";
    var d2=(el.querySelector(".desc")||{{}}).textContent||"";
    el.style.display=(!q||t2.toLowerCase().indexOf(q)>=0||d2.toLowerCase().indexOf(q)>=0)?"":"none";
  }}
  if(q){{
    document.querySelectorAll(".chip").forEach(function(c){{c.classList.remove("on")}});
    document.querySelector(".chip").classList.add("on");
  }}
}}
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

    envio_coste_str = f"{t['envio_coste']:.2f}".replace(".", ",")
    envio_gratis_str = f"{t['envio_gratis_desde']:.2f}".replace(".", ",")

    cuerpo = f"""
<div class="wrap legal" style="padding-bottom:70px">
  <div class="avisobox">
    <b>⚠ ΠΡΟΣΧΕΔΙΟ — ΚΕΙΜΕΝΟ ΥΠΟ ΝΟΜΙΚΟ ΕΛΕΓΧΟ.</b>
    Το παρόν κείμενο αποτελεί <b>πρότυπο (template)</b> και <b>δεν έχει ελεγχθεί από δικηγόρο</b>.
    Δεν συνιστά νομική συμβουλή. Όλα τα πεδία που φέρουν την ένδειξη
    <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span> εκκρεμούν και είναι <b>υποχρεωτικά</b> κατά τον
    Ν. 2251/1994 και το Π.Δ. 131/2003 για κάθε ελληνικό ηλεκτρονικό κατάστημα.
    <b>Μην θέσετε το κατάστημα σε λειτουργία και μην δημοσιεύσετε τη σελίδα πριν από τον
    έλεγχο και τη συμπλήρωσή της.</b>
    Τελευταία ενημέρωση κειμένου: <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span>.
  </div>

  <h2 id="stoixeia">1. Στοιχεία Επιχείρησης</h2>
  <p>Σύμφωνα με το άρθρο 4 του Π.Δ. 131/2003 και το άρθρο 3β του Ν. 2251/1994 περί
  προστασίας των καταναλωτών, σας γνωστοποιούμε τα ακόλουθα στοιχεία του φορέα
  εκμετάλλευσης του παρόντος ιστοτόπου:</p>
  <ul>
    <li><b>Εμπορική ονομασία καταστήματος:</b> Royal Wellness</li>
    <li><b>Επωνυμία / νόμιμος εκπρόσωπος:</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span> (Βασιλική Ανδρουτσοπούλου, Ανεξάρτητο Μέλος Herbalife)</li>
    <li><b>Έδρα / ταχυδρομική διεύθυνση:</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span></li>
    <li><b>Α.Φ.Μ. / Δ.Ο.Υ.:</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span> / <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span></li>
    <li><b>Αριθμός Γ.Ε.ΜΗ.:</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span></li>
    <li><b>Κύρια δραστηριότητα (Κ.Α.Δ.):</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span></li>
    <li><b>Τηλέφωνο επικοινωνίας:</b> <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span></li>
    <li><b>Ηλεκτρονικό ταχυδρομείο:</b> dravasi20@gmail.com</li>
    <li><b>Ώρες εξυπηρέτησης:</b> Δευτέρα έως Κυριακή, 9:00 — 21:00</li>
  </ul>
  <p>Για κάθε ερώτημα, παράπονο ή άσκηση δικαιώματος μπορείτε να απευθύνεστε στα
  ανωτέρω στοιχεία επικοινωνίας. Απαντούμε σε κάθε γραπτό αίτημα εντός εύλογου
  χρόνου και, σε κάθε περίπτωση, εντός των προθεσμιών που ορίζει ο νόμος.</p>
  <p><b>Δήλωση ανεξαρτησίας:</b> Ο παρών ιστότοπος ανήκει και λειτουργεί από
  <b>Ανεξάρτητο Μέλος Herbalife</b>. <b>Δεν ανήκει, δεν λειτουργεί και δεν ελέγχεται από τη
  Herbalife Nutrition Ltd</b> ούτε από συνδεδεμένη με αυτήν εταιρεία, και το περιεχόμενό του
  δεν τη δεσμεύει. Τα εμπορικά σήματα, οι ονομασίες και οι εικόνες προϊόντων Herbalife
  Nutrition ανήκουν στον δικαιούχο τους και χρησιμοποιούνται αποκλειστικά για την
  παρουσίαση των διατιθέμενων προϊόντων.</p>
  <p><b>Αρμόδιες αρχές εποπτείας:</b> Γενική Γραμματεία Εμπορίου — Διεύθυνση Προστασίας
  Καταναλωτή (γραμμή καταναλωτή 1520) και Συνήγορος του Καταναλωτή
  (<a href="https://www.synigoroskatanaloti.gr" target="_blank" rel="noopener">synigoroskatanaloti.gr</a>).</p>

  <h2 id="pliromes">2. Πολιτική Πληρωμών</h2>
  <p>Όλες οι τιμές του καταλόγου αναγράφονται σε <b>ευρώ (EUR, €)</b> και
  <b>περιλαμβάνουν τον αναλογούντα Φ.Π.Α.</b> Τυχόν έξοδα αποστολής ή επιβάρυνση
  αντικαταβολής υπολογίζονται χωριστά και εμφανίζονται αναλυτικά πριν από την
  οριστικοποίηση της παραγγελίας, ώστε να γνωρίζετε το <b>συνολικό τελικό κόστος</b>
  πριν δεσμευτείτε.</p>
  <h3>2.1 Αποδεκτοί τρόποι πληρωμής</h3>
  <ul>{"".join(metodos)}</ul>
  <h3>2.2 Πληρωμές με κάρτα</h3>
  <p>Το κατάστημα <b>δεν διαθέτει προς το παρόν σύστημα πληρωμής με πιστωτική ή χρεωστική
  κάρτα</b> και <b>δεν ζητά, δεν συλλέγει και δεν αποθηκεύει σε καμία περίπτωση στοιχεία
  καρτών</b>. Εάν λάβετε μήνυμα που σας ζητά στοιχεία κάρτας ή κωδικούς δήθεν εκ μέρους
  μας, <b>μην απαντήσετε</b> και ενημερώστε μας άμεσα.</p>
  <h3>2.3 Παραστατικά</h3>
  <p>Για κάθε παραγγελία εκδίδεται νόμιμο φορολογικό παραστατικό (απόδειξη λιανικής ή
  τιμολόγιο, εφόσον δηλώσετε επαγγελματικά στοιχεία κατά την παραγγελία). Η παραγγελία
  θεωρείται εξοφλημένη μόνο με την πίστωση του ποσού ή την καταβολή κατά την παράδοση.
  Σε περίπτωση μη εξόφλησης εντός <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span> ημερών από την
  επιβεβαίωση, η παραγγελία ακυρώνεται χωρίς άλλη ειδοποίηση.</p>

  <h2 id="apostoli">3. Πολιτική Αποστολής &amp; Παράδοσης</h2>
  <p>Οι αποστολές πραγματοποιούνται σε όλη την Ελλάδα μέσω συνεργαζόμενης εταιρείας
  ταχυμεταφορών (courier).</p>
  <ul>
    <li><b>Κόστος αποστολής:</b> {envio_coste_str} {sim} ανά παραγγελία.</li>
    <li><b>Δωρεάν αποστολή:</b> για παραγγελίες αξίας άνω των {envio_gratis_str} {sim}.</li>
    <li><b>Χρόνος παράδοσης:</b> 1–3 εργάσιμες ημέρες από την επιβεβαίωση και την εξόφληση της παραγγελίας.</li>
    <li><b>Δυσπρόσιτες περιοχές και νησιά:</b> ενδέχεται να απαιτηθούν 1–2 επιπλέον εργάσιμες ημέρες και, κατά περίπτωση, πρόσθετη χρέωση της εταιρείας courier, για την οποία ενημερώνεστε εκ των προτέρων.</li>
    <li><b>Παραλαβή από το χέρι:</b> διαθέσιμη κατόπιν συνεννόησης, χωρίς κόστος αποστολής.</li>
  </ul>
  <p>Σε κάθε περίπτωση, και σύμφωνα με το άρθρο 3ιη του Ν. 2251/1994, τα προϊόντα
  παραδίδονται <b>το αργότερο εντός τριάντα (30) ημερολογιακών ημερών</b> από τη σύναψη της
  σύμβασης. Εάν, για λόγο ανωτέρας βίας ή έλλειψης αποθέματος, δεν είναι δυνατή η
  παράδοση εντός της προθεσμίας, ενημερώνεστε άμεσα και δικαιούστε είτε να συμφωνήσετε
  νέα ημερομηνία είτε να υπαναχωρήσετε με πλήρη επιστροφή των χρημάτων σας.</p>
  <p>Ο <b>κίνδυνος απώλειας ή βλάβης</b> των προϊόντων μετατίθεται σε εσάς κατά τη φυσική
  παραλαβή τους. Παρακαλούμε <b>ελέγξτε τη συσκευασία ενώπιον του διανομέα</b>. Εάν
  διαπιστώσετε εμφανή φθορά, έχετε δικαίωμα να αρνηθείτε την παραλαβή ή να ζητήσετε
  σχετική σημείωση επί του αποδεικτικού παράδοσης και να μας ενημερώσετε
  <b>εντός δύο (2) εργάσιμων ημερών</b>.</p>

  <h2 id="epistrofes">4. Επιστροφές &amp; Δικαίωμα Υπαναχώρησης</h2>
  <h3>4.1 Δικαίωμα υπαναχώρησης (14 ημέρες)</h3>
  <p>Ως καταναλωτής έχετε δικαίωμα να <b>υπαναχωρήσετε αναιτιολόγητα εντός δεκατεσσάρων
  (14) ημερολογιακών ημερών</b> από την ημέρα που εσείς ή τρίτος που έχετε ορίσει
  αποκτήσατε τη φυσική κατοχή των προϊόντων, σύμφωνα με τα άρθρα 3ε έως 3ια του
  <b>Ν. 2251/1994</b>, όπως ισχύει μετά την <b>Κ.Υ.Α. Ζ1-891/2013</b> (Οδηγία 2011/83/ΕΕ).</p>
  <p>Για να ασκήσετε το δικαίωμα αρκεί να μας δηλώσετε <b>ρητά και πριν από τη λήξη της
  προθεσμίας</b> την απόφασή σας, με μήνυμα ηλεκτρονικού ταχυδρομείου στο
  dravasi20@gmail.com ή γραπτώς στη διεύθυνσή μας. Μπορείτε να χρησιμοποιήσετε το
  ακόλουθο υπόδειγμα, χωρίς να είναι υποχρεωτικό:</p>
  <p><i>«Προς Royal Wellness — Με το παρόν δηλώνω ότι υπαναχωρώ από τη σύμβαση πώλησης των
  κάτωθι αγαθών: […]. Ημερομηνία παραγγελίας / παραλαβής: […]. Ονοματεπώνυμο και
  διεύθυνση καταναλωτή: […]. Ημερομηνία: […]».</i></p>
  <h3>4.2 Επιστροφή προϊόντων και χρημάτων</h3>
  <p>Οφείλετε να επιστρέψετε τα προϊόντα <b>χωρίς αδικαιολόγητη καθυστέρηση και εντός
  δεκατεσσάρων (14) ημερών</b> από τη δήλωση υπαναχώρησης, στην αρχική τους κατάσταση,
  πλήρη, <b>σφραγισμένα</b> και με την αρχική συσκευασία. Τα <b>άμεσα έξοδα επιστροφής
  βαρύνουν εσάς</b>, εκτός εάν το προϊόν είναι ελαττωματικό, εσφαλμένο ή εστάλη εκ
  παραδρομής, οπότε τα αναλαμβάνουμε εξ ολοκλήρου εμείς. Ευθύνεστε μόνο για τυχόν
  μείωση της αξίας που οφείλεται σε χειρισμό πέραν του αναγκαίου για τη διαπίστωση της
  φύσης και της λειτουργίας του προϊόντος.</p>
  <p>Θα σας επιστρέψουμε <b>όλα τα ποσά που λάβαμε, συμπεριλαμβανομένων των εξόδων
  αρχικής αποστολής</b> (πλην τυχόν πρόσθετου κόστους λόγω επιλογής ταχύτερης αποστολής),
  χωρίς αδικαιολόγητη καθυστέρηση και <b>εντός δεκατεσσάρων (14) ημερών</b> από τη στιγμή που
  θα ενημερωθούμε για την υπαναχώρησή σας. Διατηρούμε το δικαίωμα να παρακρατήσουμε την
  επιστροφή έως ότου παραλάβουμε τα προϊόντα ή λάβουμε απόδειξη αποστολής τους. Η
  επιστροφή γίνεται με το ίδιο μέσο πληρωμής ή με τραπεζική μεταφορά στον λογαριασμό που
  θα μας υποδείξετε, χωρίς καμία επιβάρυνσή σας.</p>
  <h3>4.3 Εξαιρέσεις από το δικαίωμα υπαναχώρησης</h3>
  <p>Σύμφωνα με το άρθρο 3ιβ του Ν. 2251/1994, το δικαίωμα υπαναχώρησης
  <b>δεν ισχύει</b> για: (α) <b>σφραγισμένα αγαθά που δεν είναι κατάλληλα προς επιστροφή για
  λόγους προστασίας της υγείας ή υγιεινής και τα οποία αποσφραγίστηκαν μετά την
  παράδοση</b> — κατηγορία στην οποία εμπίπτουν τα ανοιγμένα συμπληρώματα διατροφής και
  ροφήματα· (β) αγαθά που αλλοιώνονται ή λήγουν σύντομα· (γ) αγαθά που, μετά την
  παράδοση, αναμείχθηκαν αδιαχώριστα με άλλα.</p>
  <h3>4.4 Νόμιμη εγγύηση — ελαττωματικά προϊόντα</h3>
  <p>Ανεξάρτητα από το δικαίωμα υπαναχώρησης, ισχύει η <b>νόμιμη εγγύηση συμμόρφωσης</b>
  του πωλητή (άρθρα 534 επ. Α.Κ. και Ν. 4967/2022). Εάν παραλάβετε προϊόν ελαττωματικό,
  ληγμένο, με παραβιασμένη σφράγιση ή διαφορετικό από αυτό που παραγγείλατε,
  επικοινωνήστε μαζί μας <b>εντός δύο (2) εργάσιμων ημερών</b> από την παραλαβή,
  αποστέλλοντας φωτογραφίες. Δικαιούστε, κατ' επιλογήν σας, <b>αντικατάσταση,
  μείωση τιμήματος ή πλήρη επιστροφή χρημάτων</b>, χωρίς καμία επιβάρυνσή σας.</p>
  <h3>4.5 Εξωδικαστική επίλυση διαφορών</h3>
  <p>Για κάθε διαφορά μπορείτε να απευθυνθείτε στην <b>ευρωπαϊκή πλατφόρμα Ηλεκτρονικής
  Επίλυσης Διαφορών (ΗΕΔ / ODR)</b> της Ευρωπαϊκής Επιτροπής:
  <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">ec.europa.eu/consumers/odr</a>,
  καθώς και στον <b>Συνήγορο του Καταναλωτή</b> (Λ. Αλεξάνδρας 144, 114 71 Αθήνα,
  <a href="https://www.synigoroskatanaloti.gr" target="_blank" rel="noopener">synigoroskatanaloti.gr</a>)
  ή στις κατά τόπους Επιτροπές Φιλικού Διακανονισμού. Η προσφυγή στους ανωτέρω φορείς
  δεν θίγει το δικαίωμά σας να προσφύγετε στα αρμόδια δικαστήρια.</p>

  <h2 id="aporrito">5. Πολιτική Απορρήτου (GDPR)</h2>
  <p>Η προστασία των προσωπικών σας δεδομένων μάς είναι ουσιώδης. Η παρούσα πολιτική
  συντάσσεται σύμφωνα με τον Κανονισμό (ΕΕ) 2016/679 (GDPR) και τον Ν. 4624/2019.</p>
  <h3>5.1 Υπεύθυνος επεξεργασίας</h3>
  <p>Υπεύθυνος επεξεργασίας είναι η <b>Βασιλική Ανδρουτσοπούλου</b>,
  <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span> (διεύθυνση), email dravasi20@gmail.com,
  τηλέφωνο <span class="falta">ΣΥΜΠΛΗΡΩΣΤΕ</span>. Λόγω του μεγέθους και της φύσης της
  επεξεργασίας δεν απαιτείται ορισμός Υπευθύνου Προστασίας Δεδομένων (DPO).</p>
  <h3>5.2 Ποια δεδομένα συλλέγουμε και γιατί</h3>
  <p>Συλλέγουμε <b>μόνο τα απολύτως απαραίτητα</b> δεδομένα (αρχή της ελαχιστοποίησης,
  άρθρο 5 παρ. 1 στοιχ. γ' GDPR): ονοματεπώνυμο, διεύθυνση παράδοσης, τηλέφωνο, email
  (εφόσον το δώσετε) και τα στοιχεία της παραγγελίας σας. Σκοποί και νομικές βάσεις:</p>
  <ul>
    <li><b>Εκτέλεση της παραγγελίας και της αποστολής</b> — εκτέλεση σύμβασης (άρθρο 6 παρ. 1 στοιχ. β').</li>
    <li><b>Έκδοση παραστατικών και τήρηση φορολογικών αρχείων</b> — συμμόρφωση με έννομη υποχρέωση (άρθρο 6 παρ. 1 στοιχ. γ').</li>
    <li><b>Εξυπηρέτηση, απαντήσεις σε ερωτήματα, διαχείριση επιστροφών</b> — εκτέλεση σύμβασης και έννομο συμφέρον (άρθρο 6 παρ. 1 στοιχ. στ').</li>
  </ul>
  <p><b>Δεν συλλέγουμε δεδομένα υγείας</b> και σας παρακαλούμε να μην μας αποστέλλετε
  ιατρικές πληροφορίες. <b>Δεν απευθυνόμαστε σε ανηλίκους</b> κάτω των 18 ετών και δεν
  συλλέγουμε εν γνώσει μας δεδομένα τους. Δεν διενεργείται αυτοματοποιημένη λήψη
  αποφάσεων ούτε κατάρτιση προφίλ.</p>
  <h3>5.3 Αποδέκτες</h3>
  <p>Τα δεδομένα σας <b>δεν πωλούνται και δεν διαβιβάζονται σε τρίτους για διαφημιστικούς
  σκοπούς</b>. Κοινοποιούνται μόνο: (α) στη συνεργαζόμενη εταιρεία ταχυμεταφορών, στο
  μέτρο που απαιτείται για την παράδοση· (β) στον λογιστή μας και στις φορολογικές αρχές
  (Α.Α.Δ.Ε.), βάσει έννομης υποχρέωσης· (γ) στην τράπεζα, σε περίπτωση τραπεζικής
  κατάθεσης ή IRIS.</p>
  <h3>5.4 Παραγγελίες μέσω WhatsApp</h3>
  <p>Η ολοκλήρωση της παραγγελίας γίνεται μέσω <b>WhatsApp</b>, υπηρεσίας της Meta Platforms
  Ireland Ltd. Η συνομιλία σας αποθηκεύεται στη συσκευή σας και στη δική μας και διέπεται
  επιπλέον από τους όρους και την πολιτική απορρήτου της ίδιας της υπηρεσίας, για τις
  οποίες δεν φέρουμε ευθύνη. Εάν δεν επιθυμείτε τη χρήση WhatsApp, μπορείτε να μας
  στείλετε την παραγγελία σας με email ή τηλεφωνικά.</p>
  <h3>5.5 Cookies και τοπική αποθήκευση</h3>
  <p>Ο ιστότοπος <b>δεν χρησιμοποιεί cookies παρακολούθησης, διαφημιστικά cookies ή
  εργαλεία αναλυτικών στοιχείων</b> (π.χ. Google Analytics, Meta Pixel). Χρησιμοποιεί
  αποκλειστικά την <b>τοπική αποθήκευση (localStorage)</b> του προγράμματος περιήγησής σας,
  ώστε να θυμάται το καλάθι αγορών σας. Τα δεδομένα αυτά είναι αυστηρώς απαραίτητα για τη
  λειτουργία που ζητήσατε, <b>παραμένουν αποκλειστικά στη συσκευή σας, δεν αποστέλλονται
  ποτέ σε εμάς ή σε τρίτους</b> και δεν απαιτούν συγκατάθεση. Μπορείτε να τα διαγράψετε
  οποτεδήποτε καθαρίζοντας τα δεδομένα περιήγησης.</p>
  <h3>5.6 Χρόνος διατήρησης</h3>
  <p>Τα δεδομένα παραγγελίας διατηρούνται για όσο διάστημα απαιτεί η φορολογική νομοθεσία
  (κατ' ελάχιστον πέντε έτη) και τα δεδομένα επικοινωνίας για όσο χρόνο είναι αναγκαίο για
  την εξυπηρέτησή σας. Μετά την πάροδο των προθεσμιών, διαγράφονται με ασφάλεια.</p>
  <h3>5.7 Τα δικαιώματά σας</h3>
  <p>Έχετε δικαίωμα <b>πρόσβασης, διόρθωσης, διαγραφής («δικαίωμα στη λήθη»), περιορισμού
  της επεξεργασίας, φορητότητας και εναντίωσης</b>, καθώς και δικαίωμα ανάκλησης της
  συγκατάθεσής σας οποτεδήποτε, χωρίς να θίγεται η νομιμότητα της επεξεργασίας που
  προηγήθηκε. Υποβάλετε το αίτημά σας στο dravasi20@gmail.com· απαντούμε
  <b>εντός ενός (1) μηνός</b>, χωρίς χρέωση. Εάν θεωρείτε ότι παραβιάζονται τα δικαιώματά
  σας, μπορείτε να προσφύγετε στην <b>Αρχή Προστασίας Δεδομένων Προσωπικού Χαρακτήρα</b>
  (Κηφισίας 1-3, 115 23 Αθήνα, <a href="https://www.dpa.gr" target="_blank" rel="noopener">www.dpa.gr</a>).</p>

  <h2 id="oroi">6. Όροι Χρήσης</h2>
  <p>Η περιήγηση και η χρήση του παρόντος ιστοτόπου συνεπάγεται την ανεπιφύλακτη αποδοχή
  των παρόντων όρων. Εάν δεν συμφωνείτε, παρακαλούμε μην τον χρησιμοποιείτε.</p>
  <h3>6.1 Κατάρτιση της σύμβασης</h3>
  <p>Η παρουσίαση των προϊόντων συνιστά <b>πρόσκληση προς υποβολή προσφοράς</b>. Η
  παραγγελία που αποστέλλετε μέσω WhatsApp, email ή τηλεφώνου αποτελεί <b>πρόταση
  σύναψης σύμβασης</b> και η σύμβαση καταρτίζεται μόνο με τη <b>ρητή επιβεβαίωσή μας</b>
  ως προς τη διαθεσιμότητα, την τελική τιμή και τον χρόνο παράδοσης.</p>
  <h3>6.2 Τιμές και διαθεσιμότητα</h3>
  <p>Όλες οι τιμές είναι σε <b>ευρώ και περιλαμβάνουν Φ.Π.Α.</b> Διατηρούμε το δικαίωμα
  μεταβολής τιμών και προϊόντων χωρίς προειδοποίηση· ισχύει πάντοτε η τιμή που ίσχυε κατά
  τη στιγμή της επιβεβαίωσης της παραγγελίας. Καταβάλλεται κάθε προσπάθεια για την
  ακρίβεια των πληροφοριών, ωστόσο δεν ευθυνόμαστε για τυπογραφικά λάθη, τεχνικά σφάλματα
  ή προσωρινή έλλειψη αποθέματος· σε τέτοια περίπτωση ενημερώνεστε άμεσα και δικαιούστε
  ακύρωση με πλήρη επιστροφή χρημάτων.</p>
  <h3>6.3 Υποχρεώσεις χρήστη</h3>
  <p>Δηλώνετε ότι είστε <b>άνω των 18 ετών</b> και ότι τα στοιχεία που μας παρέχετε είναι
  αληθή και ακριβή. Απαγορεύεται κάθε χρήση του ιστοτόπου για παράνομο ή αθέμιτο σκοπό,
  καθώς και ενέργεια που θέτει σε κίνδυνο τη λειτουργία ή την ασφάλειά του.</p>
  <h3>6.4 Δικαιώματα πνευματικής ιδιοκτησίας</h3>
  <p>Το περιεχόμενο του ιστοτόπου προστατεύεται από τον Ν. 2121/1993. Τα σήματα, οι
  ονομασίες και οι εικόνες προϊόντων Herbalife Nutrition ανήκουν στους δικαιούχους τους.
  Απαγορεύεται η αναπαραγωγή ή εμπορική εκμετάλλευση χωρίς προηγούμενη γραπτή άδεια.</p>
  <h3>6.5 Περιορισμός ευθύνης</h3>
  <p>Ο ιστότοπος παρέχεται «ως έχει». Δεν εγγυόμαστε αδιάλειπτη ή απαλλαγμένη σφαλμάτων
  λειτουργία και δεν ευθυνόμαστε για ζημία από ανωτέρα βία, διακοπές δικτύου ή ενέργειες
  τρίτων (μεταφορικές εταιρείες, τράπεζες, πάροχοι υπηρεσιών ανταλλαγής μηνυμάτων).
  Ουδεμία διάταξη των παρόντων όρων περιορίζει τα αναγκαστικού δικαίου δικαιώματά σας ως
  καταναλωτή.</p>
  <h3>6.6 Εφαρμοστέο δίκαιο</h3>
  <p>Οι παρόντες όροι διέπονται από το <b>ελληνικό δίκαιο</b> και το δίκαιο της Ευρωπαϊκής
  Ένωσης. Για κάθε διαφορά αρμόδια είναι τα δικαστήρια της κατοικίας του καταναλωτή,
  με την επιφύλαξη της εξωδικαστικής επίλυσης της παραγράφου 4.5. Διατηρούμε το δικαίωμα
  τροποποίησης των όρων· η εκάστοτε ισχύουσα έκδοση δημοσιεύεται στην παρούσα σελίδα.</p>

  <h2 id="apopoiisi">7. Αποποίηση Ευθυνών</h2>
  <h3>7.1 Φύση των προϊόντων</h3>
  <p>Τα προϊόντα Herbalife Nutrition που διατίθενται μέσω του παρόντος ιστοτόπου είναι
  <b>συμπληρώματα διατροφής και τρόφιμα ειδικής διατροφής — δεν είναι φάρμακα</b>.
  <b>Δεν προορίζονται για τη διάγνωση, θεραπεία, ίαση ή πρόληψη οποιασδήποτε ασθένειας</b>
  και δεν υποκαθιστούν ισορροπημένη διατροφή, επαρκή ενυδάτωση και υγιεινό τρόπο ζωής.
  Καμία αναφορά του ιστοτόπου δεν πρέπει να ερμηνευθεί ως ισχυρισμός υγείας πέραν όσων
  επιτρέπει ο Κανονισμός (ΕΚ) 1924/2006.</p>
  <h3>7.2 Ατομική χρήση και ιατρική συμβουλή</h3>
  <p>Τα αποτελέσματα <b>διαφέρουν από άτομο σε άτομο</b> και εξαρτώνται από τη διατροφή, τη
  φυσική δραστηριότητα και τον τρόπο ζωής. Τυχόν μαρτυρίες πελατών είναι προσωπικές
  εμπειρίες και δεν αποτελούν εγγύηση αποτελέσματος. <b>Συμβουλευτείτε ιατρό ή
  φαρμακοποιό πριν από τη χρήση</b>, ιδίως εάν είστε έγκυος ή θηλάζετε, εάν λαμβάνετε
  φαρμακευτική αγωγή, εάν πάσχετε από χρόνια νόσο ή εάν έχετε γνωστές τροφικές αλλεργίες.
  Διαβάζετε πάντοτε την ετικέτα, μην υπερβαίνετε τη συνιστώμενη ημερήσια δόση και
  φυλάσσετε τα προϊόντα μακριά από παιδιά. Το περιεχόμενο του ιστοτόπου έχει
  <b>αποκλειστικά ενημερωτικό χαρακτήρα και δεν συνιστά ιατρική, διατροφική ή
  φαρμακευτική συμβουλή</b>.</p>
  <h3>7.3 Ανεξάρτητο Μέλος</h3>
  <p>Ο ιστότοπος λειτουργεί από <b>Ανεξάρτητο Μέλος Herbalife</b> και <b>δεν ανήκει στη
  Herbalife Nutrition Ltd</b> ούτε εκφράζει ή δεσμεύει αυτήν ή τις συνδεδεμένες με αυτήν
  εταιρείες. Οι απόψεις, οι όροι πώλησης και οι δεσμεύσεις που διατυπώνονται εδώ βαρύνουν
  αποκλειστικά το Ανεξάρτητο Μέλος. Τυχόν αναφορές σε επαγγελματική ευκαιρία
  <b>δεν αποτελούν υπόσχεση ή εγγύηση εισοδήματος</b>· τα αποτελέσματα εξαρτώνται από την
  προσωπική προσπάθεια και τις πωλήσεις κάθε Μέλους.</p>
</div>
"""
    return shell(t, "Νομικές Πληροφορίες | " + t["nombre"],
                 "Όροι χρήσης, πληρωμές, αποστολή, επιστροφές και πολιτική απορρήτου.",
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




def pagina_kratisi(data):
    """Pagina de servicios esteticos y reservas de cita."""
    t = data["tienda"]
    wa = t["telefono_whatsapp"]
    if "X" not in wa:
        msg = ("\u0393\u03b5\u03b9\u03b1 \u03c3\u03b1\u03c2! "
               "\u0398\u03ad\u03bb\u03c9 \u03bd\u03b1 \u03ba\u03bb\u03b5\u03af\u03c3\u03c9 "
               "\u03c1\u03b1\u03bd\u03c4\u03b5\u03b2\u03bf\u03cd.")
        btn_wa = (f'<a class="btn big" href="https://wa.me/{wa}'
                  f'?text={msg.replace(" ", "%20")}" target="_blank" rel="noopener">'
                  f'\u039a\u03bb\u03b5\u03af\u03c3\u03b5 \u03c1\u03b1\u03bd\u03c4\u03b5\u03b2\u03bf\u03cd '
                  f'\u03c3\u03c4\u03bf WhatsApp</a>')
    else:
        btn_wa = '<button class="btn big" disabled>WhatsApp \u03c3\u03cd\u03bd\u03c4\u03bf\u03bc\u03b1 \u03b4\u03b9\u03b1\u03b8\u03ad\u03c3\u03b9\u03bc\u03bf</button>'

    cuerpo = (
        '<div class="wrap" style="padding-bottom:70px">'
        '<div class="hero">'
        '<div class="big" style="font-size:26px">\u0391\u03b9\u03c3\u03b8\u03b7\u03c4\u03b9\u03ba\u03ad\u03c2 \u03a5\u03c0\u03b7\u03c1\u03b5\u03c3\u03af\u03b5\u03c2</div>'
        '<p>\u039c\u03b7 \u03c7\u03b5\u03b9\u03c1\u03bf\u03c5\u03c1\u03b3\u03b9\u03ba\u03ad\u03c2 \u03b1\u03b9\u03c3\u03b8\u03b7\u03c4\u03b9\u03ba\u03ad\u03c2 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b5\u03c2 \u03b1\u03c0\u03cc<br>'
        '<b>\u0392\u03b1\u03c3\u03b9\u03bb\u03b9\u03ba\u03ae \u0391\u03bd\u03b4\u03c1\u03bf\u03c5\u03c4\u03c3\u03bf\u03c0\u03bf\u03cd\u03bb\u03bf\u03c5 MD PhD</b>, '
        '\u03a0\u03bb\u03b1\u03c3\u03c4\u03b9\u03ba\u03cc\u03c2 &amp; \u0391\u03b9\u03c3\u03b8\u03b7\u03c4\u03b9\u03ba\u03cc\u03c2 \u03a7\u03b5\u03b9\u03c1\u03bf\u03c5\u03c1\u03b3\u03cc\u03c2.</p>'
        '</div>'

        '<div class="avisobox" style="background:#f0f5f0;border-color:var(--g2);color:#3a5c38">'
        '<b>\u03a0\u03ce\u03c2 \u03bb\u03b5\u03b9\u03c4\u03bf\u03c5\u03c1\u03b3\u03b5\u03af \u03b7 \u03ba\u03c1\u03ac\u03c4\u03b7\u03c3\u03b7:</b> '
        '\u039c\u03b1\u03c2 \u03b3\u03c1\u03ac\u03c6\u03b5\u03b9\u03c2, \u03c3\u03c5\u03bc\u03c6\u03c9\u03bd\u03bf\u03cd\u03bc\u03b5 \u03b7\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b1 \u03ba\u03b1\u03b9 \u03ce\u03c1\u03b1, '
        '\u03ba\u03b1\u03b9 \u03c3\u03b5 \u03b5\u03bd\u03b7\u03bc\u03b5\u03c1\u03ce\u03bd\u03bf\u03c5\u03bc\u03b5 \u03b3\u03b9\u03b1 \u03cc,\u03c4\u03b9 \u03c7\u03c1\u03b5\u03b9\u03ac\u03b6\u03b5\u03c4\u03b1\u03b9. '
        '\u0394\u03b5\u03bd \u03c0\u03bb\u03b7\u03c1\u03ce\u03bd\u03b5\u03b9\u03c2 \u03c4\u03af\u03c0\u03bf\u03c4\u03b1 online. '
        '\u0397 \u03c0\u03bb\u03b7\u03c1\u03c9\u03bc\u03ae \u03b3\u03af\u03bd\u03b5\u03c4\u03b1\u03b9 \u03ba\u03b1\u03c4\u03ac \u03c4\u03b7\u03bd \u03b5\u03c0\u03af\u03c3\u03ba\u03b5\u03c8\u03b7.'
        '</div>'

        '<h2 style="font-size:20px;margin:24px 0 12px;color:var(--g)">'
        '\u0394\u03b9\u03b1\u03b8\u03ad\u03c3\u03b9\u03bc\u03b5\u03c2 \u0398\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b5\u03c2</h2>'

        '<div class="kratisi-card">'
        '<span class="step-pill">\u0394\u03ad\u03c1\u03bc\u03b1</span>'
        '<h3>Botox &amp; \u039d\u03b5\u03c5\u03c1\u03bf\u03c4\u03bf\u03be\u03af\u03bd\u03b7</h3>'
        '<p>\u039c\u03b5\u03af\u03c9\u03c3\u03b7 \u03b4\u03c5\u03bd\u03b1\u03bc\u03b9\u03ba\u03ce\u03bd \u03c1\u03c5\u03c4\u03af\u03b4\u03c9\u03bd \u03c3\u03c4\u03bf \u03bc\u03ad\u03c4\u03c9\u03c0\u03bf, \u03b1\u03bd\u03ac\u03bc\u03b5\u03c3\u03b1 \u03c3\u03c4\u03b1 \u03c6\u03c1\u03cd\u03b4\u03b9\u03b1 '
        '\u03ba\u03b1\u03b9 \u03b3\u03cd\u03c1\u03c9 \u03b1\u03c0\u03cc \u03c4\u03b1 \u03bc\u03ac\u03c4\u03b9\u03b1. '
        '\u0391\u03c0\u03bf\u03c4\u03ad\u03bb\u03b5\u03c3\u03bc\u03b1 \u03c3\u03b5 5\u201310 \u03b7\u03bc\u03ad\u03c1\u03b5\u03c2, '
        '\u03b4\u03b9\u03ac\u03c1\u03ba\u03b5\u03b9\u03b1 3\u20136 \u03bc\u03ae\u03bd\u03b5\u03c2.</p>'
        '<p class="price-range">\u03a4\u03b9\u03bc\u03ae: \u03ba\u03b1\u03c4\u03cc\u03c0\u03b9\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7\u03c2</p>'
        '</div>'

        '<div class="kratisi-card">'
        '<span class="step-pill">\u0394\u03ad\u03c1\u03bc\u03b1</span>'
        '<h3>\u03a5\u03b1\u03bb\u03bf\u03c5\u03c1\u03bf\u03bd\u03b9\u03ba\u03ae \u03a0\u03bb\u03ae\u03c1\u03c9\u03c3\u03b7 (Fillers)</h3>'
        '<p>\u0391\u03bd\u03cc\u03c1\u03b8\u03c9\u03c3\u03b7 \u03bc\u03ae\u03bb\u03c9\u03bd, \u03c7\u03b5\u03af\u03bb\u03b7, \u03c1\u03c5\u03c4\u03af\u03b4\u03b5\u03c2 \u03bd\u03b1\u03b6\u03bf\u03bb\u03b1\u03b2\u03b9\u03b1\u03ba\u03ad\u03c2. '
        '\u03a6\u03c5\u03c3\u03b9\u03ba\u03cc \u03b1\u03c0\u03bf\u03c4\u03ad\u03bb\u03b5\u03c3\u03bc\u03b1, \u03b1\u03c0\u03bf\u03c1\u03c1\u03bf\u03c6\u03ae\u03c3\u03b9\u03bc\u03b1 \u03c5\u03bb\u03b9\u03ba\u03ac, '
        '\u03b4\u03b9\u03ac\u03c1\u03ba\u03b5\u03b9\u03b1 12\u201318 \u03bc\u03ae\u03bd\u03b5\u03c2.</p>'
        '<p class="price-range">\u03a4\u03b9\u03bc\u03ae: \u03ba\u03b1\u03c4\u03cc\u03c0\u03b9\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7\u03c2</p>'
        '</div>'

        '<div class="kratisi-card">'
        '<span class="step-pill">\u0391\u03bd\u03b1\u03b3\u03ad\u03bd\u03bd\u03b7\u03c3\u03b7</span>'
        '<h3>PRP \u2014 \u03a0\u03bb\u03ac\u03c3\u03bc\u03b1 \u03a0\u03bb\u03bf\u03cd\u03c3\u03b9\u03bf \u03c3\u03b5 \u0391\u03b9\u03bc\u03bf\u03c0\u03b5\u03c4\u03ac\u03bb\u03b9\u03b1</h3>'
        '<p>\u0391\u03be\u03b9\u03bf\u03c0\u03bf\u03af\u03b7\u03c3\u03b7 \u03b4\u03b9\u03ba\u03ce\u03bd \u03c3\u03bf\u03c5 \u03b1\u03c5\u03be\u03b7\u03c4\u03b9\u03ba\u03ce\u03bd \u03c0\u03b1\u03c1\u03b1\u03b3\u03cc\u03bd\u03c4\u03c9\u03bd \u03b3\u03b9\u03b1 \u03b1\u03bd\u03b1\u03bd\u03ad\u03c9\u03c3\u03b7 '
        '\u03b4\u03ad\u03c1\u03bc\u03b1\u03c4\u03bf\u03c2, \u03bc\u03b1\u03bb\u03bb\u03b9\u03ce\u03bd \u03ba\u03b1\u03b9 \u03bb\u03b1\u03b9\u03bc\u03bf\u03cd. \u03a6\u03c5\u03c3\u03b9\u03ba\u03ae \u03b1\u03bd\u03b1\u03b3\u03ad\u03bd\u03bd\u03b7\u03c3\u03b7 '
        '\u03c7\u03c9\u03c1\u03af\u03c2 \u03be\u03ad\u03bd\u03b5\u03c2 \u03bf\u03c5\u03c3\u03af\u03b5\u03c2.</p>'
        '<p class="price-range">\u03a4\u03b9\u03bc\u03ae: \u03ba\u03b1\u03c4\u03cc\u03c0\u03b9\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7\u03c2</p>'
        '</div>'

        '<div class="kratisi-card">'
        '<span class="step-pill">\u03a3\u03ce\u03bc\u03b1</span>'
        '<h3>Body Contouring &amp; \u039b\u03b9\u03c0\u03cc\u03bb\u03c5\u03c3\u03b7</h3>'
        '<p>\u039c\u03b7 \u03c7\u03b5\u03b9\u03c1\u03bf\u03c5\u03c1\u03b3\u03b9\u03ba\u03ae \u03b1\u03b4\u03c5\u03bd\u03b1\u03c4\u03b9\u03c3\u03c4\u03b9\u03ba\u03ae \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b1 \u03c3\u03b5 \u03c3\u03c4\u03bf\u03c7\u03b5\u03c5\u03bc\u03ad\u03bd\u03b5\u03c2 \u03c0\u03b5\u03c1\u03b9\u03bf\u03c7\u03ad\u03c2. '
        '\u03a3\u03c5\u03bd\u03b4\u03c5\u03ac\u03b6\u03b5\u03c4\u03b1\u03b9 \u03b9\u03b4\u03b1\u03bd\u03b9\u03ba\u03ac \u03bc\u03b5 \u03b4\u03b9\u03b1\u03c4\u03c1\u03bf\u03c6\u03b9\u03ba\u03cc \u03c0\u03c1\u03cc\u03b3\u03c1\u03b1\u03bc\u03bc\u03b1.</p>'
        '<p class="price-range">\u03a4\u03b9\u03bc\u03ae: \u03ba\u03b1\u03c4\u03cc\u03c0\u03b9\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7\u03c2</p>'
        '<p style="font-size:13px;color:var(--mut)">'
        '\u03a3\u03c5\u03bd\u03b4\u03c5\u03ac\u03b6\u03b5\u03c4\u03b1\u03b9 \u03bc\u03b5 \u03c4\u03b1 <a href="index.html" style="color:var(--g)">'
        '\u03c0\u03c1\u03bf\u03b3\u03c1\u03ac\u03bc\u03bc\u03b1\u03c4\u03b1 Herbalife</a>.</p>'
        '</div>'

        '<div class="kratisi-card">'
        '<span class="step-pill">\u0391\u03b9\u03c7\u03bc\u03ae</span>'
        '<h3>\u0395\u03be\u03c9\u03c3\u03ce\u03bc\u03b1\u03c4\u03b1 &amp; \u0392\u03b9\u03bf\u03b1\u03bd\u03b1\u03b3\u03ad\u03bd\u03bd\u03b7\u03c3\u03b7</h3>'
        '<p>\u0398\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b1 \u03b5\u03be\u03c9\u03c3\u03c9\u03bc\u03ac\u03c4\u03c9\u03bd \u03b3\u03b9\u03b1 \u03b2\u03b1\u03b8\u03b9\u03ac \u03b1\u03bd\u03b1\u03b3\u03ad\u03bd\u03bd\u03b7\u03c3\u03b7 \u03b4\u03ad\u03c1\u03bc\u03b1\u03c4\u03bf\u03c2. '
        '\u0399\u03b4\u03b1\u03bd\u03b9\u03ba\u03ae \u03b3\u03b9\u03b1 \u03c3\u03b7\u03bc\u03b5\u03af\u03b1 \u03b3\u03ae\u03c1\u03b1\u03bd\u03c3\u03b7\u03c2, '
        '\u03ba\u03b7\u03bb\u03af\u03b4\u03b5\u03c2, \u03b1\u03c0\u03ce\u03bb\u03b5\u03b9\u03b1 \u03c3\u03c6\u03c1\u03b9\u03b3\u03b7\u03bb\u03cc\u03c4\u03b7\u03c4\u03b1\u03c2.</p>'
        '<p class="price-range">\u03a4\u03b9\u03bc\u03ae: \u03ba\u03b1\u03c4\u03cc\u03c0\u03b9\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7\u03c2</p>'
        '</div>'

        f'<div style="text-align:center;margin:30px 0 10px">{btn_wa}</div>'

        '<div class="ficha" style="margin-top:16px">'
        '<h3 style="color:var(--g)">\u03a0\u03ce\u03c2 \u03ba\u03bb\u03b5\u03af\u03bd\u03c9 \u03c1\u03b1\u03bd\u03c4\u03b5\u03b2\u03bf\u03cd;</h3>'
        '<ol class="pasos">'
        '<li><b>\u0393\u03c1\u03ac\u03c8\u03b5 \u03bc\u03b1\u03c2</b>'
        '\u03a0\u03b5\u03c2 \u03bc\u03b1\u03c2 \u03c4\u03b7 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b1 \u03c0\u03bf\u03c5 \u03c3\u03b5 \u03b5\u03bd\u03b4\u03b9\u03b1\u03c6\u03ad\u03c1\u03b5\u03b9 \u03ba\u03b1\u03b9 \u03c4\u03b9 \u03b5\u03c1\u03c9\u03c4\u03ae\u03c3\u03b5\u03b9\u03c2 \u03ad\u03c7\u03b5\u03b9\u03c2.'
        '<small>\u0391\u03c0\u03b1\u03bd\u03c4\u03ac\u03bc\u03b5 \u03c4\u03bf \u03c3\u03c5\u03bd\u03c4\u03bf\u03bc\u03cc\u03c4\u03b5\u03c1\u03bf.</small></li>'
        '<li><b>\u0394\u03c9\u03c1\u03b5\u03ac\u03bd \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7</b>'
        '15 \u03bb\u03b5\u03c0\u03c4\u03ac \u03b3\u03b9\u03b1 \u03bd\u03b1 \u03b4\u03bf\u03cd\u03bc\u03b5 \u03b1\u03bd \u03b7 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03ba\u03b1\u03c4\u03ac\u03bb\u03bb\u03b7\u03bb\u03b7 \u03b3\u03b9\u03b1 \u03b5\u03c3\u03ad\u03bd\u03b1.'
        '<small>\u03a7\u03c9\u03c1\u03af\u03c2 \u03c7\u03c1\u03ad\u03c9\u03c3\u03b7 \u03ba\u03b1\u03b9 \u03c7\u03c9\u03c1\u03af\u03c2 \u03c5\u03c0\u03bf\u03c7\u03c1\u03ad\u03c9\u03c3\u03b7.</small></li>'
        '<li><b>\u0395\u03c0\u03b9\u03bb\u03ad\u03b3\u03bf\u03c5\u03bc\u03b5 \u03b7\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b1</b>'
        '\u0391\u03b8\u03ae\u03bd\u03b1 \u03ba\u03b1\u03b9 \u0392\u03b5\u03bd\u03b5\u03b6\u03bf\u03c5\u03ad\u03bb\u03b1.'
        '<small>\u03a4\u03bf \u03c1\u03b1\u03bd\u03c4\u03b5\u03b2\u03bf\u03cd \u03b5\u03c0\u03b9\u03b2\u03b5\u03b2\u03b1\u03b9\u03ce\u03bd\u03b5\u03c4\u03b1\u03b9 \u03bc\u03cc\u03bb\u03b9\u03c2 \u03c3\u03c5\u03bc\u03c6\u03c9\u03bd\u03ae\u03c3\u03bf\u03c5\u03bc\u03b5.</small></li>'
        '</ol></div>'

        '<div class="avisobox">'
        '<b>\u0399\u03b1\u03c4\u03c1\u03b9\u03ba\u03ae \u03a3\u03b7\u03bc\u03b5\u03af\u03c9\u03c3\u03b7.</b> '
        '\u039f\u03b9 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b5\u03c2 \u03b5\u03ba\u03c4\u03b5\u03bb\u03bf\u03cd\u03bd\u03c4\u03b1\u03b9 \u03b1\u03c0\u03bf\u03ba\u03bb\u03b5\u03b9\u03c3\u03c4\u03b9\u03ba\u03ac \u03b1\u03c0\u03cc \u03b9\u03b1\u03c4\u03c1\u03cc. '
        '\u03a4\u03b1 \u03b1\u03c0\u03bf\u03c4\u03b5\u03bb\u03ad\u03c3\u03bc\u03b1\u03c4\u03b1 \u03b4\u03b9\u03b1\u03c6\u03ad\u03c1\u03bf\u03c5\u03bd \u03b1\u03bd\u03ac \u03b1\u03c3\u03b8\u03b5\u03bd\u03ae. '
        '\u0391\u03c0\u03b1\u03b9\u03c4\u03b5\u03af\u03c4\u03b1\u03b9 \u03b1\u03be\u03b9\u03bf\u03bb\u03cc\u03b3\u03b7\u03c3\u03b7 \u03c0\u03c1\u03b9\u03bd \u03b1\u03c0\u03cc \u03ba\u03ac\u03b8\u03b5 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b1. '
        '\u0391\u03c5\u03c4\u03ae \u03b7 \u03c3\u03b5\u03bb\u03af\u03b4\u03b1 \u03b5\u03af\u03bd\u03b1\u03b9 \u03b5\u03bd\u03b7\u03bc\u03b5\u03c1\u03c9\u03c4\u03b9\u03ba\u03ae \u03ba\u03b1\u03b9 \u03b4\u03b5\u03bd \u03b1\u03c0\u03bf\u03c4\u03b5\u03bb\u03b5\u03af \u03b9\u03b1\u03c4\u03c1\u03b9\u03ba\u03ae \u03c3\u03c5\u03bc\u03b2\u03bf\u03c5\u03bb\u03ae.'
        '</div>'
        '</div>'
    )
    return shell(t, "\u039a\u03c1\u03b1\u03c4\u03ae\u03c3\u03b5\u03b9\u03c2 & \u0398\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b5\u03c2 | " + t["nombre"],
                 "\u0391\u03b9\u03c3\u03b8\u03b7\u03c4\u03b9\u03ba\u03ad\u03c2 \u03b8\u03b5\u03c1\u03b1\u03c0\u03b5\u03af\u03b5\u03c2 \u03b1\u03c0\u03cc \u03a0\u03bb\u03b1\u03c3\u03c4\u03b9\u03ba\u03cc \u03a7\u03b5\u03b9\u03c1\u03bf\u03c5\u03c1\u03b3\u03cc. Botox, fillers, PRP, body contouring.",
                 "kratisi", cuerpo)


def pagina_404(data):
    t = data["tienda"]
    cuerpo = """
<div class="wrap" style="text-align:center;padding:80px 20px 120px">
  <p style="font-size:96px;margin:0;line-height:1;color:var(--g)">404</p>
  <h2 style="margin:8px 0 12px">Η σελίδα δεν βρέθηκε</h2>
  <p style="max-width:420px;margin:0 auto 28px;color:#666">
    Η σελίδα που ζητήσατε δεν υπάρχει ή έχει μετακινηθεί.
    Χρησιμοποιήστε τον πλοηγό παραπάνω ή επιστρέψτε στον κατάλογο.
  </p>
  <a href="index.html" class="btn">← Πίσω στον κατάλογο</a>
</div>
"""
    return shell(t, "404 – Σελίδα δεν βρέθηκε | " + t["nombre"],
                 "Η σελίδα δεν βρέθηκε.",
                 "tienda", cuerpo)


def construir(data):
    t = data["tienda"]
    # el pie necesita saber que metodos de pago hay activos
    t["_pago"] = data.get("pago", {})
    t["_faq"]  = data.get("faq", [])
    SITE.mkdir(parents=True, exist_ok=True)

    tienda_html, n, con_foto = pagina_tienda(data)
    (SITE / "index.html").write_text(tienda_html, encoding="utf-8")
    (SITE / "kratisi.html").write_text(pagina_kratisi(data), encoding="utf-8")
    (SITE / "melos.html").write_text(pagina_melos(data), encoding="utf-8")
    (SITE / "eukairia.html").write_text(pagina_oportunidad(data), encoding="utf-8")
    (SITE / "faq.html").write_text(pagina_faq(data), encoding="utf-8")
    (SITE / "epikoinonia.html").write_text(pagina_contacto(data), encoding="utf-8")
    (SITE / "nomika.html").write_text(pagina_legal(data), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    import json as _j
    _mf = {"name": data["tienda"]["nombre"], "short_name": "Royal Wellness",
           "start_url": "./index.html", "scope": "./",
           "display": "standalone", "orientation": "portrait-primary",
           "background_color": "#f8f6f2", "theme_color": "#5a7356",
           "categories": ["shopping", "health", "lifestyle"],
           "lang": "el",
           "icons": [{"src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png",
                      "purpose": "any maskable"},
                     {"src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png",
                      "purpose": "any maskable"}]}
    (SITE / "manifest.json").write_text(_j.dumps(_mf, ensure_ascii=False, indent=2), encoding="utf-8")

    _base = ("https://" + t["dominio"] if t.get("cname_activo")
             else "https://neopram.github.io/royalwellness")

    # Mientras la tienda no este lista (precios sin verificar, telefono falso,
    # sin GEMI), se bloquea la indexacion.
    (SITE / "robots.txt").write_text(
        "User-agent: *\n"
        + ("Allow: /\n" if t.get("indexable") else "Disallow: /\n")
        + f"Sitemap: {_base}/sitemap.xml\n",
        encoding="utf-8")

    # 404 page (GitHub Pages serves this for missing routes)
    (SITE / "404.html").write_text(pagina_404(data), encoding="utf-8")

    # sitemap.xml (only useful once indexable, but generated always)
    _pages = ["index.html", "kratisi.html", "melos.html",
              "eukairia.html", "faq.html", "epikoinonia.html", "nomika.html"]
    _sm = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    _sm += [f'  <url><loc>{_base}/{p}</loc></url>' for p in _pages]
    _sm.append('</urlset>')
    (SITE / "sitemap.xml").write_text("\n".join(_sm) + "\n", encoding="utf-8")

    # Service worker for PWA offline support
    _sw_pages = [
        "./", "./index.html", "./kratisi.html", "./melos.html",
        "./eukairia.html", "./faq.html", "./epikoinonia.html",
        "./nomika.html", "./manifest.json"
    ]
    _sw_ver = datetime.now().strftime("%Y%m%d")
    _sw_cache = f"rw-{_sw_ver}"
    _sw_code = f"""const CACHE='{_sw_cache}';
const URLS={_j.dumps(_sw_pages)};
self.addEventListener('install',e=>{{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(URLS)));
  self.skipWaiting();
}});
self.addEventListener('activate',e=>{{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
}});
self.addEventListener('fetch',e=>{{
  if(e.request.method!=='GET')return;
  e.respondWith(caches.open(CACHE).then(cache=>{{
    return cache.match(e.request).then(hit=>{{
      const net=fetch(e.request).then(r=>{{if(r.status===200)cache.put(e.request,r.clone());return r;}}).catch(()=>hit);
      return hit||net;
    }});
  }}));
}});
"""
    (SITE / "sw.js").write_text(_sw_code, encoding="utf-8")

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
    print("  Paginas    -> index.html (" + str(n) + " productos), kratisi.html, melos.html, nomika.html")
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
