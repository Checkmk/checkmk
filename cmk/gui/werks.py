#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# Functions for parsing Werks and showing the users a browsable change
# log

import itertools
import time
from collections.abc import Callable, Container, Iterable, Iterator
from functools import partial
from typing import Any, cast, Literal, override, TypedDict

import cmk.werks.utils as werks_utils
from cmk.ccc.version import Edition
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_main_menu_breadcrumb,
    make_simple_page_breadcrumb,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLContent
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
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
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import IconNames, StaticIcon
from cmk.gui.utils.escaping import escape_to_html_permissive, strip_tags
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri, makeuri_contextless
from cmk.gui.valuespec import (
    DropdownChoice,
    Integer,
    ListChoice,
    TextInput,
    Timerange,
    Tuple,
    ValueSpec,
)
from cmk.utils.man_pages import make_man_page_path_map
from cmk.utils.werks import load_werk_entries
from cmk.utils.werks.acknowledgement import is_acknowledged
from cmk.utils.werks.acknowledgement import load_acknowledgements as werks_load_acknowledgements
from cmk.utils.werks.acknowledgement import save_acknowledgements as werks_save_acknowledgements
from cmk.werks.models import Compatibility, WerkV2, WerkV3

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("change_log", ChangeLogPage()))
    page_registry.register(PageEndpoint("werk", page_werk))


def get_werk_by_id(werk_id: int) -> WerkV2 | WerkV3:
    for werk in load_werk_entries():
        if werk.id == werk_id:
            return werk
    raise MKUserError("werk", _("This werk does not exist."))


def sort_by_date(werks: Iterable[WerkV2 | WerkV3]) -> list[WerkV2 | WerkV3]:
    return sorted(werks, key=lambda werk: werk.date, reverse=True)


def unacknowledged_incompatible_werks() -> list[WerkV2 | WerkV3]:
    acknowledged_werk_ids = load_acknowledgements()
    return sort_by_date(
        werk
        for werk in load_werk_entries()
        if werk.compatible == Compatibility.NOT_COMPATIBLE
        and not is_acknowledged(werk, acknowledged_werk_ids)
    )


class WerkTableOptions(TypedDict):
    date_range: tuple[int, int]
    compatibility: Literal["incomp_unack"]
    classes: list[Literal["feature", "fix", "security"]]
    levels: list[Literal[1, 2, 3]]
    date: tuple[int, int]
    id: str
    compaibility: list[Literal["compat", "incomp_ack", "incomp_unack"]]
    component: str | None
    edition: str | None
    werk_content: str
    version: tuple[str, str]
    grouping: None | Literal["version", "day", "week"]
    group_limit: int


_WerkTableOptionColumns = Literal[
    "classes",
    "levels",
    "date",
    "id",
    "compatibility",
    "component",
    "edition",
    "werk_content",
    "version",
    "grouping",
    "group_limit",
]


class ChangeLogPage(Page):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        breadcrumb = make_simple_page_breadcrumb(
            main_menu_registry["help"], _("Change log (Werks)")
        )

        werk_table_options = _werk_table_options_from_request(ctx.request)

        make_header(
            html,
            _("Change log (Werks)"),
            breadcrumb,
            self._page_menu(ctx.request, breadcrumb, werk_table_options),
        )

        for message in get_flashed_messages():
            html.show_message(message.msg)

        handle_acknowledgement(ctx.request)

        html.open_div(class_="wato")
        render_werks_table(ctx.request, werk_table_options)
        html.close_div()

        html.footer()
        return None

    def _page_menu(
        self, request: Request, breadcrumb: Breadcrumb, werk_table_options: WerkTableOptions
    ) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="werks",
                    title=_("Werks"),
                    topics=[
                        PageMenuTopic(
                            title=_("Incompatible werks"),
                            entries=list(_page_menu_entries_ack_all_werks(request)),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        _extend_display_dropdown(request, menu, werk_table_options)
        return menu


def handle_acknowledgement(request: Request) -> None:
    if not transactions.check_transaction():
        return

    if request.var("_werk_ack"):
        werk_id = request.get_integer_input_mandatory("_werk_ack")
        werk = get_werk_by_id(werk_id)
        if werk.compatible == Compatibility.NOT_COMPATIBLE and not is_acknowledged(
            werk, load_acknowledgements()
        ):
            acknowledge_werk(werk)
            html.show_message(
                _("Werk %s - %s has been acknowledged.")
                % (render_werk_id(werk), render_werk_title(request, werk))
            )
            render_unacknowleged_werks(request)

    elif request.var("_ack_all"):
        num = len(unacknowledged_incompatible_werks())
        acknowledge_all_werks()
        html.show_message(_("%d incompatible Werks have been acknowledged.") % num)


def _page_menu_entries_ack_all_werks(request: Request) -> Iterator[PageMenuEntry]:
    if not may_acknowledge():
        return

    yield PageMenuEntry(
        title=_("Acknowledge all"),
        icon_name=StaticIcon(IconNames.werk_ack),
        is_shortcut=True,
        is_suggested=True,
        item=make_simple_link(
            make_confirm_delete_link(
                url=makeactionuri(request, transactions, [("_ack_all", "1")]),
                title=_("Acknowledge all incompatible werks"),
                confirm_button=_("Acknowledge all"),
            )
        ),
        is_enabled=bool(unacknowledged_incompatible_werks()),
    )


def _extend_display_dropdown(
    request: Request, menu: PageMenu, werk_table_options: WerkTableOptions
) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Filter"),
            entries=[
                PageMenuEntry(
                    title=_("Filter"),
                    icon_name=StaticIcon(IconNames.filter),
                    item=PageMenuSidePopup(_render_werk_options_form(request, werk_table_options)),
                    name="filters",
                    is_shortcut=True,
                ),
            ],
        ),
    )


def _render_werk_options_form(request: Request, werk_table_options: WerkTableOptions) -> HTML:
    with output_funnel.plugged():
        with html.form_context("werks"):
            html.hidden_field("wo_set", "set")

            _show_werk_options_controls(request)

            html.open_div(class_="side_popup_content")
            for name, height, vs, _default_value in _werk_table_option_entries():

                def renderer(
                    name: _WerkTableOptionColumns = name,
                    vs: ValueSpec = vs,
                    werk_table_options: WerkTableOptions = werk_table_options,
                ) -> None:
                    vs.render_input("wo_" + name, werk_table_options[name])

                html.render_floating_option(name, height, vs.title(), renderer)
            html.close_div()
            html.hidden_fields()

        return HTML.without_escaping(output_funnel.drain())


def _show_werk_options_controls(request: Request) -> None:
    html.open_div(class_="side_popup_controls")

    html.open_div(class_="update_buttons")
    html.button("apply", _("Apply"), "submit")
    html.buttonlink(makeuri(request, [], remove_prefix=""), _("Reset"))
    html.close_div()

    html.close_div()


def page_werk(ctx: PageContext) -> None:
    werk = get_werk_by_id(ctx.request.get_integer_input_mandatory("werk"))

    title = ("%s %s - %s") % (
        _("Werk"),
        render_werk_id(werk),
        werk.title,
    )

    breadcrumb = make_main_menu_breadcrumb(main_menu_registry["help"])
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Change log (Werks)"),
            url="change_log.py",
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    make_header(html, title, breadcrumb, _page_menu_werk(ctx.request, breadcrumb, werk))

    html.open_table(class_=["data", "headerleft", "werks"])

    def werk_table_row(caption: HTMLContent, content: HTMLContent, css: None | str = None) -> None:
        html.open_tr()
        html.th(caption)
        html.td(content, class_=css)
        html.close_tr()

    translator = werks_utils.WerkTranslator()
    werk_table_row(_("ID"), render_werk_id(werk))
    werk_table_row(_("Title"), HTMLWriter.render_b(render_werk_title(ctx.request, werk)))
    werk_table_row(_("Component"), translator.component_of(werk))
    werk_table_row(_("Date"), get_date_formatted(werk))
    werk_table_row(_("Checkmk Version"), werk.version)
    werk_table_row(
        _("Level"),
        translator.level_of(werk),
        css="werklevel werklevel%d" % werk.level.value,
    )
    werk_table_row(
        _("Class"),
        translator.class_of(werk),
        css="werkclass werkclass%s" % werk.level.value,
    )
    werk_table_row(
        _("Compatibility"),
        compatibility_of(werk.compatible, is_acknowledged(werk, load_acknowledgements())),
        css="werkcomp werkcomp%s" % _to_ternary_compatibility(werk),
    )
    werk_table_row(
        _("Description"), HTML.without_escaping(werk.description), css="nowiki"
    )  # TODO: remove nowiki

    html.close_table()

    html.footer()


def _page_menu_werk(request: Request, breadcrumb: Breadcrumb, werk: WerkV2 | WerkV3) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="Werk",
                title="Werk",
                topics=[
                    PageMenuTopic(
                        title=_("Incompatible werk"),
                        entries=list(_page_menu_entries_ack_werk(request, werk)),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


def _page_menu_entries_ack_werk(request: Request, werk: WerkV2 | WerkV3) -> Iterator[PageMenuEntry]:
    if not may_acknowledge():
        return

    ack_url = makeactionuri(
        request, transactions, [("_werk_ack", werk.id)], filename="change_log.py"
    )
    yield PageMenuEntry(
        title=_("Acknowledge"),
        icon_name=StaticIcon(IconNames.werk_ack),
        item=make_simple_link(ack_url),
        is_enabled=not is_acknowledged(werk, load_acknowledgements()),
        is_shortcut=True,
        is_suggested=True,
    )


def may_acknowledge() -> bool:
    return user.may("general.acknowledge_werks")


def acknowledge_werk(werk: WerkV2 | WerkV3) -> None:
    acknowledge_werks([werk])


def acknowledge_werks(werks: Iterable[WerkV2 | WerkV3], check_permission: bool = True) -> None:
    if check_permission:
        user.need_permission("general.acknowledge_werks")

    ack_ids = load_acknowledgements()
    for werk in werks:
        ack_ids.add(werk.id)
    save_acknowledgements(list(ack_ids))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    load_acknowledgements.cache_clear()  # type: ignore[attr-defined]
    werks_save_acknowledgements(acknowledged_werks)


def acknowledge_all_werks(check_permission: bool = True) -> None:
    acknowledge_werks(unacknowledged_incompatible_werks(), check_permission)


@request_memoize()
def load_acknowledgements() -> set[int]:
    return werks_load_acknowledgements()


def num_unacknowledged_incompatible_werks() -> int:
    return len(unacknowledged_incompatible_werks())


def _werk_table_option_entries() -> list[tuple[_WerkTableOptionColumns, str, ValueSpec, Any]]:
    translator = werks_utils.WerkTranslator()
    component_choices: list[tuple[None | str, str]] = [(None, _("All components"))]
    component_choices += sorted(translator.components())
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
        (
            "date",
            "double",
            Timerange(title=_("Date")),
            ("date", (1383149313, int(time.time()))),
        ),
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
                choices=component_choices,
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
                        for e in (
                            Edition.ULTIMATE,
                            Edition.ULTIMATEMT,
                            Edition.PRO,
                            Edition.COMMUNITY,
                            Edition.CLOUD,
                        )
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
            ("", ""),
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


def render_unacknowleged_werks(request: Request) -> None:
    werks = unacknowledged_incompatible_werks()
    if werks and not request.has_var("show_unack"):
        html.open_div(class_=["warning"])
        html.write_text_permissive(
            _("<b>Warning:</b> There are %d unacknowledged incompatible werks:") % len(werks)
        )
        html.br()
        html.br()
        html.a(
            _("Show unacknowledged incompatible werks"),
            href=makeuri_contextless(request, [("show_unack", "1"), ("wo_compatibility", "3")]),
        )
        html.close_div()


def get_sort_key_by_version_and_component(
    translator: werks_utils.WerkTranslator, werk: WerkV2 | WerkV3
) -> tuple[str | int, ...]:
    werk_result = werks_utils.get_sort_key_by_version_and_component(translator, werk)
    result = (
        *werk_result[:4],
        int(is_acknowledged(werk, load_acknowledgements())),
        *werk_result[4:],
    )
    return result


def sort_by_version_and_component(werks: Iterable[WerkV2 | WerkV3]) -> list[WerkV2 | WerkV3]:
    translator = werks_utils.WerkTranslator()
    return sorted(werks, key=partial(get_sort_key_by_version_and_component, translator))


def get_date_formatted(werk: WerkV2 | WerkV3) -> str:
    # return date formatted as string in local timezone
    return werk.date.astimezone().strftime(TIME_FORMAT)


# NOTE: The sorter and the grouping function should better agree, otherwise chaos will ensue...
_SORT_AND_GROUP: dict[
    str | None,
    tuple[
        Callable[[Iterator[WerkV2 | WerkV3]], list[WerkV2 | WerkV3]],
        Callable[[WerkV2 | WerkV3], None | str],
    ],
] = {
    "version": (sort_by_version_and_component, lambda werk: werk.version),
    "day": (
        sort_by_date,
        lambda werk: werk.date.astimezone().strftime("%Y-%m-%d"),
    ),
    "week": (
        sort_by_date,
        lambda werk: werk.date.astimezone().strftime("%s %%U - %%Y" % _("Week")),
    ),
    None: (sort_by_date, lambda _werk: None),
}

# TODO: validate version field of markdown files!


def render_werks_table(request: Request, werk_table_options: WerkTableOptions) -> None:
    translator = werks_utils.WerkTranslator()
    number_of_werks = 0
    sorter, grouper = _SORT_AND_GROUP[werk_table_options["grouping"]]
    list_of_werks = sorter(
        werk
        for werk in load_werk_entries()
        if werk_matches_options(werk, werk_table_options)  #
    )
    groups = itertools.groupby(list_of_werks, key=grouper)
    for group_title, werks in itertools.islice(groups, werk_table_options["group_limit"]):
        with table_element(
            title=group_title, limit=None, searchable=False, sortable=False, css="werks"
        ) as table:
            for werk in werks:
                number_of_werks += 1
                render_werks_table_row(request, table, translator, werk)
    if not number_of_werks:
        html.h3(_("No matching Werks found."))


def compatibility_of(compatible: Compatibility, acknowledged: bool) -> str:
    compatibilities = {
        (Compatibility.COMPATIBLE, False): _("Compatible"),
        (Compatibility.NOT_COMPATIBLE, True): _("Incompatible"),
        (Compatibility.NOT_COMPATIBLE, False): _("Incompatible - TODO"),
        # compatible and acknowledge should not be possible, but GUI Crawler hit that case:
        (Compatibility.COMPATIBLE, True): _("Compatible"),
    }
    return compatibilities[(compatible, acknowledged)]


def render_werks_table_row(
    request: Request, table: Table, translator: werks_utils.WerkTranslator, werk: WerkV2 | WerkV3
) -> None:
    table.row()
    table.cell(_("ID"), render_werk_link(request, werk), css=["number narrow"])
    table.cell(_("Version"), werk.version, css=["number narrow"])
    table.cell(_("Date"), get_date_formatted(werk), css=["number narrow"])
    table.cell(
        _("Class"),
        translator.class_of(werk),
        css=["werkclass werkclass%s" % werk.class_.value],
    )
    table.cell(
        _("Level"),
        translator.level_of(werk),
        css=["werklevel werklevel%d" % werk.level.value],
    )
    table.cell(
        _("Compatibility"),
        compatibility_of(werk.compatible, is_acknowledged(werk, load_acknowledgements())),
        css=["werkcomp werkcomp%s" % _to_ternary_compatibility(werk)],
    )
    table.cell(_("Component"), translator.component_of(werk), css=["nowrap"])
    table.cell(_("Title"), render_werk_title(request, werk))


def _to_ternary_compatibility(werk: WerkV2 | WerkV3) -> str:
    if werk.compatible == Compatibility.NOT_COMPATIBLE:
        if is_acknowledged(werk, load_acknowledgements()):
            return "incomp_ack"
        return "incomp_unack"
    return "compat"


def werk_matches_options(werk: WerkV2 | WerkV3, werk_table_options: WerkTableOptions) -> bool:
    # TODO: Fix this silly typing chaos below!
    # check if werk id is int because valuespec is TextInput
    # else, set empty id to return all results beside input warning
    try:
        werk_to_match: int | str = int(werk_table_options["id"])
    except ValueError:
        werk_to_match = ""

    if not (
        (not werk_to_match or werk.id == werk_to_match)
        and werk.level.value in werk_table_options["levels"]
        and werk.class_.value in werk_table_options["classes"]
        and _to_ternary_compatibility(werk) in werk_table_options["compatibility"]
        and werk_table_options["component"] in (None, werk.component)
        and werk.date.timestamp() >= werk_table_options["date_range"][0]
        and werk.date.timestamp() <= werk_table_options["date_range"][1]
    ):
        return False

    if werk_table_options["edition"] and werk.edition.value != werk_table_options["edition"]:
        return False

    from_version, to_version = werk_table_options["version"]
    if from_version and cmp_version(werk.version, from_version) < 0:
        return False

    if to_version and cmp_version(werk.version, to_version) > 0:
        return False

    if werk_table_options["werk_content"]:
        search_text = werk_table_options["werk_content"].lower()
        text = werk.title + strip_tags(werk.description)
        if search_text not in text.lower():
            return False

    return True


def _default_werk_table_options() -> WerkTableOptions:
    werk_table_options: dict[str, Any] = {
        name: default_value for name, _height, _vs, default_value in _werk_table_option_entries()
    }
    werk_table_options["date_range"] = (1, int(time.time()))
    werk_table_options["compatibility"] = ["incomp_unack"]
    return cast(WerkTableOptions, werk_table_options)


def _werk_table_options_from_request(request: Request) -> WerkTableOptions:
    if request.var("show_unack") and not request.has_var("wo_set"):
        return _default_werk_table_options()

    werk_table_options: dict[str, Any] = {}
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

    return cast(WerkTableOptions, werk_table_options)


def render_werk_id(werk: WerkV2 | WerkV3) -> str:
    return "#%04d" % werk.id


def render_werk_link(request: Request, werk: WerkV2 | WerkV3) -> HTML:
    werk_id = render_werk_id(werk)
    url = makeuri_contextless(request, [("werk", werk.id)], filename="werk.py")
    return HTMLWriter.render_a(werk_id, href=url)


def render_werk_title(request: Request, werk: WerkV2 | WerkV3) -> HTML:
    title = werk.title
    # if the title begins with the name or names of check plug-ins, then
    # we link to the man pages of those checks
    if ":" in title:
        parts = title.split(":", 1)
        return insert_manpage_links(request, parts[0]) + escape_to_html_permissive(":" + parts[1])
    return escape_to_html_permissive(title)


def render_nowiki_werk_description(
    description_raw: list[str],
) -> HTML:
    with output_funnel.plugged():
        html.open_p()
        in_list = False
        in_code = False
        for line in description_raw:
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
                    html.write_text_permissive(line + "\n")

        if in_list:
            html.close_ul()

        html.close_p()
        return HTML.without_escaping(output_funnel.drain())


def insert_manpage_links(request: Request, text: str) -> HTML:
    parts = text.replace(",", " ").split()
    known_checks = _get_known_checks()
    new_parts: list[HTML] = []
    for part in parts:
        if part in known_checks:
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
            new_parts.append(HTML.with_escaping(part))
    return HTML.without_escaping(" ").join(new_parts)


@request_memoize()
def _get_known_checks() -> Container[str]:
    return make_man_page_path_map(discover_families(raise_errors=False), PluginGroup.CHECKMAN.value)
