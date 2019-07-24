import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': '',
        'password': ''
    }, ["--server", "address", "--username", "", "--password", ""]),
    ({
        'username': 'userid',
        'password': 'password',
        'port': 9440
    }, ['--server', 'address', '--port', '9440', '--username', 'userid', '--password', 'password']),
])
def test_prism_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_prism')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
