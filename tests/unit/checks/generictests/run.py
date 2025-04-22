#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Submodule providing the `run` function of generictests package"""

import datetime
from contextlib import contextmanager

import time_machine

from ..checktestlib import (
    assertCheckResultsEqual,
    assertDiscoveryResultsEqual,
    assertEqual,
    Check,
    CheckResult,
    DiscoveryResult,
    Immutables,
    MissingCheckInfoError,
    mock_item_state,
)
from .checkhandler import checkhandler


class DiscoveryParameterTypeError(AssertionError):
    pass


def get_info_argument(dataset, subcheck, fallback_parsed=None):
    """Get the argument to the discovery/check function

    This may be the info variable or the parsed variable.
    """
    # see if we have a parsed result defined
    tmp = getattr(dataset, "parsed", None)
    if tmp is not None:
        return tmp

    # see if we produced one earlier
    if fallback_parsed is not None:
        return fallback_parsed

    # fall back to use info.
    try:
        return dataset.info
    except AttributeError:
        raise AttributeError("dataset has neither of the attributes 'info' or 'parsed'")


def get_merged_parameters(check, provided_p):
    default_p = check.default_parameters()

    if isinstance(provided_p, int | tuple):
        return provided_p
    if not provided_p:
        return default_p

    # legacy, no longer supported
    assert not isinstance(provided_p, str)

    if isinstance(provided_p, dict):
        default_p.update(provided_p)
        return default_p
    raise DiscoveryParameterTypeError(f"unhandled: {default_p!r}/{provided_p!r}")


def get_mock_values(dataset, subcheck):
    return getattr(dataset, "mock_item_state", {}).get(subcheck, {})


def get_discovery_expected(subcheck, dataset):
    """Return expected DiscoveryResult"""
    discovery_dict = getattr(dataset, "discovery", {})
    discovery_raw = discovery_dict.get(subcheck, [])
    return DiscoveryResult(discovery_raw)


def get_discovery_actual(check: Check, info_arg: object, immu: Immutables) -> DiscoveryResult:
    """Validate and return actual DiscoveryResult"""

    disco_func = check.info.discovery_function
    if not disco_func:
        return DiscoveryResult()

    d_result_raw = check.run_discovery(info_arg)
    immu.test(" after discovery (%s): " % disco_func.__name__)

    return DiscoveryResult(d_result_raw)


def run_test_on_parse(dataset, immu):
    """Test parse function

    If dataset has .info attribute and the check has parse function defined,
    test it, and return the result. Otherwise return None.
    If the .parsed attribute is present, it is compared to the result.
    """
    info = getattr(dataset, "info", None)
    parsed_expected = getattr(dataset, "parsed", None)

    if info is None:
        return None

    immu.register(dataset.info, "info")

    main_check: Check | None = None

    try:
        main_check = Check(dataset.checkname)
        parse_function = main_check.info.parse_function
    except MissingCheckInfoError:
        # this could be ok -
        # it just implies we don't have a parse function
        parse_function = None

    if parsed_expected is not None:
        # we *must* have a parse function in this case!
        assert parse_function, f"{dataset.checkname} has no parse function!"
    elif not parse_function:  # we may not have one:
        return None

    if main_check:
        parsed = main_check.run_parse(info)
        if parsed_expected is not None:
            assertEqual(parsed, parsed_expected, " parsed result ")

        immu.test(" after parse function ")
        immu.register(parsed, "parsed")

        return parsed


def run_test_on_discovery(check, subcheck, dataset, info_arg, immu):
    d_result_act = get_discovery_actual(check, info_arg, immu)
    d_result_exp = get_discovery_expected(subcheck, dataset)
    assertDiscoveryResultsEqual(check, d_result_act, d_result_exp)


def run_test_on_checks(check, subcheck, dataset, info_arg, immu):
    """Run check for test case listed in dataset"""
    test_cases = getattr(dataset, "checks", {}).get(subcheck, [])

    for item, params, results_expected_raw in test_cases:
        immu.register(params, "params")

        result = CheckResult(check.run_check(item, params, info_arg))

        immu.test(" after check (%s): " % check.info.check_function.__name__)

        result_expected = CheckResult(results_expected_raw)

        assertCheckResultsEqual(result, result_expected)


@contextmanager
def optional_freeze_time(dataset):
    """Optionally freeze of the time in generic dataset tests

    If present and truish the datasets freeze_time attribute is passed to
    time_machine.travel.
    """
    if getattr(dataset, "freeze_time", None):
        with time_machine.travel(datetime.datetime.fromisoformat(dataset.freeze_time)):
            yield
    else:
        yield


def run(check_info, dataset):
    """Run all possible tests on 'dataset'"""
    checklist = checkhandler.get_applicables(dataset.checkname, check_info)
    assert checklist, f"Found no check plug-in for {dataset.checkname!r}"

    immu = Immutables()

    with optional_freeze_time(dataset):
        parsed = run_test_on_parse(dataset, immu)

        # LOOP OVER ALL (SUB)CHECKS
        subcheck: str | None = None
        for sname in checklist:
            subcheck = (sname + ".").split(".")[1]
            check = Check(sname)

            info_arg = get_info_argument(dataset, subcheck, parsed)
            immu.test(" after get_info_argument ")
            immu.register(info_arg, "info_arg")

            item_state = get_mock_values(dataset, subcheck)

            with mock_item_state(item_state):
                run_test_on_discovery(check, subcheck, dataset, info_arg, immu)

                run_test_on_checks(check, subcheck, dataset, info_arg, immu)

        if subcheck:
            immu.test(f" at end of subcheck loop {subcheck!r} ")
