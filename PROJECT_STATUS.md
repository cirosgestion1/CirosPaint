# Ciros Paint - Project Status

Última actualización: **20/08/2026**

## Estado actual

Versión más reciente validada: **Ciros Paint 0.10.7**

Rama de verificación utilizada: `build/verify-0.10.7`

PR principal de integración: **#26 - Verify Ciros Paint 0.10.7 local-first assistant**

Merge en `main`: `3c26b32663699367a180dd10142b33a2925e8ff3`

La familia 0.10 amplía la base consolidada de 0.9 con análisis de pinturas en Favoritos y Ciros Assistant. La 0.10.7 cambia el asistente a una arquitectura **local-first**: las operaciones deterministas se resuelven dentro de Ciros Paint sin gastar tokens y Gemini queda como capa de interpretación/generación cuando realmente es necesario.

## Validación automática final de 0.10.7

GitHub Actions run: `32397932655` (#230)

Resultado: **SUCCESS**

Validado:

- reconstrucción completa desde la fuente histórica hasta 0.10.7;
- overlay 0.10.7 reconstruido desde nueve fragmentos y validado por SHA-256;
- instalación del SDK oficial `google-genai`;
- disponibilidad de Interactions API;
- catálogos y assets;
- **115 tests**, todos OK;
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

## Build 0.10.7

Overlay reconstruido: `CirosPaint_0.10.7_overlay.zip`

SHA-256 overlay:

`062ae2b06e881f1d243b3ae7a4cbe150d889b46fb938f98735bd45c2def89f1b`

Artefacto: `CirosPaint-Windows-0.10.7`

Artifact ID: `9417510361`

Ejecutable: `CirosPaint_0.10.7.exe`

Tamaño EXE: `244382691` bytes

SHA-256 EXE:

`ba333211e9684efd4ffb0a03175aeeb55afd152d32e7e4aef1cbae7d98a2f50e`

Tamaño ZIP del artefacto: `242991446` bytes

SHA-256 ZIP GitHub Actions:

`90e4e9b2d4b66f4e4debd69bc162d79f3e1593fb48287080ceae9e4d8ecf9a1f`

Caducidad inicial del artefacto: **19/09/2026**.

El EXE se volvió a extraer del artefacto descargado y se verificó de forma independiente: tamaño y SHA-256 coinciden con los registrados por la CI.

## Catálogos y assets

Build 0.10.7:

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

Ciros Assistant 0.10.7 puede consultar y modificar operaciones compatibles de la colección mediante la capa local, preservando los contadores de estado.

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
- ejecución local de las siete herramientas de pinturas;
- comprobación real de conexión;
- ejecución asíncrona para no bloquear PySide6;
- errores de autenticación, red, timeout, 429 y 503 tratados de forma explícita.

### 0.10.7

Optimización local-first y ampliación de Ciros Assistant:

- `AssistantLocalService` para operaciones deterministas sin Gemini;
- consultas locales de pinturas, stock, agotadas/casi agotadas y compras;
- consulta y actualización local de miniaturas/estados;
- autocompletado local;
- indicador `Consulta local · 0 tokens Gemini`;
- Gemini usado como fallback;
- `thinking_level="low"`;
- consultas generales sin tools innecesarias;
- las siete herramientas de pinturas permanecen controladas y sin acceso SQL directo;
- resolvedor de nombres de miniaturas mediante llamada separada sin tools;
- reducción del historial enviado al proveedor;
- métricas de tokens visibles cuando están disponibles;
- mejor tratamiento de cuota 429 y reintentos;
- Markdown, mensajes largos completos y mejoras de imágenes en el chat.

## Ciros Assistant - reglas de arquitectura

La IA no tiene acceso directo a la base de datos.

Flujo 0.10.7:

```text
Usuario
  -> Ciros Paint intenta resolver localmente
       -> si es determinista: repositories/SQLite -> respuesta local (0 tokens)
       -> si necesita interpretación/generación: Gemini
            -> respuesta general sin tools, o
            -> tools controladas de pinturas cuando procede
            -> Ciros Paint valida y ejecuta localmente
  -> respuesta final en el chat
```

La base de datos local es la fuente de verdad para inventario, cantidades, compras y colección de miniaturas.

Las operaciones ambiguas no deben modificar datos hasta obtener una aclaración.

Las conversaciones son temporales y no se persisten entre ejecuciones.

## Herramientas controladas de pinturas

1. `search_paints`
2. `get_paint_stock`
3. `find_paint_alternatives`
4. `add_paint_to_inventory`
5. `set_paint_quantity`
6. `add_paint_to_future_purchases`
7. `list_future_paint_purchases`

0.10.7 mantiene exactamente estas siete herramientas para function calling. La resolución de miniaturas no amplía indiscriminadamente ese registro: usa la capa local y, cuando hace falta interpretación adicional de un nombre, una llamada específica sin tools.

## Persistencia de datos

Directorio local:

`%LOCALAPPDATA%\CirosPaint\`

Base de datos:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

La API Key de Gemini se almacena en configuración local de la aplicación y no forma parte del ejecutable ni del repositorio.

Actualizar el ejecutable no debe eliminar el inventario existente.

## Pendiente de validación manual específica

La CI verifica comportamiento local, mocks de Gemini, tool-calling, errores, UI, catálogos y build. Las comprobaciones que dependen de una API Key real, cuota real del proyecto Gemini y revisión visual del ejecutable se documentan en `MANUAL_TESTS_0.10.7.md`.

## Próximos pasos posibles

Con la optimización local-first ya integrada, las siguientes mejoras deberían priorizar reducción adicional de llamadas al proveedor, cobertura de más operaciones locales deterministas, streaming si aporta valor real y refinamientos de UX medidos sobre uso real.
