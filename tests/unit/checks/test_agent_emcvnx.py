import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'infos': ['disks', 'hba', 'hwstatus'],
        'password': 'password',
        'user': 'user'
    }, ["-u", "user", "-p", "password", "-i", "disks,hba,hwstatus", "address"]),
])
def test_emcvnx_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_emcvnx')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
