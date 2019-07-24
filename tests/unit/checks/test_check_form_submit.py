import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    (["foo", {}], ["-I", "$HOSTADDRESS$"]),
    (["foo", {
        "port": 80
    }], ["-p", 80, "-I", "$HOSTADDRESS$"]),
])
def test_check_form_submit_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_form_submit")
    assert active_check.run_argument_function(params) == expected_args
