# Chatbot IA — Cloudflare Worker (0 €/mes)

Fallback del chatbot: si el FAQ no encuentra respuesta por palabras clave,
esta función llama a Gemini (tier gratuito) y responde. El FAQ sigue siendo
la primera respuesta — esto solo cubre lo que el FAQ no cubre.

**Nunca da consejo médico** — el system prompt lo prohíbe explícitamente y
redirige a consulta. Esto es importante: `royalwellness.gr` es la web de una
cirujana en ejercicio; ver `guia/` sobre el riesgo deontológico ya detectado.

## Coste: 0 €/mes, siempre que

- Cloudflare Workers free tier: 100.000 peticiones/día (de sobra para una tienda).
- Cloudflare KV free tier: 100.000 lecturas/día, 1.000 escrituras/día (el rate
  limit hace 1 lectura + 1 escritura por pregunta → soporta ~1.000 preguntas/día).
- Google AI Studio (Gemini) free tier: límite por minuto y por día, suficiente
  para un chatbot de tienda. Si algún día se agota, Gemini devuelve error y el
  widget cae automáticamente al enlace de WhatsApp (no se rompe nada).

## Pasos para desplegar (~10 minutos, tú los haces — necesitas iniciar sesión)

### 1. Consigue una API key gratis de Gemini
1. Ve a **https://aistudio.google.com/apikey**
2. Inicia sesión con tu cuenta de Google (dravasi20@gmail.com o la que prefieras)
3. "Create API key" → copia la clave (empieza por `AIza...`)

### 2. Crea una cuenta gratis de Cloudflare
1. Ve a **https://dash.cloudflare.com/sign-up** (gratis, no pide tarjeta)
2. Verifica tu email

### 3. Instala Wrangler (CLI de Cloudflare) y despliega
Abre una terminal en esta carpeta (`worker/`) y ejecuta:

```bash
npm install -g wrangler
wrangler login          # abre el navegador, inicia sesión con tu cuenta Cloudflare
wrangler kv namespace create RATE_LIMIT
```

El último comando imprime algo como:
```
{ binding = "RATE_LIMIT", id = "abcd1234..." }
```
Copia ese `id` y pégalo en `wrangler.toml`, sustituyendo `PEGAR_AQUI_EL_ID_DEL_KV_NAMESPACE`.

Luego:
```bash
wrangler secret put GEMINI_API_KEY
```
Te pedirá pegar la clave de Gemini del paso 1 (no se guarda en ningún archivo,
solo en Cloudflare, cifrada).

Finalmente:
```bash
wrangler deploy
```

Esto imprime una URL parecida a:
```
https://royalwellness-chatbot.TU-USUARIO.workers.dev
```

### 4. Conecta la URL al catálogo
Copia esa URL y pégala en `catalogo/productos.json`, campo `tienda.chat_ai_url`.
Luego:
```bash
bash actualizar.sh --publicar
```

Y el chatbot ya usa IA como fallback.

## Verificar que funciona

Pregunta al chatbot algo que el FAQ NO cubra (ej. "¿Tenéis descuento para
compras grandes?"). Debería tardar 1-2 segundos y responder con IA en vez de
mostrar el enlace de WhatsApp directamente.

## Apagar el fallback de IA

Deja `chat_ai_url` vacío (`""`) en `productos.json` y reconstruye — el chatbot
vuelve a comportarse igual que antes (solo FAQ + WhatsApp), sin tocar el Worker.
