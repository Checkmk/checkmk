import pytest  # type: ignore
from cmk.base.check_api import MKCounterWrapped

pytestmark = pytest.mark.checks

_broken_info = [[
    'DB19',
    ' Debug (121): ORA-01219: database or pluggable database not open: queries allowed on fixed tables or views only'
]]


@pytest.mark.parametrize('info', [
    _broken_info,
])
def test_oracle_jobs_discovery_error(check_manager, info):
    check = check_manager.get_check('oracle_jobs')
    assert list(check.run_discovery(info)) == []


@pytest.mark.parametrize('info', [
    _broken_info,
])
def test_oracle_jobs_check_error(check_manager, info):
    check = check_manager.get_check('oracle_jobs')
    with pytest.raises(MKCounterWrapped):
        check.run_check("DB19.SYS.JOB1", {}, info)
