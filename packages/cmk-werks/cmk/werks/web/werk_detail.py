#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Container

from cmk.web.htmllib.builder import HtmlBuilder
from cmk.web.htmllib.tag_rendering import HTMLContent
from cmk.web.page_container import (
    BreadcrumbItem,
    PageContainer,
    PageContainerMenu,
    PageMenuDropdown,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.web.utils.escaping import escape_to_html_permissive
from cmk.web.utils.html import HTML
from cmk.web.utils.urls import make_contextless_url
from cmk.werks.tool.models import Compatibility, WerkV3
from cmk.werks.tool.utils import WerkTranslator

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
# Icon id from cmk.shared_typing.icon.IconNames.werk_ack; cmk.web menu icons are
# plain strings that the cmk.gui composer maps back to its icon types.
_WERK_ACK_ICON = "werk-ack"


def _row(
    builder: HtmlBuilder, caption: HTMLContent, content: HTMLContent, css: str | None = None
) -> None:
    builder.open_tr()
    builder.th(caption)
    builder.td(content, class_=css)
    builder.close_tr()


def _render_werk_id(werk: WerkV3) -> str:
    return "#%04d" % werk.id


def _insert_manpage_links(text: str, known_checks: Container[str]) -> HTML:
    new_parts: list[HTML] = []
    for part in text.replace(",", " ").split():
        if part in known_checks:
            url = make_contextless_url("wato.py", [("mode", "check_manpage"), ("check_type", part)])
            new_parts.append(HtmlBuilder.render_a(content=part, href=url))
        else:
            new_parts.append(HTML.with_escaping(part))
    return HTML.without_escaping(" ").join(new_parts)


def _render_werk_title(werk: WerkV3, known_checks: Callable[[], Container[str]]) -> HTML:
    title = werk.title
    if ":" in title:
        check_plugins, rest = title.split(":", 1)
        return _insert_manpage_links(check_plugins, known_checks()) + escape_to_html_permissive(
            ":" + rest
        )
    return escape_to_html_permissive(title)


def _compatibility_of(
    compatible: Compatibility, acknowledged: bool, i18n: Callable[[str], str]
) -> str:
    compatibilities = {
        (Compatibility.COMPATIBLE, False): i18n("Compatible"),
        (Compatibility.NOT_COMPATIBLE, True): i18n("Incompatible"),
        (Compatibility.NOT_COMPATIBLE, False): i18n("Incompatible - TODO"),
        (Compatibility.COMPATIBLE, True): i18n("Compatible"),
    }
    return compatibilities[(compatible, acknowledged)]


def _to_ternary_compatibility(werk: WerkV3, acknowledged: bool) -> str:
    if werk.compatible == Compatibility.NOT_COMPATIBLE:
        return "incomp_ack" if acknowledged else "incomp_unack"
    return "compat"


def _page_menu(
    werk_acknowledged: bool, acknowledge_url: str | None, i18n: Callable[[str], str]
) -> PageContainerMenu:
    entries = (
        []
        if acknowledge_url is None
        else [
            PageMenuLink(
                title=i18n("Acknowledge"),
                icon_name=_WERK_ACK_ICON,
                url=acknowledge_url,
                is_enabled=not werk_acknowledged,
                is_shortcut=True,
                is_suggested=True,
            )
        ]
    )
    return PageContainerMenu(
        dropdowns=[
            PageMenuDropdown(
                name="werk",
                title="Werk",
                topics=[PageMenuTopic(title=i18n("Incompatible werk"), entries=entries)],
            ),
        ],
    )


def render_werk_detail(
    werk: WerkV3,
    *,
    acknowledged: bool,
    acknowledge_url: str | None,
    known_checks: Callable[[], Container[str]],
    i18n: Callable[[str], str],
) -> PageContainer:
    translator = WerkTranslator()

    title = "{} {} - {}".format(i18n("Werk"), _render_werk_id(werk), werk.title)

    builder = HtmlBuilder()
    builder.open_table(class_=["data", "headerleft", "werks"])
    _row(builder, i18n("ID"), _render_werk_id(werk))
    _row(builder, i18n("Title"), HtmlBuilder.render_b(_render_werk_title(werk, known_checks)))
    _row(builder, i18n("Component"), translator.component_of(werk))
    _row(builder, i18n("Date"), werk.date.astimezone().strftime(_TIME_FORMAT))
    _row(builder, i18n("Checkmk version"), werk.version)
    _row(
        builder,
        i18n("Level"),
        translator.level_of(werk),
        css="werklevel werklevel%d" % werk.level.value,
    )
    _row(
        builder,
        i18n("Class"),
        translator.class_of(werk),
        css="werkclass werkclass%s" % werk.class_.value,
    )
    _row(
        builder,
        i18n("Compatibility"),
        _compatibility_of(werk.compatible, acknowledged, i18n),
        css="werkcomp werkcomp%s" % _to_ternary_compatibility(werk, acknowledged),
    )
    _row(
        builder,
        i18n("Description"),
        HTML.without_escaping(werk.description),  # TODO: remove nowiki
        css="nowiki",
    )
    builder.close_table()

    return PageContainer(
        title=title,
        breadcrumb=[
            BreadcrumbItem(i18n("Change log (Werks)"), "change_log.py"),
            BreadcrumbItem(title),
        ],
        content=builder.render(),
        page_menu=_page_menu(acknowledged, acknowledge_url, i18n),
    )
