#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Page menu processing

Cares about the page navigation of our GUI. This is the menu bar that can be found on top of each
page. It is meant to be used for page wide actions and navigation to other related pages.

The hierarchy here is:

    PageMenu > PageMenuDropdown > PageMenuTopic > PageMenuEntry > ABCPageMenuItem
"""

import abc
import json
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple, Union

import cmk.gui.utils.escaping as escaping
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.globals import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Icon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodInline
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    makeuri,
    makeuri_contextless,
    requested_file_with_query,
)


def enable_page_menu_entry(name: str):
    _toggle_page_menu_entry(name, state=True)


def disable_page_menu_entry(name: str):
    _toggle_page_menu_entry(name, state=False)


def _toggle_page_menu_entry(name: str, state: bool) -> None:
    html.javascript(
        "cmk.page_menu.enable_menu_entry(%s, %s)" % (json.dumps(name), json.dumps(state))
    )


def enable_page_menu_entries(css_class: str):
    toggle_page_menu_entries(css_class, state=True)


def disable_page_menu_entries(css_class: str):
    toggle_page_menu_entries(css_class, state=False)


def toggle_page_menu_entries(css_class: str, state: bool) -> None:
    html.javascript(
        "cmk.page_menu.enable_menu_entries(%s, %s)" % (json.dumps(css_class), json.dumps(state))
    )


@dataclass
class Link:
    """Group of attributes used for linking"""

    url: Optional[str] = None
    target: Optional[str] = None
    onclick: Optional[str] = None


class ABCPageMenuItem(abc.ABC):
    """Base class for all page menu items of the page menu
    There can be different item types, like regular links, search fields, ...
    """


@dataclass
class PageMenuLink(ABCPageMenuItem):
    """A generic hyper link to other pages"""

    link: Link


def make_simple_link(url: str) -> PageMenuLink:
    return PageMenuLink(Link(url=url))


def make_external_link(url: str) -> PageMenuLink:
    return PageMenuLink(Link(url=url, target="_blank"))


def make_javascript_link(javascript: str) -> PageMenuLink:
    # Make all actions close the menu, even actions on the page, like for example toggling of the
    # bulk selection checkboxes
    return PageMenuLink(Link(onclick=make_javascript_action(javascript)))


def make_javascript_action(javascript: str) -> str:
    return javascript.rstrip(";") + ";cmk.page_menu.close_active_dropdown();"


def make_form_submit_link(form_name: str, button_name: str) -> PageMenuLink:
    return make_javascript_link(
        "cmk.page_menu.form_submit(%s, %s)" % (json.dumps(form_name), json.dumps(button_name))
    )


def make_confirmed_form_submit_link(
    *, form_name: str, button_name: str, message: str
) -> PageMenuLink:
    return make_javascript_link(
        "cmk.page_menu.confirmed_form_submit(%s, %s, %s)"
        % (
            json.dumps(form_name),
            json.dumps(button_name),
            json.dumps(escaping.escape_text(message)),
        )
    )


@dataclass
class PageMenuPopup(ABCPageMenuItem):
    """A link opening a pre-rendered hidden area (not necessarily a popup window)"""

    content: HTML
    css_classes: List[Optional[str]] = field(default_factory=list)


@dataclass
class PageMenuSidePopup(PageMenuPopup):
    """A link opening a pre-rendered popup on the right of the page"""

    content: HTML
    css_classes: List[Optional[str]] = field(default_factory=list)


@dataclass
class PageMenuSearch(ABCPageMenuItem):
    """A text input box right in the menu, primarily for in page quick search"""

    target_mode: Optional[str] = None
    default_value: str = ""


@dataclass
class PageMenuEntry:
    """Representing an entry in the menu, holding the ABCPageMenuItem to be displayed"""

    title: str
    icon_name: Icon
    item: ABCPageMenuItem
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True
    is_show_more: bool = False
    is_list_entry: bool = True
    is_shortcut: bool = False
    is_suggested: bool = True
    shortcut_title: Optional[str] = None
    css_classes: List[Optional[str]] = field(default_factory=list)
    disabled_tooltip: Optional[str] = None
    sort_index: int = 1


@dataclass
class PageMenuTopic:
    """A dropdown is populated with multiple topics which hold the actual entries"""

    title: str
    entries: List[PageMenuEntry] = field(default_factory=list)


@dataclass
class PageMenuDropdown:
    """Each dropdown in the page menu is represented by this structure"""

    name: str
    title: str
    topics: List[PageMenuTopic] = field(default_factory=list)
    is_enabled: bool = True
    # Optional data for the popup. To be used by popup_trigger().
    # It has been added for the "add view to dashboard/report" dropdown.
    popup_data: Optional[List[Union[str, Dict]]] = None

    @property
    def any_show_more_entries(self) -> bool:
        return any(entry.is_show_more for topic in self.topics for entry in topic.entries)

    @property
    def is_empty(self) -> bool:
        return not any(entry.is_list_entry for topic in self.topics for entry in topic.entries)


@dataclass
class PageMenu:
    """Representing the whole menu of the page"""

    dropdowns: List[PageMenuDropdown] = field(default_factory=list)
    breadcrumb: Optional[Breadcrumb] = None
    inpage_search: Optional[PageMenuSearch] = None
    has_pending_changes: bool = False
    pending_changes_tooltip: Optional[str] = None

    def __post_init__(self):
        # Add the display options dropdown
        self.dropdowns.append(make_display_options_dropdown())

        # Add the help dropdown, which shall be shown on all pages
        self.dropdowns.append(make_help_dropdown())

        # Add the up-entry
        if self.breadcrumb and len(self.breadcrumb) > 1 and self.breadcrumb[-2].url:
            self.dropdowns.append(make_up_link(self.breadcrumb))

    def __getitem__(self, name):
        for dropdown in self.dropdowns:
            if dropdown.name == name:
                return dropdown
        raise KeyError(f"Dropdown {name} not found.")

    def get_dropdown_by_name(self, name: str, deflt: PageMenuDropdown) -> PageMenuDropdown:
        try:
            return self[name]
        except KeyError:
            return deflt

    @property
    def _entries(self) -> Iterator[PageMenuEntry]:
        for dropdown in self.dropdowns:
            for topic in dropdown.topics:
                for entry in topic.entries:
                    yield entry

    @property
    def popups(self) -> Iterator[PageMenuEntry]:
        for entry in self._entries:
            if isinstance(entry.item, PageMenuPopup):
                yield entry

    @property
    def shortcuts(self) -> Iterator[PageMenuEntry]:
        has_suggestions = False
        shortcuts = []
        for entry in self._entries:
            if not entry.is_shortcut:
                continue

            if entry.is_suggested:
                has_suggestions = True

            shortcuts.append(entry)

        if has_suggestions:
            yield PageMenuEntry(
                title=_("Toggle suggested actions"),
                icon_name="suggestion",
                item=make_javascript_link("cmk.page_menu.toggle_suggestions()"),
                name="toggle_suggestions",
                is_shortcut=True,
                is_suggested=False,
            )

        yield from sorted(shortcuts, key=lambda e: e.sort_index)

    @property
    def suggestions(self) -> Iterator[PageMenuEntry]:
        for entry in self.shortcuts:
            if entry.is_suggested:
                yield entry

    @property
    def has_suggestions(self) -> bool:
        return any(True for _s in self.suggestions)

    def add_doc_reference(self, title: str, doc_ref: DocReference) -> None:
        help_dropdown = self.get_dropdown_by_name("help", make_help_dropdown())
        help_dropdown.topics[1].entries.append(
            PageMenuEntry(
                title=title, icon_name="manual", item=make_external_link(doc_reference_url(doc_ref))
            )
        )

    def add_youtube_reference(self, title: str, youtube_id: str) -> None:
        help_dropdown = self.get_dropdown_by_name("help", make_help_dropdown())
        help_dropdown.topics[2].entries.append(
            PageMenuEntry(
                title=title,
                icon_name="video",
                item=make_external_link("https://youtu.be/%s" % youtube_id),
            )
        )


def make_display_options_dropdown() -> PageMenuDropdown:
    return PageMenuDropdown(
        name="display",
        title=_("Display"),
        topics=[
            PageMenuTopic(
                title=_("General display options"),
                entries=[
                    PageMenuEntry(
                        title=_("This page without navigation"),
                        icon_name="frameurl",
                        item=PageMenuLink(
                            Link(
                                url=makeuri(request, []),
                                target="_top",
                            )
                        ),
                    ),
                    PageMenuEntry(
                        title=_("This page with navigation"),
                        icon_name="pageurl",
                        item=PageMenuLink(
                            Link(
                                url=makeuri_contextless(
                                    request,
                                    [("start_url", makeuri(request, []))],
                                    filename="index.py",
                                ),
                                target="_top",
                            )
                        ),
                    ),
                ],
            ),
        ],
    )


def make_help_dropdown() -> PageMenuDropdown:
    title_show_help = _("Show inline help")
    title_hide_help = _("Hide inline help")
    return PageMenuDropdown(
        name="help",
        title=_("Help"),
        topics=[
            PageMenuTopic(
                title=_("Context sensitive help"),
                entries=[
                    PageMenuEntry(
                        title=title_hide_help if user.show_help else title_show_help,
                        icon_name="help",
                        item=make_javascript_link(
                            'cmk.help.toggle("%s", "%s")' % (title_show_help, title_hide_help)
                        ),
                        name="inline_help",
                        is_enabled=False,
                        disabled_tooltip=_("This page does not provide an inline help."),
                    )
                ],
            ),
            PageMenuTopic(
                title=_("Articles in the user guide"),
                entries=[
                    PageMenuEntry(
                        title=_("The official Checkmk user guide"),
                        icon_name="manual",
                        item=make_external_link(doc_reference_url()),
                    ),
                ],
            ),
            PageMenuTopic(
                title=_("Suggested tutorial videos"),
                entries=[],
            ),
        ],
    )


def make_up_link(breadcrumb: Breadcrumb) -> PageMenuDropdown:
    parent_item = breadcrumb[-2]
    return PageMenuDropdown(
        name="dummy",
        title="dummy",
        topics=[
            PageMenuTopic(
                title=_("Dummy"),
                entries=[
                    PageMenuEntry(
                        title=parent_item.title,
                        icon_name="up",
                        item=make_simple_link(parent_item.url),
                        name="up",
                        is_list_entry=False,
                        is_shortcut=True,
                    ),
                ],
            ),
        ],
    )


def make_checkbox_selection_json_text() -> Tuple[str, str]:
    return json.dumps(_("Select all checkboxes")), json.dumps(_("Deselect all checkboxes"))


def make_checkbox_selection_topic(selection_key: str, is_enabled: bool = True) -> PageMenuTopic:
    is_selected = user.get_rowselection(request.var("selection") or "", selection_key)
    name_selected, name_deselected = make_checkbox_selection_json_text()
    return PageMenuTopic(
        title=_("Selection"),
        entries=[
            PageMenuEntry(
                name="checkbox_selection",
                title=_("Select all checkboxes"),
                icon_name="checkbox" if is_selected else "checked_checkbox",
                item=make_javascript_link(
                    "cmk.selection.toggle_all_rows(this.form, %s, %s);"
                    % (name_selected, name_deselected)
                ),
                is_enabled=is_enabled,
            ),
        ],
    )


def make_simple_form_page_menu(
    title: str,
    breadcrumb: Breadcrumb,
    form_name: Optional[str] = None,
    button_name: Optional[str] = None,
    save_title: Optional[str] = None,
    save_icon: str = "save",
    save_is_enabled: bool = True,
    add_abort_link: bool = False,
    abort_url: Optional[str] = None,
    inpage_search: Optional[PageMenuSearch] = None,
) -> PageMenu:
    """Factory for creating a simple menu for object edit dialogs that just link back"""
    entries = []

    if form_name and button_name:
        entries.append(
            _make_form_save_link(form_name, button_name, save_title, save_icon, save_is_enabled)
        )

    if add_abort_link:
        entries.append(_make_form_abort_link(breadcrumb, abort_url))

    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="actions",
                title=title,
                topics=[
                    PageMenuTopic(
                        title=_("Actions"),
                        entries=entries,
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
        inpage_search=inpage_search,
    )


def _make_form_save_link(
    form_name: str,
    button_name: str,
    save_title: Optional[str] = None,
    save_icon: str = "save",
    save_is_enabled: bool = True,
) -> PageMenuEntry:
    return PageMenuEntry(
        title=save_title or _("Save"),
        icon_name=save_icon,
        item=make_form_submit_link(form_name, button_name),
        is_shortcut=True,
        is_suggested=True,
        is_enabled=save_is_enabled,
        css_classes=["submit" if button_name == "_save" else ""],
    )


def _make_form_abort_link(breadcrumb: Breadcrumb, abort_url: Optional[str]) -> PageMenuEntry:
    if not abort_url:
        if not breadcrumb or len(breadcrumb) < 2 or not breadcrumb[-2].url:
            raise ValueError("Can not create back link for this page")
        abort_url = breadcrumb[-2].url
    assert abort_url is not None

    return PageMenuEntry(
        title=_("Abort"),
        icon_name="abort",
        item=make_simple_link(abort_url),
        is_shortcut=True,
        is_suggested=True,
    )


class PageMenuRenderer:
    """Renders the given page menu to the page header"""

    def show(self, menu: PageMenu, hide_suggestions: bool = False) -> None:
        html.open_table(
            id_="page_menu_bar",
            class_=["menubar", "" if not hide_suggestions else "hide_suggestions"],
        )

        html.open_tr()
        self._show_dropdowns(menu)
        if menu.inpage_search:
            self._show_inpage_search_field(menu.inpage_search)
        self._show_shortcuts(menu)
        if menu.has_pending_changes:
            self._show_pending_changes_icon(menu.pending_changes_tooltip)
        html.close_tr()

        self._show_suggestions(menu)
        html.close_table()

    def _show_dropdowns(self, menu: PageMenu) -> None:
        html.open_td(class_="menues")

        for dropdown in menu.dropdowns:
            if dropdown.is_empty:
                continue

            html.open_div(
                id_="page_menu_dropdown_%s" % dropdown.name,
                class_=["menucontainer", "disabled" if not dropdown.is_enabled else None],
            )

            self._show_dropdown_trigger(dropdown)

            html.close_div()  # menucontainer

        html.close_td()

    def _show_dropdown_trigger(self, dropdown: PageMenuDropdown) -> None:
        html.popup_trigger(
            html.render_h2(dropdown.title),
            ident="menu_" + dropdown.name,
            method=MethodInline(self._render_dropdown_area(dropdown)),
            data=dropdown.popup_data,
            popup_group="menu",
        )

    def _render_dropdown_area(self, dropdown: PageMenuDropdown) -> str:
        with output_funnel.plugged():
            self._show_dropdown_area(dropdown)
            return output_funnel.drain()

    def _show_dropdown_area(self, dropdown: PageMenuDropdown) -> None:
        id_ = "menu_%s" % dropdown.name
        show_more = user.get_tree_state("more_buttons", id_, isopen=False) or user.show_more_mode
        html.open_div(class_=["menu", ("more" if show_more else "less")], id_=id_)

        if dropdown.any_show_more_entries:
            html.open_div(class_=["more_container"])
            html.more_button(id_, dom_levels_up=2)
            html.close_div()

        for topic in dropdown.topics:
            if not topic.entries:
                continue  # Do not display empty topics

            self._show_topic(topic)

        html.close_div()

    def _show_topic(self, topic: PageMenuTopic) -> None:
        html.open_div(class_="topic")
        html.div(
            topic.title,
            class_=[
                "topic_title",
                "show_more_mode" if all(entry.is_show_more for entry in topic.entries) else None,
            ],
        )

        for entry in topic.entries:
            if not entry.is_list_entry:
                continue

            self._show_entry(entry)

        html.close_div()

    def _show_entry(self, entry: PageMenuEntry) -> None:
        classes: List[Optional[str]] = ["entry"]
        classes += self._get_entry_css_classes(entry)

        html.open_div(
            class_=classes,
            id_="menu_entry_%s" % entry.name if entry.name else None,
            title=entry.disabled_tooltip if not entry.is_enabled else None,
        )
        DropdownEntryRenderer().show(entry)
        html.close_div()

    def _show_shortcuts(self, menu: PageMenu) -> None:
        html.open_td(class_="shortcuts")

        for entry in menu.shortcuts:
            ShortcutRenderer().show(entry)

        html.close_td()

    def _show_suggestions(self, menu: PageMenu) -> None:
        entries = menu.suggestions
        if not entries:
            return

        html.open_tr(id_="suggestions")
        html.open_td(colspan=3)
        for entry in entries:
            classes: List[Optional[str]] = ["suggestion"]
            classes += self._get_entry_css_classes(entry)
            html.open_div(class_=classes)
            SuggestedEntryRenderer().show(entry)
            html.close_div()
        html.close_td()
        html.close_tr()

    def _get_entry_css_classes(self, entry: PageMenuEntry) -> List[Optional[str]]:
        classes: List[Optional[str]] = [
            ("enabled" if entry.is_enabled else "disabled"),
            ("show_more_mode" if entry.is_show_more else "basic"),
        ]
        classes += entry.css_classes
        return classes

    def _show_inpage_search_field(self, item: PageMenuSearch) -> None:
        html.open_td(class_="inpage_search")
        inpage_search_form(mode=item.target_mode, default_value=item.default_value)
        html.close_td()

    def _show_pending_changes_icon(self, tooltip: Optional[str]) -> None:
        html.open_td(class_="icon_container")
        html.icon_button("wato.py?mode=changelog", tooltip if tooltip else "", "pending_changes")
        html.close_td()


class SuggestedEntryRenderer:
    """Render the different item types for the suggestion area"""

    def show(self, entry: PageMenuEntry) -> None:
        if isinstance(entry.item, PageMenuLink):
            self._show_link_item(entry, entry.item)
        elif isinstance(entry.item, PageMenuPopup):
            self._show_popup_link_item(entry, entry.item)
        else:
            raise NotImplementedError("Suggestion rendering not implemented for %s" % entry.item)

    def _show_link_item(self, entry: PageMenuEntry, item: PageMenuLink) -> None:
        self._show_link(
            entry, url=item.link.url, onclick=item.link.onclick, target=item.link.target
        )

    def _show_popup_link_item(self, entry: PageMenuEntry, item: PageMenuPopup) -> None:
        self._show_link(
            entry,
            url="javascript:void(0)",
            onclick="cmk.page_menu.toggle_popup(%s)" % json.dumps("popup_%s" % entry.name),
            target=None,
        )

    def _show_link(
        self,
        entry: PageMenuEntry,
        url: Optional[str],
        onclick: Optional[str],
        target: Optional[str],
    ) -> None:
        html.open_a(
            href=url,
            onclick=onclick,
            target=target,
            id_=("menu_suggestion_%s" % entry.name if entry.name else None),
        )
        html.icon(entry.icon_name or "trans")
        html.write_text(entry.shortcut_title or entry.title)
        html.close_a()


class ShortcutRenderer:
    """Render the different item types for the shortcut area"""

    def show(self, entry: PageMenuEntry) -> None:
        if isinstance(entry.item, PageMenuLink):
            self._show_link_item(entry, entry.item)
        elif isinstance(entry.item, PageMenuPopup):
            self._show_popup_link_item(entry, entry.item)
        else:
            raise NotImplementedError("Shortcut rendering not implemented for %s" % entry.item)

    def _show_link_item(self, entry: PageMenuEntry, item: PageMenuLink) -> None:
        self._show_link(
            entry=entry, url=item.link.url, onclick=item.link.onclick, target=item.link.target
        )

    def _show_popup_link_item(self, entry: PageMenuEntry, item: PageMenuPopup) -> None:
        self._show_link(
            entry,
            url="javascript:void(0)",
            onclick="cmk.page_menu.toggle_popup(%s)" % json.dumps("popup_%s" % entry.name),
            target=None,
        )

    def _show_link(
        self,
        entry: PageMenuEntry,
        url: Optional[str],
        onclick: Optional[str],
        target: Optional[str],
    ) -> None:
        classes = ["link", "enabled" if entry.is_enabled else "disabled"]
        if entry.is_suggested:
            classes.append("suggested")

        html.icon_button(
            url=url,
            onclick=onclick,
            title=entry.shortcut_title or entry.title,
            icon=entry.icon_name,
            target=target,
            class_=" ".join(classes),
            id_=("menu_shortcut_%s" % entry.name if entry.name else None),
        )


class DropdownEntryRenderer:
    """Render the different item types for the dropdown menu"""

    def show(self, entry: PageMenuEntry) -> None:
        if isinstance(entry.item, PageMenuLink):
            self._show_link_item(entry.title, entry.icon_name, entry.item)
        elif isinstance(entry.item, PageMenuPopup):
            self._show_popup_link_item(entry, entry.item)
        else:
            raise NotImplementedError("Rendering not implemented for %s" % entry.item)

    def _show_link_item(self, title: str, icon: Icon, item: PageMenuLink) -> None:
        if item.link.url is not None:
            url = item.link.url
            onclick = None
        else:
            url = "javascript:void(0)"
            onclick = item.link.onclick

        self._show_link(url=url, onclick=onclick, target=item.link.target, icon=icon, title=title)

    def _show_popup_link_item(self, entry: PageMenuEntry, item: PageMenuPopup) -> None:
        self._show_link(
            url="javascript:void(0)",
            onclick="cmk.page_menu.toggle_popup(%s)" % json.dumps("popup_%s" % entry.name),
            target=None,
            icon=entry.icon_name,
            title=entry.title,
        )

    def _show_link(
        self, url: str, onclick: Optional[str], target: Optional[str], icon: Icon, title: str
    ) -> None:
        html.open_a(href=url, onclick=onclick, target=target)
        html.icon(icon or "trans")
        html.span(title)
        html.close_a()


# TODO: Cleanup all calls using title and remove the argument
def search_form(
    title: Optional[str] = None, mode: Optional[str] = None, default_value: str = ""
) -> None:
    html.begin_form("search", add_transid=False)
    if title:
        html.write_text(title + " ")
    html.text_input("search", size=32, default_value=default_value)
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode, add_var=True)
    html.set_focus("search")
    html.write_text(" ")
    html.button("_do_seach", _("Search"))
    html.end_form()


# TODO: Mesh this function into one with the above search_form()
def inpage_search_form(mode: Optional[str] = None, default_value: str = "") -> None:
    form_name = "inpage_search_form"
    reset_button_id = "%s_reset" % form_name
    was_submitted = request.get_ascii_input("filled_in") == form_name
    html.begin_form(form_name, add_transid=False)
    html.text_input(
        "search",
        size=32,
        default_value=default_value,
        placeholder=_("Filter"),
        required=True,
        title="",
    )
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode, add_var=True)
    reset_url = request.get_ascii_input_mandatory("reset_url", requested_file_with_query(request))
    html.hidden_field("reset_url", reset_url, add_var=True)
    html.button("submit", "", cssclass="submit", help_=_("Apply"))
    html.buttonlink(reset_url, "", obj_id=reset_button_id, title=_("Reset"))
    html.end_form()
    html.javascript(
        "cmk.page_menu.inpage_search_init(%s, %s)"
        % (json.dumps(reset_button_id), json.dumps(was_submitted))
    )


class PageMenuPopupsRenderer:
    """Render the contents of the popup forms referred to by PageMenuPopup entries"""

    def show(self, menu: PageMenu) -> None:
        html.open_div(id_="page_menu_popups")
        for entry in menu.popups:
            self._show_popup(entry)
        html.close_div()

    def _show_popup(self, entry: PageMenuEntry) -> None:
        assert isinstance(entry.item, PageMenuPopup)

        if entry.name is None:
            raise ValueError('Missing "name" attribute on entry "%s"' % entry.title)

        classes: List[Optional[str]] = ["page_menu_popup"]
        classes += entry.item.css_classes
        if isinstance(entry.item, PageMenuSidePopup):
            classes.append("side_popup")

        popup_id = "popup_%s" % entry.name
        html.open_div(id_=popup_id, class_=classes)

        html.open_div(class_="head")
        html.h3(entry.title)
        html.a(
            html.render_icon("close"),
            class_="close_popup",
            href="javascript:void(0)",
            onclick="cmk.page_menu.close_popup(this)",
        )
        html.close_div()

        if (
            isinstance(entry.item, PageMenuSidePopup)
            and entry.item.content
            and "side_popup_content" not in entry.item.content
        ):
            raise RuntimeError(
                'Add a div container with the class "side_popup_content" to the popup content'
            )

        html.open_div(class_="content")
        html.write_html(entry.item.content)
        html.close_div()
        html.close_div()

        if isinstance(entry.item, PageMenuSidePopup):
            html.final_javascript(
                "cmk.page_menu.side_popup_add_simplebar_scrollbar(%s);" % json.dumps(popup_id)
            )
