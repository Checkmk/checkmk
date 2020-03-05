#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a section plugin
"""
from typing import (  # pylint: disable=unused-import
    Any, Generator, List, Optional, Union)
import inspect

from cmk.base.discovered_labels import HostLabel
from cmk.base.api import PluginName
from cmk.base.api.agent_based.section_types import (
    AgentParseFunction,
    AgentSectionPlugin,
    HostLabelFunction,
)


def _validate_parse_function(parse_function):
    # type: (AgentParseFunction) -> None
    if not inspect.isfunction(parse_function):
        raise TypeError("parse function must be a function: %r" % (parse_function,))

    if inspect.isgeneratorfunction(parse_function):
        raise TypeError("parse function must not be a generator function: %r" % (parse_function,))

    parameters = inspect.signature(parse_function).parameters
    if list(parameters) != ['string_table']:
        raise ValueError("parse function must accept exactly one argument 'string_table'")


def _validate_host_label_function(host_label_function):
    # type: (HostLabelFunction) -> None
    if not inspect.isgeneratorfunction(host_label_function):
        raise TypeError("host label function must be a generator function: %r" %
                        (host_label_function,))

    parameters = inspect.signature(host_label_function).parameters
    if list(parameters) not in (['section'], ['_section']):
        raise ValueError("host label function must accept exactly one argument 'section'")


def _validate_supercedings(supercedes):
    # type: (List[PluginName]) -> None
    if not len(supercedes) == len(set(supercedes)):
        raise ValueError("duplicate supercedes entry")


def _noop_host_label_function(section):  # pylint: disable=unused-argument
    # type: (Any) -> Generator[HostLabel, None, None]
    return
    yield  # pylint: disable=unreachable


def _create_host_label_function(host_label_function):
    # type: (Optional[HostLabelFunction]) -> HostLabelFunction
    if host_label_function is None:
        return _noop_host_label_function

    _validate_host_label_function(host_label_function)
    return host_label_function


def _create_supercedes(supercedes):
    # type: (Optional[List[str]]) -> List[PluginName]
    if supercedes is None:
        return []

    supercedes_plugins = [PluginName(n) for n in supercedes]
    _validate_supercedings(supercedes_plugins)

    return sorted(supercedes_plugins)


def create_agent_section_plugin(
#    *,
    name,
    parsed_section_name=None,
    parse_function=None,  # TODO: Remove None
    host_label_function=None,
    supercedes=None,
    forbidden_names=None,  # TODO: Remove None
):
    # type: (str, Optional[str], Optional[AgentParseFunction], Optional[HostLabelFunction], Optional[List[str]], Optional[List[PluginName]]) -> AgentSectionPlugin
    """Return an AgentSectionPlugin object after validating and converting the arguments one by one"""

    if parse_function is None or forbidden_names is None:  # TODO: Remove this conditional
        raise ValueError()
    plugin_name = PluginName(name, forbidden_names=forbidden_names)

    _validate_parse_function(parse_function)

    return AgentSectionPlugin(
        plugin_name,
        PluginName(parsed_section_name) if parsed_section_name else plugin_name,
        parse_function,
        _create_host_label_function(host_label_function),
        _create_supercedes(supercedes),
    )
