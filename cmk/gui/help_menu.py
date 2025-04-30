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
from cmk.gui.main_menu import MegaMenuRegistry
from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri_contextless


def register(
    mega_menu_registry: MegaMenuRegistry,
    info_line: Callable[[], str],
    learning_items: Callable[[], list[TopicMenuItem]],
    developer_items: Callable[[], list[TopicMenuItem]],
    about_checkmk_items: Callable[[], list[TopicMenuItem]],
) -> None:
    mega_menu_registry.register(
        MegaMenu(
            name="help_links",
            title=_l("Help"),
            icon="main_help",
            sort_index=18,
            topics=_help_menu_topics(learning_items, developer_items, about_checkmk_items),
            info_line=info_line,
        )
    )


def default_info_line() -> str:
    return f"{edition(paths.omd_root).title} {__version__}{_license_status()}"


def default_learning_items() -> list[TopicMenuItem]:
    return [
        TopicMenuItem(
            name="beginners_guide",
            title=_("Beginner's guide"),
            url=doc_reference_url(DocReference.INTRO_SETUP),
            target="_blank",
            sort_index=20,
            icon="learning_beginner",
        ),
        TopicMenuItem(
            name="user_manual",
            title=_("User manual"),
            url=doc_reference_url(),
            target="_blank",
            sort_index=30,
            icon="learning_guide",
        ),
        TopicMenuItem(
            name="video_tutorials",
            title=_("Video tutorials"),
            url="https://www.youtube.com/playlist?list=PL8DfRO2DvOK1slgjfTu0hMOnepf1F7ssh",
            target="_blank",
            sort_index=40,
            icon="learning_video_tutorials",
        ),
        TopicMenuItem(
            name="community_forum",
            title=_("Community forum"),
            url="https://forum.checkmk.com/",
            target="_blank",
            sort_index=50,
            icon="learning_forum",
        ),
    ]


def default_developer_items() -> list[TopicMenuItem]:
    return [
        TopicMenuItem(
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
        TopicMenuItem(
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
        TopicMenuItem(
            name="rest_api_introduction",
            title=_("REST API introduction"),
            url=doc_reference_url(DocReference.REST_API),
            target="_blank",
            sort_index=30,
            icon={
                "icon": "global_settings",
                "emblem": "api",
            },
        ),
        TopicMenuItem(
            name="rest_api_documentation",
            title=_("REST API documentation"),
            url="openapi/",
            target="_blank",
            sort_index=40,
            icon={
                "icon": "global_settings",
                "emblem": "api",
            },
        ),
        TopicMenuItem(
            name="rest_api_interactive_gui",
            title=_("REST API interactive GUI"),
            url="api/1.0/ui/",
            target="_blank",
            sort_index=50,
            icon={
                "icon": "global_settings",
                "emblem": "api",
            },
        ),
    ]


def default_about_checkmk_items() -> list[TopicMenuItem]:
    return [
        TopicMenuItem(
            name="change_log",
            title=_("Change log (Werks)"),
            url="change_log.py",
            sort_index=30,
            icon="checkmk_logo_min",
        ),
    ]


def _help_menu_topics(
    learning_items: Callable[[], list[TopicMenuItem]],
    developer_items: Callable[[], list[TopicMenuItem]],
    about_checkmk_items: Callable[[], list[TopicMenuItem]],
) -> Callable[[], list[TopicMenuTopic]]:
    def _fun() -> list[TopicMenuTopic]:
        return [
            TopicMenuTopic(
                name="learning_checkmk",
                title=_("Learning Checkmk"),
                icon="learning_checkmk",
                items=learning_items(),
            ),
            TopicMenuTopic(
                name="developer_resources",
                title=_("Developer resources"),
                icon="developer_resources",
                items=developer_items(),
            ),
            TopicMenuTopic(
                name="ideas_portal",
                title=_("Ideas Portal"),
                icon="lightbulb",
                items=[
                    TopicMenuItem(
                        name="suggest_product_improvement",
                        title=_("Suggest a product improvement"),
                        url="https://ideas.checkmk.com",
                        target="_blank",
                        sort_index=10,
                        icon="lightbulb_idea",
                    ),
                ],
            ),
            TopicMenuTopic(
                name="about_checkmk",
                title=_("About Checkmk"),
                icon="about_checkmk",
                items=about_checkmk_items(),
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
