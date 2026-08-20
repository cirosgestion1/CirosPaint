# Build Verify - Ciros Paint 0.10.6

Fecha: **20/08/2026**

## Resultado

GitHub Actions: **SUCCESS**

Workflow: `Build Windows EXE`

Run ID: `32382923636`

Run number: `205`

Rama: `build/verify-0.10.6`

PR: `#25`

Head SHA validado antes de la actualización documental: `d8a68fb77af711f92b5996c973fdae7e781a491b`

## Entorno

- Windows Server 2025
- Python 3.12.10
- PyInstaller 6.22.2
- PySide6 6.11.2
- SQLAlchemy 2.0.52
- google-genai 2.19.0

## Reconstrucción

La ejecución reconstruyó correctamente la cadena histórica de Ciros Paint y aplicó los overlays hasta 0.10.6.

Resultado:

`Ciros Paint 0.10.6 functional Gemini overlay verified`

## Gemini SDK

La build verificó que el SDK instalado expone Interactions API:

`google-genai 2.19.0 Interactions API available`

Los tests no utilizan una API Key real.

## Catálogo de pinturas

Generado durante CI:

- 2511 pinturas
- metadatos Lab validados

## Miniaturas

Validación de assets:

- assets directos: 36/36
- Assembly: 86/86
- cobertura única Star Wars: Legion: 89/93 (95,7 %)

Productos oficiales de Assembly sin imagen individual resuelta durante esa build:

- SWL23 Imperial Royal Guards
- SWL55 Dewback Rider
- SWQ06 Galactic Empire Unit Card Pack
- SWQ08 Separatist Alliance Unit Card Pack

Estas advertencias no bloquearon la build.

## Tests

Resultado:

```text
Ran 113 tests in 6.383s
OK
```

Entre los tests específicos de 0.10.6:

- mensaje claro para error 429;
- comprobación mínima de conexión;
- function call ejecutado localmente;
- function result devuelto a Gemini;
- imagen inline con texto;
- conversación stateless;
- reutilización del historial de proveedor entre turnos;
- comprobación de Gemini asíncrona desde Ajustes;
- errores renderizados sin cerrar el chat;
- ausencia de API Key sin consumir el mensaje;
- flujo asíncrono real de Enviar;
- persistencia del historial solo en RAM.

## Smoke test funcional

Resultado:

`Ciros Paint 0.10.6 functional assistant smoke test OK`

Verificó:

- `APP_VERSION == 0.10.6`;
- AssistantPage inicializa correctamente;
- botón Enviar disponible;
- Ajustes contiene el campo Gemini en modo Password;
- botón `Comprobar conexión` presente;
- exactamente siete function tools declaradas.

## PyInstaller

Build en modo:

- `--windowed`
- `--onefile`
- `--collect-all google.genai`

El paquete incluye catálogos, assets, avisos de terceros y dependencias necesarias.

Advertencias no fatales observadas:

- `google.genai.tests` no recopilado por ausencia de pytest (submódulo de tests del SDK, no necesario en runtime);
- `tzdata` oculto no encontrado;
- plugin QML opcional ausente;
- drivers SQLAlchemy opcionales `pysqlite2`, `MySQLdb` y `psycopg2` no encontrados.

La aplicación utiliza SQLite estándar y la build terminó correctamente.

## Ejecutable

Nombre:

`CirosPaint_0.10.6.exe`

Tamaño:

`244346433` bytes

SHA-256:

`58c3ae2560c9afeda18dc4a9c49466ebfe8c9abf14f80b4f81d75d5019bf1aa0`

## Artefacto GitHub Actions

Nombre:

`CirosPaint-Windows-0.10.6`

Artifact ID:

`9411981601`

Tamaño ZIP:

`242954430` bytes

SHA-256 ZIP:

`24f5b5a2ed2effc2bfb22a192681aac8f9afc9e3f489f3688af2c4e3cb7db4ce`

Caducidad inicial:

`19/09/2026`

## Resultado final

La build 0.10.6 quedó validada automáticamente para distribución y pruebas manuales con una API Key real.

La batería de validación manual está en `MANUAL_TESTS_0.10.6.md`.
