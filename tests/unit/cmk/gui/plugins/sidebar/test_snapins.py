# Needed to trigger plugin loading
import cmk.gui.sidebar  # pylint: disable=unused-import

from cmk.gui.plugins.sidebar.utils import snapin_registry


def test_registered_snapins():
    assert sorted(snapin_registry.keys()) == sorted([
        'about',
        'admin',
        'admin_mini',
        'biaggr_groups',
        'biaggr_groups_tree',
        'bookmarks',
        'cmc_stats',
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
        'reports',
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
    ])


def test_refresh_snapins():
    refresh_snapins = [s.type_name() for s in snapin_registry.values() if s.refresh_regularly()]
    assert sorted(refresh_snapins) == sorted([
        'admin',
        'admin_mini',
        'cmc_stats',
        'performance',
        'hostmatrix',
        'mkeventd_performance',
        'nagvis_maps',
        'problem_hosts',
        'sitestatus',
        'tactical_overview',
        'tag_tree',
        'time',
    ])
