# Ciros Assistant - Arquitectura

Documento técnico de referencia para Ciros Assistant en **Ciros Paint 0.10.8**.

## Objetivo

Ciros Assistant sigue un diseño **local-first**. Ciros Paint intenta resolver primero las consultas y acciones deterministas mediante servicios/repositories locales. Gemini se utiliza únicamente cuando hace falta interpretación adicional o generación de lenguaje.

La IA no recibe acceso SQL, ORM ni acceso directo al archivo SQLite.

## Flujo general 0.10.8

```text
Usuario
  |
  v
AssistantPage (PySide6)
  |
  +--> AssistantLocalService
  |       |
  |       +--> resolución determinista
  |       |       |
  |       |       v
  |       |   Repositories / SQLite
  |       |       |
  |       |       v
  |       |   respuesta local · 0 tokens Gemini
  |       |
  |       +--> no resoluble localmente
  |
  v
AssistantRequestTask / QThreadPool
  |
  v
GeminiAssistantService
  |
  +--> consulta general sin tools
  |       |
  |       v
  |   respuesta Gemini
  |
  +--> operación de pinturas que necesita function calling
          |
          v
      AssistantPaintService
          |
          v
      Repositories / SQLite
          |
          v
      AssistantToolResult -> Gemini -> respuesta final
```

Para miniaturas, la capa local es prioritaria. Si hace falta interpretar un nombre que no puede resolverse con seguridad de forma determinista, existe una resolución específica mediante Gemini **sin exponer tools**.

## Proveedor

Versión 0.10.8:

- SDK: `google-genai>=2.3,<3`.
- SDK resuelto en la build validada: `2.19.0`.
- Modelo: `gemini-3.7-flash`.
- API: Interactions API.
- Persistencia del proveedor: `store=False`.
- Nivel de razonamiento: `thinking_level="low"`.

La reducción de razonamiento no sustituye la capa local: primero se intenta evitar completamente la llamada al proveedor.

## Capa local

`AssistantLocalService` implementa operaciones deterministas que no necesitan lenguaje generativo.

Objetivos:

- reducir consumo de tokens y cuota;
- reducir latencia;
- evitar exponer al proveedor información innecesaria;
- mantener las reglas de negocio dentro de Ciros Paint;
- permitir que consultas compatibles funcionen incluso sin API Key de Gemini.

Incluye operaciones compatibles sobre:

- búsquedas y coincidencias de pinturas;
- stock y estados de disponibilidad;
- Futuras compras;
- autocompletado local;
- consulta de colección de miniaturas;
- consulta/cambio de estados de miniaturas;
- actualización de contadores preservando la integridad de los buckets de estado.

Cuando una operación se resuelve localmente, la UI puede mostrar `Consulta local · 0 tokens Gemini`.

### Resolución local de entidades

`LocalEntityResolver` normaliza texto y clasifica coincidencias exactas, parciales y aproximadas. Solo acepta automáticamente una entidad cuando la confianza y la separación respecto al siguiente candidato son suficientes. Las coincidencias ambiguas no autorizan mutaciones.

Para pinturas y miniaturas, la capa local intenta resolver primero el nombre. Si no puede hacerlo con seguridad, Gemini puede interpretar exclusivamente el nombre entre candidatos reales. La selección externa se valida después contra el catálogo o la colección local antes de ejecutar cualquier operación.

### Workflows guiados

`AssistantWorkflowEngine` conserva en memoria el estado de los flujos guiados de cada conversación. Al añadir miniaturas se consulta el catálogo completo; al cambiar el estado se muestran únicamente miniaturas poseídas. Después de un cambio correcto puede iniciarse el flujo encadenado `Cambiar otra miniatura`.

## Conversaciones

`AssistantSessionStore` conserva las conversaciones únicamente en memoria.

Cada conversación mantiene:

- mensajes visibles de usuario/asistente;
- historial de proveedor cuando existe una interacción con Gemini;
- métricas de uso cuando el proveedor las devuelve.

No se guarda historial conversacional en:

- SQLite;
- archivos de configuración;
- disco;
- memoria persistente entre ejecuciones.

Cerrar Ciros Paint elimina el contexto conversacional.

0.10.8 limita además el historial enviado de vuelta a Gemini a los turnos recientes necesarios para reducir tokens de entrada.

## Herramientas controladas de pinturas

El registro de function calling contiene **exactamente siete herramientas**. No se amplía automáticamente por añadir nuevas capacidades locales.

### 1. `search_paints`

Busca pinturas del inventario por texto, marca, nombre, código, gama, color o tipo.

### 2. `get_paint_stock`

Devuelve la pintura resuelta y su cantidad real en la base de datos.

### 3. `find_paint_alternatives`

Busca alternativas que el usuario ya posee. Ciros Paint calcula compatibilidad por tipo y similitud CIELAB/DeltaE; Gemini no inventa los porcentajes.

### 4. `add_paint_to_inventory`

Representa una compra/nuevas unidades y suma la cantidad correspondiente.

### 5. `set_paint_quantity`

Establece la cantidad total actual indicada por el usuario.

### 6. `add_paint_to_future_purchases`

Añade una pintura del catálogo a Futuras compras reutilizando el sistema existente y evitando duplicados.

### 7. `list_future_paint_purchases`

Devuelve las pinturas actualmente pendientes en Futuras compras.

## Política de tools

- Una consulta general que no necesita datos locales se envía a Gemini **sin tools**.
- Las herramientas se exponen únicamente cuando la petición puede necesitar operaciones controladas de pinturas.
- La resolución adicional de nombres de miniaturas utiliza una llamada específica sin tools.
- Gemini nunca recibe una herramienta de acceso SQL genérico.

## Reglas de integridad

### Base de datos como fuente de verdad

Ciros Paint, no Gemini, es la fuente de verdad sobre inventario, cantidades, compras y colección de miniaturas.

### No inventar pinturas o miniaturas

Una escritura sobre una entidad que no pueda resolverse con seguridad no debe crear datos ficticios.

### Ambigüedad

Si existen varias coincidencias plausibles, no se modifica la información hasta resolver la ambigüedad.

### Confirmación real de escritura

La UI o Gemini no deben afirmar que un cambio se ha realizado hasta que el servicio local correspondiente devuelva éxito.

## Consumo de tokens

0.10.8 utiliza dos medidas complementarias:

1. evitar Gemini cuando la operación es determinista;
2. reducir el coste de las llamadas inevitables mediante `thinking_level="low"`, menos tools y menor historial.

Cuando la Interactions API devuelve métricas de uso, Ciros Paint registra y muestra datos como tokens de entrada/salida en la interfaz del asistente.

Las consultas locales no estiman falsamente tokens: se identifican explícitamente como **0 tokens Gemini** porque no realizan una llamada al proveedor.

`AssistantSettingsStore` mantiene además un contador diario persistente de requests reales. El contador se incrementa en el punto común que crea una interacción con Gemini, incluidas comprobaciones de conexión y resoluciones acotadas de nombres, y se reinicia según el día de cuota del proveedor. No contabiliza operaciones locales ni estimaciones.

## Imágenes

La interfaz admite imágenes relacionadas con el ámbito del asistente.

Formatos directos compatibles:

- JPEG
- PNG
- WebP

Otros formatos legibles por Qt pueden convertirse a JPEG antes del envío.

Las imágenes grandes pueden escalarse/comprimirse para mantener la petición por debajo del margen definido para datos inline.

La interfaz 0.10.8 mantiene la representación visual de adjuntos. No se guarda una copia persistente de la imagen dentro del sistema conversacional.

## Asincronía

Las llamadas a Gemini se ejecutan fuera del hilo principal de Qt.

Objetivos:

- evitar congelar la ventana;
- mantener navegación y repintado de la UI;
- indicar que Gemini está procesando cuando realmente se usa;
- rehabilitar controles al finalizar o fallar.

Las operaciones locales no necesitan pasar por la espera del proveedor.

## Errores tratados

Casos principales:

- falta de API Key para una función que sí necesita Gemini;
- autenticación 401/403;
- cuota/límite 429;
- solicitud inválida 400;
- indisponibilidad/saturación 503;
- timeout;
- red/DNS/conectividad;
- respuesta vacía o flujo de herramientas excesivo.

0.10.8 mantiene el mensaje de cuota y conserva información de reintento cuando el proveedor la ofrece.

## Configuración de API Key

La clave se gestiona desde Ajustes.

Propiedades:

- campo oculto por defecto;
- Mostrar/Ocultar;
- Guardar;
- Comprobar conexión;
- Eliminar;
- almacenamiento local fuera del ejecutable y de GitHub.

Una API Key no es necesaria para las operaciones que `AssistantLocalService` resuelve completamente de forma local.

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
- inventario de pinturas y compras asociadas;
- colección y estados de miniaturas compatibles con Ciros Paint.

## Tests 0.10.8

La CI final ejecutó **128 tests**, todos OK. Además de las comprobaciones heredadas de 0.10.7, 0.10.8 valida:

- resolución local fuzzy con confianza y rechazo de coincidencias inseguras;
- workflows deterministas reiniciables;
- autocompletado limitado a miniaturas poseídas al cambiar estado;
- compatibilidad con los contadores reales de estados;
- fallback de nombres de pinturas mediante una interacción sin tools;
- validación del contador diario persistente de requests Gemini;
- acción encadenada `Cambiar otra miniatura`;
- mantenimiento de exactamente siete tools de pinturas.

Smoke test funcional: **OK**.

Build Windows: **OK**.

Las baterías manuales y verificaciones históricas de 0.10.6 y 0.10.7 permanecen en el repositorio. Los datos finales de validación de 0.10.8 se registran en `CHANGELOG.md`.
