import pytest
from checktestlib import DiscoveryResult, CheckResult, \
                         assertDiscoveryResultsEqual, MockHostExtraConf


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
     [u'tmpfs', u'tmpfs', u'8152840', u'118732', u'8034108', u'2%', u'/dev/shm'],
     [u'[df_inodes_start]'],
     [u'tmpfs',
     u'tmpfs',
     u'2038205',
     u'48',
     u'2038157',
     u'1%',
     u'/opt/omd/sites/heute/tmp'],
     [u'tmpfs', u'tmpfs', u'2038210', u'57', u'2038153', u'1%', u'/dev/shm'],
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


info_solaris_zfs = [
 [u'zfs', u'is', u'hashed', u'(/usr/sbin/zfs)'],
]

#.
#   .--Test functions------------------------------------------------------.
#   |   _____         _      __                  _   _                     |
#   |  |_   _|__  ___| |_   / _|_   _ _ __   ___| |_(_) ___  _ __  ___     |
#   |    | |/ _ \/ __| __| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|    |
#   |    | |  __/\__ \ |_  |  _| |_| | | | | (__| |_| | (_) | | | \__ \    |
#   |    |_|\___||___/\__| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

@pytest.mark.parametrize("info,expected_result,inventory_df_rules", [
    ([], [], {}),
    (info_df_lnx, [(u'/', {})], {}),                                                                     # Linux
    (info_df_lnx, [(u'/', {})], { "include_volume_name" : False }),                                      # Linux w/ volume name unset
    (info_df_lnx, [(u'/dev/sda4 /', {})], { "include_volume_name" : True}),                              # Linux w/ volume name option
    (info_df_win, [(u'E:/', {}), (u'F:/', {}), (u'C:/', {})], {}),                                       # Windows
    (info_df_win, [(u'New_Volume E:/', {}), (u'New_Volume F:/', {}), (u'C:\\ C:/', {})],
                                                         { "include_volume_name" : True }),              # Windows w/ volume name option
    (info_df_lnx_tmpfs, [], {}),                                                                         # Ignoring tmpfs
    (info_df_lnx_tmpfs, [], { "ignore_fs_types" : [ 'tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660' ] }),     # Ignoring tmpfs explicitly
    (info_df_lnx_tmpfs, [(u'/opt/omd/sites/heute/tmp', {})],
                            { "ignore_fs_types" : [ 'tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660' ],        # Ignoring tmpfs explicitly, but
                              "never_ignore_mountpoints" : [ u'/opt/omd/sites/heute/tmp' ]}),            # including one mountpoint explicitly
    (info_df_lnx_tmpfs, [(u'/opt/omd/sites/heute/tmp', {}), (u'/dev/shm', {})],
                            { "ignore_fs_types" : [ 'nfs', 'smbfs', 'cifs', 'iso9660' ] }),              # Including tmpfs

    (info_df_lnx_tmpfs, [(u'tmpfs /opt/omd/sites/heute/tmp', {}), (u'tmpfs /dev/shm', {})],
                            { "ignore_fs_types" : [ 'nfs', 'smbfs', 'cifs', 'iso9660' ],
                              "include_volume_name" : True}),                                            # Including tmpfs and volume name
    (info_df_btrfs, [(u'btrfs /dev/sda1', {})], {}),                                                     # btrfs
    (info_df_btrfs, [(u'/dev/sda1 btrfs /dev/sda1', {})],
                                                         { "include_volume_name" : True }),              # btrfs w/ volume name option
    (info_solaris_zfs, [], {}),                                                                          # ignore filensystems without size
])
def test_df_discovery_with_parse(check_manager, info, expected_result, inventory_df_rules):

    check = check_manager.get_check("df")

    with MockHostExtraConf(inventory_df_rules):
        raw_discovery_result = check.run_discovery(check.run_parse(info))

    discovery_result = DiscoveryResult(raw_discovery_result)
    expected_result = DiscoveryResult(expected_result)
    assertDiscoveryResultsEqual(discovery_result, expected_result)


@pytest.mark.parametrize("item,params,info,expected_result", [
    (u"/", "default", info_df_lnx, {}),
    (u'/dev/sda4 /', "default", info_df_lnx, {}),
    (u'E:/', "default", info_df_win, {}),
    (u'New_Volume E:/', "default", info_df_win, {}),
    (u'btrfs /dev/sda1', "default", info_df_btrfs, {}),
    (u"/home", "default", info_df_lnx, {}), # When called with an item not found in info, the check should not crash.
])
def test_df_check_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("df")

    if params == "default":
        params = check.default_parameters()

    result = CheckResult(check.run_check(item, params, check.run_parse(info)))

