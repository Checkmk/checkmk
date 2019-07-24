import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({}, ["-H", "$HOSTADDRESS$"]),
    ({
        "port": 21
    }, ["-H", "$HOSTADDRESS$", "-p", 21]),
])
def test_check_ftp_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_ftp")
    assert active_check.run_argument_function(params) == expected_args
