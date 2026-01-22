#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Raw edition and only raw edition specific registrations"""

import cmk.gui.wato._notification_parameter._mail as mail
from cmk.ccc.version import Edition
from cmk.gui import login, nagvis, sidebar, visuals
from cmk.gui.background_job import job_registry
from cmk.gui.backup.registration import backup_register
from cmk.gui.common_registration import register as common_registration
from cmk.gui.cron import cron_job_registry
from cmk.gui.custom_icons.registration import custom_icons_register
from cmk.gui.customer import customer_api_registry, CustomerAPIStub
from cmk.gui.dashboard import (
    builtin_dashboard_extender_registry,
    BuiltinDashboardExtender,
    dashlet_registry,
    noop_builtin_dashboard_extender,
)
from cmk.gui.data_source import data_source_registry
from cmk.gui.features import Features, features_registry
from cmk.gui.graphing import community_registration as graphing_community_registration
from cmk.gui.graphing_main import PageHostServiceGraphPopup
from cmk.gui.help_menu import (
    default_about_checkmk_entries,
    default_developer_entries,
    default_info_line,
    default_learning_entries,
)
from cmk.gui.ldap_integration.register import register as ldap_registration
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.mkeventd import registration as mkeventd_registration
from cmk.gui.mkeventd.helpers import save_active_config
from cmk.gui.openapi import (
    endpoint_family_registry,
    endpoint_registry,
    versioned_endpoint_registry,
)
from cmk.gui.openapi.endpoints import autocomplete
from cmk.gui.openapi.endpoints import metric as metric_endpoint
from cmk.gui.pages import page_registry, PageEndpoint
from cmk.gui.painter.v0 import painter_registry
from cmk.gui.painter_options import painter_option_registry
from cmk.gui.permissions import permission_registry, permission_section_registry
from cmk.gui.quick_setup.v0_unstable._registry import quick_setup_registry
from cmk.gui.search import match_item_generator_registry
from cmk.gui.sidebar import snapin_registry
from cmk.gui.sites import site_choices
from cmk.gui.token_auth import token_authenticated_page_registry
from cmk.gui.userdb import user_attribute_registry, user_connector_registry
from cmk.gui.utils import agent_commands, plugins
from cmk.gui.utils.agent_commands import agent_commands_registry
from cmk.gui.utils.rule_specs.legacy_converter import (
    convert_dictionary_formspec_to_valuespec,
)
from cmk.gui.valuespec import autocompleter_registry
from cmk.gui.views import graph
from cmk.gui.views.builtin_views import (
    builtin_view_extender_registry,
    BuiltinViewExtender,
    noop_builtin_view_extender,
)
from cmk.gui.views.command import command_group_registry, command_registry
from cmk.gui.views.icon import icon_and_action_registry
from cmk.gui.views.layout import layout_registry
from cmk.gui.views.row_post_processing import row_post_processor_registry
from cmk.gui.views.sorter import sorter_registry
from cmk.gui.visuals import default_site_filter_heading_info
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry
from cmk.gui.wato import default_user_menu_topics
from cmk.gui.wato import registration as wato_registration
from cmk.gui.wato.pages import roles
from cmk.gui.watolib import network_scan
from cmk.gui.watolib.activate_changes import (
    activation_features_registry,
    ActivationFeatures,
    default_rabbitmq_definitions,
)
from cmk.gui.watolib.analyze_configuration import ac_test_registry
from cmk.gui.watolib.automation_commands import automation_command_registry
from cmk.gui.watolib.broker_certificates import (
    broker_certificate_sync_registry,
    DefaultBrokerCertificateSync,
)
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    config_variable_group_registry,
    config_variable_registry,
    sample_config_generator_registry,
)
from cmk.gui.watolib.config_sync import replication_path_registry
from cmk.gui.watolib.groups import contact_group_usage_finder_registry
from cmk.gui.watolib.host_attributes import (
    host_attribute_registry,
    host_attribute_topic_registry,
)
from cmk.gui.watolib.host_rename import rename_host_hook_registry
from cmk.gui.watolib.hosts_and_folders import folder_validators_registry
from cmk.gui.watolib.main_menu import main_module_registry, main_module_topic_registry
from cmk.gui.watolib.mode import mode_registry
from cmk.gui.watolib.notification_parameter import (
    notification_parameter_registry,
    NotificationParameter,
)
from cmk.gui.watolib.piggyback_hub import distribute_piggyback_hub_configs
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry
from cmk.gui.watolib.sample_config import SampleConfigGeneratorGroups
from cmk.gui.watolib.simple_config_file import config_file_registry
from cmk.gui.watolib.sites import site_management_registry, SiteManagement
from cmk.gui.watolib.snapshots import make_cre_snapshot_manager
from cmk.gui.watolib.timeperiods import timeperiod_usage_finder_registry
from cmk.gui.watolib.users import default_sites, user_features_registry, UserFeatures


def register_pages() -> None:
    page_registry.register(PageEndpoint("host_service_graph_popup", PageHostServiceGraphPopup()))


def register_painters() -> None:
    painter_registry.register(graph.PainterServiceGraphs)
    painter_registry.register(graph.PainterHostGraphs)
    painter_registry.register(graph.PainterSvcPnpgraph)
    painter_registry.register(graph.PainterHostPnpgraph)


def register(edition: Edition, *, ignore_duplicate_endpoints: bool = False) -> None:
    sample_config_generator_registry.register(SampleConfigGeneratorGroups)
    network_scan.register(host_attribute_registry, automation_command_registry, cron_job_registry)
    nagvis.register(permission_section_registry, permission_registry, snapin_registry)
    roles.register(mode_registry)
    login.register(page_registry)
    common_registration(
        main_menu_registry,
        job_registry,
        permission_section_registry,
        permission_registry,
        sorter_registry,
        painter_option_registry,
        painter_registry,
        page_registry,
        command_registry,
        visual_type_registry,
        row_post_processor_registry,
        visual_info_registry,
        filter_registry,
        rulespec_registry,
        config_variable_group_registry,
        mode_registry,
        main_module_registry,
        config_variable_registry,
        rulespec_group_registry,
        icon_and_action_registry,
        cron_job_registry,
        dashlet_registry,
        contact_group_usage_finder_registry,
        autocompleter_registry,
        data_source_registry,
        config_domain_registry,
        timeperiod_usage_finder_registry,
        automation_command_registry,
        main_module_topic_registry,
        snapin_registry,
        match_item_generator_registry,
        sample_config_generator_registry,
        host_attribute_registry,
        host_attribute_topic_registry,
        replication_path_registry,
        endpoint_registry,
        versioned_endpoint_registry,
        endpoint_family_registry,
        user_connector_registry,
        layout_registry,
        config_file_registry,
        rename_host_hook_registry,
        command_group_registry,
        folder_validators_registry,
        user_attribute_registry,
        quick_setup_registry,
        default_info_line,
        default_learning_entries,
        default_developer_entries,
        default_about_checkmk_entries,
        token_authenticated_page_registry,
        ignore_duplicate_endpoints=ignore_duplicate_endpoints,
    )

    ldap_registration(
        mode_registry,
        endpoint_registry,
        ac_test_registry,
        user_connector_registry,
        ignore_duplicate_endpoints,
    )

    features_registry.register(
        Features(
            edition,
            livestatus_only_sites_postprocess=lambda x: list(x) if x else None,
        )
    )
    customer_api_registry.register(CustomerAPIStub(str(edition)))
    visuals.register(
        page_registry,
        visual_info_registry,
        filter_registry,
        autocompleter_registry,
        site_choices,
        default_site_filter_heading_info,
        endpoint_family_registry,
        versioned_endpoint_registry,
        ignore_duplicate_endpoints=ignore_duplicate_endpoints,
    )
    sidebar.register(
        page_registry,
        permission_section_registry,
        snapin_registry,
        dashlet_registry,
        main_menu_registry,
        view_menu_topics=sidebar.default_view_menu_topics,
    )
    wato_registration.register(
        page_registry,
        painter_registry,
        sorter_registry,
        icon_and_action_registry,
        automation_command_registry,
        job_registry,
        filter_registry,
        mode_registry,
        quick_setup_registry,
        permission_section_registry,
        permission_registry,
        main_module_topic_registry,
        main_module_registry,
        rulespec_group_registry,
        config_domain_registry,
        config_variable_registry,
        config_variable_group_registry,
        snapin_registry,
        match_item_generator_registry,
        main_menu_registry,
        ac_test_registry,
        contact_group_usage_finder_registry,
        notification_parameter_registry,
        replication_path_registry,
        default_user_menu_topics,
    )
    user_features_registry.register(
        UserFeatures(
            edition=edition,
            sites=default_sites,
        )
    )
    activation_features_registry.register(
        ActivationFeatures(
            edition,
            sync_file_filter_func=None,
            snapshot_manager_factory=make_cre_snapshot_manager,
            get_rabbitmq_definitions=default_rabbitmq_definitions,
            distribute_piggyback_hub_configs=distribute_piggyback_hub_configs,
        )
    )
    broker_certificate_sync_registry.register(DefaultBrokerCertificateSync())

    site_management_registry.register(SiteManagement())
    notification_parameter_registry.register(
        NotificationParameter(
            ident="mail",
            spec=lambda: convert_dictionary_formspec_to_valuespec(mail.form_spec_mail),
            form_spec=mail.form_spec_mail,
        )
    )
    register_pages()
    register_painters()
    backup_register(
        page_registry,
        mode_registry,
        main_module_registry,
    )
    mkeventd_registration.register(
        permission_section_registry,
        permission_registry,
        data_source_registry,
        painter_registry,
        command_registry,
        sorter_registry,
        icon_and_action_registry,
        config_domain_registry,
        sample_config_generator_registry,
        mode_registry,
        main_module_registry,
        config_variable_group_registry,
        config_variable_registry,
        rulespec_group_registry,
        rulespec_registry,
        autocompleter_registry,
        filter_registry,
        notification_parameter_registry,
        snapin_registry,
        contact_group_usage_finder_registry,
        timeperiod_usage_finder_registry,
        endpoint_registry,
        replication_path_registry,
        save_active_config,
        ignore_duplicate_endpoints=ignore_duplicate_endpoints,
    )
    custom_icons_register(
        mode_registry,
        main_module_registry,
        permission_registry,
    )
    _openapi_registration(ignore_duplicates=ignore_duplicate_endpoints)
    builtin_dashboard_extender_registry.register(
        BuiltinDashboardExtender(str(edition), noop_builtin_dashboard_extender)
    )
    builtin_view_extender_registry.register(
        BuiltinViewExtender(str(edition), noop_builtin_view_extender)
    )
    agent_commands.register(agent_commands_registry)
    graphing_community_registration.register(
        edition,
        page_registry,
        config_variable_registry,
        autocompleter_registry,
    )
    plugins.register()


def _openapi_registration(*, ignore_duplicates: bool) -> None:
    autocomplete.register(endpoint_registry, ignore_duplicates=ignore_duplicates)
    metric_endpoint.register(endpoint_registry, ignore_duplicates=ignore_duplicates)
