import pytest
import pprint
import sys

pytestmark = pytest.mark.checks


#   .--Test info sections--------------------------------------------------.
#   |                _____         _     _        __                       |
#   |               |_   _|__  ___| |_  (_)_ __  / _| ___                  |
#   |                 | |/ _ \/ __| __| | | '_ \| |_ / _ \                 |
#   |                 | |  __/\__ \ |_  | | | | |  _| (_) |                |
#   |                 |_|\___||___/\__| |_|_| |_|_|  \___/                 |
#   |                                                                      |
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'

info_df_lnx = [[u'/dev/sda4',
      u'ext4',
      u'143786696',
      u'101645524',
      u'34814148',
      u'75%',
      u'/'],
     [u'[df_inodes_start]'],
     [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
     [u'[df_inodes_end]']]

info_df_win = [[u'C:\\', u'NTFS', u'8192620', u'7724268', u'468352', u'95%', u'C:\\'],
     [u'New_Volume', u'NTFS', u'10240796', u'186256', u'10054540', u'2%', u'E:\\'],
     [u'New_Volume',
     u'NTFS',
     u'124929596',
     u'50840432',
     u'74089164',
     u'41%',
     u'F:\\']]

info_df_lnx_tmpfs = [[u'tmpfs',
     u'tmpfs',
     u'8152820',
     u'76',
     u'8152744',
     u'1%',
     u'/opt/omd/sites/heute/tmp'],
     [u'[df_inodes_start]'],
     [u'tmpfs',
     u'tmpfs',
     u'2038205',
     u'48',
     u'2038157',
     u'1%',
     u'/opt/omd/sites/heute/tmp'],
     [u'[df_inodes_end]']]

# NOTE: This gargantuan test info section is uncritically used data from an archived agent output.
#       I suspect that our handling of btrfs is not really adequate, test cases using this data
#       serve the sole purpose of not inadvertenty breaking the status quo. Thus:
# TODO: Replace this monstrosity with something more concise.
info_df_btrfs = \
[[u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/'],
 [u'devtmpfs', u'devtmpfs', u'497396', u'0', u'497396', u'0%', u'/dev'],
 [u'tmpfs', u'tmpfs', u'506312', u'0', u'506312', u'0%', u'/dev/shm'],
 [u'tmpfs', u'tmpfs', u'506312', u'6980', u'499332', u'2%', u'/run'],
 [u'tmpfs', u'tmpfs', u'506312', u'0', u'506312', u'0%', u'/sys/fs/cgroup'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/.snapshots'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/tmp'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/spool'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/opt'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/log'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/lib/pgsql'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/lib/named'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/lib/mailman'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/var/crash'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/usr/local'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/tmp'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/srv'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/opt'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/home'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/boot/grub2/x86_64-efi'],
 [u'/dev/sda1',
  u'btrfs',
  u'20970496',
  u'4169036',
  u'16539348',
  u'21%',
  u'/boot/grub2/i386-pc'],
 [u'[df_inodes_start]'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/'],
 [u'devtmpfs', u'devtmpfs', u'124349', u'371', u'123978', u'1%', u'/dev'],
 [u'tmpfs', u'tmpfs', u'126578', u'1', u'126577', u'1%', u'/dev/shm'],
 [u'tmpfs', u'tmpfs', u'126578', u'481', u'126097', u'1%', u'/run'],
 [u'tmpfs', u'tmpfs', u'126578', u'12', u'126566', u'1%', u'/sys/fs/cgroup'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/.snapshots'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/tmp'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/spool'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/opt'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/log'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/pgsql'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/named'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/mailman'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/crash'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/usr/local'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/tmp'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/srv'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/opt'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/home'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/boot/grub2/x86_64-efi'],
 [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/boot/grub2/i386-pc'],
 [u'[df_inodes_end]']]



#.
#   .--Test functions------------------------------------------------------.
#   |   _____         _      __                  _   _                     |
#   |  |_   _|__  ___| |_   / _|_   _ _ __   ___| |_(_) ___  _ __  ___     |
#   |    | |/ _ \/ __| __| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|    |
#   |    | |  __/\__ \ |_  |  _| |_| | | | | (__| |_| | (_) | | | \__ \    |
#   |    |_|\___||___/\__| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

@pytest.mark.parametrize("info,expected_result,include_volume_name", [
    ([], [], False),
    (info_df_lnx, [(u'/', {})], False),
    (info_df_lnx, [(u'/dev/sda4 /', {})], True),
    (info_df_win, [(u'E:/', {}), (u'F:/', {}), (u'C:/', {})], False),
    (info_df_win, [(u'New_Volume E:/', {}), (u'New_Volume F:/', {}), (u'C:\\ C:/', {})], True),
    (info_df_lnx_tmpfs, [], False),
    (info_df_lnx_tmpfs, [], True),
    (info_df_btrfs, [(u'/sys/fs/cgroup', {}), (u'btrfs /dev/sda1', {})], False),
    (info_df_btrfs, [(u'/dev/sda1 /sys/fs/cgroup', {}), (u'/dev/sda1 btrfs /dev/sda1', {})], True),
])
def test_df_discovery_with_parse(check_manager, monkeypatch, info, expected_result, include_volume_name):
    import cmk_base

#   NOTE: This commented-out code is the result of trying to mock the the ruleset variable itself instead of the
#         host_extra_conf_merged function. It did not work. Maybe we can get it to work at a later stage.
#    import cmk_base.rulesets
#    monkeypatch.setitem(cmk_base.checks._check_contexts["df"], "inventory_df_rules",
#                [({"include_volume_name": include_volume_name}, [], cmk_base.rulesets.ALL_HOSTS, {})])

    check = check_manager.get_check("df")
    monkeypatch.setitem(cmk_base.checks._check_contexts["df"], "host_extra_conf_merged", lambda _, __: {"include_volume_name": include_volume_name})
    assert check.run_discovery(check.run_parse(info)) == expected_result
    cmk_base.config_cache.clear_all()


# TODO: Make this work by finding a way to get a check's default levels in this context.
@pytest.mark.parametrize("item,params,info,expected_result", [
    (u"/", "default", info_df_lnx, {})
])
def test_df_check_with_parse(check_manager, monkeypatch, item, params, info, expected_result):
    import cmk_base
    check = check_manager.get_check("df")

    if params == "default":
        params = check.default_parameters()

    result = check.run_check(item, params, check.run_parse(info))
    if "status" in expected_result:
        assert result[0] == expected_result["status"]
    if "infotext" in expected_result:
        assert result[1] == expected_result["infotext"]
    if "perfdata" in expected_result:
        assert result[2] == expected_result["perfdata"]

    cmk_base.config_cache.clear_all()
