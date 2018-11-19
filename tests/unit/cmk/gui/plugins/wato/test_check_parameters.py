import pytest
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters import forbid_re_delimiters_inside_groups


@pytest.mark.parametrize('pattern', ["(test)$", 'foo\\b', '^bar', '\\bfoo\\b', '(a)\\b'])
def test_validate_ps_allowed_regex(pattern):
    assert forbid_re_delimiters_inside_groups(pattern, '') is None


@pytest.mark.parametrize('pattern', ["(test$)", '(foo\\b)', '(^bar)', '(\\bfoo\\b)'])
def test_validate_ps_forbidden_regex(pattern):
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, '')
