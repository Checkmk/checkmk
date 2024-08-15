#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private.validators import IsFloat, IsInteger
from cmk.gui.form_specs.vue import shared_type_defs as VueComponents
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DataSize, IECMagnitude, SIMagnitude

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_text_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
)

_magnitudes_map: dict[SIMagnitude | IECMagnitude, tuple[str, int]] = {
    SIMagnitude.BYTE: ("B", 1),
    SIMagnitude.KILO: ("KB", 1000),
    SIMagnitude.MEGA: ("MB", 1000**2),
    SIMagnitude.GIGA: ("GB", 1000**3),
    SIMagnitude.TERA: ("TB", 1000**4),
    SIMagnitude.PETA: ("PB", 1000**5),
    SIMagnitude.EXA: ("EB", 1000**6),
    SIMagnitude.ZETTA: ("ZB", 1000**7),
    SIMagnitude.YOTTA: ("YB", 1000**8),
    IECMagnitude.BYTE: ("B", 1),
    IECMagnitude.KIBI: ("KiB", 1024),
    IECMagnitude.MEBI: ("MiB", 1024**2),
    IECMagnitude.GIBI: ("GiB", 1024**3),
    IECMagnitude.TEBI: ("TiB", 1024**4),
    IECMagnitude.PEBI: ("PiB", 1024**5),
    IECMagnitude.EXBI: ("EiB", 1024**6),
    IECMagnitude.ZEBI: ("ZiB", 1024**7),
    IECMagnitude.YOBI: ("YiB", 1024**8),
}


class DataSizeVisitor(FormSpecVisitor[DataSize, int]):
    def _convert_to_value_and_unit(self, parsed_value: float | EmptyValue) -> tuple[str, str]:
        displayed_magnitudes = self.form_spec.displayed_magnitudes
        used_magnitudes = [_magnitudes_map[x] for x in displayed_magnitudes]
        # Just in case they are ordered incorrectly..
        used_magnitudes.sort(key=lambda x: x[1])

        if isinstance(parsed_value, EmptyValue):
            return "0", used_magnitudes[-1][0]

        for unit, factor in reversed(used_magnitudes):
            if parsed_value == 0:
                return "0", used_magnitudes[0][0]
            scaled, remainder = divmod(parsed_value, factor)
            if remainder == 0:
                return str(scaled), unit

        return str(parsed_value), used_magnitudes[-1][0]

    def _convert_to_value(self, value: str, unit: str) -> int | EmptyValue:
        try:
            converted_value = float(value)
        except ValueError:
            return EMPTY_VALUE

        for unit_name, factor in _magnitudes_map.values():
            if unit_name == unit:
                return int(converted_value * factor)
        return int(converted_value)

    def _parse_value(self, raw_value: object) -> int | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        if self.options.data_origin == DataOrigin.FRONTEND and isinstance(raw_value, list):
            raw_value = self._convert_to_value(raw_value[0], raw_value[1])

        if not isinstance(raw_value, int):
            return EMPTY_VALUE

        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: int | float | EmptyValue
    ) -> tuple[VueComponents.DataSize, list[str]]:
        title, help_text = get_title_and_help(self.form_spec)

        if isinstance(parsed_value, EmptyValue):
            displayed_value = ""
            displayed_unit = _magnitudes_map[self.form_spec.displayed_magnitudes[0]][0]
        else:
            displayed_value, displayed_unit = self._convert_to_value_and_unit(parsed_value)

        # Note: The user is allowed to enter float numbers in the frontend
        #       However, the backend validation expects a valid integer valid after
        #       the float/string value went through the parse function
        vue_validators = [IsFloat()] + compute_validators(self.form_spec)
        input_hint = str(compute_text_input_hint(self.form_spec.prefill))
        return (
            VueComponents.DataSize(
                title=title,
                help=help_text,
                label=localize(self.form_spec.label),
                validators=build_vue_validators(vue_validators),
                input_hint=input_hint,
                displayed_magnitudes=[
                    _magnitudes_map[x][0] for x in self.form_spec.displayed_magnitudes
                ],
            ),
            [str(displayed_value), displayed_unit],
        )

    def _validate(
        self, raw_value: object, parsed_value: int | EmptyValue
    ) -> list[VueComponents.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if isinstance(raw_value, DefaultValue) else raw_value,
                Title("Invalid integer number"),
            )
        return compute_validation_errors(
            [IsInteger()] + compute_validators(self.form_spec), parsed_value
        )

    def _to_disk(self, raw_value: object, parsed_value: int) -> int:
        return int(parsed_value)
