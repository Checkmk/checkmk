#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import final, Literal, override

from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import CoreSchema


@final
class JsonSchema(GenerateJsonSchema):
    """
    Custom schema generator to include $schema dialect
    """

    @override
    def generate(
        self, schema: CoreSchema, mode: Literal["validation", "serialization"] = "validation"
    ) -> JsonSchemaValue:
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema
