import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    (("foo", "bar", {
        "hostname": "baz",
    }), ["-H", "baz", "-b", "bar"]),
    (("foo", "bar", {
        "hostname": "baz",
        "port": 389,
        "version": "v2"
    }), ["-H", "baz", "-b", "bar", "-p", 389, "-2"]),
])
def test_check_ldap_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_ldap")
    assert active_check.run_argument_function(params) == expected_args
