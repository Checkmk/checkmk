#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import abc
import copy
import os
import types
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, NamedTuple
from unittest import mock

import pytest

from cmk.utils.hostaddress import HostName
from cmk.utils.legacy_check_api import LegacyCheckDefinition

from cmk.checkengine.checking import CheckPluginName


class MissingCheckInfoError(KeyError):
    pass


class BaseCheck(abc.ABC):
    """Abstract base class for Check and ActiveCheck"""

    def __init__(self, name: str) -> None:
        self.name = name
        # we cant use the current_host context, b/c some tests rely on a persistent
        # item state across several calls to run_check
        import cmk.base.plugin_contexts  # pylint: disable=import-outside-toplevel,cmk-module-layer-violation

        cmk.base.plugin_contexts._hostname = HostName("non-existent-testhost")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"


class Check(BaseCheck):
    def __init__(self, name: str) -> None:
        from cmk.base import (  # pylint: disable=import-outside-toplevel,cmk-module-layer-violation
            config,
        )
        from cmk.base.api.agent_based import register  # pylint: disable=import-outside-toplevel

        super().__init__(name)
        if self.name not in config.check_info:
            raise MissingCheckInfoError(self.name)
        info = config.check_info[self.name]
        assert isinstance(info, LegacyCheckDefinition)
        self.info = info
        self._migrated_plugin = register.get_check_plugin(
            CheckPluginName(self.name.replace(".", "_"))
        )

    def default_parameters(self) -> Mapping[str, Any]:
        if self._migrated_plugin:
            return self._migrated_plugin.check_default_parameters or {}
        return {}

    def run_parse(self, info: list) -> object:
        if self.info.parse_function is None:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no parse function defined")
        return self.info.parse_function(info)

    def run_discovery(self, info: object) -> Any:
        if self.info.discovery_function is None:
            raise MissingCheckInfoError(
                "Check '%s' " % self.name + "has no discovery function defined"
            )
        return self.info.discovery_function(info)

    def run_check(self, item: object, params: object, info: object) -> Any:
        if self.info.check_function is None:
            raise MissingCheckInfoError("Check '%s' " % self.name + "has no check function defined")
        return self.info.check_function(item, params, info)


class ActiveCheck(BaseCheck):
    def __init__(self, name: str) -> None:
        from cmk.base import (  # pylint: disable=import-outside-toplevel,cmk-module-layer-violation
            config,
        )

        super().__init__(name)
        self.info = config.active_check_info.get(self.name[len("check_") :])

    def run_argument_function(self, params: Mapping[str, object]) -> Sequence[str]:
        assert self.info, "Active check has to be implemented in the legacy API"
        return self.info["argument_function"](params)

    def run_service_description(self, params: object) -> object:
        assert self.info, "Active check has to be implemented in the legacy API"
        return self.info["service_description"](params)

    def run_generate_icmp_services(self, host_config: object, params: object) -> object:
        assert self.info, "Active check has to be implemented in the legacy API"
        yield from self.info["service_generator"](host_config, params)


class SpecialAgent:
    def __init__(self, name: str) -> None:
        from cmk.base import (  # pylint: disable=import-outside-toplevel,cmk-module-layer-violation
            config,
        )

        super().__init__()
        self.name = name
        assert self.name.startswith(
            "agent_"
        ), "Specify the full name of the active check, e.g. agent_3par"
        self.argument_func = config.special_agent_info[self.name[len("agent_") :]]


class Tuploid:
    """Base class for values with (potentially variadic) tuple representations"""

    def __eq__(self, other_value):
        if isinstance(other_value, self.__class__):
            return other_value.tuple == self.tuple
        if isinstance(other_value, tuple):
            return all(x == y for x, y in zip(other_value, self.tuple))
        return None

    def __ne__(self, other_value):
        return not self.__eq__(other_value)

    @property
    def tuple(self):
        raise NotImplementedError()

    def __iter__(self):
        yield from self.tuple


class PerfValue(Tuploid):
    """Represents a single perf value"""

    def __init__(
        self,
        key: str,
        value: int | float | None,
        warn: int | float | None = None,
        crit: int | float | None = None,
        minimum: int | float | None = None,
        maximum: int | float | None = None,
    ) -> None:
        # assign first, so __repr__ won't crash
        self.key = key
        self.value = value
        self.warn = warn
        self.crit = crit
        self.minimum = minimum
        self.maximum = maximum

        # TODO: This is very basic. There is more way more magic involved
        #       in what kind of values are allowed as metric names.
        #       I'm not too sure unicode should be allowed, either.
        assert isinstance(key, str), "PerfValue: key %r must be of type str or unicode" % key
        #       Whitespace leads to serious errors
        assert len(key.split()) == 1, "PerfValue: key %r must not contain whitespaces" % key
        #       Parsing around this is way too funky and doesn't work properly
        for c in "=\n":
            assert c not in key, f"PerfValue: key {key!r} must not contain {c!r}"
        # NOTE: The CMC as well as all other Nagios-compatible cores do accept a
        #       string value that may contain a unit, which is in turn available
        #       for use in PNP4Nagios templates. Checkmk defines its own semantic
        #       context for performance values using Checkmk metrics. It is therefore
        #       preferred to return a "naked" scalar.
        msg = "PerfValue: %s parameter %r must be of type int, float or None - not %r"
        assert isinstance(value, (int, float)), msg.replace(" or None", "") % (
            "value",
            value,
            type(value),
        )
        for n in ("warn", "crit", "minimum", "maximum"):
            v = getattr(self, n)
            assert v is None or isinstance(v, (int, float)), msg % (n, v, type(v))

    @property
    def tuple(self):
        return (self.key, self.value, self.warn, self.crit, self.minimum, self.maximum)

    def __repr__(self) -> str:
        return "PerfValue(%r, %r, %r, %r, %r, %r)" % self.tuple


def assertPerfValuesEqual(actual, expected):
    """
    Compare two PerfValues.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, PerfValue), "not a PerfValue: %r" % actual
    assert isinstance(expected, PerfValue), "not a PerfValue: %r" % expected
    assert expected.key == actual.key, f"expected {expected!r}, but key is {actual.key!r}"
    assert expected.value == pytest.approx(actual.value), "expected {!r}, but value is {!r}".format(
        expected,
        actual.value,
    )
    assert (
        pytest.approx(expected.warn, rel=0.1) == actual.warn
    ), "expected {!r}, but warn is {!r}".format(
        expected,
        actual.warn,
    )
    assert (
        pytest.approx(expected.crit, rel=0.1) == actual.crit
    ), "expected {!r}, but crit is {!r}".format(
        expected,
        actual.crit,
    )
    assert expected.minimum == actual.minimum, "expected {!r}, but minimum is {!r}".format(
        expected,
        actual.minimum,
    )
    assert expected.maximum == actual.maximum, "expected {!r}, but maximum is {!r}".format(
        expected,
        actual.maximum,
    )


class BasicCheckResult(Tuploid):
    """
    A basic check result

    This class models a basic check result (status, infotext, perfdata) and provides
    facilities to match it against conditions, such as 'Status is...' or
    'Infotext contains...'
    """

    def __init__(
        self, status: int, infotext: str, perfdata: None | Sequence[tuple | PerfValue] = None
    ) -> None:
        """We perform some basic consistency checks during initialization"""
        # assign first, so __repr__ won't crash
        self.status = status
        self.infotext = infotext
        self.perfdata = []
        self.multiline = None

        assert status in [
            0,
            1,
            2,
            3,
        ], f"BasicCheckResult: status must be in (0, 1, 2, 3) - not {status!r}"

        assert isinstance(
            infotext, str
        ), "BasicCheckResult: infotext {!r} must be of type str or unicode - not {!r}".format(
            infotext,
            type(infotext),
        )
        if "\n" in infotext:
            self.infotext, self.multiline = infotext.split("\n", 1)

        if perfdata is not None:
            tp = type(perfdata)
            assert (
                tp == list
            ), "BasicCheckResult: perfdata {!r} must be of type list - not {!r}".format(
                perfdata,
                tp,
            )
            for entry in perfdata:
                te = type(entry)
                assert te in [tuple, PerfValue], (
                    "BasicCheckResult: perfdata entry %r must be of type "
                    "tuple or PerfValue - not %r" % (entry, te)
                )
                if isinstance(entry, tuple):
                    self.perfdata.append(PerfValue(*entry))
                else:
                    self.perfdata.append(entry)

    @property
    def tuple(self):
        return (self.status, self.infotext, self.perfdata, self.multiline)

    def __repr__(self) -> str:
        return "BasicCheckResult(%r, %r, %r, multiline=%r)" % self.tuple


def assertBasicCheckResultsEqual(actual, expected):
    """
    Compare two BasicCheckResults.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, BasicCheckResult), "not a BasicCheckResult: %r" % actual
    assert isinstance(expected, BasicCheckResult), "not a BasicCheckResult: %r" % expected

    msg = "expected %s, but %%s is %%r" % repr(expected).replace("%", "%%")
    assert expected.status == actual.status, msg % ("status", actual.status)

    diff_idx = len(os.path.commonprefix((expected.infotext, actual.infotext)))
    diff_msg = ", differing at char %r" % diff_idx
    assert actual.infotext == expected.infotext, msg % ("infotext", actual.infotext) + diff_msg

    perf_count = len(actual.perfdata)
    assert perf_count == len(expected.perfdata), msg % ("perfdata count", perf_count)
    for pact, pexp in zip(actual.perfdata, expected.perfdata):
        assertPerfValuesEqual(pact, pexp)

    assert actual.multiline == expected.multiline, msg % ("multiline", actual.multiline)


class CheckResult:
    """
    A check result potentially consisting of multiple subresults,
    as returned by yield-style checks

    Initializing test results using this has the following advantages:
    -Some basic consistency checks are being performed, making sure the
     check's result conforms to the API
    -A common interface to test assertions is provided, regardless of whether
     or not the check uses subresults via the yield-API
    -The check's code is being run, and doesn't disappear in the yield-APIs
     generator-induced laziness.
    """

    def __init__(self, result: Iterable | None | CheckResult) -> None:
        """
        Initializes a list of subresults using BasicCheckResult.

        If the result is already a plain check result in its tuple representation,
        we initialize a list of length 1.
        """
        self.subresults = []
        if result is None:
            return
        if isinstance(result, CheckResult):
            self.__dict__ = result.__dict__
            return

        if isinstance(result, types.GeneratorType):
            for subresult in result:
                self.subresults.append(BasicCheckResult(*subresult))
        # creation of a CheckResult via a list of
        # tuple or BasicCheckResult for test writing
        elif isinstance(result, list):
            for subresult in result:
                ts = type(subresult)
                assert ts in (tuple, BasicCheckResult), (
                    "CheckResult: subresult %r must be of type tuple or "
                    "BasicCheckResult - not %r" % (subresult, ts)
                )
                if isinstance(subresult, tuple):
                    subresult = BasicCheckResult(*subresult)
                self.subresults.append(subresult)
        else:
            assert isinstance(result, tuple)
            self.subresults.append(BasicCheckResult(*result))

    def __repr__(self) -> str:
        return "CheckResult(%r)" % self.subresults

    def __eq__(self, other):
        if not isinstance(other, CheckResult):
            return False
        return all(s1 == s2 for (s1, s2) in zip(self.subresults, other.subresults))

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def perfdata(self):
        perfdata = []
        for subresult in self.subresults:
            perfdata += subresult.perfdata if subresult.perfdata else []
        return perfdata

    def raw_repr(self):
        rr = []
        for sr in self.subresults:
            sr_perf = [p.tuple for p in sr.perfdata]
            sr_text = sr.infotext
            if sr.multiline:
                sr_text += "\n" + sr.multiline
            rr.append((sr.status, sr_text, sr_perf))
        return rr


def assertCheckResultsEqual(actual, expected):
    """
    Compare two (Basic)CheckResults.

    This gives more helpful output than 'assert actual == expected'
    """
    if isinstance(actual, BasicCheckResult):
        assertBasicCheckResultsEqual(actual, expected)

    else:
        assert isinstance(actual, CheckResult), "%r is not a CheckResult instance" % actual
        assert isinstance(expected, CheckResult), "%r is not a CheckResult instance" % expected
        for suba, sube in zip(actual.subresults, expected.subresults):
            assertBasicCheckResultsEqual(suba, sube)
        len_ac, len_ex = len(actual.subresults), len(expected.subresults)
        assert len_ac == len_ex, "expected %d subresults, but got %d instead" % (len_ex, len_ac)


class DiscoveryEntry(Tuploid):
    """A single entry as returned by the discovery function."""

    @staticmethod
    def _normalize_params(p: dict | None) -> dict:
        return {} if p is None else p

    def __init__(self, entry: tuple[str | None, dict | None]) -> None:
        self.item = entry[0]
        self.default_params = self._normalize_params(entry[1])
        assert self.item is None or isinstance(self.item, str)

    @property
    def tuple(self) -> tuple[str | None, dict]:
        return self.item, self.default_params

    def __repr__(self) -> str:
        return f"DiscoveryEntry{self.tuple!r}"


class DiscoveryResult:
    """
    The result of the discovery as a whole.

    Much like in the case of the check result, this also makes sure
    that yield-based discovery functions run, and that no exceptions
    get lost in the laziness.
    """

    def __init__(self, result: Sequence[tuple[str | None, dict | None]] = ()) -> None:
        self.entries = sorted((DiscoveryEntry(e) for e in result), key=repr)

    def __eq__(self, other):
        return self.entries == other.entries

    def __repr__(self) -> str:
        return f"DiscoveryResult({self.entries!r})"


def assertDiscoveryResultsEqual(check, actual, expected):
    """
    Compare two DiscoveryResults.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, DiscoveryResult), "%r is not a DiscoveryResult instance" % actual
    assert isinstance(expected, DiscoveryResult), "%r is not a DiscoveryResult instance" % expected
    assert len(actual.entries) == len(
        expected.entries
    ), f"DiscoveryResults entries are not of equal length: {actual!r} != {expected!r}"

    for enta, ente in zip(actual.entries, expected.entries):
        item_a, default_params_a = enta
        item_e, default_params_e = ente
        assert item_a == item_e, f"items differ: {item_a!r} != {item_e!r}"
        assert (
            default_params_a == default_params_e
        ), "default parameters differ: {!r} != {!r}".format(
            default_params_a,
            default_params_e,
        )


class BasicItemState:
    """Item state as returned by get_item_state

    We assert that we have exactly two values,
    where the first one is either float or int.
    """

    def __init__(self, *args) -> None:  # type: ignore[no-untyped-def]
        if len(args) == 1:
            args = args[0]
        msg = "BasicItemState: expected 2-tuple (time_diff, value) - not %r"
        assert isinstance(args, tuple), msg % args
        assert len(args) == 2, msg % args
        self.time_diff, self.value = args

        time_diff_type = type(self.time_diff)
        msg = "BasicItemState: time_diff should be of type float/int - not %r"
        assert time_diff_type in (float, int), msg % time_diff_type
        # We do allow negative time diffs.
        # We want to be able to test time anomalies.


class _MockValueStore:
    def __init__(self, getter: Callable) -> None:
        self._getter = getter

    def get(self, key, default=None):
        return self._getter(key, default)

    def __setitem__(self, key, value):
        pass


class _MockVSManager(NamedTuple):
    active_service_interface: _MockValueStore


def mock_item_state(mock_state):
    """Mock the calls to item_state API.

    Usage:

    with mock_item_state(mock_state):
        # run your check test here
        mocked_time_diff, mocked_value = \
            cmk.base.item_state.get_item_state('whatever_key', default="IGNORED")

    There are three different types of arguments to pass to mock_item_state:

    1) Callable object:
        The callable object will replace `get_item_state`. It must accept two
        arguments (key/default), in same way a dictionary does.

    2) Dictionary:
        The dictionary will replace the item states.
        Basically `get_item_state` gets replaced by the dictionaries GET method.

    3) Anything else:
        All calls to the item_state API behave as if the last state had
        been `mock_state`

    See for example 'test_statgrab_cpu_check.py'.
    """
    target = "cmk.agent_based.v1.value_store._active_host_value_store"

    getter = (  #
        mock_state.get
        if isinstance(mock_state, dict)
        else (mock_state if callable(mock_state) else lambda key, default: mock_state)  #
    )

    return mock.patch(target, _MockVSManager(_MockValueStore(getter)))


class MockHostExtraConf:
    """Mock the calls to get_host_values.

    Due to our rather unorthodox import structure, we cannot mock
    get_host_merged_dict directly (it's a global var in running checks!)
    Instead, we mock the calls to cmk.base.config.get_host_values.

    Passing a single dict to this objects init method will result in
    get_host_merged_dict returning said dict.

    You can also pass a list of dicts, but that's rather pointless, as
    get_host_merged_dict will return a merged dict, the result of

        merged_dict = {}
        for d in reversed(list_of_dicts):
            merged_dict.update(d)
    .

    Usage:

    with MockHostExtraConf(mockconfig):
        # run your check test here,
        # get_host_merged_dict in your check will return
        # mockconfig

    See for example 'test_df_check.py'.
    """

    def __init__(
        self,
        check: object,
        mock_config: Callable | dict[object, object],
        target: str = "get_host_values",
    ) -> None:
        self.target = target
        self.context: Any = None  # TODO: Figure out the right type
        self.check = check
        self.config = mock_config

    def __call__(self, _hostname, _ruleset):
        # ensure the default value is sane
        if hasattr(self.config, "__call__"):
            return self.config(_hostname, _ruleset)

        if self.target == "get_host_values" and isinstance(self.config, dict):
            return [self.config]
        return self.config

    def __enter__(self):
        """The default context: just mock get_item_state"""
        import cmk.base.config  # pylint: disable=import-outside-toplevel,cmk-module-layer-violation

        # we can't use get_config_cache here because it may lead to flakiness
        config_cache = cmk.base.config.reset_config_cache()
        self.context = mock.patch.object(
            config_cache.ruleset_matcher,
            self.target,
            # I'm the MockObj myself!
            new_callable=lambda: self,
        )
        assert self.context is not None
        return self.context.__enter__()

    def __exit__(self, *exc_info):
        assert self.context is not None
        return self.context.__exit__(*exc_info)


class ImmutablesChangedError(AssertionError):
    pass


class Immutables:
    """Store some data and ensure it is not changed"""

    def __init__(self) -> None:
        self.refs: dict = {}
        self.copies: dict = {}

    def register(self, v, k=None):
        if k is None:
            k = id(v)
        self.refs[k] = v
        self.copies[k] = copy.deepcopy(v)

    def test(self, descr=""):
        for k in self.refs:
            try:
                assertEqual(self.refs[k], self.copies[k], repr(k) + descr)
            except AssertionError as exc:
                raise ImmutablesChangedError(exc) from exc


def assertEqual(first, second, descr=""):
    """Help finding diffs in epic dicts or iterables"""
    if first == second:
        return

    assert isinstance(
        first, type(second)
    ), "{}differing type: {!r} != {!r} for values {!r} and {!r}".format(
        descr,
        type(first),
        type(second),
        first,
        second,
    )

    if isinstance(first, dict):
        remainder = set(second.keys())
        for k in first:
            assert k in second, f"{descr}additional key {k!r} in {first!r}"
            remainder.remove(k)
            assertEqual(first[k], second[k], descr + " [%s]" % repr(k))
        assert not remainder, f"{descr}missing keys {list(remainder)!r} in {first!r}"

    if isinstance(first, (list, tuple)):
        assert len(first) == len(second), f"{descr}varying length: {first!r} != {second!r}"
        for (c, fst), snd in zip(enumerate(first), second):
            assertEqual(fst, snd, descr + "[%d] " % c)

    raise AssertionError(f"{descr}not equal ({type(first)!r}): {first!r} != {second!r}")
