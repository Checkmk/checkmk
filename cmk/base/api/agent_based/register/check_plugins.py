#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background tools required to register a check plugin
"""
import functools
from typing import Any, Callable, Dict, Generator, get_args, List, Optional

from cmk.utils.type_defs import CheckPluginName, RuleSetName

from cmk.base.api.agent_based.type_defs import (
    CheckFunction,
    CheckPlugin,
    DiscoveryFunction,
    DiscoveryRuleSetType,
)
from cmk.base.api.agent_based.checking_classes import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    state,
)
from cmk.base.api.agent_based.register.utils import (
    create_subscribed_sections,
    validate_function_arguments,
    validate_default_parameters,
)

ITEM_VARIABLE = "%s"

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
            " you must do both of the above." %
            (CheckPluginName.MANAGEMENT_PREFIX, MANAGEMENT_DESCR_PREFIX))


def _requires_item(service_name: str) -> bool:
    """See if this check requires an item"""
    return ITEM_VARIABLE in service_name


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


def _filter_check(generator: Callable[..., Generator[Any, None, None]],) -> CheckFunction:
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


def _validate_discovery_ruleset(ruleset_name: Optional[str],
                                default_parameters: Optional[dict]) -> None:
    if ruleset_name is None:
        return

    # TODO (mo): Implelment this! CMK-4180
    # * see that the ruleset exists
    # * the item spec matches
    # * the default parameters can be loaded
    return


def _validate_discovery_ruleset_type(ruleset_type: DiscoveryRuleSetType) -> None:
    if ruleset_type not in get_args(DiscoveryRuleSetType):
        raise ValueError("invalid discovery ruleset type %r. Allowed are %s" %
                         (ruleset_type, ",".join(repr(c) for c in get_args(DiscoveryRuleSetType))))


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
    # copy signature of check_function
    @functools.wraps(check_function, ("__attributes__",))
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
    discovery_ruleset_type: DiscoveryRuleSetType = "merged",
    check_function: Callable,
    check_default_parameters: Optional[Dict] = None,
    check_ruleset_name: Optional[str] = None,
    cluster_check_function: Optional[Callable] = None,
    module: Optional[str] = None,
    validate_item: bool = True,
) -> CheckPlugin:
    """Return an CheckPlugin object after validating and converting the arguments one by one

    For a detailed description of the parameters please refer to the exposed function in the
    'register' namespace of the API.
    """
    plugin_name = CheckPluginName(name)

    subscribed_sections = create_subscribed_sections(sections, plugin_name)

    _validate_service_name(plugin_name, service_name)
    requires_item = _requires_item(service_name)

    # validate discovery arguments
    validate_default_parameters(
        "discovery",
        discovery_ruleset_name,
        discovery_default_parameters,
    )
    _validate_discovery_ruleset(
        discovery_ruleset_name,
        discovery_default_parameters,
    )
    _validate_discovery_ruleset_type(discovery_ruleset_type,)
    validate_function_arguments(
        "discovery",
        discovery_function,
        False,  # no item
        discovery_ruleset_name is not None,
        subscribed_sections,
    )
    disco_func = _filter_discovery(discovery_function, requires_item, validate_item)
    disco_params = discovery_default_parameters or {}
    disco_ruleset_name = RuleSetName(discovery_ruleset_name) if discovery_ruleset_name else None

    # validate check arguments
    validate_default_parameters(
        "check",
        check_ruleset_name,
        check_default_parameters,
    )
    _validate_check_ruleset(
        check_ruleset_name,
        check_default_parameters,
    )
    validate_function_arguments(
        "check",
        check_function,
        requires_item,
        check_default_parameters is not None,
        subscribed_sections,
    )

    if cluster_check_function is None:
        cluster_check_function = unfit_for_clustering_wrapper(check_function)
    else:
        validate_function_arguments(
            "cluster check",
            cluster_check_function,
            requires_item,
            check_ruleset_name is not None,
            subscribed_sections,
        )
        cluster_check_function = _filter_check(cluster_check_function)

    return CheckPlugin(
        name=plugin_name,
        sections=subscribed_sections,
        service_name=service_name,
        discovery_function=disco_func,
        discovery_default_parameters=disco_params,
        discovery_ruleset_name=disco_ruleset_name,
        discovery_ruleset_type=discovery_ruleset_type,
        check_function=_filter_check(check_function),
        check_default_parameters=check_default_parameters or {},
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
