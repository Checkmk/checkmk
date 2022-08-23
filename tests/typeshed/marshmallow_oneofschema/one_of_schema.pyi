from collections.abc import Mapping
from typing import Any, Type

from marshmallow import Schema


class OneOfSchema(Schema):
    type_field: str
    type_field_remove: bool
    type_schemas: Mapping[str, Type[Schema]]
    def get_obj_type(self, obj: Any) -> str: ...
    def get_data_type(self, data: dict[str, str]) -> str: ...
