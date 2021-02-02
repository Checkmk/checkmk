import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from cmk.base.plugins.agent_based.utils.cpu import Section

pytestmark = pytest.mark.checks


def test_cpu_loads_predictive(mocker):
    # make sure cpu_load check can handle predictive values
    # absolute values are tested via generic tests
    mocker.patch("cmk.base.check_api._prediction.get_levels", return_value=(None, (2.2, 4.2)))
    check_cpu = Check("cpu.loads")
    params = {
        'levels': {
            'period': 'minute',
            'horizon': 1,
            'levels_upper': ('absolute', (2.0, 4.0))
        }
    }
    section = Section(load=(0.5, 1.0, 1.5), num_cpus=4, num_threads=123)
    result = check_cpu.run_check(None, params, section)

    assert result == (0, '15 min load: 1.50 (no reference for prediction yet) '
                      'at 4 cores (0.38 per core)', [('load1', 0.5, None, None, 0, 4),
                                                     ('load5', 1.0, None, None, 0, 4),
                                                     ('load15', 1.5, None, None, 0, 4)])
