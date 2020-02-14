import pytest
import collections
from cmk.base.check_api import MKGeneralException

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'oid_value,expected',
    [
        ([0, 0, 0, 0, 0, 0, 0, 0], 0),
        ([0, 0, 0, 0, 0, 0, 1, 0], 256),
        ([0, 0, 0, 0, 0, 0, 0, 203], 203),
        ([0, 0, 0, 0, 0, 0, 2, 91], 603),
        ([0, 0, 88, 227, 183, 248, 226, 240], 97735067362032),
        ([0, 1, 43, 110, 15, 207, 84, 124], 329226688353404),
        # TODO: The following are either 184 bit counters, or something is wrong.
        ([
            48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48,
            48
        ], 4615492597874380058774580751237179345161915702775394352),
        ([
            48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48,
            51
        ], 4615492597874380058774580751237179345161915702775394355),
        ([
            48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 68, 65, 32, 56, 52, 32, 70,
            70
        ], 4615492597874380058774580751237179346607852692564887110),
        ([
            48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 48, 48, 32, 68, 65, 32, 56, 53, 32, 48,
            48
        ], 4615492597874380058774580751237179346607852692581658672),
    ])
def test_services_split(check_manager, oid_value, expected):
    check = check_manager.get_check('fc_port')
    fc_parse_counter = check.context['fc_parse_counter']
    actual = fc_parse_counter(oid_value)
    assert actual == expected
