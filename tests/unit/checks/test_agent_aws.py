import pytest


@pytest.mark.parametrize("params,result", [({
    "--aws-access-key-id": "user",
    "--aws-secret-access-key": "d1ng",
    "--regions": ['region-eu'],
}, [
    '--aws-access-key-id', 'user', '--aws-secret-access-key', 'd1ng',
    '--regions', 'region-eu', '--hostname', 'host'
]), ({
    "--aws-access-key-id": "user",
    "--aws-secret-access-key": "d1ng",
    "--regions": ['region-eu'],
    "--services": {'ec2': None, 's3': {'buckets': 'all'}},
}, [
    '--aws-access-key-id', 'user', '--aws-secret-access-key', 'd1ng',
    '--regions', 'region-eu', '--services', 'ec2', 's3', '--hostname', 'host'
]),({
    "--aws-access-key-id": "user",
    "--aws-secret-access-key": "d1ng",
    "--regions": ['region-eu'],
    "--services": {'ec2': None, 's3': {'buckets': ('buckets', ['A', 'B'])}},
}, [
    '--aws-access-key-id', 'user', '--aws-secret-access-key', 'd1ng',
    '--regions', 'region-eu', '--services', 'ec2', 's3', '--buckets', 'A', 'B',
    '--hostname', 'host'
])])
def test_aws(check_manager, params, result):
    agent = check_manager.get_special_agent("agent_aws")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == result
