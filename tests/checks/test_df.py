import pytest
import pprint
import sys

pytestmark = pytest.mark.check

@pytest.mark.parametrize("info,result,include_volume_name", [
    ([], [], False),
    ([[u'/dev/sda4',
       u'ext4',
       u'143786696',
       u'101645524',
       u'34814148',
       u'75%',
       u'/'],
      [u'[df_inodes_start]'],
      [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
      [u'[df_inodes_end]']], [(u'/', {})], False),
    ([[u'/dev/sda4',
       u'ext4',
       u'143786696',
       u'101645524',
       u'34814148',
       u'75%',
       u'/'],
      [u'[df_inodes_start]'],
      [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
      [u'[df_inodes_end]']], [(u'/dev/sda4 /', {})], True),
])
def test_df_discovery_with_parse(check_manager, monkeypatch, info, result, include_volume_name):
    import cmk_base.checks
    import cmk_base

#   NOTE: This is the result of trying to mock the the ruleset variable itself instead of the
#         host_extra_conf_merged function. It did not work. Maybe we can get it to work at a later stage.
#    import cmk_base.rulesets
#    monkeypatch.setitem(cmk_base.checks._check_contexts["df"], "inventory_df_rules",
#                [({"include_volume_name": include_volume_name}, [], cmk_base.rulesets.ALL_HOSTS, {})])

    check = check_manager.get_check("df")
    monkeypatch.setitem(cmk_base.checks._check_contexts["df"], "host_extra_conf_merged", lambda _, __: {"include_volume_name": include_volume_name})
    assert check.run_discovery(check.run_parse(info)) == result
    cmk_base.config_cache.clear_all()
