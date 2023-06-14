#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Functions for parsing Werks and showing the users a browsable change
# log

import itertools
import os
import re
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from functools import cache
from typing import Any, cast, Literal, NamedTuple, TypedDict

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils import werks as utils_werks
from cmk.utils.version import __version__, Edition, Version
from cmk.utils.werks import Werk, WerkTranslator
from cmk.utils.werks.werk import Compatibility

import cmk.gui.pages
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
from cmk.gui.htmllib.html import html, HTMLContent
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
from cmk.gui.table import Table, table_element
from cmk.gui.utils.escaping import escape_to_html, escape_to_html_permissive, strip_tags
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.theme import theme
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

acknowledgement_path = cmk.utils.paths.var_dir + "/acknowledged_werks.mk"


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class GuiWerk(NamedTuple):
    """
    Holds original Werk and attributes only used for the GUI
    """

    werk: Werk

    def sort_by_version_and_component(self, translator: WerkTranslator) -> tuple[str | int, ...]:
        werk_result = self.werk.sort_by_version_and_component(translator)
        result = (*werk_result[:4], int(self.acknowledged), *werk_result[4:])
        return result

    @property
    def acknowledged(self) -> bool:
        return self.werk.id in load_acknowledgements() or version_is_pre_127(self.werk.version)

    # @property
    # @cache
    # does not work with mypy: https://github.com/python/mypy/issues/5858
    # so we fall back to a function:
    def get_date_formatted(self) -> str:
        # return date formatted as string in local timezone
        return self.werk.date.astimezone().strftime(TIME_FORMAT)


def sort_by_date(werks: Iterable[GuiWerk]) -> list[GuiWerk]:
    return sorted(werks, key=lambda w: w.werk.date, reverse=True)


def render_description(description: str | utils_werks.NoWiki) -> HTML:
    if isinstance(description, utils_werks.NoWiki):
        return render_nowiki_werk_description(description.value)
    return HTML(description)


def get_werk_by_id(werk_id: int) -> GuiWerk:
    for werk in load_werk_entries():
        if werk.werk.id == werk_id:
            return werk
    raise MKUserError("werk", _("This werk does not exist."))


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
        html.h1(_("Your IT monitoring platform"))
        html.a(
            html.render_img(theme.url("images/checkmk_logo.svg")),
            "https://checkmk.com",
            target="_blank",
        )
        html.close_div()

        html.div(None, id_="info_underline")

        html.open_div(id_="info_intro_text")
        html.span(
            _(
                "Gain a complete view of your entire IT infrastructure: from public cloud providers, to your data centers, across servers, networks, containers, and more. Checkmk enables ITOps and DevOps teams to run your IT at peak performance."
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

        html.open_div(id="info_image")
        html.open_a(href="https://checkmk.com/product/latest-version", target="_blank")
        html.img(theme.url("images/monitoring-machine.png"))
        html.close_a()
        html.close_div()

        html.close_div()

        html.open_div(id_="info_footer")
        html.span(_("© %s Checkmk GmbH. All Rights Reserved.") % time.strftime("%Y"))
        html.a(_("License agreement"), href="https://checkmk.com/legal.html", target="_blank")
        html.close_div()
        return None


@cmk.gui.pages.page_registry.register_page("change_log")
class ModeChangeLogPage(cmk.gui.pages.Page):
    def _title(self) -> str:
        return _("Change log (Werks)")

    def page(self) -> cmk.gui.pages.PageResult:  # pylint: disable=useless-return
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry["help_links"], self._title())

        werk_table_options = _werk_table_options_from_request()

        make_header(
            html,
            self._title(),
            breadcrumb,
            self._page_menu(breadcrumb, werk_table_options),
        )

        for message in get_flashed_messages():
            html.show_message(message.msg)

        handle_acknowledgement()

        html.open_div(class_="wato")
        render_werks_table(werk_table_options)
        html.close_div()

        html.footer()
        return None

    def _page_menu(self, breadcrumb: Breadcrumb, werk_table_options: WerkTableOptions) -> PageMenu:
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
        gui_werk = get_werk_by_id(werk_id)
        werk = gui_werk.werk
        if (
            werk.compatible == utils_werks.Compatibility.NOT_COMPATIBLE
            and not gui_werk.acknowledged
        ):
            acknowledge_werk(gui_werk)
            html.show_message(
                _("Werk %s - %s has been acknowledged.")
                % (render_werk_id(werk), render_werk_title(werk))
            )
            render_unacknowleged_werks()

    elif request.var("_ack_all"):
        num = len(unacknowledged_incompatible_werks())
        acknowledge_all_werks()
        flash(_("%d incompatible Werks have been acknowledged.") % num)
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
            make_confirm_delete_link(
                url=makeactionuri(request, transactions, [("_ack_all", "1")]),
                title=_("Acknowledge all incompatible werks"),
                confirm_button=_("Acknowledge all"),
            )
        ),
        is_enabled=bool(unacknowledged_incompatible_werks()),
    )


def _extend_display_dropdown(  # type: ignore[no-untyped-def]
    menu, werk_table_options: WerkTableOptions
) -> None:
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


def _render_werk_options_form(werk_table_options: WerkTableOptions) -> HTML:
    with output_funnel.plugged():
        html.begin_form("werks")
        html.hidden_field("wo_set", "set")

        _show_werk_options_controls()

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
def page_werk() -> None:
    gui_werk = get_werk_by_id(request.get_integer_input_mandatory("werk"))
    werk = gui_werk.werk

    title = ("%s %s - %s") % (
        _("Werk"),
        render_werk_id(werk),
        werk.title,
    )

    breadcrumb = make_main_menu_breadcrumb(mega_menu_registry["help_links"])
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Change log (Werks)"),
            url="change_log.py",
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    make_header(html, title, breadcrumb, _page_menu_werk(breadcrumb, gui_werk))

    html.open_table(class_=["data", "headerleft", "werks"])

    def werk_table_row(caption: HTMLContent, content: HTMLContent, css: None | str = None) -> None:
        html.open_tr()
        html.th(caption)
        html.td(content, class_=css)
        html.close_tr()

    translator = WerkTranslator()
    werk_table_row(_("ID"), render_werk_id(werk))
    werk_table_row(_("Title"), HTMLWriter.render_b(render_werk_title(werk)))
    werk_table_row(_("Component"), translator.component_of(werk))
    werk_table_row(_("Date"), gui_werk.get_date_formatted())
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
        compatibility_of(werk.compatible, gui_werk.acknowledged),
        css="werkcomp werkcomp%s" % _to_ternary_compatibility(gui_werk),
    )
    werk_table_row(
        _("Description"), render_description(werk.description), css="nowiki"
    )  # TODO: remove nowiki

    html.close_table()

    html.footer()


def _page_menu_werk(breadcrumb: Breadcrumb, werk: GuiWerk) -> PageMenu:
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


def _page_menu_entries_ack_werk(werk: GuiWerk) -> Iterator[PageMenuEntry]:
    if not may_acknowledge():
        return

    ack_url = makeactionuri(
        request, transactions, [("_werk_ack", werk.werk.id)], filename="change_log.py"
    )
    yield PageMenuEntry(
        title=_("Acknowledge"),
        icon_name="werk_ack",
        item=make_simple_link(ack_url),
        is_enabled=not werk.acknowledged,
        is_shortcut=True,
        is_suggested=True,
    )


@cache
def load_werk_entries() -> Sequence[GuiWerk]:
    werks_raw = utils_werks.load()
    werks = []
    for werk in werks_raw.values():
        werks.append(
            GuiWerk(
                werk=werk,
            )
        )
    return werks


def may_acknowledge() -> bool:
    return user.may("general.acknowledge_werks")


def acknowledge_werk(werk: GuiWerk) -> None:
    acknowledge_werks([werk])


def acknowledge_werks(werks: Iterable[GuiWerk], check_permission: bool = True) -> None:
    if check_permission:
        user.need_permission("general.acknowledge_werks")

    ack_ids = load_acknowledgements()
    for werk in werks:
        ack_ids.add(werk.werk.id)
    save_acknowledgements(list(ack_ids))


def save_acknowledgements(acknowledged_werks: list[int]) -> None:
    load_acknowledgements.cache_clear()  # type: ignore[attr-defined]
    store.save_object_to_file(acknowledgement_path, acknowledged_werks)


def acknowledge_all_werks(check_permission: bool = True) -> None:
    acknowledge_werks(unacknowledged_incompatible_werks(), check_permission)


def version_is_pre_127(version: str) -> bool:
    return version.startswith("1.2.5") or version.startswith("1.2.6")


@request_memoize()
def load_acknowledgements() -> set[int]:
    return set(store.load_object_from_file(acknowledgement_path, default=[]))


def unacknowledged_incompatible_werks() -> list[GuiWerk]:
    return sort_by_date(
        werk
        for werk in load_werk_entries()
        if werk.werk.compatible == utils_werks.Compatibility.NOT_COMPATIBLE
        and not werk.acknowledged
    )


def num_unacknowledged_incompatible_werks() -> int:
    return len(unacknowledged_incompatible_werks())


def _werk_table_option_entries() -> list[tuple[_WerkTableOptionColumns, str, ValueSpec, Any]]:
    translator = WerkTranslator()
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
                        for e in (Edition.CCE, Edition.CME, Edition.CEE, Edition.CRE)
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
            (Version.from_str(__version__).version_base, ""),
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


def render_unacknowleged_werks() -> None:
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
_SORT_AND_GROUP: dict[
    str | None,
    tuple[
        Callable[[Iterator[GuiWerk]], list[GuiWerk]],
        Callable[[GuiWerk], None | str],
    ],
] = {
    "version": (utils_werks.sort_by_version_and_component, lambda werk: werk.werk.version),
    "day": (
        sort_by_date,
        lambda werk: werk.werk.date.astimezone().strftime("%Y-%m-%d"),
    ),
    "week": (
        sort_by_date,
        lambda werk: werk.werk.date.astimezone().strftime("%s %%U - %%Y" % _("Week")),
    ),
    None: (sort_by_date, lambda _werk: None),
}

# TODO: validate version field of markdown files!


def render_werks_table(werk_table_options: WerkTableOptions) -> None:
    translator = WerkTranslator()
    number_of_werks = 0
    sorter, grouper = _SORT_AND_GROUP[werk_table_options["grouping"]]
    list_of_werks = sorter(
        werk for werk in load_werk_entries() if werk_matches_options(werk, werk_table_options)  #
    )
    groups = itertools.groupby(list_of_werks, key=grouper)
    for group_title, werks in itertools.islice(groups, werk_table_options["group_limit"]):
        with table_element(
            title=group_title, limit=None, searchable=False, sortable=False, css="werks"
        ) as table:
            for werk in werks:
                number_of_werks += 1
                render_werks_table_row(table, translator, werk)
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


def render_werks_table_row(table: Table, translator: WerkTranslator, gui_werk: GuiWerk) -> None:
    werk = gui_werk.werk
    table.row()
    table.cell(_("ID"), render_werk_link(werk), css=["number narrow"])
    table.cell(_("Version"), werk.version, css=["number narrow"])
    table.cell(_("Date"), gui_werk.get_date_formatted(), css=["number narrow"])
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
        compatibility_of(werk.compatible, gui_werk.acknowledged),
        css=["werkcomp werkcomp%s" % _to_ternary_compatibility(gui_werk)],
    )
    table.cell(_("Component"), translator.component_of(werk), css=["nowrap"])
    table.cell(_("Title"), render_werk_title(werk))


def _to_ternary_compatibility(werk: GuiWerk) -> str:
    if werk.werk.compatible == utils_werks.Compatibility.NOT_COMPATIBLE:
        if werk.acknowledged:
            return "incomp_ack"
        return "incomp_unack"
    return "compat"


def werk_matches_options(gui_werk: GuiWerk, werk_table_options: WerkTableOptions) -> bool:
    # TODO: Fix this silly typing chaos below!
    # check if werk id is int because valuespec is TextInput
    # else, set empty id to return all results beside input warning
    werk = gui_werk.werk
    try:
        werk_to_match: int | str = int(werk_table_options["id"])
    except ValueError:
        werk_to_match = ""

    if not (
        (not werk_to_match or werk.id == werk_to_match)
        and werk.level.value in werk_table_options["levels"]
        and werk.class_.value in werk_table_options["classes"]
        and _to_ternary_compatibility(gui_werk) in werk_table_options["compatibility"]
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
        text = werk.title + strip_tags(render_description(werk.description))
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


def _werk_table_options_from_request() -> WerkTableOptions:
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


def render_werk_id(werk: Werk) -> str:
    return "#%04d" % werk.id


def render_werk_link(werk: Werk) -> HTML:
    werk_id = render_werk_id(werk)
    url = makeuri_contextless(request, [("werk", werk.id)], filename="werk.py")
    return HTMLWriter.render_a(werk_id, href=url)


def render_werk_title(werk: Werk) -> HTML:
    title = werk.title
    # if the title begins with the name or names of check plugins, then
    # we link to the man pages of those checks
    if ":" in title:
        parts = title.split(":", 1)
        return insert_manpage_links(parts[0]) + escape_to_html_permissive(":" + parts[1])
    return escape_to_html_permissive(title)


def render_nowiki_werk_description(  # pylint: disable=too-many-branches
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
                    html.write_text(line + "\n")

        if in_list:
            html.close_ul()

        html.close_p()
        return HTML(output_funnel.drain())


def insert_manpage_links(text: str) -> HTML:
    parts = text.replace(",", " ").split()
    new_parts: list[HTML] = []
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
