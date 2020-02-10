import pytest  # type: ignore
from cmk.gui.plugins.metrics import stats


@pytest.mark.parametrize("q, array, result", [
    (50, [1], 1),
    (50, [1, 5, 6], 5),
    (50, [1, 5, 6, 6], 5.5),
    (100, [1, 5, 6, 6], 6),
    (100, [1, 5, 6], 6),
    (100, [1, 5, 6, 7], 7),
    (75, [1, 5, 6, 7], 6.5),
    (0, [1, 5, 6, 7], 1),
])
def test_percentile(q, array, result):
    assert stats.percentile(array, q) == result
