# Changelog - Ciros Paint

Este archivo resume la evolución reciente del proyecto. El repositorio conserva además los overlays/parches históricos utilizados para reconstruir cada versión.

## 0.10.10 - En desarrollo

### Añadido

- `CentralizedQueryService`, fachada read-only sobre los repositories y catálogos existentes.
- Consultas centralizadas de catálogo/inventario/stock de pinturas, Futuras compras, colección y catálogo de miniaturas.
- Filtros de miniaturas por posesión y estado sin cambios de esquema.
- Tests de equivalencia entre la nueva fachada y los repositories existentes.

### Refactor

- `AssistantPaintService` y `AssistantLocalService` delegan lecturas compatibles al Query Service.
- Las páginas de pinturas, compras y miniaturas usan la fachada para sus listados principales.
- El listado de Futuras compras reutiliza `entry.paint` cargado por `ShoppingRepository` y evita recargar todo el inventario.

### Validación local

- Reconstrucción completa 0.10.10: **OK**.
- Sin cambios de esquema ni migraciones.

## 0.10.9 - 21/08/2026

Primera fase funcional del siguiente bloque local-first, construida sobre la versión validada 0.10.8.

### Añadido

- `AssistantLocalIntentRouter`, con clasificación y despacho explícitos para búsquedas/stock de pinturas, pinturas agotadas o por color, Futuras compras, miniaturas y cambios de estado.
- `ConfidenceEscalationGateway`, con una política común para coincidencia exacta, normalizada, fuzzy segura, selección ambigua y escalado solo cuando la resolución local es insuficiente.
- Tests de caracterización que prueban operaciones deterministas sin API key ni incremento del contador Gemini y bloquean mutaciones ambiguas.

### Corregido

- `Buscar pintura: Gris` se resuelve mediante búsqueda local y deja de caer innecesariamente en Gemini.
- Las consultas explícitas de unidades de pintura tienen precedencia sobre el patrón genérico de conteo de miniaturas.

### Validación local

- Reconstrucción reproducible completa hasta 0.10.9: **OK**.
- **137 tests: OK**.
- Smoke test PySide6 offscreen: **OK**.
- Sin cambios de esquema ni migraciones de base de datos.

### Validación CI

- GitHub Actions run `32489725696`: **SUCCESS**.
- **137 tests: OK**.
- Smoke PySide6, PyInstaller y artifact upload: **OK**.
- Ejecutable: `CirosPaint_0.10.9.exe`.
- SHA-256 EXE: `d02c860d946a674a6d844a62395d007ab749d8ee86c2aa833d3014e2eb7524a8`.
- Artefacto: `CirosPaint-Windows-0.10.9`, ID `9449420362`.

## 0.10.8 - 21/08/2026

Refuerzo de la arquitectura local-first de Ciros Assistant para automatizar más operaciones sin Gemini.

### Añadido

- `LocalEntityResolver` con normalización, coincidencia aproximada y control de confianza.
- `AssistantWorkflowEngine` para flujos guiados y repetibles.
- Autocompletado contextual de miniaturas: al cambiar estado se muestran solo unidades ya presentes en la colección; al añadir miniaturas se mantiene el catálogo completo.
- Confirmaciones precisas de cambios de estado con cantidad, unidad y estado final.
- Acción `Cambiar otra miniatura` para repetir el workflow dentro de la misma conversación.
- Fallback automático a Gemini cuando una pintura o miniatura no puede resolverse localmente con seguridad.
- Validación posterior contra el catálogo/base local para impedir que Gemini invente entidades.
- Contador diario persistente de requests reales a Gemini visible en Ajustes.
- Compatibilidad corregida con los contadores reales de miniaturas `unassembled_count`, `assembled_count`, `painted_count` y `finished_count`.

### Validación

- **128 tests: OK**.
- Smoke test funcional de 0.10.8: **OK**.
- GitHub Actions run `32475688035`: **SUCCESS**.
- Overlay SHA-256: `d85dc1f7c9b168890f9f03d4f5973979fbafe73ff2712fbf7428d628ce09e860`.
- EXE: `CirosPaint_0.10.8.exe`.
- Tamaño EXE: `244399034` bytes.
- SHA-256 EXE: `39f2bf097cf252cf94740428ee5b4d4f589b0bf487d42236bc3396ef22d6be38`.
- Artefacto: `CirosPaint-Windows-0.10.8`, ID `9444337506`.

### Infraestructura de reconstrucción

- Reconstrucción histórica centralizada en `tools/rebuild_current.ps1`.
- Los overlays se aplican primero en staging y `build_source/` solo se reemplaza de forma segura con `-Force`.
- Los ZIP derivados se generan temporalmente sin modificar `source/` ni `patches/`.
- Los workflows de Windows reutilizan el script y mantienen dependencias, catálogos, assets, tests, smoke test, PyInstaller y artefactos como fases separadas.

## 0.10.7 - 20/08/2026

Optimización local-first de Ciros Assistant y ampliación de su integración con Ciros Paint.

### Añadido

- `AssistantLocalService` para resolver operaciones deterministas sin consumir Gemini.
- Consultas locales de pinturas, stock, agotadas/casi agotadas y Futuras compras.
- Búsqueda y actualización local de miniaturas y sus estados: Sin montar, Montado, Pintado y Terminado.
- Resolución específica de nombres de miniaturas cuando hace falta interpretación adicional.
- Autocompletado local de pinturas mediante `QCompleter`.
- Visualización `Consulta local · 0 tokens Gemini` cuando la petición no usa el proveedor.
- Registro y presentación del consumo de tokens cuando Gemini devuelve metadatos de uso.
- Renderizado Markdown y soporte de respuestas largas sin truncado.
- Mejoras visuales para imágenes adjuntas en el chat.
- Batería manual específica `MANUAL_TESTS_0.10.7.md`.

### Optimización de Gemini

- Gemini pasa a ser fallback para consultas que no pueden resolverse localmente.
- `thinking_level="low"` en las llamadas del asistente y en la comprobación de conexión.
- Consultas generales sin exponer tools cuando no son necesarias.
- Las operaciones que realmente requieren function calling mantienen exactamente las siete herramientas controladas de pinturas.
- El resolvedor de miniaturas usa una llamada separada sin tools.
- El historial enviado al proveedor se limita a los turnos recientes necesarios.
- Mensajes de cuota 429 mejorados, incluyendo información de reintento cuando está disponible.

### Validación

- **115 tests: OK**.
- Smoke test funcional de 0.10.7: **OK**.
- GitHub Actions run `32397932655`: **SUCCESS**.
- Overlay SHA-256: `062ae2b06e881f1d243b3ae7a4cbe150d889b46fb938f98735bd45c2def89f1b`.
- EXE: `CirosPaint_0.10.7.exe`.
- Tamaño EXE: `244382691` bytes.
- SHA-256 EXE: `ba333211e9684efd4ffb0a03175aeeb55afd152d32e7e4aef1cbae7d98a2f50e`.
- Artefacto: `CirosPaint-Windows-0.10.7`, ID `9417510361`.

## 0.10.6 - 20/08/2026

Primera versión funcional de Ciros Assistant con Gemini.

### Añadido

- Integración oficial `google-genai` 2.3+.
- Modelo configurado inicialmente: `gemini-3.7-flash`.
- Interactions API con `store=False`.
- Historial de proveedor mantenido únicamente en RAM.
- Function calling con las siete herramientas locales de pinturas.
- Entrada multimodal con imagen + texto.
- Conversión/preparación de imágenes para envío inline cuando es necesario.
- Comprobación real de conexión desde Ajustes.
- Ejecución asíncrona con Qt para evitar bloquear la interfaz.
- Tratamiento específico de autenticación, cuota 429, timeout, red, solicitud inválida e indisponibilidad 503.
- Tests del servicio Gemini con cliente simulado para no consumir cuota en CI.

### Validación

- 113 tests: OK.
- Smoke test funcional: OK.
- GitHub Actions run `32382923636`: SUCCESS.
- EXE: `CirosPaint_0.10.6.exe`.
- SHA-256: `58c3ae2560c9afeda18dc4a9c49466ebfe8c9abf14f80b4f81d75d5019bf1aa0`.

## 0.10.5 - 20/08/2026

Reorganización y corrección visual del asistente.

### Cambios

- Configuración de Gemini movida desde Asistente a Ajustes.
- Bloque Gemini API junto a YouTube Data API.
- Botón `Abrir ubicación` en Base de datos local.
- Eliminación del texto auxiliar de imágenes junto al botón de adjuntar.
- Eliminación de la lista lateral `Puede trabajar con`.
- Botón informativo `ⓘ` con diálogo detallado sobre capacidades y límites.
- Corrección del bug del botón Enviar.
- Test de pulsación real del botón después de procesar el event loop de Qt.

## 0.10.4

Primera implementación visual completa de Ciros Assistant.

### Añadido

- Panel lateral de conversaciones temporales.
- Creación/eliminación de conversaciones.
- Chat con burbujas de usuario/asistente.
- Composer de texto.
- Adjuntar/eliminar imágenes.
- Configuración visual de Gemini.
- Almacenamiento local de API Key.
- Pantalla de bienvenida y prompts rápidos.

En esta versión Gemini todavía no realizaba llamadas reales.

## 0.10.3

Fundación técnica provider-neutral de Ciros Assistant.

### Añadido

- Contratos JSON compatibles para herramientas/resultados.
- Registro inicial de siete herramientas de pinturas.
- `AssistantPaintService` sin dependencia del proveedor de IA.
- Base de datos local como fuente de verdad.
- Búsquedas de inventario por texto, marca, nombre, código, gama, color y tipo.
- Consulta de stock.
- Alternativas mediante CIELAB/DeltaE, tipo compatible y umbral >=85 %.
- Diferenciación entre añadir unidades compradas y establecer cantidad total.
- Futuras compras reutilizando `ShoppingRepository`.
- Protección ante ambigüedad y pinturas inexistentes.
- Conversaciones temporales solo en memoria.
- Reglas de alcance del asistente.

## 0.10.2

Mejoras del análisis de pinturas de Favoritos.

### Cambios principales

- Umbral mínimo de alternativa visible fijado en 85 %.
- Descarte de posibles coincidencias por debajo del umbral.
- Estado claro cuando no se detectan pinturas.
- Integración de pinturas ausentes con Futuras compras.
- Reutilización de entradas existentes para evitar duplicados.

## 0.10.1

Introducción del análisis de pinturas en tutoriales favoritos de Miniaturas.

### Añadido

- Detección de pinturas en contenido del tutorial.
- Coincidencias con inventario local.
- Posibles coincidencias separadas de las exactas.
- Alternativas calculadas por color.
- Interfaz de resultados dividida en secciones visuales.

## 0.9.4.1

Corrección del cierre del reproductor interno de YouTube para asegurar que vídeo y audio se detienen completamente al cerrar el diálogo.

## 0.9.4

Mejoras del filtro de idiomas del Buscador de tutoriales y consultas bilingües contextualizadas.

## 0.9.3

Revisión del reproductor interno y metadatos de idioma.

## 0.9

Bloque consolidado de inventario, materiales, compras, miniaturas, tutoriales y favoritos sobre el que se construye la familia 0.10.
