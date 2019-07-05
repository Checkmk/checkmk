import pytest  # type: ignore

from cmk_base.check_api import MKGeneralException

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('group_patterns, filename, expected', [
    ([], 'lumberjacks.log', {}),
    ([('plain_group', ('*jack*', ''))], 'lumberjacks.log', {
        'plain_group': {('*jack*', '')},
    }),
    ([('plain_group', ('*jack*', '*.log'))], 'lumberjacks.log', {}),
    ([('plain_group', (u'~.*\\..*', ''))], 'lumberjacks.log', {
        'plain_group': {(u'~.*\\..*', '')}
    }),
    ([('%s_group', ('~.{6}(.ack)', ''))], 'lumberjacks.log', {
        'jack_group': {('~.{6}jack', '')},
    }),
    ([('%s', ('~(.).*', '')), ('%s', ('~lumberjacks.([l])og', ''))], 'lumberjacks.log', {
        'l': {('~l.*', ''), ('~lumberjacks.log', '')},
    }),
    ([('%s%s', ('~lum(ber).{8}(.)', '~ladida'))], 'lumberjacks.log', {
        'berg': {('~lumber.{8}g', '~ladida')},
    }),
])
def test_logwatch_groups_of_logfile(check_manager, group_patterns, filename, expected):
    check = check_manager.get_check('logwatch')
    logwatch_groups_of_logfile = check.context['logwatch_groups_of_logfile']
    actual = logwatch_groups_of_logfile(group_patterns, filename)
    assert actual == expected


@pytest.mark.parametrize('group_patterns, filename', [
    ([('%s_group', ('~.{6}.ack', ''))], 'lumberjacks.log'),
])
def test_logwatch_groups_of_logfile_exception(check_manager, group_patterns, filename):
    check = check_manager.get_check('logwatch')
    logwatch_groups_of_logfile = check.context['logwatch_groups_of_logfile']

    with pytest.raises(MKGeneralException):
        logwatch_groups_of_logfile(group_patterns, filename)
