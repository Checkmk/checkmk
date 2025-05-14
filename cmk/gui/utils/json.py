#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Module `json` shadows a Python standard-library module
# ruff: noqa: A005

import json

from cmk.utils.jsontype import JsonSerializable


class CustomObjectJSONEncoder(json.JSONEncoder):
    """Encodes objects with a to_json() method to JSON.

    Example:

        json.dumps(obj, cls=CustomObjectJSONEncoder)
    """

    def default(self, obj: object) -> JsonSerializable:
        if hasattr(obj, "to_json") and callable(obj.to_json):
            return obj.to_json()
        return super().default(obj)
