# Consolidación Ciros Paint 0.9

La familia 0.9.x queda cerrada con el estado funcional validado manualmente de **0.9.4.1**.

Este estado se consolida en `main` como **Ciros Paint 0.9**, siguiendo la política del proyecto:

- `0.x.y` = revisiones internas de desarrollo y corrección.
- `0.x` = bloque cerrado y consolidado en `main`.

## Estado final incluido

- Buscador especializado de tutoriales mediante YouTube Data API.
- Filtro de idioma Todos / Español / Inglés.
- Identificación visual ES / EN / ? en las tarjetas de vídeo.
- Reproductor interno de YouTube mediante Qt WebEngine y página loopback local.
- Cierre completo del reproductor al cerrar el diálogo, sin audio residual en segundo plano.
- Favoritos organizados en Miniaturas y Modelismo general, con cambio manual de categoría.
- Persistencia local fuera del ejecutable.

## Validación final

La revisión interna 0.9.4.1 superó GitHub Actions y fue validada manualmente en Windows. Se confirmó que:

- la reproducción interna funciona;
- el filtrado por idioma funciona;
- los tags de idioma funcionan;
- cerrar el reproductor detiene inmediatamente vídeo y audio.

La siguiente etapa de desarrollo será **Ciros Paint 1.0**.
