# Ciros Paint

Aplicación de escritorio local-first para Windows destinada a gestionar pinturas, materiales, miniaturas y recursos del hobby de pintura y modelismo.

## Rama `main`

**Línea estable consolidada: Ciros Paint 0.8**.

La rama `main` conserva únicamente los bloques principales `0.x` ya cerrados. Las revisiones internas `0.x.y` se desarrollan y validan en ramas separadas y, cuando se cierra el bloque, su estado final se consolida en `main` bajo `0.x`.

Ejemplo de la política de versiones:

- `0.8.1`, `0.8.2`, `0.8.3`, `0.8.3.1` → iteraciones internas del bloque 0.8.
- `main` → estado consolidado **0.8**.
- `0.9.0`, `0.9.1`, `0.9.2`, `0.9.3`, `0.9.4` → desarrollo actual del bloque 0.9, todavía fuera de `main`.
- Cuando el bloque 0.9 quede cerrado, `main` avanzará a **0.9**.

El estado funcional consolidado de 0.8 corresponde al último estado validado de la familia 0.8, incluido el hotfix final que manejábamos como `0.8.3.1`.

## Estado de desarrollo actual

El desarrollo activo continúa en:

- Rama: `build/verify-0.9.4`
- PR de verificación: **#15**

La serie 0.9 está dedicada principalmente a la Biblioteca inteligente, Buscador de tutoriales, Favoritos y sus correcciones/pulido. No se incorporará a `main` hasta que consideremos cerrado el bloque 0.9.

## Bloques cerrados en 0.8

- Pinturas
- Materiales
- Compras
- Miniaturas
  - Star Wars: Legion
  - Warhammer Age of Sigmar

El módulo de Miniaturas se considera cerrado para la 1.0 salvo errores importantes.

## Datos locales

Los datos del usuario permanecen fuera del ejecutable en:

`%LOCALAPPDATA%\CirosPaint\`

La base de datos principal se encuentra en:

`%LOCALAPPDATA%\CirosPaint\ciros_paint.db`

Actualizar el ejecutable no debe sustituir ni borrar el inventario local.

## Build de Windows

GitHub Actions reconstruye la línea estable a partir de las fuentes y overlays verificados y genera un ejecutable autocontenido mediante PyInstaller.

En `main`, el workflow reconstruye el estado final validado de la familia 0.8. Las ramas `build/verify-*` tienen sus propios workflows para comprobar las versiones en desarrollo antes de consolidarlas.
