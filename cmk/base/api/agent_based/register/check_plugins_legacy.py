#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
import copy
from contextlib import suppress
import functools
import itertools

from cmk.utils.check_utils import maincheckify, wrap_parameters, unwrap_parameters

from cmk.base import item_state
from cmk.base.api.agent_based.checking_classes import (
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
from cmk.base.api.agent_based.register.utils import DUMMY_RULESET_NAME
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import Parameters
from cmk.base.check_api_utils import Service as LegacyService
from cmk.base.check_utils import get_default_parameters
from cmk.base.discovered_labels import HostLabel, DiscoveredHostLabels

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
    get_check_context: Callable,
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
                    labels=[ServiceLabel(l.name, l.value) for l in element.service_labels],
                )
            elif isinstance(element, tuple) and len(element) in (2, 3):
                parameters = _resolve_string_parameters(element[-1], check_name, get_check_context)
                service = Service(
                    item=element[0] or None,
                    parameters=wrap_parameters(parameters or {}),
                )
                # nasty hack for nasty plugins:
                # Bypass validation. Item should be None or non-empty string!
                service = service._replace(item=element[0])
                yield service
            else:
                # just let it through. Base must deal with bogus return types anyway.
                yield element

    return discovery_migration_wrapper


def _resolve_string_parameters(
    params_unresolved: Any,
    check_name: str,
    get_check_context: Callable,
) -> Any:
    if not isinstance(params_unresolved, str):
        return params_unresolved

    try:
        context = get_check_context(check_name)
        # string may look like '{"foo": bar}', in the worst case.
        return eval(params_unresolved, context, context)
    except Exception:
        raise ValueError("Invalid check parameter string '%s' found in discovered service %r" %
                         (params_unresolved, check_name))


def _create_check_function(name: str, check_info_dict: Dict[str, Any],
                           ruleset_name: Optional[str]) -> Callable:
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
            parameters = kwargs["params"]
            if isinstance(parameters, Parameters):
                # In the new API check_functions will be passed an immutable mapping
                # instead of a dict. However, we have way too many 'if isinsance(params, dict)'
                # call sites to introduce this into legacy code, so use the plain dict.
                parameters = copy.deepcopy(parameters._data)
            kwargs["params"] = unwrap_parameters(parameters)

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


def _get_float(raw_value: Any) -> Optional[float]:
    """Try to convert to float

        >>> _get_float("12.3s")
        12.3

    """
    with suppress(TypeError, ValueError):
        return float(raw_value)

    if not isinstance(raw_value, str):
        return None
    # try to cut of units:
    for i in range(len(raw_value) - 1, 0, -1):
        with suppress(TypeError, ValueError):
            return float(raw_value[:i])

    return None


def _create_new_result(
        is_details: bool,
        legacy_state: int,
        legacy_text: str,
        legacy_metrics: Union[Tuple, List] = (),
) -> Generator[Union[Metric, Result], None, bool]:
    result_state = State(legacy_state)

    if legacy_state or legacy_text:  # skip "Null"-Result
        if is_details:
            summary = ""
            details = legacy_text
        else:
            is_details = "\n" in legacy_text
            summary, details = legacy_text.split("\n", 1) if is_details else (legacy_text, "")
        # Bypass the validation of the Result class:
        # Legacy plugins may relie on the fact that once a newline
        # as been in the output, *all* following ouput is sent to
        # the details. That means we have to create Results with
        # details only, which is prohibited by the original Result
        # class.
        yield Result(state=result_state, summary="Fake")._replace(
            summary=summary,
            details=details,
        )

    for metric in legacy_metrics:
        if len(metric) < 2:
            continue
        name = str(metric[0])
        value = _get_float(metric[1])
        if value is None:  # skip bogus metrics
            continue
        # fill up with None:
        warn, crit, min_, max_ = (
            _get_float(v) for v, _ in itertools.zip_longest(metric[2:], range(4)))
        yield Metric(name, value, levels=(warn, crit), boundaries=(min_, max_))

    return is_details


def _create_signature_check_function(
    requires_item: bool,
    requires_params: bool,
    original_function: Callable,
) -> Callable:
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


def _create_wrapped_parameters(
    check_plugin_name: str,
    check_info_dict: Dict[str, Any],
    factory_settings: Dict[str, Dict],
    get_check_context: Callable,
) -> Optional[Dict[str, Any]]:
    """compute default parameters and wrap them in a dictionary"""
    default_parameters = get_default_parameters(
        check_info_dict,
        factory_settings,
        get_check_context(check_plugin_name),
    )
    if default_parameters is None:
        return {} if check_info_dict.get("group") else None

    if isinstance(default_parameters, dict):
        return default_parameters
    return wrap_parameters(default_parameters)


def _create_cluster_legacy_mode_from_hell(check_function: Callable) -> Callable:
    # copy signature of check function:
    @functools.wraps(check_function, ('__attributes__',))
    def cluster_legacy_mode_from_hell(*args, **kwargs):
        raise NotImplementedError("This just a dummy to pass validation is.")
        yield  # pylint: disable=unreachable

    return cluster_legacy_mode_from_hell


def create_check_plugin_from_legacy(
    check_plugin_name: str,
    check_info_dict: Dict[str, Any],
    extra_sections: List[str],
    factory_settings: Dict[str, Dict],
    get_check_context: Callable,
    *,
    validate_creation_kwargs: bool = True,
) -> CheckPlugin:

    if extra_sections:
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

    check_default_parameters = _create_wrapped_parameters(
        check_plugin_name,
        check_info_dict,
        factory_settings,
        get_check_context,
    )

    discovery_function = _create_discovery_function(
        check_plugin_name,
        check_info_dict,
        get_check_context,
    )

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
        # Legacy check plugins may return an item even if the service description
        # does not contain a '%s'. In this case the old check API assumes an implicit,
        # trailing '%s'. Therefore, we disable this validation for legacy check plugins.
        # Once all check plugins are migrated to the new API this flag can be removed.
        validate_item=False,
        validate_kwargs=validate_creation_kwargs,
    )
