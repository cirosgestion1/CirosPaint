# Changelog - Ciros Paint

Este archivo resume la evolución reciente del proyecto. El repositorio conserva además los overlays/parches históricos utilizados para reconstruir cada versión.

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
