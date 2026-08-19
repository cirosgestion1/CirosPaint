# Ciros Paint

Aplicación de escritorio local-first para Windows destinada a gestionar pinturas, materiales, compras, miniaturas y recursos del hobby de pintura de miniaturas y modelismo.

Actualmente incluye soporte de miniaturas para **Star Wars: Legion** y **Warhammer Age of Sigmar**, además de la Biblioteca de tutoriales de YouTube y Favoritos.

## Estado actual

Versión de desarrollo: **0.9.4**.

Rama activa de desarrollo/verificación:

`build/verify-0.9.4`

Pull Request activo:

`#15 - Ciros Paint 0.9.4 - YouTube loopback player + bilingual filter`

### Ciros Paint 0.9.4

La versión 0.9.4 incorpora:

- filtro de tutoriales **Todos / Español / Inglés** rehecho;
- búsquedas localizadas en español e inglés;
- comprobación posterior del idioma del vídeo;
- tag visual **ES / EN / ?** en las tarjetas de resultados;
- nueva estrategia de reproducción interna de YouTube mediante una página local servida en `localhost / 127.0.0.1`;
- mantenimiento de **Abrir en YouTube** como alternativa externa.

La compilación de Windows de la 0.9.4 ha superado:

- reconstrucción del proyecto;
- suite completa de tests;
- pruebas del filtro bilingüe;
- pruebas de detección y tag de idioma;
- prueba del servidor loopback local;
- smoke test de interfaz;
- compilación con PyInstaller.

**Pendiente:** validar manualmente en Windows la reproducción real del mismo vídeo de YouTube que produjo Error 153 / bloqueo de Chromium en versiones anteriores. La reproducción interna no se considera cerrada hasta superar esa prueba real.

El código de la 0.9.4 todavía **no está fusionado en `main`**. El PR permanece en estado draft mientras continúa la validación.

## Datos locales

Los datos del usuario se almacenan fuera del ejecutable en:

`%LOCALAPPDATA%\CirosPaint\`

La base de datos principal se encuentra en:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

De este modo, sustituir o actualizar el ejecutable no elimina ni sobrescribe el inventario local del usuario.

## Build de Windows

El repositorio utiliza GitHub Actions y PyInstaller para generar el ejecutable autocontenido de Windows.

Build verificado actual:

`CirosPaint_0.9.4.exe`

Artefacto de GitHub Actions:

`CirosPaint-Windows-0.9.4`

SHA256 del ejecutable verificado:

`2f7d3275dc9b083d7d6eddcb7bcaf6556cfc10e632126306e8657cd45fdc5c5d`
