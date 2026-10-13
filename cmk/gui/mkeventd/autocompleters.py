#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Sequence

from cmk.gui.config import Config
from cmk.web.utils.choices import Choice

from .defines import syslog_facilities
from .helpers import service_levels


def service_levels_autocompleter(config: Config, value: str, params: dict) -> list[Choice]:  # noqa: ARG001
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    choices: list[Choice] = [(str(level), descr) for level, descr in service_levels()]
    empty_choices: list[Choice] = [("", "")]
    return empty_choices + _filter_choices(value, choices)


def syslog_facilities_autocompleter(config: Config, value: str, params: dict) -> list[Choice]:  # noqa: ARG001
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    choices: list[Choice] = [(str(v), title) for v, title in syslog_facilities]
    empty_choices: list[Choice] = [("", "")]
    return empty_choices + _filter_choices(value, choices)


def _filter_choices(value: str, choices: Sequence[Choice]) -> list[Choice]:
    value_to_search = value.lower()
    return [(value, title) for value, title in choices if value_to_search in title.lower()]
