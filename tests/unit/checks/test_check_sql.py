import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "description": "foo",
        "dbms": "postgres",
        "name": "bar",
        "user": "hans",
        "password": "wurst",
        "sql": ("")
    }, [
        "--hostname=$HOSTADDRESS$", "--dbms=postgres", "--name=bar", "--user=hans",
        "--password=wurst", ""
    ]),
])
def test_check_sql_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_sql")
    assert active_check.run_argument_function(params) == expected_args
