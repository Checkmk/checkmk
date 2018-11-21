import math
import pytest

from cmk_base import prediction


@pytest.mark.parametrize("group_by, timestamp, result", [
    (prediction.group_by_wday, 1543402800, ('wednesday', 43200)),
    (prediction.group_by_day, 1543402800, ('everyday', 43200)),
    (prediction.group_by_day_of_month, 1543402800, ('28', 43200)),
    (prediction.group_by_everyhour, 1543402820, ('everyhour', 20)),
])
def test_group_by(group_by, timestamp, result):
    assert group_by(timestamp) == result


@pytest.mark.parametrize("slices, result", [
    ([(0, 1, list(range(6)))], [[i] * 4 for i in range(6)]),
    ([(0, 1, [1, 5, None, 6])], [[i] * 4 for i in [1, 5, None, 6]]),
    ([
        (0, 1, [1, 5, None, 6]),
        (0, 1, [2, None, 2, 4]),
    ], [
        pytest.approx([1.5, 1, 2, math.sqrt(2) / 2]),
        [5.0, 5, 5, 5.0],
        [2.0, 2, 2, 2.0],
        pytest.approx([5.0, 4, 6, math.sqrt(2)]),
    ]),
    ([
        (0, 1, [1, 5, 3, 6, 8, None]),
        (0, 1, [2, 2, 2, 4, 3, 5]),
        (0, 2, [3, None, 2]),
    ], [
        pytest.approx([2.0, 1, 3, 1.0]),
        pytest.approx([10.0 / 3.0, 2, 5, 1.527525]),
        pytest.approx([2.5, 2, 3, math.sqrt(2) / 2]),
        pytest.approx([5.0, 4, 6, math.sqrt(2)]),
        pytest.approx([4.333333, 2, 8, 3.214550]),
        pytest.approx([3.5, 2, 5, 2.121320]),
    ]),
    ([
        (0, 1, [1, 5, 3, 2, 6, 8, None]),
        (0, 1, []),
        (0, 3.5, [5, 2]),
    ], [
        pytest.approx([3.0, 1, 5, 2.828427]),
        pytest.approx([5.0, 5, 5, 0.0]),
        pytest.approx([4.0, 3, 5, 1.414213]),
        pytest.approx([3.5, 2, 5, 2.121320]),
        pytest.approx([4.0, 2, 6, 2.828427]),
        pytest.approx([5.0, 2, 8, 4.242640]),
        pytest.approx([2.0, 2, 2, 2.0]),
    ]),
])
def test_consolidate(slices, result):
    assert prediction.consolidate_data(slices) == result
