import pytest  # type: ignore
from freezegun import freeze_time  # type: ignore
import cmk.gui.watolib as watolib


@freeze_time("2018-01-10 02:00:00", tz_offset=+1)
@pytest.mark.parametrize("allowed,last_end,next_time", [
    (((0, 0), (24, 0)), None, 1515549600.0),
    (
        ((0, 0), (24, 0)),
        1515549600.0,
        1515549900.0,
    ),
    (((20, 0), (24, 0)), None, 1515610800.0),
    ([((0, 0), (2, 0)), ((20, 0), (22, 0))], None, 1515610800.0),
    ([((0, 0), (2, 0)), ((20, 0), (22, 0))], 1515621600.0, 1515625200.0),
])
def test_next_network_scan_at(allowed, last_end, next_time):
    folder = watolib.Folder(name="bla",
                            title="Bla",
                            attributes={
                                "network_scan": {
                                    'exclude_ranges': [],
                                    'ip_ranges': [('ip_range', ('10.3.1.1', '10.3.1.100'))],
                                    'run_as': u'cmkadmin',
                                    'scan_interval': 300,
                                    'set_ipaddress': True,
                                    'tag_criticality': 'offline',
                                    'time_allowed': allowed,
                                },
                                "network_scan_result": {
                                    "end": last_end,
                                }
                            })

    assert folder.next_network_scan_at() == next_time
