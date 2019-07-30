import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'user',
        'password': 'password',
        'skip_elements': []
    }, ["-u", "user", "-s", "password", "address"]),
    ({
        'username': 'user',
        'password': 'password',
        'skip_elements': ['ctr_volumes']
    }, ['-u', 'user', '-s', 'password', '--nocounters volumes', 'address']),
])
def test_netapp_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_netapp')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
