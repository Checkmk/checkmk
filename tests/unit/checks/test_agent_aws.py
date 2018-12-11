import pytest


@pytest.mark.parametrize("params,result", [
    ({
        "--aws-access-key-id": "user",
        "--aws-secret-access-key": "d1ng",
        "--region": 'region-eu',
    }, ['--aws-access-key-id', 'user', '--aws-secret-access-key', 'd1ng', '--region', 'region-eu', 'host']),
])
def test_aws(check_manager, params, result):
    agent = check_manager.get_special_agent("agent_aws")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
