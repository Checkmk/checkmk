#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing folders"""

import abc
import json
import re
from collections.abc import Collection, Iterator, Mapping, Sequence
from typing import override, TypeVar

from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import Labels
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.tags import TagGroupID, TagID

import cmk.gui.view_utils
from cmk.gui import forms, sites
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupSpecs
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import mandatory_parameter, request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    confirmed_form_submit_options,
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
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.quick_setup.html import quick_setup_source_cell
from cmk.gui.table import show_row_count, Table, table_element
from cmk.gui.type_defs import ActionResult, Choices, HTTPVariables, PermissionName
from cmk.gui.utils.agent_registration import remove_tls_registration_help
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html_permissive
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.rendering import set_inpage_search_result_info
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.utils.sort import natural_sort
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
    YouTubeReference,
)
from cmk.gui.valuespec import (
    AjaxDropdownChoice,
    autocompleter_registry,
    DropdownChoice,
    FixedValue,
    TextInput,
    ValueSpec,
)
from cmk.gui.watolib.agent_registration import remove_tls_registration
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.check_mk_automations import delete_hosts
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.host_attributes import (
    all_host_attributes,
    collect_attributes,
    HostAttributes,
)
from cmk.gui.watolib.hosts_and_folders import (
    check_wato_foldername,
    disk_or_search_folder_from_request,
    find_available_folder_name,
    Folder,
    folder_from_request,
    folder_preserving_link,
    folder_tree,
    Host,
    make_action_link,
    SearchFolder,
)
from cmk.gui.watolib.main_menu import MenuItem
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode

from ._bulk_actions import get_hostnames_from_checkboxes
from ._host_attributes import configure_attributes
from ._status_links import make_folder_status_link
from ._tile_menu import TileMenuRenderer

_ContactgroupName = str
TagsOrLabels = TypeVar("TagsOrLabels", Mapping[TagGroupID, TagID], Labels)


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_popup_move_to_folder", PageAjaxPopupMoveToFolder))
    page_registry.register(PageEndpoint("ajax_set_foldertree", PageAjaxSetFoldertree))
    mode_registry.register(ModeFolder)
    mode_registry.register(ModeEditFolder)
    mode_registry.register(ModeCreateFolder)
    autocompleter_registry.register_autocompleter(
        "wato_folder_choices", wato_folder_choices_autocompleter
    )


def wato_folder_choices_autocompleter(config: Config, value: str, params: dict) -> Choices:
    validate_regex(value, varname=None)
    match_pattern = re.compile(value, re.IGNORECASE)
    matching_folders: Choices = []
    for path, name in folder_tree().folder_choices_fulltitle():
        if match_pattern.search(name) is not None:
            # select2 omits empty strings ("") as option therefore the path of the Main folder is
            # replaced by a placeholder
            matching_folders.append((path, name) if path != "" else ("@main", name))
    return matching_folders


class WatoFolderChoices(AjaxDropdownChoice):
    ident = "wato_folder_choices"


def make_folder_breadcrumb(folder: Folder | SearchFolder) -> Breadcrumb:
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


class ModeFolder(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "folder"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]

    def __init__(self) -> None:
        super().__init__()
        try:
            host_name = request.get_ascii_input("host")
        except MKUserError:
            host_name = None
        self._folder = disk_or_search_folder_from_request(request.var("folder"), host_name)

        if request.has_var("_show_host_tags"):
            user.wato_folders_show_tags = request.get_ascii_input("_show_host_tags") == "1"

        if request.has_var("_show_explicit_labels"):
            user.wato_folders_show_labels = request.get_ascii_input("_show_explicit_labels") == "1"

    @override
    def title(self) -> str:
        return self._folder.title()

    @override
    def breadcrumb(self) -> Breadcrumb:
        return make_folder_breadcrumb(self._folder)

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if not self._folder.is_disk_folder():
            return self._search_folder_page_menu(breadcrumb)
        assert not isinstance(self._folder, SearchFolder)

        has_hosts = self._folder.has_hosts()

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
                            is_enabled=has_hosts,
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
            inpage_search=PageMenuSearch() if has_hosts else None,
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
            title=_("Episode 1: Installing Checkmk and monitoring your first host"),
            youtube_ref=YouTubeReference.INSTALLING_CHECKMK,
        )
        menu.add_youtube_reference(
            title=_("Episode 4: Monitoring Windows in Checkmk"),
            youtube_ref=YouTubeReference.MONITORING_WINDOWS,
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
                            is_enabled=self._folder.has_hosts(),
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
        folder_has_hosts = self._folder.has_hosts()
        folder_or_subfolder_has_hosts = (
            isinstance(self._folder, Folder) and self._folder.num_hosts_recursively() > 0
        )
        add_host_tooltip_text = _("Add host to use this action")
        add_host_or_subfolder_tooltip_text = _("Add host/subfolder to use this action")

        if (
            not self._folder.locked_hosts()
            and user.may("wato.manage_hosts")
            and self._folder.permissions.may("write")
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
                title=_("Run bulk service discovery"),
                icon_name="services",
                item=make_simple_link(self._folder.url([("mode", "bulkinventory"), ("all", "1")])),
                disabled_tooltip=add_host_tooltip_text,
                is_enabled=folder_or_subfolder_has_hosts,
            )

        if user.may("wato.rename_hosts"):
            yield PageMenuEntry(
                title=_("Rename multiple hosts"),
                icon_name="rename_host",
                item=make_simple_link(self._folder.url([("mode", "bulk_rename_host")])),
                disabled_tooltip=add_host_tooltip_text,
                is_enabled=folder_or_subfolder_has_hosts,
            )

        if user.may("wato.manage_hosts") and not isinstance(self._folder, SearchFolder):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name={"icon": "tls", "emblem": "remove"},
                item=make_confirmed_form_submit_link(
                    form_name="hosts",
                    button_name="_remove_tls_registration_from_folder",
                    title=_("Remove TLS registration of hosts in this folder"),
                    message=_("This does not affect hosts in subfolders.")
                    + "<br>"
                    + "<br>"
                    + remove_tls_registration_help(),
                    confirm_button=_("Remove"),
                    warning=True,
                ),
                disabled_tooltip=add_host_or_subfolder_tooltip_text,
                is_enabled=folder_has_hosts,
            )

        if (
            not self._folder.locked_hosts()
            and user.may("wato.parentscan")
            and self._folder.permissions.may("write")
        ):
            yield PageMenuEntry(
                title=_("Detect network parent hosts"),
                icon_name="parentscan",
                item=make_simple_link(self._folder.url([("mode", "parentscan"), ("all", "1")])),
                disabled_tooltip=add_host_tooltip_text,
                is_enabled=folder_or_subfolder_has_hosts,
            )

        if user.may("wato.random_hosts"):
            yield PageMenuEntry(
                title=_("Add random hosts"),
                icon_name="random",
                item=make_simple_link(self._folder.url([("mode", "random_hosts")])),
            )

    def _page_menu_entries_selected_hosts(
        self,
    ) -> Iterator[PageMenuEntry]:
        if not user.may("wato.edit_hosts") and not user.may("wato.manage_hosts"):
            return

        is_enabled = self._folder.has_hosts()
        add_host_or_subfolder_tooltip_text = _("Add host/subfolder to use this action")

        if not self._folder.locked_hosts() and user.may("wato.edit_hosts"):
            yield PageMenuEntry(
                title=_("Edit attributes"),
                icon_name="edit",
                item=make_form_submit_link(
                    form_name="hosts",
                    button_name="_bulk_edit",
                ),
                disabled_tooltip=add_host_or_subfolder_tooltip_text,
                is_enabled=is_enabled,
            )

        if user.may("wato.services"):
            yield PageMenuEntry(
                title=_("Run bulk service discovery"),
                icon_name="services",
                item=make_form_submit_link(
                    form_name="hosts",
                    button_name="_bulk_inventory",
                ),
                disabled_tooltip=add_host_or_subfolder_tooltip_text,
                is_enabled=is_enabled,
            )

        if not self._folder.locked_hosts():
            if user.may("wato.edit_hosts") and user.may("wato.move_hosts"):
                yield PageMenuEntry(
                    title=_("Move to other folder"),
                    icon_name="move",
                    name="move_rules",
                    item=PageMenuPopup(self._render_bulk_move_form()),
                    disabled_tooltip=add_host_or_subfolder_tooltip_text,
                    is_enabled=is_enabled,
                )

            if user.may("wato.parentscan"):
                yield PageMenuEntry(
                    title=_("Detect network parent hosts"),
                    icon_name="parentscan",
                    item=make_form_submit_link(
                        form_name="hosts",
                        button_name="_parentscan",
                    ),
                    disabled_tooltip=add_host_or_subfolder_tooltip_text,
                    is_enabled=is_enabled,
                )

            if user.may("wato.edit_hosts"):
                yield PageMenuEntry(
                    title=_("Remove explicit attribute settings"),
                    icon_name="cleanup",
                    item=make_form_submit_link(
                        form_name="hosts",
                        button_name="_bulk_cleanup",
                    ),
                    disabled_tooltip=add_host_or_subfolder_tooltip_text,
                    is_enabled=is_enabled,
                )

        if user.may("wato.manage_hosts") and not isinstance(self._folder, SearchFolder):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name={"icon": "tls", "emblem": "remove"},
                item=make_confirmed_form_submit_link(
                    form_name="hosts",
                    button_name="_remove_tls_registration_from_selection",
                    title=_("Remove TLS registration of selected hosts"),
                    message=remove_tls_registration_help(),
                    confirm_button=_("Remove"),
                    warning=True,
                ),
                disabled_tooltip=add_host_or_subfolder_tooltip_text,
                is_enabled=is_enabled,
            )

        if not self._folder.locked_hosts() and user.may("wato.manage_hosts"):
            yield PageMenuEntry(
                title=_("Delete hosts"),
                icon_name="delete",
                item=make_confirmed_form_submit_link(
                    form_name="hosts",
                    button_name="_bulk_delete",
                    title=_("Delete selected hosts"),
                ),
                disabled_tooltip=add_host_or_subfolder_tooltip_text,
                is_enabled=is_enabled,
            )

    def _page_menu_entries_this_folder(self) -> Iterator[PageMenuEntry]:
        if isinstance(self._folder, SearchFolder):
            return

        if self._folder.permissions.may("read"):
            yield PageMenuEntry(
                title=_("Properties"),
                icon_name="edit",
                item=make_simple_link(self._folder.edit_url(backfolder=self._folder)),
            )

        if not self._folder.locked_subfolders() and not self._folder.locked():
            if self._folder.permissions.may("write") and user.may("wato.manage_folders"):
                yield PageMenuEntry(
                    title=_("Add folder"),
                    icon_name="newfolder",
                    item=make_simple_link(self._folder.url([("mode", "newfolder")])),
                    is_shortcut=True,
                    is_suggested=True,
                )

        yield make_folder_status_link(self._folder, view_name="allhosts")

        if user.may("wato.rulesets") or user.may("wato.seeall"):
            yield PageMenuEntry(
                title=_("Rules"),
                icon_name="rulesets",
                item=make_simple_link(
                    folder_preserving_link(
                        [
                            ("mode", "rule_search"),
                            ("filled_in", "rule_search"),
                            ("folder", self._folder.path()),
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
            item=make_simple_link(folder_preserving_link([("mode", "tags")])),
        )

        yield PageMenuEntry(
            title=_("Custom host attributes"),
            icon_name="custom_attr",
            item=make_simple_link(folder_preserving_link([("mode", "host_attrs")])),
        )

        if user.may("wato.dcd_connections"):
            yield PageMenuEntry(
                title=_("Dynamic host management"),
                icon_name="dcd_connections",
                item=make_simple_link(folder_preserving_link([("mode", "dcd_connections")])),
            )

    def _page_menu_entries_search(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Search hosts"),
            icon_name="search",
            item=make_simple_link(folder_preserving_link([("mode", "search")])),
        )

    def _page_menu_entries_details(self) -> Iterator[PageMenuEntry]:
        for toggle_id, title, setting in [
            ("_show_host_tags", _("host tags"), user.wato_folders_show_tags),
            ("_show_explicit_labels", _("explicit host labels"), user.wato_folders_show_labels),
        ]:
            yield PageMenuEntry(
                title=_("Show %s") % title,
                icon_name="toggle_on" if setting else "toggle_off",
                item=make_simple_link(
                    makeuri(
                        request,
                        [
                            (toggle_id, "" if setting else "1"),
                        ],
                    )
                ),
            )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        if request.var("_search"):  # just commit to search form
            return None

        folder_url = self._folder.url()

        # Operations on SUBFOLDERS

        if request.var("_delete_folder"):
            if isinstance(self._folder, SearchFolder):
                raise MKUserError(None, _("This action can not be performed on search results"))
            if transactions.check_transaction():
                self._folder.delete_subfolder(request.get_ascii_input_mandatory("_delete_folder"))
            return redirect(folder_url)

        if request.has_var("_move_folder_to"):
            if isinstance(self._folder, SearchFolder):
                raise MKUserError(None, _("This action can not be performed on search results"))
            if transactions.check_transaction():
                var_ident = mandatory_parameter("_ident", request.var("_ident"))
                tree = folder_tree()
                what_folder = tree.folder(var_ident)
                target_folder = tree.folder(
                    mandatory_parameter("_move_folder_to", request.var("_move_folder_to"))
                )
                self._folder.move_subfolder_to(
                    what_folder, target_folder, pprint_value=active_config.wato_pprint_config
                )
            return redirect(folder_url)

        # Operations on current FOLDER

        if request.has_var("_remove_tls_registration_from_folder"):
            if isinstance(self._folder, SearchFolder):
                raise MKUserError(None, _("This action can not be performed on search results"))
            remove_tls_registration(
                [
                    (make_automation_config(active_config.sites[site_id]), hosts)
                    for site_id, hosts in self._folder.get_hosts_by_site(
                        list(self._folder.hosts())
                    ).items()
                ],
                debug=active_config.debug,
            )
            return None

        # Operations on HOSTS

        # Deletion of single hosts
        delname = request.var("_delete_host")
        if delname is not None:
            delname = HostName(delname)

        if delname and self._folder.has_host(delname):
            self._folder.delete_hosts(
                [delname],
                automation=delete_hosts,
                pprint_value=active_config.wato_pprint_config,
                debug=active_config.debug,
            )
            return redirect(folder_url)

        # Move single hosts to other folders
        if (target_folder_str := request.var("_move_host_to")) is not None:
            hostname = request.get_validated_type_input_mandatory(HostName, "_ident")
            if self._folder.has_host(hostname):
                self._folder.move_hosts(
                    [hostname],
                    folder_tree().folder(target_folder_str),
                    pprint_value=active_config.wato_pprint_config,
                )
                return redirect(folder_url)

        # bulk operation on hosts
        if not transactions.transaction_valid():
            return redirect(folder_url)

        # Host table: No error message on search filter reset
        if request.var("_hosts_reset_sorting") or request.var("_hosts_sort"):
            return None

        selected_host_names = get_hostnames_from_checkboxes(self._folder)
        if not selected_host_names:
            raise MKUserError(
                None, _("Please select some hosts before doing bulk actions on hosts.")
            )

        # Move
        if request.var("_bulk_move"):
            target_folder_path = request.var("_bulk_moveto", request.var("_top_bulk_moveto"))
            target_folder_path = target_folder_path if target_folder_path != "@main" else ""
            if target_folder_path is None:
                raise MKUserError("_bulk_moveto", _("Please select the destination folder"))
            target_folder = folder_tree().folder(target_folder_path)
            self._folder.move_hosts(
                selected_host_names, target_folder, pprint_value=active_config.wato_pprint_config
            )
            flash(_("Moved %d hosts to %s") % (len(selected_host_names), target_folder.title()))
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
                            ("selection", SelectionId.from_request(request)),
                        ]
                    )
                )

        if request.var("_remove_tls_registration_from_selection"):
            if isinstance(self._folder, SearchFolder):
                raise MKUserError(None, _("This action can not be performed on search results"))
            remove_tls_registration(
                [
                    (make_automation_config(active_config.sites[site_id]), hosts)
                    for site_id, hosts in self._folder.get_hosts_by_site(
                        selected_host_names
                    ).items()
                ],
                debug=active_config.debug,
            )

        return None

    @override
    def page(self) -> None:
        if not self._folder.permissions.may("read"):
            reason = self._folder.permissions.reason_why_may_not("read")
            if reason:
                html.show_message(
                    html.render_icon("autherr", cssclass="authicon")
                    + escape_to_html_permissive(reason)
                )

        self._folder.show_locking_information()
        self._show_subfolders_of()
        if self._folder.permissions.may("read"):
            self._show_hosts()

        if not self._folder.has_hosts():
            if self._folder.is_search_folder():
                html.show_message(_("No matching hosts found."))
            elif not self._folder.has_subfolders() and self._folder.permissions.may("write"):
                self._show_empty_folder_menu()

    def _show_empty_folder_menu(self) -> None:
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

        TileMenuRenderer(menu_items).show()

    def _show_subfolders_of(self) -> None:
        if self._folder.has_subfolders():
            assert isinstance(self._folder, Folder)
            html.open_div(
                class_="folders"
            )  # This won't hurt even if there are no visible subfolders

            if (searched_folder := request.var("search")) is not None:
                match_regex = re.compile(searched_folder.lower(), re.IGNORECASE)
                search_results = 0

            subfolders_dict = {
                subfolder.name(): subfolder
                for subfolder in self._folder.subfolders(only_visible=True)
            }
            sorted_subfolder_names = natural_sort(
                {
                    subfolder_name: subfolder.title()
                    for subfolder_name, subfolder in subfolders_dict.items()
                }
            )

            for name in sorted_subfolder_names:
                subfolder = subfolders_dict[name]
                if searched_folder is not None:
                    if not match_regex.search(subfolder.title()):
                        continue
                    search_results += 1

                self._show_subfolder(subfolder)

            if searched_folder is not None:
                set_inpage_search_result_info(search_results)

            html.close_div()
            html.open_div(
                class_=["floatfolder", "unlocked", "newfolder"],
                onclick="location.href='%s'" % self._folder.url([("mode", "newfolder")]),
            )
            html.write_text_permissive("+")
            html.close_div()
            html.div("", class_="folder_foot")

    def _show_subfolder(self, subfolder: Folder) -> None:
        html.open_div(
            class_=["floatfolder", "unlocked" if subfolder.permissions.may("read") else "locked"],
            id_="folder_%s" % subfolder.name(),
            onclick="cmk.wato.open_folder(event, '%s');" % subfolder.url(),
        )
        self._show_subfolder_hoverarea(subfolder)
        self._show_subfolder_infos(subfolder)
        self._show_subfolder_title(subfolder)
        html.close_div()  # floatfolder

    def _show_subfolder_hoverarea(self, subfolder: Folder) -> None:
        # Only make folder openable when permitted to edit
        if subfolder.permissions.may("read"):
            html.open_div(
                class_="hoverarea",
                onmouseover="cmk.wato.toggle_folder(event, this, true);",
                onmouseout="cmk.wato.toggle_folder(event, this, false);",
            )
            self._show_subfolder_buttons(subfolder)
            html.close_div()  # hoverarea
        else:
            html.icon(
                "autherr", subfolder.permissions.reason_why_may_not("read"), class_=["autherr"]
            )
            html.div("", class_="hoverarea")

    def _show_subfolder_title(self, subfolder: Folder) -> None:
        title = subfolder.title()
        if not active_config.wato_hide_filenames:
            title += " (%s)" % subfolder.name()

        html.open_div(class_="title", title=title)
        if subfolder.permissions.may("read"):
            html.a(subfolder.title(), href=subfolder.url())
        else:
            html.write_text_permissive(subfolder.title())
        html.close_div()

    def _show_subfolder_buttons(self, subfolder: Folder) -> None:
        self._show_subfolder_edit_button(subfolder)

        if not subfolder.locked_subfolders() and not subfolder.locked():
            if subfolder.permissions.may("write") and user.may("wato.manage_folders"):
                self._show_move_to_folder_action(subfolder)
                self._show_subfolder_delete_button(subfolder)

    def _show_subfolder_edit_button(self, subfolder: Folder) -> None:
        html.icon_button(
            subfolder.edit_url(subfolder.parent()),
            _("Edit the properties of this folder"),
            "edit",
            id_="edit_" + subfolder.name(),
            cssclass="edit",
            style="display:none",
        )

    def _show_subfolder_delete_button(self, subfolder: Folder) -> None:
        confirm_message: str = ""
        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts:
            confirm_message += (
                _("<b>Beware:</b> The folder contains <b>%d</b> hosts, which will also be deleted!")
                % num_hosts
            )

        if not active_config.wato_hide_filenames:
            if num_hosts:
                confirm_message += _("<br><br>")
            confirm_message += _("Directory: <tt>%s</tt>.") % subfolder.filesystem_path()

        html.icon_button(
            make_confirm_delete_link(
                url=make_action_link([("mode", "folder"), ("_delete_folder", subfolder.name())]),
                title=_("Delete folder"),
                suffix=subfolder.title(),
                message=confirm_message,
            ),
            _("Delete this folder"),
            "delete",
            id_="delete_" + subfolder.name(),
            cssclass="delete",
            style="display:none",
        )

    def _show_subfolder_infos(self, subfolder: Folder) -> None:
        html.open_div(class_="infos")
        html.open_div(class_="infos_content")
        groups = load_contact_group_information()
        permitted_groups, _folder_contact_groups, _use_for_services = subfolder.groups()
        for num, pg in enumerate(permitted_groups):
            cgalias = groups.get(pg, {"alias": pg})["alias"]
            html.icon("contactgroups", _("Contact groups that have permission on this folder"))
            html.write_text_permissive(" %s" % cgalias)
            html.br()
            if num > 1 and len(permitted_groups) > 4:
                html.write_text_permissive(
                    _("<i>%d more contact groups</i><br>") % (len(permitted_groups) - num - 1)
                )
                break

        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts == 1:
            html.write_text_permissive(_("1 Host"))
        elif num_hosts > 0:
            html.write_text_permissive("%d %s" % (num_hosts, _("Hosts")))
        else:
            html.i(_("(no hosts)"))
        html.close_div()
        html.close_div()

    def _show_move_to_folder_action(self, obj: Folder | Host) -> None:
        if isinstance(obj, Host):
            what = "host"
            what_title = _("host")
            ident = str(obj.name())
            style = None
        elif isinstance(obj, Folder):
            what = "folder"
            what_title = _("folder")
            ident = obj.path()
            style = "display:none"
        else:
            raise NotImplementedError()

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

    def _show_hosts(self) -> None:
        if not self._folder.has_hosts():
            return

        hostnames = natural_sort(self._folder.hosts().keys())

        html.div("", id_="row_info")

        # Show table of hosts in this folder
        with html.form_context("hosts", method="POST"):
            with table_element("hosts", title=_("Hosts"), omit_empty_columns=True) as table:
                # Compute colspan for bulk actions
                colspan = 6
                for attr in all_host_attributes(active_config).values():
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
                rendered_hosts: list[HostName] = []

                # Now loop again over all hosts and display them
                max_hosts = len(hostnames)
                for hostname in hostnames:
                    if table.limit_reached:
                        table.limit_hint = max_hosts
                        continue
                    self._show_host_row(
                        rendered_hosts,
                        table,
                        HostName(hostname),
                        colspan,
                        host_errors,
                        contact_group_names,
                    )

            html.hidden_field("selection_id", SelectionId.from_request(request))
            html.hidden_fields()

        show_row_count(
            row_count=(row_count := len(hostnames)),
            row_info=ungettext("host", "hosts", row_count),
            selection_id="wato-folder-/" + self._folder.path(),
        )

    def _show_host_row(
        self,
        rendered_hosts: list[HostName],
        table: Table,
        hostname: HostName,
        colspan: int,
        host_errors: dict[HostName, list[str]],
        contact_group_names: GroupSpecs,
    ) -> None:
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
                onclick="cmk.selection.toggle_all_rows(this.form);",
                value="X",
            ),
            sortable=False,
            css=["checkbox"],
        )
        # Use CSS class "failed" in order to provide information about
        # selective toggling inventory-failed hosts for Javascript
        html.input(
            name="_c_%s" % hostname,
            type_="checkbox",
            value=str(colspan),
            class_="failed" if host.discovery_failed() else None,
        )
        html.label("", "_c_%s" % hostname)

        table.cell(_("Actions"), css=["buttons"], sortable=False)
        self._show_host_actions(host)

        # Hostname with link to details page (edit host)
        table.cell(_("Host name"))
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
            nodes = host.cluster_nodes()
            assert nodes is not None
            html.icon("cluster", _("This host is a cluster of %s") % ", ".join(nodes))
            html.nbsp()

        html.a(hostname, href=host.edit_url())

        # Show attributes
        for attr in folder_tree().all_host_attributes().values():
            if attr.show_in_table():
                attrname = attr.name()
                if attrname in host.attributes:
                    # Mypy can not help here with the dynamic key
                    tdclass, tdcontent = attr.paint(host.attributes[attrname], hostname)  # type: ignore[literal-required]
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                table.cell(attr.title(), tdcontent, css=[tdclass])

        # Am I authorized?
        reason = host.permissions.reason_why_may_not("read")
        if not reason:
            icon = "authok"
            title = _("You have permission to this host.")
        else:
            icon = "autherr"
            title = reason

        table.cell(_("Auth"), html.render_icon(icon, title), css=["buttons"], sortable=False)

        # Permissions and Contact groups - through complete recursion and inhertance
        permitted_groups, host_contact_groups, _use_for_services = host.groups()
        table.cell(
            _("Permissions"),
            HTML.without_escaping(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in permitted_groups]
            ),
        )
        table.cell(
            _("Contact groups"),
            HTML.without_escaping(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in host_contact_groups]
            ),
        )

        if not active_config.wato_hide_hosttags and user.wato_folders_show_tags:
            table.cell(_("Tags"), css=["tag-ellipsis"])
            tag_groups, show_all_code = self._limit_labels(host.tag_groups())
            html.write_html(
                cmk.gui.view_utils.render_tag_groups(
                    tag_groups, "host", with_links=False, request=request
                )
            )
            html.write_html(show_all_code)

        if user.wato_folders_show_labels:
            table.cell(_("Explicit labels"), css=["tag-ellipsis"])
            labels, show_all_code = self._limit_labels(host.labels())
            html.write_html(
                cmk.gui.view_utils.render_labels(
                    labels,
                    "host",
                    with_links=False,
                    label_sources={k: "explicit" for k in labels.keys()},
                    request=request,
                )
            )
            html.write_html(show_all_code)

        # Located in folder
        if self._folder.is_search_folder():
            table.cell(_("Folder"))
            html.a(host.folder().alias_path(), href=host.folder().url())

        quick_setup_source_cell(table, host.locked_by())

    def _limit_labels(self, labels: TagsOrLabels) -> tuple[TagsOrLabels, HTML]:
        show_all, limit = HTML.empty(), 3
        if len(labels) > limit and request.var("_show_all") != "1":
            show_all = HTML.without_escaping(" ") + HTMLWriter.render_a(
                "... (%s)" % _("show all"), href=makeuri(request, [("_show_all", "1")])
            )
            labels = dict(sorted(labels.items())[:limit])
        return labels, show_all

    def _render_contact_group(self, contact_group_names: GroupSpecs, c: _ContactgroupName) -> HTML:
        display_name = contact_group_names.get(c, {"alias": c})["alias"]
        return HTMLWriter.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)

    def _show_host_actions(self, host: Host) -> None:
        html.icon_button(host.edit_url(), _("Edit the properties of this host"), "edit")
        if host.permissions.may("read"):
            if user.may("wato.services"):
                msg = _("Run service discovery")
            else:
                msg = _("Display the services of this host")
            image = "services"
            if host.discovery_failed():
                image = "inventory_failed"
                msg += ". " + _(
                    "The service discovery of this host failed during a previous bulk service discovery."
                )
            html.icon_button(host.services_url(), msg, image)

        if user.may("wato.rulesets"):
            html.icon_button(
                host.params_url(),
                _("View the rule based effective parameters of this host"),
                "rulesets",
            )

        if not host.locked():
            if user.may("wato.edit_hosts") and user.may("wato.move_hosts"):
                self._show_move_to_folder_action(host)

            if host.permissions.may("write"):
                delete_host_options: dict[str, str | dict[str, str]] = (
                    confirmed_form_submit_options(
                        title=_("Delete host"),
                        message=_(
                            "This change must be activated via <a href='https://docs.checkmk.com"
                            "/latest/en/wato.html#activate_changes' target='_blank'>Activate cha"
                            "nges</a> before it becomes effective in monitoring."
                        )
                        if host.name()
                        in [h["name"] for h in Query([Hosts.name]).fetchall(sites=sites.live())]
                        else None,
                        confirm_text=_("Yes, delete host"),
                        cancel_text=_("No, keep host"),
                        suffix=host.name(),
                    )
                )
                html.icon_button(
                    url=None,
                    onclick="cmk.selection.execute_bulk_action_for_single_host(this,"
                    " cmk.page_menu.confirmed_form_submit, %s); cmk.popup_menu.close_popup()"
                    % json.dumps(
                        [
                            "hosts",
                            "_bulk_delete",
                            delete_host_options,
                        ],
                    ),
                    title=_("Delete host"),
                    icon="delete",
                )

            self._show_host_actions_menu(host)

    def _show_host_actions_menu(self, host: Host) -> None:
        action_menu_show_flags: list[str] = []
        if not host.locked() and user.may("wato.manage_hosts"):
            if not is_locked_by_quick_setup(host.locked_by()):
                action_menu_show_flags.append("show_delete_link")

            if user.may("wato.clone_hosts"):
                action_menu_show_flags.append("show_clone_link")

        if not self._folder.locked_hosts() and user.may("wato.parentscan"):
            action_menu_show_flags.append("show_parentscan_link")

        if user.may("wato.manage_hosts"):
            action_menu_show_flags.append("show_remove_tls_link")

        if action_menu_show_flags:
            url_vars: HTTPVariables = [
                ("hostname", host.name()),
                *[(flag_name, True) for flag_name in action_menu_show_flags],
            ]
            html.popup_trigger(
                html.render_icon("menu", _("Open the host action menu"), cssclass="iconbutton"),
                f"host_action_menu_{host.name()}",
                MethodAjax(endpoint="host_action_menu", url_vars=url_vars),
            )

    def _delete_hosts(self, host_names: Sequence[HostName]) -> ActionResult:
        self._folder.delete_hosts(
            host_names,
            automation=delete_hosts,
            pprint_value=active_config.wato_pprint_config,
            debug=active_config.debug,
        )
        flash(_("Successfully deleted %d hosts") % len(host_names))
        return redirect(self._folder.url())

    def _render_bulk_move_form(self) -> HTML:
        with output_funnel.plugged():
            form_name = "form_hosts"
            dropdown = WatoFolderChoices(html_attrs={"form": form_name})
            dropdown.render_input("_bulk_moveto", "")
            html.button("_bulk_move", _("Move"), form=form_name)
            return HTML.without_escaping(output_funnel.drain())


# TODO: Split this into one base class and one subclass for folder and hosts
class PageAjaxPopupMoveToFolder(AjaxPage):
    """Renders the popup menu contents for either moving a host or a folder to another folder"""

    @override
    def _from_vars(self) -> None:
        self._what = request.var("what")
        if self._what not in ["host", "folder"]:
            raise NotImplementedError()

        self._ident = request.var("ident")

        self._back_url = request.get_url_input("back_url")
        if not self._back_url or not self._back_url.startswith("wato.py"):
            raise MKUserError("back_url", _("Invalid back URL provided."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    @override
    def handle_page(self, config: Config) -> None:
        self._handle_exc(config, self.page)

    @override
    def page(self, config: Config) -> PageResult:
        html.span(self._move_title())

        choices = self._get_choices()
        if not choices:
            html.write_text_permissive(_("No valid target folder."))
            return None

        html.dropdown(
            "_host_move_%s" % self._ident,
            choices=choices,
            deflt="@",
            size=10,
            onchange=f"location.href='{self._back_url}&_ident={self._ident}&_move_{self._what}_to=' + this.value;",
        )
        return None

    def _move_title(self) -> str:
        if self._what == "host":
            return _("Move this host to:")
        return _("Move this folder to:")

    def _get_choices(self) -> Choices:
        choices: Choices = [
            ("@", _("(select target folder)")),
        ]

        if self._what == "host" and self._ident is not None:
            host = Host.host(HostName(self._ident))
            if host is not None:
                choices += host.folder().choices_for_moving_host()

        elif self._what == "folder" and self._ident is not None:
            folder = folder_tree().folder(self._ident)
            choices += folder.choices_for_moving_folder()

        else:
            raise NotImplementedError()

        return choices


class ABCFolderMode(WatoMode, abc.ABC):
    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    def __init__(self, is_new: bool) -> None:
        super().__init__()
        self._is_new = is_new
        self._folder = self._init_folder()

    @abc.abstractmethod
    def _init_folder(self) -> Folder:
        # TODO: Needed to make pylint know the correct type of the return value.
        # Will be cleaned up in future when typing is established
        return folder_tree().root_folder()

    @abc.abstractmethod
    def _save(self, title: str, attributes: HostAttributes) -> None:
        raise NotImplementedError()

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        is_enabled = (
            self._is_new
            or not folder_from_request(
                request.var("folder"), request.get_ascii_input("host")
            ).locked()
        )

        # When backfolder is set, we have the special situation that we want to redirect the user
        # two breadcrumb layers up. This is a very specific case, so we realize this locally instead
        # of using a generic approach. Just like it done locally by the action method.
        if (backfolder := request.var("backfolder")) is not None:
            breadcrumb = make_folder_breadcrumb(folder_tree().folder(backfolder))
            breadcrumb.append(self._breadcrumb_item())

        return make_simple_form_page_menu(
            _("Folder"),
            breadcrumb,
            form_name="edit_host",
            button_name="_save",
            save_is_enabled=is_enabled,
        )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        if (backfolder := request.var("backfolder")) is not None:
            # Edit icon on subfolder preview should bring user back to parent folder
            folder = folder_tree().folder(backfolder)
        else:
            folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))

        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=folder.path()))

        # Title
        title = TextInput().from_html_vars("title")
        TextInput(allow_empty=False).validate_value(title, "title")

        attributes = collect_attributes("folder", new=self._is_new)
        self._save(title, attributes)

        return redirect(mode_url("folder", folder=folder.path()))

    # TODO: Clean this method up! Split new/edit handling to sub classes
    @override
    def page(self) -> None:
        new = self._is_new
        folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        folder.permissions.need_permission("read")

        if new and folder.locked():
            folder.show_locking_information()

        with html.form_context("edit_host", method="POST"):
            # title
            basic_attributes: list[tuple[str, ValueSpec, str]] = [
                ("title", TextInput(title=_("Title")), "" if new else self._folder.title()),
            ]
            html.set_focus("title")

            # folder name (omit this for editing root folder)
            if not active_config.wato_hide_filenames:
                folder_name_title = _("Internal directory name")
                folder_name_help = _(
                    "This is the name of subdirectory where the files and "
                    "other folders will be created. You cannot change this later."
                )
                if new:
                    basic_attributes += [
                        (
                            "name",
                            TextInput(
                                title=folder_name_title,
                                help=folder_name_help,
                            ),
                            self._folder.name(),
                        ),
                    ]
                elif not folder.is_root():
                    basic_attributes += [
                        (
                            "name",
                            FixedValue(
                                value=self._folder.name(),
                                title=folder_name_title,
                                help=folder_name_help,
                            ),
                            self._folder.name(),
                        ),
                    ]

            configure_attributes(
                new=new,
                hosts={"folder": (myself := None if new else folder)},
                for_what="folder",
                parent=folder if new else folder.parent(),
                myself=myself,
                basic_attributes=basic_attributes,
            )

            forms.end()
            html.hidden_fields()


class ModeEditFolder(ABCFolderMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "editfolder"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]

    def __init__(self) -> None:
        super().__init__(is_new=False)

    @override
    def _init_folder(self) -> Folder:
        return folder_from_request(request.var("folder"), request.get_ascii_input("host"))

    @override
    def title(self) -> str:
        return _("Folder properties")

    @override
    def _save(self, title: str, attributes: HostAttributes) -> None:
        self._folder.edit(title, attributes, pprint_value=active_config.wato_pprint_config)


class ModeCreateFolder(ABCFolderMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "newfolder"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_folders"]

    def __init__(self) -> None:
        super().__init__(is_new=True)

    @override
    def _init_folder(self) -> Folder:
        return folder_tree().root_folder()

    @override
    def title(self) -> str:
        return _("Add folder")

    @override
    def _save(self, title: str, attributes: HostAttributes) -> None:
        parent_folder = folder_from_request(request.var("folder"), request.get_ascii_input("host"))
        if not active_config.wato_hide_filenames:
            name = request.get_ascii_input_mandatory("name", "").strip()
            check_wato_foldername("name", name)
        else:
            name = find_available_folder_name(title, parent_folder)

        parent_folder.create_subfolder(
            name, title, attributes, pprint_value=active_config.wato_pprint_config
        )


class PageAjaxSetFoldertree(AjaxPage):
    @override
    def page(self, config: Config) -> PageResult:
        check_csrf_token()
        api_request = self.webapi_request()
        user.save_file("foldertree", (api_request.get("topic"), api_request.get("target")))

        return None
