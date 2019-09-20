"""Submodule providing the `run` function of generictests package"""
from __future__ import print_function
from ast import literal_eval

from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual, \
                         CheckResult, assertCheckResultsEqual, \
                         MockHostExtraConf, MockItemState, \
                         Immutables, assertEqual
from testlib import MissingCheckInfoError
from generictests.checkhandler import checkhandler
from contextlib import contextmanager
import freezegun


class DiscoveryParameterTypeError(AssertionError):
    pass


def get_info_argument(dataset, subcheck, fallback_parsed=None):
    """Get the argument to the discovery/check function

    This may be the info variable, the parsed variable,
    and/or including extra sections.
    """
    # see if we have a parsed result defined
    tmp = getattr(dataset, 'parsed', None)
    if tmp is not None:
        arg = [tmp]
    # see if we produced one earlier
    elif fallback_parsed is not None:
        arg = [fallback_parsed]
    # fall back to use info.
    else:
        try:
            arg = [dataset.info]
        except AttributeError:
            raise AttributeError("dataset has neither of the attributes " "'info' or 'parsed'")

    es_dict = getattr(dataset, 'extra_sections', {})
    for es in es_dict.get(subcheck, []):
        arg.append(es)

    if len(arg) == 1:
        return arg[0]
    return arg


def get_merged_parameters(check, provided_p):
    default_p = check.default_parameters()

    if isinstance(provided_p, int):
        return provided_p
    if not provided_p:
        return default_p
    if isinstance(provided_p, str):
        if provided_p in check.context:
            return check.context[provided_p]

        evaluated_params = literal_eval(provided_p)
        default_p.update(evaluated_params)
        return default_p
    if isinstance(provided_p, dict):
        default_p.update(provided_p)
        return default_p
    raise DiscoveryParameterTypeError("unhandled: %r/%r" % (default_p, provided_p))


def get_mock_values(dataset, subcheck):
    mock_is_d = getattr(dataset, 'mock_item_state', {})
    mock_hc_d = getattr(dataset, 'mock_host_conf', {})
    mock_hc_m = getattr(dataset, 'mock_host_conf_merged', {})
    return mock_is_d.get(subcheck, {}), mock_hc_d.get(subcheck, []), mock_hc_m.get(subcheck, {}),


def parse(check_manager, dataset):
    """Test parse function

    If dataset has .info attribute and the check has parse function defined,
    test it, and return the result. Otherwise return None.
    If the .parsed attribute is present, it is compared to the result.
    """
    print("parse: %r" % dataset.checkname)
    info = getattr(dataset, 'info', None)
    parsed_expected = getattr(dataset, 'parsed', None)

    if info is None:
        return None

    try:
        main_check = check_manager.get_check(dataset.checkname)
        parse_function = main_check.info.get("parse_function")
    except MissingCheckInfoError:
        # this could be ok -
        # it just implies we don't have a parse function
        parse_function = None

    if parsed_expected is not None:
        # we *must* have a parse function in this case!
        assert parse_function, "%s has no parse function!" \
                               % dataset.checkname
    elif not parse_function:  # we may not have one:
        return None

    parsed = main_check.run_parse(info)
    if parsed_expected is not None:
        assertEqual(parsed, parsed_expected, ' parsed result ')
    return parsed


def discovery(check, subcheck, dataset, info_arg, immu):
    """Test discovery funciton, return discovery result"""
    print("discovery: %r" % check.name)

    discov_expected = getattr(dataset, 'discovery', {})

    disco_func = check.info.get("inventory_function")
    if discov_expected.get(subcheck):
        # we *must* have a discovery function in this case!
        assert disco_func, "%r has no discovery function!" \
                           % check.name
    if not disco_func:
        return []

    d_result_raw = check.run_discovery(info_arg)
    immu.test(' after discovery (%s): ' % disco_func.__name__)

    d_result = DiscoveryResult(d_result_raw)
    if subcheck in discov_expected:
        d_result_expected = DiscoveryResult(discov_expected[subcheck])
        assertDiscoveryResultsEqual(check, d_result, d_result_expected)

    return d_result


def check_discovered_result(check, discovery_result, info_arg, immu):
    """Run the check on all discovered items with the default parameters.
    We cannot validate the results, but at least make sure we don't crash.
    """
    print("Check %r in check %r" % (discovery_result, check.name))

    item = discovery_result.item

    params = get_merged_parameters(check, discovery_result.default_params)
    immu.register(params, 'params')

    raw_checkresult = check.run_check(item, params, info_arg)
    check_func = check.info.get("check_function")
    immu.test(' after check (%s): ' % check_func.__name__)

    cr = CheckResult(raw_checkresult)

    return (item, params, cr.raw_repr())


def check_listed_result(check, list_entry, info_arg, immu):
    """Run check for all results listed in dataset"""
    item, params, results_expected_raw = list_entry
    print("Dataset item %r in check %r" % (item, check.name))

    immu.register(params, 'params')
    result_raw = check.run_check(item, params, info_arg)
    check_func = check.info.get("check_function")
    immu.test(' after check (%s): ' % check_func.__name__)

    result = CheckResult(result_raw)
    result_expected = CheckResult(results_expected_raw)
    assertCheckResultsEqual(result, result_expected)


@contextmanager
def optional_freeze_time(dataset):
    """Optionally freeze of the time in generic dataset tests

    If present and truish the datasets freeze_time attribute is passed to
    freezegun.freeze_time.
    """
    if getattr(dataset, 'freeze_time', None):
        with freezegun.freeze_time(dataset.freeze_time):
            yield
    else:
        yield


def run(check_manager, dataset, write=False):
    """Run all possible tests on 'dataset'"""
    print("START: %r" % dataset)
    checklist = checkhandler.get_applicables(dataset.checkname)
    assert checklist, "Found no check plugin for %r" % dataset.checkname

    immu = Immutables()

    with optional_freeze_time(dataset):
        # test the parse function
        if hasattr(dataset, 'info'):
            immu.register(dataset.info, 'info')
        parsed = parse(check_manager, dataset)
        immu.test(' after parse function ')

        immu.register(parsed, 'parsed')

        # get the expected check results, if present
        checks_expected = getattr(dataset, 'checks', {})

        # LOOP OVER ALL (SUB)CHECKS
        for sname in checklist:
            subcheck = (sname + '.').split('.')[1]
            check = check_manager.get_check(sname)

            info_arg = get_info_argument(dataset, subcheck, parsed)
            immu.test(' after get_info_argument ')
            immu.register(info_arg, 'info_arg')

            mock_is, mock_hec, mock_hecm = get_mock_values(dataset, subcheck)

            with MockItemState(mock_is), \
                 MockHostExtraConf(check, mock_hec), \
                 MockHostExtraConf(check, mock_hecm, "host_extra_conf_merged"):
                # test discovery
                d_result = discovery(check, subcheck, dataset, info_arg, immu)
                if write:
                    dataset.discovery[subcheck] = [e.tuple for e in d_result]
                    # test checks
                for dr in d_result:
                    cdr = check_discovered_result(check, dr, info_arg, immu)
                    if write and cdr:
                        dataset.checks.setdefault(subcheck, []).append(cdr)
                if not write:
                    for entry in checks_expected.get(subcheck, []):

                        check_listed_result(check, entry, info_arg, immu)

        immu.test(' at end of subcheck loop %r ' % subcheck)
