# Ciros Paint 0.10.6 - Validación manual

Batería recomendada para validar la primera versión funcional de Ciros Assistant con una API Key real de Gemini.

> Los tests automáticos de CI no utilizan una API Key real ni consumen cuota.

## 1. Arranque y regresión

- [ ] El EXE abre normalmente.
- [ ] La versión visible es 0.10.6.
- [ ] Inventario, Favoritos, Miniaturas, Compras y Ajustes siguen disponibles.
- [ ] `Ajustes -> Base de datos local -> Abrir ubicación` abre la ubicación correcta.
- [ ] La configuración de YouTube sigue disponible.

## 2. Gemini en Ajustes

- [ ] La API Key aparece oculta por defecto.
- [ ] Mostrar/Ocultar funciona.
- [ ] Guardar conserva la clave localmente.
- [ ] La clave continúa disponible tras cerrar y volver a abrir la aplicación.
- [ ] `Comprobar conexión` devuelve conexión correcta con una clave válida.
- [ ] Una clave deliberadamente incorrecta produce un error de autenticación comprensible.
- [ ] Eliminar clave borra la configuración local.

## 3. Chat básico

Consulta sugerida:

`¿Cómo pintarías una armadura negra?`

- [ ] Se obtiene una respuesta real de Gemini.
- [ ] No aparece el placeholder de 0.10.5.
- [ ] Mientras responde se muestra el estado de espera.
- [ ] La aplicación no se congela.
- [ ] El botón Enviar vuelve a habilitarse al terminar.

## 4. Alcance

Consulta fuera de ámbito:

`¿Cuál es la capital de Australia?`

- [ ] El asistente explica brevemente que está especializado en pintura/modelismo.

## 5. Contexto dentro de una conversación

1. `Quiero pintar una armadura negra con luces azuladas.`
2. `¿Y cómo harías las luces?`

- [ ] La segunda respuesta mantiene el contexto de la primera.

Crear después una nueva conversación y preguntar:

`¿Qué color te dije que quería para las luces?`

- [ ] La nueva conversación no hereda el contexto anterior.

## 6. Temporalidad

- [ ] Crear varias conversaciones mantiene contextos separados.
- [ ] Eliminar una conversación funciona.
- [ ] Cerrar Ciros Paint elimina el historial conversacional.
- [ ] Al volver a abrir no aparecen conversaciones anteriores.

## 7. Consulta de inventario

Elegir una pintura cuya existencia y cantidad sean conocidas.

- [ ] `¿Tengo [pintura]?` coincide con el inventario.
- [ ] `¿Cuántas unidades tengo de [pintura]?` coincide exactamente.
- [ ] `¿Qué pinturas grises tengo?` devuelve únicamente pinturas locales compatibles.
- [ ] `¿Qué pinturas AK tengo?` respeta la marca.
- [ ] No inventa productos ausentes del inventario.

## 8. Contexto + inventario

1. `¿Cuántas unidades tengo de [pintura]?`
2. `¿Y qué alternativas tengo para ella?`

- [ ] La segunda pregunta mantiene la referencia a la pintura anterior.

## 9. Alternativas

- [ ] Una pintura con alternativas compatibles devuelve solo pinturas que el usuario posee.
- [ ] Las alternativas respetan el tipo compatible.
- [ ] No inventa equivalencias cuando no existe ninguna por encima del criterio de Ciros Paint.

## 10. Compra: sumar unidades

Anotar la cantidad previa.

Ejemplo:

`He comprado 2 unidades de [pintura].`

- [ ] La cantidad final aumenta en +2.
- [ ] La respuesta refleja la operación realizada.

## 11. Establecer cantidad total

Ejemplo:

`Ahora tengo 4 unidades de [pintura].`

- [ ] El total final queda exactamente en 4.
- [ ] No suma 4 a la cantidad anterior.

## 12. Escritura ambigua

Ejemplo deliberadamente impreciso:

`Añade una unidad de Grey.`

- [ ] Si existen varias coincidencias plausibles, pide aclaración.
- [ ] Ninguna cantidad cambia antes de recibir la aclaración.

## 13. Pintura inexistente

Pedir una pintura con un nombre ficticio.

- [ ] No crea una pintura inventada.
- [ ] Indica que no puede identificarla en el catálogo.

## 14. Futuras compras

- [ ] `Añade [pintura] a futuras compras` crea/reutiliza la entrada correcta.
- [ ] Repetir la instrucción no genera duplicados.
- [ ] `¿Qué pinturas tengo en futuras compras?` coincide con la pantalla local.

## 15. Imagen + texto

Adjuntar una foto clara relacionada con pinturas/modelismo.

Pregunta sugerida:

`¿Qué puedes identificar en esta imagen?`

- [ ] Gemini utiliza el contenido visual.
- [ ] No se limita al nombre del archivo.

## 16. Solo imagen

- [ ] Adjuntar imagen sin texto y pulsar Enviar funciona.
- [ ] Se obtiene una respuesta visualmente contextualizada.

## 17. Imagen + inventario

Pregunta sugerida:

`Identifica esta pintura y dime si tengo algo parecido en mi inventario.`

- [ ] Gemini analiza la imagen.
- [ ] Cuando necesita inventario usa las herramientas locales.
- [ ] La respuesta final solo menciona inventario real.

## 18. Eliminar adjunto

- [ ] Adjuntar imagen.
- [ ] Pulsar `×`.
- [ ] Enviar texto.
- [ ] La imagen eliminada no forma parte de la consulta.

## 19. Formatos

- [ ] JPG funciona.
- [ ] PNG funciona.
- [ ] WebP funciona si está disponible.
- [ ] BMP/otro formato compatible se convierte o produce un error controlado.

## 20. Sin Internet

- [ ] Desconectar Internet.
- [ ] Enviar una consulta.
- [ ] Aparece un error de conexión comprensible.
- [ ] La aplicación no se cierra ni se bloquea.
- [ ] Tras reconectar, una nueva consulta vuelve a funcionar.

## 21. API Key incorrecta

- [ ] Una clave incorrecta genera error de autenticación.
- [ ] El chat no queda permanentemente bloqueado.

## 22. Cuota 429

No es necesario provocar el límite artificialmente.

Si ocurre durante uso real:

- [ ] Ciros Paint muestra un mensaje de límite/cuota.
- [ ] La aplicación sigue operativa.

## 23. Navegación durante una respuesta

- [ ] Enviar una consulta.
- [ ] Cambiar de conversación mientras Gemini responde.
- [ ] La UI permanece fluida.
- [ ] La respuesta se asocia a la conversación que originó la petición.

## 24. Eliminar conversación durante petición

- [ ] Enviar una consulta.
- [ ] Eliminar la conversación antes de recibir la respuesta.
- [ ] La aplicación no se cierra.
- [ ] La respuesta no se inserta incorrectamente en otra conversación.

## 25. Persistencia correcta

- [ ] Modificar inventario mediante el asistente.
- [ ] Cerrar Ciros Paint.
- [ ] Volver a abrir.
- [ ] El cambio de inventario persiste.
- [ ] La conversación no persiste.

## 26. Regresión final

- [ ] Inventario operativo.
- [ ] Materiales operativos.
- [ ] Futuras compras operativas.
- [ ] Miniaturas operativas.
- [ ] Favoritos operativos.
- [ ] Buscador YouTube operativo.
- [ ] Ajustes operativos.
- [ ] Cierre de la aplicación normal.

## Formato recomendado para reportar resultados

```text
1 ✅
2 ✅
3 ✅
4 ❌ - Texto exacto del error/respuesta
...
17 ❌ - Identifica la imagen pero no consulta inventario
...
26 ✅
```

En cualquier fallo conviene adjuntar:

- consulta exacta;
- respuesta exacta;
- pintura implicada si aplica;
- cantidad antes/después si hubo escritura;
- captura de pantalla cuando el problema sea visual.
