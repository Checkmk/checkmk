#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import os
import types
from typing import List

import mock
import pytest  # type: ignore[import]

from cmk.base.item_state import MKCounterWrapped
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel
from cmk.base.check_api_utils import Service


class Tuploid:
    """Base class for values with (potentially variadic) tuple representations"""
    def __eq__(self, other_value):
        if isinstance(other_value, self.__class__):
            return other_value.tuple == self.tuple
        if isinstance(other_value, tuple):
            return all(x == y for x, y in zip(other_value, self.tuple))

    def __ne__(self, other_value):
        return not self.__eq__(other_value)

    @property
    def tuple(self):
        raise NotImplementedError()

    def __iter__(self):
        for x in self.tuple:
            yield x


class PerfValue(Tuploid):
    """Represents a single perf value"""
    def __init__(self, key, value, warn=None, crit=None, minimum=None, maximum=None):
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
        assert isinstance(key, str),\
               "PerfValue: key %r must be of type str or unicode" % key
        #       Whitespace leads to serious errors
        assert len(key.split()) == 1, \
               "PerfValue: key %r must not contain whitespaces" % key
        #       Parsing around this is way too funky and doesn't work properly
        for c in "=\n":
            assert c not in key, "PerfValue: key %r must not contain %r" % (key, c)
        # NOTE: The CMC as well as all other Nagios-compatible cores do accept a
        #       string value that may contain a unit, which is in turn available
        #       for use in PNP4Nagios templates. Checkmk defines its own semantic
        #       context for performance values using Checkmk metrics. It is therefore
        #       preferred to return a "naked" scalar.
        msg = "PerfValue: %s parameter %r must be of type int, float or None - not %r"
        assert isinstance(value, (int, float)),\
               msg.replace(' or None', '') % ('value', value, type(value))
        for n in ('warn', 'crit', 'minimum', 'maximum'):
            v = getattr(self, n)
            assert v is None or isinstance(v, (int, float)), msg % (n, v, type(v))

    @property
    def tuple(self):
        return (self.key, self.value, self.warn, self.crit, self.minimum, self.maximum)

    def __repr__(self):
        return "PerfValue(%r, %r, %r, %r, %r, %r)" % self.tuple


def assertPerfValuesEqual(actual, expected):
    """
    Compare two PerfValues.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, PerfValue), "not a PerfValue: %r" % actual
    assert isinstance(expected, PerfValue), "not a PerfValue: %r" % expected
    assert expected.key == actual.key, "expected %r, but key is %r" % (expected, actual.key)
    assert expected.value == pytest.approx(
        actual.value), "expected %r, but value is %r" % (expected, actual.value)
    assert expected.warn == actual.warn, "expected %r, but warn is %r" % (expected, actual.warn)
    assert expected.crit == actual.crit, "expected %r, but crit is %r" % (expected, actual.crit)
    assert expected.minimum == actual.minimum, "expected %r, but minimum is %r" % (expected,
                                                                                   actual.minimum)
    assert expected.maximum == actual.maximum, "expected %r, but maximum is %r" % (expected,
                                                                                   actual.maximum)


class BasicCheckResult(Tuploid):
    """
    A basic check result

    This class models a basic check result (status, infotext, perfdata) and provides
    facilities to match it against conditions, such as 'Status is...' or
    'Infotext contains...'
    """
    def __init__(self, status, infotext, perfdata=None):
        """We perform some basic consistency checks during initialization"""
        # assign first, so __repr__ won't crash
        self.status = status
        self.infotext = infotext
        self.perfdata = []
        self.multiline = None

        assert status in [0, 1, 2, 3], \
               "BasicCheckResult: status must be in (0, 1, 2, 3) - not %r" % (status,)

        assert isinstance(infotext, str), \
                "BasicCheckResult: infotext %r must be of type str or unicode - not %r" % \
                (infotext, type(infotext))
        if "\n" in infotext:
            self.infotext, \
            self.multiline = infotext.split("\n", 1)

        if perfdata is not None:
            tp = type(perfdata)
            assert tp == list, \
                   "BasicCheckResult: perfdata %r must be of type list - not %r" \
                   % (perfdata, tp)
            for entry in perfdata:
                te = type(entry)
                assert te in [tuple, PerfValue], \
                       "BasicCheckResult: perfdata entry %r must be of type " \
                       "tuple or PerfValue - not %r" % (entry, te)
                if isinstance(entry, tuple):
                    self.perfdata.append(PerfValue(*entry))
                else:
                    self.perfdata.append(entry)

    @property
    def tuple(self):
        return (self.status, self.infotext, self.perfdata, self.multiline)

    def __repr__(self):
        return 'BasicCheckResult(%r, %r, %r, multiline=%r)' % self.tuple


def assertBasicCheckResultsEqual(actual, expected):
    """
    Compare two BasicCheckResults.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, BasicCheckResult), "not a BasicCheckResult: %r" % actual
    assert isinstance(expected, BasicCheckResult), "not a BasicCheckResult: %r" % expected

    msg = "expected %s, but %%s is %%r" % repr(expected).replace('%', '%%')
    assert expected.status == actual.status, msg % ("status", actual.status)

    diff_idx = len(os.path.commonprefix((expected.infotext, actual.infotext)))
    diff_msg = ", differing at char %r" % diff_idx
    assert expected.infotext == actual.infotext, msg % ("infotext", actual.infotext) + diff_msg

    perf_count = len(actual.perfdata)
    assert len(expected.perfdata) == perf_count, msg % ("perfdata count", perf_count)
    for pact, pexp in zip(actual.perfdata, expected.perfdata):
        assertPerfValuesEqual(pact, pexp)

    assert expected.multiline == actual.multiline, msg % ("multiline", actual.multiline)


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
    def __init__(self, result):
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
                assert ts in (tuple, BasicCheckResult), \
                       "CheckResult: subresult %r must be of type tuple or " \
                       "BasicCheckResult - not %r" % (subresult, ts)
                if isinstance(subresult, tuple):
                    subresult = BasicCheckResult(*subresult)
                self.subresults.append(subresult)
        else:
            self.subresults.append(BasicCheckResult(*result))

    def __repr__(self):
        return 'CheckResult(%r)' % self.subresults

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
                sr_text += '\n' + sr.multiline
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
        assert isinstance(actual, CheckResult), \
               "%r is not a CheckResult instance" % actual
        assert isinstance(expected, CheckResult), \
               "%r is not a CheckResult instance" % expected
        for suba, sube in zip(actual.subresults, expected.subresults):
            assertBasicCheckResultsEqual(suba, sube)
        len_ac, len_ex = len(actual.subresults), len(expected.subresults)
        assert len_ac == len_ex, "expected %d subresults, but got %d instead" % (len_ex, len_ac)


class DiscoveryEntry(Tuploid):
    """A single entry as returned by the discovery (or in oldspeak: inventory) function."""
    def __init__(self, entry):
        # hack for ServiceLabel
        if isinstance(entry, Service):
            self.item, self.default_params, self.service_labels = entry.item, entry.parameters, entry.service_labels
        else:
            self.item, self.default_params = entry
        ti = type(self.item)
        assert self.item is None or isinstance(self.item, str), \
               "DiscoveryEntry: item %r must be of type str, unicode or None - not %r" \
               % (self.item, type(ti))

    @property
    def tuple(self):
        return (self.item, self.default_params)

    def __repr__(self):
        return "DiscoveryEntry(%r, %r)" % self.tuple


class DiscoveryResult:
    """
    The result of the discovery as a whole.

    Much like in the case of the check result, this also makes sure
    that yield-based discovery functions run, and that no exceptions
    get lost in the laziness.
    """

    # TODO: Add some more consistency checks here.
    def __init__(self, result=()):
        self.entries = []
        self.labels = DiscoveredHostLabels()
        if not result:
            # discovering nothing is valid!
            return
        for entry in result:
            if isinstance(entry, DiscoveredHostLabels):
                self.labels += entry
            elif isinstance(entry, HostLabel):
                self.labels.add_label(entry)
            # preparation for ServiceLabel Discovery
            #elif isinstance(entry, Service):
            #
            else:
                self.entries.append(DiscoveryEntry(entry))
        self.entries.sort(key=repr)

    def __eq__(self, other):
        return self.entries == other.entries and self.labels == other.labels

    # TODO: Very questionable __repr__ conversion, leading to even more
    # interesting typing Kung Fu...
    def __repr__(self) -> str:
        entries: List[object] = [o for o in self.entries if isinstance(o, object)]
        host_labels: List[object] = [HostLabel(str(k), str(self.labels[k])) for k in self.labels]
        return "DiscoveryResult(%r)" % (entries + host_labels,)

    # TODO: Very obscure and inconsistent __str__ conversion...
    def __str__(self):
        return "%s%s" % ([tuple(e) for e in self.entries
                         ], [self.labels[k].label for k in self.labels])


def assertDiscoveryResultsEqual(check, actual, expected):
    """
    Compare two DiscoveryResults.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, DiscoveryResult), \
           "%r is not a DiscoveryResult instance" % actual
    assert isinstance(expected, DiscoveryResult), \
           "%r is not a DiscoveryResult instance" % expected
    assert len(actual.entries) == len(expected.entries), \
           "DiscoveryResults entries are not of equal length: %r != %r" % (actual, expected)

    for enta, ente in zip(actual.entries, expected.entries):
        item_a, default_params_a = enta
        if isinstance(default_params_a, str):
            default_params_a = eval(default_params_a, check.context, check.context)

        item_e, default_params_e = ente
        if isinstance(default_params_e, str):
            default_params_e = eval(default_params_e, check.context, check.context)

        assert item_a == item_e, "items differ: %r != %r" % (item_a, item_e)
        assert default_params_a == default_params_e, "default parameters differ: %r != %r" % (
            default_params_a, default_params_e)

    assert len(actual.labels) == len(expected.labels), \
           "DiscoveryResults labels are not of equal length: %s != %s" % (actual.labels.to_dict(), expected.labels.to_dict())

    # iterate over the HostLabels in DiscoveredHostLabels, not lable string
    for laba, labe in zip(actual.labels.to_list(), expected.labels.to_list()):
        assert laba == labe, "discovered host labels differ: expected %r got %r" % (laba, labe)


class BasicItemState:
    """Item state as returned by get_item_state

    We assert that we have exactly two values,
    where the first one is either float or int.
    """
    def __init__(self, *args):
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


class MockItemState:
    """Mock the calls to item_state API.

    Due to our rather unorthodox import structure, we cannot mock
    cmk.base.item_state.get_item_state directly (it's a global var
    in running checks!)
    Instead, this context manager mocks
    cmk.base.item_state._cached_item_states.get_item_state.

    This will affect get_rate and get_average as well as
    get_item_state.

    Usage:

    with MockItemState(mock_state):
        # run your check test here
        mocked_time_diff, mocked_value = \
            cmk.base.item_state.get_item_state('whatever_key', default="IGNORED")

    There are three different types of arguments to pass to MockItemState:

    1) Callable object:
        The callable object will replace `get_item_state`. It must accept two
        arguments (key/default), in same way a dictionary does.

    2) Dictionary:
        The dictionary will replace the item states.
        Basically `get_item_state` gets replaced by the dictionaries GET method.

    3) Anything else:
        All calls to the item_state API behave as if the last state had
        been `value`, recorded
        `time_diff` seconds ago.

    See for example 'test_statgrab_cpu_check.py'.
    """
    TARGET = 'cmk.base.item_state._cached_item_states.get_item_state'

    def __init__(self, mock_state):
        self.context = None

        if hasattr(mock_state, '__call__'):
            self.get_val_function = mock_state
        elif isinstance(mock_state, dict):
            self.get_val_function = mock_state.get  # in dict case check values
        else:
            self.get_val_function = lambda key, default: mock_state

    def __call__(self, user_key, default=None):
        val = self.get_val_function(user_key, default)
        return val

    def __enter__(self):
        '''The default context: just mock get_item_state'''
        self.context = mock.patch(
            MockItemState.TARGET,
            # I'm the MockObj myself!
            new_callable=lambda: self)
        return self.context.__enter__()

    def __exit__(self, *exc_info):
        assert self.context is not None
        return self.context.__exit__(*exc_info)


class assertMKCounterWrapped:
    """Contextmanager in which a MKCounterWrapped exception is expected

    If you can choose to also assert a certain error message:

    with MockItemState((1., -42)):
        with assertMKCounterWrapped("value is negative"):
            # do a check that raises such an exception
            run_my_check()

    Or you can ignore the exact error message:

    with MockItemState((1., -42)):
        with assertMKCounterWrapped():
            # do a check that raises such an exception
            run_my_check()

    See for example 'test_statgrab_cpu_check.py'.
    """
    def __init__(self, msg=None):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, ty, ex, tb):
        if ty is AssertionError:
            raise
        assert ty is not None, "assertMKCounterWrapped: no exception has occurred"
        assert ty == MKCounterWrapped, \
               "assertMKCounterWrapped: %r is not of type %r" % (ex, MKCounterWrapped)
        if self.msg is not None:
            assert self.msg == str(ex), "assertMKCounterWrapped: %r != %r" \
                   % (self.msg, str(ex))
        return True


class MockHostExtraConf:
    """Mock the calls to host_extra_conf.

    Due to our rather unorthodox import structure, we cannot mock
    host_extra_conf_merged directly (it's a global var in running checks!)
    Instead, we mock the calls to cmk.base.config.host_extra_conf.

    Passing a single dict to this objects init method will result in
    host_extra_conf_merged returning said dict.

    You can also pass a list of dicts, but that's rather pointless, as
    host_extra_conf_merged will return a merged dict, the result of

        merged_dict = {}
        for d in reversed(list_of_dicts):
            merged_dict.update(d)
    .

    Usage:

    with MockHostExtraConf(mockconfig):
        # run your check test here,
        # host_extra_conf_merged in your check will return
        # mockconfig

    See for example 'test_df_check.py'.
    """
    def __init__(self, check, mock_config, target="host_extra_conf"):
        self.target = target
        self.context = None
        self.check = check
        self.config = mock_config

    def __call__(self, _hostname, _ruleset):
        # ensure the default value is sane
        if hasattr(self.config, '__call__'):
            return self.config(_hostname, _ruleset)

        if self.target == "host_extra_conf" and isinstance(self.config, dict):
            return [self.config]
        return self.config

    def __enter__(self):
        '''The default context: just mock get_item_state'''
        import cmk.base.config  # pylint: disable=import-outside-toplevel
        config_cache = cmk.base.config.get_config_cache()
        self.context = mock.patch.object(
            config_cache,
            self.target,
            # I'm the MockObj myself!
            new_callable=lambda: self)
        return self.context.__enter__()

    def __exit__(self, *exc_info):
        assert self.context is not None
        return self.context.__exit__(*exc_info)


class ImmutablesChangedError(AssertionError):
    pass


class Immutables:
    """Store some data and ensure it is not changed"""
    def __init__(self):
        self.refs = {}
        self.copies = {}

    def register(self, v, k=None):
        if k is None:
            k = id(v)
        self.refs.__setitem__(k, v)
        self.copies.__setitem__(k, copy.deepcopy(v))

    def test(self, descr=''):
        for k in self.refs:
            try:
                assertEqual(self.refs[k], self.copies[k], repr(k) + descr)
            except AssertionError as exc:
                raise ImmutablesChangedError(exc) from exc


def assertEqual(first, second, descr=''):
    """Help finding diffs in epic dicts or iterables"""
    if first == second:
        return

    assert isinstance(first, type(second)), ("%sdiffering type: %r != %r for values %r and %r" %
                                             (descr, type(first), type(second), first, second))

    if isinstance(first, dict):
        remainder = set(second.keys())
        for k in first:
            assert k in second, "%sadditional key %r in %r" % (descr, k, first)
            remainder.remove(k)
            assertEqual(first[k], second[k], descr + " [%s]" % repr(k))
        assert not remainder, "%smissing keys %r in %r" % (descr, list(remainder), first)

    if isinstance(first, (list, tuple)):
        assert len(first) == len(second), "%svarying length: %r != %r" % (descr, first, second)
        for (c, fst), snd in zip(enumerate(first), second):
            assertEqual(fst, snd, descr + "[%d] " % c)

    raise AssertionError("%snot equal (%r): %r != %r" % (descr, type(first), first, second))
