import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        "use_piggyback": False,
        'servername': 'testserver',
        'port': 8161
    }, ["--servername", "testserver", "--port", "8161"]),
    ({
        'use_piggyback': True,
        'servername': 'testserver',
        'port': 8161
    }, ["--servername", "testserver", "--port", "8161", "--piggyback"]),
])
def test_activemq_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_activemq')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
