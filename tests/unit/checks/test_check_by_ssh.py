import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args",
                         [(["foo", {}], ["-H", "$HOSTADDRESS$", "-C", "foo"]),
                          (["foo", {
                              "port": 22
                          }], ["-H", "$HOSTADDRESS$", "-C", "foo", "-p", 22])])
def test_check_by_ssh_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_by_ssh")
    assert active_check.run_argument_function(params) == expected_args
