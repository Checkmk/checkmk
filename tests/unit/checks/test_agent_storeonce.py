import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'password': 'password',
        'user': 'username'
    }, ["--address=host", "--user=username", "--password=password"]),
    ({
        'cert': True,
        'password': 'password',
        'user': 'username'
    }, ["--address=host", "--user=username", "--password=password"]),
    ({
        'cert': False,
        'password': 'password',
        'user': 'username'
    }, ["--address=host", "--user=username", "--password=password", "--no-cert-check"]),
])
def test_storeonce_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_storeonce')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
