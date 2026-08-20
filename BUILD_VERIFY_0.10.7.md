# Ciros Paint 0.10.7 - Build Verification

Fecha de validación: **20/08/2026**

## Resultado

GitHub Actions run: `32397932655` (#230)

Resultado final: **SUCCESS**

Pull request validado: **#26 - Verify Ciros Paint 0.10.7 local-first assistant**

Merge en `main`: `3c26b32663699367a180dd10142b33a2925e8ff3`

## Validaciones ejecutadas

- reconstrucción histórica completa hasta 0.10.6;
- reconstrucción y verificación criptográfica del overlay 0.10.7;
- aplicación correcta del overlay 0.10.7;
- instalación de dependencias;
- disponibilidad de Google Gen AI Interactions API;
- generación del catálogo de pinturas;
- descarga/verificación de assets de miniaturas;
- **115 tests, todos OK**;
- smoke test funcional de Ciros Assistant, OK;
- build PyInstaller Windows `--windowed --onefile`, OK;
- subida del artefacto, OK.

## Entorno validado

- Windows Server 2025
- Python 3.12.10
- PyInstaller 6.22.2
- PySide6 6.11.2
- SQLAlchemy 2.0.52
- `google-genai` 2.19.0

## Overlay 0.10.7

Archivo reconstruido: `CirosPaint_0.10.7_overlay.zip`

SHA-256:

`062ae2b06e881f1d243b3ae7a4cbe150d889b46fb938f98735bd45c2def89f1b`

La build falla si los nueve fragmentos almacenados en `patches/v0.10.7/chunks/` no reconstruyen exactamente este hash.

## Ejecutable

Archivo: `CirosPaint_0.10.7.exe`

Tamaño: `244382691` bytes

SHA-256:

`ba333211e9684efd4ffb0a03175aeeb55afd152d32e7e4aef1cbae7d98a2f50e`

El ejecutable extraído nuevamente del artefacto de GitHub Actions fue verificado de forma independiente y produjo el mismo tamaño y SHA-256.

## Artefacto GitHub Actions

Nombre: `CirosPaint-Windows-0.10.7`

Artifact ID: `9417510361`

Tamaño ZIP: `242991446` bytes

SHA-256 ZIP GitHub Actions:

`90e4e9b2d4b66f4e4debd69bc162d79f3e1593fb48287080ceae9e4d8ecf9a1f`

Caducidad inicial: **19/09/2026**.

## Catálogos y assets

- catálogo de pinturas generado: **2511 pinturas**;
- metadatos Lab validados;
- catálogo de miniaturas validado con más de 500 unidades;
- Star Wars: Legion: 89/93 productos únicos con cobertura de imagen durante la build (95,7 %);
- banners y recursos principales verificados.

## Ciros Assistant 0.10.7 validado

La batería automática confirma, entre otros puntos:

- consultas locales capaces de funcionar sin API Key de Gemini;
- operaciones locales de pinturas y miniaturas;
- actualización de estados de miniaturas preservando los contadores;
- Gemini con `thinking_level="low"` cuando es necesario;
- consultas generales a Gemini sin exponer herramientas innecesarias;
- function calling restringido a las siete herramientas controladas de pinturas cuando corresponde;
- resolvedor de miniaturas mediante una llamada específica sin tools;
- reducción del historial enviado al proveedor;
- información de consumo de tokens visible cuando Gemini devuelve métricas;
- tratamiento más claro de cuota 429 y tiempo de reintento;
- Markdown y mensajes largos sin truncado;
- integración de autocomplete y mejoras visuales del chat.

## Validación manual

Las pruebas que dependen de una API Key real, cuota real del proyecto Gemini y comprobación visual del ejecutable están recogidas en `MANUAL_TESTS_0.10.7.md`.
