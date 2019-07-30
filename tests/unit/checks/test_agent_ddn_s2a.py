import pytest


@pytest.mark.parametrize("params,result", [
    ({
        'username': 'user',
        'password': 'test'
    }, ['address', '8008', 'user', 'test']),
    ({
        'username': 'user',
        'password': 'test',
        'port': 8090
    }, ['address', '8090', 'user', 'test']),
])
def test_ddn_s2a(check_manager, params, result):
    agent = check_manager.get_special_agent("agent_ddn_s2a")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
