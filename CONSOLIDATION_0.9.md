# Consolidación Ciros Paint 0.9

> **Documento histórico.** Esta consolidación describe el cierre de la familia 0.9. El estado actual del proyecto está documentado en `README.md` y `PROJECT_STATUS.md` y corresponde a la familia 0.10, con **Ciros Paint 0.10.6** como última versión validada a 20/08/2026.

La familia 0.9.x quedó cerrada con el estado funcional validado manualmente de **0.9.4.1**.

Este estado se consolidó en `main` como **Ciros Paint 0.9**, siguiendo la política vigente en ese momento:

- `0.x.y` = revisiones internas de desarrollo y corrección.
- `0.x` = bloque cerrado y consolidado en `main`.

## Estado final incluido en 0.9

- Buscador especializado de tutoriales mediante YouTube Data API.
- Filtro de idioma Todos / Español / Inglés.
- Identificación visual ES / EN / ? en las tarjetas de vídeo.
- Reproductor interno de YouTube mediante Qt WebEngine y página loopback local.
- Cierre completo del reproductor al cerrar el diálogo, sin audio residual en segundo plano.
- Favoritos organizados en Miniaturas y Modelismo general, con cambio manual de categoría.
- Persistencia local fuera del ejecutable.

## Validación final de 0.9

La revisión interna 0.9.4.1 superó GitHub Actions y fue validada manualmente en Windows. Se confirmó que:

- la reproducción interna funciona;
- el filtrado por idioma funciona;
- los tags de idioma funcionan;
- cerrar el reproductor detiene inmediatamente vídeo y audio.

## Evolución posterior

La planificación cambió después de cerrar 0.9: antes de 1.0 se abrió la familia **0.10**, dedicada principalmente al análisis de pinturas en Favoritos y al desarrollo de Ciros Assistant.

Consultar `CHANGELOG.md` para la evolución 0.10.1 -> 0.10.6.
