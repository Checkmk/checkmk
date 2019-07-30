import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'tcp_port': 4711,
        'secret': 'wef',
        'infos': ['hostsystem', 'virtualmachine'],
        'user': 'wefwef'
    }, ["host"]),
])
def test_random_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_random')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
