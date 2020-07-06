#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a check plugin
"""
import functools
import inspect
import itertools
from inspect import signature
from typing import Any, Callable, Dict, Generator, List, Optional, Union

from cmk.utils.check_utils import ensure_management_name, MANAGEMENT_NAME_PREFIX
from cmk.utils.type_defs import ParsedSectionName, CheckPluginName, RuleSetName

from cmk.base.api.agent_based.checking_types import (
    CheckPlugin,
    IgnoreResults,
    Metric,
    Result,
    Service,
    state,
)

ITEM_VARIABLE = "%s"

MANAGEMENT_DESCR_PREFIX = "Management Interface: "


def _validate_service_name(plugin_name: str, service_name: str) -> None:
    if not isinstance(service_name, str):
        raise TypeError("[%s]: service_name must be str, got %r" % (plugin_name, service_name))
    if not service_name:
        raise ValueError("[%s]: service_name must not be empty" % plugin_name)
    if service_name.count(ITEM_VARIABLE) not in (0, 1):
        raise ValueError("[%s]: service_name must contain %r at most once" %
                         (plugin_name, ITEM_VARIABLE))

    if (plugin_name.startswith(MANAGEMENT_NAME_PREFIX)
            is not service_name.startswith(MANAGEMENT_DESCR_PREFIX)):
        raise ValueError(
            "[%s]: service name and description inconsistency: Please neither have your plugins "
            "name start with %r, nor the description with %r. In the rare case that you want to "
            "implement a check plugin explicitly designed for management boards (and nothing else),"
            " you must do both of the above." %
            (plugin_name, MANAGEMENT_NAME_PREFIX, MANAGEMENT_DESCR_PREFIX))


def _requires_item(service_name: str) -> bool:
    """See if this check requires an item"""
    return ITEM_VARIABLE in service_name


def _create_sections(sections: Optional[List[str]],
                     plugin_name: CheckPluginName) -> List[ParsedSectionName]:
    if sections is None:
        return [ParsedSectionName(str(plugin_name))]
    if not isinstance(sections, list):
        raise TypeError("[%s]: 'sections' must be a list of str, got %r" % (plugin_name, sections))
    if not sections:
        raise ValueError("[%s]: 'sections' must not be empty" % plugin_name)
    return [ParsedSectionName(n) for n in sections]


def _validate_function_args(plugin_name: str, func_type: str, function: Callable, has_item: bool,
                            has_params: bool, sections: List[ParsedSectionName]) -> None:
    """Validate the functions signature and type"""

    if not inspect.isgeneratorfunction(function):
        raise TypeError("[%s]: %s function must be a generator function" % (plugin_name, func_type))

    parameters = enumerate(signature(function).parameters, 1)
    if has_item:
        pos, name = next(parameters)
        if name != "item":
            raise TypeError("[%s]: %s function must have 'item' as %d. argument, got %s" %
                            (plugin_name, func_type, pos, name))
    if has_params:
        pos, name = next(parameters)
        if name != "params":
            raise TypeError("[%s]: %s function must have 'params' as %d. argument, got %s" %
                            (plugin_name, func_type, pos, name))

    if len(sections) == 1:
        pos, name = next(parameters)
        if name != 'section':
            raise TypeError("[%s]: %s function must have 'section' as %d. argument, got %r" %
                            (plugin_name, func_type, pos, name))
    else:
        for (pos, name), section in itertools.zip_longest(parameters, sections):
            if name != "section_%s" % section:
                raise TypeError("[%s]: %s function must have 'section_%s' as %d. argument, got %r" %
                                (plugin_name, func_type, section, pos, name))


def _filter_discovery(
    generator: Callable[..., Generator[Any, None, None]],
    requires_item: bool,
) -> Callable[..., Generator[Service, None, None]]:
    """Only let Services through

    This allows for better typing in base code.
    """
    @functools.wraps(generator)
    def filtered_generator(*args, **kwargs):
        for element in generator(*args, **kwargs):
            if not isinstance(element, Service):
                raise TypeError("unexpected type in discovery: %r" % type(element))
            if requires_item is (element.item is None):
                raise TypeError("unexpected type of item discovered: %r" % type(element.item))
            yield element

    return filtered_generator


def _filter_check(
    generator: Callable[..., Generator[Any, None, None]],
) -> Callable[..., Generator[Union[Result, Metric, IgnoreResults], None, None]]:
    """Only let Result, Metric and IgnoreResults through

    This allows for better typing in base code.
    """
    @functools.wraps(generator)
    def filtered_generator(*args, **kwargs):
        for element in generator(*args, **kwargs):
            if not isinstance(element, (Result, Metric, IgnoreResults)):
                raise TypeError("unexpected type in check function: %r" % type(element))
            yield element

    return filtered_generator


def _validate_default_parameters(params_type: str, ruleset_name: Optional[str],
                                 default_parameters: Optional[Dict]) -> None:
    if default_parameters is None:
        if ruleset_name is None:
            return
        raise TypeError("missing default %s parameters for ruleset %s" %
                        (params_type, ruleset_name))

    if not isinstance(default_parameters, dict):
        raise TypeError("default %s parameters must be dict" % (params_type,))

    if ruleset_name is None:
        raise TypeError("missing ruleset name for default %s parameters" % (params_type))


def _validate_discovery_ruleset(ruleset_name: Optional[str],
                                default_parameters: Optional[dict]) -> None:
    if ruleset_name is None:
        return

    # TODO (mo): Implelment this! CMK-4180
    # * see that the ruleset exists
    # * the item spec matches
    # * the default parameters can be loaded
    return


def _validate_check_ruleset(ruleset_name: Optional[str],
                            default_parameters: Optional[dict]) -> None:
    if ruleset_name is None:
        return

    # TODO (mo): Implelment this! CMK-4180
    # * see that the ruleset exists
    # * the item spec matches
    # * the default parameters can be loaded
    return


def unfit_for_clustering_wrapper(check_function):
    """Return a cluster_check_function that displays a generic warning"""
    @functools.wraps(check_function)
    def unfit_for_clustering(*args, **kwargs):
        yield Result(
            state=state.UNKNOWN,
            summary=("This service is not ready to handle clustered data. "
                     "Please change your configuration."),
        )

    return unfit_for_clustering


def create_check_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    service_name: str,
    discovery_function: Callable,
    discovery_default_parameters: Optional[Dict] = None,
    discovery_ruleset_name: Optional[str] = None,
    check_function: Callable,
    check_default_parameters: Optional[Dict] = None,
    check_ruleset_name: Optional[str] = None,
    cluster_check_function: Optional[Callable] = None,
    module: Optional[str] = None,
) -> CheckPlugin:
    """Return an CheckPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    plugin_name = CheckPluginName(name)

    subscribed_sections = _create_sections(sections, plugin_name)

    _validate_service_name(name, service_name)
    requires_item = _requires_item(service_name)

    # validate discovery arguments
    _validate_default_parameters(
        "discovery",
        discovery_ruleset_name,
        discovery_default_parameters,
    )
    _validate_discovery_ruleset(
        discovery_ruleset_name,
        discovery_default_parameters,
    )
    _validate_function_args(
        name,
        "discovery",
        discovery_function,
        False,  # no item
        discovery_ruleset_name is not None,
        subscribed_sections,
    )

    # validate check arguments
    _validate_default_parameters(
        "check",
        check_ruleset_name,
        check_default_parameters,
    )
    _validate_check_ruleset(
        check_ruleset_name,
        check_default_parameters,
    )
    _validate_function_args(
        name,
        "check",
        check_function,
        requires_item,
        check_ruleset_name is not None,
        subscribed_sections,
    )

    if cluster_check_function is None:
        cluster_check_function = unfit_for_clustering_wrapper(check_function)
    else:
        _validate_function_args(
            name,
            "cluster check",
            cluster_check_function,
            requires_item,
            check_ruleset_name is not None,
            subscribed_sections,
        )
        cluster_check_function = _filter_check(cluster_check_function)

    return CheckPlugin(
        plugin_name,
        subscribed_sections,
        service_name,
        _filter_discovery(discovery_function, requires_item),
        discovery_default_parameters or {},
        None if discovery_ruleset_name is None else RuleSetName(discovery_ruleset_name),
        _filter_check(check_function),
        check_default_parameters or {},
        None if check_ruleset_name is None else RuleSetName(check_ruleset_name),
        cluster_check_function,
        module,
    )


def management_plugin_factory(original_plugin: CheckPlugin) -> CheckPlugin:
    return CheckPlugin(
        ensure_management_name(original_plugin.name),
        original_plugin.sections,
        "%s%s" % (MANAGEMENT_DESCR_PREFIX, original_plugin.service_name),
        original_plugin.discovery_function,
        original_plugin.discovery_default_parameters,
        original_plugin.discovery_ruleset_name,
        original_plugin.check_function,
        original_plugin.check_default_parameters,
        original_plugin.check_ruleset_name,
        original_plugin.cluster_check_function,
        original_plugin.module,
    )
