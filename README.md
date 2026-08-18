# Ciros Paint

Aplicación de escritorio local para gestionar pinturas, materiales y miniaturas de Star Wars: Legion y Warhammer Fantasy.

## Estado actual

Versión de desarrollo: **0.2**.

El repositorio incluye un workflow de GitHub Actions que compila automáticamente una versión autocontenida para Windows con PyInstaller. El resultado se publica como artefacto `CirosPaint-Windows` y contiene `CirosPaint.exe`.

## Datos locales

La aplicación guarda el inventario fuera del ejecutable en:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

De este modo, actualizar el ejecutable no sustituye el inventario local.
