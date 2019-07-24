import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args",
                         [({}, ["-w", "200.00,80%", "-c", "500.00,100%", "'$HOSTADDRESS$'"])])
def test_check_icmp_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_icmp")
    assert active_check.run_argument_function(params) == expected_args
