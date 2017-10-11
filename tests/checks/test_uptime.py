
import pytest

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.check


@pytest.mark.parametrize("info,result", [
    # Discover the service once non-empty agent output is available
    ([], None),
    ([[]], [ (None, {}) ]),
])
def test_uptime_discovery2(check_manager, info, result):
    check = check_manager.get_check("uptime")
    assert check.run_discovery(info) == result


def test_uptime_check_basic(check_manager):
    check = check_manager.get_check("uptime")

    result = check.run_check(None, {}, [["123"]])
    assert len(result) == 3
    assert result[0] == 0
    assert "Up since " in result[1]
    assert result[2] == [("uptime", 123.0)]


def test_uptime_check_zero(check_manager):
    check = check_manager.get_check("uptime")

    result = check.run_check(None, {}, [["0"]])
    assert len(result) == 3
    assert result[0] == 0
    assert "Up since " in result[1]
    assert result[2] == [("uptime", 0.0)]
