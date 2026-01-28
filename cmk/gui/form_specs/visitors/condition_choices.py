#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast, Literal, override

from cmk.gui.form_specs.unstable.condition_choices import (
    Condition,
    ConditionChoices,
    ConditionGroupID,
    Conditions,
)
from cmk.gui.i18n import _
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._type_defs import DefaultValue, IncomingData, InvalidValue, RawFrontendData
from ._utils import (
    compute_validation_errors,
    compute_validators,
    get_title_and_help,
    localize,
)
from .validators import build_vue_validators

_UNSUPPORTED_VALUE_FROM_FRONTEND = Literal["Unsupported value received from frontend"]
_FallbackModel = list[shared_type_defs.ConditionChoicesValue]


def _condition_to_value(name: str, condition: Condition) -> shared_type_defs.ConditionChoicesValue:
    match condition:
        # All following assignments and assertions shouldn't be necessary, mypy just doesn't
        # understand narrowing on unions in match statements yet as other tooling like pyright does.
        # Remove once https://github.com/python/mypy/issues/16286 is implemented.
        case {"$or": list()}:
            or_condition = condition["$or"]  # type: ignore[index]
            assert isinstance(or_condition, list)
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Or(oper_or=or_condition)
            )
        case {"$nor": list()}:
            nor_condition = condition["$nor"]  # type: ignore[index]
            assert isinstance(nor_condition, list)  # Same as above
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Nor(oper_nor=nor_condition)
            )
        case {"$ne": str()}:
            ne_condition = condition["$ne"]  # type: ignore[index]
            assert isinstance(ne_condition, str)  # Same as above
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Ne(oper_ne=ne_condition)
            )
        case str():
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Eq(oper_eq=condition)
            )
        case other:
            assert not isinstance(other, dict)  # Remove this as well
            # I would like to use:
            # assert_never(condition)
            # but https://github.com/python/mypy/issues/19081#issuecomment-2920053885
            raise TypeError(other)


def _value_to_condition(condition_value: object) -> tuple[ConditionGroupID, Condition]:
    assert isinstance(condition_value, dict)
    try:
        name = condition_value["group_name"]
        value = condition_value["value"]
    except KeyError:
        raise TypeError(_UNSUPPORTED_VALUE_FROM_FRONTEND)

    if not isinstance(value, dict):
        raise TypeError(_UNSUPPORTED_VALUE_FROM_FRONTEND)
    if not isinstance(name, str):
        raise TypeError(_UNSUPPORTED_VALUE_FROM_FRONTEND)

    # We don't want to hard-code attribute names here as they
    # might be subject to change in shared typing.
    try:
        ne_operator: Literal["$ne"] = "$ne"
        return name, {ne_operator: shared_type_defs.Ne(**value).oper_ne}
    except TypeError:
        pass

    try:
        or_operator: Literal["$or"] = "$or"
        return name, {or_operator: shared_type_defs.Or(**value).oper_or}
    except TypeError:
        pass

    try:
        nor_operator: Literal["$nor"] = "$nor"
        return name, {nor_operator: shared_type_defs.Nor(**value).oper_nor}
    except TypeError:
        pass

    try:
        return name, shared_type_defs.Eq(**value).oper_eq
    except TypeError:
        raise TypeError(_UNSUPPORTED_VALUE_FROM_FRONTEND)


def _parse_frontend(raw_value: object) -> Conditions | InvalidValue[_FallbackModel]:
    if not isinstance(raw_value, list):
        return InvalidValue(reason=_("Invalid data"), fallback_value=[])

    try:
        return dict(_value_to_condition(c) for c in raw_value)
    except TypeError:
        return InvalidValue(reason=_("Invalid data"), fallback_value=[])


def _parse_disk(raw_value: object) -> Conditions | InvalidValue[_FallbackModel]:
    if not isinstance(raw_value, dict):
        return InvalidValue(reason=_("Invalid data"), fallback_value=[])

    for group in raw_value.values():
        if isinstance(group, dict):
            if any(key not in ["$ne", "$or", "$nor"] for key in group):
                return InvalidValue(reason=_("Invalid data"), fallback_value=[])

            if cond := group.get("$ne"):
                if not isinstance(cond, str):
                    return InvalidValue(reason=_("Invalid data"), fallback_value=[])
            elif cond := (group.get("$or") or group.get("$nor")):
                if not isinstance(cond, list):
                    return InvalidValue(reason=_("Invalid data"), fallback_value=[])
            elif not isinstance(cond, str):
                return InvalidValue(reason=_("Invalid data"), fallback_value=[])

            continue

        if not isinstance(group, str):
            return InvalidValue(reason=_("Invalid data"), fallback_value=[])

    return cast(Conditions, raw_value)


class ConditionChoicesVisitor(FormSpecVisitor[ConditionChoices, Conditions, _FallbackModel]):
    @override
    def _parse_value(self, raw_value: IncomingData) -> Conditions | InvalidValue[_FallbackModel]:
        if isinstance(raw_value, DefaultValue):
            return InvalidValue(
                fallback_value=[], reason=_("No default values can be set for condition choices.")
            )

        if isinstance(raw_value, RawFrontendData):
            return _parse_frontend(raw_value.value)

        return _parse_disk(raw_value.value)

    @override
    def _to_vue(
        self, parsed_value: Conditions | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.ConditionChoices, object]:
        title, help_text = get_title_and_help(self.form_spec)

        conditions = self.form_spec.get_conditions()

        value = (
            [_condition_to_value(name, c) for name, c in parsed_value.items()]
            if not isinstance(parsed_value, InvalidValue)
            else []
        )

        return (
            shared_type_defs.ConditionChoices(
                title=title,
                help=help_text,
                condition_groups=conditions,
                validators=build_vue_validators(self.form_spec.custom_validate or []),
                i18n=shared_type_defs.ConditionChoicesI18n(
                    choose_condition=_("Choose condition"),
                    choose_operator=_("Choose operator"),
                    add_condition_label=localize(self.form_spec.add_condition_group_label),
                    select_condition_group_to_add=localize(
                        self.form_spec.select_condition_group_to_add
                    ),
                    no_more_condition_groups_to_add=localize(
                        self.form_spec.no_more_condition_groups_to_add
                    ),
                    eq_operator=_("is"),
                    ne_operator=_("is not"),
                    or_operator=_("any of"),
                    nor_operator=_("none of"),
                ),
            ),
            value,
        )

    @override
    def _validate(self, parsed_value: Conditions) -> list[shared_type_defs.ValidationMessage]:
        vue_value = (
            [_condition_to_value(name, c) for name, c in parsed_value.items()]
            if not isinstance(parsed_value, InvalidValue)
            else []
        )

        return compute_validation_errors(
            compute_validators(self.form_spec), lambda: vue_value, vue_value
        )

    @override
    def _to_disk(self, parsed_value: Conditions) -> Conditions:
        return parsed_value
