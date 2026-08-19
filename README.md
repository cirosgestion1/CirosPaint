# Ciros Paint

Aplicación de escritorio local para gestionar pinturas, materiales, compras, miniaturas y tutoriales de modelismo.

## Estado actual

Versión actual de desarrollo y verificación: **0.9.2**.

Rama activa de verificación:

`build/verify-0.9.2`

Pull request activo:

`#13 - Ciros Paint 0.9.2 - fix YouTube Error 153`

## Funcionalidad disponible

- Inventario de pinturas con catálogo integrado.
- Gestión de materiales y lista de compras.
- Gestión de miniaturas de Star Wars: Legion y Age of Sigmar.
- Estados de miniaturas: Sin montar, Montado, Pintado y Terminado.
- Buscador de tutoriales mediante YouTube Data API.
- Favoritos organizados automáticamente en dos carpetas visuales:
  - Miniaturas.
  - Modelismo general.
- Cambio manual de categoría para cualquier favorito.
- Reproductor interno de YouTube mediante Qt WebEngine.

## Ciros Paint 0.9.2

La 0.9.2 corrige el **Error 153 de YouTube** observado al intentar reproducir vídeos dentro de Ciros Paint 0.9.1.

La corrección modifica el reproductor embebido para identificar correctamente la aplicación ante YouTube mediante `HTTP Referer`, `origin` y `widget_referrer`.

La implementación ha superado:

- reconstrucción completa de la aplicación desde la cadena de versiones almacenada en el repositorio;
- suite de tests;
- test específico de identidad/Referer del reproductor de YouTube;
- smoke test de interfaz;
- compilación con PyInstaller para Windows;
- publicación del artefacto `CirosPaint-Windows-0.9.2`.

La validación definitiva de reproducción real de YouTube queda pendiente de probar la 0.9.2 en un equipo Windows de usuario, ya que GitHub Actions verifica la petición y la interfaz pero no reproduce un vídeo real en una sesión gráfica interactiva.

## Build de Windows verificado

Workflow run funcional verificado: `32260154450`

Artefacto: `CirosPaint-Windows-0.9.2`

Ejecutable: `CirosPaint_0.9.2.exe`

SHA256:

`2dee6d3f6728c59c0057092886e41b805010951832fe3af86fa312fd07c2f7a6`

## Datos locales

La aplicación guarda los datos fuera del ejecutable en:

`%LOCALAPPDATA%\CirosPaint\`

La base de datos principal se encuentra en:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

Por tanto, sustituir el ejecutable por una versión nueva no elimina ni reemplaza el inventario local.

## Política actual de ramas

Las versiones verificadas se desarrollan y prueban en ramas `build/verify-*`. La rama `main` permanece sin fusionar automáticamente mientras se valida el comportamiento real de cada versión.
