# Ciros Paint

Aplicación de escritorio **local-first para Windows** destinada a gestionar pinturas, materiales, compras, miniaturas y recursos del hobby de pintura y modelismo.

## Estado actual

**Última versión validada: Ciros Paint 0.10.6** — 20/08/2026.

La familia 0.10 incorpora análisis de pinturas en favoritos y, desde 0.10.6, la primera versión funcional de **Ciros Assistant** con Gemini.

Validación automática de 0.10.6:

- GitHub Actions: **SUCCESS**.
- 113 tests: **OK**.
- Smoke test funcional del asistente: **OK**.
- Python 3.12.10.
- PyInstaller 6.22.2.
- `google-genai` 2.19.0 en la build validada.
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
- Imágenes oficiales/locales incluidas en el paquete cuando están disponibles.

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

Desde **0.10.6** puede conectarse realmente a Gemini y trabajar con la base de datos de Ciros Paint mediante herramientas controladas por la aplicación.

Capacidades iniciales:

1. Buscar pinturas del inventario.
2. Consultar stock y cantidades.
3. Buscar alternativas de color que el usuario ya posee.
4. Añadir unidades compradas al inventario.
5. Establecer la cantidad total de una pintura.
6. Añadir pinturas a Futuras compras.
7. Consultar Futuras compras.
8. Resolver preguntas generales sobre pintura de miniaturas, aerografía, técnicas, desgaste, dioramas y escenografía.
9. Recibir imágenes relacionadas con el hobby y utilizarlas como contexto visual.

### Arquitectura y seguridad del asistente

Gemini **no recibe acceso directo a SQLite**. El modelo puede solicitar una función; Ciros Paint valida y ejecuta la operación localmente y devuelve únicamente el resultado necesario.

La base de datos local es siempre la fuente de verdad sobre inventario, cantidades y compras.

Las conversaciones:

- se mantienen únicamente en memoria durante la ejecución;
- son independientes entre sí;
- no se almacenan en SQLite;
- desaparecen al cerrar Ciros Paint;
- utilizan llamadas Gemini con `store=False`.

Las operaciones ambiguas deben solicitar aclaración antes de modificar datos.

## Configuración de APIs

En **Ajustes** se encuentran las dos integraciones externas:

### YouTube Data API

Necesaria para el Buscador de tutoriales.

### Gemini API

Necesaria para Ciros Assistant.

La API Key se introduce manualmente, se muestra oculta por defecto y se guarda únicamente en los datos locales del ordenador. No se incluye en el ejecutable ni se publica en GitHub.

El botón **Comprobar conexión** realiza una comprobación real contra Gemini.

Ciros Paint trata de forma específica errores de autenticación, red, timeout, indisponibilidad y límites de cuota (`429`).

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

Build 0.10.6:

- Workflow run: `32382923636` (#205).
- Artefacto: `CirosPaint-Windows-0.10.6`.
- Ejecutable: `CirosPaint_0.10.6.exe`.
- Tamaño del EXE: `244346433` bytes.
- SHA-256 EXE: `58c3ae2560c9afeda18dc4a9c49466ebfe8c9abf14f80b4f81d75d5019bf1aa0`.
- Artifact ID: `9411981601`.
- SHA-256 del ZIP de GitHub Actions: `24f5b5a2ed2effc2bfb22a192681aac8f9afc9e3f489f3688af2c4e3cb7db4ce`.

## Estructura de desarrollo

El repositorio conserva una cadena histórica de fuente base + overlays/parches. La build reconstruye de forma determinista las versiones anteriores y aplica los overlays hasta llegar a la versión actual.

Para 0.10.6 la secuencia relevante termina en:

```text
0.9 -> 0.10.1 -> 0.10.2 -> 0.10.3 -> 0.10.4 -> 0.10.5 -> 0.10.6
```

Esta arquitectura permite conservar el historial de evolución y reproducir la build final desde GitHub Actions.

## Documentación

- `PROJECT_STATUS.md`: estado técnico actual del proyecto.
- `CHANGELOG.md`: resumen de versiones y cambios.
- `ASSISTANT_ARCHITECTURE.md`: arquitectura y reglas de Ciros Assistant.
- `MANUAL_TESTS_0.10.6.md`: batería de validación manual de la primera integración funcional con Gemini.
- `BUILD_VERIFY_0.10.6.md`: datos exactos de la build validada.

## Nota sobre servicios externos

Ciros Paint funciona localmente para inventarios y datos propios, pero YouTube y Gemini requieren conexión a Internet y sus respectivas API Keys. Sus cuotas, disponibilidad y políticas dependen de los proveedores externos.
