#  !/usr/bin/env python3
#  Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
#  This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
#  conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Callable, Sequence
from typing import Sized

from cmk.rulesets.v1._localize import Localizable


class ValidationError(ValueError):
    """Raise when custom validation found invalid values

    Args:
        message: Description of why the value is invalid
    """

    def __init__(self, message: Localizable) -> None:
        super().__init__(message)
        self._message = message

    @property
    def message(self) -> Localizable:
        return self._message


def disallow_empty(
    error_msg: Localizable = Localizable("An empty value is not allowed here."),
) -> Callable[[Sequence[object]], None]:
    def validator(value: Sequence[object]) -> None:
        if value is None or (isinstance(value, Sized) and len(value) == 0):
            raise ValidationError(error_msg)

    return validator


def in_range(
    min_value: int | float = float("-inf"),
    max_value: int | float = float("inf"),
    error_msg: Localizable | None = None,
) -> Callable[[int | float], None]:
    def validator(value: int | float) -> None:
        def _get_error_msg(value_too: str, limit_type: str, limit: int | float) -> Localizable:
            return (
                Localizable("%s is too %s. The %s allowed value is %s.")
                % (str(value), value_too, limit_type, str(limit))
                if error_msg is None
                else error_msg
            )

        if min_value is not None and value < min_value:
            raise ValidationError(_get_error_msg("low", "minimum", min_value))
        if max_value is not None and value > max_value:
            raise ValidationError(_get_error_msg("high", "maximum", max_value))

    return validator


def match_regex(
    regex: str | re.Pattern[str], error_msg: Localizable | None = None
) -> Callable[[str], None]:
    def validator(value: str) -> None:
        if isinstance(regex, re.Pattern):
            pattern = regex.pattern
            if regex.match(value):
                return
        elif re.match(pattern := regex, value):
            return

        msg = (
            Localizable("Your input '%s' does not match the required format '%s'.")
            % (value, pattern)
            if error_msg is None
            else error_msg
        )
        raise ValidationError(msg)

    return validator
