import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("info, result", [
    ([["", "", "", ""]], (None, None, None)),
    ([["", 0, "", ""]], (None, None, None)),
    ([[0, "", "", ""]], (None, None, None)),
    ([[0, 0, "", ""]], (0.0, 0.0, [("total", {})])),
    ([[1, 0, "", ""]], (1.0, 0.0, [("total", {})])),
])
def test_f5_bigip_mem_discovery(check_manager, info, result):
    mem_total, mem_used, items = result
    check = check_manager.get_check("f5_bigip_mem")
    parsed = check.run_parse(info)
    assert check.run_discovery(parsed) == items

    if items is not None:
        assert parsed['mem_total'] == mem_total
        assert parsed['mem_used'] == mem_used


@pytest.mark.parametrize("info, result", [
    ([["", "", "", ""]], None),
    ([["", "", 0, ""]], None),
    ([["", "", "", 0]], None),
    ([["", "", 0, 0]], None),
    ([["", "", 1, 0]], [("TMM", {})]),
])
def test_f5_bigip_mem_tmm_discovery(check_manager, info, result):
    parsed = check_manager.get_check("f5_bigip_mem").run_parse(info)
    check = check_manager.get_check("f5_bigip_mem.tmm")
    assert check.run_discovery(parsed) == result

    if result is not None:
        assert parsed['tmm_mem_total'] == 1024.0
        assert parsed['tmm_mem_used'] == 0.0
