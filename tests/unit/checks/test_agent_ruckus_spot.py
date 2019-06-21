import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'venueid': 'venueID',
        'api_key': '55410aaa',
        'port': 8443,
        'address': True
    }, ["--address", "address", "8443", "--venueid", "venueID", "--apikey", "55410aaa"]),
    ({
        'cmk_agent': {
            'port': 6556
        },
        'venueid': 'venueID',
        'api_key': '55410aaa',
        'port': 8443,
        'address': 'addresstest'
    }, [
        "--address", "addresstest", "8443", "--venueid", "venueID", "--apikey", "55410aaa",
        "--agent_port", "6556"
    ]),
])
def test_ruckus_spot_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_ruckus_spot')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
