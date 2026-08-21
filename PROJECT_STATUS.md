# Ciros Paint - Project Status

Última actualización: **21/08/2026**

## Estado actual

Versión más reciente validada: **Ciros Paint 0.10.9**

Rama de verificación utilizada: `build/verify-0.10.8`

La familia 0.10 amplía la base consolidada de 0.9 con análisis de pinturas en Favoritos y Ciros Assistant. 0.10.8 refuerza la arquitectura **local-first** con resolución local de entidades, workflows guiados, autocompletado contextual y fallback acotado a Gemini para nombres que no pueden resolverse localmente con seguridad.

0.10.9 fue validada por GitHub Actions run `32489725696` con 137 tests, smoke PySide6, PyInstaller y artefacto Windows correctos.

Desarrollo actual en `feature/centralized-query-service`: **0.10.10**, con una fachada central read-only sobre repositories/SQLite y catálogos. No cambia mutaciones ni esquema de base de datos.

## Validación automática final de 0.10.8

GitHub Actions run: `32475688035`

Resultado: **SUCCESS**

Validado:

- reconstrucción completa desde la fuente histórica hasta 0.10.8;
- overlays 0.10.7 y 0.10.8 reconstruidos y validados por SHA-256;
- instalación del SDK oficial `google-genai`;
- disponibilidad de Interactions API;
- catálogos y assets;
- **128 tests**, todos OK;
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

## Build 0.10.8

Overlay reconstruido: `CirosPaint_0.10.8_overlay.zip`

SHA-256 overlay:

`d85dc1f7c9b168890f9f03d4f5973979fbafe73ff2712fbf7428d628ce09e860`

Artefacto: `CirosPaint-Windows-0.10.8`

Artifact ID: `9444337506`

Ejecutable: `CirosPaint_0.10.8.exe`

Tamaño EXE: `244399034` bytes

SHA-256 EXE:

`39f2bf097cf252cf94740428ee5b4d4f589b0bf487d42236bc3396ef22d6be38`

La CI verificó el ejecutable y publicó el artefacto Windows de 0.10.8.

## Catálogos y assets

Build 0.10.8:

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

Ciros Assistant 0.10.8 puede consultar y modificar operaciones compatibles de la colección mediante la capa local, preservando los contadores de estado.

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

### 0.10.8

Refuerzo de la resolución y los workflows locales:

- `LocalEntityResolver` con normalización, fuzzy matching y control de confianza;
- `AssistantWorkflowEngine` para flujos guiados deterministas por conversación;
- catálogo completo al añadir miniaturas y colección poseída al cambiar estados;
- acción encadenada `Cambiar otra miniatura`;
- fallback automático a Gemini únicamente para interpretar nombres no resueltos;
- validación posterior del resultado contra entidades locales reales;
- contador diario persistente de requests reales a Gemini;
- compatibilidad con los contadores reales de estados de miniaturas.

## Ciros Assistant - reglas de arquitectura

La IA no tiene acceso directo a la base de datos.

Flujo 0.10.8:

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

0.10.8 mantiene exactamente estas siete herramientas para function calling. La resolución de pinturas y miniaturas intenta primero `LocalEntityResolver`; cuando hace falta interpretación adicional de un nombre, utiliza una llamada específica sin tools y valida localmente el resultado.

## Reconstrucción de la fuente actual

`tools/rebuild_current.ps1` reconstruye la cadena histórica completa hasta 0.10.8 en un staging temporal, valida todos los hashes publicados y solo entonces publica `build_source/`. Los ZIP derivados permanecen en el staging y no se escriben en `source/` ni `patches/`. Dependencias, catálogos, assets, tests y PyInstaller continúan como fases separadas del workflow de GitHub Actions.

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
