#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
import copy
import functools
import itertools
from collections import defaultdict
from contextlib import suppress
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

from cmk.utils.check_utils import maincheckify, unwrap_parameters, wrap_parameters

from cmk.base import item_state  # pylint: disable=cmk-module-layer-violation
from cmk.base.api.agent_based.checking_classes import CheckPlugin, Metric, Result, Service, State
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
from cmk.base.api.agent_based.type_defs import Parameters, ParametersTypeAlias

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


def _get_default_parameters(
    check_legacy_info: Dict[str, Any],
    factory_settings: Dict[str, Dict[str, Any]],
    check_context: Dict[str, Any],
) -> Optional[ParametersTypeAlias]:
    """compute default parameters"""
    params_variable_name = check_legacy_info.get("default_levels_variable")
    if not params_variable_name:
        return None

    # factory_settings
    fs_parameters = factory_settings.get(params_variable_name, {})

    # global scope of check context
    gs_parameters = check_context.get(params_variable_name)

    return (
        {
            **fs_parameters,
            **gs_parameters,
        }
        if isinstance(gs_parameters, dict)
        else fs_parameters
    )


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
            if isinstance(element, tuple) and len(element) in (2, 3):
                item, raw_params = element[0], element[-1]
                if item is not None and not isinstance(item, str):
                    raise ValueError("item must be None or of type `str`")

                parameters = _resolve_string_parameters(raw_params, check_name, get_check_context)
                service = Service(
                    item=None,  # will be replaced
                    parameters=wrap_parameters(parameters or {}),
                )
                # nasty hack for nasty plugins: item = ''
                # Bypass validation. Item should be None or non-empty string!
                service = service._replace(item=item)
                yield service
                continue

            with suppress(AttributeError):
                yield Service(
                    item=element.item,
                    parameters=wrap_parameters(element.parameters or {}),
                    # there used to be labels, but they are no longer supported
                )
                continue

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
        # This evaluation was needed in the past to resolve references to variables in context and
        # to evaluate data structure declarations containing references to variables.
        # Since Checkmk 2.0 we have a better API and need it only for compatibility. The parameters
        # are resolved now *before* they are written to the autochecks file, and earlier autochecks
        # files are resolved during cmk-update-config.
        return eval(params_unresolved, context, context)  # pylint: disable=eval-used
    except Exception:
        raise ValueError(
            "Invalid check parameter string '%s' found in discovered service %r"
            % (params_unresolved, check_name)
        )


def _create_check_function(name: str, check_info_dict: Dict[str, Any]) -> Callable:
    """Create an API compliant check function"""
    service_descr = check_info_dict["service_description"]
    if not isinstance(service_descr, str):
        raise ValueError("[%s]: invalid service description: %r" % (name, service_descr))

    # 1) ensure we have the correct signature
    requires_item = "%s" in service_descr
    sig_function = _create_signature_check_function(
        requires_item=requires_item,
        original_function=check_info_dict["check_function"],
    )

    # 2) unwrap parameters and ensure it is a generator of valid instances
    @functools.wraps(sig_function)
    def check_result_generator(*args, **kwargs):
        assert not args, "pass arguments as keywords to check function"
        assert "params" in kwargs, "'params' is missing in kwargs: %r" % (kwargs,)
        parameters = kwargs["params"]
        if isinstance(parameters, Parameters):
            # In the new API check_functions will be passed an immutable mapping
            # instead of a dict. However, we have way too many 'if isinsance(params, dict)'
            # call sites to introduce this into legacy code, so use the plain dict.
            parameters = copy.deepcopy(parameters._data)
        kwargs["params"] = unwrap_parameters(parameters)

        item_state.reset_wrapped_counters()  # not supported by the new API!

        if not requires_item:
            # this handles a very weird case, in which check plugins do not have an '%s'
            # in their description (^= no item) but do in fact discover an empty string.
            # We cannot just append "%s" to the service description, because in that case
            # our tests complain about the ruleset not being for plugins with item :-(
            kwargs = {k: v for k, v in kwargs.items() if k != "item"}

        subresults = sig_function(**kwargs)

        if subresults is None:
            return

        if isinstance(subresults, tuple):  # just one result
            subresults = [subresults]
        else:
            subresults = list(subresults)

        # Do we have results with details?
        try:
            idx = next(i for i, val in enumerate(subresults) if "\n" in val[1])
        except StopIteration:
            idx = len(subresults)

        for subresult in subresults[:idx]:
            yield from _create_new_result(*subresult)

        yield from _create_new_results_with_details(subresults[idx:])

        item_state.raise_counter_wrap()

    return check_result_generator


def _create_new_results_with_details(
    results: list,
) -> Generator[Union[Metric, Result], None, None]:
    state_sorted = defaultdict(list)
    for result in results:
        state = State(result[0])
        state_sorted[state].append(result)

    for idx, (state, subresults) in enumerate(state_sorted.items()):
        metrics = []
        details = []
        first_detail = subresults[0][1] if subresults else ""
        for result in subresults:
            if len(result) > 2:
                metrics.extend(list(result[2]))
            details.extend([el for el in result[1].split("\n") if el])

        # we might have an actual summary to use
        if idx == 0 and (s := first_detail.split("\n", 1)[0]):
            summary = s
        else:
            summary = (
                f"{len(details)} additional detail{'' if len(details) == 1 else 's'} available"
            )

        yield Result(
            state=state,
            summary=summary,
            details="\n".join(d.lstrip() for d in details),
        )
        yield from _create_new_metric(metrics)


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
    legacy_state: int,
    legacy_text: str,
    legacy_metrics: Union[Tuple, List] = (),
) -> Generator[Union[Metric, Result], None, None]:

    if legacy_state or legacy_text:  # skip "Null"-Result
        yield Result(state=State(legacy_state), summary=legacy_text.strip())
    yield from _create_new_metric(legacy_metrics)


def _create_new_metric(legacy_metrics: Union[tuple, list] = ()) -> Generator[Metric, None, None]:
    for metric in legacy_metrics:
        if len(metric) < 2:
            continue
        name = str(metric[0])
        value = _get_float(metric[1])
        if value is None:  # skip bogus metrics
            continue
        # fill up with None:
        warn, crit, min_, max_ = (
            _get_float(v) for v, _ in itertools.zip_longest(metric[2:], range(4))
        )
        yield Metric(name, value, levels=(warn, crit), boundaries=(min_, max_))


def _create_signature_check_function(
    requires_item: bool,
    original_function: Callable,
) -> Callable:
    """Create the function for a check function with the required signature"""
    if requires_item:

        def check_migration_wrapper(item, params, section):
            return original_function(item, params, section)

    else:

        def check_migration_wrapper(params, section):  # type: ignore[misc]
            return original_function(None, params, section)

    return check_migration_wrapper


def _create_wrapped_parameters(
    check_plugin_name: str,
    check_info_dict: Dict[str, Any],
    factory_settings: Dict[str, Dict],
    get_check_context: Callable,
) -> ParametersTypeAlias:
    """compute default parameters and wrap them in a dictionary"""
    default_parameters = _get_default_parameters(
        check_info_dict,
        factory_settings,
        get_check_context(check_plugin_name),
    )
    if default_parameters is None:
        return {}

    if isinstance(default_parameters, dict):
        return default_parameters
    return wrap_parameters(default_parameters)


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
        raise NotImplementedError(
            "[%s]: cannot auto-migrate plugins with extra sections" % check_plugin_name
        )

    if check_info_dict.get("node_info"):
        # We refuse to tranform these. The requirement of adding the node info
        # makes rewriting of the base code too difficult.
        # Affected Plugins must be migrated manually after CMK-4240 is done.
        raise NotImplementedError(
            "[%s]: cannot auto-migrate plugins with node info" % check_plugin_name
        )

    # make sure we haven't missed something important:
    unconsidered_keys = set(check_info_dict) - CONSIDERED_KEYS
    assert not unconsidered_keys, "Unconsidered key(s) in check_info[%r]: %r" % (
        check_plugin_name,
        unconsidered_keys,
    )

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

    check_function = _create_check_function(
        check_plugin_name,
        check_info_dict,
    )

    return create_check_plugin(
        name=new_check_name,
        sections=[check_plugin_name.split(".", 1)[0]],
        service_name=check_info_dict["service_description"],
        discovery_function=discovery_function,
        discovery_default_parameters=None,  # legacy madness!
        discovery_ruleset_name=None,
        check_function=check_function,
        check_default_parameters=check_default_parameters,
        check_ruleset_name=check_info_dict.get("group"),
        # Legacy check plugins may return an item even if the service description
        # does not contain a '%s'. In this case the old check API assumes an implicit,
        # trailing '%s'. Therefore, we disable this validation for legacy check plugins.
        # Once all check plugins are migrated to the new API this flag can be removed.
        validate_item=False,
        validate_kwargs=validate_creation_kwargs,
    )
