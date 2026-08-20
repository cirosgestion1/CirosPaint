# Ciros Paint - Project Status

Última actualización: **20/08/2026**

## Estado actual

Versión más reciente validada: **Ciros Paint 0.10.6**

Rama de verificación: `build/verify-0.10.6`

PR principal de integración: **#25 - Verify Ciros Paint 0.10.6 functional Gemini assistant**

La familia 0.10 amplía la base consolidada de 0.9 con análisis de pinturas en Favoritos y la introducción progresiva de Ciros Assistant.

## Validación automática final de 0.10.6

GitHub Actions run: `32382923636` (#205)

Resultado: **SUCCESS**

Validado:

- reconstrucción completa desde la fuente histórica hasta 0.10.6;
- instalación del SDK oficial `google-genai`;
- disponibilidad de Interactions API;
- catálogos y assets;
- **113 tests**, todos OK;
- smoke test funcional del asistente, OK;
- build PyInstaller Windows, OK;
- subida del artefacto, OK.

Entorno de CI validado:

- Windows Server 2025;
- Python 3.12.10;
- PyInstaller 6.22.2;
- PySide6 6.11.2;
- SQLAlchemy 2.0.52;
- `google-genai` 2.19.0.

## Build 0.10.6

Artefacto: `CirosPaint-Windows-0.10.6`

Artifact ID: `9411981601`

Ejecutable: `CirosPaint_0.10.6.exe`

Tamaño EXE: `244346433` bytes

SHA-256 EXE:

`58c3ae2560c9afeda18dc4a9c49466ebfe8c9abf14f80b4f81d75d5019bf1aa0`

Tamaño ZIP del artefacto: `242954430` bytes

SHA-256 ZIP GitHub Actions:

`24f5b5a2ed2effc2bfb22a192681aac8f9afc9e3f489f3688af2c4e3cb7db4ce`

Caducidad inicial del artefacto: **19/09/2026**.

## Catálogos y assets

Build 0.10.6:

- catálogo de pinturas generado: **2511 pinturas**;
- todas las pinturas del catálogo validado incluyen metadatos Lab;
- catálogo de miniaturas: más de 500 unidades;
- Star Wars: Legion: 89/93 productos únicos con cobertura de imagen en la build (95,7 %);
- banners principales y recursos de Favoritos verificados.

## Módulos actuales

### Pinturas

Operativo.

Incluye inventario, cantidades, stock, marcas, gamas, tipos, colores, RGB/Lab y búsqueda de alternativas mediante CIELAB/DeltaE.

### Materiales

Operativo.

Incluye inventario, marcas, cantidades, futuras compras y flujo de confirmación de compra.

### Compras

Operativo.

Futuras compras, cesta, confirmación y actualización del inventario.

### Miniaturas

Operativo para Star Wars: Legion y Warhammer Age of Sigmar.

Estados disponibles:

- Sin montar
- Montado
- Pintado
- Terminado

### Buscador de tutoriales

Operativo mediante YouTube Data API.

Incluye:

- contextualización de consultas hacia pintura/modelismo;
- filtros Todos / Español / Inglés;
- tags ES / EN / ?;
- ranking por relevancia y señales de popularidad;
- reproductor interno Qt WebEngine;
- apertura externa en YouTube.

### Favoritos

Operativo.

Categorías:

- Miniaturas
- Modelismo general

Los vídeos de miniaturas pueden analizar las pinturas mencionadas y compararlas con la base de datos local.

## Evolución 0.10

### 0.10.1

Introducción del análisis de pinturas en tutoriales favoritos de miniaturas y comparación con el inventario.

### 0.10.2

Refuerzo del análisis de pinturas, umbral de alternativas >=85 % y conexión de pinturas ausentes con Futuras compras.

### 0.10.3

Fundación provider-neutral de Ciros Assistant y siete herramientas locales de pinturas. Sin proveedor de IA todavía.

### 0.10.4

Primera interfaz visual completa del asistente: conversaciones, chat, imágenes y configuración visual de Gemini.

### 0.10.5

Gemini se mueve a Ajustes, se añade `Abrir ubicación` para la base de datos, se incorpora el diálogo informativo del asistente y se corrige el botón Enviar.

### 0.10.6

Primera integración funcional de Gemini:

- Interactions API;
- Gemini 3.7 Flash;
- conversación stateless con `store=False`;
- contexto temporal en RAM;
- entrada multimodal;
- function calling;
- ejecución local de las siete herramientas;
- comprobación real de conexión;
- ejecución asíncrona para no bloquear PySide6;
- errores de autenticación, red, timeout, 429 y 503 tratados de forma explícita.

## Ciros Assistant - reglas de arquitectura

La IA no tiene acceso directo a la base de datos.

Flujo:

```text
Usuario
  -> Gemini interpreta la petición
  -> Gemini solicita una herramienta cuando necesita datos/acciones locales
  -> Ciros Paint valida y ejecuta la herramienta
  -> SQLite/repositories locales
  -> resultado estructurado a Gemini
  -> respuesta al usuario
```

La base de datos local es la fuente de verdad para inventario, cantidades y compras.

Las operaciones ambiguas no deben modificar datos hasta obtener una aclaración.

Las conversaciones son temporales y no se persisten entre ejecuciones.

## Herramientas iniciales del asistente

1. `search_paints`
2. `get_paint_stock`
3. `find_paint_alternatives`
4. `add_paint_to_inventory`
5. `set_paint_quantity`
6. `add_paint_to_future_purchases`
7. `list_future_paint_purchases`

## Persistencia de datos

Directorio local:

`%LOCALAPPDATA%\CirosPaint\`

Base de datos:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

La API Key de Gemini se almacena en configuración local de la aplicación y no forma parte del ejecutable ni del repositorio.

Actualizar el ejecutable no debe eliminar el inventario existente.

## Pendiente de validación manual específica

Aunque CI verifica el SDK, tool-calling mediante mocks, errores y UI, la integración con una API Key real depende del proyecto/cuota Gemini del usuario.

La batería manual está documentada en `MANUAL_TESTS_0.10.6.md`.

## Próximos pasos posibles

Antes de añadir capacidades nuevas al asistente, conviene cerrar la validación manual completa de 0.10.6. Después se pueden valorar mejoras como streaming de respuestas, indicadores de herramientas ejecutadas, nuevas herramientas locales y refinamientos de UX.
