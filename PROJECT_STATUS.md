# Ciros Paint - Project Status

Última actualización: **19/08/2026**

## Versión actual

**Ciros Paint 0.9.2**

Estado: **build de Windows generado y verificado automáticamente; pendiente de validación final de reproducción real de YouTube en el equipo del usuario.**

Rama activa: `build/verify-0.9.2`

PR activo: `#13`

## Estado funcional

### Inventario y gestión

- Pinturas: operativo.
- Materiales: operativo.
- Compras: operativo.
- Miniaturas: operativo.
- Catálogo integrado de pinturas: operativo.
- Star Wars: Legion: operativo.
- Age of Sigmar: operativo.

### Tutoriales

- Búsqueda mediante YouTube Data API: operativa.
- Reproducción interna: corregida en 0.9.2 para el Error 153.
- Apertura externa en YouTube: disponible como fallback.

### Favoritos

Implementado en 0.9.1:

- carpeta `Miniaturas`;
- carpeta `Modelismo general`;
- banners visuales propios;
- clasificación automática al guardar;
- reclasificación manual;
- compatibilidad con favoritos existentes sin migración destructiva de la base de datos.

## Incidencia actual: YouTube Error 153

En 0.9.1 se observó el Error 153 al reproducir vídeos dentro de la aplicación.

Diagnóstico: el WebView de escritorio no estaba proporcionando a YouTube una identificación suficiente del cliente embebido.

Corrección aplicada en 0.9.2:

- uso de `QWebEngineHttpRequest`;
- encabezado `HTTP Referer` explícito;
- parámetro `origin`;
- parámetro `widget_referrer`;
- mantenimiento del botón `Abrir en YouTube` para vídeos cuyo propietario prohíba embeds.

## Verificación 0.9.2

GitHub Actions run funcional verificado: `32260154450`

Resultado: **success**

Comprobaciones superadas:

- reconstrucción 0.9.1 + overlay 0.9.2;
- instalación de dependencias;
- generación y verificación de catálogos y assets;
- suite de tests;
- test específico del Referer/identidad del reproductor;
- UI smoke test;
- PyInstaller;
- publicación de artefacto.

Artefacto: `CirosPaint-Windows-0.9.2`

Ejecutable: `CirosPaint_0.9.2.exe`

SHA256 del ejecutable:

`2dee6d3f6728c59c0057092886e41b805010951832fe3af86fa312fd07c2f7a6`

## Próximo paso

1. Ejecutar `CirosPaint_0.9.2.exe` en Windows.
2. Abrir el mismo vídeo que produjo Error 153 en 0.9.1.
3. Confirmar si la reproducción interna funciona.
4. Si funciona, considerar 0.9.2 validada en entorno real.
5. Si YouTube devuelve otro código, registrar el nuevo error por separado porque puede corresponder a restricciones de embed del propio vídeo.

## Persistencia de datos

Los datos locales permanecen fuera del ejecutable, bajo:

`%LOCALAPPDATA%\CirosPaint\`

La actualización del ejecutable no debe eliminar el inventario existente.
