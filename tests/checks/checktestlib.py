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
            assert all([len(entry) >= 2 for entry in perfdata])

            for entry in perfdata:
                assert type(entry) == tuple
                assert len(entry) >= 2

                # TODO: This is very basic. There is more way more magic involved
                #       in what kind of values are allowed as metric names.
                #       I'm not too sure unicode should be allowed, either.
                assert type(entry[0]) in [str, unicode]

                assert type(entry[1]) in [int, float]
                assert all(type(value) in [int, float, type(None)] for value in entry[2:])
        self.perfdata = perfdata

    def match_status(self, expected_status):
        """Check if this result's status matches a given value. Exact match."""
        return self.status == expected_status

    def match_infotext(self, expected_infotext):
        """Check whether this result's infotext contains a given string. Case-sensitive."""
        return expected_infotext in self.infotext

    def match_perfdata(self, expected_perfdata):
        """Check whether this result's perfdata matches a given value. Exact match."""
        return expected_perfdata == self.perfdata

    def assert_result(self, expected_result):
        """Assert that a result matches certain criteria

        expected_result is a Dictionary defining the criteria, allowing to not
        rigidly define every detail about the check result, but only what we
        really want to test. Unset fields mean we don't care.
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
