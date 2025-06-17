#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from collections.abc import Sequence
from typing import Any, TypedDict

from cmk.gui.form_specs.generators.timeperiod_selection import create_timeperiod_selection
from cmk.gui.form_specs.private.time_specific import TimeSpecific
from cmk.gui.form_specs.vue.validators import build_vue_validators
from cmk.gui.i18n import _

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, List
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, DEFAULT_VALUE, InvalidValue
from ._utils import compute_validators, get_title_and_help

_default_value_key = shared_type_defs.TimeSpecific.default_value_key
_ts_values_key = shared_type_defs.TimeSpecific.time_specific_values_key


class _TimeperiodConfig(TypedDict):
    timeperiod: str
    parameters: object


_ParsedValueModel = object
_FrontendModel = object


class TimeSpecificVisitor(FormSpecVisitor[TimeSpecific, _ParsedValueModel, _FrontendModel]):
    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        # Since an inactive time specific form spec leaves no traces in the data
        # we can not make any assumptions/tests on the raw_value and return it "as is".
        if self._is_active(raw_value):
            # At least some basic tests if both keys are present
            assert isinstance(raw_value, dict)
            if not (_ts_values_key in raw_value and _default_value_key in raw_value):
                return InvalidValue(reason=_("Invalid time specific data"), fallback_value={})

            if self.options.data_origin == DataOrigin.DISK:
                return {
                    _default_value_key: raw_value[_default_value_key],
                    _ts_values_key: self._convert_to_dict_config(raw_value[_ts_values_key]),
                }
            return raw_value
        return raw_value

    def _convert_to_dict_config(
        self, config: Sequence[tuple[str, object]]
    ) -> Sequence[_TimeperiodConfig]:
        return [{"timeperiod": x[0], "parameters": x[1]} for x in config]

    def _convert_to_tuple_config(
        self, config: Sequence[_TimeperiodConfig]
    ) -> Sequence[tuple[str, object]]:
        return [(x["timeperiod"], x["parameters"]) for x in config]

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.TimeSpecific, None | object]:
        title, help_text = get_title_and_help(self.form_spec)

        disabled_visitor = self._time_specific_disabled_visitor()
        disabled_spec = disabled_visitor.to_vue(DEFAULT_VALUE)[0]

        enabled_visitor = self._time_specific_enabled_visitor()
        enabled_spec = enabled_visitor.to_vue(DEFAULT_VALUE)[0]

        return (
            shared_type_defs.TimeSpecific(
                title=title,
                help=help_text,
                i18n=shared_type_defs.TimeSpecificI18n(
                    enable=_("Enable time specific parameters"),
                    disable=_("Disable time specific parameters"),
                ),
                validators=build_vue_validators(compute_validators(self.form_spec)),
                parameter_form_enabled=enabled_spec,
                parameter_form_disabled=disabled_spec,
            ),
            self._get_current_visitor(parsed_value).to_vue(parsed_value)[1],
        )

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        return self._get_current_visitor(parsed_value).validate(parsed_value)

    def _to_disk(self, parsed_value: _ParsedValueModel) -> object:
        disk_value = self._get_current_visitor(parsed_value).to_disk(parsed_value)
        if self._is_active(parsed_value):
            # Convert value to ugly tuple format
            disk_value = {
                _default_value_key: disk_value[_default_value_key],
                _ts_values_key: self._convert_to_tuple_config(disk_value[_ts_values_key]),
            }
        return disk_value

    def _is_active(self, data: object) -> bool:
        if isinstance(data, dict):
            return _default_value_key in data
        return False

    def _get_current_visitor(self, parsed_value: object) -> FormSpecVisitor[Any, Any, Any]:
        return (
            self._time_specific_enabled_visitor()
            if self._is_active(parsed_value)
            else self._time_specific_disabled_visitor()
        )

    def _time_specific_spec(self) -> Dictionary:
        spec_default = dataclasses.replace(
            self.form_spec.parameter_form,
            title=Title("Default parameters when no time period matches"),
        )

        return Dictionary(
            title=self.form_spec.parameter_form.title,
            help_text=self.form_spec.parameter_form.help_text,
            elements={
                _default_value_key: DictElement(
                    parameter_form=spec_default,
                    required=True,
                ),
                _ts_values_key: DictElement(
                    parameter_form=List(
                        title=Title("Configured time period parameters"),
                        help_text=Help(
                            "Specify the time periods for which the parameters should be used."
                        ),
                        element_template=Dictionary(
                            elements={
                                "timeperiod": DictElement(
                                    parameter_form=create_timeperiod_selection(
                                        title=Title("Match only during time period")
                                    ),
                                    required=True,
                                ),
                                "parameters": DictElement(
                                    parameter_form=self.form_spec.parameter_form,
                                    required=True,
                                ),
                            },
                        ),
                    ),
                    required=True,
                ),
            },
        )

    def _time_specific_enabled_visitor(self) -> FormSpecVisitor[Any, Any, Any]:
        return get_visitor(self._time_specific_spec(), self.options)

    def _time_specific_disabled_visitor(self) -> FormSpecVisitor[Any, Any, Any]:
        return get_visitor(self.form_spec.parameter_form, self.options)
