# Ciros Assistant - Arquitectura

Documento técnico de referencia para la integración del asistente en Ciros Paint 0.10.6.

## Objetivo

Ciros Assistant utiliza Gemini como capa de interpretación y generación de lenguaje, mientras que **Ciros Paint conserva el control total de los datos y de las operaciones locales**.

La IA no recibe acceso SQL, ORM ni acceso directo al archivo SQLite.

## Flujo general

```text
Usuario
  |
  v
AssistantPage (PySide6)
  |
  v
AssistantRequestTask / QThreadPool
  |
  v
GeminiAssistantService
  |
  +--> Gemini Interactions API
  |       |
  |       +--> respuesta directa
  |       |
  |       +--> function_call
  |               |
  |               v
  |       AssistantPaintService
  |               |
  |               v
  |       Repositories de Ciros Paint
  |               |
  |               v
  |             SQLite
  |               |
  |               v
  |       AssistantToolResult
  |               |
  +<------ function_result
  |
  v
Respuesta final en el chat
```

## Proveedor

Versión 0.10.6:

- SDK: `google-genai>=2.3,<3`.
- SDK resuelto durante la build validada: `2.19.0`.
- Modelo inicial: `gemini-3.7-flash`.
- API: Interactions API.
- Persistencia del proveedor: `store=False`.

## Conversaciones

`AssistantSessionStore` conserva las conversaciones únicamente en memoria.

Cada conversación mantiene:

- mensajes visibles de usuario/asistente;
- historial de proveedor necesario para continuar la interacción stateless.

No se guarda historial conversacional en:

- SQLite;
- archivos de configuración;
- disco;
- memoria persistente entre ejecuciones.

Cerrar Ciros Paint elimina el contexto conversacional.

## Herramientas locales

El registro inicial contiene exactamente siete herramientas:

### 1. `search_paints`

Busca pinturas del inventario por texto, marca, nombre, código, gama, color o tipo.

Puede limitar la búsqueda a pinturas con stock positivo.

### 2. `get_paint_stock`

Devuelve la pintura resuelta y su cantidad real en la base de datos.

### 3. `find_paint_alternatives`

Busca alternativas que el usuario ya posee.

La equivalencia no la decide Gemini: Ciros Paint calcula compatibilidad por tipo y similitud CIELAB/DeltaE y aplica el umbral mínimo definido por la aplicación.

### 4. `add_paint_to_inventory`

Representa una compra/nuevas unidades.

Ejemplo semántico:

`He comprado 2` -> suma 2 unidades.

### 5. `set_paint_quantity`

Establece la cantidad total actual.

Ejemplo semántico:

`Ahora tengo 2` -> total = 2.

### 6. `add_paint_to_future_purchases`

Añade una pintura del catálogo a Futuras compras reutilizando el sistema existente y evitando duplicados.

### 7. `list_future_paint_purchases`

Devuelve las pinturas actualmente pendientes en Futuras compras.

## Reglas de integridad

### Base de datos como fuente de verdad

Gemini no debe afirmar que una pintura se posee, su stock o una compra pendiente sin consultar las herramientas cuando la respuesta depende de datos locales.

### No inventar pinturas

Una escritura que haga referencia a una pintura inexistente en el catálogo no debe crear un producto ficticio.

### Ambigüedad

Si existen varias coincidencias plausibles para una escritura, el servicio devuelve `requires_user_input=True` y no modifica la base de datos.

Gemini debe pedir aclaración antes de continuar.

### Confirmación real de escritura

Gemini no debe afirmar que una modificación se ha realizado hasta recibir un resultado satisfactorio de la herramienta local.

## Imágenes

La interfaz admite imágenes relacionadas con el ámbito del asistente.

Formatos directos compatibles:

- JPEG
- PNG
- WebP

Otros formatos legibles por Qt pueden convertirse a JPEG antes del envío.

Las imágenes grandes pueden escalarse/comprimirse para mantener la petición por debajo del margen definido para datos inline.

No se guarda una copia persistente de la imagen dentro del sistema conversacional.

## Asincronía

Las llamadas a Gemini se ejecutan fuera del hilo principal de Qt.

Objetivos:

- evitar congelar la ventana;
- mantener navegación y repintado de la UI;
- mostrar estado `Gemini está pensando…`;
- rehabilitar controles al finalizar o fallar.

## Errores tratados

La capa Gemini transforma errores técnicos en mensajes comprensibles para el usuario.

Casos principales:

- falta de API Key;
- autenticación 401/403;
- cuota/límite 429;
- solicitud inválida 400;
- indisponibilidad/saturación 503;
- timeout;
- red/DNS/conectividad;
- respuesta vacía o flujo de herramientas excesivo.

## Configuración de API Key

La clave se gestiona desde Ajustes.

Propiedades:

- campo oculto por defecto;
- Mostrar/Ocultar;
- Guardar;
- Comprobar conexión;
- Eliminar;
- almacenamiento local fuera del ejecutable y de GitHub.

La build y los tests no contienen una API Key real.

## Alcance de producto

Ciros Assistant está especializado en:

- pintura de miniaturas;
- modelismo;
- aerografía;
- pincel;
- imprimación;
- luces/sombras/degradados;
- teoría de color aplicada al hobby;
- desgaste, suciedad y óxido;
- dioramas y escenografía;
- inventario de pinturas y compras asociadas.

Las consultas claramente ajenas al ámbito deben redirigirse de forma breve al propósito del asistente.

## Tests 0.10.6

CI cubre, entre otros:

- interacción de texto stateless;
- reutilización del historial entre turnos;
- function calling local;
- devolución de function results a Gemini;
- imagen + texto inline;
- error 429;
- conexión mínima;
- flujo asíncrono de UI;
- error sin crash;
- ausencia de clave;
- persistencia de historial solo en la conversación en memoria;
- las siete herramientas originales y sus reglas de integridad.

La validación manual con una clave real se documenta en `MANUAL_TESTS_0.10.6.md`.
