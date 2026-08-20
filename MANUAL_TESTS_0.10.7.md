# Ciros Paint 0.10.7 - Validación manual

Esta batería complementa los tests automáticos. Su objetivo principal es confirmar el comportamiento local-first del asistente y que Gemini se utiliza únicamente cuando la consulta no puede resolverse de forma determinista dentro de Ciros Paint.

## 1. Arranque y versión

- Abrir `CirosPaint_0.10.7.exe`.
- Confirmar que la aplicación inicia sin errores.
- Confirmar que los inventarios existentes siguen disponibles.
- Confirmar que la API Key de Gemini configurada anteriormente sigue disponible en Ajustes.

## 2. Consultas locales de pinturas - 0 tokens Gemini

Probar consultas simples que dependan exclusivamente de la base de datos local, por ejemplo:

- buscar una pintura concreta;
- consultar pinturas de una marca;
- consultar pinturas por color;
- consultar pinturas agotadas o casi agotadas;
- consultar Futuras compras.

Resultado esperado:

- respuesta inmediata desde Ciros Paint;
- indicación visual `Consulta local · 0 tokens Gemini`;
- no se realiza una petición a Gemini.

## 3. Autocompletado de pinturas

- Empezar a escribir el nombre, código o marca de una pintura conocida.
- Comprobar que aparecen sugerencias locales.
- Seleccionar una sugerencia y completar la consulta.

Resultado esperado:

- coincidencias obtenidas de la base de datos/catálogo local;
- no se necesita Gemini para generar las sugerencias.

## 4. Inventario y Futuras compras

Probar:

- añadir una pintura válida a Futuras compras;
- repetir la operación y comprobar que no se crean duplicados incompatibles;
- consultar después la lista;
- modificar cantidades mediante una petición local compatible.

Resultado esperado:

- la base de datos local refleja la operación;
- las operaciones deterministas no consumen tokens Gemini.

## 5. Miniaturas

Probar consultas/acciones compatibles con la colección local:

- localizar una miniatura por nombre;
- consultar miniaturas por estado;
- cambiar una miniatura a `Sin montar`, `Montado`, `Pintado` o `Terminado`;
- volver a consultar la colección.

Resultado esperado:

- Ciros Paint resuelve la identidad contra su catálogo/colección;
- los cambios se reflejan en la sección Miniaturas;
- las acciones locales no requieren Gemini cuando el nombre se puede resolver de forma segura;
- ante ambigüedad no se modifica información sin aclaración.

## 6. Consulta general con Gemini

Realizar una pregunta técnica abierta, por ejemplo un proceso de pintura que requiera explicación y no sea una simple lectura/escritura local.

Resultado esperado:

- se utiliza Gemini como fallback;
- la interfaz permanece operativa mientras se procesa la petición;
- la respuesta se muestra completa;
- se muestra información de consumo de la interacción cuando Gemini devuelve metadatos de uso;
- la solicitud usa el nivel de razonamiento reducido configurado para 0.10.7.

## 7. Contexto de conversación

- Realizar una consulta con Gemini.
- Formular una segunda pregunta que dependa de la anterior.

Resultado esperado:

- se conserva el contexto temporal de esa conversación;
- no se crea memoria persistente al cerrar Ciros Paint;
- las llamadas continúan usando `store=False`.

## 8. Markdown y mensajes largos

Solicitar una respuesta con pasos, listas o apartados.

Resultado esperado:

- listas y formato Markdown se muestran correctamente;
- los mensajes largos no quedan truncados;
- el texto puede seleccionarse.

## 9. Imágenes

- Adjuntar una imagen PNG/JPEG/WebP relacionada con pintura/modelismo.
- Comprobar la previsualización/miniatura en el chat.
- Enviar la consulta.

Resultado esperado:

- la imagen aparece representada visualmente en la conversación;
- Gemini recibe la imagen únicamente cuando la consulta necesita el proveedor;
- imágenes grandes se preparan para envío inline sin bloquear la UI.

## 10. Errores Gemini

Comprobar, cuando sea posible:

- API Key incorrecta;
- desconexión de Internet;
- timeout;
- cuota/límite 429.

Resultado esperado:

- error legible para el usuario;
- la conversación no bloquea la aplicación;
- después del error se puede volver a enviar otra consulta;
- un 429 se identifica como límite de uso y no como fallo genérico.

## 11. Persistencia tras actualización

Cerrar 0.10.7 y volver a abrirla.

Resultado esperado:

- inventario, materiales, compras y miniaturas persisten;
- las conversaciones del asistente no persisten;
- la actualización del ejecutable no sustituye `%LOCALAPPDATA%\\CirosPaint\\ciros_paint.db`.
