
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

    def assert_result(self, expected_result):
        if "status" in expected_result:
            assert result.status == expected_result["status"]
        if "infotext" in expected_result:
            assert result.infotext == expected_result["infotext"]
        if "perfdata" in expected_result:
            assert result.perfdata == expected_result["perfdata"]
