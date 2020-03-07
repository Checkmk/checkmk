import pytest  # type: ignore[import]
import testlib  # type: ignore[import]

import cmk.base.config as config
import cmk.base.check_api as check_api
from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees

pytestmark = pytest.mark.checks

config.load_all_checks(check_api.get_check_api_context)


@pytest.mark.parametrize("_name, snmp_info", list(config.snmp_info.items()))
def test_dataset(_name, snmp_info):
    _ = _create_snmp_trees(snmp_info)
