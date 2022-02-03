#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class OpenAPIAttributes:
    def __init__(self, *args, **kwargs):
        metadata = kwargs.setdefault("metadata", {})
        for key in [
            "description",
            "doc_default",
            "enum",
            "example",
            "maximum",
            "maxLength",
            "minimum",
            "minLength",
            "pattern",
            "format",
            "uniqueItems",
            "table",  # used for Livestatus ExprSchema, not an OpenAPI key
            "context",  # used in MultiNested, not an OpenAPI key
        ]:
            if key in kwargs:
                if key in metadata:
                    raise RuntimeError(f"Key {key!r} defined in 'metadata' and 'kwargs'.")
                metadata[key] = kwargs.pop(key)

        super().__init__(*args, **kwargs)
