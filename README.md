# Ciros Paint

Aplicación de escritorio local-first para Windows destinada a gestionar pinturas, materiales, compras, miniaturas y recursos del hobby de pintura y modelismo.

## Estado del proyecto

La familia **0.9.x está finalizada**.

Última revisión interna validada: **0.9.4.1**.

Estado consolidado actualmente en `main`: **Ciros Paint 0.9**.

Siguiente etapa de desarrollo: **Ciros Paint 1.0**.

## Funcionalidad consolidada hasta 0.9

- Inventario de pinturas con catálogo integrado.
- Gestión de materiales y lista de compras.
- Gestión de miniaturas de Star Wars: Legion y Warhammer Age of Sigmar.
- Estados de miniaturas: Sin montar, Montado, Pintado y Terminado.
- Buscador especializado de tutoriales mediante YouTube Data API.
- Filtro de idioma: Todos / Español / Inglés.
- Tags ES / EN / ? en las tarjetas de vídeo.
- Reproductor interno de YouTube mediante Qt WebEngine y página loopback local.
- Cierre completo de la sesión del reproductor al cerrar el diálogo, sin audio residual en segundo plano.
- Favoritos organizados en Miniaturas y Modelismo general.
- Cambio manual de categoría de favoritos.

## Validación final de la familia 0.9

La revisión **0.9.4.1** superó GitHub Actions y fue probada manualmente en Windows.

Se confirmó en entorno real que:

- la reproducción interna de YouTube funciona;
- el filtrado Todos / Español / Inglés funciona;
- los tags de idioma funcionan;
- al cerrar el reproductor, el vídeo y el audio se detienen inmediatamente.

## Política de versiones

- Las revisiones `0.x.y` se utilizan para desarrollo, correcciones y validación interna.
- Cuando un bloque queda cerrado, su último estado validado se consolida en `main` como `0.x`.
- La cadena consolidada actual queda: `0.8` → `0.9`.
- El próximo objetivo es **1.0**.

## Datos locales

Los datos del usuario se guardan fuera del ejecutable en:

`%LOCALAPPDATA%\CirosPaint\`

Base de datos principal:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

Actualizar el ejecutable no debe sustituir ni borrar el inventario local.
