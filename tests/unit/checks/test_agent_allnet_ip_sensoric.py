import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({}, ["address"]),
    ({
        'timeout': 20
    }, ['--timeout', '20', "address"]),
])
def test_allnet_ip_sensoric_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_allnet_ip_sensoric')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
