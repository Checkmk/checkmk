class PerfValue(object):
    """Represents a single perf value"""

    def __init__(self, key, value, warn=None, crit=None, minimum=None, maximum=None):
        # TODO: This is very basic. There is more way more magic involved
        #       in what kind of values are allowed as metric names.
        #       I'm not too sure unicode should be allowed, either.
        assert type(key) in [str, unicode]
        self.key = key

        # NOTE: The CMC as well as all other Nagios-compatible cores do accept a
        #       string value that may contain a unit, which is in turn available
        #       for use in PNP4Nagios templates. Check_MK defines its own semantic
        #       context for performance values using Check_MK metrics. It is therefore
        #       preferred to return a "naked" scalar.
        assert type(value) in [int, float]
        self.value = value

        assert type(warn) in [int, float, type(None)]
        self.warn = warn
        assert type(crit) in [int, float, type(None)]
        self.crit = crit
        assert type(minimum) in [int, float, type(None)]
        self.minimum = minimum
        assert type(maximum) in [int, float, type(None)]
        self.maximum = maximum


class BasicCheckResult(object):
    """A basic check result

    This class models a basic check result (status, infotext, perfdata) and provides
    facilities to match it against conditions, such as 'Status is...' or 'Infotext contains...'
    """

    def __init__(self, status, infotext, perfdata=None):
        """We perform some basic consistency checks during initialization"""

        assert status in [0,1,2,3]
        assert type(infotext) == str
        assert "\n" not in infotext
        self.status = status
        self.infotext = infotext
        if perfdata is not None:
            assert type(perfdata) == list

            self.perfdata = []
            for entry in perfdata:
                assert type(entry) == tuple
                self.perfdata.append(PerfValue(*entry))
        else:
            self.perfdata = None

    def match_status(self, expected_status):
        """Check if this result's status matches a given value. Exact match."""
        return self.status == expected_status

    def match_infotext(self, expected_infotext):
        """Check whether this result's infotext contains a given string. Case-sensitive."""
        return expected_infotext in self.infotext

    def match_perfdata(self, expected_perfdata):
        """Check whether this result's perfdata matches a given value. Exact match."""
        return expected_perfdata == self.perfdata

    def match(self, expected_result):
        """Check whether a result matches certain criteria

        expected_result is a Dictionary defining the criteria, allowing to not
        rigidly define every detail about the check result, but only what we
        really want to test. Unset fields mean we don't care.
        """

        if "status" in expected_result and not match_status(expected_result["status"]):
            return False
        if "infotext" in expected_result and not match_infotext(expected_result["infotext"]):
            return False
        if "perfdata" in expected_result and not match_perfdata(expected_result["perfdata"]):
            return False
        return True

    def assert_result(self, expected_result):
        """Assert that a result matches certain criteria

        expected_result works as in match_result
        """

        if "status" in expected_result:
            assert match_status(expected_result["status"])
        if "infotext" in expected_result:
            assert match_infotext(expected_result["infotext"])
        if "perfdata" in expected_result:
            assert match_perfdata(expected_result["perfdata"])


class CompoundCheckResult(object):
    """A check result consisting of multiple subresults, as returned by yield-style checks"""

    def __init__(self, result):
        """Initializes a list of subresults using BasicCheckResult"""

        self.subresults = []
        for subresult in result:
            self.subresults.append(BasicCheckResult(*subresult))

    def match_subresult(self, expected_result):
        """Checks whether a subresult matching certain criteria is contained in this compound result"""

        for subresult in self.subresults:
            if subresult.match(expected_result):
                return True
        return False

    def assert_result(self, expected_result):
        """Assert that a subresult matching certain criteria is contained in this compound result"""

        assert self.match_subresult(expected_result)
