#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
import warnings
from collections.abc import Callable

from cmk.ccc.exceptions import MKGeneralException

from cmk.rulesets.v1 import Help, Message
from cmk.rulesets.v1.form_specs import FormSpec, MatchingScope, RegularExpression, String
from cmk.rulesets.v1.form_specs.validators import ValidationError


class RegexFutureWarning(FutureWarning): ...


def recompose(form_spec: FormSpec[str]) -> String:
    if not isinstance(form_spec, RegularExpression):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a Percentage form spec, got {type(form_spec)}"
        )

    matching_help_text = Help("")
    match form_spec.predefined_help_text:
        case MatchingScope.PREFIX:
            matching_help_text = Help(
                "The pattern is matched from the beginning. Add a tailing "
                "<tt>$</tt> to change it to a whole text match."
            )
        case MatchingScope.INFIX:
            matching_help_text = Help(
                "The pattern is applied as infix search. Add a leading <tt>^</tt> "
                "to make it match from the beginning and/or a tailing <tt>$</tt> "
                "to match till the end of the text."
            )
        case MatchingScope.FULL:
            matching_help_text = Help(
                "The pattern is matching the whole text. You can add <tt>.*</tt> "
                "in front or at the end of your pattern to make it either a prefix "
                "or infix search."
            )

    help_text = form_spec.help_text if form_spec.help_text is not None else Help("")
    # Note: RegularExpression currently does not support case insensitivity
    case_sensitive_help = Help("The match is case sensitive.")

    combined_help = (
        help_text
        + Help(" ")
        + Help("The text entered here is handled as a regular expression pattern.")
        + Help(" ")
        + matching_help_text
        + Help(" ")
        + case_sensitive_help
        + Help(" ")
        + Help(
            "Read more about [regexes|regular expression matching in Checkmk] in our user guide."
        )
    )

    def _validate_regex(value: str) -> str:
        try:
            with warnings.catch_warnings(action="error", category=FutureWarning):
                re.compile(value)

        except FutureWarning as e:
            warnings.warn(f"{e} in {value}", RegexFutureWarning)
            re.compile(value)

        except re.error:
            raise ValidationError(Message("Invalid regular expression: %s") % value)

        return value

    combined_validate: list[Callable[[str], object]] = [_validate_regex]
    if form_spec.custom_validate:
        combined_validate.extend(form_spec.custom_validate)

    return String(
        title=form_spec.title,
        help_text=combined_help,
        custom_validate=combined_validate,
        label=form_spec.label,
        migrate=form_spec.migrate,
        prefill=form_spec.prefill,
    )
