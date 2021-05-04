import os
import pytest

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/elphase.include'))


@pytest.mark.parametrize(
    "item, params, parsed, expected_result",
    [
        pytest.param(
            "Output",
            {},
            {
                'Output': {
                    'voltage': 231.0,
                    'current': 10.0,
                    'output_load': 4.0,
                },
            },
            [
                (
                    0,
                    'Voltage: 231.0 V',
                    [('voltage', 231.0)],
                ),
                (
                    0,
                    'Current: 10.0 A',
                    [('current', 10.0)],
                ),
                (
                    0,
                    'Load: 4.0%',
                    [('output_load', 4.0)],
                ),
            ],
            id="no parameters",
        ),
        pytest.param(
            "Output",
            {
                'voltage': (250, 200),
                'output_load': (0, 2),
            },
            {
                'Output': {
                    'voltage': 231.0,
                    'current': 10.0,
                    'output_load': 4.0,
                },
            },
            [
                (
                    1,
                    'Voltage: 231.0 V (warn/crit below 250/200 V)',
                    [('voltage', 231.0)],
                ),
                (
                    0,
                    'Current: 10.0 A',
                    [('current', 10.0)],
                ),
                (
                    0,
                    'Load: 4.0%',
                    [('output_load', 4.0)],
                ),
            ],
            id="with parameters",
        ),
        pytest.param(
            "Output",
            {
                'current': (10, 15),
                'differential_current_ac': (90, 100),
            },
            {
                'Output': {
                    'current': 10.0,
                    'differential_current_ac': 100,
                },
            },
            [
                (
                    0,
                    'Current: 10.0 A',
                    [('current', 10.0, 10, 15)],
                ),
                (
                    1,
                    'Differential current AC: 100 mA (warn/crit at 90/100 mA)',
                    [('differential_current_ac', 0.1, 0.09, 0.1)],
                ),
            ],
            id="with parameters, value exactly at the threshold",
        ),
    ],
)
def test_check_elphase(
        item,
        params,
        parsed,
        expected_result,
):
    assert list(check_elphase(
        item,
        params,
        parsed,
    )) == expected_result
