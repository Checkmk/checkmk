import pytest

from cmk import prediction


@pytest.mark.parametrize("ref_value, stdev, sig, params, levels_factor, result", [
    (2, 0.5, 1, ("absolute", (3, 5)), 0.5, (3.5, 4.5)),
    (2, 0.5, -1, ("relative", (20, 50)), 0.5, (1.6, 1)),
    (2, 0.5, -1, ("stdev", (2, 4)), 0.5, (1, 0)),
])
def test_estimate_level_bounds(ref_value, stdev, sig, params, levels_factor, result):
    assert prediction.estimate_level_bounds(ref_value, stdev, sig, params, levels_factor) == result


@pytest.mark.parametrize("reference, params, levels_factor, result", [
    (
        {
            'average': 5,
            'stdev': 2
        },
        {
            'levels_lower': ('absolute', (2, 4))
        },
        1,
        (5, [None, None, 3, 1]),
    ),
    (
        {
            'average': 15,
            'stdev': 2,
        },
        {
            'levels_upper': ('stddev', (2, 4)),
            'levels_lower': ('stddev', (3, 5)),
        },
        1,
        (15, [19, 23, 9, 5]),
    ),
    (
        {
            'average': 2,
            'stdev': 3,
        },
        {
            'levels_upper': ('relative', (20, 40)),
            'levels_upper_min': (2, 4),
        },
        1,
        (2, [2.4, 4, None, None]),
    ),
    (
        {
            'average': None
        },
        {},
        1,
        (None, [None, None, None, None]),
    ),
])
def test_estimate_levels(reference, params, levels_factor, result):
    assert prediction.estimate_levels(reference, params, levels_factor) == result
