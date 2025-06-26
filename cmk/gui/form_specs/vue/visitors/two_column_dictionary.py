#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import asdict

from cmk.gui.form_specs.vue.visitors.dictionary import DictionaryVisitor

from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._type_defs import InvalidValue


class TwoColumnDictionaryVisitor(DictionaryVisitor):
    def _to_vue(
        self, parsed_value: Mapping[str, object] | InvalidValue[Mapping[str, object]]
    ) -> tuple[shared_type_defs.TwoColumnDictionary, Mapping[str, object]]:
        schema, value = super()._to_vue(parsed_value)
        schema_args = asdict(schema)
        del schema_args["type"]
        two_column_dictionary = shared_type_defs.TwoColumnDictionary(
            **schema_args,
        )
        return (two_column_dictionary, value)
