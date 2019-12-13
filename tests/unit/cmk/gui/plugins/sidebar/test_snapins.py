import cmk
# Needed to trigger plugin loading
import cmk.gui.sidebar  # pylint: disable=unused-import

from cmk.gui.plugins.sidebar.utils import snapin_registry


def test_registered_snapins():
    expected_snapins = [
        'about',
        'admin',
        'admin_mini',
        'biaggr_groups',
        'biaggr_groups_tree',
        'bookmarks',
        'custom_links',
        'dashboards',
        'hostgroups',
        'hostmatrix',
        'hosts',
        'master_control',
        'mkeventd_performance',
        'nagios_legacy',
        'nagvis_maps',
        'performance',
        'problem_hosts',
        'search',
        'servicegroups',
        'sitestatus',
        'speedometer',
        'tactical_overview',
        'tag_tree',
        'time',
        'views',
        'wato_folders',
        'wato_foldertree',
        'wiki',
    ]

    if not cmk.is_raw_edition():
        expected_snapins += [
            'cmc_stats',
            'reports',
        ]

    assert sorted(snapin_registry.keys()) == sorted(expected_snapins)


def test_refresh_snapins():
    expected_refresh_snapins = [
        'admin',
        'admin_mini',
        'performance',
        'hostmatrix',
        'mkeventd_performance',
        'nagvis_maps',
        'problem_hosts',
        'sitestatus',
        'tactical_overview',
        'tag_tree',
        'time',
    ]

    if not cmk.is_raw_edition():
        expected_refresh_snapins += [
            'cmc_stats',
        ]

    refresh_snapins = [s.type_name() for s in snapin_registry.values() if s.refresh_regularly()]
    assert sorted(refresh_snapins) == sorted(expected_refresh_snapins)
