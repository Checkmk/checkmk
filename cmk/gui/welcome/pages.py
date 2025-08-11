#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from dataclasses import asdict

from cmk.gui import sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.dashboard.store import get_all_dashboards
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri, makeuri_contextless
from cmk.gui.wato.pages.user_profile.main_menu import set_user_attribute
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.rulesets import SingleRulesetRecursively
from cmk.gui.watolib.sample_config import get_default_notification_rule
from cmk.gui.welcome.registry import welcome_url_registry
from cmk.shared_typing.welcome import FinishedEnum, StageInformation, WelcomePage, WelcomeUrls
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.notify_types import EventRule
from cmk.utils.urls import is_allowed_url


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("welcome", _welcome_page))


def _compare_notification_rules(
    notification_rule_1: EventRule,
    notification_rule_2: EventRule,
) -> bool:
    return {k: v for k, v in notification_rule_1.items() if k != "rule_id"} == {
        k: v for k, v in notification_rule_2.items() if k != "rule_id"
    }


def _get_finished_stages() -> Generator[FinishedEnum]:
    # Creation of first host
    if any(Host.all()):
        yield FinishedEnum.add_host

    # Activation of the host
    if Query([Hosts.name]).fetchall(sites=sites.live()):
        yield FinishedEnum.adjust_services

    collection = SingleRulesetRecursively.load_single_ruleset_recursively(name="host_contactgroups")
    if len(collection.get("host_contactgroups").get_rules()) > 0:
        yield FinishedEnum.assign_responsibilities

    notification_rules = NotificationRuleConfigFile().load_for_reading()
    # Creation of a new notification rule
    if len(notification_rules) > 1:
        yield FinishedEnum.enable_notifications
    # Adjusted the built-in notification rule
    if len(notification_rules) == 1 and not _compare_notification_rules(
        notification_rules[0], get_default_notification_rule()
    ):
        yield FinishedEnum.enable_notifications

    # Creation of a custom dashboard
    for user_id, _dashboard_name in get_all_dashboards().keys():
        if user_id == user.id:
            yield FinishedEnum.customize_dashboard
            break


def make_url_from_registry(identifier: str, permitted: bool = True) -> str | None:
    url = welcome_url_registry.get(identifier)
    if url is None or not permitted:
        return None
    return makeuri(
        request,
        addvars=url.vars,
        filename=url.filename,
    )


WELCOME_PAGE_PERMISSIONS = {
    "wato.use",
    "wato.hosts",
    "wato.edit",
    "wato.manage_hosts",
    "wato.service_discovery_to_undecided",
    "wato.service_discovery_to_monitored",
    "wato.service_discovery_to_ignored",
    "wato.service_discovery_to_removed",
    "wato.download_agents",
    "wato.download_all_agents",
    "wato.activate",
    "wato.timeperiods",
    "wato.groups",
    "wato.notifications",
    "general.force_dashboards",
    "general.edit_dashboards",
    "general.see_user_dashboards",
    "general.see_packaged_dashboards",
}


def _welcome_page(config: Config) -> None:
    make_header(
        html,
        "Welcome",
        breadcrumb=Breadcrumb(),
        show_top_heading=False,
        enable_main_page_scrollbar=False,
    )
    if not all(user.may(perm) for perm in WELCOME_PAGE_PERMISSIONS):
        set_user_attribute("start_url", None)
        default_start_url = user.start_url or config.start_url
        if not is_allowed_url(default_start_url):
            default_start_url = "dashboard.py"
        html.immediate_browser_redirect(
            0.1,
            makeuri_contextless(
                request,
                [],
                filename=default_start_url,
            ),
        )
        return

    html.vue_component(component_name="cmk-welcome", data=asdict(get_welcome_data()))


def get_welcome_data() -> WelcomePage:
    return WelcomePage(
        urls=WelcomeUrls(
            checkmk_ai="https://chat.checkmk.com",
            checkmk_forum="https://forum.checkmk.com",
            checkmk_docs=doc_reference_url(),
            create_contactgroups=makeuri(
                request,
                addvars=[("mode", "contact_groups")],
                filename="wato.py",
            ),
            users=makeuri(
                request,
                addvars=[("mode", "users")],
                filename="wato.py",
            ),
            assign_host_to_contactgroups=makeuri(
                request,
                addvars=[("mode", "edit_ruleset"), ("varname", "host_contactgroups")],
                filename="wato.py",
            ),
            setup_backup=makeuri(
                request,
                addvars=[("mode", "backup")],
                filename="wato.py",
            ),
            scale_monitoring=doc_reference_url(DocReference.DISTRIBUTED_MONITORING),
            fine_tune_monitoring=doc_reference_url(DocReference.FINETUNING_MONITORING),
            license_site=makeuri(
                request,
                addvars=[("mode", "licensing")],
                filename="wato.py",
            ),
            add_host=makeuri(
                request,
                addvars=[("mode", "newhost")],
                filename="wato.py",
            ),
            network_devices=makeuri(
                request,
                addvars=[("mode", "newhost"), ("prefill", "snmp")],
                filename="wato.py",
            ),
            aws_quick_setup=makeuri(
                request,
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:aws"),
                ],
                filename="wato.py",
            ),
            azure_quick_setup=makeuri(
                request,
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:azure"),
                ],
                filename="wato.py",
            ),
            gcp_quick_setup=makeuri(
                request,
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:gcp"),
                ],
                filename="wato.py",
            ),
            synthetic_monitoring=make_url_from_registry(
                "robotmk_managed_robots_overview", user.may("edit_managed_robots")
            ),
            opentelemetry=make_url_from_registry("otel_collectors"),
            activate_changes=makeuri(
                request,
                addvars=[("mode", "changelog")],
                filename="wato.py",
            ),
            setup_hosts=makeuri(
                request,
                addvars=[("mode", "folder")],
                filename="wato.py",
            ),
            main_dashboard=makeuri(
                request,
                addvars=[("name", "main")],
                filename="dashboard.py",
            ),
            problem_dashboard=makeuri(
                request,
                addvars=[("name", "problems")],
                filename="dashboard.py",
            ),
            unhandled_service_problems=makeuri(
                request,
                addvars=[("view_name", "svcproblems")],
                filename="view.py",
            ),
            time_periods=makeuri(
                request,
                addvars=[("mode", "timeperiods")],
                filename="wato.py",
            ),
            host_groups=makeuri(
                request,
                addvars=[("mode", "host_groups")],
                filename="wato.py",
            ),
            add_notification_rule=makeuri(
                request,
                addvars=[("mode", "notification_rule_quick_setup")],
                filename="wato.py",
            ),
            test_notifications=makeuri(
                request,
                addvars=[("mode", "test_notifications")],
                filename="wato.py",
            ),
            add_custom_dashboard=makeuri(
                request,
                addvars=[],
                filename="create_dashboard.py",
            ),
            all_dashboards=makeuri(
                request,
                addvars=[],
                filename="edit_dashboards.py",
            ),
        ),
        is_start_url=user.start_url == "welcome.py",
        stage_information=StageInformation(
            finished=list(_get_finished_stages()),
        ),
    )
