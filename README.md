# Ciros Paint

Aplicación de escritorio **local-first para Windows** destinada a gestionar pinturas, materiales, compras, miniaturas y recursos del hobby de pintura y modelismo.

## Estado actual

**Última versión validada: Ciros Paint 0.10.7** — 20/08/2026.

La familia 0.10 incorpora análisis de pinturas en favoritos y Ciros Assistant. Desde 0.10.7 el asistente utiliza una arquitectura **local-first**: las consultas y operaciones deterministas se intentan resolver dentro de Ciros Paint sin consumir Gemini, y el proveedor se utiliza como fallback cuando hace falta interpretación o generación.

Validación automática de 0.10.7:

- GitHub Actions run `32397932655`: **SUCCESS**.
- **115 tests: OK**.
- Smoke test funcional del asistente: **OK**.
- Python 3.12.10.
- PyInstaller 6.22.2.
- `google-genai` 2.19.0.
- Catálogo generado: **2511 pinturas** con metadatos Lab.

## Funcionalidades principales

### Pinturas

- Inventario local de pinturas.
- Catálogo integrado con marcas, gamas, códigos, tipos y color.
- Cantidades disponibles y control de stock.
- Colores primarios/complementarios.
- Metadatos RGB/Lab para comparaciones de color.
- Alternativas por similitud CIELAB/DeltaE con umbral mínimo del 85 %.
- Enlaces oficiales para marcas compatibles.

### Materiales y compras

- Inventario de materiales.
- Marcas predefinidas y personalizadas.
- Futuras compras y cesta.
- Confirmación de compras antes de añadir cantidades al inventario.
- Reposición automática en casos compatibles.

### Miniaturas

- Colección de **Star Wars: Legion** y **Warhammer Age of Sigmar**.
- Estados: Sin montar, Montado, Pintado y Terminado.
- Catálogo local de unidades y facciones.
- Imágenes oficiales/locales incluidas cuando están disponibles.
- Ciros Assistant 0.10.7 puede consultar y actualizar operaciones compatibles de la colección mediante la capa local.

### Buscador de tutoriales

- Integración con **YouTube Data API**.
- Consultas contextualizadas hacia pintura de miniaturas y modelismo.
- Filtros Todos / Español / Inglés.
- Identificación ES / EN / ?.
- Ranking por relevancia, visualizaciones, likes y recencia.
- Reproductor interno con Qt WebEngine.
- Apertura externa en YouTube.
- Favoritos organizados en Miniaturas y Modelismo general.

### Análisis de pinturas en Favoritos

- Detección de pinturas mencionadas en tutoriales guardados.
- Comparación con el inventario local.
- Diferenciación entre coincidencias exactas, posibles coincidencias y pinturas ausentes.
- Alternativas por color usando CIELAB/DeltaE y umbral >=85 %.
- Pinturas ausentes añadibles a Futuras compras sin duplicados.

## Ciros Assistant

Ciros Assistant es un asistente especializado en pintura de miniaturas y modelismo.

### Local-first en 0.10.7

Antes de llamar a Gemini, Ciros Paint intenta resolver localmente las operaciones compatibles. Esto permite responder con **0 tokens Gemini** en consultas deterministas y mantiene la base de datos local como fuente de verdad.

Entre las operaciones cubiertas localmente se incluyen:

1. Buscar pinturas y sugerir coincidencias/autocompletado.
2. Consultar stock, pinturas agotadas o casi agotadas.
3. Consultar y gestionar Futuras compras en casos compatibles.
4. Consultar miniaturas de la colección.
5. Consultar o modificar estados de miniaturas cuando la identidad es segura.

Cuando la consulta requiere razonamiento o lenguaje abierto, Gemini se utiliza como fallback.

### Gemini

- Modelo configurado: `gemini-3.7-flash`.
- Interactions API.
- `store=False`.
- `thinking_level="low"` para reducir consumo innecesario.
- Historial temporal limitado a los turnos recientes necesarios.
- Consultas generales sin tools cuando no hacen falta.
- Function calling restringido a las siete herramientas controladas de pinturas cuando corresponde.
- Métricas de tokens mostradas en la UI cuando el proveedor las devuelve.
- Tratamiento específico de autenticación, red, timeout, 429 y 503.

### Interfaz del asistente

- Conversaciones temporales independientes.
- Autocompletado local de pinturas.
- Indicador `Consulta local · 0 tokens Gemini`.
- Markdown.
- Respuestas largas sin truncado.
- Imágenes adjuntas con presentación visual mejorada.
- Ejecución asíncrona para no bloquear PySide6.

### Arquitectura y seguridad

Gemini **no recibe acceso directo a SQLite**. Ciros Paint controla las consultas/escrituras locales y valida cualquier operación antes de modificar información.

Las conversaciones:

- se mantienen únicamente en memoria durante la ejecución;
- son independientes entre sí;
- no se almacenan en SQLite;
- desaparecen al cerrar Ciros Paint;
- utilizan llamadas Gemini con `store=False`.

Las operaciones ambiguas deben solicitar aclaración antes de modificar datos.

## Configuración de APIs

En **Ajustes** se encuentran las integraciones externas:

### YouTube Data API

Necesaria para el Buscador de tutoriales.

### Gemini API

Necesaria únicamente para las funciones de Ciros Assistant que realmente requieren Gemini. Las consultas locales compatibles pueden funcionar sin API Key.

La API Key se introduce manualmente, se muestra oculta por defecto y se guarda únicamente en los datos locales del ordenador. No se incluye en el ejecutable ni se publica en GitHub.

El botón **Comprobar conexión** realiza una comprobación real contra Gemini.

## Datos locales

Los datos del usuario se guardan fuera del ejecutable en:

```text
%LOCALAPPDATA%\CirosPaint\
```

Base de datos principal:

```text
%LOCALAPPDATA%\CirosPaint\ciros_paint.db
```

Desde Ajustes se puede utilizar **Abrir ubicación** para abrir directamente la carpeta de datos.

Actualizar el ejecutable no debe sustituir ni borrar el inventario local.

## Build de Windows

La build validada se genera mediante GitHub Actions sobre Windows Server 2025 con Python 3.12 y PyInstaller en modo `--windowed --onefile`.

Build 0.10.7:

- Workflow run: `32397932655` (#230).
- Artefacto: `CirosPaint-Windows-0.10.7`.
- Artifact ID: `9417510361`.
- Ejecutable: `CirosPaint_0.10.7.exe`.
- Tamaño EXE: `244382691` bytes.
- SHA-256 EXE: `ba333211e9684efd4ffb0a03175aeeb55afd152d32e7e4aef1cbae7d98a2f50e`.
- Tamaño ZIP: `242991446` bytes.
- SHA-256 ZIP: `90e4e9b2d4b66f4e4debd69bc162d79f3e1593fb48287080ceae9e4d8ecf9a1f`.
- SHA-256 overlay 0.10.7: `062ae2b06e881f1d243b3ae7a4cbe150d889b46fb938f98735bd45c2def89f1b`.

## Estructura de desarrollo

El repositorio conserva una cadena histórica de fuente base + overlays/parches. La build reconstruye de forma determinista las versiones anteriores y aplica los overlays hasta llegar a la versión actual.

Para 0.10.7 la secuencia relevante termina en:

```text
0.9 -> 0.10.1 -> 0.10.2 -> 0.10.3 -> 0.10.4 -> 0.10.5 -> 0.10.6 -> 0.10.7
```

## Documentación

- `PROJECT_STATUS.md`: estado técnico actual del proyecto.
- `CHANGELOG.md`: resumen de versiones y cambios.
- `ASSISTANT_ARCHITECTURE.md`: arquitectura y reglas de Ciros Assistant.
- `MANUAL_TESTS_0.10.7.md`: batería de validación manual de 0.10.7.
- `BUILD_VERIFY_0.10.7.md`: datos exactos de la build validada.

## Nota sobre servicios externos

Ciros Paint funciona localmente para inventarios y datos propios. YouTube y las capacidades de Ciros Assistant que usan Gemini requieren conexión a Internet y sus respectivas API Keys. Sus cuotas, disponibilidad y políticas dependen de los proveedores externos.
