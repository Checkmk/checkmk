#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
import functools
import itertools

from cmk.utils.type_defs import PluginName

from cmk.base import item_state
from cmk.base.api.agent_based.checking_types import (
    CheckPlugin,
    Metric,
    state,
    Parameters,
    Result,
    Service,
)
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
import cmk.base.config as config
from cmk.base.check_api_utils import Service as LegacyService
from cmk.base.discovered_labels import HostLabel, DiscoveredHostLabels

DUMMY_RULESET_NAME = "non_existent_auto_migration_dummy_rule"

CLUSTER_LEGACY_MODE_FROM_HELL = "cluster_legacy_mode_from_hell"

# There are so many check_info keys, make sure we didn't miss one.
CONSIDERED_KEYS = {
    "check_function",
    "default_levels_variable",
    "extra_sections",
    "group",
    "handle_empty_info",  # obsolete, and ineffective anyway due to new snmp data layout
    "handle_real_time_checks",  # obsolete
    "has_perfdata",  # obsolete
    "includes",
    "inventory_function",
    "management_board",  # obsolete
    "node_info",  # handled in section
    "parse_function",
    "service_description",
    "snmp_info",  # handled in section
    "snmp_scan_function",  # handled in section
}


def _create_discovery_function(
    check_name: str,
    check_info_dict: Dict[str, Any],
) -> Callable:
    """Create an API compliant discovery function"""

    # 1) ensure we have the correct signature
    # 2) ensure it is a generator of Service instances
    def discovery_migration_wrapper(section):
        disco_func = check_info_dict.get("inventory_function")
        if not callable(disco_func):  # never discover:
            return

        original_discovery_result = disco_func(section)
        if not original_discovery_result:
            return

        for element in original_discovery_result:
            if isinstance(element, (HostLabel, DiscoveredHostLabels)):
                # these are dealt with in the host_label_function!
                continue

            if isinstance(element, LegacyService):
                yield Service(
                    item=element.item,
                    parameters=wrap_parameters(element.parameters or {}),
                    labels=list(element.service_labels),
                )
            elif isinstance(element, tuple) and len(element) in (2, 3):
                parameters = _resolve_string_parameters(element[-1], check_name)
                service = Service(
                    item=element[0] or None,
                    parameters=wrap_parameters(parameters or {}),
                )
                # nasty hack for nasty plugins:
                # Bypass validation. Item should be None or non-empty string!
                service._item = element[0]  # pylint: disable=protected-access
                yield service
            else:
                # just let it through. Base must deal with bogus return types anyway.
                yield element

    return discovery_migration_wrapper


def _resolve_string_parameters(params_unresolved: Any, check_name: str) -> Any:
    if not isinstance(params_unresolved, str):
        return params_unresolved

    try:
        context = config.get_check_context(check_name)
        # string may look like '{"foo": bar}', in the worst case.
        return eval(params_unresolved, context, context)
    except Exception:
        raise ValueError("Invalid check parameter string '%s' found in discovered service %r" %
                         (params_unresolved, check_name))


def _create_check_function(name, check_info_dict, ruleset_name):
    # type: (str, Dict[str, Any], Optional[str]) -> Callable
    """Create an API compliant check function"""
    service_descr = check_info_dict["service_description"]
    if not isinstance(service_descr, str):
        raise ValueError("[%s]: invalid service description: %r" % (name, service_descr))

    # 1) ensure we have the correct signature
    sig_function = _create_signature_check_function(
        requires_item="%s" in service_descr,
        requires_params=ruleset_name is not None,
        original_function=check_info_dict["check_function"],
    )

    # 2) unwrap parameters and ensure it is a generator of valid instances
    @functools.wraps(sig_function)
    def check_result_generator(*args, **kwargs):
        assert not args, "pass arguments as keywords to check function"
        if "params" in kwargs:
            kwargs["params"] = unwrap_parameters(kwargs["params"])

        item_state.reset_wrapped_counters()  # not supported by the new API!

        try:
            subresults = sig_function(**kwargs)
        except TypeError:
            # this handles a very weird case, in which check plugins do not have an '%s'
            # in their description (^= no item) but do in fact discover an empty string.
            # We cannot just append "%s" to the service description, because in that case
            # our tests complain about the ruleset not being for plugins with item :-(
            # Just retry without item:
            subresults = sig_function(**{k: v for k, v in kwargs.items() if k != "item"})

        if subresults is None:
            return

        if isinstance(subresults, tuple):  # just one result
            subresults = [subresults]

        # Once we have seen a newline in *any* subresult,
        # all remaining output is sent to the details page!
        # I'm not saying that is good, but we stay compatible.
        is_details = False
        for subresult in subresults:
            is_details = yield from _create_new_result(is_details, *subresult)

        item_state.raise_counter_wrap()

    return check_result_generator


def _create_new_result(
        is_details,  # type: bool
        legacy_state,  # type: int
        legacy_text,  # type: str
        legacy_metrics=(),  # type: Union[Tuple, List]
):
    # type: (...) -> Generator[Union[Metric, Result], None, bool]
    result_state = state(legacy_state)

    if legacy_state or legacy_text:  # skip "Null"-Result
        if is_details:
            summary = None  # type: Optional[str]
            details = legacy_text  # type: Optional[str]
        else:
            is_details = "\n" in legacy_text
            summary, details = legacy_text.split("\n", 1) if is_details else (legacy_text, None)
        yield Result(
            state=result_state,
            summary=summary or None,
            details=details or None,
        )

    for metric in legacy_metrics:
        # fill up with None:
        name, value, warn, crit, min_, max_ = (
            v for v, _ in itertools.zip_longest(metric, range(6)))
        yield Metric(name, value, levels=(warn, crit), boundaries=(min_, max_))

    return is_details


def _create_signature_check_function(
        requires_item,  # type: bool
        requires_params,  # type: bool
        original_function,  # type: Callable
):
    # type: (...) -> Callable
    """Create the function for a check function with the required signature"""
    if requires_item:
        if requires_params:

            def check_migration_wrapper(item, params, section):
                return original_function(item, params, section)
        else:
            # suppress "All conditional function variants must have identical signatures"
            def check_migration_wrapper(item, section):  # type: ignore[misc]
                return original_function(item, {}, section)
    else:
        if requires_params:

            def check_migration_wrapper(params, section):  # type: ignore[misc]
                return original_function(None, params, section)
        else:

            def check_migration_wrapper(section):  # type: ignore[misc]
                return original_function(None, {}, section)

    return check_migration_wrapper


def _create_wrapped_parameters(check_plugin_name, check_info_dict):
    # type: (str, Dict[str, Any]) -> Optional[Dict[str, Any]]
    """compute default parameters and wrap them in a dictionary"""
    var_name = check_info_dict.get("default_levels_variable")
    if var_name is None:
        return {} if check_info_dict.get("group") else None

    # look in factory settings
    parameters = config.factory_settings.get(var_name)
    if isinstance(parameters, dict):
        return parameters
    if parameters is not None:
        return wrap_parameters(parameters)

    # look in check context
    parameters = _resolve_string_parameters(var_name, check_plugin_name)
    if isinstance(parameters, dict):
        return parameters
    if parameters is not None:
        return wrap_parameters(parameters)

    raise ValueError("[%s]: default levels variable %r is undefined" %
                     (check_plugin_name, var_name))


def _create_cluster_legacy_mode_from_hell(check_function):
    # type: (Callable) -> Callable
    @functools.wraps(check_function)
    def cluster_legacy_mode_from_hell(*args, **kwargs):
        raise NotImplementedError("This just a dummy to pass validation.")
        yield  # pylint: disable=unreachable

    cluster_legacy_mode_from_hell.__name__ = CLUSTER_LEGACY_MODE_FROM_HELL
    return cluster_legacy_mode_from_hell


def create_check_plugin_from_legacy(check_plugin_name, check_info_dict, forbidden_names):
    # type: (str, Dict[str, Any], List[PluginName]) -> CheckPlugin

    if check_info_dict.get('extra_sections'):
        raise NotImplementedError("[%s]: cannot auto-migrate plugins with extra sections" %
                                  check_plugin_name)

    if check_info_dict.get("node_info"):
        # We refuse to tranform these. The requirement of adding the node info
        # makes rewriting of the base code too difficult.
        # Affected Plugins must be migrated manually after CMK-4240 is done.
        raise NotImplementedError("[%s]: cannot auto-migrate plugins with node info" %
                                  check_plugin_name)

    # make sure we haven't missed something important:
    unconsidered_keys = set(check_info_dict) - CONSIDERED_KEYS
    assert not unconsidered_keys, ("Unconsidered key(s) in check_info[%r]: %r" %
                                   (check_plugin_name, unconsidered_keys))

    new_check_name = maincheckify(check_plugin_name)

    check_default_parameters = _create_wrapped_parameters(check_plugin_name, check_info_dict)

    discovery_function = _create_discovery_function(check_plugin_name, check_info_dict)

    check_ruleset_name = check_info_dict.get("group")
    if check_ruleset_name is None and check_default_parameters is not None:
        check_ruleset_name = DUMMY_RULESET_NAME
    check_function = _create_check_function(
        check_plugin_name,
        check_info_dict,
        check_ruleset_name,
    )

    return create_check_plugin(
        name=new_check_name,
        sections=[check_plugin_name.split('.', 1)[0]],
        service_name=check_info_dict['service_description'],
        discovery_function=discovery_function,
        discovery_default_parameters=None,  # legacy madness!
        discovery_ruleset_name=None,
        check_function=check_function,
        check_default_parameters=check_default_parameters,
        check_ruleset_name=check_ruleset_name,
        cluster_check_function=_create_cluster_legacy_mode_from_hell(check_function),
        forbidden_names=forbidden_names,
    )


def maincheckify(subcheck_name):
    # type: (str) -> str
    """Get new plugin name

    The new API does not know about "subchecks", so drop the dot notation.
    The validation step will prevent us from having colliding plugins.
    """
    return subcheck_name.replace('.', '_')


@functools.lru_cache()
def resolve_legacy_name(plugin_name):
    # type: (PluginName) -> str
    """Get legacy plugin name back"""
    # TODO (mo): remove this with CMK-4295. Function is only needed during transition
    for legacy_name in config.check_info:
        if str(plugin_name) == maincheckify(legacy_name):
            return legacy_name
    # nothing found, it may be a new plugin, which is OK.
    return str(plugin_name)


PARAMS_WRAPPER_KEY = "auto-migration-wrapper-key"


def wrap_parameters(parameters):
    # type: (Any) -> Dict[str, Any]
    if isinstance(parameters, dict):
        return parameters
    return {PARAMS_WRAPPER_KEY: parameters}


def unwrap_parameters(parameters):
    # type: (Union[Dict[str, Any], Parameters]) -> Any
    if isinstance(parameters, Parameters):
        # In the new API check_functions will be passed an immutable mapping
        # instead of a dict. However, we have way too many 'if isinsance(params, dict)'
        # call sites to introduce this into legacy code, so use the plain dict.
        parameters = parameters._data

    if PARAMS_WRAPPER_KEY not in parameters:
        return parameters
    assert len(parameters) == 1, "unexpected keys in parameters: %r" % (parameters,)
    return parameters[PARAMS_WRAPPER_KEY]
