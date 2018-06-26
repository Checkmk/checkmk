import types
import mock
from cmk_base.item_state import MKCounterWrapped


class Tuploid(object):
    """Base class for values with (potentially variadic) tuple representations"""

    def __eq__(self, other_value):
        if isinstance(other_value, self.__class__):
            return other_value.tuple == self.tuple
        elif type(other_value) == tuple:
            return all(x==y for x, y in zip(other_value, self.tuple))

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
        # TODO: This is very basic. There is more way more magic involved
        #       in what kind of values are allowed as metric names.
        #       I'm not too sure unicode should be allowed, either.
        assert type(key) in [str, unicode]
        assert " " not in key   # This leads to serious errors
        assert "=" not in key   # The parsing around this is way too funky and doesn't work properly
        assert "\n" not in key
        self.key = key

        # NOTE: The CMC as well as all other Nagios-compatible cores do accept a
        #       string value that may contain a unit, which is in turn available
        #       for use in PNP4Nagios templates. Check_MK defines its own semantic
        #       context for performance values using Check_MK metrics. It is therefore
        #       preferred to return a "naked" scalar.
        assert type(value) in [int, float]
        self.value = value

        assert type(warn) in [int, float, types.NoneType]
        self.warn = warn
        assert type(crit) in [int, float, types.NoneType]
        self.crit = crit
        assert type(minimum) in [int, float, types.NoneType]
        self.minimum = minimum
        assert type(maximum) in [int, float, types.NoneType]
        self.maximum = maximum

    @property
    def tuple(self):
        return (self.key, self.value, self.warn, self.crit, self.minimum, self.maximum)

    def __repr__(self):
        return "PerfValue(%r, %r, %r, %r, %r, %r)" % self.tuple


class BasicCheckResult(Tuploid):
    """
    A basic check result

    This class models a basic check result (status, infotext, perfdata) and provides
    facilities to match it against conditions, such as 'Status is...' or
    'Infotext contains...'
    """

    def __init__(self, status, infotext, perfdata=None):
        """We perform some basic consistency checks during initialization"""

        assert status in [0, 1, 2, 3]
        self.status = status

        assert type(infotext) in [ str, unicode ]

        if "\n" in infotext:
            self.infotext, \
            self.multiline = infotext.split("\n", 1)
        else:
            self.infotext = infotext
            self.multiline = None

        if perfdata is not None:
            assert type(perfdata) == list

            self.perfdata = []
            for entry in perfdata:
                assert type(entry) in [tuple, PerfValue]
                if type(entry) is tuple:
                    self.perfdata.append(PerfValue(*entry))
                else:
                    self.perfdata.append(entry)
        else:
            self.perfdata = None

    @property
    def tuple(self):
        return (self.status, self.infotext, self.perfdata, self.multiline)

    def __repr__(self):
        if self.multiline is not None:
            return 'BasicCheckResult(%r, %r, %r)' % \
                   (self.status, self.infotext, self.perfdata)
        else:
            return 'BasicCheckResult(%r, %r, %r, multiline=%r)' % \
                   self.tuple


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
        if isinstance(result, types.GeneratorType):
            for subresult in result:
                self.subresults.append(BasicCheckResult(*subresult))
        # creation of a CheckResult via a list of
        # tuple or BasicCheckResult for test writing
        elif isinstance(result, list):
            for subresult in result:
                assert type(subresult) in (tuple, BasicCheckResult), \
                       "type of subresult must be %s or %s - not %r" % \
                       (tuple, BasicCheckResult, subresult)
                if isinstance(subresult, tuple):
                    subresult = BasicCheckResult(*subresult)
                self.subresults.append(subresult)
            self.subresults = result
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


def assertCheckResultsEqual(actual, expected):
    """
    Compare two (Basic)CheckResults.

    This gives more helpful output than 'assert actual == expected'
    """
    if isinstance(actual, BasicCheckResult):
        assert isinstance(expected, BasicCheckResult)
        assert actual == expected, "%s != %s" % (actual, expected)

    else:
        assert isinstance(actual, CheckResult)
        assert isinstance(expected, CheckResult)
        assert len(actual.subresults) == len(expected.subresults)
        for suba, sube in zip(actual.subresults, expected.subresults):
            assert suba == sube, "%r != %r" % (suba, sube)


class DiscoveryEntry(Tuploid):
    """A single entry as returned by the discovery (or in oldspeak: inventory) function."""

    def __init__(self, entry):
        item, default_params = entry
        assert type(item) in [ str, unicode, types.NoneType ]
        self.item = item
        self.default_params = default_params

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


def assertDiscoveryResultsEqual(actual, expected):
    """
    Compare two DiscoveryResults.

    This gives more helpful output than 'assert actual == expected'
    """
    assert isinstance(actual, DiscoveryResult)
    assert isinstance(expected, DiscoveryResult)
    assert len(actual.entries) == len(expected.entries)
    for enta, ente in zip(actual, expected):
        assert enta == ente, "%r != %r" % (enta, ente)


class BasicItemState(object):
    """Item state as returned by get_item_state

    We assert that we have exactly two values,
    where the first one is either float or int.
    """
    def __init__(self, *args):
        if len(args) == 1:
            args = args[0]
        msg = "BasicItemStates expected 2-tuple (time_diff, value) - not %r"
        assert isinstance(args, tuple), msg % args
        assert len(args) == 2, msg % args
        self.time_diff, self.value = args

        time_diff_type = type(self.time_diff)
        msg = "time_diff should be of type float/int - not %r"
        assert time_diff_type in (float, int), msg % time_diff_type
        # We do allow negative time diffs.
        # We want to ba able to test time anomalies.


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

    1) Tuple or a BasicItemState:
        The argument is assumed to be (time_diff, value). All calls to the
        item_state API behave as if the last state had been `value`, recorded
        `time_diff` seeconds ago.

    2) Dictionary containing Tuples or BasicItemStates:
        The dictionary will replace the item states.
        Basically `get_item_state` gets replaced by the dictionarys GET method.

    3) Callable object:
        The callable object will replace `get_item_state`. It must accept two
        arguments (key/default), in same way a dictionary does.

    In all of these cases, the sanity of the returned values is checked
    (i.e. they have to be BasicItemState).

    See for example 'test_statgrab_cpu_check.py'.
    """
    TARGET = 'cmk_base.item_state._cached_item_states.get_item_state'

    def __init__(self, mock_state):
        self.context = None
        self.get_val_function = None

        if hasattr(mock_state, '__call__'):
            self.get_val_function = mock_state
            return

        type_mock_state = type(mock_state)
        allowed_types = (tuple, BasicItemState, dict)
        assert type_mock_state in allowed_types, \
               "type must be in %r, or callable - not %r" % \
               (allowed_types, type_mock_state)

        # in dict case check values
        if type_mock_state == dict:
            msg = "dict values must be in %r - not %r"
            allowed_types = (tuple, BasicItemState)
            for v in mock_state.values():
                tyv = type(v)
                assert tyv in allowed_types, msg % (allowed_types, tyv)
            self.get_val_function = mock_state.get
        else:
            self.get_val_function = lambda key, default: mock_state


    def __call__(self, user_key, default=None):
        # ensure the default value is sane
        BasicItemState(default)
        val = self.get_val_function(user_key, default)
        if not isinstance(val, BasicItemState):
            val = BasicItemState(val)
        return val.time_diff, val.value

    def __enter__(self):
        '''The default context: just mock get_item_state'''
        self.context = mock.patch(MockItemState.TARGET,
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
        assert ty is not None, "No exception has occurred!"
        assert ty == MKCounterWrapped, "%r is not of type %r" % (ex, MKCounterWrapped)
        if self.msg is not None:
            assert self.msg == str(ex), "%r != %r" % (self.msg, str(ex))
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
    TARGET = 'cmk_base.config.host_extra_conf'

    def __init__(self, mock_config):
        self.context = None
        assert type(mock_config) in (dict, list)
        if isinstance(mock_config, dict):
            self.config = [mock_config]
        else:
            self.config = mock_config

    def __call__(self, _hostname, _ruleset):
        # ensure the default value is sane
        return self.config

    def __enter__(self):
        '''The default context: just mock get_item_state'''
        self.context = mock.patch(MockHostExtraConf.TARGET,
                                  # I'm the MockObj myself!
                                  new_callable=lambda: self)
        return self.context.__enter__()

    def __exit__(self, *exc_info):
        return self.context.__exit__(*exc_info)


