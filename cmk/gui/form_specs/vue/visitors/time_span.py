#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterator, Sequence

from cmk.utils.render import SecondsRenderer

from cmk.gui.form_specs.private.validators import IsFloat
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.validators import build_vue_validators

from cmk.rulesets.v1 import Label, Message, Title
from cmk.rulesets.v1.form_specs import TimeMagnitude, TimeSpan
from cmk.rulesets.v1.form_specs.validators import NumberInRange

from ._base import FormSpecVisitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    compute_input_hint,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_prefill_default,
    get_title_and_help,
    localize,
)


def magnitude_translator(magnitude: TimeMagnitude) -> shared_type_defs.TimeSpanTimeMagnitude:
    match magnitude:
        case TimeMagnitude.MILLISECOND:
            return shared_type_defs.TimeSpanTimeMagnitude.millisecond
        case TimeMagnitude.SECOND:
            return shared_type_defs.TimeSpanTimeMagnitude.second
        case TimeMagnitude.MINUTE:
            return shared_type_defs.TimeSpanTimeMagnitude.minute
        case TimeMagnitude.HOUR:
            return shared_type_defs.TimeSpanTimeMagnitude.hour
        case TimeMagnitude.DAY:
            return shared_type_defs.TimeSpanTimeMagnitude.day
        case _:
            raise RuntimeError()


def _render_value(value: float) -> str:
    _whole_seconds, frac = divmod(value, 1.0)
    return SecondsRenderer.detailed_str(int(value)) + (f" {round(frac * 1000)} ms" if frac else "")


class TimeSpanVisitor(FormSpecVisitor[TimeSpan, float]):
    def _parse_value(self, raw_value: object) -> float | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            if isinstance(
                prefill_default := get_prefill_default(self.form_spec.prefill), EmptyValue
            ):
                return prefill_default
            raw_value = prefill_default

        if not isinstance(raw_value, (float, int)):
            return EMPTY_VALUE

        try:
            return float(raw_value)
        except ValueError:
            return EMPTY_VALUE

    def _validators(self) -> Sequence[Callable[[float], object]]:
        def custom_validate() -> Iterator[Callable[[float], object]]:
            for validator in compute_validators(self.form_spec):
                if isinstance(validator, NumberInRange):
                    min_value, max_value = validator.range

                    if max_value is not None and min_value is not None:
                        message = Message("Allowed values range from %s to %s.") % (
                            _render_value(min_value),
                            _render_value(max_value),
                        )
                    elif min_value is None and max_value is not None:
                        message = Message("The maximum allowed value is %s.") % _render_value(
                            max_value
                        )
                    elif min_value is not None and max_value is None:
                        message = Message("The minimum allowed value is %s.") % _render_value(
                            min_value
                        )
                    else:
                        raise RuntimeError()  # is impossible because of NumberInRange init function

                    yield NumberInRange(
                        min_value=min_value,
                        max_value=max_value,
                        error_msg=message,
                    )
                else:
                    yield validator

        return [IsFloat()] + list(custom_validate())

    def _to_vue(
        self, raw_value: object, parsed_value: float | EmptyValue
    ) -> tuple[shared_type_defs.TimeSpan, None | float]:
        title, help_text = get_title_and_help(self.form_spec)
        return (
            shared_type_defs.TimeSpan(
                # FormSpec
                title=title,
                help=help_text,
                validators=build_vue_validators(self._validators()),
                # TimeSpan
                label=localize(self.form_spec.label),
                displayed_magnitudes=[
                    magnitude_translator(m) for m in self.form_spec.displayed_magnitudes
                ],
                i18n=shared_type_defs.TimeSpanI18n(
                    # TODO: remove this once we have i18n in the frontend
                    millisecond=localize(Label("ms")),
                    second=localize(Label("s")),
                    minute=localize(Label("mins")),
                    hour=localize(Label("hours")),
                    day=localize(Label("days")),
                ),
                input_hint=compute_input_hint(self.form_spec.prefill),
            ),
            None if isinstance(parsed_value, EmptyValue) else parsed_value,
        )

    def _validate(
        self, raw_value: object, parsed_value: float | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if raw_value == DEFAULT_VALUE else raw_value, Title("Invalid float number")
            )
        return compute_validation_errors(self._validators(), parsed_value)

    def _to_disk(self, raw_value: object, parsed_value: float) -> float:
        return parsed_value


# TODO: this is mainly a copy of float?!
