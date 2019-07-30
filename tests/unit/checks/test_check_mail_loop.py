import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "item": "foo",
        "fetch": (None, {
            "server": "bar",
            "ssl": (False, 143),
            "auth": ("hans", "wurst")
        }),
        "mail_from": None,
        "mail_to": None,
    }, [
        '--smtp-server=$HOSTADDRESS$', '--fetch-protocol=None', '--fetch-server=bar',
        '--fetch-port=143', '--fetch-username=hans', '--fetch-password=wurst', '--mail-from=None',
        '--mail-to=None', '--status-suffix=non-existent-testhost-foo'
    ]),
])
def test_check_mail_loop_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_mail_loop")
    assert active_check.run_argument_function(params) == expected_args
