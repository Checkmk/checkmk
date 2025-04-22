#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from marshmallow import Schema

class OneOfSchema(Schema):
    type_field: str
    type_field_remove: bool
    type_schemas: Mapping[str, type[Schema]]
    def get_obj_type(self, obj: Any) -> str: ...
    def get_data_type(self, data: dict[str, str]) -> str: ...
