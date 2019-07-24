import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    (None, ["host"]),
])
def test_acme_sbc_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent("agent_acme_sbc")
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
