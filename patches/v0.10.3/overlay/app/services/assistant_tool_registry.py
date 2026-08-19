from __future__ import annotations

from app.services.assistant_contracts import AssistantToolDefinition


PAINT_TOOL_DEFINITIONS: tuple[AssistantToolDefinition, ...] = (
    AssistantToolDefinition(
        name="search_paints",
        description=(
            "Busca pinturas registradas en el inventario de Ciros Paint por texto, marca, nombre, "
            "código, gama, color o tipo. La base de datos local es la fuente de verdad."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
                "color": {"type": "string"},
                "paint_type": {"type": "string"},
                "only_in_stock": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    ),
    AssistantToolDefinition(
        name="get_paint_stock",
        description="Consulta si una pintura está registrada y cuántas unidades reales hay.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
            },
            "additionalProperties": False,
        },
    ),
    AssistantToolDefinition(
        name="find_paint_alternatives",
        description=(
            "Busca alternativas que el usuario ya posee para una pintura. Ciros Paint calcula tipo compatible, "
            "CIELAB/DeltaE y porcentaje; el modelo no inventa equivalencias."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "additionalProperties": False,
        },
    ),
    AssistantToolDefinition(
        name="add_paint_to_inventory",
        description=(
            "Añade unidades recién compradas de una pintura al inventario. Si ya existe suma unidades; "
            "si no existe localmente debe existir primero en el catálogo de Ciros Paint."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
            },
            "required": ["quantity"],
            "additionalProperties": False,
        },
        mutates_data=True,
    ),
    AssistantToolDefinition(
        name="set_paint_quantity",
        description=(
            "Establece la cantidad TOTAL indicada por el usuario para una pintura ya registrada. "
            "No debe confundirse con una compra que suma unidades."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 0},
            },
            "required": ["quantity"],
            "additionalProperties": False,
        },
        mutates_data=True,
    ),
    AssistantToolDefinition(
        name="add_paint_to_future_purchases",
        description=(
            "Añade una pintura del catálogo a Futuras compras reutilizando el sistema de compras de Ciros Paint "
            "y evitando duplicados."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "brand": {"type": "string"},
                "name": {"type": "string"},
                "code": {"type": "string"},
                "range_name": {"type": "string"},
                "quantity": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        mutates_data=True,
    ),
    AssistantToolDefinition(
        name="list_future_paint_purchases",
        description="Consulta las pinturas registradas actualmente en Futuras compras.",
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
)


PAINT_TOOL_NAMES = tuple(item.name for item in PAINT_TOOL_DEFINITIONS)


def get_paint_tool_definitions() -> list[dict]:
    return [item.as_dict() for item in PAINT_TOOL_DEFINITIONS]
