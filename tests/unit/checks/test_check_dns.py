import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args",
                         [(["foo", {}], ["-H", "foo", "-s", "$HOSTADDRESS$"]),
                          (["foo", {
                              "timeout": 1
                          }], ["-H", "foo", "-s", "$HOSTADDRESS$", "-t", 1])])
def test_check_dns_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_dns")
    assert active_check.run_argument_function(params) == expected_args
