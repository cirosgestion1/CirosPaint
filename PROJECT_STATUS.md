# Ciros Paint - Project Status

Última actualización: **19/08/2026**

## Estado actual

Familia cerrada: **Ciros Paint 0.9.x**

Última revisión interna validada: **0.9.4.1**

Estado a consolidar en `main`: **Ciros Paint 0.9**

Siguiente objetivo de desarrollo: **Ciros Paint 1.0**

## Validación final

La revisión 0.9.4.1 superó GitHub Actions y fue validada manualmente en Windows.

Confirmado en uso real:

- reproducción interna de YouTube operativa;
- filtro Todos / Español / Inglés operativo;
- tags de idioma ES / EN / ? operativos;
- Favoritos operativos;
- al cerrar el diálogo del reproductor, vídeo y audio se detienen completamente;
- persistencia local conservada fuera del ejecutable.

## Módulos consolidados

### Pinturas

Operativo y considerado cerrado para la 1.0 salvo errores importantes.

### Materiales

Operativo y considerado cerrado para la 1.0 salvo errores importantes.

### Compras

Operativo y considerado cerrado para la 1.0 salvo errores importantes.

### Miniaturas

Operativo para Star Wars: Legion y Warhammer Age of Sigmar, con estados Sin montar / Montado / Pintado / Terminado.

### Biblioteca y tutoriales

- Buscador especializado mediante YouTube Data API.
- Contextualización de búsquedas hacia pintura/modelismo.
- Filtro de idioma Todos / Español / Inglés.
- Identificación visual ES / EN / ?.
- Reproductor interno con Qt WebEngine sobre página loopback local.
- Apertura externa en YouTube disponible.
- Favoritos organizados en Miniaturas y Modelismo general.
- Cambio manual de categoría.

## Incidencias resueltas durante 0.9.x

- Error 153 de YouTube en WebView.
- Bloqueo de Chromium con origen remoto artificial.
- Sesgo incorrecto del filtro de idioma hacia español.
- Audio del reproductor continuando en segundo plano tras cerrar la ventana.

## Build final validado de la revisión interna

GitHub Actions run: `32271003247`

Artefacto: `CirosPaint-Windows-0.9.4.1`

Ejecutable validado: `CirosPaint_0.9.4.1.exe`

SHA256:

`484b409ffcddea3528e04d66a3bd8f4e3e365b70f4571a116d86507a57047d46`

## Política de ramas y versiones

Las revisiones `0.x.y` son iteraciones internas. Cuando se cierra una familia, su estado final se consolida en `main` bajo `0.x`.

Con la familia 0.9 cerrada, `main` pasa a representar **Ciros Paint 0.9**. El siguiente bloque será **1.0**.

## Persistencia de datos

Los datos locales permanecen bajo:

`%LOCALAPPDATA%\CirosPaint\`

La actualización del ejecutable no debe eliminar el inventario existente.
