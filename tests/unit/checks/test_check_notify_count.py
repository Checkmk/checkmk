import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [(("foo", 60, ()), ["-r", 60]),
                                                  (("foo", 60, (20, 50)), ["-r", 60])])
def test_check_notify_count_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_notify_count")
    assert active_check.run_argument_function(params) == expected_args
