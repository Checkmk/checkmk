#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
from typing import Any, Dict

import pytest

import cmk.utils.version as cmk_version

import cmk.gui.plugins.visuals.filters
import cmk.gui.plugins.visuals.utils as utils
import cmk.gui.views
import cmk.gui.visuals as visuals
from cmk.gui.http import request


def test_get_filter():
    f = visuals.get_filter("hostregex")
    assert isinstance(f, utils.Filter)


def test_get_not_existing_filter():
    with pytest.raises(KeyError):
        visuals.get_filter("dingelig")


# TODO: The Next two are really poor tests. Put something better
def test_filters_allowed_for_info():
    allowed = dict(visuals.filters_allowed_for_info("host"))
    assert isinstance(allowed["host"], cmk.gui.plugins.visuals.filters.AjaxDropdownFilter)
    assert "service" not in allowed


def test_filters_allowed_for_infos():
    allowed = visuals.filters_allowed_for_infos(["host", "service"])
    assert isinstance(allowed["host"], cmk.gui.plugins.visuals.filters.AjaxDropdownFilter)
    assert isinstance(allowed["service"], cmk.gui.plugins.visuals.filters.AjaxDropdownFilter)


def _expected_visual_types():
    expected_visual_types = {
    'dashboards': {
        'add_visual_handler': 'popup_add_dashlet',
        'ident_attr': 'name',
        'multicontext_links': False,
        'plural_title': u'dashboards',
        'show_url': 'dashboard.py',
        'title': u'dashboard',
    },
    'views': {
        'add_visual_handler': None,
        'ident_attr': 'view_name',
        'multicontext_links': False,
        'plural_title': u'views',
        'show_url': 'view.py',
        'title': u'view',
    },
    }

    if not cmk_version.is_raw_edition():
        expected_visual_types.update({
        'reports': {
        'add_visual_handler': 'popup_add_element',
        'ident_attr': 'name',
        'multicontext_links': True,
        'plural_title': u'reports',
        'show_url': 'report.py',
        'title': u'report',
        },
        })

    return expected_visual_types


def test_registered_visual_types():
    assert sorted(utils.visual_type_registry.keys()) == sorted(_expected_visual_types().keys())


def test_registered_visual_type_attributes():
    for ident, plugin_class in utils.visual_type_registry.items():
        plugin = plugin_class()
        spec = _expected_visual_types()[ident]

        # TODO: Add tests for the results of these functions
        #assert plugin.add_visual_handler == spec["add_visual_handler"]
        assert plugin.ident_attr == spec["ident_attr"]
        assert plugin.multicontext_links == spec["multicontext_links"]
        assert plugin.plural_title == spec["plural_title"]
        assert plugin.show_url == spec["show_url"]
        assert plugin.title == spec["title"]


expected_filters: Dict[str, Dict[str, Any]] = {
    'address_families': {
        'comment': None,
        'filter_class': 'FilterAddressFamilies',
        'htmlvars': ['address_families'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 103,
        'title': u'Host address families'
    },
    'address_family': {
        'comment': None,
        'filter_class': 'FilterAddressFamily',
        'htmlvars': ['address_family'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 103,
        'title': u'Host address family (Primary)'
    },
    'aggr_assumed_state': {
        'column': 'aggr_assumed_state',
        'comment': None,
        'filter_class': 'BIStatusFilter',
        'htmlvars': ['bias-1', 'bias0', 'bias1', 'bias2', 'bias3', 'biasn'],
        'info': 'aggr',
        'link_columns': [],
        'sort_index': 152,
        'title': 'Assumed  State'
    },
    'aggr_effective_state': {
        'column': 'aggr_effective_state',
        'comment': None,
        'filter_class': 'BIStatusFilter',
        'htmlvars': ['bies-1', 'bies0', 'bies1', 'bies2', 'bies3'],
        'info': 'aggr',
        'link_columns': [],
        'sort_index': 151,
        'title': 'Effective  State'
    },
    'aggr_group': {
        'column': 'aggr_group',
        'comment': None,
        'filter_class': 'FilterAggrGroup',
        'htmlvars': ['aggr_group'],
        'info': 'aggr_group',
        'link_columns': ['aggr_group'],
        'sort_index': 90,
        'title': u'Aggregation group'
    },
    'aggr_group_tree': {
        'column': 'aggr_group_tree',
        'comment': None,
        'filter_class': 'FilterAggrGroupTree',
        'htmlvars': ['aggr_group_tree'],
        'info': 'aggr_group',
        'link_columns': ['aggr_group_tree'],
        'sort_index': 91,
        'title': u'Aggregation group tree'
    },
    'aggr_hosts': {
        'comment': u'Filter for all aggregations that base on status information of that host. Exact match (no regular expression)',
        'filter_class': 'FilterAggrHosts',
        'htmlvars': ['aggr_host_site', 'aggr_host_host'],
        'info': 'aggr',
        'link_columns': [],
        'sort_index': 130,
        'title': u'Affected hosts contain'
    },
    'aggr_name': {
        'column': 'aggr_name',
        'comment': None,
        'filter_class': 'BITextFilter',
        'htmlvars': ['aggr_name'],
        'info': 'aggr',
        'link_columns': ['aggr_name'],
        'sort_index': 120,
        'title': u'Aggregation name (exact match)'
    },
    'aggr_name_regex': {
        'column': 'aggr_name',
        'comment': None,
        'filter_class': 'BITextFilter',
        'htmlvars': ['aggr_name_regex'],
        'info': 'aggr',
        'link_columns': ['aggr_name'],
        'sort_index': 120,
        'title': u'Aggregation name'
    },
    'aggr_output': {
        'column': 'aggr_output',
        'comment': None,
        'filter_class': 'BITextFilter',
        'htmlvars': ['aggr_output'],
        'info': 'aggr',
        'link_columns': ['aggr_output'],
        'sort_index': 121,
        'title': u'Aggregation output'
    },
    'aggr_service': {
        'comment': u'Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)',
        'filter_class': 'FilterAggrService',
        'htmlvars': ['aggr_service_site', 'aggr_service_host', 'aggr_service_service'],
        'info': 'aggr',
        'link_columns': [],
        'sort_index': 131,
        'title': u'Affected by service'
    },
    'aggr_service_used': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterAggrServiceUsed',
        'htmlvars': ['is_aggr_service_used'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 300,
        'title': u'Used in BI aggregate'
    },
    'aggr_state': {
        'column': 'aggr_state',
        'comment': None,
        'filter_class': 'BIStatusFilter',
        'htmlvars': ['birs-1', 'birs0', 'birs1', 'birs2', 'birs3'],
        'info': 'aggr',
        'link_columns': [],
        'sort_index': 150,
        'title': ' State'
    },
    'check_command': {
        'comment': None,
        'filter_class': 'FilterQueryDropdown',
        'htmlvars': ['check_command'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 210,
        'title': u'Service check command'
    },
    'comment_author': {
        'column': 'comment_author',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['comment_author', 'neg_comment_author'],
        'info': 'comment',
        'link_columns': ['comment_author'],
        'sort_index': 259,
        'title': u'Author comment'
    },
    'comment_comment': {
        'column': 'comment_comment',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['comment_comment', 'neg_comment_comment'],
        'info': 'comment',
        'link_columns': ['comment_comment'],
        'sort_index': 258,
        'title': u'Comment'
    },
    'comment_entry_time': {
        'column': 'comment_entry_time',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'comment_entry_time_from', 'comment_entry_time_from_range', 'comment_entry_time_until',
            'comment_entry_time_until_range'
        ],
        'info': 'comment',
        'link_columns': ['comment_entry_time'],
        'sort_index': 253,
        'title': u'Time of comment'
    },
    'deployment_has_agent': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTristateFilter',
        'htmlvars': ['is_deployment_has_agent'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 502,
        'title': u'Host has a baked agent'
    },
    'deployment_has_downloaded': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTristateFilter',
        'htmlvars': ['is_deployment_has_downloaded'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 503,
        'title': u'Host has downloaded an agent'
    },
    'deployment_host_has_error': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTristateFilter',
        'htmlvars': ['is_deployment_host_has_error'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 504,
        'title': u'Host has deployment error'
    },
    'deployment_is_registered': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTristateFilter',
        'htmlvars': ['is_deployment_is_registered'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 500,
        'title': u'Host has registered for deployment'
    },
    'deployment_last_contact': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTimestampFilter',
        'htmlvars': [
            'deployment_last_contact_from', 'deployment_last_contact_from_range',
            'deployment_last_contact_until', 'deployment_last_contact_until_range'
        ],
        'info': 'host',
        'link_columns': [None],
        'sort_index': 505,
        'title': u'Last contact of agent updater'
    },
    'deployment_last_download': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTimestampFilter',
        'htmlvars': [
            'deployment_last_download_from', 'deployment_last_download_from_range',
            'deployment_last_download_until', 'deployment_last_download_until_range'
        ],
        'info': 'host',
        'link_columns': [None],
        'sort_index': 506,
        'title': u'Last download of agent updater'
    },
    'deployment_last_registered': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTimestampFilter',
        'htmlvars': [
            'deployment_last_registered_from', 'deployment_last_registered_from_range',
            'deployment_last_registered_until', 'deployment_last_registered_until_range'
        ],
        'info': 'host',
        'link_columns': [None],
        'sort_index': 504,
        'title': u'Time of registration'
    },
    'deployment_need_update': {
        'column': None,
        'comment': None,
        'filter_class': 'DeploymentTristateFilter',
        'htmlvars': ['is_deployment_need_update'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 501,
        'title': u'Host needs agent update'
    },
    'discovery_state': {
        'comment': None,
        'filter_class': 'FilterDiscoveryState',
        'htmlvars': [
            'discovery_state_ignored', 'discovery_state_vanished', 'discovery_state_unmonitored'
        ],
        'info': 'discovery_state',
        'link_columns': [],
        'sort_index': 601,
        'title': u'Discovery state'
    },
    'downtime_author': {
        'column': 'downtime_author',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['downtime_author'],
        'info': 'downtime',
        'link_columns': ['downtime_author'],
        'sort_index': 256,
        'title': u'Downtime author'
    },
    'downtime_comment': {
        'column': 'downtime_comment',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['downtime_comment'],
        'info': 'downtime',
        'link_columns': ['downtime_comment'],
        'sort_index': 254,
        'title': u'Downtime comment'
    },
    'downtime_entry_time': {
        'column': 'downtime_entry_time',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'downtime_entry_time_from', 'downtime_entry_time_from_range',
            'downtime_entry_time_until', 'downtime_entry_time_until_range'
        ],
        'info': 'downtime',
        'link_columns': ['downtime_entry_time'],
        'sort_index': 253,
        'title': u'Time when downtime was created'
    },
    'downtime_id': {
        'column': 'downtime_id',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['downtime_id'],
        'info': 'downtime',
        'link_columns': ['downtime_id'],
        'sort_index': 301,
        'title': u'Downtime ID'
    },
    'downtime_start_time': {
        'column': 'downtime_start_time',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'downtime_start_time_from', 'downtime_start_time_from_range',
            'downtime_start_time_until', 'downtime_start_time_until_range'
        ],
        'info': 'downtime',
        'link_columns': ['downtime_start_time'],
        'sort_index': 255,
        'title': u'Start of downtime'
    },
    'event_application': {
        'column': 'event_application',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_application'],
        'info': 'event',
        'link_columns': ['event_application'],
        'sort_index': 201,
        'title': u'Application / Syslog-Tag'
    },
    'event_comment': {
        'column': 'event_comment',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_comment'],
        'info': 'event',
        'link_columns': ['event_comment'],
        'sort_index': 201,
        'title': u'Comment to the event'
    },
    'event_contact': {
        'column': 'event_contact',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_contact'],
        'info': 'event',
        'link_columns': ['event_contact'],
        'sort_index': 201,
        'title': u'Contact Person'
    },
    'event_count': {
        'comment': None,
        'filter_class': 'FilterEventCount',
        'htmlvars': ['event_count_from', 'event_count_to'],
        'info': 'event',
        'link_columns': ['event_count'],
        'sort_index': 205,
        'title': u'Message count'
    },
    'event_facility': {
        'comment': None,
        'filter_class': 'FilterEventFacility',
        'htmlvars': ['event_facility'],
        'info': 'event',
        'link_columns': ['event_facility'],
        'sort_index': 210,
        'title': u'Syslog Facility'
    },
    'event_first': {
        'column': 'event_first',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'event_first_from', 'event_first_from_range', 'event_first_until',
            'event_first_until_range'
        ],
        'info': 'event',
        'link_columns': ['event_first'],
        'sort_index': 220,
        'title': u'First occurrence of event'
    },
    'event_host': {
        'column': 'event_host',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_host'],
        'info': 'event',
        'link_columns': ['event_host'],
        'sort_index': 201,
        'title': u'Hostname of event, exact match'
    },
    'event_host_in_downtime': {
        'column': 'event_host_in_downtime',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_event_host_in_downtime'],
        'info': 'event',
        'link_columns': [],
        'sort_index': 223,
        'title': u'Host in downtime during event creation'
    },
    'event_host_regex': {
        'column': 'event_host',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_host'],
        'info': 'event',
        'link_columns': ['event_host'],
        'sort_index': 201,
        'title': u'Hostname of original event'
    },
    'event_id': {
        'column': 'event_id',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_id'],
        'info': 'event',
        'link_columns': ['event_id'],
        'sort_index': 200,
        'title': u'Event ID'
    },
    'event_ipaddress': {
        'column': 'event_ipaddress',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_ipaddress'],
        'info': 'event',
        'link_columns': ['event_ipaddress'],
        'sort_index': 201,
        'title': u'Original IP Address of event'
    },
    'event_last': {
        'column': 'event_last',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'event_last_from', 'event_last_from_range', 'event_last_until', 'event_last_until_range'
        ],
        'info': 'event',
        'link_columns': ['event_last'],
        'sort_index': 221,
        'title': u'Last occurrance of event'
    },
    'event_owner': {
        'column': 'event_owner',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_owner'],
        'info': 'event',
        'link_columns': ['event_owner'],
        'sort_index': 201,
        'title': u'Owner of event'
    },
    'event_phase': {
        'comment': None,
        'filter_class': 'EventFilterState',
        'htmlvars': [
            'event_phase_ack', 'event_phase_counting', 'event_phase_open', 'event_phase_delayed',
            'event_phase_closed'
        ],
        'info': 'event',
        'link_columns': ['event_phase'],
        'sort_index': 207,
        'title': u'Phase'
    },
    'event_priority': {
        'comment': None,
        'filter_class': 'EventFilterState',
        'htmlvars': [
            'event_priority_0', 'event_priority_1', 'event_priority_2', 'event_priority_3',
            'event_priority_4', 'event_priority_5', 'event_priority_6', 'event_priority_7'
        ],
        'info': 'event',
        'link_columns': ['event_priority'],
        'sort_index': 209,
        'title': u'Syslog Priority'
    },
    'event_rule_id': {
        'column': 'event_rule_id',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_rule_id'],
        'info': 'event',
        'link_columns': ['event_rule_id'],
        'sort_index': 200,
        'title': u'ID of rule'
    },
    'event_sl': {
        'comment': None,
        'filter_class': 'EventFilterDropdown',
        'htmlvars': ['event_sl'],
        'info': 'event',
        'link_columns': ['event_sl'],
        'sort_index': 211,
        'title': u'Service Level at least'
    },
    'event_sl_max': {
        'comment': None,
        'filter_class': 'EventFilterDropdown',
        'htmlvars': ['event_sl_max'],
        'info': 'event',
        'link_columns': ['event_sl'],
        'sort_index': 211,
        'title': u'Service Level at most'
    },
    'event_state': {
        'comment': None,
        'filter_class': 'EventFilterState',
        'htmlvars': ['event_state_0', 'event_state_1', 'event_state_2', 'event_state_3'],
        'info': 'event',
        'link_columns': ['event_state'],
        'sort_index': 206,
        'title': u'State classification'
    },
    'event_text': {
        'column': 'event_text',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['event_text'],
        'info': 'event',
        'link_columns': ['event_text'],
        'sort_index': 201,
        'title': u'Message/Text of event'
    },
    'has_inv': {
        'column': 'host_inventory',
        'comment': None,
        'filter_class': 'FilterHasInv',
        'htmlvars': ['is_has_inv'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 801,
        'title': u'Has Inventory Data'
    },
    'has_performance_data': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterOption',
        'htmlvars': ['is_has_performance_data'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 251,
        'title': u'Has performance data'
    },
    'history_line': {
        'column': 'history_line',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['history_line'],
        'info': 'history',
        'link_columns': ['history_line'],
        'sort_index': 222,
        'title': u'Line number in history logfile'
    },
    'history_time': {
        'column': 'history_time',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'history_time_from', 'history_time_from_range', 'history_time_until',
            'history_time_until_range'
        ],
        'info': 'history',
        'link_columns': ['history_time'],
        'sort_index': 222,
        'title': u'Time of entry in event history'
    },
    'history_what': {
        'comment': None,
        'filter_class': 'EventFilterState',
        'htmlvars': [
            'history_what_AUTODELETE', 'history_what_COUNTREACHED', 'history_what_UPDATE',
            'history_what_CANCELLED', 'history_what_NEW', 'history_what_EMAIL',
            'history_what_DELAYOVER', 'history_what_COUNTFAILED', 'history_what_ARCHIVED',
            'history_what_NOCOUNT', 'history_what_SCRIPT', 'history_what_ORPHANED',
            'history_what_CHANGESTATE', 'history_what_EXPIRED', 'history_what_DELETE'
        ],
        'info': 'history',
        'link_columns': ['history_what'],
        'sort_index': 225,
        'title': u'History action type'
    },
    'history_who': {
        'column': 'history_who',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['history_who'],
        'info': 'history',
        'link_columns': ['history_who'],
        'sort_index': 221,
        'title': u'User that performed action'
    },
    'host': {
        'column': 'host_name',
        'comment': u'Exact match, used for linking',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['host', 'neg_host'],
        'info': 'host',
        'link_columns': ['host_name'],
        'sort_index': 101,
        'title': u'Hostname (exact match)'
    },
    'host_acknowledged': {
        'column': 'host_acknowledged',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_acknowledged'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 131,
        'title': u'Host problem has been acknowledged'
    },
    'host_active_checks_enabled': {
        'column': 'host_active_checks_enabled',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_active_checks_enabled'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 132,
        'title': u'Host active checks enabled'
    },
    'host_address': {
        'comment': None,
        'filter_class': 'IPAddressFilter',
        'htmlvars': ['host_address', 'host_address_prefix'],
        'info': 'host',
        'link_columns': ['host_address'],
        'sort_index': 102,
        'title': u'Host address (Primary)'
    },
    'host_auxtags': {
        'comment': None,
        'filter_class': 'FilterHostAuxTags',
        'htmlvars': [
            'host_auxtags_0', 'host_auxtags_0_neg', 'host_auxtags_1', 'host_auxtags_1_neg',
            'host_auxtags_2', 'host_auxtags_2_neg'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 302,
        'title': u'Host Auxiliary Tags'
    },
    'host_check_command': {
        'comment': None,
        'filter_class': 'FilterQueryDropdown',
        'htmlvars': ['host_check_command'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 110,
        'title': u'Host check command'
    },
    'host_ctc': {
        'column': 'host_contacts',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['host_ctc'],
        'info': 'host',
        'link_columns': ['host_contacts'],
        'sort_index': 107,
        'title': u'Host Contact'
    },
    'host_ctc_regex': {
        'column': 'host_contacts',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['host_ctc_regex'],
        'info': 'host',
        'link_columns': ['host_contacts'],
        'sort_index': 107,
        'title': u'Host Contact (Regex)'
    },
    'host_favorites': {
        'column': 'host_favorite',
        'comment': None,
        'filter_class': 'FilterStarred',
        'htmlvars': ['is_host_favorites'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 501,
        'title': 'Favorite Hosts'
    },
    'host_in_notification_period': {
        'column': 'host_in_notification_period',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_in_notification_period'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 130,
        'title': u'Host in notification period'
    },
    'host_in_service_period': {
        'column': 'host_in_service_period',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_in_service_period'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 130,
        'title': u'Host in service period'
    },
    'host_ipv4_address': {
        'comment': None,
        'filter_class': 'IPAddressFilter',
        'htmlvars': ['host_ipv4_address', 'host_ipv4_address_prefix'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 102,
        'title': u'Host address (IPv4)'
    },
    'host_ipv6_address': {
        'comment': None,
        'filter_class': 'IPAddressFilter',
        'htmlvars': ['host_ipv6_address', 'host_ipv6_address_prefix'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 102,
        'title': u'Host address (IPv6)'
    },
    'host_last_check': {
        'column': 'host_last_check',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'host_last_check_from', 'host_last_check_from_range', 'host_last_check_until',
            'host_last_check_until_range'
        ],
        'info': 'host',
        'link_columns': ['host_last_check'],
        'sort_index': 251,
        'title': u'Last host check'
    },
    'host_last_state_change': {
        'column': 'host_last_state_change',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'host_last_state_change_from', 'host_last_state_change_from_range',
            'host_last_state_change_until', 'host_last_state_change_until_range'
        ],
        'info': 'host',
        'link_columns': ['host_last_state_change'],
        'sort_index': 250,
        'title': u'Last host state change'
    },
    'host_notif_number': {
        'column': 'current_notification_number',
        'comment': None,
        'filter_class': 'FilterNumberRange',
        'htmlvars': ['host_notif_number_from', 'host_notif_number_until'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 232,
        'title': u'Current Host Notification Number'
    },
    'host_notifications_enabled': {
        'column': 'host_notifications_enabled',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_notifications_enabled'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 133,
        'title': u'Host notifications enabled'
    },
    'host_num_services': {
        'column': 'num_services',
        'comment': None,
        'filter_class': 'FilterNumberRange',
        'htmlvars': ['host_num_services_from', 'host_num_services_until'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 234,
        'title': u'Number of Services of the Host'
    },
    'host_scheduled_downtime_depth': {
        'column': 'host_scheduled_downtime_depth',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_host_scheduled_downtime_depth'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 132,
        'title': u'Host in downtime'
    },
    'host_staleness': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterOption',
        'htmlvars': ['is_host_staleness'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 232,
        'title': u'Host is stale'
    },
    'host_state_type': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterTristate',
        'htmlvars': ['is_host_state_type'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 116,
        'title': u'Host state type'
    },
    'host_tags': {
        'comment': None,
        'filter_class': 'FilterHostTags',
        'htmlvars': [
            'host_tag_0_grp', 'host_tag_0_op', 'host_tag_0_val', 'host_tag_1_grp', 'host_tag_1_op',
            'host_tag_1_val', 'host_tag_2_grp', 'host_tag_2_op', 'host_tag_2_val'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 302,
        'title': u'Host Tags'
    },
    'hostalias': {
        'column': 'host_alias',
        'comment': u'Search field allowing regular expressions and partial matches',
        'filter_class': 'FilterUnicode',
        'htmlvars': ['hostalias', 'neg_hostalias'],
        'info': 'host',
        'link_columns': ['host_alias'],
        'sort_index': 102,
        'title': u'Hostalias'
    },
    'hostgroup': {
        'comment': u'Selection of the host group',
        'filter_class': 'FilterGroupSelection',
        'htmlvars': ['hostgroup'],
        'info': 'hostgroup',
        'link_columns': [],
        'sort_index': 104,
        'title': u'Host Group'
    },
    'hostgroupnameregex': {
        'column': 'hostgroup_name',
        'comment': u'Search field allowing regular expressions and partial matches on the names of hostgroups',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['hostgroup_regex'],
        'info': 'hostgroup',
        'link_columns': ['hostgroup_name'],
        'sort_index': 101,
        'title': u'Hostgroup (Regex)'
    },
    'hostgroups': {
        'comment': u'Selection of multiple host groups',
        'filter_class': 'FilterMultigroup',
        'htmlvars': ['hostgroups', 'neg_hostgroups'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 105,
        'title': u'Several Host Groups'
    },
    'hostgroupvisibility': {
        'comment': u'You can enable this checkbox to show empty hostgroups',
        'filter_class': 'FilterHostgroupVisibility',
        'htmlvars': ['hostgroupshowempty'],
        'info': 'hostgroup',
        'link_columns': [],
        'sort_index': 102,
        'title': u'Empty Hostgroup Visibilitiy'
    },
    'hostsgroups_having_problems': {
        'comment': u'Selection of multiple host groups',
        'filter_class': 'FilterHostgroupProblems',
        'htmlvars': [
            'hostgroups_having_hosts_down',
            'hostgroups_having_hosts_pending',
            'hostgroups_having_hosts_unreach',
            'hostgroups_having_services__warn',
            'hostgroups_having_services_crit',
            'hostgroups_having_services_pending',
            'hostgroups_having_services_unknown'
            ],
        'info': 'hostgroup',
        'link_columns': [],
        'sort_index': 103,
        'title': u'Hostgroups having certain problems'
    },
    'hostnameoralias': {
        'column': ['host_alias', 'host_name'],
        'comment': u'Search field allowing regular expressions and partial matches',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['hostnameoralias'],
        'info': 'host',
        'link_columns': ['host_alias', 'host_name'],
        'sort_index': 102,
        'title': u'Hostname or Alias'
    },
    'hostregex': {
        'column': 'host_name',
        'comment': u'Search field allowing regular expressions and partial matches',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['host_regex', 'neg_host_regex'],
        'info': 'host',
        'link_columns': ['host_name'],
        'sort_index': 100,
        'title': u'Hostname'
    },
    'hosts_having_service_problems': {
        'comment': None,
        'filter_class': 'FilterHostsHavingServiceProblems',
        'htmlvars': [
            'hosts_having_services_warn', 'hosts_having_services_crit',
            'hosts_having_services_pending', 'hosts_having_services_unknown'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 120,
        'title': u'Hosts having certain service problems'
    },
    'hoststate': {
        'comment': None,
        'filter_class': 'FilterHostState',
        'htmlvars': ['hoststate_filled', 'hst0', 'hst1', 'hst2', 'hstp'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 115,
        'title': u'Host states'
    },
    'hst_service_level': {
        'comment': None,
        'filter_class': 'FilterECServiceLevelRange',
        'htmlvars': ['hst_service_level_lower', 'hst_service_level_upper'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 310,
        'title': u'Host service level'
    },
    'in_downtime': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterOption',
        'htmlvars': ['is_in_downtime'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 232,
        'title': u'Host/service in downtime'
    },
    'inv_hardware_cpu_arch': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_cpu_arch'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 CPU Architecture'
    },
    'inv_hardware_cpu_bus_speed': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_bus_speed_from', 'inv_hardware_cpu_bus_speed_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Bus Speed'
    },
    'inv_hardware_cpu_cache_size': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_cache_size_from', 'inv_hardware_cpu_cache_size_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Cache Size'
    },
    'inv_hardware_cpu_cores': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_cores_from', 'inv_hardware_cpu_cores_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Total Number of Cores'
    },
    'inv_hardware_cpu_cores_per_cpu': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_cores_per_cpu_from', 'inv_hardware_cpu_cores_per_cpu_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Cores per CPU'
    },
    'inv_hardware_cpu_cpus': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_cpus_from', 'inv_hardware_cpu_cpus_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Number of physical CPUs'
    },
    'inv_hardware_cpu_entitlement': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_cpu_entitlement'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 CPU Entitlement'
    },
    'inv_hardware_cpu_logical_cpus': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_logical_cpus_from', 'inv_hardware_cpu_logical_cpus_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Number of logical CPUs'
    },
    'inv_hardware_cpu_max_speed': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_max_speed_from', 'inv_hardware_cpu_max_speed_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Maximum Speed'
    },
    'inv_hardware_cpu_model': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_cpu_model'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Model'
    },
    'inv_hardware_cpu_sharing_mode': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_cpu_sharing_mode'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 CPU sharing mode'
    },
    'inv_hardware_cpu_smt_threads': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_smt_threads_from', 'inv_hardware_cpu_smt_threads_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Simultaneous multithreading'
    },
    'inv_hardware_cpu_threads': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_threads_from', 'inv_hardware_cpu_threads_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Total Number of Hyperthreads'
    },
    'inv_hardware_cpu_threads_per_cpu': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': [
            'inv_hardware_cpu_threads_per_cpu_from', 'inv_hardware_cpu_threads_per_cpu_to'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Hyperthreads per CPU'
    },
    'inv_hardware_cpu_voltage': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_cpu_voltage_from', 'inv_hardware_cpu_voltage_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Processor \u27a4 Voltage'
    },
    'inv_hardware_memory_total_ram_usable': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': [
            'inv_hardware_memory_total_ram_usable_from', 'inv_hardware_memory_total_ram_usable_to'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Memory (RAM) \u27a4 Total usable RAM'
    },
    'inv_hardware_memory_total_swap': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_hardware_memory_total_swap_from', 'inv_hardware_memory_total_swap_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Memory (RAM) \u27a4 Total swap space'
    },
    'inv_hardware_memory_total_vmalloc': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': [
            'inv_hardware_memory_total_vmalloc_from', 'inv_hardware_memory_total_vmalloc_to'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Memory (RAM) \u27a4 Virtual addresses for mapping'
    },
    'inv_hardware_storage_controller_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_storage_controller_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Controller \u27a4 Version'
    },
    'inv_hardware_system_expresscode': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_expresscode'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'System \u27a4 Express Servicecode'
    },
    'inv_hardware_system_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_manufacturer'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'System \u27a4 Manufacturer'
    },
    'inv_hardware_system_model': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_model'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'System \u27a4 Model Name'
    },
    'inv_hardware_system_model_name': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_model_name'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u"System \u27a4 Model Name - LEGACY, don't use"
    },
    'inv_hardware_system_product': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_product'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'System \u27a4 Product'
    },
    'inv_hardware_system_serial': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_serial'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'System \u27a4 Serial Number'
    },
    'inv_hardware_system_serial_number': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_hardware_system_serial_number'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u"System \u27a4 Serial Number - LEGACY, don't use"
    },
    'inv_networking_available_ethernet_ports': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': [
            'inv_networking_available_ethernet_ports_from',
            'inv_networking_available_ethernet_ports_to'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Networking \u27a4 Ports available'
    },
    'inv_networking_total_ethernet_ports': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': [
            'inv_networking_total_ethernet_ports_from', 'inv_networking_total_ethernet_ports_to'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Networking \u27a4 Ports'
    },
    'inv_networking_hostname': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_networking_hostname_from', 'inv_networking_hostname_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Networking \u27a4 Hostname'
    },
    'inv_networking_total_interfaces': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_networking_total_interfaces_from', 'inv_networking_total_interfaces_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Networking \u27a4 Interfaces'
    },
    'inv_networking_wlan': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_networking_wlan'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Networking \u27a4 WLAN'
    },
    'inv_networking_wlan_controller': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_networking_wlan_controller'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'WLAN \u27a4 Controller'
    },
    'inv_software_applications_check_mk_cluster_is_cluster': {
        'column': 'inv_software_applications_check_mk_cluster_is_cluster',
        'comment': None,
        'filter_class': 'FilterInvBool',
        'htmlvars': ['is_inv_software_applications_check_mk_cluster_is_cluster'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Cluster \u27a4 Cluster host'
    },
    'inv_software_applications_citrix_controller_controller_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_citrix_controller_controller_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Controller \u27a4 Controller Version'
    },
    'inv_software_applications_citrix_vm_agent_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_citrix_vm_agent_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Virtual Machine \u27a4 Agent Version'
    },
    'inv_software_applications_citrix_vm_catalog': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_citrix_vm_catalog'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Virtual Machine \u27a4 Catalog'
    },
    'inv_software_applications_citrix_vm_desktop_group_name': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_citrix_vm_desktop_group_name'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Virtual Machine \u27a4 Desktop Group Name'
    },
    'inv_software_applications_docker_container_node_name': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_container_node_name'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Container \u27a4 Node name'
    },
    'inv_software_applications_docker_num_containers_paused': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_num_containers_paused'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker \u27a4 # Containers paused'
    },
    'inv_software_applications_docker_num_containers_running': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_num_containers_running'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker \u27a4 # Containers running'
    },
    'inv_software_applications_docker_num_containers_stopped': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_num_containers_stopped'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker \u27a4 # Containers stopped'
    },
    'inv_software_applications_docker_num_containers_total': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_num_containers_total'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker \u27a4 # Containers'
    },
    'inv_software_applications_docker_num_images': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_applications_docker_num_images'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker \u27a4 # Images'
    },
    'inv_software_bios_date': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_software_bios_date_from', 'inv_software_bios_date_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'BIOS \u27a4 Date'
    },
    'inv_software_bios_vendor': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_bios_vendor'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'BIOS \u27a4 Vendor'
    },
    'inv_software_bios_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_bios_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'BIOS \u27a4 Version'
    },
    'inv_software_configuration_snmp_info_contact': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_configuration_snmp_info_contact'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'SNMP Information \u27a4 Contact'
    },
    'inv_software_configuration_snmp_info_location': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_configuration_snmp_info_location'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'SNMP Information \u27a4 Location'
    },
    'inv_software_configuration_snmp_info_name': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_configuration_snmp_info_name'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'SNMP Information \u27a4 System name'
    },
    'inv_software_firmware_platform_level': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_firmware_platform_level'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Firmware \u27a4 Platform Firmware level'
    },
    'inv_software_firmware_vendor': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_firmware_vendor'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Firmware \u27a4 Vendor'
    },
    'inv_software_firmware_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_firmware_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Firmware \u27a4 Version'
    },
    'inv_software_os_arch': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_arch'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Kernel Architecture'
    },
    'inv_software_os_install_date': {
        'comment': None,
        'filter_class': 'FilterInvFloat',
        'htmlvars': ['inv_software_os_install_date_from', 'inv_software_os_install_date_to'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Install Date'
    },
    'inv_software_os_kernel_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_kernel_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Kernel Version'
    },
    'inv_software_os_name': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_name'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Name'
    },
    'inv_software_os_service_pack': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_service_pack'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Latest Service Pack'
    },
    'inv_software_os_type': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_type'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Type'
    },
    'inv_software_os_vendor': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_vendor'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Vendor'
    },
    'inv_software_os_version': {
        'comment': None,
        'filter_class': 'FilterInvText',
        'htmlvars': ['inv_software_os_version'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Operating System \u27a4 Version'
    },
    'invbackplane_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_description'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Description'
    },
    'invbackplane_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_index'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Index'
    },
    'invbackplane_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_location'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Location'
    },
    'invbackplane_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_manufacturer'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Manufacturer'
    },
    'invbackplane_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_model'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Model Name'
    },
    'invbackplane_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_name'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Name'
    },
    'invbackplane_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_serial'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Serial Number'
    },
    'invbackplane_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invbackplane_software'],
        'info': 'invbackplane',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Backplane: Software'
    },
    'invchassis_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_description'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Description'
    },
    'invchassis_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_index'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Index'
    },
    'invchassis_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_location'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Location'
    },
    'invchassis_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_manufacturer'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Manufacturer'
    },
    'invchassis_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_model'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Model Name'
    },
    'invchassis_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_name'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Name'
    },
    'invchassis_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_serial'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Serial Number'
    },
    'invchassis_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invchassis_software'],
        'info': 'invchassis',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Chassis: Software'
    },
    'invcontainer_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_description'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Description'
    },
    'invcontainer_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_index'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Index'
    },
    'invcontainer_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_location'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Location'
    },
    'invcontainer_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_manufacturer'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Manufacturer'
    },
    'invcontainer_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_model'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Model Name'
    },
    'invcontainer_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_name'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Name'
    },
    'invcontainer_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_serial'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Serial Number'
    },
    'invcontainer_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invcontainer_software'],
        'info': 'invcontainer',
        'link_columns': [],
        'sort_index': 800,
        'title': u'HW container: Software'
    },
    'invdockercontainers_creation': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_creation'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Creation'
    },
    'invdockercontainers_id': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_id'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: ID'
    },
    'invdockercontainers_labels': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invdockercontainers_labels_from', 'invdockercontainers_labels_to'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Labels'
    },
    'invdockercontainers_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_name'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Name'
    },
    'invdockercontainers_repository': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_repository'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Repository'
    },
    'invdockercontainers_status': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_status'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Status'
    },
    'invdockercontainers_tag': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockercontainers_tag'],
        'info': 'invdockercontainers',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker containers: Tag'
    },
    'invdockerimages_amount_containers': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_amount_containers'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: # Containers'
    },
    'invdockerimages_creation': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_creation'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: Creation'
    },
    'invdockerimages_id': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_id'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: ID'
    },
    'invdockerimages_labels': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invdockerimages_labels_from', 'invdockerimages_labels_to'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: Labels'
    },
    'invdockerimages_repository': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_repository'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: Repository'
    },
    'invdockerimages_size': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_size'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: Size'
    },
    'invdockerimages_tag': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invdockerimages_tag'],
        'info': 'invdockerimages',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Docker images: Tag'
    },
    'invfan_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_description'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Description'
    },
    'invfan_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_index'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Index'
    },
    'invfan_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_location'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Location'
    },
    'invfan_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_manufacturer'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Manufacturer'
    },
    'invfan_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_model'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Model Name'
    },
    'invfan_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_name'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Name'
    },
    'invfan_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_serial'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Serial Number'
    },
    'invfan_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invfan_software'],
        'info': 'invfan',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Fan: Software'
    },
    'invinterface_admin_status': {
        'comment': None,
        'filter_class': 'FilterInvtableAdminStatus',
        'htmlvars': ['invinterface_admin_status'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Administrative Status'
    },
    'invinterface_alias': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invinterface_alias'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Alias'
    },
    'invinterface_available': {
        'comment': None,
        'filter_class': 'FilterInvtableAvailable',
        'htmlvars': ['invinterface_available'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Port Usage'
    },
    'invinterface_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invinterface_description'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Description'
    },
    'invinterface_index': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invinterface_index_from', 'invinterface_index_to'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Index'
    },
    'invinterface_last_change': {
        'comment': None,
        'filter_class': 'FilterInvtableTimestampAsAge',
        'htmlvars': ['invinterface_last_change_from', 'invinterface_last_change_to'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Last Change'
    },
    'invinterface_oper_status': {
        'comment': None,
        'filter_class': 'FilterInvtableOperStatus',
        'htmlvars': [
            'invinterface_oper_status_1', 'invinterface_oper_status_2',
            'invinterface_oper_status_3', 'invinterface_oper_status_4',
            'invinterface_oper_status_5', 'invinterface_oper_status_6',
            'invinterface_oper_status_7', 'invinterface_oper_status_8', 'invinterface_oper_status_9'
        ],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Operational Status'
    },
    'invinterface_phys_address': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invinterface_phys_address'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Physical Address (MAC)'
    },
    'invinterface_port_type': {
        'comment': None,
        'filter_class': 'FilterInvtableInterfaceType',
        'htmlvars': ['invinterface_port_type'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Type'
    },
    'invinterface_speed': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invinterface_speed_from', 'invinterface_speed_to'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: Speed'
    },
    'invinterface_vlans': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invinterface_vlans'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: VLANs'
    },
    'invinterface_vlantype': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invinterface_vlantype'],
        'info': 'invinterface',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Network interface: VLAN type'
    },
    'invmodule_bootloader': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_bootloader'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Bootloader'
    },
    'invmodule_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_description'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Description'
    },
    'invmodule_firmware': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_firmware'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Firmware'
    },
    'invmodule_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_index'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Index'
    },
    'invmodule_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_location'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Location'
    },
    'invmodule_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_manufacturer'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Manufacturer'
    },
    'invmodule_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_model'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Model Name'
    },
    'invmodule_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_name'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Name'
    },
    'invmodule_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_serial'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Serial Number'
    },
    'invmodule_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_software'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Software'
    },
    'invmodule_type': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invmodule_type'],
        'info': 'invmodule',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Module: Type'
    },
    'invoradataguardstats_db_unique': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoradataguardstats_db_unique'],
        'info': 'invoradataguardstats',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle dataguard statistic: Name'
    },
    'invoradataguardstats_role': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoradataguardstats_role'],
        'info': 'invoradataguardstats',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle dataguard statistic: Role'
    },
    'invoradataguardstats_sid': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoradataguardstats_sid'],
        'info': 'invoradataguardstats',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle dataguard statistic: SID'
    },
    'invoradataguardstats_switchover': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoradataguardstats_switchover'],
        'info': 'invoradataguardstats',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle dataguard statistic: Switchover'
    },
    'invorainstance_db_creation_time': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorainstance_db_creation_time_from', 'invorainstance_db_creation_time_to'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Creation time'
    },
    'invorainstance_db_uptime': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorainstance_db_uptime_from', 'invorainstance_db_uptime_to'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Uptime'
    },
    'invorainstance_logins': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorainstance_logins'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Logins'
    },
    'invorainstance_logmode': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorainstance_logmode'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Log mode'
    },
    'invorainstance_openmode': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorainstance_openmode'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Open mode'
    },
    'invorainstance_sid': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorainstance_sid'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: SID'
    },
    'invorainstance_version': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorainstance_version'],
        'info': 'invorainstance',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle instance: Version'
    },
    'invorarecoveryarea_flashback': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorarecoveryarea_flashback'],
        'info': 'invorarecoveryarea',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle recovery area: Flashback'
    },
    'invorarecoveryarea_sid': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorarecoveryarea_sid'],
        'info': 'invorarecoveryarea',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle recovery area: SID'
    },
    'invorasga_buf_cache_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_buf_cache_size_from', 'invorasga_buf_cache_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Buffer cache size'
    },
    'invorasga_data_trans_cache_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_data_trans_cache_size_from', 'invorasga_data_trans_cache_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Data transfer cache size'
    },
    'invorasga_fixed_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_fixed_size_from', 'invorasga_fixed_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Fixed size'
    },
    'invorasga_free_mem_avail': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_free_mem_avail_from', 'invorasga_free_mem_avail_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Free SGA memory available'
    },
    'invorasga_granule_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_granule_size_from', 'invorasga_granule_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Granule size'
    },
    'invorasga_in_mem_area_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_in_mem_area_size_from', 'invorasga_in_mem_area_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: In-memory area'
    },
    'invorasga_java_pool_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_java_pool_size_from', 'invorasga_java_pool_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Java pool size'
    },
    'invorasga_large_pool_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_large_pool_size_from', 'invorasga_large_pool_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Large pool size'
    },
    'invorasga_max_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_max_size_from', 'invorasga_max_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Maximum size'
    },
    'invorasga_redo_buffer': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_redo_buffer_from', 'invorasga_redo_buffer_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Redo buffers'
    },
    'invorasga_shared_io_pool_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_shared_io_pool_size_from', 'invorasga_shared_io_pool_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Shared pool size'
    },
    'invorasga_shared_pool_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_shared_pool_size_from', 'invorasga_shared_pool_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Shared pool size'
    },
    'invorasga_sid': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invorasga_sid'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: SID'
    },
    'invorasga_start_oh_shared_pool': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_start_oh_shared_pool_from', 'invorasga_start_oh_shared_pool_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Startup overhead in shared pool'
    },
    'invorasga_streams_pool_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invorasga_streams_pool_size_from', 'invorasga_streams_pool_size_to'],
        'info': 'invorasga',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle performance: Streams pool size'
    },
    'invoratablespace_autoextensible': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_autoextensible'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Autoextensible'
    },
    'invoratablespace_current_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invoratablespace_current_size_from', 'invoratablespace_current_size_to'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Current size'
    },
    'invoratablespace_free_space': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invoratablespace_free_space_from', 'invoratablespace_free_space_to'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Free space'
    },
    'invoratablespace_increment_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invoratablespace_increment_size_from', 'invoratablespace_increment_size_to'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Increment size'
    },
    'invoratablespace_max_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invoratablespace_max_size_from', 'invoratablespace_max_size_to'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Max. size'
    },
    'invoratablespace_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_name'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Name'
    },
    'invoratablespace_num_increments': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_num_increments'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Number of increments'
    },
    'invoratablespace_sid': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_sid'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: SID'
    },
    'invoratablespace_type': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_type'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Type'
    },
    'invoratablespace_used_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invoratablespace_used_size_from', 'invoratablespace_used_size_to'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Used size'
    },
    'invoratablespace_version': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invoratablespace_version'],
        'info': 'invoratablespace',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Oracle tablespace: Version'
    },
    'invother_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_description'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Description'
    },
    'invother_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_index'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Index'
    },
    'invother_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_location'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Location'
    },
    'invother_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_manufacturer'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Manufacturer'
    },
    'invother_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_model'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Model Name'
    },
    'invother_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_name'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Name'
    },
    'invother_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_serial'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Serial Number'
    },
    'invother_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invother_software'],
        'info': 'invother',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Other entity: Software'
    },
    'invpsu_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_description'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Description'
    },
    'invpsu_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_index'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Index'
    },
    'invpsu_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_location'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Location'
    },
    'invpsu_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_manufacturer'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Manufacturer'
    },
    'invpsu_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_model'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Model Name'
    },
    'invpsu_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_name'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Name'
    },
    'invpsu_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_serial'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Serial Number'
    },
    'invpsu_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invpsu_software'],
        'info': 'invpsu',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Power supply: Software'
    },
    'invsensor_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_description'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Description'
    },
    'invsensor_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_index'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Index'
    },
    'invsensor_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_location'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Location'
    },
    'invsensor_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_manufacturer'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Manufacturer'
    },
    'invsensor_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_model'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Model Name'
    },
    'invsensor_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_name'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Name'
    },
    'invsensor_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_serial'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Serial Number'
    },
    'invsensor_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invsensor_software'],
        'info': 'invsensor',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Sensor: Software'
    },
    'invstack_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_description'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Description'
    },
    'invstack_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_index'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Index'
    },
    'invstack_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_location'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Location'
    },
    'invstack_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_manufacturer'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Manufacturer'
    },
    'invstack_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_model'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Model Name'
    },
    'invstack_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_name'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Name'
    },
    'invstack_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_serial'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Serial Number'
    },
    'invstack_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invstack_software'],
        'info': 'invstack',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Stack: Software'
    },
    'invswpac': {
        'comment': None,
        'filter_class': 'FilterInvHasSoftwarePackage',
        'htmlvars': [
            'invswpac_host_name', 'invswpac_host_version_from', 'invswpac_host_version_to',
            'invswpac_host_negate'
        ],
        'info': 'host',
        'link_columns': [],
        'sort_index': 801,
        'title': u'Host has software package'
    },
    'invswpac_arch': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_arch'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Architecture'
    },
    'invswpac_install_date': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invswpac_install_date_from', 'invswpac_install_date_to'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Install Date'
    },
    'invswpac_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_name'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Name'
    },
    'invswpac_package_type': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_package_type'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Type'
    },
    'invswpac_package_version': {
        'comment': None,
        'filter_class': 'FilterInvtableVersion',
        'htmlvars': ['invswpac_package_version_from', 'invswpac_package_version_to'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Package Version'
    },
    'invswpac_path': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_path'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Path'
    },
    'invswpac_size': {
        'comment': None,
        'filter_class': 'FilterInvtableIDRange',
        'htmlvars': ['invswpac_size_from', 'invswpac_size_to'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Size'
    },
    'invswpac_summary': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_summary'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Description'
    },
    'invswpac_vendor': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invswpac_vendor'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Publisher'
    },
    'invswpac_version': {
        'comment': None,
        'filter_class': 'FilterInvtableVersion',
        'htmlvars': ['invswpac_version_from', 'invswpac_version_to'],
        'info': 'invswpac',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Software package: Version'
    },
    'invunknown_description': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_description'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Description'
    },
    'invunknown_index': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_index'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Index'
    },
    'invunknown_location': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_location'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Location'
    },
    'invunknown_manufacturer': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_manufacturer'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Manufacturer'
    },
    'invunknown_model': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_model'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Model Name'
    },
    'invunknown_name': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_name'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Name'
    },
    'invunknown_serial': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_serial'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Serial Number'
    },
    'invunknown_software': {
        'comment': None,
        'filter_class': 'FilterInvtableText',
        'htmlvars': ['invunknown_software'],
        'info': 'invunknown',
        'link_columns': [],
        'sort_index': 800,
        'title': u'Unknown entity: Software'
    },
    'log_class': {
        'comment': None,
        'filter_class': 'FilterLogClass',
        'htmlvars': [
            'logclass_filled', 'logclass0', 'logclass1', 'logclass2', 'logclass3', 'logclass4',
            'logclass5', 'logclass6', 'logclass8'
        ],
        'info': 'log',
        'link_columns': [],
        'sort_index': 255,
        'title': u'Logentry class'
    },
    'log_command_name_regex': {
        'column': 'log_command_name',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['log_command_name_regex', 'neg_log_command_name_regex'],
        'info': 'log',
        'link_columns': ['log_command_name'],
        'sort_index': 262,
        'title': u'Log: command'
    },
    'log_contact_name': {
        'column': 'log_contact_name',
        'comment': u'Exact match, used for linking',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['log_contact_name'],
        'info': 'log',
        'link_columns': ['log_contact_name'],
        'sort_index': 260,
        'title': u'Log: contact name (exact match)'
    },
    'log_contact_name_regex': {
        'column': 'log_contact_name',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['log_contact_name_regex', 'neg_log_contact_name_regex'],
        'info': 'log',
        'link_columns': ['log_contact_name'],
        'sort_index': 261,
        'title': u'Log: contact name'
    },
    'log_notification_phase': {
        'column': 'log_command_name',
        'comment': None,
        'filter_class': 'FilterLogNotificationPhase',
        'htmlvars': ['is_log_notification_phase'],
        'info': 'log',
        'link_columns': [],
        'sort_index': 271,
        'title': u'Notification phase'
    },
    'log_plugin_output': {
        'column': 'log_plugin_output',
        'comment': None,
        'filter_class': 'FilterUnicode',
        'htmlvars': ['log_plugin_output'],
        'info': 'log',
        'link_columns': ['log_plugin_output'],
        'sort_index': 202,
        'title': u'Log: plugin output'
    },
    'log_state': {
        'comment': None,
        'filter_class': 'FilterLogState',
        'htmlvars': [
            'logst_h0', 'logst_h1', 'logst_h2', 'logst_s0', 'logst_s1', 'logst_s2', 'logst_s3'
        ],
        'info': 'log',
        'link_columns': [],
        'sort_index': 270,
        'title': u'Type of alerts of hosts and services'
    },
    'log_state_type': {
        'column': 'log_state_type',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['log_state_type'],
        'info': 'log',
        'link_columns': ['log_state_type'],
        'sort_index': 204,
        'title': u'Log: state type'
    },
    'log_type': {
        'column': 'log_type',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['log_type'],
        'info': 'log',
        'link_columns': ['log_type'],
        'sort_index': 203,
        'title': u'Log: message type'
    },
    'logtime': {
        'column': 'log_time',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': ['logtime_from', 'logtime_from_range', 'logtime_until', 'logtime_until_range'],
        'info': 'log',
        'link_columns': ['log_time'],
        'sort_index': 252,
        'title': u'Time of log entry'
    },
    'optevent_effective_contactgroup': {
        'comment': None,
        'filter_class': 'FilterOptEventEffectiveContactgroup',
        'htmlvars': ['optevent_effective_contact_group', 'neg_optevent_effective_contact_group'],
        'info': 'event',
        'link_columns': [
            'event_contact_groups', 'event_contact_groups_precedence', 'host_contact_groups'
        ],
        'sort_index': 212,
        'title': u'Contact group (effective)'
    },
    'opthost_contactgroup': {
        'comment': u'Optional selection of host contact group',
        'filter_class': 'FilterGroupCombo',
        'htmlvars': ['opthost_contact_group', 'neg_opthost_contact_group'],
        'info': 'host',
        'link_columns': ['host_contactgroup_name'],
        'sort_index': 106,
        'title': u'Host Contact Group'
    },
    'opthostgroup': {
        'comment': u'Optional selection of host group',
        'filter_class': 'FilterGroupCombo',
        'htmlvars': ['opthost_group', 'neg_opthost_group'],
        'info': 'host',
        'link_columns': ['hostgroup_name'],
        'sort_index': 104,
        'title': u'Host is in Group'
    },
    'optservice_contactgroup': {
        'comment': u'Optional selection of service contact group',
        'filter_class': 'FilterGroupCombo',
        'htmlvars': ['optservice_contact_group', 'neg_optservice_contact_group'],
        'info': 'service',
        'link_columns': ['service_contactgroup_name'],
        'sort_index': 206,
        'title': u'Service Contact Group'
    },
    'optservicegroup': {
        'comment': u'Optional selection of service group',
        'filter_class': 'FilterGroupCombo',
        'htmlvars': ['optservice_group', 'neg_optservice_group'],
        'info': 'service',
        'link_columns': ['servicegroup_name'],
        'sort_index': 204,
        'title': u'Service is in Group'
    },
    'output': {
        'column': 'service_plugin_output',
        'comment': None,
        'filter_class': 'FilterUnicode',
        'htmlvars': ['service_output', 'neg_service_output'],
        'info': 'service',
        'link_columns': ['service_plugin_output'],
        'sort_index': 202,
        'title': u'Status detail'
    },
    'service': {
        'column': 'service_description',
        'comment': u'Exact match, used for linking',
        'filter_class': 'FilterUnicode',
        'htmlvars': ['service'],
        'info': 'service',
        'link_columns': ['service_description'],
        'sort_index': 201,
        'title': u'Service (exact match)'
    },
    'service_acknowledged': {
        'column': 'service_acknowledged',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_acknowledged'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 230,
        'title': u'Problem acknowledged'
    },
    'service_active_checks_enabled': {
        'column': 'service_active_checks_enabled',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_active_checks_enabled'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 233,
        'title': u'Active checks enabled'
    },
    'service_ctc': {
        'column': 'service_contacts',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['service_ctc'],
        'info': 'service',
        'link_columns': ['service_contacts'],
        'sort_index': 207,
        'title': u'Service Contact'
    },
    'service_ctc_regex': {
        'column': 'service_contacts',
        'comment': None,
        'filter_class': 'InputTextFilter',
        'htmlvars': ['service_ctc_regex'],
        'info': 'service',
        'link_columns': ['service_contacts'],
        'sort_index': 207,
        'title': u'Service Contact (Regex)'
    },
    'service_display_name': {
        'column': 'service_display_name',
        'comment': u'Alternative display name of the service, regex match',
        'filter_class': 'FilterUnicode',
        'htmlvars': ['service_display_name'],
        'info': 'service',
        'link_columns': ['service_display_name'],
        'sort_index': 202,
        'title': u'Service alternative display name'
    },
    'service_favorites': {
        'column': 'service_favorite',
        'comment': None,
        'filter_class': 'FilterStarred',
        'htmlvars': ['is_service_favorites'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 501,
        'title': 'Favorite Services'
    },
    'service_in_notification_period': {
        'column': 'service_in_notification_period',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_in_notification_period'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 231,
        'title': u'Service in notification period'
    },
    'service_in_service_period': {
        'column': 'service_in_service_period',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_in_service_period'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 231,
        'title': u'Service in service period'
    },
    'service_is_flapping': {
        'column': 'service_is_flapping',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_is_flapping'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 236,
        'title': u'Flapping'
    },
    'service_notifications_enabled': {
        'column': 'service_notifications_enabled',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_notifications_enabled'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 234,
        'title': u'Notifications enabled'
    },
    'service_process_performance_data': {
        'column': 'service_process_performance_data',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_process_performance_data'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 250,
        'title': u'Processes performance data'
    },
    'service_scheduled_downtime_depth': {
        'column': 'service_scheduled_downtime_depth',
        'comment': None,
        'filter_class': 'FilterNagiosFlag',
        'htmlvars': ['is_service_scheduled_downtime_depth'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 231,
        'title': u'Service in downtime'
    },
    'service_staleness': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterOption',
        'htmlvars': ['is_service_staleness'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 232,
        'title': u'Service is stale'
    },
    'service_state_type': {
        'column': None,
        'comment': None,
        'filter_class': 'FilterTristate',
        'htmlvars': ['is_service_state_type'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 217,
        'title': u'Service state type'
    },
    'servicegroup': {
        'comment': u'Selection of the service group',
        'filter_class': 'FilterGroupSelection',
        'htmlvars': ['servicegroup'],
        'info': 'servicegroup',
        'link_columns': [],
        'sort_index': 104,
        'title': u'Service Group'
    },
    'servicegroupname': {
        'column': 'servicegroup_name',
        'comment': u'Exact match, used for linking',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['servicegroup_name'],
        'info': 'servicegroup',
        'link_columns': ['servicegroup_name'],
        'sort_index': 101,
        'title': u'Servicegroup (enforced)'
    },
    'servicegroupnameregex': {
        'column': 'servicegroup_name',
        'comment': u'Search field allowing regular expression and partial matches',
        'filter_class': 'InputTextFilter',
        'htmlvars': ['servicegroup_regex', 'neg_servicegroup_regex'],
        'info': 'servicegroup',
        'link_columns': ['servicegroup_name'],
        'sort_index': 101,
        'title': u'Servicegroup (Regex)'
    },
    'servicegroups': {
        'comment': u'Selection of multiple service groups',
        'filter_class': 'FilterMultigroup',
        'htmlvars': ['servicegroups', 'neg_servicegroups'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 205,
        'title': u'Several Service Groups'
    },
    'serviceregex': {
        'column': 'service_description',
        'comment': u'Search field allowing regular expressions and partial matches',
        'filter_class': 'FilterUnicode',
        'htmlvars': ['service_regex', 'neg_service_regex'],
        'info': 'service',
        'link_columns': ['service_description'],
        'sort_index': 200,
        'title': u'Service'
    },
    'site': {
        'comment': u'Selection of site is enforced, use this filter for joining',
        'filter_class': 'FilterSite',
        'htmlvars': ['site'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 501,
        'title': u'Site (enforced)'
    },
    'siteopt': {
        'comment': u'Optional selection of a site',
        'filter_class': 'FilterSiteOpt',
        'htmlvars': ['site'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 500,
        'title': u'Site'
    },
    'svc_last_check': {
        'column': 'service_last_check',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'svc_last_check_from', 'svc_last_check_from_range', 'svc_last_check_until',
            'svc_last_check_until_range'
        ],
        'info': 'service',
        'link_columns': ['service_last_check'],
        'sort_index': 251,
        'title': u'Last service check'
    },
    'svc_last_state_change': {
        'column': 'service_last_state_change',
        'comment': None,
        'filter_class': 'FilterTime',
        'htmlvars': [
            'svc_last_state_change_from', 'svc_last_state_change_from_range',
            'svc_last_state_change_until', 'svc_last_state_change_until_range'
        ],
        'info': 'service',
        'link_columns': ['service_last_state_change'],
        'sort_index': 250,
        'title': u'Last service state change'
    },
    'svc_notif_number': {
        'column': 'current_notification_number',
        'comment': None,
        'filter_class': 'FilterNumberRange',
        'htmlvars': ['svc_notif_number_from', 'svc_notif_number_until'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 232,
        'title': u'Current Service Notification Number'
    },
    'svc_service_level': {
        'comment': None,
        'filter_class': 'FilterECServiceLevelRange',
        'htmlvars': ['svc_service_level_lower', 'svc_service_level_upper'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 310,
        'title': u'Service service level'
    },
    'svchardstate': {
        'comment': None,
        'filter_class': 'FilterServiceState',
        'htmlvars': ['hd_filled', 'hdst0', 'hdst1', 'hdst2', 'hdst3', 'hdstp'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 216,
        'title': u'Service hard states'
    },
    'svcstate': {
        'comment': None,
        'filter_class': 'FilterServiceState',
        'htmlvars': ['_filled', 'st0', 'st1', 'st2', 'st3', 'stp'],
        'info': 'service',
        'link_columns': [],
        'sort_index': 215,
        'title': u'Service states'
    },
    'wato_folder': {
        'comment': None,
        'filter_class': 'FilterWatoFolder',
        'htmlvars': ['wato_folder'],
        'info': 'host',
        'link_columns': [],
        'sort_index': 10,
        'title': u'Folder'
    },
}


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_filters():
    names = cmk.gui.plugins.visuals.utils.filter_registry.keys()
    assert sorted(expected_filters.keys()) == sorted(names)

    for filt in cmk.gui.plugins.visuals.utils.filter_registry.values():
        spec = expected_filters[filt.ident]

        assert filt.title == spec["title"]
        assert filt.description == spec["comment"]
        assert filt.sort_index == spec["sort_index"]
        assert filt.info == spec["info"]
        assert sorted(filt.link_columns) == sorted(spec["link_columns"])
        assert sorted(filt.htmlvars) == sorted(spec["htmlvars"])
        if "column" in spec:
            # FIXME: ugly getattr so that mypy doesn't complain about missing attribute column
            column = getattr(filt, "column")
            assert column == spec["column"]

        bases = [c.__name__ for c in filt.__class__.__bases__] + [filt.__class__.__name__]
        assert spec["filter_class"] in bases


expected_infos: Dict[str, Dict[str, Any]] = {
    'aggr': {
        'single_spec': [('aggr_name', 'TextInput')],
        'title': u'BI Aggregation',
        'title_plural': u'BI Aggregations'
    },
    'aggr_group': {
        'single_spec': [('aggr_group', 'TextInput')],
        'title': u'BI Aggregation Group',
        'title_plural': u'BI Aggregation Groups'
    },
    'command': {
        'single_spec': [('command_name', 'TextInput')],
        'title': u'Command',
        'title_plural': u'Commands'
    },
    'comment': {
        'single_spec': [('comment_id', 'Integer')],
        'title': u'Comment',
        'title_plural': u'Comments'
    },
    'contact': {
        'single_spec': [('log_contact_name', 'TextInput')],
        'title': u'Contact',
        'title_plural': u'Contacts'
    },
    'discovery': {
        'single_spec': None,
        'title': u'Discovery Output',
        'title_plural': u'Discovery Outputs'
    },
    'downtime': {
        'single_spec': [('downtime_id', 'Integer')],
        'title': u'Downtime',
        'title_plural': u'Downtimes'
    },
    'event': {
        'single_spec': [('event_id', 'Integer')],
        'title': u'Event Console Event',
        'title_plural': u'Event Console Events'
    },
    'history': {
        'single_spec': [('event_id', 'Integer'), ('history_line', 'Integer')],
        'title': u'Historic Event Console Event',
        'title_plural': u'Historic Event Console Events'
    },
    'host': {
        'multiple_site_filters': ['hostgroup'],
        'single_spec': [('host', 'TextInput')],
        'title': u'Host',
        'title_plural': u'Hosts'
    },
    'hostgroup': {
        'single_site': False,
        'single_spec': [('hostgroup', 'TextInput')],
        'title': u'Host Group',
        'title_plural': u'Host Groups'
    },
    'invbackplane': {
        'single_spec': None,
        'title': u'Backplane',
        'title_plural': u'Backplanes'
    },
    'invchassis': {
        'single_spec': None,
        'title': u'Chassis',
        'title_plural': u'Chassis'
    },
    'invcontainer': {
        'single_spec': None,
        'title': u'HW container',
        'title_plural': u'HW containers'
    },
    'invdockercontainers': {
        'single_spec': None,
        'title': u'Docker containers',
        'title_plural': u'Docker containers'
    },
    'invdockerimages': {
        'single_spec': None,
        'title': u'Docker images',
        'title_plural': u'Docker images'
    },
    'invfan': {
        'single_spec': None,
        'title': u'Fan',
        'title_plural': u'Fans'
    },
    'invhist': {
        'single_spec': None,
        'title': u'Inventory History',
        'title_plural': u'Inventory Historys'
    },
    'invinterface': {
        'single_spec': None,
        'title': u'Network interface',
        'title_plural': u'Network interfaces'
    },
    'invmodule': {
        'single_spec': None,
        'title': u'Module',
        'title_plural': u'Modules'
    },
    'invoradataguardstats': {
        'single_spec': None,
        'title': u'Oracle dataguard statistic',
        'title_plural': u'Oracle dataguard statistics'
    },
    'invorainstance': {
        'single_spec': None,
        'title': u'Oracle instance',
        'title_plural': u'Oracle instances'
    },
    'invorarecoveryarea': {
        'single_spec': None,
        'title': u'Oracle recovery area',
        'title_plural': u'Oracle recovery areas'
    },
    'invorasga': {
        'single_spec': None,
        'title': u'Oracle performance',
        'title_plural': u'Oracle performance'
    },
    'invoratablespace': {
        'single_spec': None,
        'title': u'Oracle tablespace',
        'title_plural': u'Oracle tablespaces'
    },
    'invother': {
        'single_spec': None,
        'title': u'Other entity',
        'title_plural': u'Other entities'
    },
    'invpsu': {
        'single_spec': None,
        'title': u'Power supply',
        'title_plural': u'Power supplies'
    },
    'invsensor': {
        'single_spec': None,
        'title': u'Sensor',
        'title_plural': u'Sensors'
    },
    'invstack': {
        'single_spec': None,
        'title': u'Stack',
        'title_plural': u'Stacks'
    },
    'invswpac': {
        'single_spec': None,
        'title': u'Software package',
        'title_plural': u'Software packages'
    },
    'invunknown': {
        'single_spec': None,
        'title': u'Unknown entity',
        'title_plural': u'Unknown entities'
    },
    'log': {
        'single_spec': None,
        'title': u'Log Entry',
        'title_plural': u'Log Entries'
    },
    'service': {
        'multiple_site_filters': ['servicegroup'],
        'single_spec': [('service', 'TextInput')],
        'title': u'Service',
        'title_plural': u'Services'
    },
    'servicegroup': {
        'single_site': False,
        'single_spec': [('servicegroup', 'TextInput')],
        'title': u'Service Group',
        'title_plural': u'Service Groups'
    },
}


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_infos():
    assert sorted(utils.visual_info_registry.keys()) == sorted(expected_infos.keys())


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_registered_info_attributes():
    for ident, cls in utils.visual_info_registry.items():
        info = cls()
        spec = expected_infos[ident]

        assert info.title == spec["title"]
        assert info.title_plural == spec["title_plural"]

        if spec["single_spec"] is None:
            assert info.single_spec is None
        else:
            assert [(e[0], e[1].__class__.__name__) for e in info.single_spec
                   ] == spec["single_spec"]

        assert info.multiple_site_filters == spec.get("multiple_site_filters", [])
        assert info.single_site == spec.get("single_site", True)


@pytest.mark.parametrize(
    "context,expected_vars",
    [
        # No single context, use multi filter
        ({"filter_name": {"filter_var": "eee"}}, [('filter_var', 'eee')]),
        # Single host context
        ({"host": {"host": "abc"}}, [("host", "abc")]),
        # Single host context, and other filters
        ({"host": {"host": "abc"}, "bla": {"blub": "ble"}},
         [('blub', 'ble'), ('host', 'abc')]),
        # Single host context, missing filter -> no failure
        ({}, []),
        # Single host + service context
        ({"host": {"host": "abc"}, "service": {"service": "äää"}},
         [("host", "abc"), ("service", u"äää")]),
    ])
def test_context_to_uri_vars(context, expected_vars):
    context_vars = visuals.context_to_uri_vars(context)
    assert sorted(context_vars) == sorted(expected_vars)


@pytest.mark.parametrize("infos,uri_vars,expected_context", [
    # No single context, no filter
    (["host"], [("abc", "dingeling")], {}),
    # Single host context
    (["host"], [("host", "aaa")], {"host": {"host": "aaa"}}),
    # Single host context with site hint
    # -> add site and siteopt (Why? Was like this in 1.6...)
    (["host"], [("host", "aaa"),("site", "abc")], {"host": {"host": "aaa"}, "site": {"site": "abc"},
        "siteopt": {"site": "abc"}}),
    # Single host context -> not set
    (["host"], [], {}),
    # Single host context -> empty set
    (["host"], [("host", "")], {}),
    # Single host context with non-ascii char
    (["host"], [("host", "äbc")], {"host": {"host": "äbc"}}),
    # Single host context, multiple services
    (["host", "service"], [("host", "aaa"), ("service_regex", "äbc")], {"host": {"host": "aaa"},
        'serviceregex': {'service_regex': 'äbc'}}),
    # multiple services
    (["service", "host"], [("host", "aaa"), ("service_regex", "äbc")], {
        'serviceregex': {'service_regex': 'äbc'}, 'host': {'host': 'aaa'},}),
    # multiple services, ignore filters of unrelated infos
    (["service"], [("host", "aaa"), ("service_regex", "äbc")], {
        'serviceregex': {'service_regex': 'äbc'},}),
])
def test_get_context_from_uri_vars(request_context, infos, uri_vars,
        expected_context):
    for key, val in uri_vars:
        request.set_var(key, val)

    context = visuals.get_context_from_uri_vars(infos)
    assert context == expected_context


@pytest.mark.parametrize("uri_vars,visual,expected_context", [
    # Single host context, set via URL, with some service filter, set via context
    ([("host", "aaa")], {"infos": ["host", "service"], "single_infos": ["host"], "context": {"service_regex":
        {"serviceregex": "abc"}},}, {"host": {"host": "aaa"}, "service_regex": {"serviceregex": "abc"},}),
    # Single host context, set via context and URL
    ([("host", "aaa")], {"infos": ["host", "service"], "single_infos": ["host"], "context": {"host":
        {"host": "from_context"},}}, {"host": {"host": "from_context"}}),
    # No single context with some host & service filter
    ([("host", "aaa")], {"infos": ["host", "service"], "single_infos": [], "context": {"service_regex":
        {"serviceregex": "abc"}},}, {"host": {"host": "aaa"}, "service_regex": {"serviceregex": "abc"},}),
    # No single context with some host filter from URL
    ([("host", "aaa")], {"infos": ["host", "service"], "single_infos": [], "context": {}},
        {"host": {"host": "aaa"},}),
])
def test_get_merged_context(request_context, uri_vars, visual, expected_context):
    for key, val in uri_vars:
        request.set_var(key, val)

    url_context = visuals.get_context_from_uri_vars(visual["infos"])
    context = visuals.get_merged_context(url_context, visual["context"])

    assert context == expected_context


def test_get_missing_single_infos_has_context():
    assert (
        visuals.get_missing_single_infos(single_infos=["host"], context={"host": {"host": "abc"}})
        == set()
    )


def test_get_missing_single_infos_missing_context():
    assert visuals.get_missing_single_infos(single_infos=["host"], context={}) == {"host"}


@pytest.mark.parametrize(
    "context, single_infos, expected_context",
    [
        pytest.param(
            {
                "discovery_state": {
                    "discovery_state_ignored": True,
                    "discovery_state_vanished": False,
                    "discovery_state_unmonitored": True,
                }
            },
            [],
            {
                "discovery_state": {
                    "discovery_state_ignored": "on",
                    "discovery_state_vanished": "",
                    "discovery_state_unmonitored": "on",
                }
            },
            id="1.6.0->2.1.0 CMK-6606",
        ),
        pytest.param(
            {"host": {"host": "heute"}},
            ["host"],
            {"host": {"host": "heute"}},
            id="-> 2.1.0 Idempotent on already transformed single_info",
        ),
        pytest.param(
            {"host": "heute", "event_id": 5},
            ["host", "history"],
            {"host": {"host": "heute"}, "event_id": {"event_id": "5"}},
            id="-> 2.1.0 No single_info, only FilterHTTPVariables VisualContext",
        ),
        pytest.param(
            {"site": "heute", "sites": "heute|morgen", "siteopt": "heute"},
            [],
            {
                "site": {"site": "heute"},
                "siteopt": {"site": "heute"},
                "sites": {"sites": "heute|morgen"},
            },
            id="-> 2.1.0 Site hint is not bound to single info",
        ),
        pytest.param(
            {
                "invinterface_last_change": {
                    "invinterface_last_change_from_days": "1",
                    "invinterface_last_change_to_days": "5",
                },
                "inv_hardware_cpu_bus_speed": {
                    "inv_hardware_cpu_bus_speed_from": "10",
                    "inv_hardware_cpu_bus_speed_to": "20",
                },
                "event_count": {"event_count_from": "1", "event_count_to": "123"},
                # Never existed with "to", just for the test
                "history_time": {
                    "history_time_from": "2001-02-03",
                    "history_time_from_range": "abs",
                    "history_time_to": "2001-02-05",
                    "history_time_to_range": "abs",
                },
                # Not range filter
                "another_filter": {
                    "another_filter_to": "2001-02-05",
                    "another_filter_to_range": "abs",
                },
            },
            [],
            {
                "invinterface_last_change": {
                    "invinterface_last_change_from_days": "1",
                    "invinterface_last_change_until_days": "5",
                },
                "inv_hardware_cpu_bus_speed": {
                    "inv_hardware_cpu_bus_speed_from": "10",
                    "inv_hardware_cpu_bus_speed_until": "20",
                },
                "event_count": {"event_count_from": "1", "event_count_until": "123"},
                "history_time": {
                    "history_time_from": "2001-02-03",
                    "history_time_from_range": "abs",
                    "history_time_until": "2001-02-05",
                    "history_time_until_range": "abs",
                },
                # Not range filter
                "another_filter": {
                    "another_filter_to": "2001-02-05",
                    "another_filter_to_range": "abs",
                },
            },
            id="-> 2.1.0 Range Filters have homogenous request vars",
        ),
    ],
)
def test_cleanup_contexts(context, single_infos, expected_context):
    assert visuals.cleanup_context_filters(context, single_infos) == expected_context
