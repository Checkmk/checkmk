import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'testID',
        'application': 'appName',
        'password': 'password'
    }, ["-u", "testID", "-p", "password", "address", "appName"]),
    ({
        'username': 'testID',
        'application': 'appName',
        'password': 'password',
        'port': 8090,
        'timeout': 30
    }, ["-u", "testID", "-p", "password", "-P", "8090", "-t", "30", "address", "appName"]),
])
def test_appdynamics_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_appdynamics')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
