#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.type_defs import Choices

from .defines import syslog_facilities
from .helpers import service_levels


def service_levels_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    choices: Choices = [(str(level), descr) for level, descr in service_levels()]
    empty_choices: Choices = [("", "")]
    return empty_choices + _filter_choices(value, choices)


def syslog_facilities_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    choices: Choices = [(str(v), title) for v, title in syslog_facilities]
    empty_choices: Choices = [("", "")]
    return empty_choices + _filter_choices(value, choices)


def _filter_choices(value: str, choices: Choices) -> Choices:
    value_to_search = value.lower()
    return [(value, title) for value, title in choices if value_to_search in title.lower()]
