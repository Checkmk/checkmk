import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "share": "foo",
        "levels": (85.0, 95.0)
    }, ["-a", "$HOSTADDRESS$", "-s", "foo", "-w85%", "-c95%", "-H", "$HOSTADDRESS$"]),
])
def test_check_disk_smb_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_disk_smb")
    assert active_check.run_argument_function(params) == expected_args
