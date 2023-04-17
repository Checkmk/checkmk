#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-style section based on config.check_info
"""
import copy
import functools
import itertools
from collections import defaultdict
from collections.abc import Callable, Generator, Iterable
from contextlib import suppress
from typing import Any

from cmk.utils.check_utils import maincheckify, unwrap_parameters, wrap_parameters

from cmk.checkers import Parameters

from cmk.base import item_state  # pylint: disable=cmk-module-layer-violation
from cmk.base.api.agent_based.checking_classes import (
    CheckPlugin,
    CheckResult,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.api.agent_based.register.check_plugins import create_check_plugin
from cmk.base.api.agent_based.type_defs import ParametersTypeAlias

from .utils_legacy import CheckInfoElement


def _create_discovery_function(
    check_name: str,
    check_info_element: CheckInfoElement,
    check_context: dict[str, object],
) -> Callable:
    """Create an API compliant discovery function"""

    # 1) ensure we have the correct signature
    # 2) ensure it is a generator of Service instances
    def discovery_migration_wrapper(section: object) -> object:
        disco_func = check_info_element.get("inventory_function")
        if not callable(disco_func):  # never discover:
            return

        original_discovery_result = disco_func(section)
        if not original_discovery_result:
            return

        for element in original_discovery_result:
            if isinstance(element, Service):
                yield element
                continue

            if isinstance(element, tuple) and len(element) in (2, 3):
                item, raw_params = element[0], element[-1]
                if item is not None and not isinstance(item, str):
                    raise ValueError("item must be None or of type `str`")

                parameters = _resolve_string_parameters(raw_params, check_name, check_context)
                service = Service(
                    item=None,  # will be replaced
                    parameters=wrap_parameters(parameters or {}),
                )
                # nasty hack for nasty plugins: item = ''
                # Bypass validation. Item should be None or non-empty string!
                service = service._replace(item=item)
                yield service
                continue

            # just let it through. Base must deal with bogus return types anyway.
            yield element

    return discovery_migration_wrapper


def _resolve_string_parameters(
    params_unresolved: Any,
    check_name: str,
    context: dict[str, object],
) -> Any:
    if not isinstance(params_unresolved, str):
        return params_unresolved

    try:
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


def _normalize_check_function_return_value(subresults: object) -> list:
    """Normalize the return value of a check function

    Check functions are known to (and *should*) either return
     * None
     * a single subresult (a tuple)
     * a list of subresults
     * a generator of subresults

    However, anything that was an iterable of subresults worked in the past, so we just try our
    best to normalize it.
    """
    if subresults is None:
        return []
    if isinstance(subresults, tuple):
        return [subresults]
    if isinstance(subresults, Iterable):
        return list(subresults)
    raise TypeError(f"expected None, Tuple or Iterable, got {subresults=}")


def _create_check_function(name: str, check_info_element: CheckInfoElement) -> Callable:
    """Create an API compliant check function"""
    service_descr = check_info_element["service_description"]
    if not isinstance(service_descr, str):
        raise ValueError(f"[{name}]: invalid service description: {service_descr!r}")

    # 1) ensure we have the correct signature
    requires_item = "%s" in service_descr
    sig_function = _create_signature_check_function(
        requires_item=requires_item,
        original_function=check_info_element["check_function"],
    )

    # 2) unwrap parameters and ensure it is a generator of valid instances
    @functools.wraps(sig_function)
    def check_result_generator(*args, **kwargs) -> CheckResult:  # type: ignore[no-untyped-def]
        assert not args, "pass arguments as keywords to check function"
        assert "params" in kwargs, f"'params' is missing in kwargs: {kwargs!r}"
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

        subresults = _normalize_check_function_return_value(sig_function(**kwargs))

        for idx, subresult in enumerate(subresults):
            if isinstance(subresult, (Result, Metric)):
                yield subresult
                continue

            if "\n" in subresult[1]:
                yield from _create_new_results_with_details(subresults[idx:])
                break

            yield from _create_new_result(*subresult)

        item_state.raise_counter_wrap()

    return check_result_generator


def _create_new_results_with_details(
    results: list,
) -> CheckResult:
    state_sorted = defaultdict(list)
    for result in results:
        if isinstance(result, (Result, Metric)):
            yield result
            continue
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

        if len(details) == 0:
            continue

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


def _get_float(raw_value: Any) -> float | None:
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
    legacy_metrics: tuple | list = (),
) -> CheckResult:
    if legacy_state or legacy_text:  # skip "Null"-Result
        yield Result(state=State(legacy_state), summary=legacy_text.strip())
    yield from _create_new_metric(legacy_metrics)


def _create_new_metric(legacy_metrics: tuple | list = ()) -> Generator[Metric, None, None]:
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
) -> Callable[..., tuple | Iterable[tuple | Result | Metric]]:
    """Create the function for a check function with the required signature"""
    if requires_item:

        def check_migration_wrapper(item, params, section):
            return original_function(item, params, section)

    else:

        def check_migration_wrapper(params, section):  # type: ignore[misc]
            return original_function(None, params, section)

    return check_migration_wrapper


def _create_wrapped_parameters(
    check_info_element: CheckInfoElement,
    factory_settings: dict[str, dict],
) -> ParametersTypeAlias:
    """compute default parameters and wrap them in a dictionary"""
    if (params_variable_name := check_info_element.get("default_levels_variable")) is None:
        return {}

    default_parameters = factory_settings[params_variable_name]
    if isinstance(default_parameters, dict):
        return default_parameters
    return wrap_parameters(default_parameters)


def create_check_plugin_from_legacy(
    check_plugin_name: str,
    check_info_element: CheckInfoElement,
    factory_settings: dict[str, dict],
    check_context: dict[str, object],
    *,
    validate_creation_kwargs: bool = True,
) -> CheckPlugin:
    # We only intend to deal with checks from our repo.
    # We know what we can and have to deal with.
    if (
        unexpected_keys := set(check_info_element)
        - CheckInfoElement.__optional_keys__
        - CheckInfoElement.__required_keys__
    ):
        raise ValueError(
            f"Unexpected key(s) in check_info[{check_plugin_name!r}]: {unexpected_keys!r}"
        )

    new_check_name = maincheckify(check_plugin_name)

    check_default_parameters = _create_wrapped_parameters(
        check_info_element,
        factory_settings,
    )

    discovery_function = _create_discovery_function(
        check_plugin_name,
        check_info_element,
        check_context,
    )

    check_function = _create_check_function(
        check_plugin_name,
        check_info_element,
    )

    return create_check_plugin(
        name=new_check_name,
        sections=[check_plugin_name.split(".", 1)[0]],
        service_name=check_info_element["service_description"],
        discovery_function=discovery_function,
        discovery_default_parameters=None,  # legacy madness!
        discovery_ruleset_name=None,
        check_function=check_function,
        check_default_parameters=check_default_parameters,
        check_ruleset_name=check_info_element.get("group"),
        # Legacy check plugins may return an item even if the service description
        # does not contain a '%s'. In this case the old check API assumes an implicit,
        # trailing '%s'. Therefore, we disable this validation for legacy check plugins.
        # Once all check plugins are migrated to the new API this flag can be removed.
        validate_item=False,
        validate_kwargs=validate_creation_kwargs,
    )
