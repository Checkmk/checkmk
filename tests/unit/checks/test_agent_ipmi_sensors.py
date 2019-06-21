import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'username': 'user',
        'password': 'password',
        'privilege_lvl': 'user'
    }, ["-u", "user", "-p", "password", "-l", "user", "--ipmi-command", "freeipmi", "address"]),
    ({
        'username': 'user',
        'ipmi_driver': 'driver',
        'password': 'password',
        'privilege_lvl': 'user'
    }, [
        "-u", "user", "-p", "password", "-l", "user", "--ipmi-command", "freeipmi", "-D", "driver",
        "address"
    ]),
])
def test_ipmi_sensors_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_ipmi_sensors')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
