#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Royal Wellness - generador de la tienda.

Lee  catalogo/productos.json  ->  escribe  docs/index.html  +  ops/inventario.csv

Uso:
    python scripts/build.py

Nunca edites docs/index.html a mano: este script lo sobrescribe.
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


def cargar():
    with open(CATALOGO, encoding="utf-8") as f:
        return json.load(f)


def validar(data):
    """Devuelve (errores, avisos). Los errores bloquean el build."""
    errores, avisos = [], []
    t = data["tienda"]

    if "X" in t["telefono_whatsapp"]:
        avisos.append("telefono_whatsapp sigue siendo un placeholder -> el boton de pedido no funcionara")
    if t["gemi"] == "PENDIENTE":
        avisos.append("GEMI sin rellenar -> obligatorio por ley griega en el pie de un e-shop")
    if t.get("cname_activo"):
        avisos.append("cname_activo=true -> la web solo respondera en " + t["dominio"] +
                      ". Asegurate de que el DNS ya resuelve, si no quedara inaccesible")

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
            avisos.append(p["sku"] + ": precio sin verificar contra la lista oficial de Herbalife Grecia")
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


def tarjeta(p, sim, modo_catalogo=False, img=None):
    # En modo catalogo se ignora el stock: todo se muestra disponible porque los
    # pedidos se encargan a Herbalife por cliente, no salen de un almacen propio.
    agotado = (not modo_catalogo) and p["stock"] <= 0
    nombre = html.escape(p["nombre_el"])
    desc = html.escape(p.get("descripcion_el", ""))
    precio = f'{p["precio"]:.2f}'.replace(".", ",")
    boton = (
        '<button class="btn" disabled>Εξαντλήθηκε</button>'
        if agotado else
        f'<button class="btn" onclick="add(\'{p["sku"]}\')">Προσθήκη</button>'
    )
    badge = '<span class="badge">Εξαντλήθηκε</span>' if agotado else ""
    if img:
        media = (f'<div class="ph has-img">{badge}'
                 f'<img src="{img}" alt="{nombre}" loading="lazy"></div>')
    else:
        media = f'<div class="ph">{badge}<span class="ph-t">{nombre[:2]}</span></div>'
    return f"""      <article class="card{' out' if agotado else ''}" data-cat="{p['categoria']}">
        {media}
        <h3>{nombre}</h3>
        <p class="desc">{desc}</p>
        <div class="row"><span class="price">{precio} {sim}</span>{boton}</div>
      </article>"""


def construir(data):
    t = data["tienda"]
    sim = t["simbolo"]
    activos = [p for p in data["productos"] if p.get("activo")]
    cats = [c for c in data["categorias"] if any(p["categoria"] == c["id"] for p in activos)]

    chips = '<button class="chip on" onclick="filt(this,\'all\')">Όλα</button>' + "".join(
        f'<button class="chip" onclick="filt(this,\'{c["id"]}\')">{html.escape(c["nombre_el"])}</button>'
        for c in cats
    )
    fotos = {p["sku"]: buscar_imagen(p) for p in activos}
    cards = "\n".join(
        tarjeta(p, sim, t.get("modo_catalogo", False), fotos[p["sku"]])
        for p in activos
    )
    con_foto = sum(1 for v in fotos.values() if v)

    precios = {p["sku"]: {"n": p["nombre_el"], "p": p["precio"]} for p in activos}
    sello = datetime.now().strftime("%d/%m/%Y %H:%M")

    tpl = PLANTILLA
    for k, v in {
        "__NOMBRE__": html.escape(t["nombre"]),
        "__CONSULTORA__": html.escape(t["consultora"]),
        "__EMAIL__": html.escape(t["email"]),
        "__WA__": t["telefono_whatsapp"],
        "__GEMI__": html.escape(str(t["gemi"])),
        "__SIM__": sim,
        "__ENVIO__": f'{t["envio_coste"]:.2f}',
        "__GRATIS__": f'{t["envio_gratis_desde"]:.2f}',
        "__CHIPS__": chips,
        "__CARDS__": cards,
        "__PRECIOS__": json.dumps(precios, ensure_ascii=False),
        "__SELLO__": sello,
        "__ANIO__": str(datetime.now().year),
        "__NOINDEX__": ("" if t.get("indexable")
                        else '\n<meta name="robots" content="noindex,nofollow">'),
    }.items():
        tpl = tpl.replace(k, v)

    SITE.mkdir(parents=True, exist_ok=True)
    ruta = SITE / "index.html"
    ruta.write_text(tpl, encoding="utf-8")

    # .nojekyll evita que Jekyll se coma carpetas que empiezan por guion bajo.
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    # CNAME ata el dominio propio, PERO solo cuando el DNS ya existe. Si se
    # activa antes, GitHub redirige <usuario>.github.io -> shop.royalwellness.gr,
    # que todavia no resuelve, y la tienda queda inaccesible para todos.
    # Por eso arranca desactivado: ver cname_activo en productos.json.
    # Mientras la tienda no este lista (precios sin verificar, telefono falso,
    # sin GEMI), se bloquea la indexacion. Asi Google no ensena al mundo una
    # tienda a medias ni la mezcla con la web principal en los resultados.
    if t.get("indexable"):
        (SITE / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n", encoding="utf-8")
    else:
        (SITE / "robots.txt").write_text(
            "User-agent: *\nDisallow: /\n", encoding="utf-8")

    cname = SITE / "CNAME"
    if t.get("cname_activo"):
        cname.write_text(t["dominio"] + "\n", encoding="utf-8")
    elif cname.exists():
        cname.unlink()

    return ruta, len(activos), con_foto


PLANTILLA = r"""<!doctype html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__NOMBRE__ | Herbalife Nutrition</title>
<meta name="description" content="Προϊόντα Herbalife Nutrition με προσωπική υποστήριξη. Αποστολή σε όλη την Ελλάδα.">__NOINDEX__
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--g:#0b7d3b;--g2:#12a34f;--ink:#14201a;--mut:#5f6f66;--bg:#f6f8f6;--card:#fff;--line:#e3e9e4}
@media(prefers-color-scheme:dark){:root{--ink:#e9f1ec;--mut:#9fb0a6;--bg:#0f1512;--card:#18211c;--line:#27332c}}
body{font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:linear-gradient(135deg,var(--g),var(--g2));color:#fff;padding:28px 18px 34px;text-align:center}
header h1{font-size:26px;letter-spacing:.3px}
header p{opacity:.92;font-size:14px;margin-top:6px}
.wrap{max-width:1040px;margin:0 auto;padding:18px}
.chips{display:flex;gap:8px;overflow-x:auto;padding:16px 0 6px;-webkit-overflow-scrolling:touch}
.chip{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:8px 15px;border-radius:999px;font-size:14px;cursor:pointer}
.chip.on{background:var(--g);border-color:var(--g);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;padding:10px 0 90px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;display:flex;flex-direction:column}
.card.out{opacity:.55}
.ph{position:relative;height:120px;border-radius:10px;background:linear-gradient(135deg,#d9efe1,#b7e2c8);display:grid;place-items:center;margin-bottom:10px}
.ph-t{font-size:34px;font-weight:800;color:var(--g);opacity:.5}
.ph.has-img{background:#fff;overflow:hidden}
.ph.has-img img{width:100%;height:100%;object-fit:contain;display:block}
.badge{position:absolute;top:8px;left:8px;background:#b3261e;color:#fff;font-size:11px;padding:3px 8px;border-radius:6px}
.card h3{font-size:15px;line-height:1.35;margin-bottom:5px}
.desc{font-size:13px;color:var(--mut);flex:1;margin-bottom:10px}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px}
.price{font-weight:800;color:var(--g);font-size:17px}
.btn{background:var(--g);color:#fff;border:0;border-radius:9px;padding:9px 14px;font-size:14px;font-weight:600;cursor:pointer}
.btn:disabled{background:#98a79e;cursor:not-allowed}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:11px 16px;display:none;align-items:center;justify-content:space-between;gap:12px;box-shadow:0 -6px 20px rgba(0,0,0,.10)}
.bar.on{display:flex}
.bar .t{font-size:14px}
.bar .t b{display:block;font-size:17px;color:var(--g)}
dialog{border:0;border-radius:16px;padding:0;max-width:440px;width:92%;background:var(--card);color:var(--ink)}
dialog::backdrop{background:rgba(0,0,0,.5)}
.dh{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
.dh h2{font-size:17px}
.x{border:0;background:none;font-size:24px;line-height:1;cursor:pointer;color:var(--mut)}
.items{padding:8px 18px;max-height:46vh;overflow:auto}
.it{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px}
.it .nm{flex:1}
.qty{display:flex;align-items:center;gap:7px}
.qty button{width:27px;height:27px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:7px;cursor:pointer;font-size:15px}
.tot{padding:14px 18px;border-top:1px solid var(--line);font-size:14px}
.tot div{display:flex;justify-content:space-between;margin-bottom:6px}
.tot .g{font-size:19px;font-weight:800;color:var(--g)}
.send{display:block;width:calc(100% - 36px);margin:0 18px 18px;background:#25D366;color:#fff;text-align:center;padding:13px;border-radius:11px;font-weight:700;text-decoration:none}
footer{background:var(--card);border-top:1px solid var(--line);padding:26px 18px 110px;text-align:center;font-size:12px;color:var(--mut)}
footer a{color:var(--g)}
.legal{max-width:640px;margin:12px auto 0;line-height:1.7}
</style>
</head>
<body>

<header>
  <h1>__NOMBRE__</h1>
  <p>Herbalife Nutrition · __CONSULTORA__</p>
  <p>Αποστολή σε όλη την Ελλάδα · Δωρεάν άνω των __GRATIS__ __SIM__</p>
</header>

<div class="wrap">
  <div class="chips">__CHIPS__</div>
  <div class="grid" id="grid">
__CARDS__
  </div>
</div>

<div class="bar" id="bar">
  <div class="t"><span id="n">0 προϊόντα</span><b id="s">0,00 __SIM__</b></div>
  <button class="btn" onclick="dlg.showModal();render()">Παραγγελία</button>
</div>

<dialog id="dlg">
  <div class="dh"><h2>Η παραγγελία σου</h2><button class="x" onclick="dlg.close()">&times;</button></div>
  <div class="items" id="items"></div>
  <div class="tot">
    <div><span>Υποσύνολο</span><span id="sub">0,00 __SIM__</span></div>
    <div><span>Μεταφορικά</span><span id="shp">0,00 __SIM__</span></div>
    <div><span>Σύνολο</span><span class="g" id="grd">0,00 __SIM__</span></div>
  </div>
  <a class="send" id="wa" href="#" target="_blank" rel="noopener">Αποστολή στο WhatsApp</a>
</dialog>

<footer>
  <p><b>__NOMBRE__</b> · Ανεξάρτητο Μέλος Herbalife</p>
  <p>__EMAIL__ · ΓΕΜΗ: __GEMI__</p>
  <div class="legal">
    <p>Τα προϊόντα Herbalife Nutrition δεν είναι φάρμακα και δεν προορίζονται για τη διάγνωση, θεραπεία ή πρόληψη ασθενειών.
    Τα αποτελέσματα διαφέρουν ανά άτομο. Συμβουλευτείτε τον γιατρό σας πριν από οποιοδήποτε πρόγραμμα διατροφής.</p>
    <p>Δικαίωμα υπαναχώρησης 14 ημερών (Ν. 2251/1994). Πλατφόρμα ΗΕΔ: <a href="https://ec.europa.eu/consumers/odr" target="_blank" rel="noopener">ec.europa.eu/consumers/odr</a></p>
  </div>
  <p style="margin-top:14px;opacity:.6">&copy; __ANIO__ · Ενημερώθηκε __SELLO__</p>
</footer>

<script>
var P = __PRECIOS__;
var SHIP = __ENVIO__, FREE = __GRATIS__, SIM = "__SIM__", WA = "__WA__";
var cart = {};
try { cart = JSON.parse(localStorage.getItem("rw_cart") || "{}"); } catch(e) { cart = {}; }
var dlg = document.getElementById("dlg");

function eur(n){ return n.toFixed(2).replace(".", ",") + " " + SIM; }
function save(){ try{ localStorage.setItem("rw_cart", JSON.stringify(cart)); }catch(e){} }
function count(){ var c=0; for(var k in cart) c+=cart[k]; return c; }
function sub(){ var s=0; for(var k in cart) s += P[k].p * cart[k]; return s; }
function ship(){ var s=sub(); return (s<=0 || s>=FREE) ? 0 : SHIP; }

function add(sku){ cart[sku]=(cart[sku]||0)+1; save(); bar(); }
function chg(sku,d){ cart[sku]=(cart[sku]||0)+d; if(cart[sku]<=0) delete cart[sku]; save(); bar(); render(); }

function bar(){
  var b=document.getElementById("bar"), c=count();
  b.classList.toggle("on", c>0);
  document.getElementById("n").textContent = c + (c===1 ? " προϊόν" : " προϊόντα");
  document.getElementById("s").textContent = eur(sub()+ship());
}

function render(){
  var box=document.getElementById("items"), h="";
  for(var k in cart){
    h += '<div class="it"><span class="nm">'+P[k].n+'</span>'
       + '<div class="qty"><button onclick="chg(\''+k+'\',-1)">-</button>'
       + '<span>'+cart[k]+'</span>'
       + '<button onclick="chg(\''+k+'\',1)">+</button></div>'
       + '<span>'+eur(P[k].p*cart[k])+'</span></div>';
  }
  box.innerHTML = h || '<p style="padding:18px 0;color:var(--mut)">Το καλάθι είναι άδειο.</p>';
  document.getElementById("sub").textContent = eur(sub());
  document.getElementById("shp").textContent = ship()===0 ? "Δωρεάν" : eur(ship());
  document.getElementById("grd").textContent = eur(sub()+ship());

  var t = "Γεια σας! Θέλω να παραγγείλω:\n";
  for(var k in cart) t += "• " + cart[k] + "x " + P[k].n + " - " + eur(P[k].p*cart[k]) + "\n";
  t += "\nΜεταφορικά: " + (ship()===0 ? "Δωρεάν" : eur(ship()));
  t += "\nΣΥΝΟΛΟ: " + eur(sub()+ship());
  t += "\n\nΟνοματεπώνυμο:\nΔιεύθυνση:\nΤηλέφωνο:";
  document.getElementById("wa").href = "https://wa.me/" + WA + "?text=" + encodeURIComponent(t);
}

function filt(btn, cat){
  var cs=document.querySelectorAll(".chip");
  for(var i=0;i<cs.length;i++) cs[i].classList.remove("on");
  btn.classList.add("on");
  var cards=document.querySelectorAll(".card");
  for(var j=0;j<cards.length;j++){
    cards[j].style.display = (cat==="all" || cards[j].dataset.cat===cat) ? "" : "none";
  }
}

for(var k in cart){ if(!P[k]) delete cart[k]; }
save(); bar();
</script>
</body>
</html>
"""


def main():
    # --out DIR : escribe en otra carpeta (necesario si Windows "Controlled Folder
    # Access" bloquea a python.exe en Escritorio/Documentos. Ver docs/ENTORNO.md)
    global SITE, OPS
    if "--out" in sys.argv:
        base = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
        SITE = base / "docs"
        OPS = base / "ops"
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
    print("  Web        -> " + corto(ruta) + "  (" + str(n) + " productos)")
    print("  Inventario -> " + corto(inv))
    print("  Fotos      -> " + str(con_foto) + " de " + str(n) +
          " productos con foto en docs/assets/" +
          ("" if con_foto == n else "  <- faltan " + str(n - con_foto)))
    if errores:
        print("")
        print("  NO PUBLICAR todavia: " + str(len(errores)) + " error(es) arriba.")
        return 1
    print("")
    print("  Listo para publicar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
