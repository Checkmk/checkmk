import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "base_url": "some/path",
        "aggregation_name": "foo",
        "username": "bar",
        "credentials": "automation",
        "optional": {}
    }, ["-b", "some/path", "-a", "foo", "--use-automation-user"]),
])
def test_check_bi_aggr_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_bi_aggr")
    assert active_check.run_argument_function(params) == expected_args
