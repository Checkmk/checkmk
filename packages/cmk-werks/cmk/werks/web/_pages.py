#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Container
from typing import override

from cmk.discover_plugins import discover_families, PluginGroup
from cmk.utils.man_pages import make_man_page_path_map
from cmk.web.exceptions import MKUserError
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
from cmk.web.pages import Page, PageContext
from cmk.web.utils.escaping import escape_to_html_permissive
from cmk.web.utils.html import HTML
from cmk.web.utils.urls import make_contextless_url
from cmk.werks.site import load_werk_entries
from cmk.werks.site.acknowledgement import is_acknowledged, load_acknowledgements
from cmk.werks.tool.models import Compatibility, WerkV3
from cmk.werks.tool.utils import WerkTranslator

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
_ACKNOWLEDGE_PERMISSION = "general.acknowledge_werks"
# Icon id from cmk.shared_typing.icon.IconNames.werk_ack; cmk.web menu icons are
# plain strings that the cmk.gui composer maps back to its icon types.
_WERK_ACK_ICON = "werk-ack"


class WerkDetailPage(Page):
    """Renders the detail view of a single werk."""

    @override
    def page(self, ctx: PageContext) -> PageContainer:
        _ = ctx.i18n
        werk = _get_werk_by_id(ctx.request.get_integer_input_mandatory("werk"), _)
        acknowledged_ids = load_acknowledgements()
        translator = WerkTranslator()

        title = "{} {} - {}".format(_("Werk"), _render_werk_id(werk), werk.title)

        builder = HtmlBuilder()
        builder.open_table(class_=["data", "headerleft", "werks"])
        _row(builder, _("ID"), _render_werk_id(werk))
        _row(builder, _("Title"), HtmlBuilder.render_b(_render_werk_title(werk)))
        _row(builder, _("Component"), translator.component_of(werk))
        _row(builder, _("Date"), werk.date.astimezone().strftime(_TIME_FORMAT))
        _row(builder, _("Checkmk version"), werk.version)
        _row(
            builder,
            _("Level"),
            translator.level_of(werk),
            css="werklevel werklevel%d" % werk.level.value,
        )
        _row(
            builder,
            _("Class"),
            translator.class_of(werk),
            css="werkclass werkclass%s" % werk.level.value,
        )
        acknowledged = is_acknowledged(werk, acknowledged_ids)
        _row(
            builder,
            _("Compatibility"),
            _compatibility_of(werk.compatible, acknowledged, _),
            css="werkcomp werkcomp%s" % _to_ternary_compatibility(werk, acknowledged),
        )
        _row(
            builder,
            _("Description"),
            HTML.without_escaping(werk.description),  # TODO: remove nowiki
            css="nowiki",
        )
        builder.close_table()

        return PageContainer(
            title=title,
            breadcrumb=[
                BreadcrumbItem(_("Change log (Werks)"), "change_log.py"),
                BreadcrumbItem(title),
            ],
            content=builder.render(),
            page_menu=_page_menu(ctx, werk, acknowledged),
        )


def _row(
    builder: HtmlBuilder, caption: HTMLContent, content: HTMLContent, css: str | None = None
) -> None:
    builder.open_tr()
    builder.th(caption)
    builder.td(content, class_=css)
    builder.close_tr()


def _page_menu(ctx: PageContext, werk: WerkV3, acknowledged: bool) -> PageContainerMenu:
    entries: list[PageMenuLink] = []
    if ctx.user.may(_ACKNOWLEDGE_PERMISSION):
        entries.append(
            PageMenuLink(
                title=ctx.i18n("Acknowledge"),
                icon_name=_WERK_ACK_ICON,
                url=ctx.make_action_url([("_werk_ack", werk.id)], filename="change_log.py"),
                is_enabled=not acknowledged,
                is_shortcut=True,
                is_suggested=True,
            )
        )
    return PageContainerMenu(
        dropdowns=[
            PageMenuDropdown(
                name="werk",
                title="Werk",
                topics=[PageMenuTopic(title=ctx.i18n("Incompatible werk"), entries=entries)],
            ),
        ],
    )


def _get_werk_by_id(werk_id: int, _: Callable[[str], str]) -> WerkV3:
    for werk in load_werk_entries():
        if werk.id == werk_id:
            return werk
    raise MKUserError("werk", _("This Werk does not exist."))


def _render_werk_id(werk: WerkV3) -> str:
    return "#%04d" % werk.id


def _render_werk_title(werk: WerkV3) -> HTML:
    title = werk.title
    # If the title begins with the name(s) of check plug-ins, link to their man pages.
    if ":" in title:
        parts = title.split(":", 1)
        return _insert_manpage_links(parts[0]) + escape_to_html_permissive(":" + parts[1])
    return escape_to_html_permissive(title)


def _insert_manpage_links(text: str) -> HTML:
    known_checks = _get_known_checks()
    new_parts: list[HTML] = []
    for part in text.replace(",", " ").split():
        if part in known_checks:
            url = make_contextless_url("wato.py", [("mode", "check_manpage"), ("check_type", part)])
            new_parts.append(HtmlBuilder.render_a(content=part, href=url))
        else:
            new_parts.append(HTML.with_escaping(part))
    return HTML.without_escaping(" ").join(new_parts)


def _get_known_checks() -> Container[str]:
    return make_man_page_path_map(discover_families(raise_errors=False), PluginGroup.CHECKMAN.value)


def _compatibility_of(
    compatible: Compatibility, acknowledged: bool, _: Callable[[str], str]
) -> str:
    compatibilities = {
        (Compatibility.COMPATIBLE, False): _("Compatible"),
        (Compatibility.NOT_COMPATIBLE, True): _("Incompatible"),
        (Compatibility.NOT_COMPATIBLE, False): _("Incompatible - TODO"),
        # compatible and acknowledged should not be possible, but the GUI crawler hit that case:
        (Compatibility.COMPATIBLE, True): _("Compatible"),
    }
    return compatibilities[(compatible, acknowledged)]


def _to_ternary_compatibility(werk: WerkV3, acknowledged: bool) -> str:
    if werk.compatible == Compatibility.NOT_COMPATIBLE:
        return "incomp_ack" if acknowledged else "incomp_unack"
    return "compat"
