#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Functions for parsing Werks and showing the users a browsable change
# log

import itertools
import os
import re
import time
from typing import Any, Dict, Iterator, List, Union

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.werks
from cmk.utils.version import __version__, Edition, Version

import cmk.gui.pages
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_main_menu_breadcrumb,
    make_simple_page_breadcrumb,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.num_split import cmp_version
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.utils.escaping import escape_to_html, escape_to_html_permissive
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.theme import theme
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_link, makeactionuri, makeuri, makeuri_contextless
from cmk.gui.valuespec import DropdownChoice, Integer, ListChoice, TextInput, Timerange, Tuple

acknowledgement_path = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"

# Keep global variable for caching werks between requests. The never change.
g_werks: Dict[int, Dict[str, Any]] = {}


@cmk.gui.pages.page_registry.register_page("info")
class ModeAboutCheckmkPage(cmk.gui.pages.Page):
    def _title(self) -> str:
        return _("About Checkmk")

    def page(self) -> cmk.gui.pages.PageResult:  # pylint: disable=useless-return
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry["help_links"], _("Info"))
        make_header(
            html,
            self._title(),
            breadcrumb=breadcrumb,
        )

        html.open_div(id_="info_title")
        html.h1(_("Your monitoring machine"))
        html.a(
            HTMLWriter.render_img(theme.url("images/tribe29.svg")),
            "https://tribe29.com",
            target="_blank",
        )
        html.close_div()

        html.div(None, id_="info_underline")

        html.open_div(id_="info_intro_text")
        html.span(_("Open. Effective. Awesome."))
        html.span(
            _(
                "May we present? Monitoring as it's supposed to be: "
                "incredibly quick to install, infinetely scalable, highly customizable and "
                "designed for admins."
            )
        )
        html.span(
            _("Visit our %s to learn more about Checkmk and about the %s.")
            % (
                HTMLWriter.render_a(_("website"), "https://checkmk.com", target="_blank"),
                HTMLWriter.render_a(
                    _("latest version"),
                    "https://checkmk.com/product/latest-version",
                    target="_blank",
                ),
            )
        )
        html.close_div()

        version_major_minor = re.sub(r".\d+$", "", Version(__version__).version_base)
        if version_major_minor:
            current_version_link = "https://checkmk.com/product/checkmk-%s" % version_major_minor
        else:
            current_version_link = "https://checkmk.com/product/latest-version"

        html.open_div(id="info_image")
        html.open_a(href=current_version_link, target="_blank")
        html.img(theme.url("images/monitoring-machine.png"))
        html.close_a()
        html.close_div()

        html.close_div()

        html.open_div(id_="info_footer")
        html.span(_("© %s tribe29 GmbH. All Rights Reserved.") % time.strftime("%Y"))
        html.a(_("License agreement"), href="https://checkmk.com/legal.html", target="_blank")
        html.close_div()
        return None


@cmk.gui.pages.page_registry.register_page("change_log")
class ModeChangeLogPage(cmk.gui.pages.Page):
    def _title(self) -> str:
        return _("Change log (Werks)")

    def page(self) -> cmk.gui.pages.PageResult:  # pylint: disable=useless-return
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry["help_links"], self._title())

        load_werks()
        werk_table_options = _werk_table_options_from_request()

        make_header(
            html,
            self._title(),
            breadcrumb,
            self._page_menu(breadcrumb, werk_table_options),
        )

        for message in get_flashed_messages():
            html.show_message(message)

        handle_acknowledgement()

        html.open_div(class_="wato")
        render_werks_table(werk_table_options)
        html.close_div()

        html.footer()
        return None

    def _page_menu(self, breadcrumb: Breadcrumb, werk_table_options: Dict[str, Any]) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="werks",
                    title=_("Werks"),
                    topics=[
                        PageMenuTopic(
                            title=_("Incompatible werks"),
                            entries=list(_page_menu_entries_ack_all_werks()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        _extend_display_dropdown(menu, werk_table_options)
        return menu


def handle_acknowledgement():
    if not transactions.check_transaction():
        return

    if request.var("_werk_ack"):
        werk_id = request.get_integer_input_mandatory("_werk_ack")
        if werk_id not in g_werks:
            raise MKUserError("werk", _("This werk does not exist."))
        werk = g_werks[werk_id]

        if werk["compatible"] == "incomp_unack":
            acknowledge_werk(werk)
            html.show_message(
                _("Werk %s - %s has been acknowledged.")
                % (render_werk_id(werk, with_link=True), render_werk_title(werk))
            )
            load_werks()  # reload ack states after modification
            render_unacknowleged_werks()

    elif request.var("_ack_all"):
        num = len(unacknowledged_incompatible_werks())
        acknowledge_all_werks()
        flash(_("%d incompatible Werks have been acknowledged.") % num)
        load_werks()  # reload ack states after modification
        html.reload_whole_page()


def _page_menu_entries_ack_all_werks() -> Iterator[PageMenuEntry]:
    if not may_acknowledge():
        return

    yield PageMenuEntry(
        title=_("Acknowledge all"),
        icon_name="werk_ack",
        is_shortcut=True,
        is_suggested=True,
        item=make_simple_link(
            make_confirm_link(
                url=makeactionuri(request, transactions, [("_ack_all", "1")]),
                message=_("Do you really want to acknowledge <b>all</b> incompatible werks?"),
            )
        ),
        is_enabled=bool(unacknowledged_incompatible_werks()),
    )


def _extend_display_dropdown(menu, werk_table_options: Dict[str, Any]) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Filter"),
            entries=[
                PageMenuEntry(
                    title=_("Filter"),
                    icon_name="filter",
                    item=PageMenuSidePopup(_render_werk_options_form(werk_table_options)),
                    name="filters",
                    is_shortcut=True,
                ),
            ],
        ),
    )


def _render_werk_options_form(werk_table_options: Dict[str, Any]) -> HTML:
    with output_funnel.plugged():
        html.begin_form("werks")
        html.hidden_field("wo_set", "set")

        _show_werk_options_controls()

        html.open_div(class_="side_popup_content")
        for name, height, vs, _default_value in _werk_table_option_entries():

            def renderer(name=name, vs=vs, werk_table_options=werk_table_options) -> None:
                vs.render_input("wo_" + name, werk_table_options[name])

            html.render_floating_option(name, height, vs.title(), renderer)
        html.close_div()

        html.hidden_fields()
        html.end_form()

        return HTML(output_funnel.drain())


def _show_werk_options_controls() -> None:
    html.open_div(class_="side_popup_controls")

    html.open_div(class_="update_buttons")
    html.button("apply", _("Apply"), "submit")
    html.buttonlink(makeuri(request, [], remove_prefix=""), _("Reset"))
    html.close_div()

    html.close_div()


@cmk.gui.pages.register("werk")
def page_werk():
    load_werks()
    werk_id = request.get_integer_input_mandatory("werk")
    if werk_id not in g_werks:
        raise MKUserError("werk", _("This werk does not exist."))
    werk = g_werks[werk_id]

    title = ("%s %s - %s") % (_("Werk"), render_werk_id(werk, with_link=False), werk["title"])

    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry["help_links"])
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Change log (Werks)"),
            url="change_log.py",
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    make_header(html, title, breadcrumb, _page_menu_werk(breadcrumb, werk))

    html.open_table(class_=["data", "headerleft", "werks"])

    def werk_table_row(caption, content, css=None):
        html.open_tr()
        html.th(caption)
        html.td(content, class_=css)
        html.close_tr()

    translator = cmk.utils.werks.WerkTranslator()
    werk_table_row(_("ID"), render_werk_id(werk, with_link=False))
    werk_table_row(_("Title"), HTMLWriter.render_b(render_werk_title(werk)))
    werk_table_row(_("Component"), translator.component_of(werk))
    werk_table_row(_("Date"), render_werk_date(werk))
    werk_table_row(_("Checkmk Version"), werk["version"])
    werk_table_row(
        _("Level"), translator.level_of(werk), css="werklevel werklevel%d" % werk["level"]
    )
    werk_table_row(
        _("Class"), translator.class_of(werk), css="werkclass werkclass%s" % werk["class"]
    )
    werk_table_row(
        _("Compatibility"),
        translator.compatibility_of(werk),
        css="werkcomp werkcomp%s" % werk["compatible"],
    )
    werk_table_row(_("Description"), render_werk_description(werk), css="nowiki")

    html.close_table()

    html.footer()


def _page_menu_werk(breadcrumb: Breadcrumb, werk: Dict[str, Any]):
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="Werk",
                title="Werk",
                topics=[
                    PageMenuTopic(
                        title=_("Incompatible werk"),
                        entries=list(_page_menu_entries_ack_werk(werk)),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


def _page_menu_entries_ack_werk(werk: Dict[str, Any]) -> Iterator[PageMenuEntry]:
    if not may_acknowledge():
        return

    ack_url = makeactionuri(
        request, transactions, [("_werk_ack", werk["id"])], filename="change_log.py"
    )
    yield PageMenuEntry(
        title=_("Acknowledge"),
        icon_name="werk_ack",
        item=make_simple_link(ack_url),
        is_enabled=werk["compatible"] == "incomp_unack",
        is_shortcut=True,
        is_suggested=True,
    )


def load_werks():
    global g_werks
    if not g_werks:
        g_werks = cmk.utils.werks.load()

    ack_ids = load_acknowledgements()
    for werk in g_werks.values():
        if werk["compatible"] in ["incomp", "incomp_unack"]:
            if werk["id"] in ack_ids or werk_is_pre_127(werk):
                werk["compatible"] = "incomp_ack"
            else:
                werk["compatible"] = "incomp_unack"


def may_acknowledge():
    return user.may("general.acknowledge_werks")


def acknowledge_werk(werk):
    acknowledge_werks([werk])


def acknowledge_werks(werks, check_permission=True):
    if check_permission:
        user.need_permission("general.acknowledge_werks")

    ack_ids = load_acknowledgements()
    for werk in werks:
        ack_ids.append(werk["id"])
        werk["compatible"] = "incomp_ack"
    save_acknowledgements(ack_ids)


def save_acknowledgements(acknowledged_werks):
    store.save_object_to_file(acknowledgement_path, acknowledged_werks)


def acknowledge_all_werks(check_permission=True):
    load_werks()
    acknowledge_werks(unacknowledged_incompatible_werks(), check_permission)


def werk_is_pre_127(werk):
    return werk["version"].startswith("1.2.5") or werk["version"].startswith("1.2.6")


def load_acknowledgements():
    return store.load_object_from_file(acknowledgement_path, default=[])


def unacknowledged_incompatible_werks():
    return cmk.utils.werks.sort_by_date(
        werk for werk in g_werks.values() if werk["compatible"] == "incomp_unack"  #
    )


def num_unacknowledged_incompatible_werks():
    load_werks()
    return len(unacknowledged_incompatible_werks())


def _werk_table_option_entries():
    translator = cmk.utils.werks.WerkTranslator()
    return [
        (
            "classes",
            "double",
            ListChoice(
                title=_("Classes"),
                choices=sorted(translator.classes()),
            ),
            ["feature", "fix", "security"],
        ),
        (
            "levels",
            "double",
            ListChoice(
                title=_("Levels"),
                choices=sorted(translator.levels()),
            ),
            [1, 2, 3],
        ),
        ("date", "double", Timerange(title=_("Date")), ("date", (1383149313, int(time.time())))),
        (
            "id",
            "single",
            TextInput(
                title=_("Werk ID"),
                label="#",
                regex="^[0-9]{1,5}$",
                size=7,
            ),
            "",
        ),
        (
            "compatibility",
            "single",
            DropdownChoice(
                title=_("Compatibility"),
                choices=[
                    (
                        ["compat", "incomp_ack", "incomp_unack"],
                        _("Compatible and incompatible Werks"),
                    ),
                    (["compat"], _("Compatible Werks")),
                    (["incomp_ack", "incomp_unack"], _("Incompatible Werks")),
                    (["incomp_unack"], _("Unacknowledged incompatible Werks")),
                    (["incomp_ack"], _("Acknowledged incompatible Werks")),
                ],
            ),
            ["compat", "incomp_ack", "incomp_unack"],
        ),
        (
            "component",
            "single",
            DropdownChoice(
                title=_("Component"),
                choices=[
                    (None, _("All components")),
                ]
                + sorted(translator.components()),
            ),
            None,
        ),
        (
            "edition",
            "single",
            DropdownChoice(
                title=_("Edition"),
                choices=[
                    (None, _("All editions")),
                    *(
                        (e.short, _("Werks only concerning the %s") % e.title)
                        for e in (Edition.CPE, Edition.CME, Edition.CEE, Edition.CRE)
                    ),
                ],
            ),
            None,
        ),
        (
            "werk_content",
            "single",
            TextInput(
                title=_("Werk title or content"),
                size=41,
            ),
            "",
        ),
        (
            "version",
            "single",
            Tuple(
                title=_("Checkmk Version"),
                orientation="float",
                elements=[
                    TextInput(label=_("from:"), size=12),
                    TextInput(label=_("to:"), size=12),
                ],
            ),
            (Version(__version__).version_base, ""),
        ),
        (
            "grouping",
            "single",
            DropdownChoice(
                title=_("Group Werks by"),
                choices=[
                    ("version", _("Checkmk Version")),
                    ("day", _("Day of creation")),
                    ("week", _("Week of creation")),
                    (None, _("Do not group")),
                ],
            ),
            "version",
        ),
        (
            "group_limit",
            "single",
            Integer(
                title=_("Show number of groups"),
                unit=_("groups"),
                minvalue=1,
            ),
            50,
        ),
    ]


def render_unacknowleged_werks():
    werks = unacknowledged_incompatible_werks()
    if werks and not request.has_var("show_unack"):
        html.open_div(class_=["warning"])
        html.write_text(
            _("<b>Warning:</b> There are %d unacknowledged incompatible werks:") % len(werks)
        )
        html.br()
        html.br()
        html.a(
            _("Show unacknowledged incompatible werks"),
            href=makeuri_contextless(request, [("show_unack", "1"), ("wo_compatibility", "3")]),
        )
        html.close_div()


# NOTE: The sorter and the grouping function should better agree, otherwise chaos will ensue...
_SORT_AND_GROUP = {
    "version": (cmk.utils.werks.sort_by_version_and_component, lambda werk: werk["version"]),  #
    "day": (
        cmk.utils.werks.sort_by_date,
        lambda werk: time.strftime("%Y-%m-%d", time.localtime(werk["date"])),  #
    ),
    "week": (
        cmk.utils.werks.sort_by_date,
        lambda werk: time.strftime("%s %%U - %%Y" % _("Week"), time.localtime(werk["date"])),  #
    ),
    None: (cmk.utils.werks.sort_by_date, lambda _werk: None),  #
}


def render_werks_table(werk_table_options: Dict[str, Any]):
    translator = cmk.utils.werks.WerkTranslator()
    number_of_werks = 0
    sorter, grouper = _SORT_AND_GROUP[werk_table_options["grouping"]]
    werklist = sorter(
        werk for werk in g_werks.values() if werk_matches_options(werk, werk_table_options)  #
    )
    groups = itertools.groupby(werklist, key=grouper)
    for group_title, werks in itertools.islice(groups, werk_table_options["group_limit"]):
        with table_element(
            title=group_title, limit=None, searchable=False, sortable=False, css="werks"
        ) as table:
            for werk in werks:
                number_of_werks += 1
                render_werks_table_row(table, translator, werk)
    if not number_of_werks:
        html.h3(_("No matching Werks found."))


def render_werks_table_row(table, translator, werk):
    table.row()
    table.cell(_("ID"), render_werk_id(werk, with_link=True), css="number narrow")
    table.cell(_("Version"), werk["version"], css="number narrow")
    table.cell(_("Date"), render_werk_date(werk), css="number narrow")
    table.cell(_("Class"), translator.class_of(werk), css="werkclass werkclass%s" % werk["class"])
    table.cell(_("Level"), translator.level_of(werk), css="werklevel werklevel%d" % werk["level"])
    table.cell(
        _("Compatibility"),
        translator.compatibility_of(werk),
        css="werkcomp werkcomp%s" % werk["compatible"],
    )
    table.cell(_("Component"), translator.component_of(werk), css="nowrap")
    table.cell(_("Title"), render_werk_title(werk))


def werk_matches_options(werk, werk_table_options):
    # TODO: Fix this silly typing chaos below!
    # check if werk id is int because valuespec is TextInput
    # else, set empty id to return all results beside input warning
    try:
        werk_to_match: Union[int, str] = int(werk_table_options["id"])
    except ValueError:
        werk_to_match = ""

    if not (
        (not werk_to_match or werk["id"] == werk_to_match)
        and werk["level"] in werk_table_options["levels"]
        and werk["class"] in werk_table_options["classes"]
        and werk["compatible"] in werk_table_options["compatibility"]
        and werk_table_options["component"] in (None, werk["component"])
        and werk["date"] >= werk_table_options["date_range"][0]
        and werk["date"] <= werk_table_options["date_range"][1]
    ):
        return False

    if werk_table_options["edition"] and werk["edition"] != werk_table_options["edition"]:
        return False

    from_version, to_version = werk_table_options["version"]
    if from_version and cmp_version(werk["version"], from_version) < 0:
        return False

    if to_version and cmp_version(werk["version"], to_version) > 0:
        return False

    if werk_table_options["werk_content"]:
        have_match = False
        search_text = werk_table_options["werk_content"].lower()
        for line in [werk["title"]] + werk["body"]:
            if search_text in line.lower():
                have_match = True
                break
        if not have_match:
            return False

    return True


def _default_werk_table_options():
    werk_table_options = {
        name: default_value for name, _height, _vs, default_value in _werk_table_option_entries()  #
    }
    werk_table_options["date_range"] = (1, int(time.time()))
    werk_table_options["compatibility"] = ["incomp_unack"]
    return werk_table_options


def _werk_table_options_from_request() -> Dict[str, Any]:
    if request.var("show_unack") and not request.has_var("wo_set"):
        return _default_werk_table_options()

    werk_table_options: Dict[str, Any] = {}
    for name, _height, vs, default_value in _werk_table_option_entries():
        value = default_value
        try:
            if request.has_var("wo_set"):
                value = vs.from_html_vars("wo_" + name)
                vs.validate_value(value, "wo_" + name)
        except MKUserError as e:
            html.user_error(e)

        werk_table_options.setdefault(name, value)

    from_date, until_date = Timerange.compute_range(werk_table_options["date"]).range
    werk_table_options["date_range"] = from_date, until_date

    return werk_table_options


def render_werk_id(werk, with_link) -> Union[HTML, str]:
    if with_link:
        url = makeuri_contextless(request, [("werk", werk["id"])], filename="werk.py")
        return HTMLWriter.render_a("#%04d" % werk["id"], href=url)
    return "#%04d" % werk["id"]


def render_werk_date(werk):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(werk["date"]))


def render_werk_title(werk) -> HTML:
    title = werk["title"]
    # if the title begins with the name or names of check plugins, then
    # we link to the man pages of those checks
    if ":" in title:
        parts = title.split(":", 1)
        return insert_manpage_links(parts[0]) + escape_to_html_permissive(":" + parts[1])
    return escape_to_html_permissive(title)


def render_werk_description(werk) -> HTML:  # pylint: disable=too-many-branches
    with output_funnel.plugged():
        html.open_p()
        in_list = False
        in_code = False
        for line in werk["body"]:
            if line.startswith("LI:"):
                if not in_list:
                    html.open_ul()
                    in_list = True
                html.li(line[3:])
            else:
                if in_list:
                    html.close_ul()
                    in_list = False

                if line.startswith("H2:"):
                    html.h3(line[3:])
                elif line.startswith("C+:"):
                    html.open_pre(class_="code")
                    in_code = True
                elif line.startswith("F+:"):
                    file_name = line[3:]
                    if file_name:
                        html.div(file_name, class_="filename")
                    html.open_pre(class_="file")
                    in_code = True
                elif line.startswith("C-:") or line.startswith("F-:"):
                    html.close_pre()
                    in_code = False
                elif line.startswith("OM:"):
                    html.write_text("OMD[mysite]:~$ ")
                    html.b(line[3:])
                elif line.startswith("RP:"):
                    html.write_text("root@myhost:~# ")
                    html.b(line[3:])
                elif not line.strip() and not in_code:
                    html.p("")
                else:
                    html.write_text(line + "\n")

        if in_list:
            html.close_ul()

        html.close_p()
        return HTML(output_funnel.drain())


def insert_manpage_links(text: str) -> HTML:
    parts = text.replace(",", " ").split()
    new_parts: List[HTML] = []
    check_regex = re.compile(r"[-_\.a-z0-9]")
    for part in parts:
        if check_regex.match(part) and os.path.exists(
            cmk.utils.paths.check_manpages_dir + "/" + part
        ):
            url = makeuri_contextless(
                request,
                [
                    ("mode", "check_manpage"),
                    ("check_type", part),
                ],
                filename="wato.py",
            )
            new_parts.append(HTMLWriter.render_a(content=part, href=url))
        else:
            new_parts.append(escape_to_html(part))
    return HTML(" ").join(new_parts)
