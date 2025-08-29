#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import InputHint, MatchingScope, Prefill, RegularExpression
from cmk.rulesets.v1.form_specs.validators import MatchRegex


def create_regex(
    scope: MatchingScope,
    case_sensitive: bool = True,
    validate_pattern: str | None = None,
    title: Title | None = None,
    help_text: Help | None = None,
    error_message: Message | None = None,
    prefill: Prefill[str] | None = None,
) -> RegularExpression:
    return RegularExpression(
        title=title or Title("Regular Expression"),
        predefined_help_text=scope,
        help_text=make_help(help_text, case_sensitive),
        prefill=prefill or InputHint(""),
        custom_validate=[
            MatchRegex(
                regex=validate_pattern,
                error_msg=error_message
                or Message(f"Invalid regex pattern. Expected: {validate_pattern}"),  # pylint: disable=localization-of-non-literal-string
            ),
        ]
        if validate_pattern
        else [],
    )


def make_help(help_text: Help | None, case_sensitive: bool) -> Help:
    help_text = Help("") if help_text is None else help_text + Help(" ")
    if case_sensitive:
        help_text += Help("The match is case sensitive.")
    else:
        help_text += Help("The match is case insensitive.")
    return help_text
