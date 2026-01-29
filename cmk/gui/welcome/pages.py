#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.wato.pages.user_profile.main_menu import set_user_attribute
from cmk.gui.welcome.registry import welcome_card_registry, WelcomeCardCallback
from cmk.gui.welcome.utils import WELCOME_PERMISSIONS
from cmk.shared_typing.welcome import FinishedEnum, StageInformation, WelcomeCards, WelcomePage
from cmk.utils.urls import is_allowed_url


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
    is_snapin: bool,
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
        is_snapin=is_snapin,
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
        return asdict(get_welcome_data(is_snapin=True).stage_information)


def _welcome_page(ctx: PageContext) -> None:
    make_header(
        html,
        "Welcome",
        breadcrumb=Breadcrumb(),
        show_top_heading=False,
        enable_main_page_scrollbar=False,
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

    html.vue_component(component_name="cmk-welcome", data=asdict(get_welcome_data(is_snapin=False)))

    html.footer()


def _make_url(addvars: HTTPVariables, filename: str, is_snapin: bool) -> str:
    """This ensures that the navigation is always shown"""
    if not is_snapin:
        return makeuri(
            request,
            addvars=addvars,
            filename=filename,
        )

    return makeuri(
        request,
        addvars=[("start_url", makeuri(request, addvars, filename=filename))],
        filename="index.py",
        delvars=["start_url"],
    )


def get_welcome_data(is_snapin: bool) -> WelcomePage:
    return WelcomePage(
        cards=WelcomeCards(
            add_folder=_make_url(
                addvars=[("mode", "newfolder")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            checkmk_ai="https://chat.checkmk.com",
            checkmk_forum="https://forum.checkmk.com",
            checkmk_docs=doc_reference_url(DocReference.INTRO_GUI),
            checkmk_best_practices=doc_reference_url(DocReference.INTRO_BESTPRACTICE),
            checkmk_trainings="https://checkmk.com/trainings/schedule",
            checkmk_webinars="https://checkmk.com/webinars",
            create_contactgroups=_make_url(
                addvars=[("mode", "contact_groups")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            users=_make_url(
                addvars=[("mode", "users")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            assign_host_to_contactgroups=_make_url(
                addvars=[("mode", "edit_ruleset"), ("varname", "host_contactgroups")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            setup_backup=_make_url(
                addvars=[("mode", "backup")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            scale_monitoring=doc_reference_url(DocReference.DISTRIBUTED_MONITORING),
            fine_tune_monitoring=doc_reference_url(DocReference.FINETUNING_MONITORING),
            license_site=_make_url_or_callback_from_registry(
                is_snapin=is_snapin,
                identifier="license_your_site",
            ),
            add_host=_make_url_or_callback_from_registry(
                is_snapin=is_snapin,
                identifier="add_host",
            )
            or _make_url(
                addvars=[("mode", "newhost")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            network_devices=_make_url_or_callback_from_registry(
                is_snapin=is_snapin,
                identifier="relays",
            )
            or _make_url(
                addvars=[("mode", "newhost"), ("prefill", "snmp")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            aws_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:aws"),
                ],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            azure_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:azure_v2"),
                ],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            gcp_quick_setup=_make_url(
                addvars=[
                    ("mode", "new_special_agent_configuration"),
                    ("varname", "special_agents:gcp"),
                ],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            synthetic_monitoring=_make_url_or_callback_from_registry(
                is_snapin=is_snapin,
                identifier="robotmk_managed_robots_overview",
                permitted=user.may("edit_managed_robots"),
            ),
            opentelemetry=_make_url_or_callback_from_registry(
                is_snapin=is_snapin,
                identifier="otel_collectors",
            ),
            activate_changes=_make_url(
                addvars=[("mode", "changelog")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            setup_hosts=_make_url(
                addvars=[("mode", "folder")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            main_dashboard=_make_url(
                addvars=[("name", "main")],
                filename="dashboard.py",
                is_snapin=is_snapin,
            ),
            problem_dashboard=_make_url(
                addvars=[("name", "problems")],
                filename="dashboard.py",
                is_snapin=is_snapin,
            ),
            unhandled_service_problems=_make_url(
                addvars=[("view_name", "svcproblems")],
                filename="view.py",
                is_snapin=is_snapin,
            ),
            time_periods=_make_url(
                addvars=[("mode", "timeperiods")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            host_groups=_make_url(
                addvars=[("mode", "host_groups")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            add_notification_rule=_make_url(
                addvars=[("mode", "notification_rule_quick_setup")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            test_notifications=_make_url(
                addvars=[("mode", "test_notifications")],
                filename="wato.py",
                is_snapin=is_snapin,
            ),
            add_custom_dashboard=_make_url(
                addvars=[],
                filename="dashboard.py?mode=create",
                is_snapin=is_snapin,
            ),
            all_dashboards=_make_url(
                addvars=[],
                filename="edit_dashboards.py",
                is_snapin=is_snapin,
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
        ),
        is_start_url=user.start_url == "welcome.py",
        stage_information=StageInformation(
            finished=list(_get_finished_stages()),
        ),
    )
