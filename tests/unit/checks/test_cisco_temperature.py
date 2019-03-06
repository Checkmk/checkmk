import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("dlh_upper, dlh_lower, user_levels, dev_levels, expected", [
    ("no", "no", (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0), None),
    ("usr", "usr", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0), (1.5, 3.0, -1.5, -3.0)),
    ("usr", "devdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0), (1.5, 3.0, -1.0, -2.0)),
    ("usr", "usrdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0), (1.5, 3.0, -1.5, -3.0)),
    ("devdefault", "usr", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0), (1.0, 2.0, -1.5, -3.0)),
    ("devdefault", "devdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0),
     (1.0, 2.0, -1.0, -2.0)),
    ("devdefault", "usrdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0),
     (1.0, 2.0, -1.5, -3.0)),
    ("usrdefault", "usr", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0), (1.5, 3.0, -1.5, -3.0)),
    ("usrdefault", "devdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0),
     (1.5, 3.0, -1.0, -2.0)),
    ("usrdefault", "usrdefault", (1.5, 3.0, -1.5, -3.0), (1.0, 2.0, -1.0, -2.0),
     (1.5, 3.0, -1.5, -3.0)),
    ("usrdefault", "devdefault", (1.5, 3.0, -1.5, -3.0), (None, None, None, None),
     (1.5, 3.0, -1.5, -3.0)),
    ("usrdefault", "devdefault", (1.5, 3.0, -1.5, -3.0), (None, None, -1 - 0, -2.0),
     (1.5, 3.0, -1.0, -2.0)),
])
def test_level_determination(check_manager, dlh_upper, dlh_lower, user_levels, dev_levels,
                             expected):
    """
    Combinatorical "all pairs" testing applied to device level handling parameters.
    """
    check = check_manager.get_check("cisco_temperature")
    determine_all_levels = check.context["_determine_all_levels"]
    assert determine_all_levels(dlh_upper, dlh_lower, user_levels, dev_levels) == expected
