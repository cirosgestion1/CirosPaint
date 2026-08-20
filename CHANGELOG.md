# Changelog - Ciros Paint

Este archivo resume la evolución reciente del proyecto. El repositorio conserva además los overlays/parches históricos utilizados para reconstruir cada versión.

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
