import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [({
    "imap_parameters": {
        "server": "foo",
        "ssl": (False, 143),
        "auth": ("hans", "wurst"),
    }
}, ["--server=foo", "--port=143", "--username=hans", "--password=wurst"])])
def test_check_mailboxes_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_mailboxes")
    assert active_check.run_argument_function(params) == expected_args
