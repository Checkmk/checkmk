import pytest

pytestmark = pytest.mark.check

@pytest.mark.parametrize("info,result", [
    ([], [])
])
def test_df_discovery_with_parse(check_manager, info, result):
    check = check_manager.get_check("df")
    assert check.run_discovery(check.run_parse(info)) == result

