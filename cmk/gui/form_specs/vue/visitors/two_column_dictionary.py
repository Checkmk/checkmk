#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import asdict
from typing import override

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import InvalidValue
from .dictionary import (
    _FallbackModel,
    _ParsedValueModel,
    DictionaryVisitor,
)


class TwoColumnDictionaryVisitor(DictionaryVisitor):
    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.TwoColumnDictionary, object]:
        schema, value = super()._to_vue(parsed_value)
        schema_args = asdict(schema)
        del schema_args["type"]
        two_column_dictionary = shared_type_defs.TwoColumnDictionary(
            **schema_args,
        )
        return (two_column_dictionary, value)
