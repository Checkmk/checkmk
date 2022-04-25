#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing folders"""

import abc
import json
import operator
from typing import Dict, Iterator, List, Optional, Tuple, Type

from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.type_defs import HostName

import cmk.gui.forms as forms
import cmk.gui.utils as utils
import cmk.gui.view_utils
import cmk.gui.watolib as watolib
import cmk.gui.weblib as weblib
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_checkbox_selection_json_text,
    make_checkbox_selection_topic,
    make_confirmed_form_submit_link,
    make_display_options_dropdown,
    make_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuPopup,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.plugins.wato.utils import (
    configure_attributes,
    get_hostnames_from_checkboxes,
    mode_registry,
)
from cmk.gui.plugins.wato.utils.base_modes import mode_url, redirect, WatoMode
from cmk.gui.plugins.wato.utils.context_buttons import make_folder_status_link
from cmk.gui.plugins.wato.utils.main_menu import MainMenu, MenuItem
from cmk.gui.table import init_rowselect, table_element
from cmk.gui.type_defs import ActionResult, Choices
from cmk.gui.utils.agent_registration import remove_tls_registration_help
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.valuespec import DropdownChoice, TextInput, ValueSpec, WatoFolderChoices
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.watolib.hosts_and_folders import Folder


def make_folder_breadcrumb(folder: watolib.CREFolder) -> Breadcrumb:
    return (
        Breadcrumb(
            [
                BreadcrumbItem(
                    title=_("Hosts"),
                    url=None,
                ),
            ]
        )
        + folder.breadcrumb()
    )


@mode_registry.register
class ModeFolder(WatoMode):
    @classmethod
    def name(cls):
        return "folder"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def __init__(self):
        super().__init__()
        self._folder = watolib.Folder.current()

        if request.has_var("_show_host_tags"):
            user.wato_folders_show_tags = request.get_ascii_input("_show_host_tags") == "1"

        if request.has_var("_show_explicit_labels"):
            user.wato_folders_show_labels = request.get_ascii_input("_show_explicit_labels") == "1"

    def title(self):
        return self._folder.title()

    def breadcrumb(self):
        return make_folder_breadcrumb(self._folder)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if not self._folder.is_disk_folder():
            return self._search_folder_page_menu(breadcrumb)

        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="hosts",
                    title=_("Hosts"),
                    topics=[
                        PageMenuTopic(
                            title=_("In this folder"),
                            entries=list(self._page_menu_entries_hosts_in_folder()),
                        ),
                        PageMenuTopic(
                            title=_("On selected hosts"),
                            entries=list(self._page_menu_entries_selected_hosts()),
                        ),
                        make_checkbox_selection_topic(
                            "wato-folder-/%s" % self._folder.path(),
                            is_enabled=bool(self._folder.has_hosts()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="folders",
                    title=_("Folder"),
                    topics=[
                        PageMenuTopic(
                            title=_("Folder"),
                            entries=list(self._page_menu_entries_this_folder()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

        self._extend_display_dropdown(menu)
        self._extend_help_dropdown(menu)

        return menu

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Details"),
                entries=list(self._page_menu_entries_details()),
            ),
        )

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Below this folder"),
                entries=list(self._page_menu_entries_search()),
            ),
        )

    def _extend_help_dropdown(self, menu: PageMenu) -> None:
        menu.add_doc_reference(title=_("Host administration"), doc_ref=DocReference.WATO_HOSTS)
        menu.add_doc_reference(
            title=_("Beginner's guide: Host folder structures"),
            doc_ref=DocReference.INTRO_FOLDERS,
        )
        menu.add_doc_reference(
            title=_("Beginner's guide: Creating folders"),
            doc_ref=DocReference.INTRO_CREATING_FOLDERS,
        )
        menu.add_doc_reference(
            title=_("Beginner's guide: Adding the first hosts"),
            doc_ref=DocReference.INTRO_LINUX,
        )

        menu.add_youtube_reference(
            title=_("Episode 1: Installing Checkmk and monitoring Linux"), youtube_id="g1g2ztXeJbo"
        )
        menu.add_youtube_reference(
            title=_("Episode 3: Monitoring Windows"), youtube_id="iz8S9TGGklQ"
        )

    def _search_folder_page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="hosts",
                    title=_("Hosts"),
                    topics=[
                        PageMenuTopic(
                            title=_("On selected hosts"),
                            entries=list(self._page_menu_entries_selected_hosts()),
                        ),
                        make_checkbox_selection_topic(
                            "wato-folder-/%s" % self._folder.path(),
                            is_enabled=bool(self._folder.has_hosts()),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="search",
                    title=_("Search"),
                    topics=[
                        PageMenuTopic(
                            title=_("Search hosts"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Refine search"),
                                    icon_name="search",
                                    item=make_simple_link(self._folder.url([("mode", "search")])),
                                    is_shortcut=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_hosts_in_folder(self) -> Iterator[PageMenuEntry]:
        if (
            not self._folder.locked_hosts()
            and user.may("wato.manage_hosts")
            and self._folder.may("write")
        ):
            yield PageMenuEntry(
                title=_("Add host"),
                icon_name="new",
                item=make_simple_link(self._folder.url([("mode", "newhost")])),
                is_shortcut=True,
                is_suggested=True,
            )
            yield PageMenuEntry(
                title=_("Add cluster"),
                icon_name="new_cluster",
                item=make_simple_link(self._folder.url([("mode", "newcluster")])),
            )
            yield PageMenuEntry(
                title=_("Import hosts via CSV file"),
                icon_name="bulk_import",
                item=make_simple_link(self._folder.url([("mode", "bulk_import")])),
            )

        if user.may("wato.services"):
            yield PageMenuEntry(
                title=_("Discover services"),
                icon_name="services",
                item=make_simple_link(self._folder.url([("mode", "bulkinventory"), ("all", "1")])),
            )

        if user.may("wato.rename_hosts"):
            yield PageMenuEntry(
                title=_("Rename multiple hosts"),
                icon_name="rename_host",
                item=make_simple_link(self._folder.url([("mode", "bulk_rename_host")])),
            )

        if user.may("wato.manage_hosts"):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name="delete",
                item=make_confirmed_form_submit_link(
                    form_name="hosts",
                    button_name="_remove_tls_registration_from_folder",
                    message=_(
                        "Do you really want to remove the TLS registration of the hosts in"
                        " this folder (recursively)?"
                    )
                    + remove_tls_registration_help(),
                ),
            )

        if (
            not self._folder.locked_hosts()
            and user.may("wato.parentscan")
            and self._folder.may("write")
        ):
            yield PageMenuEntry(
                title=_("Detect network parent hosts"),
                icon_name="parentscan",
                item=make_simple_link(self._folder.url([("mode", "parentscan"), ("all", "1")])),
            )

        if user.may("wato.random_hosts"):
            yield PageMenuEntry(
                title=_("Add random hosts"),
                icon_name="random",
                item=make_simple_link(self._folder.url([("mode", "random_hosts")])),
            )

    def _page_menu_entries_selected_hosts(self) -> Iterator[PageMenuEntry]:
        if not user.may("wato.edit_hosts") and not user.may("wato.manage_hosts"):
            return

        hostnames = sorted(self._folder.hosts().keys(), key=utils.key_num_split)
        is_enabled = bool(self._folder.has_hosts())
        search_text = request.var("search")

        # Remember if that host has a target folder (i.e. was imported with
        # a folder information but not yet moved to that folder). If at least
        # one host has a target folder, then we show an additional bulk action.
        at_least_one_imported = False
        for hostname in hostnames:
            if search_text and (search_text.lower() not in hostname.lower()):
                continue

            host = self._folder.load_host(hostname)
            effective = host.effective_attributes()

            if effective.get("imported_folder"):
                at_least_one_imported = True

        if not self._folder.locked_hosts():
            if user.may("wato.manage_hosts"):
                yield PageMenuEntry(
                    title=_("Delete hosts"),
                    icon_name="delete",
                    item=make_confirmed_form_submit_link(
                        form_name="hosts",
                        button_name="_bulk_delete",
                        message=_("Do you really want to delete the selected hosts?"),
                    ),
                    is_enabled=is_enabled,
                )

            if user.may("wato.edit_hosts"):
                yield PageMenuEntry(
                    title=_("Edit attributes"),
                    icon_name="edit",
                    item=make_form_submit_link(
                        form_name="hosts",
                        button_name="_bulk_edit",
                    ),
                    is_enabled=is_enabled,
                )

                yield PageMenuEntry(
                    title=_("Remove explicit attribute settings"),
                    icon_name="cleanup",
                    item=make_form_submit_link(
                        form_name="hosts",
                        button_name="_bulk_cleanup",
                    ),
                    is_enabled=is_enabled,
                )

        if user.may("wato.manage_hosts"):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name="delete",
                item=make_confirmed_form_submit_link(
                    form_name="hosts",
                    button_name="_remove_tls_registration_from_selection",
                    message=_(
                        "Do you really want to remove the TLS registration of the selected hosts?"
                    )
                    + remove_tls_registration_help(),
                ),
            )

        if user.may("wato.services"):
            yield PageMenuEntry(
                title=_("Discover services"),
                icon_name="services",
                item=make_form_submit_link(
                    form_name="hosts",
                    button_name="_bulk_inventory",
                ),
                is_enabled=is_enabled,
            )

        if not self._folder.locked_hosts():
            if user.may("wato.parentscan"):
                yield PageMenuEntry(
                    title=_("Detect network parent hosts"),
                    icon_name="parentscan",
                    item=make_form_submit_link(
                        form_name="hosts",
                        button_name="_parentscan",
                    ),
                    is_enabled=is_enabled,
                )
            if user.may("wato.edit_hosts") and user.may("wato.move_hosts"):
                yield PageMenuEntry(
                    title=_("Move to other folder"),
                    icon_name="move",
                    name="move_rules",
                    item=PageMenuPopup(self._render_bulk_move_form()),
                    is_enabled=is_enabled,
                )

                if at_least_one_imported:
                    yield PageMenuEntry(
                        title=_("Move to target folders"),
                        icon_name="move",
                        item=make_confirmed_form_submit_link(
                            form_name="hosts",
                            button_name="_bulk_movetotarget",
                            message=_(
                                "You are going to move the selected hosts to folders "
                                "representing their original folder location in the system "
                                "you did the import from. Please make sure that you have "
                                "done an <b>inventory</b> before moving the hosts."
                            ),
                        ),
                        is_enabled=is_enabled,
                    )

    def _page_menu_entries_this_folder(self) -> Iterator[PageMenuEntry]:
        if self._folder.may("read"):
            yield PageMenuEntry(
                title=_("Properties"),
                icon_name="edit",
                item=make_simple_link(self._folder.edit_url(backfolder=self._folder)),
            )

        if not self._folder.locked_subfolders() and not self._folder.locked():
            if self._folder.may("write") and user.may("wato.manage_folders"):
                yield PageMenuEntry(
                    title=_("Add folder"),
                    icon_name="newfolder",
                    item=make_simple_link(self._folder.url([("mode", "newfolder")])),
                    is_shortcut=True,
                    is_suggested=True,
                )

        yield make_folder_status_link(watolib.Folder.current(), view_name="allhosts")

        if user.may("wato.rulesets") or user.may("wato.seeall"):
            yield PageMenuEntry(
                title=_("Rules"),
                icon_name="rulesets",
                item=make_simple_link(
                    watolib.folder_preserving_link(
                        [
                            ("mode", "rule_search"),
                            ("filled_in", "rule_search"),
                            ("folder", watolib.Folder.current().path()),
                            ("search_p_ruleset_used", DropdownChoice.option_id(True)),
                            ("search_p_ruleset_used_USE", "on"),
                        ]
                    )
                ),
            )

        if user.may("wato.auditlog"):
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name="auditlog",
                item=make_simple_link(make_object_audit_log_url(self._folder.object_ref())),
            )

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Tags"),
            icon_name="tag",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "tags")])),
        )

        yield PageMenuEntry(
            title=_("Custom host attributes"),
            icon_name="custom_attr",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "host_attrs")])),
        )

        if user.may("wato.dcd_connections"):
            yield PageMenuEntry(
                title=_("Dynamic host management"),
                icon_name="dcd_connections",
                item=make_simple_link(
                    watolib.folder_preserving_link([("mode", "dcd_connections")])
                ),
            )

    def _page_menu_entries_search(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Search hosts"),
            icon_name="search",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "search")])),
        )

    def _page_menu_entries_details(self) -> Iterator[PageMenuEntry]:
        for toggle_id, title, setting in [
            ("_show_host_tags", _("host tags"), user.wato_folders_show_tags),
            ("_show_explicit_labels", _("explicit host labels"), user.wato_folders_show_labels),
        ]:
            yield PageMenuEntry(
                title=_("Show %s") % title,
                icon_name="checked_checkbox" if setting else "checkbox",
                item=make_simple_link(
                    makeuri(
                        request,
                        [
                            (toggle_id, "" if setting else "1"),
                        ],
                    )
                ),
            )

    def action(self) -> ActionResult:
        if request.var("_search"):  # just commit to search form
            return None

        folder_url = self._folder.url()

        # Operations on SUBFOLDERS

        if request.var("_delete_folder"):
            if transactions.check_transaction():
                self._folder.delete_subfolder(request.var("_delete_folder"))
            return redirect(folder_url)

        if request.has_var("_move_folder_to"):
            if transactions.check_transaction():
                what_folder = watolib.Folder.folder(request.var("_ident"))
                target_folder = watolib.Folder.folder(request.var("_move_folder_to"))
                watolib.Folder.current().move_subfolder_to(what_folder, target_folder)
            return redirect(folder_url)

        if request.has_var("_remove_tls_registration_from_folder"):
            get_uuid_link_manager().unlink_sources(set(self._folder.all_hosts_recursively()))
            return None

        # Operations on HOSTS

        # Deletion of single hosts
        delname = request.var("_delete_host")
        if delname and watolib.Folder.current().has_host(delname):
            watolib.Folder.current().delete_hosts([delname])
            return redirect(folder_url)

        # Move single hosts to other folders
        if request.has_var("_move_host_to"):
            hostname = request.var("_ident")
            if hostname and watolib.Folder.current().has_host(hostname):
                target_folder = watolib.Folder.folder(request.var("_move_host_to"))
                watolib.Folder.current().move_hosts([hostname], target_folder)
                return redirect(folder_url)

        # bulk operation on hosts
        if not transactions.transaction_valid():
            return redirect(folder_url)

        # Host table: No error message on search filter reset
        if request.var("_hosts_reset_sorting") or request.var("_hosts_sort"):
            return None

        selected_host_names = get_hostnames_from_checkboxes()
        if not selected_host_names:
            raise MKUserError(
                None, _("Please select some hosts before doing bulk operations on hosts.")
            )

        # Move
        if request.var("_bulk_move"):
            target_folder_path = request.var("_bulk_moveto", request.var("_top_bulk_moveto"))
            if target_folder_path == "@":
                raise MKUserError("_bulk_moveto", _("Please select the destination folder"))
            target_folder = watolib.Folder.folder(target_folder_path)
            watolib.Folder.current().move_hosts(selected_host_names, target_folder)
            flash(_("Moved %d hosts to %s") % (len(selected_host_names), target_folder.title()))
            return redirect(folder_url)

        # Move to target folder (from import)
        if request.var("_bulk_movetotarget"):
            self._move_to_imported_folders(selected_host_names)
            return redirect(folder_url)

        # Deletion
        if request.var("_bulk_delete"):
            return self._delete_hosts(selected_host_names)

        search_text = request.get_str_input_mandatory("search", "")
        for request_var, mode_name in [
            ("_bulk_inventory", "bulkinventory"),
            ("_parentscan", "parentscan"),
            ("_bulk_edit", "bulkedit"),
            ("_bulk_cleanup", "bulkcleanup"),
        ]:
            if request.var(request_var):
                return redirect(
                    self._folder.url(
                        add_vars=[
                            ("mode", mode_name),
                            ("search", search_text),
                            ("selection", weblib.selection_id()),
                        ]
                    )
                )

        if request.var("_remove_tls_registration_from_selection"):
            get_uuid_link_manager().unlink_sources(selected_host_names)

        return None

    def page(self):
        if not self._folder.may("read"):
            reason = self._folder.reason_why_may_not("read")
            if reason:
                html.show_message(
                    html.render_icon("autherr", cssclass="authicon")
                    + escape_to_html_permissive(reason)
                )

        self._folder.show_locking_information()
        self._show_subfolders_of()
        if self._folder.may("read"):
            self._show_hosts()

        if not self._folder.has_hosts():
            if self._folder.is_search_folder():
                html.show_message(_("No matching hosts found."))
            elif not self._folder.has_subfolders() and self._folder.may("write"):
                self._show_empty_folder_menu()

    def _show_empty_folder_menu(self):
        menu_items = []

        if not self._folder.locked_hosts():
            menu_items.extend(
                [
                    MenuItem(
                        mode_or_url=makeuri_contextless(
                            request, [("mode", "newhost"), ("folder", self._folder.path())]
                        ),
                        title=_("Add host to the monitoring"),
                        icon="new",
                        permission="hosts",
                        description=_(
                            "The host must have the Checkmk agent or SNMP or an API integration prepared."
                        ),
                    ),
                    MenuItem(
                        mode_or_url=makeuri_contextless(
                            request, [("mode", "newcluster"), ("folder", self._folder.path())]
                        ),
                        title=_("Create cluster"),
                        icon="new_cluster",
                        permission="hosts",
                        description=_(
                            "Use Checkmk clusters if an item can move from one host "
                            "to another at runtime."
                        ),
                    ),
                ]
            )

        if not self._folder.locked_subfolders():
            menu_items.extend(
                [
                    MenuItem(
                        mode_or_url=makeuri_contextless(
                            request, [("mode", "newfolder"), ("folder", self._folder.path())]
                        ),
                        title=_("Add folder"),
                        icon="newfolder",
                        permission="hosts",
                        description=_(
                            "Folders group your hosts, can inherit attributes and can have permissions."
                        ),
                    )
                ]
            )

        MainMenu(menu_items).show()

    def _show_subfolders_of(self):
        if self._folder.has_subfolders():
            html.open_div(
                class_="folders"
            )  # This won't hurt even if there are no visible subfolders
            for subfolder in sorted(
                self._folder.subfolders(only_visible=True), key=operator.methodcaller("title")
            ):
                self._show_subfolder(subfolder)
            html.close_div()
            html.open_div(
                class_=["floatfolder", "unlocked", "newfolder"],
                onclick="location.href='%s'" % self._folder.url([("mode", "newfolder")]),
            )
            html.write_text("+")
            html.close_div()
            html.div("", class_="folder_foot")

    def _show_subfolder(self, subfolder):
        html.open_div(
            class_=["floatfolder", "unlocked" if subfolder.may("read") else "locked"],
            id_="folder_%s" % subfolder.name(),
            onclick="cmk.wato.open_folder(event, '%s');" % subfolder.url(),
        )
        self._show_subfolder_hoverarea(subfolder)
        self._show_subfolder_infos(subfolder)
        self._show_subfolder_title(subfolder)
        html.close_div()  # floatfolder

    def _show_subfolder_hoverarea(self, subfolder):
        # Only make folder openable when permitted to edit
        if subfolder.may("read"):
            html.open_div(
                class_="hoverarea",
                onmouseover="cmk.wato.toggle_folder(event, this, true);",
                onmouseout="cmk.wato.toggle_folder(event, this, false);",
            )
            self._show_subfolder_buttons(subfolder)
            html.close_div()  # hoverarea
        else:
            html.icon("autherr", subfolder.reason_why_may_not("read"), class_=["autherr"])
            html.div("", class_="hoverarea")

    def _show_subfolder_title(self, subfolder):
        title = subfolder.title()
        if not active_config.wato_hide_filenames:
            title += " (%s)" % subfolder.name()

        html.open_div(class_="title", title=title)
        if subfolder.may("read"):
            html.a(subfolder.title(), href=subfolder.url())
        else:
            html.write_text(subfolder.title())
        html.close_div()

    def _show_subfolder_buttons(self, subfolder):
        self._show_subfolder_edit_button(subfolder)

        if not subfolder.locked_subfolders() and not subfolder.locked():
            if subfolder.may("write") and user.may("wato.manage_folders"):
                self._show_move_to_folder_action(subfolder)
                self._show_subfolder_delete_button(subfolder)

    def _show_subfolder_edit_button(self, subfolder):
        html.icon_button(
            subfolder.edit_url(subfolder.parent()),
            _("Edit the properties of this folder"),
            "edit",
            id_="edit_" + subfolder.name(),
            cssclass="edit",
            style="display:none",
        )

    def _show_subfolder_delete_button(self, subfolder):
        msg = _("Do you really want to delete the folder %s?") % subfolder.title()
        if not active_config.wato_hide_filenames:
            msg += _(" Its directory is <tt>%s</tt>.") % subfolder.filesystem_path()
        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts:
            msg += (
                _(" The folder contains <b>%d</b> hosts, which will also be deleted!") % num_hosts
            )

        html.icon_button(
            make_confirm_link(
                url=watolib.make_action_link(
                    [("mode", "folder"), ("_delete_folder", subfolder.name())]
                ),
                message=msg,
            ),
            _("Delete this folder"),
            "delete",
            id_="delete_" + subfolder.name(),
            cssclass="delete",
            style="display:none",
        )

    def _show_subfolder_infos(self, subfolder):
        html.open_div(class_="infos")
        html.open_div(class_="infos_content")
        groups = load_contact_group_information()
        permitted_groups, _folder_contact_groups, _use_for_services = subfolder.groups()
        for num, pg in enumerate(permitted_groups):
            cgalias = groups.get(pg, {"alias": pg})["alias"]
            html.icon("contactgroups", _("Contactgroups that have permission on this folder"))
            html.write_text(" %s" % cgalias)
            html.br()
            if num > 1 and len(permitted_groups) > 4:
                html.write_text(
                    _("<i>%d more contact groups</i><br>") % (len(permitted_groups) - num - 1)
                )
                break

        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts == 1:
            html.write_text(_("1 Host"))
        elif num_hosts > 0:
            html.write_text("%d %s" % (num_hosts, _("Hosts")))
        else:
            html.i(_("(no hosts)"))
        html.close_div()
        html.close_div()

    def _show_move_to_folder_action(self, obj):
        if isinstance(obj, watolib.Host):
            what = "host"
            what_title = _("host")
            ident = obj.name()
            style = None
        else:
            what = "folder"
            what_title = _("folder")
            ident = obj.path()
            style = "display:none"

        html.popup_trigger(
            html.render_icon(
                "move",
                title=_("Move this %s to another folder") % what_title,
                cssclass="iconbutton",
            ),
            ident="move_" + obj.name(),
            method=MethodAjax(
                endpoint="move_to_folder",
                url_vars=[
                    ("what", what),
                    ("ident", ident),
                    ("back_url", makeactionuri(request, transactions, [])),
                ],
            ),
            style=style,
        )

    def _show_hosts(self):
        if not self._folder.has_hosts():
            return

        hostnames = sorted(self._folder.hosts().keys(), key=utils.key_num_split)

        html.div("", id_="row_info")

        # Show table of hosts in this folder
        html.begin_form("hosts", method="POST")
        with table_element("hosts", title=_("Hosts"), omit_empty_columns=True) as table:

            # Compute colspan for bulk actions
            colspan = 6
            for attr in host_attribute_registry.attributes():
                if attr.show_in_table():
                    colspan += 1
            if (
                not self._folder.locked_hosts()
                and user.may("wato.edit_hosts")
                and user.may("wato.move_hosts")
            ):
                colspan += 1
            if self._folder.is_search_folder():
                colspan += 1

            contact_group_names = load_contact_group_information()

            host_errors = self._folder.host_validation_errors()
            rendered_hosts: List[HostName] = []

            # Now loop again over all hosts and display them
            max_hosts = len(hostnames)
            for hostname in hostnames:
                if table.limit_reached:
                    table.limit_hint = max_hosts
                    continue
                self._show_host_row(
                    rendered_hosts, table, hostname, colspan, host_errors, contact_group_names
                )

        html.hidden_field("selection_id", weblib.selection_id())
        html.hidden_fields()
        html.end_form()

        row_count = len(hostnames)
        row_info = "%d %s" % (row_count, _("host") if row_count == 1 else _("hosts"))
        html.javascript("cmk.utils.update_row_info(%s);" % json.dumps(row_info))

        init_rowselect("wato-folder-/" + self._folder.path())

    def _show_host_row(
        self, rendered_hosts, table, hostname, colspan, host_errors, contact_group_names
    ):
        host = self._folder.load_host(hostname)
        rendered_hosts.append(hostname)
        effective = host.effective_attributes()

        table.row()

        # Column with actions (buttons)
        table.cell(
            html.render_input(
                "_toggle_group",
                type_="button",
                class_="checkgroup",
                onclick="cmk.selection.toggle_all_rows(this.form, %s, %s);"
                % make_checkbox_selection_json_text(),
                value="X",
            ),
            sortable=False,
            css="checkbox",
        )
        # Use CSS class "failed" in order to provide information about
        # selective toggling inventory-failed hosts for Javascript
        html.input(
            name="_c_%s" % hostname,
            type_="checkbox",
            value=colspan,
            class_="failed" if host.discovery_failed() else None,
        )
        html.label("", "_c_%s" % hostname)

        table.cell(_("Actions"), css="buttons", sortable=False)
        self._show_host_actions(host)

        # Hostname with link to details page (edit host)
        table.cell(_("Hostname"))
        errors = host_errors.get(hostname, []) + host.validation_errors()
        if errors:
            msg = _("Warning: This host has an invalid configuration: ")
            msg += ", ".join(errors)
            html.icon("validation_error", msg)
            html.nbsp()

        if host.is_offline():
            html.icon("disabled", _("This host is disabled"))
            html.nbsp()

        if host.is_cluster():
            html.icon(
                "cluster", _("This host is a cluster of %s") % ", ".join(host.cluster_nodes())
            )
            html.nbsp()

        html.a(hostname, href=host.edit_url())

        # Show attributes
        for attr in host_attribute_registry.attributes():
            if attr.show_in_table():
                attrname = attr.name()
                if attrname in host.attributes():
                    tdclass, tdcontent = attr.paint(host.attributes()[attrname], hostname)
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                table.cell(attr.title(), tdcontent, css=tdclass)

        # Am I authorized?
        reason = host.reason_why_may_not("read")
        if not reason:
            icon = "authok"
            title = _("You have permission to this host.")
        else:
            icon = "autherr"
            title = reason

        table.cell(_("Auth"), html.render_icon(icon, title), css="buttons", sortable=False)

        # Permissions and Contact groups - through complete recursion and inhertance
        permitted_groups, host_contact_groups, _use_for_services = host.groups()
        table.cell(
            _("Permissions"),
            HTML(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in permitted_groups]
            ),
        )
        table.cell(
            _("Contact Groups"),
            HTML(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in host_contact_groups]
            ),
        )

        if not active_config.wato_hide_hosttags and user.wato_folders_show_tags:
            table.cell(_("Tags"), css="tag-ellipsis")
            tag_groups, show_all_code = self._limit_labels(host.tag_groups())
            html.write_html(
                cmk.gui.view_utils.render_tag_groups(tag_groups, "host", with_links=False)
            )
            html.write_html(show_all_code)

        if user.wato_folders_show_labels:
            table.cell(_("Explicit labels"), css="tag-ellipsis")
            labels, show_all_code = self._limit_labels(host.labels())
            html.write_html(
                cmk.gui.view_utils.render_labels(
                    labels,
                    "host",
                    with_links=False,
                    label_sources={k: "explicit" for k in labels.keys()},
                )
            )
            html.write_html(show_all_code)

        # Located in folder
        if self._folder.is_search_folder():
            table.cell(_("Folder"))
            html.a(host.folder().alias_path(), href=host.folder().url())

    def _limit_labels(self, labels):
        show_all, limit = HTML(""), 3
        if len(labels) > limit and request.var("_show_all") != "1":
            show_all = HTML(" ") + html.render_a(
                "... (%s)" % _("show all"), href=makeuri(request, [("_show_all", "1")])
            )
            labels = dict(sorted(labels.items())[:limit])
        return labels, show_all

    def _render_contact_group(self, contact_group_names, c):
        display_name = contact_group_names.get(c, {"alias": c})["alias"]
        return html.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)

    def _show_host_actions(self, host):
        html.icon_button(host.edit_url(), _("Edit the properties of this host"), "edit")
        if user.may("wato.rulesets"):
            html.icon_button(
                host.params_url(),
                _("View the rule based effective parameters of this host"),
                "rulesets",
            )

        if host.may("read"):
            if user.may("wato.services"):
                msg = _("Edit the services of this host, do a service discovery")
            else:
                msg = _("Display the services of this host")
            image = "services"
            if host.discovery_failed():
                image = "inventory_failed"
                msg += ". " + _(
                    "The service discovery of this host failed during a previous bulk service discovery."
                )
            html.icon_button(host.services_url(), msg, image)

        if not host.locked():
            if user.may("wato.edit_hosts") and user.may("wato.move_hosts"):
                self._show_move_to_folder_action(host)

            if user.may("wato.manage_hosts"):
                if user.may("wato.clone_hosts"):
                    html.icon_button(host.clone_url(), _("Create a clone of this host"), "insert")
                delete_url = make_confirm_link(
                    url=watolib.make_action_link(
                        [("mode", "folder"), ("_delete_host", host.name())]
                    ),
                    message=_("Do you really want to delete the host <tt>%s</tt>?") % host.name(),
                )
                html.icon_button(delete_url, _("Delete this host"), "delete")

    def _delete_hosts(self, host_names) -> ActionResult:
        self._folder.delete_hosts(host_names)
        flash(_("Successfully deleted %d hosts") % len(host_names))
        return redirect(self._folder.url())

    def _render_bulk_move_form(self) -> HTML:
        with output_funnel.plugged():

            form_name = "form_hosts"
            dropdown = WatoFolderChoices(html_attrs={"form": form_name})
            dropdown.render_input("_bulk_moveto", "")
            html.button("_bulk_move", _("Move"), form=form_name)
            return HTML(output_funnel.drain())

    def _move_to_imported_folders(self, host_names_to_move) -> None:
        # Create groups of hosts with the same target folder
        target_folder_names: Dict[str, List[HostName]] = {}
        for host_name in host_names_to_move:
            host = self._folder.load_host(host_name)
            imported_folder_name = host.attribute("imported_folder")
            if imported_folder_name is None:
                continue
            target_folder_names.setdefault(imported_folder_name, []).append(host_name)

            # Remove target folder information, now that the hosts are
            # at their target position.
            host.remove_attribute("imported_folder")

        # Now handle each target folder
        for imported_folder, host_names in target_folder_names.items():
            # Next problem: The folder path in imported_folder refers
            # to the Alias of the folders, not to the internal file
            # name. And we need to create folders not yet existing.
            target_folder = self._create_target_folder_from_aliaspath(imported_folder)
            self._folder.move_hosts(host_names, target_folder)

        flash(_("Successfully moved hosts to their original folder destinations."))

    def _create_target_folder_from_aliaspath(self, aliaspath):
        # The alias path is a '/' separated path of folder titles.
        # An empty path is interpreted as root path. The actual file
        # name is the host list with the name "Hosts".
        if aliaspath in ("", "/"):
            folder = watolib.Folder.root_folder()
        else:
            parts = aliaspath.strip("/").split("/")
            folder = watolib.Folder.root_folder()
            while len(parts) > 0:
                # Look in the current folder for a subfolder with the target title
                subfolder = folder.subfolder_by_title(parts[0])
                if subfolder is not None:
                    folder = subfolder
                else:
                    name = _create_wato_foldername(parts[0], folder)
                    folder = folder.create_subfolder(name, parts[0], {})
                parts = parts[1:]

        return folder


# TODO: Split this into one base class and one subclass for folder and hosts
@page_registry.register_page("ajax_popup_move_to_folder")
class ModeAjaxPopupMoveToFolder(AjaxPage):
    """Renders the popup menu contents for either moving a host or a folder to another folder"""

    def _from_vars(self):
        self._what = request.var("what")
        if self._what not in ["host", "folder"]:
            raise NotImplementedError()

        self._ident = request.var("ident")

        self._back_url = request.get_url_input("back_url")
        if not self._back_url or not self._back_url.startswith("wato.py"):
            raise MKUserError("back_url", _("Invalid back URL provided."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self._handle_exc(self.page)

    def page(self):
        html.span(self._move_title())

        choices = self._get_choices()
        if not choices:
            html.write_text(_("No valid target folder."))
            return

        html.dropdown(
            "_host_move_%s" % self._ident,
            choices=choices,
            deflt="@",
            size=10,
            onchange="location.href='%s&_ident=%s&_move_%s_to=' + this.value;"
            % (self._back_url, self._ident, self._what),
        )

    def _move_title(self):
        if self._what == "host":
            return _("Move this host to:")
        return _("Move this folder to:")

    def _get_choices(self):
        choices: Choices = [
            ("@", _("(select target folder)")),
        ]

        if self._what == "host" and self._ident is not None:
            host = watolib.Host.host(self._ident)
            if host is not None:
                choices += host.folder().choices_for_moving_host()

        elif self._what == "folder" and self._ident is not None:
            folder = watolib.Folder.folder(self._ident)
            choices += folder.choices_for_moving_folder()

        else:
            raise NotImplementedError()

        return choices


class ABCFolderMode(WatoMode, abc.ABC):
    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def __init__(self):
        super().__init__()
        self._folder = self._init_folder()

    @abc.abstractmethod
    def _init_folder(self):
        # TODO: Needed to make pylint know the correct type of the return value.
        # Will be cleaned up in future when typing is established
        return watolib.Folder(name=None)

    @abc.abstractmethod
    def _save(self, title, attributes):
        raise NotImplementedError()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        new = self._folder.name() is None
        is_enabled = new or not watolib.Folder.current().locked()

        # When backfolder is set, we have the special situation that we want to redirect the user
        # two breadcrumb layers up. This is a very specific case, so we realize this locally instead
        # of using a generic approach. Just like it done locally by the action method.
        if request.has_var("backfolder"):
            breadcrumb = make_folder_breadcrumb(watolib.Folder.folder(request.var("backfolder")))
            breadcrumb.append(self._breadcrumb_item())

        return make_simple_form_page_menu(
            _("Folder"),
            breadcrumb,
            form_name="edit_host",
            button_name="_save",
            save_is_enabled=is_enabled,
        )

    def action(self) -> ActionResult:
        if request.has_var("backfolder"):
            # Edit icon on subfolder preview should bring user back to parent folder
            folder = watolib.Folder.folder(request.var("backfolder"))
        else:
            folder = watolib.Folder.current()

        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=folder.path()))

        # Title
        title = TextInput().from_html_vars("title")
        TextInput(allow_empty=False).validate_value(title, "title")

        attributes = watolib.collect_attributes("folder", new=self._folder.name() is None)
        self._save(title, attributes)

        return redirect(mode_url("folder", folder=folder.path()))

    # TODO: Clean this method up! Split new/edit handling to sub classes
    def page(self):
        new = self._folder.name() is None

        watolib.Folder.current().need_permission("read")

        if new and watolib.Folder.current().locked():
            watolib.Folder.current().show_locking_information()

        html.begin_form("edit_host", method="POST")

        # title
        basic_attributes: List[Tuple[str, ValueSpec, str]] = [
            ("title", TextInput(title=_("Title")), "" if new else self._folder.title()),
        ]
        html.set_focus("title")

        # folder name (omit this for root folder)
        if new or not watolib.Folder.current().is_root():
            if not active_config.wato_hide_filenames:
                basic_attributes += [
                    (
                        "name",
                        TextInput(
                            title=_("Internal directory name"),
                            help=_(
                                "This is the name of subdirectory where the files and "
                                "other folders will be created. You cannot change this later."
                            ),
                        ),
                        self._folder.name(),
                    ),
                ]

        # Attributes inherited to hosts
        if new:
            parent = watolib.Folder.current()
            myself = None
        else:
            parent = watolib.Folder.current().parent()
            myself = watolib.Folder.current()

        configure_attributes(
            new=new,
            hosts={"folder": myself},
            for_what="folder",
            parent=parent,
            myself=myself,
            basic_attributes=basic_attributes,
        )

        forms.end()
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeEditFolder(ABCFolderMode):
    @classmethod
    def name(cls):
        return "editfolder"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def _init_folder(self):
        return watolib.Folder.current()

    def title(self):
        return _("Folder properties")

    def _save(self, title, attributes):
        self._folder.edit(title, attributes)


@mode_registry.register
class ModeCreateFolder(ABCFolderMode):
    @classmethod
    def name(cls):
        return "newfolder"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_folders"]

    def _init_folder(self):
        return watolib.Folder(name=None)

    def title(self):
        return _("Add folder")

    def _save(self, title, attributes):
        if not active_config.wato_hide_filenames:
            name = request.get_ascii_input_mandatory("name", "").strip()
            watolib.check_wato_foldername("name", name)
        else:
            name = _create_wato_foldername(title)

        watolib.Folder.current().create_subfolder(name, title, attributes)


# TODO: Move to Folder()?
def _create_wato_foldername(title: str, in_folder=None) -> str:
    if in_folder is None:
        in_folder = Folder.current()

    basename = _convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if not in_folder.has_subfolder(name):
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


# TODO: Move to Folder()?
def _convert_title_to_filename(title: str) -> str:
    """lower(), replace german umlauts then everything except [-a-z0-9_] with '_'

    >>> _convert_title_to_filename("abc")
    'abc'
    >>> _convert_title_to_filename("Äbc")
    'aebc'
    >>> _convert_title_to_filename("../Äbc")
    '___aebc'
    """
    converted = ""
    for c in title.lower():
        if c == "ä":
            converted += "ae"
        elif c == "ö":
            converted += "oe"
        elif c == "ü":
            converted += "ue"
        elif c == "ß":
            converted += "ss"
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return converted


@page_registry.register_page("ajax_set_foldertree")
class ModeAjaxSetFoldertree(AjaxPage):
    def page(self):
        api_request = self.webapi_request()
        user.save_file("foldertree", (api_request.get("topic"), api_request.get("target")))
