#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from marshmallow_oneofschema import OneOfSchema

from cmk.gui.openapi.endpoints.global_settings.schemas import (
    CAInputSchema,
    FileUploadSchema,
    IconSchema,
)


@pytest.mark.parametrize(
    "schema, data",
    [
        (IconSchema(), {"type": "enabled", "icon": "delete"}),
        (IconSchema(), {"type": "enabled", "icon": "delete", "emblem": "search"}),
        (IconSchema(), {"type": "disabled"}),
        (CAInputSchema(), {"type": "enabled", "address": "localhost", "port": 443}),
        (CAInputSchema(), {"type": "disabled"}),
        (
            FileUploadSchema(),
            {"type": "file", "name": "my_file", "content": "foobar", "mimetype": "text/plain"},
        ),
        (FileUploadSchema(), {"type": "raw", "raw_value": "foobar"}),
        (FileUploadSchema(), {"type": "disabled"}),
    ],
)
def test_global_settings_oneofschemas(schema: OneOfSchema, data: dict) -> None:
    assert schema.load(data) == data
    assert schema.dump(data) == data
