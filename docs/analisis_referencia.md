# Análisis de referencia del proyecto

Fecha: 2025-11-04

Este documento resume la arquitectura, dependencias, hallazgos y recomendaciones identificadas durante la revisión de código. No modifica el comportamiento del sistema y sirve como guía para próximas mejoras.

## Arquitectura y apps

- Proyecto: `myclase`
  - Configuración en `myclase/settings.py` y ruteo en `myclase/urls.py`.
- Apps propias:
  - `core`: landing/home, login simple, vincula a tienda; sin modelos.
  - `market`: catálogo de `Product`, carrito (`Cart`, `CartItem`), CRUD básico, integración Mercado Pago.
  - `market_ai`: integración con Google GenAI (Gemini) para sugerir precios, chat y recomendaciones por embeddings (`ProductEmbedding`). Señales post_save para mantener embeddings.
  - `perfil`: perfil de usuario (`Profile`) con avatar y bio, señales en el mismo `models.py` para autogenerar y guardar.
  - `presence`: middleware de auto-logout e indicador de usuarios en línea (`UserActivity`).
  - `simple_chat`: chat simple con polling y API JSON.
  - `quotes`: esqueleto sin lógica.

## Dependencias (requirements.txt) – observaciones clave

- Django==5.2.5 con sqlparse==0.4.2 (incompatible). Django ≥5.0 requiere sqlparse≥0.5.0. Riesgo: errores en arranque/migraciones.
- Duplicidad/conflicto de dotenv: `python-dotenv==1.1.1` (correcto) y `dotenv==0.9.9` (otro paquete distinto). Mantener solo `python-dotenv`.
- Librerías pesadas/ajenas al alcance actual (posible sobrecarga): `torch`, `torchvision`, `ultralytics`, `opencv-*`, `jax*`, `matplotlib`, `scipy`, `sounddevice`, `polars`, etc. Verificar uso real antes de desplegar.
- Base de datos: incluye `mysqlclient` y `psycopg2-binary`; settings usa MySQL. README menciona SQLite (y hay `db.sqlite3`), pero settings no contempla SQLite por defecto.
- Whitenoise está instalado pero no habilitado en middleware/STATICFILES; no hay configuración de `STATIC_ROOT`.
- Mercado Pago: se usa `mercadopago==2.3.0` (SDK) solo con Access Token. Falta PUBLIC_KEY para front.
- Paquetes Google AI: `google-genai==1.31.0` coincide con import `from google import genai`.

## Configuración (settings.py)

- SECRET_KEY/DEBUG/ALLOWED_HOSTS via .env. ALLOWED_HOSTS por defecto `*` (no recomendado en prod).
- INSTALLED_APPS: incluye Allauth y proveedor Google.
- Allauth:
  - `ACCOUNT_SIGNUP_FIELDS` se define dos veces; la segunda usa nombres con asterisco (`"email*"`) que no corresponden a Allauth.
  - `ACCOUNT_LOGIN_METHODS` no es un ajuste estándar (históricamente `ACCOUNT_AUTHENTICATION_METHOD`). Revisar docs de la versión instalada (65.11.0).
- MIDDLEWARE: incluye `presence` (auto-logout y last_seen) y `allauth.account.middleware.AccountMiddleware`.
- Templates: `context_processors` duplica `request` y agrega `csrf` explícito (no suele ser necesario); inofensivo pero ruidoso.
- DB: fija MySQL vía variables. Sin fallback a SQLite. `dj-database-url` está instalado pero no se utiliza.
- Static/Media: `STATIC_URL` definido, sin `STATIC_ROOT` ni Whitenoise. `MEDIA_URL`/`MEDIA_ROOT` OK.

## Ruteo (myclase/urls.py y apps)

- Raíz `/` apunta a `core.views.home`. Luego incluye `core.urls` y `presence.urls` también en raíz. En `core/urls.py` se incluye nuevamente `market.urls` en `""`, generando rutas duplicadas/solapadas (p. ej. endpoints de `market` accesibles en `/` y `/market/`).
- Allauth en `/accounts/`, perfiles en `/profiles/`, AI en `/ai/`, `market` en `/market/`.

## App core

- `home` arma listado de últimos 6 `Product`, la plantilla `core/templates/index.html` ya los muestra correctamente.
- `index.html` usa rutas correctas con template tags de Django.

## App market

- Modelos: `Product` (con `stock`, `image`, `active`), `Cart` y `CartItem`. OK.
- Vistas: listado, crear/editar/eliminar lógico (marca `active=False`). Carrito: `add_to_cart`, `view_cart`, y `create_preference_cart` (Mercado Pago) para checkout del carrito.
- Plantillas:
  - `cart.html` usa enlaces a `market:cart-increase`, `cart-decrease`, `cart-remove` que NO existen en `urls.py` ni `views.py`.
  - `cart.html` requiere variable `PUBLIC_KEY` para Mercado Pago (no se pasa desde la vista ni existe en settings).
  - Filtros por categoría y orden de precio en `product_list.html`: OK.
- URLs: no hay `product-detail`, pero AI lo referencia en recomendaciones. Agregar detalla o ajustar links.

## App market_ai

- Cliente Gemini (`gemini_client.py`): usa `google.genai` con API Key desde `GEMINI_API_KEY` o `GOOGLE_API_KEY`. `generate_text` y `embed_text` con manejo básico de errores.
- Modelos: `ProductEmbedding` en relación 1-1 con `market.Product` y `vector` en `JSONField`.
- Señales: `post_save` de `Product` calcula/actualiza embeddings; puede ser costoso en requests web.
- Vistas:
  - `price_suggest`: prompt claro; devuelve texto completo.
  - `ai_chat`: historial en sesión con "limpiar chat".
  - `recommend_similar`: calcula similitud coseno con NumPy. Renderiza `market_ai/recommendations.html`.
- Plantillas:
  - Existe `market_ai/templates/recommentations.html` (typo). La vista espera `market_ai/recommendations.html`. Provocará TemplateDoesNotExist.
  - Enlace a `market:product-detail` no existe.

## App perfil

- `Profile` OneToOne con `User`. Señales en `models.py` crean/guardan perfil al crear usuario. Vistas para ver y editar perfil; template correcto.

## App presence

- `AutoLogoutMiddleware`: cierra sesión tras 30 minutos de inactividad (1800s) según timestamp en sesión; redirige a `presence:session_expired`.
- `UpdateLastSeenMiddleware`: actualiza/crea `UserActivity` por request autenticado. Vista `online_users` calcula activos en 5 minutos.

## App simple_chat

- Chat con polling cada 3s, endpoints JSON (`messages_api`, `post_message_api`). `post_message_api` permite anónimos; opcional endurecer.

## App quotes

- Vacía por ahora.

## Hallazgos y riesgos (prioridad)

1) Incompatibilidades de dependencias
- Django 5.2.5 + sqlparse 0.4.2 (mínimo requerido ≈0.5.0). Bloqueante.
- Dos paquetes dotenv instalados; puede romper import (`from dotenv import load_dotenv`).

2) Carrito y pagos (Mercado Pago)
- Falta `PUBLIC_KEY` en settings/.env y en contexto de `cart.html`.
- No existen endpoints `cart-increase`, `cart-decrease`, `cart-remove` usados en plantilla.

3) IA recomendaciones/plantillas
- Nombre de plantilla mal escrito: `recommentations.html` vs `recommendations.html`.
- Link a `market:product-detail` no existe.

4) Allauth configuración
- `ACCOUNT_SIGNUP_FIELDS` duplicado y con nombres inválidos (con `*`).
- `ACCOUNT_LOGIN_METHODS` no estándar para la versión indicada.

5) Ruteo duplicado/solapado
- `core/urls.py` incluye `market.urls` en `""` además de `myclase/urls.py` en `/market/`, generando rutas duplicadas/confusas.

6) Base de datos
- Settings fuerzan MySQL por .env; si no está configurado, el proyecto no arranca a pesar de tener `db.sqlite3`. Considerar fallback o usar `dj-database-url`.

7) Estáticos/Deploy
- Whitenoise no usado; falta `STATIC_ROOT` y posible configuración para producción.

8) Menores
- Duplicación de `request` en `context_processors`.
- `index.html` ya muestra correctamente los productos.
- Enlaces y rutas corregidos en plantillas.

9) Pruebas
- `tests.py` vacíos en todas las apps. No hay cobertura automatizada.

## Recomendaciones de acción

Corto plazo (alta prioridad):
- Ajustar requirements:
  - Actualizar `sqlparse>=0.5.0`.
  - Eliminar `dotenv` (mantener solo `python-dotenv`).
  - Remover/aislar libs pesadas si no se usan.
- Mercado Pago:
  - Agregar `MERCADOPAGO_PUBLIC_KEY` en `.env`/settings y pasarlo al contexto de `view_cart`.
  - Implementar endpoints `cart-increase`, `cart-decrease`, `cart-remove` o quitar los enlaces.
- market_ai:
  - Renombrar plantilla a `market_ai/templates/recommendations.html` o corregir la ruta en la vista.
  - Cambiar link a un detalle existente (o crear `product_detail`).
- Allauth:
  - Reemplazar `ACCOUNT_LOGIN_METHODS` por `ACCOUNT_AUTHENTICATION_METHOD = "username_email"` (según docs v65).
  - Dejar un solo `ACCOUNT_SIGNUP_FIELDS` sin asteriscos, p. ej. `["username", "email", "password1", "password2"]`.
- Ruteo:
  - Eliminar el include de `market.urls` desde `core/urls.py` para evitar duplicidad.

Medio plazo:
- DB:
  - Soportar `DATABASE_URL` con `dj-database-url` y fallback a SQLite en desarrollo.
- Static/Deploy:
  - Añadir Whitenoise en `MIDDLEWARE`, `STATIC_ROOT`, y `STATICFILES_DIRS` si aplica.
- IA:
  - Mover cálculo de embeddings a tarea async (Celery/RQ) o señal encolada para evitar latencia en requests.
  - Añadir variable `.env` `GEMINI_API_KEY` documentada en README.
- UX/UI:
  - Ya corregido: `index.html` usa correctamente los productos y template tags.
- Seguridad:
  - Endurecer `ALLOWED_HOSTS` y `DEBUG=False` en prod.
  - Restringir `post_message_api` a usuarios autenticados si se requiere.

Pruebas mínimas sugeridas:
- Crear tests para: creación de producto, agregar al carrito y cálculo de total, vistas de listado, y endpoints de chat.

## Datos de entorno sugeridos (.env)

- SECRET_KEY=...
- DEBUG=True
- ALLOWED_HOSTS=127.0.0.1,localhost
- DATABASE_URL=mysql://user:pass@localhost:3306/dbname (o variables separadas actuales)
- MERCADOPAGO_ACCESS_TOKEN=...
- MERCADOPAGO_PUBLIC_KEY=...
- GEMINI_API_KEY=...
- GOOGLE_CLIENT_ID=...
- GOOGLE_CLIENT_SECRET=...

## Glosario de rutas clave

- `/` → `core.home`
- `/market/` → listado y CRUD de productos
- `/profiles/ver_perfil/` → perfil de usuario
- `/ai/chat/` y `/ai/price-suggest/` → IA
- `/presence/online/` → usuarios activos; `/presence/session-expired/` → aviso de sesión expirada
- `/accounts/` → Allauth (login/signup)

---

Si querés, puedo preparar PRs/commits puntuales con cada corrección (sin tocar nada más) y tests mínimos para validar. Marca cuáles querés priorizar y los implemento.