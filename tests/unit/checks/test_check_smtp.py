import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    (("foo", {}), ["-4", "-H", "$_HOSTADDRESS_4$"]),
])
def test_check_smtp_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_smtp")
    assert active_check.run_argument_function(params) == expected_args
