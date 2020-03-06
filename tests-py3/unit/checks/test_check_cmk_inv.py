import pytest  # type: ignore[import]

pytestmark = pytest.mark.checks

STATIC_ARGS = ["--cache", "--inventory-as-check", "$HOSTNAME$"]


@pytest.mark.parametrize("params,expected_args", [
    ({},
     ["--inv-fail-status=1", "--hw-changes=0", "--sw-changes=0", "--sw-missing=0"] + STATIC_ARGS),
    ({
        "timeout": 0
    }, ["--inv-fail-status=1", "--hw-changes=0", "--sw-changes=0", "--sw-missing=0"] + STATIC_ARGS),
])
def test_check_cmk_inv_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_cmk_inv")
    assert active_check.run_argument_function(params) == expected_args
