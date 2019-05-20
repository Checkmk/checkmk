import types
import copy
import mock
import pytest
from cmk_base.item_state import MKCounterWrapped


class Tuploid(object):
    """Base class for values with (potentially variadic) tuple representations"""

    def __eq__(self, other_value):
        if isinstance(other_value, self.__class__):
            return other_value.tuple == self.tuple
        elif type(other_value) == tuple:
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
        assert type(key) in [str, unicode],\
               "PerfValue: key %r must be of type str or unicode" % key
        #       Whitespace leads to serious errors
        assert len(key.split()) == 1, \
               "PerfValue: key %r must not contain whitespaces" % key
        #       Parsing around this is way too funky and doesn't work properly
        for c in "=\n":
            assert c not in key, "PerfValue: key %r must not contain %r" % (key, c)
        # NOTE: The CMC as well as all other Nagios-compatible cores do accept a
        #       string value that may contain a unit, which is in turn available
        #       for use in PNP4Nagios templates. Check_MK defines its own semantic
        #       context for performance values using Check_MK metrics. It is therefore
        #       preferred to return a "naked" scalar.
        msg = "PerfValue: %s parameter %r must be of type int, float or None - not %r"
        assert type(value) in [int, float],\
               msg.replace(' or None', '') % ('value', value, type(value))
        for n in ('warn', 'crit', 'minimum', 'maximum'):
            v = getattr(self, n)
            assert type(v) in [int, float, types.NoneType], msg % (n, v, type(v))

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

        ti = type(infotext)
        assert ti in [str, unicode], \
               "BasicCheckResult: infotext %r must be of type str or unicode - not %r" \
               % (infotext, ti)
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
                if type(entry) is tuple:
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
    assert expected.status == actual.status, "expected %r, but status is %r" % (expected,
                                                                                actual.status)
    assert expected.infotext == actual.infotext, "expected %r, but infotext is %r" % (
        expected, actual.infotext)
    assert len(expected.perfdata) == len(
        actual.perfdata), "expected %r, but got %d perfdata" % (expected, len(actual.perfdata))
    for pact, pexp in zip(actual.perfdata, expected.perfdata):
        assertPerfValuesEqual(pact, pexp)
    assert expected.multiline == actual.multiline, "expected %r, but multiline is %r" % (
        expected, actual.multiline)


class CheckResult(object):
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
        assert len(actual.subresults) == len(expected.subresults), \
               "subresults not of equal length (expected %d)" % len(expected.subresults)
        for suba, sube in zip(actual.subresults, expected.subresults):
            assertBasicCheckResultsEqual(suba, sube)


class DiscoveryEntry(Tuploid):
    """A single entry as returned by the discovery (or in oldspeak: inventory) function."""

    def __init__(self, entry):
        self.item, self.default_params = entry
        ti = type(self.item)
        assert ti in [str, unicode, types.NoneType], \
               "DiscoveryEntry: item %r must be of type str, unicode or None - not %r" \
               % (self.item, ti)

    @property
    def tuple(self):
        return (self.item, self.default_params)

    def __repr__(self):
        return "DiscoveryEntry(%r, %r)" % self.tuple


class DiscoveryResult(object):
    """
    The result of the discovery as a whole.

    Much like in the case of the check result, this also makes sure
    that yield-based discovery functions run, and that no exceptions
    get lost in the laziness.
    """

    # TODO: Add some more consistency checks here.
    def __init__(self, result):
        self.entries = []
        if result is None:
            # discovering nothing is valid!
            return
        for entry in result:
            self.entries.append(DiscoveryEntry(entry))
        self.entries.sort(key=repr)

    def __eq__(self, other_value):
        return all(entry in other_value for entry in self) and \
               all(other_entry in self for other_entry in other_value)

    def __contains__(self, value):
        return value in self.entries

    def __iter__(self):
        return iter(self.entries)

    def __repr__(self):
        return "DiscoveryResult(%r)" % map(repr, self)


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
           "DiscoveryResults are not of equal length"
    for enta, ente in zip(actual, expected):
        item_a, default_params_a = enta
        if isinstance(default_params_a, str):
            default_params_a = eval(default_params_a, check.context, check.context)

        item_e, default_params_e = ente
        if isinstance(default_params_e, str):
            default_params_e = eval(default_params_e, check.context, check.context)

        assert item_a == item_e, "items differ: %r != %r" % (item_a, item_e)
        assert default_params_a == default_params_e, "default parameters differ: %r != %r" % (
            default_params_a, default_params_e)


class BasicItemState(object):
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


class MockItemState(object):
    """Mock the calls to item_state API.

    Due to our rather unorthodox import structure, we cannot mock
    cmk_base.item_state.get_item_state directly (it's a global var
    in running checks!)
    Instead, this context manager mocks
    cmk_base.item_state._cached_item_states.get_item_state.

    This will affect get_rate and get_average as well as
    get_item_state.

    Usage:

    with MockItemState(mock_state):
        # run your check test here
        mocked_time_diff, mocked_value = \
            cmk_base.item_state.get_item_state('whatever_key', default="IGNORED")

    There are three different types of arguments to pass to MockItemState:

    1) Callable object:
        The callable object will replace `get_item_state`. It must accept two
        arguments (key/default), in same way a dictionary does.

    2) Dictionary:
        The dictionary will replace the item states.
        Basically `get_item_state` gets replaced by the dictionarys GET method.

    3) Anything else:
        All calls to the item_state API behave as if the last state had
        been `value`, recorded
        `time_diff` seeconds ago.

    See for example 'test_statgrab_cpu_check.py'.
    """
    TARGET = 'cmk_base.item_state._cached_item_states.get_item_state'

    def __init__(self, mock_state):
        self.context = None
        self.get_val_function = None

        if hasattr(mock_state, '__call__'):
            self.get_val_function = mock_state
            return

        # in dict case check values
        if isinstance(mock_state, dict):
            self.get_val_function = mock_state.get
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
        return self.context.__exit__(*exc_info)


class assertMKCounterWrapped(object):
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


class MockHostExtraConf(object):
    """Mock the calls to host_extra_conf.

    Due to our rather unorthodox import structure, we cannot mock
    host_extra_conf_merged directly (it's a global var in running checks!)
    Instead, we mock the calls to cmk_base.config.host_extra_conf.

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
        if callable(self.config):
            return self.config(_hostname, _ruleset)

        if self.target == "host_extra_conf" and isinstance(self.config, dict):
            return [self.config]
        return self.config

    def __enter__(self):
        '''The default context: just mock get_item_state'''
        import cmk_base.config
        config_cache = cmk_base.config.get_config_cache()
        self.context = mock.patch.object(
            config_cache,
            self.target,
            # I'm the MockObj myself!
            new_callable=lambda: self)
        return self.context.__enter__()

    def __exit__(self, *exc_info):
        return self.context.__exit__(*exc_info)


class ImmutablesChangedError(AssertionError):
    pass


class Immutables(object):
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
        for k in self.refs.keys():
            try:
                assertEqual(self.refs[k], self.copies[k], repr(k) + descr)
            except AssertionError as e:
                raise ImmutablesChangedError(e.message)


def assertEqual(first, second, descr=''):
    """Help finding diffs in epic dicts or iterables"""
    if first == second:
        return

    assert type(first) == type(second), "%sdiffering type: %r != %r for values %r and %r" \
        % (descr, type(first), type(second), first, second)

    if isinstance(first, dict):
        remainder = set(second.keys())
        for k in first:
            assert k in second, "%sadditional key %r in %r" \
                % (descr, k, first)
            remainder.remove(k)
            assertEqual(first[k], second[k], descr + " [%r]" % k)
        assert not remainder, "%smissing keys %r in %r" \
            % (descr, list(remainder), first)

    if isinstance(first, (list, tuple)):
        assert len(first) == len(second), "%svarying length: %r != %r" \
            % (descr, first, second)
        for c in range(len(first)):
            assertEqual(first[c], second[c], descr + "[%d] " % c)

    raise AssertionError("%snot equal (%r): %r != %r" % (descr, type(first), first, second))
