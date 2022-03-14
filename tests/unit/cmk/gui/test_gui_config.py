#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import json
from pathlib import Path

import pytest  # type: ignore[import]
from flask_babel.speaklater import LazyString  # type: ignore[import]

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.gui.config as config
import cmk.gui.permissions as permissions
from cmk.gui.exceptions import MKAuthException
from cmk.gui.globals import html
from cmk.gui.permissions import Permission, permission_registry, permission_section_registry
from cmk.gui.watolib.utils import may_edit_ruleset

pytestmark = pytest.mark.usefixtures("load_plugins")


def test_sorted_sites(mocker):
    mocker.patch.object(config.user,
                        "authorized_sites",
                        return_value={
                            'site1': {
                                'alias': 'Site 1'
                            },
                            'site3': {
                                'alias': 'Site 3'
                            },
                            'site5': {
                                'alias': 'Site 5'
                            },
                            'site23': {
                                'alias': 'Site 23'
                            },
                            'site6': {
                                'alias': 'Site 6'
                            },
                            'site12': {
                                'alias': 'Site 12'
                            },
                        })
    expected = [('site1', 'Site 1'), ('site12', 'Site 12'), ('site23', 'Site 23'),
                ('site3', 'Site 3'), ('site5', 'Site 5'), ('site6', 'Site 6')]
    assert config.sorted_sites() == expected


def test_registered_permission_sections():
    expected_sections = [
        ('bookmark_list', (50, u'Bookmark lists', True)),
        ('custom_snapin', (50, u'Custom sidebar elements', True)),
        ('sidesnap', (50, u'Sidebar elements', True)),
        ('notification_plugin', (50, u'Notification plugins', True)),
        ('wato', (50, u"WATO - Checkmk's Web Administration Tool", False)),
        ('background_jobs', (50, u'Background jobs', False)),
        ('bi', (50, u'BI - Checkmk Business Intelligence', False)),
        ('general', (10, u'General Permissions', False)),
        ('mkeventd', (50, u'Event Console', False)),
        ('action', (50, u'Commands on host and services', True)),
        ('dashboard', (50, u'Dashboards', True)),
        ('nagvis', (50, u'NagVis', False)),
        ('view', (50, u'Views', True)),
        ('icons_and_actions', (50, u'Icons', True)),
        ('pagetype_topic', (50, u'Topics', True)),
    ]

    if not cmk_version.is_raw_edition():
        expected_sections += [
            ('custom_graph', (50, u'Custom graphs', True)),
            ('forecast_graph', (50, u'Forecast graphs', True)),
            ('graph_collection', (50, u'Graph collections', True)),
            ('graph_tuning', (50, u'Graph tunings', True)),
            ('sla_configuration', (50, u'Service Level Agreements', True)),
            ('report', (50, u'Reports', True)),
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
        'action.delete_crash_report',
        'background_jobs.delete_foreign_jobs',
        'background_jobs.delete_jobs',
        'background_jobs.manage_jobs',
        'background_jobs.see_foreign_jobs',
        'background_jobs.stop_foreign_jobs',
        'background_jobs.stop_jobs',
        'bi.see_all',
        'dashboard.main',
        'dashboard.simple_problems',
        'dashboard.checkmk',
        'dashboard.checkmk_host',
        'general.acknowledge_werks',
        'general.act',
        'general.change_password',
        'general.configure_sidebar',
        'general.csv_export',
        'general.delete_foreign_pagetype_topic',
        'general.edit_pagetype_topic',
        'general.edit_foreign_pagetype_topic',
        'general.force_pagetype_topic',
        'general.publish_pagetype_topic',
        'general.publish_to_foreign_groups_pagetype_topic',
        'general.see_user_pagetype_topic',
        'general.delete_foreign_bookmark_list',
        'general.delete_foreign_custom_snapin',
        'general.delete_foreign_dashboards',
        'general.delete_foreign_views',
        'general.disable_notifications',
        'general.edit_bookmark_list',
        'general.edit_custom_snapin',
        'general.edit_dashboards',
        'general.edit_foreign_bookmark_list',
        'general.edit_foreign_dashboards',
        'general.edit_foreign_views',
        'general.edit_foreign_custom_snapin',
        'general.edit_notifications',
        'general.edit_profile',
        'general.edit_user_attributes',
        'general.edit_views',
        'general.force_bookmark_list',
        'general.force_custom_snapin',
        'general.force_dashboards',
        'general.force_views',
        'general.ignore_hard_limit',
        'general.ignore_soft_limit',
        'general.logout',
        'general.notify',
        'general.painter_options',
        'general.parent_child_topology',
        'general.publish_bookmark_list',
        'general.publish_to_foreign_groups_bookmark_list',
        'general.publish_custom_snapin',
        'general.publish_to_foreign_groups_custom_snapin',
        'general.publish_dashboards',
        'general.publish_dashboards_to_foreign_groups',
        'general.publish_views',
        'general.publish_views_to_foreign_groups',
        'general.see_all',
        'general.see_availability',
        'general.see_crash_reports',
        'general.see_failed_notifications',
        'general.see_failed_notifications_24h',
        'general.see_sidebar',
        'general.see_stales_in_tactical_overview',
        'general.see_user_bookmark_list',
        'general.see_user_custom_snapin',
        'general.see_user_dashboards',
        'general.see_user_views',
        'general.use',
        'general.view_option_columns',
        'general.view_option_refresh',
        'icons_and_actions.action_menu',
        'icons_and_actions.aggregation_checks',
        'icons_and_actions.aggregations',
        'icons_and_actions.check_manpage',
        'icons_and_actions.check_period',
        'icons_and_actions.crashed_check',
        'icons_and_actions.custom_action',
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
        'icons_and_actions.status_stale',
        'icons_and_actions.wato',
        'icons_and_actions.parent_child_topology',
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
        'notification_plugin.cisco_webex_teams',
        'notification_plugin.jira_issues',
        'notification_plugin.mail',
        'notification_plugin.mkeventd',
        'notification_plugin.opsgenie_issues',
        'notification_plugin.pagerduty',
        'notification_plugin.pushover',
        'notification_plugin.servicenow',
        'notification_plugin.signl4',
        'notification_plugin.ilert',
        'notification_plugin.slack',
        'notification_plugin.sms',
        'notification_plugin.sms_api',
        'notification_plugin.spectrum',
        'notification_plugin.victorops',
        'sidesnap.about',
        'sidesnap.admin',
        'sidesnap.admin_mini',
        'sidesnap.biaggr_groups',
        'sidesnap.biaggr_groups_tree',
        'sidesnap.bookmarks',
        'sidesnap.custom_links',
        'sidesnap.dashboards',
        'sidesnap.hostgroups',
        'sidesnap.hostmatrix',
        'sidesnap.hosts',
        'sidesnap.master_control',
        'sidesnap.mkeventd_performance',
        'sidesnap.nagvis_maps',
        'sidesnap.performance',
        'sidesnap.problem_hosts',
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
        'view.allservices',
        'view.bi_map_hover_host',
        'view.bi_map_hover_service',
        'view.api_downtimes',
        'view.comments',
        'view.comments_of_host',
        'view.comments_of_service',
        'view.contactnotifications',
        'view.crash_reports',
        'view.downtime_history',
        'view.downtimes',
        'view.downtimes_of_host',
        'view.downtimes_of_service',
        'view.docker_containers',
        'view.docker_nodes',
        'view.vpshere_vms',
        'view.vsphere_servers',
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
        'view.host_ok',
        'view.host_pending',
        'view.host_unknown',
        'view.host_warn',
        'view.hostevents',
        'view.hostgroup',
        'view.hostgroup_up',
        'view.hostgroup_down',
        'view.hostgroup_unreach',
        'view.hostgroup_pend',
        'view.hostgroups',
        'view.hostgroupservices',
        'view.hostgroupservices_ok',
        'view.hostgroupservices_warn',
        'view.hostgroupservices_crit',
        'view.hostgroupservices_unknwn',
        'view.hostgroupservices_pend',
        'view.hostnotifications',
        'view.hostpnp',
        'view.hostproblems',
        'view.hostproblems_dash',
        'view.hosts',
        'view.hoststatus',
        'view.hostsvcevents',
        'view.hostsvcnotifications',
        'view.inv_host',
        'view.inv_host_history',
        'view.inv_hosts_cpu',
        'view.inv_hosts_ports',
        'view.invbackplane_of_host',
        'view.invbackplane_search',
        'view.invchassis_of_host',
        'view.invchassis_search',
        'view.invcmksites_of_host',
        'view.invcmksites_search',
        'view.invcmkversions_of_host',
        'view.invcmkversions_search',
        'view.invcontainer_of_host',
        'view.invcontainer_search',
        'view.invdockercontainers_of_host',
        'view.invdockercontainers_search',
        'view.invdockerimages_of_host',
        'view.invdockerimages_search',
        'view.invfan_of_host',
        'view.invfan_search',
        'view.invibmmqchannels_of_host',
        'view.invibmmqchannels_search',
        'view.invibmmqmanagers_of_host',
        'view.invibmmqmanagers_search',
        'view.invibmmqqueues_of_host',
        'view.invibmmqqueues_search',
        'view.invinterface_of_host',
        'view.invinterface_search',
        'view.invkernelconfig_of_host',
        'view.invkernelconfig_search',
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
        'view.invorapga_of_host',
        'view.invorapga_search',
        'view.invoratablespace_of_host',
        'view.invoratablespace_search',
        'view.invorasystemparameter_of_host',
        'view.invorasystemparameter_search',
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
        'view.servicedesc',
        'view.servicedescpnp',
        'view.servicegroup',
        'view.sitehosts',
        'view.sitesvcs',
        'view.sitesvcs_crit',
        'view.sitesvcs_ok',
        'view.sitesvcs_pend',
        'view.sitesvcs_unknwn',
        'view.sitesvcs_warn',
        'view.stale_hosts',
        'view.svc_dt_hist',
        'view.svcevents',
        'view.svcgroups',
        'view.svcnotifications',
        'view.svcproblems',
        'view.svcproblems_dash',
        'view.topology_hover_host',
        'view.topology_filters',
        'view.uncheckedsvc',
        'view.unmonitored_services',
        'wato.activate',
        'wato.activateforeign',
        'wato.add_or_modify_executables',
        'wato.all_folders',
        'wato.analyze_config',
        'wato.api_allowed',
        'wato.auditlog',
        'wato.automation',
        'wato.backups',
        'wato.bi_admin',
        'wato.bi_rules',
        'wato.check_plugins',
        'wato.clear_auditlog',
        'wato.clone_hosts',
        'wato.custom_attributes',
        'wato.diag_host',
        'wato.diagnostics',
        'wato.download_agent_output',
        'wato.download_agents',
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
        'wato.sites',
        'wato.snapshots',
        'wato.timeperiods',
        'wato.update_dns_cache',
        'wato.use',
        'wato.users',
        'wato.show_last_user_activity',
        'view.cmk_servers',
        'view.cmk_sites',
        'view.cmk_sites_of_host',
        'view.host_graphs',
        'view.service_graphs',
    ]

    if not cmk_version.is_raw_edition():
        expected_permissions += [
            'dashboard.problems',
            'dashboard.site',
            'dashboard.ntop_alerts',
            'dashboard.ntop_flows',
            'dashboard.ntop_top_talkers',
            'general.edit_reports',
            'icons_and_actions.agent_deployment',
            'icons_and_actions.status_shadow',
            'report.bi_availability',
            'report.default',
            'report.host',
            'report.instant',
            'report.instant_availability',
            'report.instant_graph_collection',
            'report.instant_view',
            'report.service_availability',
            'report.host_performance_graphs',
            'sidesnap.cmc_stats',
            'sidesnap.reports',
            'view.allhosts_deploy',
            'view.ntop_interfaces',
            'wato.agent_deploy_custom_files',
            'wato.agent_deployment',
            'wato.agents',
            'wato.alert_handlers',
            'wato.bake_agents',
            'wato.dcd_connections',
            'wato.download_all_agents',
            'wato.license_usage',
            'wato.submit_license_usage',
            'wato.manage_mkps',
            'wato.mkps',
            'wato.sign_agents',
            'general.delete_foreign_custom_graph',
            'general.delete_foreign_forecast_graph',
            'general.delete_foreign_graph_collection',
            'general.delete_foreign_graph_tuning',
            'general.delete_foreign_reports',
            'general.delete_foreign_sla_configuration',
            'general.delete_foreign_stored_report',
            'general.delete_stored_report',
            'general.edit_custom_graph',
            'general.edit_forecast_graph',
            'general.edit_foreign_forecast_graph',
            'general.edit_foreign_custom_graph',
            'general.edit_foreign_graph_collection',
            'general.edit_foreign_graph_tuning',
            'general.edit_foreign_reports',
            'general.edit_foreign_sla_configuration',
            'general.edit_graph_collection',
            'general.edit_graph_tuning',
            'general.edit_sla_configuration',
            'general.force_custom_graph',
            'general.publish_forecast_graph',
            'general.force_graph_collection',
            'general.force_graph_tuning',
            'general.publish_graph_collection',
            'general.publish_to_foreign_groups_graph_collection',
            'general.publish_graph_tuning',
            'general.publish_to_foreign_groups_graph_tuning',
            'general.publish_reports',
            'general.publish_reports_to_foreign_groups',
            'general.publish_sla_configuration',
            'general.publish_to_foreign_groups_sla_configuration',
            'general.publish_stored_report',
            'general.publish_to_foreign_groups_forecast_graph',
            'general.see_user_custom_graph',
            'general.see_user_forecast_graph',
            'general.see_user_graph_collection',
            'general.see_user_graph_tuning',
            'general.see_user_reports',
            'general.see_user_sla_configuration',
            'general.see_user_stored_report',
            'general.reporting',
            'general.schedule_reports',
            'general.schedule_reports_all',
            'general.force_forecast_graph',
            'general.force_reports',
            'general.force_sla_configuration',
            'general.instant_reports',
            'general.publish_custom_graph',
            'general.publish_to_foreign_groups_custom_graph',
            'icons_and_actions.deployment_status',
            'icons_and_actions.ntop_host',
        ]

    if cmk_version.is_managed_edition():
        expected_permissions += [
            "wato.customer_management",
            "view.customers",
            "view.customer_hosts",
            "view.customer_hosts_up",
            "view.customer_hosts_down",
            "view.customer_hosts_pend",
            "view.customer_hosts_unreach",
            "sidesnap.customers",
        ]

    assert sorted(expected_permissions) == sorted(permission_registry.keys())

    for perm in permission_registry.values():
        assert isinstance(perm.description, (str, LazyString))
        assert isinstance(perm.title, (str, LazyString))
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

    permission = permissions.permission_registry["bla.blub"]
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

    for permission_name in ["Z", "z", "A", "b", "a", "1", "g"]:
        perms.register(
            Permission(
                section=Sec1,
                name=permission_name,
                title=permission_name.title(),
                description="bla",
                defaults=["admin"],
            ))

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
    monkeypatch.setattr(cmk.utils.paths, "local_web_dir", tmp_path / "local")

    return theme_path, local_theme_path


@pytest.fixture()
def my_theme(theme_dirs):
    theme_path = theme_dirs[0]
    my_dir = theme_path / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"})))
    return my_dir


def test_theme_choices_empty(theme_dirs):
    assert config.theme_choices() == []


def test_theme_choices_normal(my_theme):
    assert config.theme_choices() == [("my_theme", u"Määh Theme :-)")]


def test_theme_choices_local_theme(theme_dirs, my_theme):
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_improved_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Bettr Theme :-D"})))

    assert config.theme_choices() == sorted([
        ("my_theme", u"Määh Theme :-)"),
        ("my_improved_theme", u"Määh Bettr Theme :-D"),
    ])


def test_theme_choices_override(theme_dirs, my_theme):
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w",
                                 encoding="utf-8").write(str(json.dumps({"title": "Fixed theme"})))

    assert config.theme_choices() == sorted([
        ("my_theme", u"Fixed theme"),
    ])


def test_theme_broken_meta(my_theme):
    (my_theme / "theme.json").open(mode="w",
                                   encoding="utf-8").write(str("{\"titlewrong\": xyz\"bla\"}"))

    assert config.theme_choices() == sorted([
        ("my_theme", u"my_theme"),
    ])


def test_html_set_theme(my_theme, register_builtin_html):
    html.set_theme("")
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


@pytest.mark.parametrize(
    "user, alias, email, role_ids, baserole_id",
    [
        (
            config.LoggedInNobody(),
            "Unauthenticated user",
            "nobody",
            [],
            "guest",  # TODO: Why is this guest "guest"?
        ),
        (
            config.LoggedInSuperUser(),
            "Superuser for unauthenticated pages",
            "admin",
            ["admin"],
            "admin",
        ),
    ])
def test_unauthenticated_users(user, alias, email, role_ids, baserole_id):
    assert user.id is None
    assert user.alias == alias
    assert user.email == email
    assert user.confdir is None

    assert user.role_ids == role_ids
    assert user.get_attribute('roles') == role_ids
    assert user.baserole_id == baserole_id

    assert user.get_attribute('baz', 'default') == 'default'
    assert user.get_attribute('foo') is None

    assert user.customer_id is None
    assert user.contact_groups == []
    assert user.stars == set()
    assert user.is_site_disabled('any_site') is False

    assert user.load_file('any_file', 'default') == 'default'
    assert user.file_modified('any_file') == 0

    with pytest.raises(TypeError):
        user.save_stars()
    with pytest.raises(TypeError):
        user.save_site_config()


@pytest.mark.parametrize('user', [
    config.LoggedInNobody(),
    config.LoggedInSuperUser(),
])
def test_unauthenticated_users_language(mocker, user):
    mocker.patch.object(config, 'default_language', 'esperanto')
    assert user.language == 'esperanto'

    user.language = 'sindarin'
    assert user.language == 'sindarin'

    user.reset_language()
    assert user.language == 'esperanto'


@pytest.mark.parametrize('user', [
    config.LoggedInNobody(),
    config.LoggedInSuperUser(),
])
def test_unauthenticated_users_authorized_sites(mocker, user):
    assert user.authorized_sites({
        'site1': {},
    }) == {
        'site1': {},
    }

    mocker.patch.object(config, 'allsites', lambda: {'site1': {}, 'site2': {}})
    assert user.authorized_sites() == {'site1': {}, 'site2': {}}


@pytest.mark.parametrize('user', [
    config.LoggedInNobody(),
    config.LoggedInSuperUser(),
])
def test_unauthenticated_users_authorized_login_sites(mocker, user):
    mocker.patch.object(config, 'get_login_slave_sites', lambda: ['slave_site'])
    mocker.patch.object(config, 'allsites', lambda: {
        'master_site': {},
        'slave_site': {},
    })
    assert user.authorized_login_sites() == {'slave_site': {}}


def test_logged_in_nobody_permissions(mocker):
    user = config.LoggedInNobody()

    mocker.patch.object(config, 'roles', {})
    mocker.patch.object(permissions, 'permission_registry')

    assert user.may('any_permission') is False
    with pytest.raises(MKAuthException):
        user.need_permission('any_permission')


def test_logged_in_super_user_permissions(mocker):
    user = config.LoggedInSuperUser()

    mocker.patch.object(
        config,
        'roles',
        {
            'admin': {
                'permissions': {
                    'eat_other_peoples_cake': True
                }
            },
        },
    )
    mocker.patch.object(permissions, 'permission_registry')

    assert user.may('eat_other_peoples_cake') is True
    assert user.may('drink_other_peoples_milk') is False
    user.need_permission('eat_other_peoples_cake')
    with pytest.raises(MKAuthException):
        user.need_permission('drink_other_peoples_milk')


MONITORING_USER_CACHED_PROFILE = {
    'alias': u'Test user',
    'authorized_sites': ['heute', 'heute_slave_1'],
    'contactgroups': ['all'],
    'disable_notifications': {},
    'email': u'test_user@tribe29.com',
    'fallback_contact': False,
    'force_authuser': False,
    'locked': False,
    'language': 'de',
    'pager': '',
    'roles': ['user'],
    'start_url': None,
    'ui_theme': 'modern-dark',
}

MONITORING_USER_SITECONFIG = {
    'heute_slave_1': {
        'disabled': False
    },
    'heute_slave_2': {
        'disabled': True
    }
}

MONITORING_USER_BUTTONCOUNTS = {
    'cb_host': 1.9024999999999999,
    'cb_hoststatus': 1.8073749999999997,
}

MONITORING_USER_FAVORITES = ['heute;CPU load']


@pytest.fixture(name="monitoring_user")
def fixture_monitoring_user(tmp_path, mocker):
    """Returns a "Normal monitoring user" object."""
    config_dir = tmp_path / 'config_dir'
    user_dir = config_dir / 'test'
    user_dir.mkdir(parents=True)
    user_dir.joinpath('cached_profile.mk').write_text(str(MONITORING_USER_CACHED_PROFILE))
    # SITE STATUS snapin settings:
    user_dir.joinpath('siteconfig.mk').write_text(str(MONITORING_USER_SITECONFIG))
    # Ordering of the buttons:
    user_dir.joinpath('buttoncounts.mk').write_text(str(MONITORING_USER_BUTTONCOUNTS))
    # Favorites set in the commands menu:
    user_dir.joinpath('favorites.mk').write_text(str(MONITORING_USER_FAVORITES))

    mocker.patch.object(config, 'config_dir', str(config_dir))
    mocker.patch.object(config, 'roles_of_user', lambda user_id: ['user'])

    assert config.builtin_role_ids == ['user', 'admin', 'guest']
    assert 'test' not in config.admin_users

    return config.LoggedInUser('test')


def test_monitoring_user(monitoring_user):
    assert monitoring_user.id == 'test'
    assert monitoring_user.alias == 'Test user'
    assert monitoring_user.email == 'test_user@tribe29.com'
    assert monitoring_user.confdir.endswith('/config_dir/test')

    assert monitoring_user.role_ids == ['user']
    assert monitoring_user.get_attribute('roles') == ['user']
    assert monitoring_user.baserole_id == 'user'

    assert monitoring_user.get_attribute('ui_theme') == 'modern-dark'

    assert monitoring_user.language == 'de'
    assert monitoring_user.customer_id is None
    assert monitoring_user.contact_groups == ['all']

    assert monitoring_user.stars == set(MONITORING_USER_FAVORITES)
    monitoring_user.stars.add('heute;Memory')
    assert monitoring_user.stars == {'heute;CPU load', 'heute;Memory'}
    monitoring_user.save_stars()
    assert set(monitoring_user.load_file('favorites', [])) == monitoring_user.stars

    assert monitoring_user.is_site_disabled('heute_slave_1') is False
    assert monitoring_user.is_site_disabled('heute_slave_2') is True

    assert monitoring_user.load_file('siteconfig', None) == MONITORING_USER_SITECONFIG
    assert monitoring_user.file_modified('siteconfig') > 0
    assert monitoring_user.file_modified('unknown_file') == 0

    monitoring_user.disable_site('heute_slave_1')
    monitoring_user.enable_site('heute_slave_2')
    assert monitoring_user.is_site_disabled('heute_slave_1') is True
    assert monitoring_user.is_site_disabled('heute_slave_2') is False

    assert monitoring_user.show_help is False
    monitoring_user.show_help = True
    assert monitoring_user.show_help is True

    assert monitoring_user.acknowledged_notifications == 0
    timestamp = 1578479929
    monitoring_user.acknowledged_notifications = timestamp
    assert monitoring_user.acknowledged_notifications == timestamp


def test_monitoring_user_read_broken_file(monitoring_user, tmp_path):
    with Path(monitoring_user.confdir, "asd.mk").open("w") as f:
        f.write("%#%#%")

    assert monitoring_user.load_file("asd", deflt="xyz") == "xyz"


def test_monitoring_user_permissions(mocker, monitoring_user):
    mocker.patch.object(
        config,
        'roles',
        {
            'user': {
                'permissions': {
                    'action.star': False,
                    'general.edit_views': True,
                }
            },
        },
    )
    mocker.patch.object(permissions, 'permission_registry')

    assert monitoring_user.may('action.star') is False
    assert monitoring_user.may('general.edit_views') is True
    assert monitoring_user.may('unknown_permission') is False

    with pytest.raises(MKAuthException):
        monitoring_user.need_permission('action.start')
    monitoring_user.need_permission('general.edit_views')
    with pytest.raises(MKAuthException):
        monitoring_user.need_permission('unknown_permission')


@pytest.mark.parametrize("varname", [
    "custom_checks",
    "datasource_programs",
    "agent_config:mrpe",
    "agent_config:agent_paths",
    "agent_config:runas",
    "agent_config:only_from",
])
def test_ruleset_permissions_with_commandline_access(monitoring_user, varname):
    assert may_edit_ruleset(varname) is False


def test_is_ntop_available():
    is_ntop_available = config.is_ntop_available()

    if cmk_version.is_raw_edition():
        assert not is_ntop_available
    if not cmk_version.is_raw_edition():
        assert is_ntop_available


@pytest.mark.parametrize("ntop_connection, custom_user, answer, reason", [
    (
        {
            'is_activated': False
        },
        "",
        False,
        "ntopng integration is not activated under global settings.",
    ),
    (
        {
            'is_activated': True,
            'use_custom_attribute_as_ntop_username': False
        },
        "",
        True,
        "",
    ),
    (
        {
            'is_activated': True,
            'use_custom_attribute_as_ntop_username': 'ntop_alias'
        },
        "",
        False,
        ("The ntopng username should be derived from \'ntopng Username\' "
         "under the current's user settings (identity) but this is not "
         "set for the current user."),
    ),
    (
        {
            'is_activated': True,
            'use_custom_attribute_as_ntop_username': 'ntop_alias'
        },
        "a_ntop_user",
        True,
        "",
    ),
])
def test_is_ntop_configured_and_reason(
    mocker,
    ntop_connection,
    custom_user,
    answer,
    reason,
):
    if cmk_version.is_raw_edition():
        assert not config.is_ntop_configured()
        assert config.get_ntop_misconfiguration_reason(
        ) == "ntopng integration is only available in CEE"
    if not cmk_version.is_raw_edition():
        mocker.patch.object(
            config,
            'ntop_connection',
            ntop_connection,
        )
        if custom_user:
            config.user._set_attribute("ntop_alias", custom_user)
        assert config.is_ntop_configured() == answer
        assert config.get_ntop_misconfiguration_reason() == reason
