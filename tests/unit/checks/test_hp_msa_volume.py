import pytest
from testlib import cmk_path

# all tests in this file are hp_msa_volume check related
pytestmark = pytest.mark.checks

###### hp_msa_volume (health) #########


def test_health_parse_yields_with_volume_name_as_items(check_manager):
    info = [["volume", "1", "volume-name", "Foo"]]
    expected_yield = {'Foo': {'volume-name': 'Foo'}}
    check = check_manager.get_check("hp_msa_volume")
    parse_result = check.run_parse(info)
    assert parse_result == expected_yield


def test_health_parse_yields_volume_name_as_items_despite_of_durable_id(check_manager):
    info = [["volume", "1", "durable-id", "Foo 1"], ["volume", "1", "volume-name", "Bar 1"],
            ["volume", "1", "any-key-1", "abc"], ["volume-statistics", "1", "volume-name", "Bar 1"],
            ["volume-statistics", "1", "any-key-2", "ABC"], ["volume", "2", "durable-id", "Foo 2"],
            ["volume", "2", "volume-name", "Bar 2"], ["volume", "2", "any-key-2", "abc"],
            ["volume-statistics", "2", "volume-name", "Bar 2"],
            ["volume-statistics", "2", "any-key-2", "ABC"]]
    check = check_manager.get_check("hp_msa_volume")
    parse_result = check.run_parse(info)
    parsed_items = sorted(parse_result.iterkeys())
    expected_items = ['Bar 1', 'Bar 2']
    assert parsed_items == expected_items


def test_health_discovery_forwards_info(check_manager):
    info = [["volume", "1", "volume-name", "Foo"]]
    check = check_manager.get_check("hp_msa_volume")
    discovery_result = check.run_discovery(info)
    assert discovery_result == [(info[0], None)]


def test_health_check_accepts_volume_name_and_durable_id_as_item(check_manager):
    item_1st = "VMFS_01"
    item_2nd = "V4"
    check = check_manager.get_check("hp_msa_volume")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'container-name': u'A',
            u'health': u'OK',
            u'item_type': u'volumes',
            u'raidtype': u'RAID0',
        },
        u'V4': {
            u'durable-id': u'V4',
            u'container-name': u'B',
            u'health': u'OK',
            u'item_type': u'volumes',
            u'raidtype': u'RAID0',
        }
    }
    _, status_message_item_1st = check.run_check(item_1st, None, parsed)
    assert status_message_item_1st == 'Status: OK, container name: A (RAID0)'
    _, status_message_item_2nd = check.run_check(item_2nd, None, parsed)
    assert status_message_item_2nd == 'Status: OK, container name: B (RAID0)'


###### hp_msa_volume.df ######


def test_df_discovery_yields_volume_name_as_item(check_manager):
    parsed = {'Foo': {'durable-id': 'Bar'}}
    expected_yield = ('Foo', {})
    check = check_manager.get_check("hp_msa_volume.df")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


def test_df_check(check_manager):
    item_1st = 'VMFS_01'
    params = {'flex_levels': 'irrelevant'}
    check = check_manager.get_check("hp_msa_volume.df")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'virtual-disk-name': u'A',
            u'total-size-numeric': u'4296482816',
            u'allocated-size-numeric': u'2484011008',
            u'raidtype': u'RAID0',
        },
        u'VMFS_02': {
            u'durable-id': u'V4',
            u'virtual-disk-name': u'A',
            u'total-size-numeric': u'4296286208',
            u'allocated-size-numeric': u'3925712896',
            u'raidtype': u'RAID0',
        }
    }
    expected_result = (0, '57.81% used (1.16 of 2.00 TB), trend: 0.00 B / 24 hours',
                       [('VMFS_01', 1212896, 1678313.6, 1888102.8, 0, 2097892),
                        ('fs_size', 2097892), ('growth', 0.0), ('trend', 0, None, None, 0, 87412)])
    _, result = check.run_check(item_1st, params, parsed)
    assert result == expected_result


##### hp_msa_io.io  #####


def test_io_discovery_yields_summary(check_manager):
    parsed = {'Foo': {'durable-id': 'Bar'}}
    expected_yield = ('SUMMARY', 'diskstat_default_levels')
    check = check_manager.get_check("hp_msa_volume.io")
    for item in check.run_discovery(parsed):
        assert item == expected_yield


def test_io_check(check_manager):
    item_1st = 'VMFS_01'
    params = {'flex_levels': 'irrelevant'}
    check = check_manager.get_check("hp_msa_volume.io")
    parsed = {
        u'VMFS_01': {
            u'durable-id': u'V3',
            u'data-read-numeric': u'23719999539712',
            u'data-written-numeric': u'18093374647808',
            u'virtual-disk-name': u'A',
            u'raidtype': u'RAID0',
        },
        u'VMFS_02': {
            u'durable-id': u'V4',
            u'data-read-numeric': u'49943891507200',
            u'data-written-numeric': u'7384656100352',
            u'virtual-disk-name': u'A',
            u'raidtype': u'RAID0',
        }
    }
    _, read, written = check.run_check(item_1st, params, parsed)
    assert read == (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0, None, None)])
    assert written == (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0, None, None)])
