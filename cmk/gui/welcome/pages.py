#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri

from cmk.shared_typing.welcome import WelcomePage, WelcomeUrls


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("welcome", _welcome_page))


def _welcome_page(config: Config) -> None:
    make_header(html, "Welcome", breadcrumb=Breadcrumb(), show_top_heading=False)
    html.vue_component(
        component_name="cmk-welcome",
        data=asdict(
            WelcomePage(
                urls=WelcomeUrls(
                    checkmk_ai="https://chat.checkmk.com",
                    checkmk_forum="https://forum.checkmk.com",
                    checkmk_docs=doc_reference_url(),
                    create_contactgoups=makeuri(
                        request,
                        addvars=[("mode", "contact_groups")],
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
                    # TODO: prefill options
                    network_devices=makeuri(
                        request,
                        addvars=[("mode", "newhost")],
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
                    synthetic_monitoring=makeuri(
                        request,
                        addvars=[
                            ("mode", "robotmk_managed_robots_overview"),
                        ],
                        filename="wato.py",
                    ),
                    opentelemetry="",
                    # TODO: add again with CMK-24147, currently is breaks the GUI crawler
                    # makeuri(
                    #     request,
                    #     addvars=[
                    #         ("mode", "otel_collectors"),
                    #     ],
                    #     filename="wato.py",
                    # ),
                    all_hosts=makeuri(
                        request,
                        addvars=[("view_name", "allhosts")],
                        filename="view.py",
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
            )
        ),
    )
