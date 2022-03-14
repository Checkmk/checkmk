#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a check plugin
"""
import functools
from typing import Any, Callable, Generator, List, Optional

from cmk.utils.type_defs import CheckPluginName, ParsedSectionName, RuleSetName

from cmk.base.api.agent_based.checking_classes import (
    CheckFunction,
    CheckPlugin,
    DiscoveryFunction,
    IgnoreResults,
    Metric,
    Result,
    Service,
)
from cmk.base.api.agent_based.register.utils import (
    create_subscribed_sections,
    ITEM_VARIABLE,
    RuleSetType,
    validate_default_parameters,
    validate_function_arguments,
    validate_ruleset_type,
)
from cmk.base.api.agent_based.type_defs import ParametersTypeAlias

MANAGEMENT_DESCR_PREFIX = "Management Interface: "


def _validate_service_name(plugin_name: CheckPluginName, service_name: str) -> None:
    if not isinstance(service_name, str):
        raise TypeError("service_name must be str, got %r" % (service_name,))
    if not service_name:
        raise ValueError("service_name must not be empty")
    if service_name.count(ITEM_VARIABLE) not in (0, 1):
        raise ValueError("service_name must contain %r at most once" % ITEM_VARIABLE)

    if plugin_name.is_management_name() is not service_name.startswith(MANAGEMENT_DESCR_PREFIX):
        raise ValueError(
            "service name and description inconsistency: Please neither have your plugins "
            "name start with %r, nor the description with %r. In the rare case that you want to "
            "implement a check plugin explicitly designed for management boards (and nothing else),"
            " you must do both of the above."
            % (CheckPluginName.MANAGEMENT_PREFIX, MANAGEMENT_DESCR_PREFIX)
        )


def _requires_item(service_name: str) -> bool:
    """See if this check requires an item"""
    try:
        return ITEM_VARIABLE in service_name
    except TypeError:
        # _validate_service_name will fail with a better message
        return False


def _filter_discovery(
    generator: Callable[..., Generator[Any, None, None]],
    requires_item: bool,
    validate_item: bool,
) -> DiscoveryFunction:
    """Only let Services through

    This allows for better typing in base code.
    """

    @functools.wraps(generator)
    def filtered_generator(*args, **kwargs):
        for element in generator(*args, **kwargs):
            if not isinstance(element, Service):
                raise TypeError("unexpected type in discovery: %r" % type(element))
            if validate_item and requires_item is (element.item is None):
                raise TypeError("unexpected type of item discovered: %r" % type(element.item))
            yield element

    return filtered_generator


def _filter_check(
    generator: Callable[..., Generator[Any, None, None]],
) -> CheckFunction:
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


def _validate_kwargs(
    *,
    plugin_name: CheckPluginName,
    subscribed_sections: List[ParsedSectionName],
    service_name: str,
    requires_item: bool,
    discovery_function: Callable,
    discovery_default_parameters: Optional[ParametersTypeAlias],
    discovery_ruleset_name: Optional[str],
    discovery_ruleset_type: RuleSetType,
    check_function: Callable,
    check_default_parameters: Optional[ParametersTypeAlias],
    check_ruleset_name: Optional[str],
    cluster_check_function: Optional[Callable],
) -> None:
    _validate_service_name(plugin_name, service_name)

    # validate discovery arguments
    validate_default_parameters(
        "discovery",
        discovery_ruleset_name,
        discovery_default_parameters,
    )
    validate_ruleset_type(discovery_ruleset_type)
    validate_function_arguments(
        type_label="discovery",
        function=discovery_function,
        has_item=False,
        default_params=discovery_default_parameters,
        sections=subscribed_sections,
    )
    # validate check arguments
    validate_default_parameters(
        "check",
        check_ruleset_name,
        check_default_parameters,
    )
    validate_function_arguments(
        type_label="check",
        function=check_function,
        has_item=requires_item,
        default_params=check_default_parameters,
        sections=subscribed_sections,
    )

    if cluster_check_function is None:
        return

    validate_function_arguments(
        type_label="cluster_check",
        function=cluster_check_function,
        has_item=requires_item,
        default_params=check_default_parameters,
        sections=subscribed_sections,
    )


def create_check_plugin(
    *,
    name: str,
    sections: Optional[List[str]] = None,
    service_name: str,
    discovery_function: Callable,
    discovery_default_parameters: Optional[ParametersTypeAlias] = None,
    discovery_ruleset_name: Optional[str] = None,
    discovery_ruleset_type: RuleSetType = RuleSetType.MERGED,
    check_function: Callable,
    check_default_parameters: Optional[ParametersTypeAlias] = None,
    check_ruleset_name: Optional[str] = None,
    cluster_check_function: Optional[Callable] = None,
    module: Optional[str] = None,
    validate_item: bool = True,
    validate_kwargs: bool = True,
) -> CheckPlugin:
    """Return an CheckPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    plugin_name = CheckPluginName(name)

    subscribed_sections = create_subscribed_sections(sections, plugin_name)

    requires_item = _requires_item(service_name)

    if validate_kwargs:
        _validate_kwargs(
            plugin_name=plugin_name,
            subscribed_sections=subscribed_sections,
            service_name=service_name,
            requires_item=requires_item,
            discovery_function=discovery_function,
            discovery_default_parameters=discovery_default_parameters,
            discovery_ruleset_name=discovery_ruleset_name,
            discovery_ruleset_type=discovery_ruleset_type,
            check_function=check_function,
            check_default_parameters=check_default_parameters,
            check_ruleset_name=check_ruleset_name,
            cluster_check_function=cluster_check_function,
        )

    disco_func = _filter_discovery(discovery_function, requires_item, validate_item)
    disco_ruleset_name = RuleSetName(discovery_ruleset_name) if discovery_ruleset_name else None

    cluster_check_function = (
        None if cluster_check_function is None else _filter_check(cluster_check_function)
    )

    return CheckPlugin(
        name=plugin_name,
        sections=subscribed_sections,
        service_name=service_name,
        discovery_function=disco_func,
        discovery_default_parameters=discovery_default_parameters,
        discovery_ruleset_name=disco_ruleset_name,
        discovery_ruleset_type=(
            "merged" if discovery_ruleset_type is RuleSetType.MERGED else "all"
        ),
        check_function=_filter_check(check_function),
        check_default_parameters=check_default_parameters,
        check_ruleset_name=RuleSetName(check_ruleset_name) if check_ruleset_name else None,
        cluster_check_function=cluster_check_function,
        module=module,
    )


def management_plugin_factory(original_plugin: CheckPlugin) -> CheckPlugin:
    return CheckPlugin(
        original_plugin.name.create_management_name(),
        original_plugin.sections,
        "%s%s" % (MANAGEMENT_DESCR_PREFIX, original_plugin.service_name),
        original_plugin.discovery_function,
        original_plugin.discovery_default_parameters,
        original_plugin.discovery_ruleset_name,
        original_plugin.discovery_ruleset_type,
        original_plugin.check_function,
        original_plugin.check_default_parameters,
        original_plugin.check_ruleset_name,
        original_plugin.cluster_check_function,
        original_plugin.module,
    )
