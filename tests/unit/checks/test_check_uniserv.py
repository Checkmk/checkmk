import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "port": 123,
        "service": "foobar",
        "job": "version"
    }, ["$HOSTADDRESS$", 123, "foobar", "VERSION"]),
    ({
        "port": 123,
        "service": "foobar",
        "job": ("address", {
            "street": "street",
            "street_no": 0,
            "city": "city",
            "search_regex": "regex"
        })
    }, ["$HOSTADDRESS$", 123, "foobar", "ADDRESS", "street", 0, "city", "regex"]),
])
def test_check_uniserv_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_uniserv")
    assert active_check.run_argument_function(params) == expected_args
