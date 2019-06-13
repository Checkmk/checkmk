import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [({
    "fetch": ("IMAP", ({
        "ssl": (True, 143),
        "auth": ("foo", "bar"),
    }))
}, [
    "--protocol=IMAP", "--server=$HOSTADDRESS$", "--ssl", "--port=143", "--username=foo",
    "--password=bar"
])])
def test_check_mail_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_mail")
    assert active_check.run_argument_function(params) == expected_args
