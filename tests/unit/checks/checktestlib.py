#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import copy
import os
import types
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple
from unittest import mock

import pytest

from tests.testlib.common.repo import repo_path

import cmk.utils.paths

from cmk.agent_based.legacy import discover_legacy_checks, FileLoader, find_plugin_files
from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition


class MissingCheckInfoError(KeyError):
    pass


class Check:
    _LEGACY_CHECKS: dict[str, LegacyCheckDefinition] = {}

    @classmethod
    def _load_checks(cls) -> None:
        for legacy_check in discover_legacy_checks(
            find_plugin_files(repo_path() / "cmk/base/legacy_checks"),
            FileLoader(
                precomile_path=cmk.utils.paths.precompiled_checks_dir,
                makedirs=lambda path: Path(path).mkdir(mode=0o770, exist_ok=True, parents=True),
            ),
            raise_errors=True,
        ).sane_check_info:
            cls._LEGACY_CHECKS[legacy_check.name] = legacy_check

    def __init__(self, name: str) -> None:
        self.name = name
        if not self._LEGACY_CHECKS:
            self._load_checks()

        if (info := self._LEGACY_CHECKS.get(name)) is None:
            raise MissingCheckInfoError(self.name)

        self.info = info

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r})"

    def default_parameters(self) -> Mapping[str, Any]:
        return self.info.check_default_parameters or {}

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
        assert isinstance(value, int | float), msg.replace(" or None", "") % (
            "value",
            value,
            type(value),
        )
        for n in ("warn", "crit", "minimum", "maximum"):
            v = getattr(self, n)
            assert v is None or isinstance(v, int | float), msg % (n, v, type(v))

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
    assert expected.value == pytest.approx(actual.value), (
        f"expected {expected!r}, but value is {actual.value!r}"
    )
    assert pytest.approx(expected.warn, rel=0.1) == actual.warn, (
        f"expected {expected!r}, but warn is {actual.warn!r}"
    )
    assert pytest.approx(expected.crit, rel=0.1) == actual.crit, (
        f"expected {expected!r}, but crit is {actual.crit!r}"
    )
    assert expected.minimum == actual.minimum, (
        f"expected {expected!r}, but minimum is {actual.minimum!r}"
    )
    assert expected.maximum == actual.maximum, (
        f"expected {expected!r}, but maximum is {actual.maximum!r}"
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

        assert isinstance(infotext, str), (
            f"BasicCheckResult: infotext {infotext!r} must be of type str or unicode - not {type(infotext)!r}"
        )
        if "\n" in infotext:
            self.infotext, self.multiline = infotext.split("\n", 1)

        if perfdata is not None:
            tp = type(perfdata)
            assert tp is list, (
                f"BasicCheckResult: perfdata {perfdata!r} must be of type list - not {tp!r}"
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
    assert len(actual.entries) == len(expected.entries), (
        f"DiscoveryResults entries are not of equal length: {actual!r} != {expected!r}"
    )

    for enta, ente in zip(actual.entries, expected.entries):
        item_a, default_params_a = enta
        item_e, default_params_e = ente
        assert item_a == item_e, f"items differ: {item_a!r} != {item_e!r}"
        assert default_params_a == default_params_e, (
            f"default parameters differ: {default_params_a!r} != {default_params_e!r}"
        )


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

    assert isinstance(first, type(second)), (
        f"{descr}differing type: {type(first)!r} != {type(second)!r} for values {first!r} and {second!r}"
    )

    if isinstance(first, dict):
        remainder = set(second.keys())
        for k in first:
            assert k in second, f"{descr}additional key {k!r} in {first!r}"
            remainder.remove(k)
            assertEqual(first[k], second[k], descr + " [%s]" % repr(k))
        assert not remainder, f"{descr}missing keys {list(remainder)!r} in {first!r}"

    if isinstance(first, list | tuple):
        assert len(first) == len(second), f"{descr}varying length: {first!r} != {second!r}"
        for (c, fst), snd in zip(enumerate(first), second):
            assertEqual(fst, snd, descr + "[%d] " % c)

    raise AssertionError(f"{descr}not equal ({type(first)!r}): {first!r} != {second!r}")
