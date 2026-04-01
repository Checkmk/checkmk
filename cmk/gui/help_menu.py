#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc.version import __version__, edition
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.main_menu_types import MainMenuItem
from cmk.gui.type_defs import IconNames
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri_contextless
from cmk.gui.welcome.utils import WELCOME_PERMISSIONS
from cmk.licensing.registry import get_license_message
from cmk.shared_typing.main_menu import (
    ColorEnum,
    DefaultIcon,
    EmblemIcon,
    HeaderTriggerModeEnum,
    NavItemHeader,
    NavItemHeaderTriggerButton,
    NavItemIdEnum,
    NavItemShortcut,
    NavItemTopic,
    NavItemTopicEntry,
    TopicItemMode,
)
from cmk.utils import paths


def register(
    main_menu_registry: MainMenuRegistry,
    info_line: Callable[[], str],
    learning_entries: Callable[[], list[NavItemTopicEntry]],
    developer_entries: Callable[[], list[NavItemTopicEntry]],
    about_checkmk_entries: Callable[[], list[NavItemTopicEntry]],
) -> None:
    main_menu_registry.register(
        MainMenuItem(
            id=NavItemIdEnum.help,
            title=_l("Help"),
            sort_index=18,
            get_topics=_help_menu_topics(
                learning_entries, developer_entries, about_checkmk_entries
            ),
            shortcut=NavItemShortcut(key="h", alt=True),
            is_user_nav=True,
            info_line=info_line,
            popup_small=True,
            header=NavItemHeader(
                trigger_button=NavItemHeaderTriggerButton(
                    mode=HeaderTriggerModeEnum.unack_incomp_werks,
                    color=ColorEnum.danger,
                    target_url=makeuri_contextless(request, vars_=[], filename="change_log.py"),
                ),
            ),
            hint=_l("Docs, references and guides"),
        )
    )


def default_info_line() -> str:
    return f"{edition(paths.omd_root).title} {__version__}{_license_status()}"


def default_learning_entries() -> list[NavItemTopicEntry]:
    entries: list[NavItemTopicEntry] = [
        NavItemTopicEntry(
            id="beginners_guide",
            title=_("Beginner's Guide"),
            url=doc_reference_url(user.language, DocReference.INTRO_SETUP),
            target="_blank",
            sort_index=20,
            icon=DefaultIcon(id=IconNames.learning_beginner),
        ),
        NavItemTopicEntry(
            id="user_manual",
            title=_("User Guide"),
            url=doc_reference_url(user.language),
            target="_blank",
            sort_index=30,
            icon=DefaultIcon(id=IconNames.learning_guide),
        ),
        NavItemTopicEntry(
            id="video_tutorials",
            title=_("Video tutorials"),
            url="https://www.youtube.com/playlist?list=PL8DfRO2DvOK1slgjfTu0hMOnepf1F7ssh",
            target="_blank",
            sort_index=40,
            icon=DefaultIcon(id=IconNames.learning_video_tutorials),
        ),
        NavItemTopicEntry(
            id="community_forum",
            title=_("Community forum"),
            url="https://forum.checkmk.com/",
            target="_blank",
            sort_index=50,
            icon=DefaultIcon(id=IconNames.learning_forum),
        ),
        NavItemTopicEntry(
            id="ask_checkmk_ai",
            title=_("Ask Checkmk AI"),
            url="https://chat.checkmk.com",
            target="_blank",
            sort_index=60,
            icon=DefaultIcon(id=IconNames.sparkle),
        ),
    ]
    if all(user.may(perm) for perm in WELCOME_PERMISSIONS):
        return [
            *entries,
            NavItemTopicEntry(
                id="welcome_page",
                title=_("Welcome page"),
                url="welcome.py",
                sort_index=10,
                icon=DefaultIcon(id=IconNames.learning_beginner),
            ),
        ]
    return [*entries]


def default_developer_entries() -> list[NavItemTopicEntry]:
    return [
        NavItemTopicEntry(
            id="plugin_api_introduction",
            title=_("Check plug-in API introduction"),
            url=doc_reference_url(user.language, DocReference.DEVEL_CHECK_PLUGINS),
            target="_blank",
            sort_index=10,
            icon=EmblemIcon(
                icon=DefaultIcon(id=IconNames.services_green),
                emblem="api",
            ),
        ),
        NavItemTopicEntry(
            id="plugin_api_reference",
            title=_("Plug-in API references"),
            url="plugin-api/",
            target="_blank",
            sort_index=20,
            icon=EmblemIcon(
                icon=DefaultIcon(id=IconNames.services_green),
                emblem="api",
            ),
        ),
        rest_api_menu_items(),
    ]


def rest_api_menu_items() -> NavItemTopicEntry:
    return NavItemTopicEntry(
        mode=TopicItemMode.multilevel,
        id="rest_api",
        title=_("REST API"),
        sort_index=30,
        entries=[
            NavItemTopicEntry(
                id="rest_api_introduction",
                title=_("Introduction"),
                url=doc_reference_url(user.language, DocReference.REST_API),
                target="_blank",
                sort_index=10,
                icon=EmblemIcon(
                    icon=DefaultIcon(id=IconNames.global_settings),
                    emblem="api",
                ),
            ),
            NavItemTopicEntry(
                mode=TopicItemMode.indented,
                id="rest_api_version_1",
                title=_("Version 1"),
                sort_index=20,
                entries=[
                    NavItemTopicEntry(
                        id="rest_api_documentation",
                        title=_("Documentation"),
                        url="openapi/",
                        target="_blank",
                        sort_index=10,
                        icon=EmblemIcon(
                            icon=DefaultIcon(id=IconNames.global_settings),
                            emblem="api",
                        ),
                    ),
                    NavItemTopicEntry(
                        id="rest_api_interactive_gui",
                        title=_("Interactive GUI"),
                        url="api/1.0/ui/",
                        target="_blank",
                        sort_index=20,
                        icon=EmblemIcon(
                            icon=DefaultIcon(id=IconNames.global_settings),
                            emblem="api",
                        ),
                    ),
                ],
            ),
            NavItemTopicEntry(
                mode=TopicItemMode.indented,
                id="rest_api_unstable",
                title=_("Unstable"),
                sort_index=30,
                entries=[
                    NavItemTopicEntry(
                        id="rest_api_unstable_documentation",
                        title=_("Documentation"),
                        url="api/unstable/doc/",
                        target="_blank",
                        sort_index=10,
                        icon=EmblemIcon(
                            icon=DefaultIcon(id=IconNames.global_settings),
                            emblem="api",
                        ),
                    ),
                ],
            ),
        ],
        icon=EmblemIcon(
            icon=DefaultIcon(id=IconNames.global_settings),
            emblem="api",
        ),
    )


def default_about_checkmk_entries() -> list[NavItemTopicEntry]:
    return [
        NavItemTopicEntry(
            id="change_log",
            title=_("Change log (Werks)"),
            url="change_log.py",
            sort_index=30,
            icon=DefaultIcon(id=IconNames.checkmk_logo_min),
        ),
        NavItemTopicEntry(
            id="product_usage_analytics_manifest",
            title=_("Product usage analytics manifest"),
            url="https://analytics.checkmk.com/manifest",
            target="_blank",
            sort_index=40,
            icon=DefaultIcon(id=IconNames.checkmk_logo_min),
        ),
    ]


def _help_menu_topics(
    learning_entries: Callable[[], list[NavItemTopicEntry]],
    developer_entries: Callable[[], list[NavItemTopicEntry]],
    about_checkmk_entries: Callable[[], list[NavItemTopicEntry]],
) -> Callable[[UserPermissions], list[NavItemTopic]]:
    def _fun(user_permissions: UserPermissions) -> list[NavItemTopic]:
        return [
            NavItemTopic(
                id="learning_checkmk",
                title=_("Learning Checkmk"),
                icon=DefaultIcon(id=IconNames.learning_checkmk),
                entries=learning_entries(),
                sort_index=10,
            ),
            NavItemTopic(
                id="developer_resources",
                title=_("Developer resources"),
                icon=DefaultIcon(id=IconNames.developer_resources),
                entries=developer_entries(),
                sort_index=20,
            ),
            NavItemTopic(
                id="ideas_portal",
                title=_("Ideas portal"),
                icon=DefaultIcon(id=IconNames.lightbulb),
                entries=[
                    NavItemTopicEntry(
                        id="suggest_product_improvement",
                        title=_("Suggest a product improvement"),
                        url="https://ideas.checkmk.com",
                        target="_blank",
                        sort_index=10,
                        icon=DefaultIcon(id=IconNames.lightbulb_idea),
                    ),
                ],
                sort_index=30,
            ),
            NavItemTopic(
                id="about_checkmk",
                title=_("About Checkmk"),
                icon=DefaultIcon(id=IconNames.about_checkmk),
                entries=about_checkmk_entries(),
                sort_index=40,
            ),
        ]

    return _fun


def _license_status() -> HTML | str:
    status_message: HTML | str = get_license_message(paths.omd_root)
    if not status_message:
        return ""
    if user.may("wato.licensing"):
        status_message = HTMLWriter.render_a(
            status_message,
            makeuri_contextless(request, [("mode", "licensing")], filename="wato.py"),
            target="main",
        )
    return HTMLWriter.render_br() + status_message
