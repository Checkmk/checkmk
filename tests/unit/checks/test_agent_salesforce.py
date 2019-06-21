import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'instances': ['5']
    }, [
        "--section_url", "salesforce_instances",
        "https://api.status.salesforce.com/v1/instances/5/status"
    ]),
])
def test_agent_salesforce_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_salesforce')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
