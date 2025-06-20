#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc.version import __version__, edition

from cmk.utils import paths
from cmk.utils.licensing.registry import get_license_message

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.type_defs import (
    MainMenu,
    MainMenuItem,
    MainMenuTopic,
    MainMenuTopicEntries,
    MainMenuTopicSegment,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri_contextless


def register(
    main_menu_registry: MainMenuRegistry,
    info_line: Callable[[], str],
    learning_entries: Callable[[], MainMenuTopicEntries],
    developer_entries: Callable[[], MainMenuTopicEntries],
    about_checkmk_entries: Callable[[], MainMenuTopicEntries],
) -> None:
    main_menu_name = "help"
    main_menu_registry.register(
        MainMenu(
            name=main_menu_name,
            title=_l("Help"),
            icon="main_help",
            sort_index=18,
            topics=_help_menu_topics(learning_entries, developer_entries, about_checkmk_entries),
            info_line=info_line,
            onopen=f'cmk.popup_menu.main_menu_reset_default_expansion("{main_menu_name}");',
        )
    )


def default_info_line() -> str:
    return f"{edition(paths.omd_root).title} {__version__}{_license_status()}"


def default_learning_entries() -> MainMenuTopicEntries:
    return [
        MainMenuItem(
            name="getting_started",
            title=_("Getting started"),
            url="welcome.py",
            sort_index=10,
            icon="learning_beginner",
        ),
        MainMenuItem(
            name="beginners_guide",
            title=_("Beginner's guide"),
            url=doc_reference_url(DocReference.INTRO_SETUP),
            target="_blank",
            sort_index=20,
            icon="learning_beginner",
        ),
        MainMenuItem(
            name="user_manual",
            title=_("User manual"),
            url=doc_reference_url(),
            target="_blank",
            sort_index=30,
            icon="learning_guide",
        ),
        MainMenuItem(
            name="video_tutorials",
            title=_("Video tutorials"),
            url="https://www.youtube.com/playlist?list=PL8DfRO2DvOK1slgjfTu0hMOnepf1F7ssh",
            target="_blank",
            sort_index=40,
            icon="learning_video_tutorials",
        ),
        MainMenuItem(
            name="community_forum",
            title=_("Community forum"),
            url="https://forum.checkmk.com/",
            target="_blank",
            sort_index=50,
            icon="learning_forum",
        ),
        MainMenuItem(
            name="ask_checkmk_ai",
            title=_("Ask Checkmk AI"),
            url="https://chat.checkmk.com",
            target="_blank",
            sort_index=60,
            icon="sparkle",
        ),
    ]


def default_developer_entries() -> MainMenuTopicEntries:
    return [
        MainMenuItem(
            name="plugin_api_introduction",
            title=_("Check plug-in API introduction"),
            url=doc_reference_url(DocReference.DEVEL_CHECK_PLUGINS),
            target="_blank",
            sort_index=10,
            icon={
                "icon": "services_green",
                "emblem": "api",
            },
        ),
        MainMenuItem(
            name="plugin_api_reference",
            title=_("Plug-in API references"),
            url="plugin-api/",
            target="_blank",
            sort_index=20,
            icon={
                "icon": "services_green",
                "emblem": "api",
            },
        ),
        MainMenuTopicSegment(
            mode="multilevel",
            name="rest_api",
            title=_("REST API"),
            sort_index=30,
            entries=[
                MainMenuItem(
                    name="rest_api_introduction",
                    title=_("Introduction"),
                    url=doc_reference_url(DocReference.REST_API),
                    target="_blank",
                    sort_index=10,
                    icon={
                        "icon": "global_settings",
                        "emblem": "api",
                    },
                ),
                MainMenuTopicSegment(
                    mode="indented",
                    name="rest_api_version_1",
                    title=_("Version 1"),
                    sort_index=20,
                    entries=[
                        MainMenuItem(
                            name="rest_api_documentation",
                            title=_("Documentation"),
                            url="openapi/",
                            target="_blank",
                            sort_index=10,
                            icon={
                                "icon": "global_settings",
                                "emblem": "api",
                            },
                        ),
                        MainMenuItem(
                            name="rest_api_interactive_gui",
                            title=_("Interactive GUI"),
                            url="api/1.0/ui/",
                            target="_blank",
                            sort_index=20,
                            icon={
                                "icon": "global_settings",
                                "emblem": "api",
                            },
                        ),
                    ],
                ),
            ],
            icon={
                "icon": "global_settings",
                "emblem": "api",
            },
        ),
    ]


def default_about_checkmk_entries() -> MainMenuTopicEntries:
    return [
        MainMenuItem(
            name="change_log",
            title=_("Change log (Werks)"),
            url="change_log.py",
            sort_index=30,
            icon="checkmk_logo_min",
        ),
    ]


def _help_menu_topics(
    learning_entries: Callable[[], MainMenuTopicEntries],
    developer_entries: Callable[[], MainMenuTopicEntries],
    about_checkmk_entries: Callable[[], MainMenuTopicEntries],
) -> Callable[[], list[MainMenuTopic]]:
    def _fun() -> list[MainMenuTopic]:
        return [
            MainMenuTopic(
                name="learning_checkmk",
                title=_("Learning Checkmk"),
                icon="learning_checkmk",
                entries=learning_entries(),
            ),
            MainMenuTopic(
                name="developer_resources",
                title=_("Developer resources"),
                icon="developer_resources",
                entries=developer_entries(),
            ),
            MainMenuTopic(
                name="ideas_portal",
                title=_("Ideas Portal"),
                icon="lightbulb",
                entries=[
                    MainMenuItem(
                        name="suggest_product_improvement",
                        title=_("Suggest a product improvement"),
                        url="https://ideas.checkmk.com",
                        target="_blank",
                        sort_index=10,
                        icon="lightbulb_idea",
                    ),
                ],
            ),
            MainMenuTopic(
                name="about_checkmk",
                title=_("About Checkmk"),
                icon="about_checkmk",
                entries=about_checkmk_entries(),
            ),
        ]

    return _fun


def _license_status() -> HTML | str:
    status_message: HTML | str = get_license_message()
    if not status_message:
        return ""
    if user.may("wato.licensing"):
        status_message = HTMLWriter.render_a(
            status_message,
            makeuri_contextless(request, [("mode", "licensing")], filename="wato.py"),
            target="main",
        )
    return HTMLWriter.render_br() + status_message
