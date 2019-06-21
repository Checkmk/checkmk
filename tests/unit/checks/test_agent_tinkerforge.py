import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({}, ["--host", "address"]),
    ({
        'segment_display_brightness': 5,
        'segment_display_uid': '8888',
        'port': 4223
    }, [
        "--host", "address", "--port", "4223", "--segment_display_uid", "8888",
        "--segment_display_brightness", "5"
    ]),
])
def test_tinkerforge_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_tinkerforge')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
