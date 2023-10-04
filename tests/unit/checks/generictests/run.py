#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Submodule providing the `run` function of generictests package"""
from contextlib import contextmanager

import freezegun

from tests.testlib import Check, MissingCheckInfoError

from cmk.utils.check_utils import maincheckify
from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_contexts import current_host, current_service

from ..checktestlib import (
    assertCheckResultsEqual,
    assertDiscoveryResultsEqual,
    assertEqual,
    CheckResult,
    DiscoveryResult,
    Immutables,
    mock_item_state,
    MockHostExtraConf,
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

    if isinstance(provided_p, (int, tuple)):
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
    mock_is_d = getattr(dataset, "mock_item_state", {})
    mock_hc_d = getattr(dataset, "mock_host_conf", {})
    mock_hc_m = getattr(dataset, "mock_host_conf_merged", {})
    return mock_is_d.get(subcheck, {}), mock_hc_d.get(subcheck, []), mock_hc_m.get(subcheck, {})


def get_discovery_expected(subcheck, dataset):
    """Return expected DiscoveryResult"""
    discovery_dict = getattr(dataset, "discovery", {})
    discovery_raw = discovery_dict.get(subcheck, [])
    return DiscoveryResult(discovery_raw)


def get_discovery_actual(check: Check, info_arg: object, immu: Immutables) -> DiscoveryResult:
    """Validate and return actual DiscoveryResult"""
    print(f"discovery: {check.name!r}")

    disco_func = check.info.get("discovery_function")
    if not disco_func:
        return DiscoveryResult()

    d_result_raw = check.run_discovery(info_arg)
    immu.test(" after discovery (%s): " % disco_func.__name__)

    d_result = DiscoveryResult(d_result_raw)
    for entry in d_result.entries:
        params = get_merged_parameters(check, entry.default_params)
        validate_discovered_params(check, params)

    return d_result


def validate_discovered_params(check, params):
    """Validate params with respect to the rule's valuespec"""
    # TODO CMK-4180
    return
    # if not params:
    #     return

    # # get the rule's valuespec
    # rulespec_group = check.info.get("group")
    # if rulespec_group is None:
    #     return

    # key = "checkgroup_parameters:%s" % (rulespec_group,)
    # if key in rulespec_registry:
    #     spec = rulespec_registry[key].valuespec
    # else:
    #     # Static checks still don't work. For example the test for
    #     # domino_tasks. For the moment just skip
    #     # key_sc = "static_checks:%s" % (rulespec_group,)
    #     return

    # # We need to handle one exception: In the ps params, the key 'cpu_rescale_max'
    # # *may* be 'None'. However, this is deliberately not allowed by the valuespec,
    # # to force the user to make a choice. The 'Invalid Parameter' message in this
    # # case does make sense, as it encourages the user to open and update the
    # # parameters. See Werk 6646
    # if 'cpu_rescale_max' in params:
    #     params = params.copy()
    #     params.update(cpu_rescale_max=True)

    # print("Loading %r with prams %r" % (key, params))
    # spec.validate_value(params, "")


def run_test_on_parse(dataset, immu):
    """Test parse function

    If dataset has .info attribute and the check has parse function defined,
    test it, and return the result. Otherwise return None.
    If the .parsed attribute is present, it is compared to the result.
    """
    print(f"parse: {dataset.checkname!r}")
    info = getattr(dataset, "info", None)
    parsed_expected = getattr(dataset, "parsed", None)

    if info is None:
        return None

    immu.register(dataset.info, "info")
    try:
        main_check = Check(dataset.checkname)
        parse_function = main_check.info.get("parse_function")
    except MissingCheckInfoError:
        # this could be ok -
        # it just implies we don't have a parse function
        parse_function = None

    if parsed_expected is not None:
        # we *must* have a parse function in this case!
        assert parse_function, f"{dataset.checkname} has no parse function!"
    elif not parse_function:  # we may not have one:
        return None

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
    check_func = check.info.get("check_function")
    check_plugin_name = CheckPluginName(maincheckify(check.name))

    for item, params, results_expected_raw in test_cases:
        print(f"Dataset item {item!r} in check {check.name!r}")
        immu.register(params, "params")

        with current_service(check_plugin_name, "unit test description"):
            result = CheckResult(check.run_check(item, params, info_arg))

        immu.test(" after check (%s): " % check_func.__name__)

        result_expected = CheckResult(results_expected_raw)

        assertCheckResultsEqual(result, result_expected)


@contextmanager
def optional_freeze_time(dataset):
    """Optionally freeze of the time in generic dataset tests

    If present and truish the datasets freeze_time attribute is passed to
    freezegun.freeze_time.
    """
    if getattr(dataset, "freeze_time", None):
        with freezegun.freeze_time(dataset.freeze_time):
            yield
    else:
        yield


def run(check_info, dataset):
    """Run all possible tests on 'dataset'"""
    print(f"START: {dataset!r}")
    checklist = checkhandler.get_applicables(dataset.checkname, check_info)
    assert checklist, f"Found no check plugin for {dataset.checkname!r}"

    immu = Immutables()

    with optional_freeze_time(dataset):
        parsed = run_test_on_parse(dataset, immu)

        # LOOP OVER ALL (SUB)CHECKS
        for sname in checklist:
            subcheck = (sname + ".").split(".")[1]
            check = Check(sname)

            info_arg = get_info_argument(dataset, subcheck, parsed)
            immu.test(" after get_info_argument ")
            immu.register(info_arg, "info_arg")

            mock_is, mock_hec, mock_hecm = get_mock_values(dataset, subcheck)

            with current_host(HostName("non-existent-testhost")), mock_item_state(
                mock_is
            ), MockHostExtraConf(check, mock_hec), MockHostExtraConf(
                check, mock_hecm, "get_host_merged_dict"
            ):
                run_test_on_discovery(check, subcheck, dataset, info_arg, immu)

                run_test_on_checks(check, subcheck, dataset, info_arg, immu)

        immu.test(f" at end of subcheck loop {subcheck!r} ")
