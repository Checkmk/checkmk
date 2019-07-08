import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,expected_parsed",
    [
        ([], []),
        ([["tcp", "0", "0", "0.0.0.0:6556", "0.0.0.0:*", "LISTENING"]
         ], [("TCP", ["0.0.0.0", "6556"], ["0.0.0.0", "*"], "LISTENING")]),
        # Some AIX systems separate the port with a dot (.) instead of a colon (:)
        ([["tcp4", "0", "0", "127.0.0.1.1234", "127.0.0.1.5678", "ESTABLISHED"]
         ], [("TCP", ["127.0.0.1", "1234"], ["127.0.0.1", "5678"], "ESTABLISHED")]),
    ])
def test_parse_netstat(check_manager, info, expected_parsed):
    parsed = check_manager.get_check('netstat').run_parse(info)
    assert parsed == expected_parsed
