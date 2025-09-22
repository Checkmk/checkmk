#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import override

from cmk.ccc.i18n import _
from cmk.gui.form_specs.unstable.validators import IsFloat, IsInteger
from cmk.rulesets.v1.form_specs import DataSize, IECMagnitude, SIMagnitude
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from .._type_defs import DefaultValue, IncomingData, InvalidValue, RawFrontendData
from .._utils import (
    compute_input_hint,
    compute_validators,
    get_prefill_default,
    get_title_and_help,
    localize,
)
from .._visitor_base import FormSpecVisitor
from ..validators import build_vue_validators

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

_ParseValueModel = int
_FallbackModel = list[str]


class DataSizeVisitor(FormSpecVisitor[DataSize, _ParseValueModel, _FallbackModel]):
    def _convert_to_value_and_unit(
        self, parsed_value: float | InvalidValue[_FallbackModel]
    ) -> tuple[str, str]:
        displayed_magnitudes = self.form_spec.displayed_magnitudes
        used_magnitudes = [_magnitudes_map[x] for x in displayed_magnitudes]
        # Just in case they are ordered incorrectly..
        used_magnitudes.sort(key=lambda x: x[1])

        if isinstance(parsed_value, InvalidValue):
            return "0", used_magnitudes[-1][0]

        for unit, factor in reversed(used_magnitudes):
            if parsed_value == 0:
                return "0", used_magnitudes[0][0]
            scaled, remainder = divmod(parsed_value, factor)
            if remainder == 0:
                return str(scaled), unit

        return str(parsed_value), used_magnitudes[-1][0]

    def _convert_to_value(self, value: str, unit: str) -> int | InvalidValue[_FallbackModel]:
        try:
            converted_value = float(value)
        except ValueError:
            return InvalidValue(
                reason=_("Invalid number"),
                fallback_value=["", _magnitudes_map[self.form_spec.displayed_magnitudes[0]][0]],
            )

        for unit_name, factor in _magnitudes_map.values():
            if unit_name == unit:
                return int(converted_value * factor)
        return int(converted_value)

    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParseValueModel | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(
                    self.form_spec.prefill,
                    fallback_value=["", _magnitudes_map[self.form_spec.displayed_magnitudes[0]][0]],
                ),
                InvalidValue,
            ):
                return prefill_default
            value: object = prefill_default
        elif isinstance(raw_value, RawFrontendData) and isinstance(raw_value.value, list):
            value = self._convert_to_value(raw_value.value[0], raw_value.value[1])
        else:
            value = raw_value.value

        if not isinstance(value, int):
            return InvalidValue(
                reason=_("Invalid number"),
                fallback_value=["", _magnitudes_map[self.form_spec.displayed_magnitudes[0]][0]],
            )

        return value

    @override
    def _to_vue(
        self, parsed_value: _ParseValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.DataSize, object]:
        title, help_text = get_title_and_help(self.form_spec)

        if isinstance(parsed_value, InvalidValue):
            displayed_value, displayed_unit = parsed_value.fallback_value
        else:
            displayed_value, displayed_unit = self._convert_to_value_and_unit(parsed_value)

        # Note: The user is allowed to enter float numbers in the frontend
        #       However, the backend validation expects a valid integer valid after
        #       the float/string value went through the parse function
        vue_validators = [IsFloat()] + compute_validators(self.form_spec)
        input_hint = str(compute_input_hint(self.form_spec.prefill))
        return (
            shared_type_defs.DataSize(
                i18n=shared_type_defs.DataSizeI18n(choose_unit=_("Choose unit")),
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

    @override
    def _validators(self) -> Sequence[Callable[[int], object]]:
        return [IsInteger()] + compute_validators(self.form_spec)

    @override
    def _to_disk(self, parsed_value: _ParseValueModel) -> int:
        return int(parsed_value)
