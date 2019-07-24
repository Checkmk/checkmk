import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'username',
        'password': 'password'
    }, ["-u", "username", "-p", "password", "address"]),
])
def test_ucs_bladecenter_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_ucs_bladecenter')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
