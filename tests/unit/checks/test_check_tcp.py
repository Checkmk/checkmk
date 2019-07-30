import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ((1, {}), ["-p", 1, "-H", "'$HOSTADDRESS$'"]),
])
def test_check_tcp_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_tcp")
    assert active_check.run_argument_function(params) == expected_args
