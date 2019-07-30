# encoding: utf-8
# pylint: disable=redefined-outer-name

import json
import six
import pytest  # type: ignore
from pathlib2 import Path

import cmk.utils.paths
import cmk.gui.modules as modules
import cmk.gui.config as config
import cmk.gui.permissions as permissions
from cmk.gui.globals import html
from cmk.gui.permissions import (
    permission_section_registry,
    permission_registry,
)

pytestmark = pytest.mark.usefixtures("load_plugins")


def test_registered_permission_sections():
    expected_sections = [
        ('graph_collection', (50, u'Graph Collections', True)),
        ('graph_tuning', (50, u'Graph tunings', True)),
        ('sla_configuration', (50, u'Service Level Agreements', True)),
        ('custom_graph', (50, u'Custom Graphs', True)),
        ('bookmark_list', (50, u'Bookmark lists', True)),
        ('custom_snapin', (50, u'Custom snapins', True)),
        ('sidesnap', (50, u'Sidebar snapins', True)),
        ('notification_plugin', (50, u'Notification plugins', True)),
        ('wato', (50, u"WATO - Check_MK's Web Administration Tool", False)),
        ('background_jobs', (50, u'Background jobs', False)),
        ('bi', (50, u'BI - Check_MK Business Intelligence', False)),
        ('general', (10, u'General Permissions', False)),
        ('mkeventd', (50, u'Event Console', False)),
        ('action', (50, u'Commands on host and services', True)),
        ('dashboard', (50, u'Dashboards', True)),
        ('report', (50, u'Reports', True)),
        ('nagvis', (50, u'NagVis', False)),
        ('view', (50, u'Views', True)),
        ('icons_and_actions', (50, u'Icons', True)),
    ]

    section_names = permission_section_registry.keys()
    assert sorted([s[0] for s in expected_sections]) == sorted(section_names)

    for name, (sort_index, title, do_sort) in expected_sections:
        section = permission_section_registry[name]()
        assert section.title == title
        assert section.sort_index == sort_index
        assert section.do_sort == do_sort


def test_registered_permissions():
    expected_permissions = [
        'action.acknowledge',
        'action.addcomment',
        'action.clearmodattr',
        'action.customnotification',
        'action.downtimes',
        'action.enablechecks',
        'action.fakechecks',
        'action.notifications',
        'action.remove_all_downtimes',
        'action.reschedule',
        'action.star',
        'background_jobs.delete_foreign_jobs',
        'background_jobs.delete_jobs',
        'background_jobs.manage_jobs',
        'background_jobs.see_foreign_jobs',
        'background_jobs.stop_foreign_jobs',
        'background_jobs.stop_jobs',
        'bi.see_all',
        'dashboard.main',
        'dashboard.simple_problems',
        'dashboard.topology',
        'general.acknowledge_werks',
        'general.act',
        'general.change_password',
        'general.configure_sidebar',
        'general.csv_export',
        'general.delete_foreign_bookmark_list',
        'general.delete_foreign_custom_graph',
        'general.delete_foreign_custom_snapin',
        'general.delete_foreign_dashboards',
        'general.delete_foreign_graph_collection',
        'general.delete_foreign_graph_tuning',
        'general.delete_foreign_reports',
        'general.delete_foreign_sla_configuration',
        'general.delete_foreign_stored_report',
        'general.delete_foreign_views',
        'general.delete_stored_report',
        'general.disable_notifications',
        'general.edit_bookmark_list',
        'general.edit_custom_graph',
        'general.edit_custom_snapin',
        'general.edit_dashboards',
        'general.edit_foreign_bookmark_list',
        'general.edit_foreign_custom_graph',
        'general.edit_foreign_custom_snapin',
        'general.edit_foreign_dashboards',
        'general.edit_foreign_graph_collection',
        'general.edit_foreign_graph_tuning',
        'general.edit_foreign_reports',
        'general.edit_foreign_sla_configuration',
        'general.edit_foreign_views',
        'general.edit_graph_collection',
        'general.edit_graph_tuning',
        'general.edit_notifications',
        'general.edit_profile',
        'general.edit_reports',
        'general.edit_sla_configuration',
        'general.edit_user_attributes',
        'general.edit_views',
        'general.force_bookmark_list',
        'general.force_custom_graph',
        'general.force_custom_snapin',
        'general.force_dashboards',
        'general.force_graph_collection',
        'general.force_graph_tuning',
        'general.force_reports',
        'general.force_sla_configuration',
        'general.force_views',
        'general.ignore_hard_limit',
        'general.ignore_soft_limit',
        'general.instant_reports',
        'general.logout',
        'general.notify',
        'general.painter_options',
        'general.publish_bookmark_list',
        'general.publish_to_foreign_groups_bookmark_list',
        'general.publish_custom_graph',
        'general.publish_to_foreign_groups_custom_graph',
        'general.publish_custom_snapin',
        'general.publish_to_foreign_groups_custom_snapin',
        'general.publish_dashboards',
        'general.publish_dashboards_to_foreign_groups',
        'general.publish_graph_collection',
        'general.publish_to_foreign_groups_graph_collection',
        'general.publish_graph_tuning',
        'general.publish_to_foreign_groups_graph_tuning',
        'general.publish_reports',
        'general.publish_reports_to_foreign_groups',
        'general.publish_sla_configuration',
        'general.publish_to_foreign_groups_sla_configuration',
        'general.publish_stored_report',
        'general.publish_views',
        'general.publish_views_to_foreign_groups',
        'general.reporting',
        'general.schedule_reports',
        'general.schedule_reports_all',
        'general.see_all',
        'general.see_availability',
        'general.see_crash_reports',
        'general.see_failed_notifications',
        'general.see_failed_notifications_24h',
        'general.see_sidebar',
        'general.see_stales_in_tactical_overview',
        'general.see_user_bookmark_list',
        'general.see_user_custom_graph',
        'general.see_user_custom_snapin',
        'general.see_user_dashboards',
        'general.see_user_graph_collection',
        'general.see_user_graph_tuning',
        'general.see_user_reports',
        'general.see_user_sla_configuration',
        'general.see_user_stored_report',
        'general.see_user_views',
        'general.use',
        'general.view_option_columns',
        'general.view_option_refresh',
        'icons_and_actions.action_menu',
        'icons_and_actions.agent_deployment',
        'icons_and_actions.aggregation_checks',
        'icons_and_actions.aggregations',
        'icons_and_actions.check_manpage',
        'icons_and_actions.check_period',
        'icons_and_actions.crashed_check',
        'icons_and_actions.custom_action',
        'icons_and_actions.deployment_status',
        'icons_and_actions.download_agent_output',
        'icons_and_actions.download_snmp_walk',
        'icons_and_actions.icon_image',
        'icons_and_actions.inventory',
        'icons_and_actions.logwatch',
        'icons_and_actions.mkeventd',
        'icons_and_actions.notes',
        'icons_and_actions.perfgraph',
        'icons_and_actions.prediction',
        'icons_and_actions.reschedule',
        'icons_and_actions.rule_editor',
        'icons_and_actions.stars',
        'icons_and_actions.status_acknowledged',
        'icons_and_actions.status_active_checks',
        'icons_and_actions.status_comments',
        'icons_and_actions.status_downtimes',
        'icons_and_actions.status_flapping',
        'icons_and_actions.status_notification_period',
        'icons_and_actions.status_notifications_enabled',
        'icons_and_actions.status_passive_checks',
        'icons_and_actions.status_service_period',
        'icons_and_actions.status_shadow',
        'icons_and_actions.status_stale',
        'icons_and_actions.wato',
        'mkeventd.actions',
        'mkeventd.activate',
        'mkeventd.archive_events_of_hosts',
        'mkeventd.changestate',
        'mkeventd.config',
        'mkeventd.delete',
        'mkeventd.edit',
        'mkeventd.see_in_tactical_overview',
        'mkeventd.seeall',
        'mkeventd.seeunrelated',
        'mkeventd.switchmode',
        'mkeventd.update',
        'mkeventd.update_comment',
        'mkeventd.update_contact',
        'nagvis.*_*_*',
        'nagvis.Map_delete',
        'nagvis.Map_delete_*',
        'nagvis.Map_edit',
        'nagvis.Map_edit_*',
        'nagvis.Map_view',
        'nagvis.Map_view_*',
        'nagvis.Rotation_view_*',
        'notification_plugin.asciimail',
        'notification_plugin.jira_issues',
        'notification_plugin.mail',
        'notification_plugin.mkeventd',
        'notification_plugin.opsgenie_issues',
        'notification_plugin.pagerduty',
        'notification_plugin.pushover',
        'notification_plugin.servicenow',
        'notification_plugin.slack',
        'notification_plugin.sms',
        'notification_plugin.spectrum',
        'notification_plugin.victorops',
        'report.bi_availability',
        'report.default',
        'report.host',
        'report.instant',
        'report.instant_availability',
        'report.instant_graph_collection',
        'report.instant_view',
        'report.service_availability',
        'sidesnap.about',
        'sidesnap.admin',
        'sidesnap.admin_mini',
        'sidesnap.biaggr_groups',
        'sidesnap.biaggr_groups_tree',
        'sidesnap.bookmarks',
        'sidesnap.cmc_stats',
        'sidesnap.custom_links',
        'sidesnap.dashboards',
        'sidesnap.hostgroups',
        'sidesnap.hostmatrix',
        'sidesnap.hosts',
        'sidesnap.master_control',
        'sidesnap.mkeventd_performance',
        'sidesnap.nagios_legacy',
        'sidesnap.nagvis_maps',
        'sidesnap.performance',
        'sidesnap.problem_hosts',
        'sidesnap.reports',
        'sidesnap.search',
        'sidesnap.servicegroups',
        'sidesnap.sitestatus',
        'sidesnap.speedometer',
        'sidesnap.tactical_overview',
        'sidesnap.tag_tree',
        'sidesnap.time',
        'sidesnap.views',
        'sidesnap.wato_folders',
        'sidesnap.wato_foldertree',
        'sidesnap.wiki',
        'view.aggr_all',
        'view.aggr_all_api',
        'view.aggr_group',
        'view.aggr_host',
        'view.aggr_hostgroup_boxed',
        'view.aggr_hostnameaggrs',
        'view.aggr_hostproblems',
        'view.aggr_problems',
        'view.aggr_service',
        'view.aggr_single',
        'view.aggr_single_api',
        'view.aggr_singlehost',
        'view.aggr_singlehosts',
        'view.aggr_summary',
        'view.alerthandlers',
        'view.alertstats',
        'view.allhosts',
        'view.allhosts_deploy',
        'view.allhosts_mini',
        'view.bi_map_hover_host',
        'view.bi_map_hover_service',
        'view.allservices',
        'view.api_downtimes',
        'view.comments',
        'view.comments_of_host',
        'view.comments_of_service',
        'view.contactnotifications',
        'view.downtime_history',
        'view.downtimes',
        'view.downtimes_of_host',
        'view.downtimes_of_service',
        'view.ec_event',
        'view.ec_event_mobile',
        'view.ec_events',
        'view.ec_events_mobile',
        'view.ec_events_of_host',
        'view.ec_events_of_monhost',
        'view.ec_history_of_event',
        'view.ec_history_of_host',
        'view.ec_history_recent',
        'view.ec_historyentry',
        'view.events',
        'view.events_dash',
        'view.failed_notifications',
        'view.host',
        'view.host_crit',
        'view.host_dt_hist',
        'view.host_export',
        'view.host_graphs',
        'view.host_ok',
        'view.host_pending',
        'view.host_unknown',
        'view.host_warn',
        'view.hostevents',
        'view.hostgroup',
        'view.hostgroupgrid',
        'view.hostgroups',
        'view.hostgroupservices',
        'view.hostnotifications',
        'view.hostpnp',
        'view.hostproblems',
        'view.hostproblems_dash',
        'view.hosts',
        'view.hostsbygroup',
        'view.hoststatus',
        'view.hostsvcevents',
        'view.hostsvcnotifications',
        'view.hosttiles',
        'view.inv_host',
        'view.inv_host_history',
        'view.inv_hosts_cpu',
        'view.inv_hosts_ports',
        'view.invbackplane_of_host',
        'view.invbackplane_search',
        'view.invchassis_of_host',
        'view.invchassis_search',
        'view.invcontainer_of_host',
        'view.invcontainer_search',
        'view.invdockercontainers_of_host',
        'view.invdockercontainers_search',
        'view.invdockerimages_of_host',
        'view.invdockerimages_search',
        'view.invfan_of_host',
        'view.invfan_search',
        'view.invinterface_of_host',
        'view.invinterface_search',
        'view.invmodule_of_host',
        'view.invmodule_search',
        'view.invoradataguardstats_of_host',
        'view.invoradataguardstats_search',
        'view.invorainstance_of_host',
        'view.invorainstance_search',
        'view.invorarecoveryarea_of_host',
        'view.invorarecoveryarea_search',
        'view.invorasga_of_host',
        'view.invorasga_search',
        'view.invoratablespace_of_host',
        'view.invoratablespace_search',
        'view.invother_of_host',
        'view.invother_search',
        'view.invpsu_of_host',
        'view.invpsu_search',
        'view.invsensor_of_host',
        'view.invsensor_search',
        'view.invstack_of_host',
        'view.invstack_search',
        'view.invswpac_of_host',
        'view.invswpac_search',
        'view.invtunnels_of_host',
        'view.invtunnels_search',
        'view.invunknown_of_host',
        'view.invunknown_search',
        'view.logfile',
        'view.mobile_contactnotifications',
        'view.mobile_events',
        'view.mobile_host',
        'view.mobile_hostproblems',
        'view.mobile_hostproblems_unack',
        'view.mobile_hoststatus',
        'view.mobile_hostsvcevents',
        'view.mobile_hostsvcnotifications',
        'view.mobile_notifications',
        'view.mobile_searchhost',
        'view.mobile_searchsvc',
        'view.mobile_service',
        'view.mobile_svcevents',
        'view.mobile_svcnotifications',
        'view.mobile_svcproblems',
        'view.mobile_svcproblems_unack',
        'view.nagstamon_hosts',
        'view.nagstamon_svc',
        'view.notifications',
        'view.pending_discovery',
        'view.pendingsvc',
        'view.perf_matrix',
        'view.perf_matrix_search',
        'view.problemsofhost',
        'view.recentsvc',
        'view.searchhost',
        'view.searchpnp',
        'view.searchsvc',
        'view.service',
        'view.service_check_durations',
        'view.service_graphs',
        'view.servicedesc',
        'view.servicedescpnp',
        'view.servicegroup',
        'view.sitehosts',
        'view.sitesvcs',
        'view.stale_hosts',
        'view.starred_hosts',
        'view.starred_services',
        'view.svc_dt_hist',
        'view.svcbygroups',
        'view.svcbyhgroups',
        'view.svcevents',
        'view.svcgroups',
        'view.svcgroups_grid',
        'view.svcnotifications',
        'view.svcproblems',
        'view.svcproblems_dash',
        'view.uncheckedsvc',
        'view.unmonitored_services',
        'wato.activate',
        'wato.activateforeign',
        'wato.add_or_modify_executables',
        'wato.agent_deploy_custom_files',
        'wato.agent_deployment',
        'wato.agents',
        'wato.alert_handlers',
        'wato.all_folders',
        'wato.analyze_config',
        'wato.api_allowed',
        'wato.auditlog',
        'wato.automation',
        'wato.backups',
        'wato.bake_agents',
        'wato.bi_admin',
        'wato.bi_rules',
        'wato.clear_auditlog',
        'wato.clone_hosts',
        'wato.custom_attributes',
        'wato.dcd_connections',
        'wato.diag_host',
        'wato.download_agent_output',
        'wato.download_agents',
        'wato.download_all_agents',
        'wato.edit',
        'wato.edit_all_passwords',
        'wato.edit_all_predefined_conditions',
        'wato.edit_folders',
        'wato.edit_hosts',
        'wato.global',
        'wato.groups',
        'wato.hosts',
        'wato.hosttags',
        'wato.icons',
        'wato.manage_folders',
        'wato.manage_hosts',
        'wato.manage_mkps',
        'wato.mkps',
        'wato.move_hosts',
        'wato.notifications',
        'wato.parentscan',
        'wato.passwords',
        'wato.pattern_editor',
        'wato.random_hosts',
        'wato.rename_hosts',
        'wato.rulesets',
        'wato.see_all_folders',
        'wato.seeall',
        'wato.service_discovery_to_ignored',
        'wato.service_discovery_to_monitored',
        'wato.service_discovery_to_removed',
        'wato.service_discovery_to_undecided',
        'wato.services',
        'wato.set_read_only',
        'wato.sign_agents',
        'wato.sites',
        'wato.snapshots',
        'wato.timeperiods',
        'wato.update_dns_cache',
        'wato.use',
        'wato.users',
    ]

    assert sorted(expected_permissions) == sorted(permission_registry.keys())

    for perm_class in permission_registry.values():
        perm = perm_class()
        assert isinstance(perm.description, six.string_types)
        assert isinstance(perm.title, six.string_types)
        assert isinstance(perm.defaults, list)


def test_declare_permission_section(monkeypatch):
    monkeypatch.setattr(permissions, "permission_section_registry",
                        permissions.PermissionSectionRegistry())
    assert "bla" not in permissions.permission_section_registry
    config.declare_permission_section("bla", u"bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    section = permissions.permission_section_registry["bla"]()
    assert section.title == u"bla perm"
    assert section.sort_index == 50
    assert section.do_sort is False


def test_declare_permission(monkeypatch):
    monkeypatch.setattr(permissions, "permission_section_registry",
                        permissions.PermissionSectionRegistry())
    assert "bla" not in permissions.permission_section_registry
    config.declare_permission_section("bla", u"bla perm", do_sort=False)
    assert "bla" in permissions.permission_section_registry

    monkeypatch.setattr(permissions, "permission_registry", permissions.PermissionRegistry())
    assert "bla.blub" not in permissions.permission_registry
    config.declare_permission("bla.blub", u"bla perm", u"descrrrrr", ["admin"])
    assert "bla.blub" in permissions.permission_registry

    permission = permissions.permission_registry["bla.blub"]()
    assert permission.section == permissions.permission_section_registry["bla"]
    assert permission.name == "bla.blub"
    assert permission.title == u"bla perm"
    assert permission.description == "descrrrrr"
    assert permission.defaults == ["admin"]


@pytest.mark.parametrize("do_sort,result", [
    (True, ['sec1.1', 'sec1.A', 'sec1.a', 'sec1.b', 'sec1.g', 'sec1.Z', 'sec1.z']),
    (False, ['sec1.Z', 'sec1.z', 'sec1.A', 'sec1.b', 'sec1.a', 'sec1.1', 'sec1.g']),
])
def test_permission_sorting(do_sort, result):
    sections = permissions.PermissionSectionRegistry()
    perms = permissions.PermissionRegistry()

    @sections.register
    class Sec1(permissions.PermissionSection):
        @property
        def name(self):
            return "sec1"

        @property
        def title(self):
            return "SEC1"

        @property
        def do_sort(self):
            return do_sort

    section_name = "sec1"
    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        cls = type(
            "TestPermission%s%s" % (section_name.title(), permission_name.title()),
            (permissions.Permission,), {
                "section": Sec1,
                "permission_name": permission_name,
                "title": permission_name.title(),
                "description": "bla",
                "defaults": ["admin"],
            })
        perms.register(cls)

    sorted_perms = [p.name for p in perms.get_sorted_permissions(Sec1())]
    assert sorted_perms == result


@pytest.mark.parametrize(
    "site,result",
    [
        # Possible formats pre 1.6:
        ({}, {
            "socket": ("local", None),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": None,
        }, {
            "socket": ("local", None),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": "disabled"
        }, {
            "socket": ("local", None),
            "disabled": True,
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": "unix:/ab:c/xyz"
        }, {
            "socket": ("unix", {
                "path": "/ab:c/xyz"
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": "tcp:127.0.0.1:1234"
        }, {
            "socket": ("tcp", {
                "address": ("127.0.0.1", 1234),
                "tls": ("plain_text", {}),
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": "tcp6:::1:1234"
        }, {
            "socket": ("tcp6", {
                "address": ("::1", 1234),
                "tls": ("plain_text", {}),
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("proxy", {
                "socket": None,
            })
        }, {
            "socket": ("local", None),
            "proxy": {},
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("proxy", {
                "socket": ("127.0.0.1", 6790),
            })
        }, {
            "socket": ("tcp", {
                "address": ("127.0.0.1", 6790),
                "tls": ("plain_text", {}),
            }),
            "proxy": {},
            "replication": None,
            "url_prefix": "/mysite/",
        }),

        # Is allowed in 1.6 and should not be converted
        ({
            "proxy": {},
            "socket": ("unix", {
                "path": "/a/b/c"
            })
        }, {
            "socket": ("unix", {
                "path": "/a/b/c"
            }),
            "proxy": {},
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("tcp", {
                "address": ("127.0.0.1", 1234),
                "tls": ("plain_text", {}),
            })
        }, {
            "socket": ("tcp", {
                "address": ("127.0.0.1", 1234),
                "tls": ("plain_text", {}),
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("tcp6", {
                "address": ("::1", 1234),
                "tls": ("plain_text", {}),
            }),
        }, {
            "socket": ("tcp6", {
                "address": ("::1", 1234),
                "tls": ("plain_text", {}),
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("local", None)
        }, {
            "socket": ("local", None),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
        ({
            "socket": ("unix", {
                "path": "/a/b/c"
            })
        }, {
            "socket": ("unix", {
                "path": "/a/b/c"
            }),
            "proxy": None,
            "replication": None,
            "url_prefix": "/mysite/",
        }),
    ])
def test_migrate_old_site_config(site, result):
    assert config.migrate_old_site_config({"mysite": site}) == {"mysite": result}


@pytest.fixture()
def theme_dirs(tmp_path, monkeypatch):
    theme_path = tmp_path / "htdocs" / "themes"
    theme_path.mkdir(parents=True)

    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)

    monkeypatch.setattr(cmk.utils.paths, "web_dir", str(tmp_path))
    monkeypatch.setattr(cmk.utils.paths, "local_web_dir", str(tmp_path / "local"))

    return theme_path, local_theme_path


@pytest.fixture()
def my_theme(theme_dirs):
    theme_path = theme_dirs[0]
    my_dir = theme_path / "my_theme"
    my_dir.mkdir()
    my_dir.joinpath("theme.json").open(mode="w", encoding="utf-8").write(
        unicode(json.dumps({"title": "Määh Theme :-)"})))
    return my_dir


def test_theme_choices_empty(theme_dirs):
    assert config.theme_choices() == []


def test_theme_choices_normal(my_theme):
    assert config.theme_choices() == [("my_theme", u"Määh Theme :-)")]


def test_theme_choices_local_theme(theme_dirs, my_theme):
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_improved_theme"
    my_dir.mkdir()
    my_dir.joinpath("theme.json").open(mode="w", encoding="utf-8").write(
        unicode(json.dumps({"title": "Määh Bettr Theme :-D"})))

    assert config.theme_choices() == sorted([
        ("my_theme", u"Määh Theme :-)"),
        ("my_improved_theme", u"Määh Bettr Theme :-D"),
    ])


def test_theme_choices_override(theme_dirs, my_theme):
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_theme"
    my_dir.mkdir()
    my_dir.joinpath("theme.json").open(mode="w", encoding="utf-8").write(
        unicode(json.dumps({"title": "Fixed theme"})))

    assert config.theme_choices() == sorted([
        ("my_theme", u"Fixed theme"),
    ])


def test_theme_broken_meta(my_theme):
    my_theme.joinpath("theme.json").open(mode="w", encoding="utf-8").write(
        unicode("{\"titlewrong\": xyz\"bla\"}"))

    assert config.theme_choices() == sorted([
        ("my_theme", u"my_theme"),
    ])


def test_html_set_theme(my_theme, register_builtin_html):
    html.set_theme(None)
    assert html.get_theme() == "facelift"

    html.set_theme("not_existing")
    assert html.get_theme() == "facelift"

    html.set_theme("my_theme")
    assert html.get_theme() == "my_theme"


@pytest.mark.usefixtures("load_config")
def test_default_tags():
    groups = {
        "snmp_ds": [
            'no-snmp',
            'snmp-v1',
            'snmp-v2',
        ],
        "address_family": [
            'ip-v4-only',
            'ip-v4v6',
            'ip-v6-only',
            'no-ip',
        ],
        "piggyback": [
            "auto-piggyback",
            "piggyback",
            "no-piggyback",
        ],
        "agent": [
            'all-agents',
            'cmk-agent',
            'no-agent',
            'special-agents',
        ],
    }

    assert sorted(dict(config.tags.get_tag_group_choices()).keys()) == sorted(groups.keys())

    for tag_group in config.tags.tag_groups:
        assert sorted(tag_group.get_tag_ids()) == sorted(groups[tag_group.id])


@pytest.mark.usefixtures("load_config")
def test_default_aux_tags():
    assert sorted(config.tags.aux_tag_list.get_tag_ids()) == sorted([
        'ip-v4',
        'ip-v6',
        'ping',
        'snmp',
        'tcp',
    ])
