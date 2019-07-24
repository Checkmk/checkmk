import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({}, ["--server", "address"]),
    ({
        'port': 8080
    }, ["--server", "address", "--port", "8080"]),
    ({
        'instance': u'monitor',
        'port': 8080
    }, ["--server", "address", "--port", "8080", "--instance", "monitor"]),
    ({
        'login': ('userID', 'password', 'basic'),
        'port': 8080
    }, [
        "--server", "address", "--port", "8080", "--user", "userID", "--password", "password",
        "--mode", "basic"
    ]),
])
def test_jolokia_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_jolokia')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
