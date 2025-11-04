# Marketplace Local Colaborativo

![Django](https://img.shields.io/badge/Django-5.2.7-green)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![Database](https://img.shields.io/badge/Database-SQLite3-orange)

## 📌 Descripción

**Marketplace Local Colaborativo** es una plataforma tipo Wallapop o MercadoLibre "de barrio", enfocada en facilitar la compra, venta e intercambio de productos dentro de una comunidad local sin comisiones altas.

### Problema real
Mucha gente quiere vender o intercambiar cosas en su comunidad sin pagar comisiones altas a plataformas grandes.

### Solución
Marketplace simple y funcional con publicación de productos, chat en tiempo real, gestión de usuarios y pagos digitales integrados.

### Innovación
- **Foco en intercambio** además de compra/venta tradicional
- **Integración con pagos digitales** (MercadoPago)
- **Chat interno** entre usuarios para negociación directa

---

## ⚙️ Tecnologías utilizadas

- **Backend:** Django 5.2.7, Python 3.10
- **Base de datos:** SQLite3 (desarrollo y producción ligera)
- **Autenticación:** Django Allauth (login social con Google)
- **Pagos:** MercadoPago SDK
- **Frontend:** HTML, CSS retro personalizado

---

## 💡 Funcionalidades principales

- **Registro e inicio de sesión** con autenticación social (Google)
- **Gestión de productos**: crear, editar, eliminar y listar con filtros por categoría y precio
- **Carrito de compras** con gestión de cantidades y checkout integrado con MercadoPago
- **Chat interno** entre usuarios para coordinar ventas/intercambios
- **Perfiles de usuario** con avatar y biografía personalizados
- **Presencia en línea** y auto-logout por inactividad
