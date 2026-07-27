#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared machinery for the per-edition config variable disk-data round-trip
tests, see tests/unit/cmk/gui/wato/pages/test_config_variable_form_data.py for
the community edition and tests/unit/cmk/gui/nonfree/*/wato/ for the others.

CASES covers the config variables of all editions in one flat table; the
config variable registry of the edition under test decides which entries
apply, see generate_config_variable_tests."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui import valuespec
from cmk.gui.exceptions import MKConfigError, MKUserError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs._utils import (
    migrate_form_spec_disk_value,
    parse_and_validate_frontend_data,
    validate_value_from_frontend,
)
from cmk.gui.form_specs.unstable.legacy_converter.transform import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.watolib.config_domain_name import (
    config_variable_registry,
    ConfigVariable,
    GlobalSettingsContext,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.internal.form_specs import SingleChoiceExtended
from cmk.rulesets.v1 import form_specs
from cmk.rulesets.v1.form_specs import FormSpec
from tests.testlib.fake_site import edition as edition_from_env
from tests.testlib.gui.common_fixtures import perform_load_plugins


def make_global_settings_context(edition: Edition) -> GlobalSettingsContext:
    return GlobalSettingsContext(
        target_site_id=SiteId("test"),
        edition_of_local_site=edition,
        site_neutral_log_dir=Path("/tmp"),
        site_neutral_var_dir=Path("/tmp"),
        configured_sites=SiteConfigurations({}),
        configured_graph_timeranges=[],
    )


def default_disk_value(config_variable: ConfigVariable, context: GlobalSettingsContext) -> object:
    value_model = config_variable.value_model(context)
    if isinstance(value_model, FormSpec):
        visitor = get_visitor(value_model, VisitorOptions(migrate_values=True, mask_values=False))
        return visitor.to_disk(DEFAULT_VALUE)
    return value_model.default_value()


def round_trip_disk_value(
    config_variable: ConfigVariable, context: GlobalSettingsContext, value: object
) -> object:
    """The load-and-save-again path of cmk-update-config, see
    _transform_global_config_value in cmk.update_config.plugins.actions.global_settings."""
    value_model = config_variable.value_model(context)
    if isinstance(value_model, FormSpec):
        return migrate_form_spec_disk_value(value_model, value)
    return value_model.transform_value(value)


def gui_save_round_trip_disk_value[T](form_spec: FormSpec[T], value: object) -> object:
    """The unedited GUI save path: the stored value is rendered to the frontend
    (serialize_data_for_frontend), reported as valid by the live validation
    (validate_value_from_frontend) and submitted back unchanged as JSON
    (parse_and_validate_frontend_data), see cmk.gui.form_specs._utils."""
    render_visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    _vue_spec, frontend_value = render_visitor.to_vue(RawDiskData(value))
    submitted = RawFrontendData(json.loads(json.dumps(frontend_value)))
    assert validate_value_from_frontend(form_spec, submitted) == []
    return parse_and_validate_frontend_data(form_spec, submitted)


def validate_disk_value(
    config_variable: ConfigVariable, context: GlobalSettingsContext, value: object
) -> None:
    value_model = config_variable.value_model(context)
    if isinstance(value_model, FormSpec):
        visitor = get_visitor(value_model, VisitorOptions(migrate_values=True, mask_values=False))
        if errors := visitor.validate(RawDiskData(value)):
            raise MKUserError(None, ", ".join(str(e.message) for e in errors))
        return
    value_model.validate_datatype(value, "")
    value_model.validate_value(value, "")


@dataclass(frozen=True)
class CasePass:
    id: str
    value: object


@dataclass(frozen=True)
class CaseFail:
    id: str
    value: object
    exception: type[BaseException] = MKUserError


@dataclass(frozen=True)
class CaseMigrates:
    """Legacy stored data that the load-and-save-again path must rewrite to the
    current format."""

    id: str
    value: object
    expected: object


@dataclass(frozen=True)
class CaseDirty:
    """Valid stored data that the current value model fails to validate cleanly,
    while the round trip still keeps it unchanged. Expected to become a CasePass
    once the variable is ported to FormSpec (or the test environment gap closes,
    or the valuespec bug named in the case id is fixed)."""

    id: str
    value: object
    exception: type[BaseException]


Case = CasePass | CaseFail | CaseMigrates | CaseDirty


@dataclass(frozen=True)
class DefaultWithOverrides:
    """Resolved in the test body to the variable's default disk value updated
    with the overrides. The default itself cannot be spelled out in the case
    table because it differs between editions."""

    overrides: Mapping[str, object]


@dataclass(frozen=True)
class DefaultWithoutKeys:
    """Resolved in the test body to the variable's default disk value with the
    keys removed."""

    keys: frozenset[str]


@dataclass(frozen=True)
class EditionDependentDefault:
    """A config variable whose default differs between the community edition
    and the commercial editions."""

    community: object
    commercial: object

    def for_edition(self, edition: Edition) -> object:
        return self.community if edition is Edition.COMMUNITY else self.commercial


def resolve_case_value(
    config_variable: ConfigVariable, context: GlobalSettingsContext, value: object
) -> object:
    if not isinstance(value, DefaultWithOverrides | DefaultWithoutKeys):
        return value
    default = default_disk_value(config_variable, context)
    assert isinstance(default, dict)
    if isinstance(value, DefaultWithoutKeys):
        return {key: v for key, v in default.items() if key not in value.keys}
    return {**default, **value.overrides}


CHECKBOX_CASES: list[Case] = [
    CasePass("enabled", True),
    CasePass("disabled", False),
    CaseFail("not-a-bool", 1),
]

MIN_ONE_INTEGER_CASES: list[Case] = [
    CasePass("configured", 10),
    CaseFail("below-minimum", 0),
    CaseFail("not-an-int", "10"),
]

MIN_ONE_AGE_CASES: list[Case] = [
    CasePass("configured", 120),
    CaseFail("below-minimum", 0),
    CaseFail("not-an-int", "2m"),
]

MIN_ONE_FLOAT_CASES: list[Case] = [
    CasePass("configured", 4.0),
    CaseFail("below-minimum", 0.5),
    CaseFail("not-a-float", "4"),
]

OPTIONAL_MIN_ONE_INTEGER_CASES: list[Case] = [
    CasePass("disabled", None),
    CasePass("configured", 60),
    CaseFail("below-minimum", 0),
]

UNBOUNDED_INTEGER_CASES: list[Case] = [
    CasePass("configured", 30),
    CaseFail("not-an-int", "30"),
]

UNBOUNDED_AGE_CASES: list[Case] = [
    CasePass("configured", 30),
    CaseFail("not-an-int", "30s"),
]


def choice_cases(configured: object, not_a_choice: object) -> list[Case]:
    return [
        CasePass("configured", configured),
        CaseFail("not-a-choice", not_a_choice),
    ]


CLOUD_EXCLUSIVE_VARIABLES = frozenset({"enable_ai_explanations"})


SCALAR_VALUE_MODELS: frozenset[type] = frozenset(
    {
        valuespec.Age,
        valuespec.Checkbox,
        valuespec.DropdownChoice,
        valuespec.EmailAddress,
        valuespec.Filesize,
        valuespec.Float,
        valuespec.Integer,
        valuespec.TextInput,
        valuespec.Url,
        form_specs.BooleanChoice,
        form_specs.DataSize,
        form_specs.Float,
        form_specs.Integer,
        form_specs.Percentage,
        form_specs.SingleChoice,
        form_specs.String,
        form_specs.TimeSpan,
        SingleChoiceExtended,
    }
)


def is_scalar_value_model(value_model: object) -> bool:
    """Whether the value model is a leaf widget whose own default never takes
    effect because the default config always wins, unlike composite value
    models, which surface their embedded defaults when a sub-form is activated.
    A TransformDataForLegacyFormatOrRecomposeFunction only adapts the disk
    format, so it is classified by the form spec it wraps.
    """
    if isinstance(value_model, TransformDataForLegacyFormatOrRecomposeFunction):
        return is_scalar_value_model(value_model.wrapped_form_spec)
    return type(value_model) in SCALAR_VALUE_MODELS


DEFAULT_DISK_VALUES: Mapping[str, object] = {
    "acknowledge_problems": {
        "ack_sticky": False,
        "ack_persistent": False,
        "ack_notify": True,
        "ack_expire": 3600,
    },
    "actions": [],
    "adhoc_downtime": None,
    "agent_bakery_logging": None,
    "agent_controller_certificates": {"lifetime_in_months": 3},
    "agent_deployment_central": {},
    "agent_deployment_host_selection": {},
    "agent_deployment_remote": {},
    "alert_handler_event_types": [],
    "apache_process_tuning": {"number_of_processes": 5},
    "auth_by_http_header": None,
    "builtin_icon_visibility": {},
    "bulk_discovery_default_settings": {
        "mode": (
            "update_everything",
            {
                "add_new_services": True,
                "remove_vanished_services": True,
                "update_host_labels": True,
                "update_changed_service_labels": True,
                "update_changed_service_parameters": True,
            },
        ),
        "selection": (True, False, False, False),
        "performance": (True, 10),
        "error_handling": True,
    },
    "cmc_authorization": {"host": 0, "group": 0},
    "cmc_config_multiprocessing": {"use_multiprocessing": False},
    "cmc_flap_settings": (3.0, 5.0, 0.1),
    "cmc_graphite": [],
    "cmc_initial_scheduling": {"burst": 10, "spread_cmk": 1200, "spread_generic": 150},
    "cmc_log_cmk_helpers": {"debug": False},
    "cmc_log_levels": {
        "cmk.alert": 5,
        "cmk.carbon": 5,
        "cmk.core": 5,
        "cmk.downtime": 5,
        "cmk.helper": 5,
        "cmk.livestatus": 5,
        "cmk.notification": 5,
        "cmk.rrd": 5,
        "cmk.influxdb": 5,
        "cmk.smartping": 5,
    },
    "cmc_real_time_checks": None,
    "cmc_smartping_tuning": {"omit_payload": False, "num_sockets": 8, "ignore_rst": False},
    "cmc_statehist_cache": None,
    "custom_service_attributes": {},
    "dcd_log_levels": {"cmk.dcd": 20, "cmk.dcd.web_api": 20},
    "default_bi_layout": {"node_style": "builtin_force", "line_style": "round"},
    "default_user_profile": {"roles": ["user"], "contactgroups": [], "force_authuser": False},
    "diskspace_cleanup": {"cleanup_abandoned_host_files": 2592000},
    "event_limit": {
        "by_host": {"limit": 1000, "action": "stop_overflow_notify"},
        "by_rule": {"limit": 1000, "action": "stop_overflow_notify"},
        "overall": {"limit": 10000, "action": "stop_overflow_notify"},
    },
    "graph_timeranges": [],
    "hostname_translation": {},
    "http_proxies": {},
    "inventory_check_interval": None,
    "inventory_cleanup": {
        "for_hosts": [],
        "default": {"strategy": "and", "file_age": 34560000, "number_of_history_entries": 100},
        "abandoned_file_age": 2592000,
    },
    "ldap_quarantine_period": None,
    "liveproxyd_default_connection_params": {
        "channels": 5,
        "heartbeat": (5, 2.0),
        "channel_timeout": 3.0,
        "query_timeout": 120.0,
        "connect_retry": 4.0,
        "cache": True,
    },
    "liveproxyd_log_levels": {"cmk.liveproxyd": 20},
    "lock_on_logon_failures": None,
    "log_level": {
        "cmk.mkeventd": 20,
        "cmk.mkeventd.EventServer": 20,
        "cmk.mkeventd.EventStatus": 20,
        "cmk.mkeventd.StatusServer": 20,
        "cmk.mkeventd.lock": 20,
        "cmk.mkeventd.EventServer.snmp": 20,
    },
    "log_levels": EditionDependentDefault(
        community={
            "cmk.web": 30,
            "cmk.web.auth": 30,
            "cmk.web.ldap": 30,
            "cmk.web.bi.compilation": 30,
            "cmk.automations": 30,
            "cmk.web.ui-job-scheduler": 30,
            "cmk.web.background-job": 30,
            "cmk.web.slow-views": 30,
            "cmk.web.automatic_host_removal": 30,
        },
        commercial={
            "cmk.web": 30,
            "cmk.web.auth": 30,
            "cmk.web.ldap": 30,
            "cmk.web.bi.compilation": 30,
            "cmk.automations": 30,
            "cmk.web.ui-job-scheduler": 30,
            "cmk.web.background-job": 30,
            "cmk.web.slow-views": 30,
            "cmk.web.automatic_host_removal": 30,
            "cmk.web.agent_registration": 30,
            "cmk.web.saml2": 30,
        },
    ),
    "login_screen": {},
    "metric_backend": ("disabled", None),
    "mkeventd_notify_contactgroup": "",
    "mkeventd_notify_remotehost": None,
    "mkeventd_service_levels": [],
    "network_flow": ("disabled", None),
    "notification_fallback_format": ("asciimail", {}),
    "notification_spooler_config": {
        "log_level": 20,
        "deferred_cooldown": 1,
        "deferred_force_retransmit": 1,
        "outgoing": [],
        "concurrency": [],
    },
    "ntop_connection": {
        "is_activated": True,
        "is_host_filter_activated": True,
        "hostaddress": "",
        "port": 3000,
        "protocol": "https",
        "no-cert-check": True,
        "admin_username": "",
        "admin_password": ("password", ""),
        "use_custom_attribute_as_ntop_username": False,
    },
    "password_policy": {},
    "product_usage_analytics": {
        "enabled": "enabled",
        "proxy_setting": ("environment", "environment"),
    },
    "profiling_options": {"enabled": False, "max_count": 100},
    "quicksearch_search_order": [],
    "remote_status": None,
    "replication": None,
    "reporting_email_options": {},
    "reporting_graph_layout": {
        "font_size": 8.0,
        "show_title": True,
        "title_format": ["plain"],
        "show_graph_time": True,
        "show_margin": True,
        "show_legend": True,
        "show_vertical_axis": True,
        "vertical_axis_width": "fixed",
        "show_time_axis": True,
        "fixed_timerange": False,
        "border_width": 0.05,
        "color_gradient": 20.0,
    },
    "reporting_margins": (10.0, 10.0, 10.0, 10.0),
    "reporting_pagesize": (210.0, 297.0),
    "reporting_rangespec": "fwd0",
    "reporting_table_layout": {
        "font_size": 8.0,
        "show_headings": True,
        "hrules": True,
        "vrules": False,
        "rule_width": 0.05,
        "padding": (2, 0.5),
        "spacing": (4, 1),
        "row_shading": {
            "enabled": False,
            "odd": (0.9686274509803922, 0.9686274509803922, 0.9686274509803922),
            "even": (0.9411764705882353, 0.9411764705882353, 0.9411764705882353),
            "heading": (0.7019607843137254, 0.7019607843137254, 0.7019607843137254),
        },
    },
    "rrdcached_tuning": {"TIMEOUT": 0, "RANDOM_DELAY": 0, "FLUSH_TIMEOUT": 0, "WRITE_THREADS": 1},
    "service_view_grouping": [],
    "session_mgmt": {},
    "sidebar_notify_interval": None,
    "single_user_session": None,
    "site_livestatus_tcp": None,
    "site_mkeventd": None,
    "site_opentelemetry_collector_delta_to_cumulative_processor": {
        "max_stale": 300,
        "max_streams": 9223372036854775807,
    },
    "site_opentelemetry_collector_memory_limit": {
        "check_interval": 1,
        "limit": ("relative", {"limit": 80, "spike_limit": 20}),
    },
    "site_subject_alternative_names": [],
    "site_trace_receive": None,
    "site_trace_send": "no_tracing",
    "snmp_backend_default": "classic",
    "snmp_credentials": [],
    "translate_snmptraps": False,
    "trusted_certificate_authorities": {"use_system_wide_cas": False, "trusted_cas": []},
    "use_new_descriptions_for": {
        "aix_memory": False,
        "barracuda_mailqueues": False,
        "brocade_sys_mem": False,
        "casa_cpu_temp": False,
        "cisco_mem": False,
        "cisco_mem_asa": False,
        "cisco_mem_asa64": False,
        "cmciii_psm_current": False,
        "cmciii_temp": False,
        "cmciii_lcp_airin": False,
        "cmciii_lcp_airout": False,
        "cmciii_lcp_water": False,
        "cmk_inventory": False,
        "db2_mem": False,
        "df": False,
        "df_netapp": False,
        "df_netapp32": False,
        "docker_container_mem": False,
        "enterasys_temp": False,
        "esx_vsphere_datastores": False,
        "esx_vsphere_hostsystem_mem_usage": False,
        "esx_vsphere_hostsystem_mem_usage_cluster": False,
        "etherbox_temp": False,
        "fortigate_memory": False,
        "fortigate_memory_base": False,
        "fortigate_node_memory": False,
        "hr_fs": False,
        "hr_mem": False,
        "http": False,
        "huawei_switch_mem": False,
        "hyperv_vms": False,
        "ibm_svc_mdiskgrp": False,
        "ibm_svc_system": False,
        "ibm_svc_systemstats_cache": False,
        "ibm_svc_systemstats_disk_latency": False,
        "ibm_svc_systemstats_diskio": False,
        "ibm_svc_systemstats_iops": False,
        "innovaphone_mem": False,
        "innovaphone_temp": False,
        "juniper_mem": False,
        "juniper_screenos_mem": False,
        "juniper_trpz_mem": False,
        "liebert_bat_temp": False,
        "logwatch": False,
        "logwatch_groups": False,
        "megaraid_pdisks": False,
        "megaraid_ldisks": False,
        "megaraid_bbu": False,
        "mem_used": False,
        "mem_win": False,
        "mknotifyd": False,
        "mknotifyd_connection": False,
        "mssql_backup": False,
        "mssql_blocked_sessions": False,
        "mssql_counters_cache_hits": False,
        "mssql_counters_file_sizes": False,
        "mssql_counters_locks": False,
        "mssql_counters_locks_per_batch": False,
        "mssql_counters_pageactivity": False,
        "mssql_counters_sqlstats": False,
        "mssql_counters_transactions": False,
        "mssql_databases": False,
        "mssql_datafiles": False,
        "mssql_tablespaces": False,
        "mssql_transactionlogs": False,
        "mssql_versions": False,
        "netapp_ontap_volumes": False,
        "netapp_ontap_snapshots": False,
        "netscaler_mem": False,
        "nullmailer_mailq": False,
        "prism_alerts": False,
        "prism_containers": False,
        "prism_info": False,
        "prism_storage_pools": False,
        "nvidia_temp": False,
        "postfix_mailq": False,
        "ps": False,
        "qmail_stats": False,
        "raritan_emx": False,
        "raritan_pdu_inlet": False,
        "services": False,
        "solaris_mem": False,
        "sophos_memory": False,
        "statgrab_mem": False,
        "tplink_mem": False,
        "ups_bat_temp": False,
        "vms_diskstat_df": False,
        "wmic_process": False,
        "zfsget": False,
    },
    "user_downtime_timeranges": [],
    "user_icons_and_actions": {},
    "user_localizations": {},
    "user_security_notification_duration": {
        "max_duration": 604800,
        "update_existing_duration": False,
    },
    "virtual_host_trees": [],
    "vue_experimental_features": {"rule_render_mode": "frontend"},
    "wato_icon_categories": [],
}


CASES: Mapping[str, list[Case]] = {
    "acknowledge_problems": [
        CasePass(
            "configured",
            {
                "ack_sticky": True,
                "ack_persistent": False,
                "ack_notify": True,
                "ack_expire": 7200,
            },
        ),
        CaseFail("missing-required-keys", {"ack_sticky": True}),
        CaseFail(
            "expire-below-minimum",
            {
                "ack_sticky": True,
                "ack_persistent": False,
                "ack_notify": True,
                "ack_expire": 30,
            },
        ),
    ],
    "actions": [
        CasePass(
            "email-and-script",
            [
                {
                    "id": "notify_ops",
                    "title": "Notify ops",
                    "disabled": False,
                    "hidden": False,
                    "action": (
                        "email",
                        {"to": "ops@example.com", "subject": "EC event", "body": "$DETAILS$"},
                    ),
                },
                {
                    "id": "restart_svc",
                    "title": "Restart service",
                    "disabled": True,
                    "hidden": True,
                    "action": ("script", {"script": "systemctl restart foo"}),
                },
            ],
        ),
        CaseFail(
            "invalid-action-id",
            [
                {
                    "id": "bad id!",
                    "title": "Bad",
                    "disabled": False,
                    "hidden": False,
                    "action": ("script", {"script": "true"}),
                }
            ],
        ),
        CaseFail("not-a-list", "notify_ops"),
    ],
    "adhoc_downtime": [
        CasePass("disabled", None),
        CasePass("configured", {"duration": 120, "comment": "Deployment"}),
        CaseFail("missing-comment", {"duration": 120}),
        CaseFail("not-a-dict", "2h"),
    ],
    "agent_bakery_logging": [
        CasePass("disabled", None),
        CasePass("configured", 10),
        CaseFail("not-a-log-level", 25),
    ],
    "agent_controller_certificates": [
        CasePass("configured", {"lifetime_in_months": 60}),
        CaseFail("lifetime-not-a-choice", {"lifetime_in_months": 7}),
        CaseFail("missing-required-keys", {}),
    ],
    "agent_deployment_central": [
        CasePass("configured", {"central_url": "https://cmk.example.com/prod/check_mk/"}),
        CaseFail("unknown-key", {"bogus": 1}),
    ],
    "agent_deployment_enabled": CHECKBOX_CASES,
    "agent_deployment_host_selection": [
        CasePass("configured", {"match_hosts": ["web01"], "match_exclude_hosts": ["web02"]}),
        CasePass(
            "tags-and-labels",
            {"match_hosttags": {"agent": "cmk-agent"}, "match_hostlabels": {"env": "prod"}},
        ),
        CaseFail("label-value-not-a-string", {"match_hostlabels": {"env": 1}}),
        CaseFail("not-a-dict", "web01"),
    ],
    "agent_deployment_remote": [
        CasePass("configured", {"remote_url": "https://remote.example.com/site/check_mk/"}),
        CaseFail("unknown-key", {"bogus": 1}),
    ],
    "alert_handler_event_types": [
        CasePass("configured", ["statechange", "checkresult"]),
        CaseFail("empty-list", []),
        CaseFail("unknown-event-type", ["bogus"]),
    ],
    "alert_handler_timeout": MIN_ONE_AGE_CASES,
    "alert_logging": choice_cases(10, 30),
    "apache_process_tuning": [
        CasePass("configured", {"number_of_processes": 10}),
        CaseFail("below-minimum", {"number_of_processes": 1}),
        CaseFail("not-an-int", {"number_of_processes": "10"}),
    ],
    "apply_bake_revision": CHECKBOX_CASES,
    "archive_orphans": CHECKBOX_CASES,
    "auth_by_http_header": [
        CasePass("disabled", None),
        CasePass("configured", "X-Remote-User"),
        CaseFail("not-a-string", 123),
    ],
    "bake_agents_on_restart": CHECKBOX_CASES,
    "builtin_icon_visibility": [
        CasePass("configured", {"reschedule": {"toplevel": True, "sort_index": 10}}),
        CaseFail("unknown-icon", {"no_such_icon": {"toplevel": True}}),
        CaseFail("not-a-dict-crashes-transform", "reschedule", AttributeError),
    ],
    "bulk_discovery_default_settings": [
        CasePass(
            "configured",
            {
                "mode": (
                    "custom",
                    {
                        "add_new_services": True,
                        "remove_vanished_services": False,
                        "update_host_labels": True,
                        "update_changed_service_labels": False,
                        "update_changed_service_parameters": False,
                    },
                ),
                "selection": (True, False, False, False),
                "performance": (True, 10),
                "error_handling": True,
            },
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "check_mk_perfdata_with_times": CHECKBOX_CASES,
    "cluster_max_cachefile_age": UNBOUNDED_INTEGER_CASES,
    "cmc_authorization": [
        CasePass("configured", {"host": 1, "group": 1}),
        CaseFail("not-a-choice", {"host": 2, "group": 0}),
        CaseFail("missing-required-keys", {}),
    ],
    "cmc_check_helpers": MIN_ONE_INTEGER_CASES,
    "cmc_check_timeout": MIN_ONE_AGE_CASES,
    "cmc_checker_helpers": MIN_ONE_INTEGER_CASES,
    "cmc_config_multiprocessing": [
        CasePass("configured", {"use_multiprocessing": True, "limit_workers": 4}),
        CaseFail("workers-below-minimum", {"use_multiprocessing": True, "limit_workers": 0}),
        CaseFail("missing-required-keys", {}),
    ],
    "cmc_debug_notifications": CHECKBOX_CASES,
    "cmc_dump_core": CHECKBOX_CASES,
    "cmc_fetcher_helpers": MIN_ONE_INTEGER_CASES,
    "cmc_flap_settings": [
        CasePass("configured", (2.0, 6.0, 0.5)),
        CaseFail("wrong-length", (2.0, 6.0)),
        CaseFail("not-a-tuple", 3.0),
    ],
    "cmc_graphite": [
        CasePass(
            "configured",
            [{"host": "graphite.example.com", "port": 2003, "prefix": "cmk", "mangling": True}],
        ),
        CaseFail("missing-required-keys", [{"host": "graphite.example.com"}]),
        CaseFail("not-a-list", "graphite.example.com"),
    ],
    "cmc_import_nagios_state": CHECKBOX_CASES,
    "cmc_initial_scheduling": [
        CasePass("configured", {"burst": 20, "spread_cmk": 600, "spread_generic": 300}),
        CaseFail("missing-required-keys", {}),
    ],
    "cmc_livestatus_lines_per_file": [
        CasePass("configured", 100000),
        CaseFail("below-minimum", 5),
        CaseFail("not-an-int", "many"),
    ],
    "cmc_livestatus_logcache_size": [
        CasePass("configured", 500000),
        CaseFail("below-minimum", -1),
        CaseFail("not-an-int", "500MB"),
    ],
    "cmc_livestatus_threads": MIN_ONE_INTEGER_CASES,
    "cmc_log_cmk_helpers": [
        CasePass("configured", {"debug": True}),
        CaseFail("missing-required-keys", {}),
    ],
    "cmc_log_levels": [
        CasePass("configured", DefaultWithOverrides({"cmk.core": 7})),
        CaseFail("not-a-log-level", DefaultWithOverrides({"cmk.core": 8})),
    ],
    "cmc_log_limit": [
        CasePass("configured", 204800),
        CaseFail("below-minimum", 1024),
        CaseFail("not-an-int", "100KB"),
    ],
    "cmc_log_microtime": CHECKBOX_CASES,
    "cmc_log_rotation_method": choice_cases(3, 9),
    "cmc_log_rrdcreation": choice_cases("terse", "verbose"),
    "cmc_max_response_size": [
        CasePass("configured", 200),
        CaseFail("below-minimum", 5),
        CaseFail("not-an-int", "200MB"),
    ],
    "cmc_pnp_update_delay": UNBOUNDED_AGE_CASES,
    "cmc_pnp_update_on_restart": CHECKBOX_CASES,
    "cmc_real_time_checks": [
        CasePass("disabled", None),
        CasePass("configured", {"port": 6559}),
        CaseMigrates(
            "secret-dropped-on-update",
            {"port": 6559, "secret": "hunter2"},
            {"port": 6559},
        ),
        CaseFail("well-known-port", {"port": 80}),
    ],
    "cmc_real_time_helpers": MIN_ONE_INTEGER_CASES,
    "cmc_smartping_tuning": [
        CasePass("configured", {"omit_payload": True, "num_sockets": 16, "ignore_rst": True}),
        CaseFail(
            "sockets-below-minimum",
            {"omit_payload": False, "num_sockets": 0, "ignore_rst": False},
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "cmc_state_retention_interval": UNBOUNDED_AGE_CASES,
    "cmc_statehist_cache": [
        CasePass("disabled", None),
        CasePass("configured", {"horizon": 86400, "max_core_downtime": 60}),
        CaseFail("horizon-below-minimum", {"horizon": 0, "max_core_downtime": 60}),
    ],
    "cmc_timeperiod_horizon": [
        CasePass("configured", 30),
        CaseFail("below-minimum", 5),
        CaseFail("not-an-int", "30d"),
    ],
    "crash_report_target": [
        CasePass("configured", "support@example.com"),
        CaseFail("not-a-string", 123),
    ],
    "crash_report_url": [
        CasePass("configured", "https://crash.checkmk.com"),
        CasePass("empty", ""),
        CaseFail("unsupported-scheme", "ftp://crash.checkmk.com"),
        CaseFail("scheme-without-host", "http://"),
        CaseFail("not-a-string", 123),
    ],
    "custom_service_attributes": [
        CasePass(
            "configured",
            {"ENV": {"ident": "ENV", "title": "Environment", "type": "TextAscii"}},
        ),
        CaseFail(
            "lowercase-ident",
            {"env": {"ident": "env", "title": "Environment", "type": "TextAscii"}},
        ),
        CaseFail(
            "reserved-internal-ident",
            {"EC_SL": {"ident": "EC_SL", "title": "Service level", "type": "TextAscii"}},
        ),
        CaseFail(
            "duplicate-title",
            {
                "ENV": {"ident": "ENV", "title": "Environment", "type": "TextAscii"},
                "ENV2": {"ident": "ENV2", "title": "Environment", "type": "TextAscii"},
            },
        ),
        CaseFail("not-a-dict-crashes-transform", "ENV", AttributeError),
    ],
    "dcd_activate_changes_timeout": [
        CasePass("configured", 300),
        CaseFail("below-minimum", 1),
        CaseFail("not-an-int", "5m"),
    ],
    "dcd_bulk_discovery_timeout": [
        CasePass("configured", 300),
        CaseFail("below-minimum", 1),
        CaseFail("not-an-int", "5m"),
    ],
    "dcd_log_levels": [
        CasePass("configured", DefaultWithOverrides({"cmk.dcd": 10})),
        CaseFail("not-a-log-level", DefaultWithOverrides({"cmk.dcd": 25})),
    ],
    "dcd_max_activation_delay": UNBOUNDED_AGE_CASES,
    "dcd_max_hosts_per_bulk_discovery": [
        CasePass("configured", 100),
        CaseFail("below-minimum", 1),
        CaseFail("not-an-int", "100"),
    ],
    "dcd_prevent_unwanted_notification": CHECKBOX_CASES,
    "dcd_site_update_interval": MIN_ONE_AGE_CASES,
    "debug": CHECKBOX_CASES,
    "debug_livestatus_queries": CHECKBOX_CASES,
    "debug_rules": CHECKBOX_CASES,
    "default_bi_layout": [
        CasePass("configured", {"node_style": "builtin_hierarchy", "line_style": "straight"}),
        CaseFail("unknown-node-style", {"node_style": "bogus", "line_style": "round"}),
    ],
    "default_dynamic_visual_permission": choice_cases("no", "maybe"),
    "default_language": choice_cases("en", "klingon"),
    "default_temperature_unit": choice_cases("fahrenheit", "kelvin"),
    "default_user_profile": [
        CasePass("configured", {"roles": ["admin"], "contactgroups": [], "force_authuser": False}),
        CaseFail(
            "unknown-role",
            {"roles": ["no_such_role"], "contactgroups": [], "force_authuser": False},
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "delay_precompile": CHECKBOX_CASES,
    "diskspace_cleanup": [
        CasePass("configured", {"max_file_age": 86400, "cleanup_abandoned_host_files": 7200}),
        CasePass("min-free-bytes", {"min_free_bytes": (1073741824, 3600)}),
        CaseFail("max-file-age-below-minimum", {"max_file_age": 0}),
        CaseFail("unknown-key", {"bogus": 1}),
    ],
    "enable_ai_explanations": choice_cases(False, "yes"),
    "enable_login_via_get": CHECKBOX_CASES,
    "enable_sounds": CHECKBOX_CASES,
    "escape_plugin_output": CHECKBOX_CASES,
    "event_limit": [
        CasePass(
            "configured",
            {
                "by_host": {"limit": 500, "action": "stop"},
                "by_rule": {"limit": 200, "action": "delete_oldest"},
                "overall": {"limit": 5000, "action": "stop_overflow"},
            },
        ),
        CaseFail(
            "unknown-action",
            {
                "by_host": {"limit": 500, "action": "explode"},
                "by_rule": {"limit": 200, "action": "delete_oldest"},
                "overall": {"limit": 5000, "action": "stop_overflow"},
            },
        ),
        CaseFail("missing-required-keys", {"by_host": {"limit": 500, "action": "stop"}}),
    ],
    "eventsocket_queue_len": MIN_ONE_INTEGER_CASES,
    "failed_notification_horizon": [
        CasePass("configured", 172800),
        CaseFail("below-minimum", 3600),
        CaseFail("not-an-int", "1d"),
    ],
    "graph_timeranges": [
        CasePass("configured", [{"title": "The last 4 fortnights", "duration": 4838400}]),
        CaseFail("missing-duration", [{"title": "The last 4 fortnights"}]),
        CaseFail("not-a-list", "4h"),
    ],
    "hard_query_limit": MIN_ONE_INTEGER_CASES,
    "history_lifetime": MIN_ONE_INTEGER_CASES,
    "history_rotation": choice_cases("weekly", "monthly"),
    "hostname_translation": [
        CasePass(
            "configured",
            {
                "drop_domain": True,
                "case": "lower",
                "regex": [("vm_(.*)_prod", "\\1")],
                "mapping": [("host666", "host667")],
            },
        ),
        CaseFail("unknown-case-conversion", {"case": "mixed"}),
        CaseFail("invalid-regex", {"regex": [("(unbalanced", "x")]}),
    ],
    "housekeeping_interval": UNBOUNDED_AGE_CASES,
    "http_proxies": [
        CasePass(
            "configured",
            {
                "corp": {
                    "ident": "corp",
                    "title": "Corp proxy",
                    "proxy_config": {
                        "scheme": "http",
                        "proxy_server_name": "proxy.corp.example",
                        "port": 3128,
                    },
                }
            },
        ),
        CaseFail(
            "unknown-scheme",
            {
                "corp": {
                    "ident": "corp",
                    "title": "Corp proxy",
                    "proxy_config": {
                        "scheme": "gopher",
                        "proxy_server_name": "proxy.corp.example",
                        "port": 3128,
                    },
                }
            },
        ),
        CaseFail(
            "duplicate-ident",
            {
                "corp": {
                    "ident": "corp",
                    "title": "Corp proxy",
                    "proxy_config": {
                        "scheme": "http",
                        "proxy_server_name": "proxy.corp.example",
                        "port": 3128,
                    },
                },
                "corp2": {
                    "ident": "corp",
                    "title": "Corp proxy 2",
                    "proxy_config": {
                        "scheme": "http",
                        "proxy_server_name": "proxy2.corp.example",
                        "port": 3128,
                    },
                },
            },
        ),
        CaseFail(
            "duplicate-title",
            {
                "corp": {
                    "ident": "corp",
                    "title": "Corp proxy",
                    "proxy_config": {
                        "scheme": "http",
                        "proxy_server_name": "proxy.corp.example",
                        "port": 3128,
                    },
                },
                "corp2": {
                    "ident": "corp2",
                    "title": "Corp proxy",
                    "proxy_config": {
                        "scheme": "http",
                        "proxy_server_name": "proxy2.corp.example",
                        "port": 3128,
                    },
                },
            },
        ),
        CaseFail("not-a-dict-crashes-transform", ["corp"], AttributeError),
    ],
    "inject_js_profiling_code": CHECKBOX_CASES,
    "inventory_check_autotrigger": CHECKBOX_CASES,
    "inventory_check_interval": OPTIONAL_MIN_ONE_INTEGER_CASES,
    "inventory_check_severity": choice_cases(2, 5),
    "inventory_cleanup": [
        CasePass(
            "configured",
            {
                "for_hosts": [
                    {
                        "regex_or_explicit": ["legacy-.*"],
                        "parameters": ("file_age", 86400),
                    }
                ],
                "default": {
                    "strategy": "and",
                    "file_age": 86400,
                    "number_of_history_entries": 50,
                },
                "abandoned_file_age": 3600,
            },
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "ldap_quarantine_period": [
        CasePass("disabled", None),
        CasePass("configured", 86400),
        CaseFail("below-minimum", 60),
    ],
    "liveproxyd_default_connection_params": [
        CasePass("configured", DefaultWithOverrides({"channels": 10})),
        CaseFail("channels-below-minimum", DefaultWithOverrides({"channels": 1})),
        CaseFail("missing-required-keys", {}),
    ],
    "liveproxyd_log_levels": [
        CasePass("configured", DefaultWithOverrides({"cmk.liveproxyd": 10})),
        CaseFail("not-a-log-level", DefaultWithOverrides({"cmk.liveproxyd": 25})),
    ],
    "load_frontend_vue": choice_cases("inject", "bogus"),
    "lock_on_logon_failures": OPTIONAL_MIN_ONE_INTEGER_CASES,
    "log_level": [
        CasePass("configured", DefaultWithOverrides({"cmk.mkeventd": 10})),
        CaseFail("not-a-log-level", DefaultWithOverrides({"cmk.mkeventd": 25})),
    ],
    "log_levels": [
        CasePass("configured", DefaultWithOverrides({"cmk.web.auth": 10})),
        CaseFail("not-a-log-level", DefaultWithOverrides({"cmk.web": 25})),
        CaseMigrates(
            "job-scheduler-level-added-on-update",
            DefaultWithoutKeys(frozenset({"cmk.web.ui-job-scheduler"})),
            DefaultWithOverrides({"cmk.web.ui-job-scheduler": 20}),
        ),
    ],
    "log_logon_failures": CHECKBOX_CASES,
    "log_messages": CHECKBOX_CASES,
    "log_rulehits": CHECKBOX_CASES,
    "login_screen": [
        CasePass(
            "configured",
            {
                "hide_version": True,
                "login_message": "Welcome to ops",
                "footer_links": [("Docs", "https://docs.checkmk.com", "_blank")],
            },
        ),
        CaseFail("unknown-link-target", {"footer_links": [("Docs", "https://docs", "_new")]}),
        CaseFail("hide-version-not-fixed-value", {"hide_version": False}),
    ],
    "max_long_output_size": [
        CasePass("configured", 5000),
        CaseFail("below-minimum", 100),
        CaseFail("not-an-int", "5000"),
    ],
    "metric_backend": [
        CasePass("disabled", ("disabled", None)),
        CasePass(
            "configured",
            (
                "enabled",
                {"tls_port": 9000, "https_port": 8443, "relative_memory_limit_percentage": 50.0},
            ),
        ),
        CaseFail(
            "duplicate-ports",
            (
                "enabled",
                {"tls_port": 9000, "https_port": 9000, "relative_memory_limit_percentage": 50.0},
            ),
        ),
        CaseFail("unknown-choice", ("bogus", None)),
    ],
    "mkeventd_connect_timeout": MIN_ONE_INTEGER_CASES,
    "mkeventd_notify_contactgroup": [
        CaseDirty("no-groups-defined-in-test-config", "oncall", MKUserError),
        CaseFail("not-a-string", 123),
    ],
    "mkeventd_notify_facility": choice_cases(5, 99),
    "mkeventd_notify_remotehost": [
        CasePass("disabled", None),
        CasePass("configured", "central.example.com"),
        CaseFail("not-a-string", 123),
    ],
    "mkeventd_pprint_rules": CHECKBOX_CASES,
    "mkeventd_service_levels": [
        CasePass("configured", [(10, "Silver"), (20, "Gold")]),
        CaseFail("level-out-of-range", [(200, "Out of range")]),
        CaseFail("empty-list", []),
        CaseFail("empty-name", [(10, "")]),
        CaseFail("not-a-list", "10"),
    ],
    "multisite_draw_ruleicon": CHECKBOX_CASES,
    "network_flow": [
        CasePass("disabled", ("disabled", None)),
        CasePass(
            "configured",
            (
                "enabled",
                {
                    "flow_source_endpoints": [
                        ("connect", "collector.example.com:9995"),
                        ("listen", 9996),
                    ],
                    "local_networks": ["10.0.0.0/8"],
                    "dns_mode": 0,
                    "retention_days": 30,
                },
            ),
        ),
        CaseFail(
            "endpoint-missing-port",
            (
                "enabled",
                {
                    "flow_source_endpoints": [("connect", "collector.example.com")],
                    "local_networks": [],
                    "dns_mode": 0,
                    "retention_days": 30,
                },
            ),
        ),
        CaseFail(
            "endpoint-port-not-a-number",
            (
                "enabled",
                {
                    "flow_source_endpoints": [("connect", "collector.example.com:abc")],
                    "local_networks": [],
                    "dns_mode": 0,
                    "retention_days": 30,
                },
            ),
        ),
        CaseFail(
            "endpoint-port-out-of-range",
            (
                "enabled",
                {
                    "flow_source_endpoints": [("connect", "collector.example.com:70000")],
                    "local_networks": [],
                    "dns_mode": 0,
                    "retention_days": 30,
                },
            ),
        ),
        CaseFail(
            "empty-endpoints",
            (
                "enabled",
                {
                    "flow_source_endpoints": [],
                    "local_networks": [],
                    "dns_mode": 0,
                    "retention_days": 30,
                },
            ),
        ),
    ],
    "notification_backlog": UNBOUNDED_INTEGER_CASES,
    "notification_bulk_interval": MIN_ONE_AGE_CASES,
    "notification_fallback_email": [
        CasePass("configured", "ops@example.com"),
        CaseFail("not-an-email", "not-an-email"),
        CaseFail("not-a-string", 123),
    ],
    "notification_fallback_format": [
        CasePass("ascii-email", ("asciimail", {})),
        CasePass("html-email", ("mail", {})),
        CaseFail("unknown-format", ("carrier-pigeon", {})),
        CaseFail("bare-ident-missing-parameters", "asciimail"),
    ],
    "notification_logging": choice_cases(15, 30),
    "notification_plugin_timeout": MIN_ONE_AGE_CASES,
    "notification_spooler_config": [
        CasePass("configured", DefaultWithOverrides({"log_level": 10})),
        CaseDirty(
            "no-notification-scripts-in-test-environment",
            DefaultWithOverrides(
                {"concurrency": [("mail", {"process_count": 2, "retries": 3, "timeout": 60})]}
            ),
            MKUserError,
        ),
        CaseFail(
            "tls-authentication-without-tls",
            DefaultWithOverrides(
                {
                    "incoming": {
                        "listen_port": 6555,
                        "encryption": "unencrypted",
                        "authentication": "tls_authenticated",
                        "heartbeat_interval": 10,
                    }
                }
            ),
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "notification_spooling": choice_cases("both", "everywhere"),
    "ntop_connection": [
        CasePass(
            "configured",
            {
                "is_activated": True,
                "is_host_filter_activated": False,
                "hostaddress": "ntop.example.com",
                "port": 3000,
                "protocol": "https",
                "no-cert-check": False,
                "admin_username": "admin",
                "admin_password": ("password", "hunter2"),
                "use_custom_attribute_as_ntop_username": "ntop_alias",
            },
        ),
        CaseFail("missing-required-keys", {}),
        CaseFail("not-a-dict", "ntop.example.com"),
    ],
    "page_heading": [
        CasePass("configured", "Checkmk %s monitoring"),
        CaseFail("not-a-string", 123),
    ],
    "pagetitle_date_format": [
        CasePass("disabled", None),
        CasePass("configured", "yyyy-mm-dd"),
        CaseFail("not-a-choice", "mm/dd/yyyy"),
    ],
    "password_policy": [
        CasePass(
            "configured",
            {"min_length": 12, "num_groups": 3, "max_age": 7776000, "wordlist_check": True},
        ),
        CaseFail("num-groups-above-maximum", {"num_groups": 5}),
        CaseFail("min-length-below-minimum", {"min_length": 0}),
    ],
    "piggyback_max_cachefile_age": UNBOUNDED_AGE_CASES,
    "product_usage_analytics": [
        CasePass(
            "configured",
            {"enabled": "enabled", "proxy_setting": ("environment", "environment")},
        ),
        CasePass(
            "manual-proxy",
            {
                "enabled": "enabled",
                "proxy_setting": (
                    "url",
                    {"scheme": "http", "proxy_server_name": "proxy.corp.example", "port": 3128},
                ),
            },
        ),
        CaseFail(
            "manual-proxy-missing-port",
            {
                "enabled": "enabled",
                "proxy_setting": (
                    "url",
                    {"scheme": "http", "proxy_server_name": "proxy.corp.example"},
                ),
            },
        ),
        CaseFail(
            "unknown-enabled-choice",
            {"enabled": "definitely", "proxy_setting": ("environment", "environment")},
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "profile": [
        CasePass("configured", "enable_by_var"),
        CasePass("enabled", True),
        CaseFail("not-a-choice", "yes"),
    ],
    "profiling_options": [
        CasePass("configured", {"enabled": True, "max_count": 200, "max_age_days": 7}),
        CaseFail("missing-max-count", {"enabled": True}),
        CaseFail("max-count-below-minimum", {"enabled": True, "max_count": 0}),
    ],
    "quicksearch_dropdown_limit": MIN_ONE_INTEGER_CASES,
    "quicksearch_search_order": [
        CasePass("configured", [("h", "continue"), ("s", "finished")]),
        CaseFail("unknown-filter", [("bogus", "continue")]),
        CaseFail("not-a-list", "h"),
    ],
    "remote_status": [
        CasePass("disabled", None),
        CasePass("configured", (6558, True, ["10.0.0.1"])),
        CasePass("no-commands", (6558, False, None)),
        CaseFail("port-below-minimum", (0, True, None)),
        CaseFail("only-from-not-an-ip", (6558, True, ["999.0.0.1"])),
        CaseFail("only-from-empty", (6558, True, [])),
        CaseFail("not-a-tuple", "6558"),
    ],
    "replication": [
        CasePass("disabled", None),
        CasePass(
            "configured",
            {
                "master": ("ec.example.com", 6558),
                "interval": 30,
                "connect_timeout": 10,
                "takeover": 120,
                "fallback": 60,
                "disabled": True,
                "logging": True,
            },
        ),
        CaseFail(
            "port-below-minimum",
            {"master": ("ec.example.com", 0), "interval": 30, "connect_timeout": 10},
        ),
    ],
    "reporting_date_format": choice_cases("%d.%m.%Y", "%q"),
    "reporting_email_options": [
        CasePass("configured", {"from": "reports@example.com", "subject": "Monthly report"}),
        CaseFail("not-an-email", {"from": "not-an-email"}),
        CaseFail("unknown-key", {"bogus": 1}),
    ],
    "reporting_filename": [
        CasePass("configured", "monthly.pdf"),
        CaseFail("not-a-string", 123),
    ],
    "reporting_font_family": choice_cases("Times", "ComicSans"),
    "reporting_font_size": [
        CasePass("configured", 12.0),
        CaseFail("not-a-float", "12"),
    ],
    "reporting_graph_layout": [
        CasePass("configured", DefaultWithOverrides({"font_size": 10.0})),
        CaseFail("unknown-key", DefaultWithOverrides({"bogus": 1})),
    ],
    "reporting_lineheight": [
        CasePass("configured", 1.5),
        CaseFail("not-a-float", "1.5"),
    ],
    "reporting_margins": [
        CasePass("configured", (5.0, 5.0, 5.0, 5.0)),
        CaseFail("wrong-length", (5.0, 5.0)),
        CaseFail("not-a-tuple", 5.0),
    ],
    "reporting_mirror_margins": CHECKBOX_CASES,
    "reporting_pagesize": [
        CasePass("choice", (148.0, 210.0)),
        CasePass("custom", (100.0, 100.0)),
        CaseFail("not-a-size", "A4"),
    ],
    "reporting_rangespec": [
        CasePass("today", "d0"),
        CasePass("date-range", ("date", (1753142400.0, 1753228800.0))),
        CaseFail("not-a-choice", "bogus-range"),
    ],
    "reporting_table_layout": [
        CasePass(
            "configured",
            DefaultWithOverrides({"font_size": 10.0, "padding": (2.0, 0.5), "spacing": (4.0, 1.0)}),
        ),
        CaseDirty("int-defaults-fail-float-validation", DefaultWithOverrides({}), MKUserError),
        CaseFail("unknown-key", DefaultWithOverrides({"bogus": 1})),
    ],
    "reporting_time_format": choice_cases("%H:%M", "%q"),
    "reporting_use": [
        CaseDirty("default-report-missing-in-test-environment", "default", MKUserError),
        CaseFail("not-a-string", 123),
    ],
    "reporting_view_limit": UNBOUNDED_INTEGER_CASES,
    "require_two_factor_all_users": CHECKBOX_CASES,
    "reschedule_timeout": MIN_ONE_FLOAT_CASES,
    "rest_api_etag_locking": CHECKBOX_CASES,
    "restart_locking": [
        CasePass("configured", "wait"),
        CasePass("disabled", None),
        CaseFail("not-a-choice", "block"),
    ],
    "retention_interval": UNBOUNDED_AGE_CASES,
    "rrdcached_tuning": [
        CasePass(
            "configured",
            {"TIMEOUT": 3600, "RANDOM_DELAY": 1800, "FLUSH_TIMEOUT": 7200, "WRITE_THREADS": 4},
        ),
        CaseFail(
            "write-threads-below-minimum",
            {"TIMEOUT": 3600, "RANDOM_DELAY": 1800, "FLUSH_TIMEOUT": 7200, "WRITE_THREADS": 0},
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "rule_optimizer": CHECKBOX_CASES,
    "selection_livetime": MIN_ONE_INTEGER_CASES,
    "service_view_grouping": [
        CasePass("configured", [{"title": "Filesystems", "pattern": "fs_", "min_items": 2}]),
        CaseFail("invalid-regex", [{"title": "Broken", "pattern": "(", "min_items": 2}]),
        CaseFail("not-a-list", "fs_"),
    ],
    "session_mgmt": [
        CasePass(
            "configured",
            {"max_duration": {"enforce_reauth": 86400}, "user_idle_timeout": 5400},
        ),
        CasePass(
            "configured-with-warning-threshold",
            {
                "max_duration": {
                    "enforce_reauth": 86400,
                    "enforce_reauth_warning_threshold": 3600,
                }
            },
        ),
        CaseFail("idle-timeout-below-minimum", {"user_idle_timeout": 30}),
        CaseFail(
            "warning-threshold-not-below-max-duration",
            {
                "max_duration": {
                    "enforce_reauth": 86400,
                    "enforce_reauth_warning_threshold": 86400,
                }
            },
        ),
        CaseFail("unknown-key", {"bogus": 1}),
    ],
    "show_livestatus_errors": CHECKBOX_CASES,
    "show_mode": choice_cases("enforce_show_more", "bogus"),
    "sidebar_notify_interval": [
        CasePass("disabled", None),
        CasePass("configured", 60.0),
        CaseFail("below-minimum", 5.0),
    ],
    "sidebar_update_interval": [
        CasePass("configured", 30.0),
        CaseFail("below-minimum", 5.0),
    ],
    "simulation_mode": CHECKBOX_CASES,
    "single_user_session": [
        CasePass("disabled", None),
        CasePass("configured", 300),
        CaseFail("below-minimum", 10),
    ],
    "site_autostart": CHECKBOX_CASES,
    "site_core": choice_cases("none", "icinga"),
    "site_liveproxyd": CHECKBOX_CASES,
    "site_livestatus_tcp": [
        CasePass("disabled", None),
        CasePass(
            "configured",
            {
                "port": 6557,
                "only_from": ["10.0.0.0/8"],
                "instances": 1,
                "per_source": 1,
                "tls": True,
            },
        ),
        CaseFail("missing-required-keys", {"port": 6557}),
        CaseFail(
            "only-from-not-a-network",
            {
                "port": 6557,
                "only_from": ["not-an-ip"],
                "instances": 1,
                "per_source": 1,
                "tls": True,
            },
        ),
    ],
    "site_mcp_server": CHECKBOX_CASES,
    "site_mcp_trace_forward": CHECKBOX_CASES,
    "site_mkeventd": [
        CasePass("disabled", None),
        CasePass("configured", ["SYSLOG", "SNMPTRAP"]),
        CaseFail("unknown-listener", ["BOGUS"]),
    ],
    "site_opentelemetry_collector": CHECKBOX_CASES,
    "site_opentelemetry_collector_delta_to_cumulative_processor": [
        CasePass("configured", {"max_stale": 600, "max_streams": 1000}),
        CaseFail("stale-below-minimum", {"max_stale": 0, "max_streams": 1000}),
        CaseFail("missing-required-keys", {}),
    ],
    "site_opentelemetry_collector_memory_limit": [
        CasePass(
            "absolute",
            {"check_interval": 5, "limit": ("absolute", {"limit": 2048, "spike_limit": 512})},
        ),
        CasePass(
            "relative",
            {"check_interval": 1, "limit": ("relative", {"limit": 75.0, "spike_limit": 25.0})},
        ),
        CaseFail(
            "spike-not-below-limit",
            {"check_interval": 1, "limit": ("relative", {"limit": 20.0, "spike_limit": 20.0})},
        ),
    ],
    "site_piggyback_hub": CHECKBOX_CASES,
    "site_subject_alternative_names": [
        CasePass("configured", ["monitoring.example.com", "10.0.0.1"]),
        CaseFail("invalid-host-address", ["host name with spaces"]),
        CaseFail("not-a-list", "monitoring.example.com"),
    ],
    "site_trace_receive": [
        CasePass("disabled", None),
        CasePass("configured", {"address": "0.0.0.0", "port": 4317}),
        CaseFail("port-below-minimum", {"address": "0.0.0.0", "port": 80}),
    ],
    "site_trace_send": [
        CasePass("no-tracing", "no_tracing"),
        CasePass("local-site", "local_site"),
        CasePass("configured", ("other_collector", {"url": "https://collector.example.com:4317"})),
        CaseFail("invalid-url", ("other_collector", {"url": "not a url"})),
        CaseFail("unknown-choice", ("bogus_choice", None)),
    ],
    "slow_views_duration_threshold": UNBOUNDED_INTEGER_CASES,
    "snmp_backend_default": [
        CasePass("configured", "classic"),
        CaseFail("not-a-choice-crashes-transform", "netsnmp", MKConfigError),
    ],
    "snmp_credentials": [
        CasePass("community", [{"description": "core switches", "credentials": "public"}]),
        CasePass(
            "v3-auth-priv",
            [
                {
                    "description": "secure devices",
                    "credentials": (
                        "authPriv",
                        "SHA-256",
                        "monitor",
                        "authpass123",
                        "AES-256",
                        "privpass123",
                    ),
                    "engine_ids": ["8000000001020304"],
                }
            ],
        ),
        CaseFail("missing-description", [{"credentials": "public"}]),
        CaseFail(
            "invalid-credential-tuple-length",
            [{"description": "broken", "credentials": ("authPriv", "SHA-256")}],
        ),
    ],
    "snmp_walk_download_timeout": MIN_ONE_AGE_CASES,
    "socket_queue_len": MIN_ONE_INTEGER_CASES,
    "soft_query_limit": MIN_ONE_INTEGER_CASES,
    "sqlite_freelist_size": [
        CasePass("configured", 10485760),
        CaseFail("below-minimum", 1024),
        CaseFail("not-an-int", "10MB"),
    ],
    "sqlite_housekeeping_interval": UNBOUNDED_AGE_CASES,
    "staleness_threshold": MIN_ONE_FLOAT_CASES,
    "start_url": [
        CasePass("configured", "dashboard.py"),
        CaseFail("absolute-url", "http://evil.example.com/"),
        CaseFail("not-a-string", 123),
    ],
    "statistics_interval": UNBOUNDED_AGE_CASES,
    "table_row_limit": MIN_ONE_INTEGER_CASES,
    "tcp_connect_timeout": MIN_ONE_FLOAT_CASES,
    "translate_snmptraps": [
        CasePass("disabled", False),
        CasePass("configured", (True, {"add_description": True})),
        CaseFail("description-not-fixed-value", (True, {"add_description": False})),
        CaseFail("not-a-choice", "yes"),
    ],
    "trusted_certificate_authorities": [
        CasePass("configured", {"use_system_wide_cas": True, "trusted_cas": []}),
        CaseFail("missing-required-keys", {"use_system_wide_cas": True}),
        CaseFail("not-a-pem", {"use_system_wide_cas": False, "trusted_cas": ["not a pem"]}),
    ],
    "ui_theme": [
        CasePass("configured", "modern-dark"),
        CaseFail("unknown-theme", "no-such-theme"),
    ],
    "use_dns_cache": CHECKBOX_CASES,
    "use_new_descriptions_for": [
        CasePass("configured", DefaultWithOverrides({"df": True, "ps": True})),
        CaseFail("missing-required-keys", {"df": True}),
        CaseFail("unknown-key", DefaultWithOverrides({"no_such_check": True})),
    ],
    "user_downtime_timeranges": [
        CasePass(
            "configured",
            [
                {"title": "2 hours", "end": 7200},
                {"title": "Until next day", "end": "next_day"},
            ],
        ),
        CaseFail("unknown-end-keyword", [{"title": "Broken", "end": "next_century"}]),
        CaseFail("missing-title", [{"end": 7200}]),
    ],
    "user_icons_and_actions": [
        CaseDirty(
            "icon-existence-check-fails-in-test-environment",
            {
                "jira": {
                    "icon": "link",
                    "title": "Open Jira",
                    "url": ("https://jira.example.com/?host=$HOSTNAME$", "_blank"),
                    "toplevel": True,
                    "sort_index": 10,
                }
            },
            MKUserError,
        ),
        CaseFail("missing-icon", {"jira": {"title": "No icon"}}),
        CaseFail("not-a-dict-crashes-transform", ["jira"], AttributeError),
    ],
    "user_localizations": [
        CasePass("configured", {"Business critical": {"en": "Important"}}),
        CaseFail("not-a-dict-crashes-transform", "Business critical", AttributeError),
    ],
    "user_security_notification_duration": [
        CasePass("configured", {"max_duration": 172800, "update_existing_duration": True}),
        CaseFail("duration-not-an-int", {"max_duration": "2d", "update_existing_duration": True}),
        CaseFail(
            "duration-below-minimum",
            {"max_duration": 600, "update_existing_duration": True},
        ),
        CaseFail("missing-required-keys", {}),
    ],
    "virtual_host_trees": [
        CasePass(
            "configured",
            [
                {
                    "id": "by_folder",
                    "title": "By folder",
                    "exclude_empty_tag_choices": True,
                    "tree_spec": ["foldertree:", "folder:1"],
                }
            ],
        ),
        CaseFail("missing-required-keys", [{"id": "by_site"}]),
        CaseFail(
            "duplicate-tree-id",
            [
                {
                    "id": "by_folder",
                    "title": "By folder",
                    "exclude_empty_tag_choices": True,
                    "tree_spec": ["foldertree:"],
                },
                {
                    "id": "by_folder",
                    "title": "By folder again",
                    "exclude_empty_tag_choices": True,
                    "tree_spec": ["foldertree:"],
                },
            ],
        ),
        CaseFail(
            "duplicate-tree-spec-element",
            [
                {
                    "id": "by_folder",
                    "title": "By folder",
                    "exclude_empty_tag_choices": True,
                    "tree_spec": ["foldertree:", "foldertree:"],
                }
            ],
        ),
        CaseFail("not-a-list", "by_site"),
    ],
    "vue_experimental_features": [
        CasePass("configured", {"rule_render_mode": "backend"}),
        CaseFail("unknown-render-mode", {"rule_render_mode": "gpu"}),
        CaseFail("missing-required-keys", {}),
    ],
    "wato_activate_changes_comment_mode": choice_cases("optional", "mandatory"),
    "wato_activation_method": choice_cases("reload", "hup"),
    "wato_hide_filenames": CHECKBOX_CASES,
    "wato_hide_folders_without_read_permissions": CHECKBOX_CASES,
    "wato_hide_hosttags": CHECKBOX_CASES,
    "wato_hide_varnames": CHECKBOX_CASES,
    "wato_icon_categories": [
        CasePass("configured", [("network", "Network")]),
        CaseFail("not-a-list", "network"),
    ],
    "wato_max_snapshots": MIN_ONE_INTEGER_CASES,
    "wato_pprint_config": CHECKBOX_CASES,
    "wato_use_git": CHECKBOX_CASES,
}


@pytest.mark.usefixtures("load_config", "patch_theme")
class ConfigVariableSuite:
    """The per-edition test suite. The edition is a property of the Bazel
    target under test, propagated via its EDITION environment variable (see
    e.g. tests/unit/cmk/gui/nonfree/pro/BUILD), so it is derived from there
    instead of being restated per edition. Each edition's test module just
    subclasses this and assigns generate_config_variable_tests to the module
    attribute pytest_generate_tests."""

    EDITION: ClassVar[Edition] = edition_from_env()

    @pytest.fixture(name="global_settings_context")
    def fixture_global_settings_context(self) -> GlobalSettingsContext:
        return make_global_settings_context(self.EDITION)

    def test_all_config_variable_defaults_round_trip_unchanged(
        self, global_settings_context: GlobalSettingsContext
    ) -> None:
        """A FormSpec variable ported with an InputHint prefill has no spec
        default at all - the effective default comes from the default config
        anyway - so there is nothing to round trip for it."""
        crashed = {}
        mutated = set()

        for config_variable in config_variable_registry.values():
            ident = config_variable.ident()
            try:
                value = default_disk_value(config_variable, global_settings_context)
                if round_trip_disk_value(config_variable, global_settings_context, value) != value:
                    mutated.add(ident)
            except MKGeneralException as e:
                if "input hint" not in str(e):
                    crashed[ident] = repr(e)
            except Exception as e:
                crashed[ident] = repr(e)

        assert crashed == {}
        assert mutated == set()

    def test_form_spec_defaults_survive_unedited_gui_save(
        self, global_settings_context: GlobalSettingsContext
    ) -> None:
        """Opening a FormSpec-backed setting in the GUI and saving without edits
        must not rewrite the stored value. Grows automatically with the FormSpec
        port. Variables ported with an InputHint prefill have no default to
        save and are skipped."""
        for config_variable in config_variable_registry.values():
            value_model = config_variable.value_model(global_settings_context)
            if not isinstance(value_model, FormSpec):
                continue
            try:
                value = default_disk_value(config_variable, global_settings_context)
            except MKGeneralException as e:
                if "input hint" in str(e):
                    continue
                raise
            assert gui_save_round_trip_disk_value(value_model, value) == value, (
                config_variable.ident()
            )

    def test_default_disk_value_unchanged(
        self, ident: str, global_settings_context: GlobalSettingsContext
    ) -> None:
        """Changing a default must be a conscious decision, made in this table
        as well: the FormSpec port of a config variable must not change it, and
        the DefaultWithOverrides cases silently shift their meaning when the
        default underneath them moves. Scalar variables need no pin, see
        is_scalar_value_model.

        Once every config variable is moved to FormSpec this restriction can be deleted."""
        pinned = DEFAULT_DISK_VALUES[ident]
        if isinstance(pinned, EditionDependentDefault):
            pinned = pinned.for_edition(self.EDITION)
        assert (
            default_disk_value(config_variable_registry[ident], global_settings_context) == pinned
        )

    def test_every_config_variable_has_cases(self) -> None:
        """Every config variable the edition registers must have cases. The
        reverse check runs only under ULTIMATEMT, the edition that registers
        every variable except the cloud-exclusive ones: an entry it cannot
        match to a registered variable is registered in no edition at all,
        i.e. a typo or a leftover of a removed variable."""
        registered = set(config_variable_registry)
        assert registered <= set(CASES), f"missing cases for: {sorted(registered - set(CASES))}"
        if self.EDITION is Edition.ULTIMATEMT:
            assert set(CASES) - registered == CLOUD_EXCLUSIVE_VARIABLES

    def test_default_pins_cover_exactly_the_non_scalar_variables(
        self, global_settings_context: GlobalSettingsContext
    ) -> None:
        """A scalar variable's default needs no pin, see is_scalar_value_model:
        the default config always wins, so a pin would only produce noise when
        that effective default moves. Every other variable must stay pinned."""
        required = set()
        forbidden = set()
        for ident, config_variable in config_variable_registry.items():
            if is_scalar_value_model(config_variable.value_model(global_settings_context)):
                forbidden.add(ident)
            else:
                required.add(ident)
        assert required <= set(DEFAULT_DISK_VALUES), (
            f"missing default pins for: {sorted(required - set(DEFAULT_DISK_VALUES))}"
        )
        assert forbidden & set(DEFAULT_DISK_VALUES) == set(), (
            f"dead pins for: {sorted(forbidden & set(DEFAULT_DISK_VALUES))}"
        )
        if self.EDITION is Edition.ULTIMATEMT:
            assert set(DEFAULT_DISK_VALUES) - set(config_variable_registry) <= (
                CLOUD_EXCLUSIVE_VARIABLES
            )

    def test_configured_disk_value_behavior(
        self, ident: str, case: Case, global_settings_context: GlobalSettingsContext
    ) -> None:
        config_variable = config_variable_registry[ident]
        context = global_settings_context
        value = resolve_case_value(config_variable, context, case.value)

        match case:
            case CasePass():
                validate_disk_value(config_variable, context, value)
                assert round_trip_disk_value(config_variable, context, value) == value
                value_model = config_variable.value_model(context)
                if isinstance(value_model, FormSpec):
                    assert gui_save_round_trip_disk_value(value_model, value) == value
            case CaseMigrates():
                expected = resolve_case_value(config_variable, context, case.expected)
                assert round_trip_disk_value(config_variable, context, value) == expected
                validate_disk_value(config_variable, context, expected)
            case CaseFail():
                with pytest.raises(case.exception):
                    validate_disk_value(config_variable, context, value)
            case CaseDirty():
                with pytest.raises(case.exception):
                    validate_disk_value(config_variable, context, value)
                assert round_trip_disk_value(config_variable, context, value) == value


def generate_config_variable_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize the suite with the case table entries the edition under test
    actually registers. The config variable registry is the single source of
    truth for edition membership, so the case tables need no per-edition
    bookkeeping. Loading the plugins at collection time is safe because
    main_modules.register is idempotent; the session-scoped load_plugins
    fixture then finds them already loaded."""
    if metafunc.cls is None or not issubclass(metafunc.cls, ConfigVariableSuite):
        return
    perform_load_plugins(metafunc.cls.EDITION)
    registered = set(config_variable_registry)
    if "case" in metafunc.fixturenames:
        metafunc.parametrize(
            "ident, case",
            [
                pytest.param(ident, case, id=f"{ident}-{case.id}")
                for ident, case_list in CASES.items()
                if ident in registered
                for case in case_list
            ],
        )
    elif "ident" in metafunc.fixturenames:
        metafunc.parametrize("ident", sorted(set(DEFAULT_DISK_VALUES) & registered))
