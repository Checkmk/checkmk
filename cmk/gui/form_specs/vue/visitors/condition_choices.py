#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import assert_never, cast, Literal

from cmk.gui.form_specs.private.condition_choices import (
    Condition,
    ConditionChoices,
    ConditionGroupID,
    Conditions,
)
from cmk.gui.form_specs.vue import shared_type_defs

from cmk.rulesets.v1 import Title

from ._base import FormSpecVisitor
from ._type_defs import DataOrigin, DEFAULT_VALUE, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
)

_UNSUPPORTED_VALUE_FROM_FRONTEND = Literal["Unsupported value received from frontend"]


def _condition_to_value(name: str, condition: Condition) -> shared_type_defs.ConditionChoicesValue:
    match condition:
        # All following assignments and assertions shouldn't be necessary, mypy just doesn't
        # understand narrowing on unions in match statements yet as other tooling like pyright does.
        # Remove once https://github.com/python/mypy/issues/16286 is implemented.
        case {"$or": list()}:
            or_condition = condition["$or"]  # type: ignore[index]
            assert isinstance(or_condition, list)
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Or(or_=or_condition)
            )
        case {"$nor": list()}:
            nor_condition = condition["$nor"]  # type: ignore[index]
            assert isinstance(nor_condition, list)  # Same as above
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Nor(nor=nor_condition)
            )
        case {"$ne": str()}:
            ne_condition = condition["$ne"]  # type: ignore[index]
            assert isinstance(ne_condition, str)  # Same as above
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Ne(ne=ne_condition)
            )
        case str():
            return shared_type_defs.ConditionChoicesValue(
                group_name=name, value=shared_type_defs.Eq(eq=condition)
            )
        case _other:
            assert not isinstance(_other, dict)  # Remove this as well
            assert_never(condition)


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
        return name, {ne_operator: shared_type_defs.Ne(**value).ne}
    except TypeError:
        pass

    try:
        or_operator: Literal["$or"] = "$or"
        return name, {or_operator: shared_type_defs.Or(**value).or_}
    except TypeError:
        pass

    try:
        nor_operator: Literal["$nor"] = "$nor"
        return name, {nor_operator: shared_type_defs.Nor(**value).nor}
    except TypeError:
        pass

    try:
        return name, shared_type_defs.Eq(**value).eq
    except TypeError:
        raise TypeError(_UNSUPPORTED_VALUE_FROM_FRONTEND)


def _parse_frontend(raw_value: object) -> Conditions | EmptyValue:
    if not isinstance(raw_value, list):
        return EMPTY_VALUE

    try:
        return dict(_value_to_condition(c) for c in raw_value)
    except TypeError:
        return EMPTY_VALUE


def _parse_disk(raw_value: object) -> Conditions | EmptyValue:
    if not isinstance(raw_value, dict):
        return EMPTY_VALUE

    for group in raw_value.values():
        if isinstance(group, dict):
            if any(key not in ["$ne", "$or", "$nor"] for key in group):
                return EMPTY_VALUE

            if cond := group.get("$ne"):
                if not isinstance(cond, str):
                    return EMPTY_VALUE
            elif cond := (group.get("$or") or group.get("$nor")):
                if not isinstance(cond, list):
                    return EMPTY_VALUE
            elif not isinstance(cond, str):
                return EMPTY_VALUE

            continue

        if not isinstance(group, str):
            return EMPTY_VALUE

    return cast(Conditions, raw_value)


class ConditionChoicesVisitor(FormSpecVisitor[ConditionChoices, Conditions]):
    def _parse_value(self, raw_value: object) -> Conditions | EmptyValue:
        if self.options.data_origin == DataOrigin.FRONTEND:
            return _parse_frontend(raw_value)

        return _parse_disk(raw_value)

    def _to_vue(
        self, raw_value: object, parsed_value: Conditions | EmptyValue
    ) -> tuple[shared_type_defs.ConditionChoices, list[shared_type_defs.ConditionChoicesValue]]:
        title, help_text = get_title_and_help(self.form_spec)

        conditions = self.form_spec.get_conditions()

        value = (
            [_condition_to_value(name, c) for name, c in parsed_value.items()]
            if not isinstance(parsed_value, EmptyValue)
            else []
        )

        return (
            shared_type_defs.ConditionChoices(
                title=title, help=help_text, condition_groups=conditions
            ),
            value,
        )

    def _validate(
        self, raw_value: object, parsed_value: Conditions | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid conditions")
            )

        return compute_validation_errors(compute_validators(self.form_spec), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: Conditions) -> Conditions:
        return parsed_value
