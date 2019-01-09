import pytest
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.unsorted import forbid_re_delimiters_inside_groups
from cmk.gui.plugins.wato.check_parameters.cpu_utilization import transform_cpu_iowait


@pytest.mark.parametrize('pattern', ["(test)$", 'foo\\b', '^bar', '\\bfoo\\b', '(a)\\b'])
def test_validate_ps_allowed_regex(pattern):
    assert forbid_re_delimiters_inside_groups(pattern, '') is None


@pytest.mark.parametrize('pattern', ["(test$)", '(foo\\b)', '(^bar)', '(\\bfoo\\b)'])
def test_validate_ps_forbidden_regex(pattern):
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, '')


@pytest.mark.parametrize('params, result', [
    (
        (10, 20),
        {
            'iowait': (10, 20)
        },
    ),
    ({}, {}),
    (
        {
            'util': (50, 60)
        },
        {
            'util': (50, 60)
        },
    ),
])
def test_transform_cpu_iowait(params, result):
    assert transform_cpu_iowait(params) == result
