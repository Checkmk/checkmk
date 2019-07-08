import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'values': [],
        'devices': [{
            'slot': 2,
            'tcp_port': 102,
            'values': [],
            'host_name': 'device1',
            'host_address': 'host',
            'rack': 2
        }, {
            'slot': 1,
            'tcp_port': 22,
            'values': [],
            'host_name': 'device2',
            'host_address': 'hostaddress',
            'rack': 2
        }]
    }, ['device1;host;2;2;102', 'device2;hostaddress;2;1;22']),
])
def test_siemens_plc_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_siemens_plc')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
