#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.top_heading import show_license_banner, show_license_expiry
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    DocReferenceUtm,
    is_allowed_url,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.wato.pages.user_profile.main_menu import set_user_attribute
from cmk.gui.welcome.registry import welcome_card_registry, WelcomeCardCallback
from cmk.gui.welcome.utils import WELCOME_PERMISSIONS
from cmk.shared_typing.welcome import FinishedEnum, StageInformation, WelcomeCards, WelcomePage


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("welcome", _welcome_page))
    page_registry.register(PageEndpoint("ajax_mark_step_as_complete", _ajax_mark_step_as_complete))
    page_registry.register(
        PageEndpoint("ajax_get_welcome_page_stage_information", PageWelcomePageStageInformation())
    )


def _get_finished_stages() -> Generator[FinishedEnum]:
    if "add_host" in user.welcome_completed_steps:
        yield FinishedEnum.add_host

    if "activate_changes" in user.welcome_completed_steps:
        yield FinishedEnum.activate_changes

    if "adjust_services" in user.welcome_completed_steps:
        yield FinishedEnum.adjust_services

    if "assign_responsibilities" in user.welcome_completed_steps:
        yield FinishedEnum.assign_responsibilities

    if "enable_notifications" in user.welcome_completed_steps:
        yield FinishedEnum.enable_notifications

    if "create_dashboard" in user.welcome_completed_steps:
        yield FinishedEnum.create_dashboard


def _make_url_or_callback_from_registry(
    identifier: str,
    permitted: bool = True,
) -> str | None:
    url = welcome_card_registry.get(identifier)
    if url is None or not permitted:
        return None

    if isinstance(url, WelcomeCardCallback):
        return url.callback_id

    return _make_url(
        addvars=url.vars,
        filename=url.filename,
    )


def _ajax_mark_step_as_complete(ctx: PageContext) -> None:
    # Handle step completion if completed-step parameter is provided
    if completed_step_name := request.get_ascii_input("_completed_step"):
        if completed_step_name in FinishedEnum:
            completed_steps = user.welcome_completed_steps
            completed_steps.add(completed_step_name)
            user.welcome_completed_steps = completed_steps


class PageWelcomePageStageInformation(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        return asdict(get_welcome_data().stage_information)


def _welcome_page(ctx: PageContext) -> None:
    make_header(
        html,
        "Welcome",
        breadcrumb=Breadcrumb(),
        show_top_heading=False,
        enable_main_page_scrollbar=False,
        debug=ctx.config.debug,
        lang=user.language,
        inject_js_profiling_code=ctx.config.inject_js_profiling_code,
        load_frontend_vue=ctx.config.load_frontend_vue,
        custom_style_sheet=ctx.config.custom_style_sheet,
        screenshotmode=ctx.config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
        hide_suggestions=not user.get_tree_state("suggestions", "all", True),
        user_role_ids=user.role_ids,
    )
    if not all(user.may(perm) for perm in WELCOME_PERMISSIONS):
        set_user_attribute("start_url", None)
        default_start_url = user.start_url or ctx.config.start_url
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

    html.open_div(id_="welcome_expiry")
    show_license_expiry(html, user.role_ids)
    html.close_div()

    html.open_div(id_="welcome_titlebar")
    show_license_banner(html, user.role_ids)
    html.close_div()

    html.vue_component(component_name="cmk-welcome", data=asdict(get_welcome_data()))

    html.footer()


def _make_url(addvars: HTTPVariables, filename: str) -> str:
    return makeuri(request, addvars=addvars, filename=filename)


def get_welcome_data() -> WelcomePage:
    return WelcomePage(
        cards=WelcomeCards(
            add_folder=_make_url(
                addvars=[("mode", "newfolder")],
                filename="wato.py",
            ),
            checkmk_ai="https://chat.checkmk.com",
            checkmk_forum="https://forum.checkmk.com",
            checkmk_docs=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.intro_gui"),
                DocReference.INTRO_GUI,
            ),
            checkmk_best_practices=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.best_practices"),
                DocReference.INTRO_BESTPRACTICE,
            ),
            checkmk_trainings="https://checkmk.com/trainings/schedule",
            checkmk_webinars="https://checkmk.com/webinars",
            create_contactgroups=_make_url(
                addvars=[("mode", "contact_groups")],
                filename="wato.py",
            ),
            users=_make_url(
                addvars=[("mode", "users")],
                filename="wato.py",
            ),
            assign_host_to_contactgroups=_make_url(
                addvars=[("mode", "edit_ruleset"), ("varname", "host_contactgroups")],
                filename="wato.py",
            ),
            setup_backup=_make_url(
                addvars=[("mode", "backup")],
                filename="wato.py",
            ),
            setup_folder_structure=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.hosts_structure"),
                DocReference.HOSTS_STRUCTURE,
            ),
            start_page=_make_url(
                addvars=[],
                filename="user_profile.py",
            ),
            scale_monitoring=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.distributed_monitoring"),
                DocReference.DISTRIBUTED_MONITORING,
            ),
            fine_tune_monitoring=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.finetune_monitoring"),
                DocReference.FINETUNING_MONITORING,
            ),
            license_site=_make_url_or_callback_from_registry(
                identifier="license_your_site",
            ),
            add_host=_make_url_or_callback_from_registry(
                identifier="add_host",
            )
            or _make_url(
                addvars=[("mode", "newhost")],
                filename="wato.py",
            ),
            network_devices=_make_url_or_callback_from_registry(
                identifier="network_devices",
            ),
            relays=_make_url_or_callback_from_registry(
                identifier="relays",
            ),
            aws_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:aws"),
                ],
                filename="wato.py",
            ),
            azure_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:azure_v2"),
                ],
                filename="wato.py",
            ),
            gcp_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:gcp"),
                ],
                filename="wato.py",
            ),
            synthetic_monitoring=_make_url_or_callback_from_registry(
                identifier="robotmk_managed_robots_overview",
                permitted=user.may("edit_managed_robots"),
            ),
            # TODO Readd if target is implemented, see CMK-31599
            # opentelemetry=_make_url_or_callback_from_registry(
            #    identifier="otel_collectors",
            # ),
            activate_changes=_make_url(
                addvars=[("mode", "changelog")],
                filename="wato.py",
            ),
            setup_hosts=_make_url(
                addvars=[("mode", "folder")],
                filename="wato.py",
            ),
            main_dashboard=_make_url(
                addvars=[("name", "main")],
                filename="dashboard.py",
            ),
            problem_dashboard=_make_url(
                addvars=[("name", "problems")],
                filename="dashboard.py",
            ),
            unhandled_service_problems=_make_url(
                addvars=[("view_name", "svcproblems")],
                filename="view.py",
            ),
            time_periods=_make_url(
                addvars=[("mode", "timeperiods")],
                filename="wato.py",
            ),
            host_groups=_make_url(
                addvars=[("mode", "host_groups")],
                filename="wato.py",
            ),
            add_notification_rule=_make_url(
                addvars=[("mode", "notification_rule_quick_setup")],
                filename="wato.py",
            ),
            test_notifications=_make_url(
                addvars=[("mode", "test_notifications")],
                filename="wato.py",
            ),
            add_custom_dashboard=_make_url(
                addvars=[("mode", "create")],
                filename="dashboard.py",
            ),
            all_dashboards=_make_url(
                addvars=[],
                filename="edit_dashboards.py",
            ),
            mark_step_completed=makeuri(
                request,
                addvars=[],
                filename="ajax_mark_step_as_complete.py",
            ),
            get_stage_information=makeuri(
                request,
                addvars=[],
                filename="ajax_get_welcome_page_stage_information.py",
            ),
            intro_users=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.users"),
                DocReference.INTRO_USERS,
            ),
            intro_notifications=doc_reference_url(
                user.language,
                DocReferenceUtm(campaign="setup_wizard", content="welcome.notifications"),
                DocReference.INTRO_NOTIFICATIONS,
            ),
        ),
        is_start_url=user.start_url == "welcome.py",
        stage_information=StageInformation(
            finished=list(_get_finished_stages()),
        ),
    )
