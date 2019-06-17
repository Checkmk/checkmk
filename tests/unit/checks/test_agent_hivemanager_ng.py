import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'client_id': 'clientID',
        'url': 'http://cloud.com',
        'vhm_id': '102',
        'redirect_url': 'http://redirect.com',
        'api_token': 'token',
        'client_secret': 'clientsecret'
    }, ["http://cloud.com", "102", "token", "clientID", "clientsecret", "http://redirect.com"]),
])
def test_hivemanager_ng_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_hivemanager_ng')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
