#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Modes for managing folders"""

import abc
import json
import six

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.utils as utils
from cmk.gui.table import table_element
import cmk.gui.weblib as weblib
import cmk.gui.forms as forms
import cmk.gui.view_utils

from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.watolib.groups import load_contact_group_information
from cmk.gui.plugins.wato.utils import (
    mode_registry,
    configure_attributes,
    get_hostnames_from_checkboxes,
)
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import wato_confirm
from cmk.gui.plugins.wato.utils.main_menu import MainMenu, MenuItem
from cmk.gui.plugins.wato.utils.context_buttons import folder_status_button, global_buttons

from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    TextUnicode,
    TextAscii,
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
        super(ModeFolder, self).__init__()
        self._folder = watolib.Folder.current()

    def title(self):
        return self._folder.title()

    def buttons(self):
        global_buttons()
        if not self._folder.is_disk_folder():
            html.context_button(_("Back"), self._folder.parent().url(), "back")
            html.context_button(_("Refine search"), self._folder.url([("mode", "search")]),
                                "search")
            return

        if config.user.may("wato.rulesets") or config.user.may("wato.seeall"):
            html.context_button(_("Rulesets"),
                                watolib.folder_preserving_link([("mode", "ruleeditor")]),
                                "rulesets")
            html.context_button(_("Manual checks"),
                                watolib.folder_preserving_link([("mode", "static_checks")]),
                                "static_checks")
        if self._folder.may("read"):
            html.context_button(_("Folder properties"),
                                self._folder.edit_url(backfolder=self._folder), "edit")
        if not self._folder.locked_subfolders() and config.user.may(
                "wato.manage_folders") and self._folder.may("write"):
            html.context_button(_("New folder"), self._folder.url([("mode", "newfolder")]),
                                "newfolder")
        if not self._folder.locked_hosts() and config.user.may(
                "wato.manage_hosts") and self._folder.may("write"):
            html.context_button(_("New host"), self._folder.url([("mode", "newhost")]), "new")
            html.context_button(_("New cluster"), self._folder.url([("mode", "newcluster")]),
                                "new_cluster")
            html.context_button(_("Bulk import"), self._folder.url([("mode", "bulk_import")]),
                                "bulk_import")
        if config.user.may("wato.services"):
            html.context_button(_("Bulk discovery"),
                                self._folder.url([("mode", "bulkinventory"), ("all", "1")]),
                                "inventory")
        if config.user.may("wato.rename_hosts"):
            html.context_button(_("Bulk renaming"),
                                self._folder.url([("mode", "bulk_rename_host")]), "rename_host")
        if config.user.may("wato.custom_attributes"):
            html.context_button(_("Custom attributes"),
                                watolib.folder_preserving_link([("mode", "host_attrs")]),
                                "custom_attr")
        if not self._folder.locked_hosts() and config.user.may(
                "wato.parentscan") and self._folder.may("write"):
            html.context_button(_("Parent scan"),
                                self._folder.url([("mode", "parentscan"), ("all", "1")]),
                                "parentscan")
        folder_status_button()
        if config.user.may("wato.random_hosts"):
            html.context_button(_("Random hosts"), self._folder.url([("mode", "random_hosts")]),
                                "random")
        html.context_button(_("Search"), watolib.folder_preserving_link([("mode", "search")]),
                            "search")

        if config.user.may("wato.dcd_connections"):
            html.context_button(_("Dynamic config"),
                                watolib.folder_preserving_link([("mode", "dcd_connections")]),
                                "dcd_connections")

    def action(self):
        if html.request.var("_search"):  # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.request.var("_delete_folder"):
            if html.transaction_valid():
                return self._delete_subfolder_after_confirm(html.request.var("_delete_folder"))
            return

        elif html.request.has_var("_move_folder_to"):
            if html.check_transaction():
                what_folder = watolib.Folder.folder(html.request.var("_ident"))
                target_folder = watolib.Folder.folder(html.request.var("_move_folder_to"))
                watolib.Folder.current().move_subfolder_to(what_folder, target_folder)
            return

        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.request.var("_delete_host")
        if delname and watolib.Folder.current().has_host(delname):
            return delete_host_after_confirm(delname)

        # Move single hosts to other folders
        if html.request.has_var("_move_host_to"):
            hostname = html.request.var("_ident")
            if hostname:
                target_folder = watolib.Folder.folder(html.request.var("_move_host_to"))
                watolib.Folder.current().move_hosts([hostname], target_folder)
                return

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        # Host table: No error message on search filter reset
        if html.request.var("_hosts_reset_sorting") or html.request.var("_hosts_sort"):
            return

        selected_host_names = get_hostnames_from_checkboxes()
        if len(selected_host_names) == 0:
            raise MKUserError(None,
                              _("Please select some hosts before doing bulk operations on hosts."))

        if html.request.var("_bulk_inventory"):
            return "bulkinventory"

        elif html.request.var("_parentscan"):
            return "parentscan"

        # Deletion
        if html.request.var("_bulk_delete"):
            return self._delete_hosts_after_confirm(selected_host_names)

        # Move
        elif html.request.var("_bulk_move"):
            target_folder_path = html.request.var("bulk_moveto",
                                                  html.request.var("_top_bulk_moveto"))
            if target_folder_path == "@":
                raise MKUserError("bulk_moveto", _("Please select the destination folder"))
            target_folder = watolib.Folder.folder(target_folder_path)
            watolib.Folder.current().move_hosts(selected_host_names, target_folder)
            return None, _("Moved %d hosts to %s") % (len(selected_host_names),
                                                      target_folder.title())

        # Move to target folder (from import)
        elif html.request.var("_bulk_movetotarget"):
            return self._move_to_imported_folders(selected_host_names)

        elif html.request.var("_bulk_edit"):
            return "bulkedit"

        elif html.request.var("_bulk_cleanup"):
            return "bulkcleanup"

    def _delete_subfolder_after_confirm(self, subfolder_name):
        subfolder = self._folder.subfolder(subfolder_name)
        msg = _("Do you really want to delete the folder %s?") % subfolder.title()
        if not config.wato_hide_filenames:
            msg += _(" Its directory is <tt>%s</tt>.") % subfolder.filesystem_path()
        num_hosts = subfolder.num_hosts_recursively()
        if num_hosts:
            msg += _(
                " The folder contains <b>%d</b> hosts, which will also be deleted!") % num_hosts
        c = wato_confirm(_("Confirm folder deletion"), msg)

        if c:
            self._folder.delete_subfolder(subfolder_name)  # pylint: disable=no-member
            return "folder"
        elif c is False:  # not yet confirmed
            return ""
        return None  # browser reload

    def page(self):
        self._folder.show_breadcrump()

        if not self._folder.may("read"):
            html.message(
                html.render_icon("autherr", cssclass="authicon") + " " +
                self._folder.reason_why_may_not("read"))

        self._folder.show_locking_information()
        self._show_subfolders_of()
        if self._folder.may("read"):
            self._show_hosts()

        if not self._folder.has_hosts():
            if self._folder.is_search_folder():
                html.message(_("No matching hosts found."))
            elif not self._folder.has_subfolders() and self._folder.may("write"):
                self._show_empty_folder_menu()

    def _show_empty_folder_menu(self):
        menu_items = []

        if not self._folder.locked_hosts():
            menu_items.extend([
                MenuItem("newhost", _("Create new host"), "new", "hosts",
                         _("Add a new host to the monitoring (agent must be installed)")),
                MenuItem(
                    "newcluster", _("Create new cluster"), "new_cluster", "hosts",
                    _("Use Check_MK clusters if an item can move from one host "
                      "to another at runtime"))
            ])

        if not self._folder.locked_subfolders():
            menu_items.extend([
                MenuItem(
                    "newfolder", _("Create new folder"), "newfolder", "hosts",
                    _("Folders group your hosts, can inherit attributes and can have permissions."))
            ])

        MainMenu(menu_items).show()

    def _show_subfolders_of(self):
        if self._folder.has_subfolders():
            html.open_div(
                class_="folders")  # This won't hurt even if there are no visible subfolders
            for subfolder in self._folder.visible_subfolders_sorted_by_title():  # pylint: disable=no-member
                self._show_subfolder(subfolder)
            html.close_div()
            html.div('', class_="folder_foot")

    def _show_subfolder(self, subfolder):
        html.open_div(class_=["floatfolder", "unlocked" if subfolder.may("read") else "locked"],
                      id_="folder_%s" % subfolder.name(),
                      onclick="cmk.wato.open_folder(event, \'%s\');" % subfolder.url())
        self._show_subfolder_hoverarea(subfolder)
        self._show_subfolder_infos(subfolder)
        self._show_subfolder_title(subfolder)
        html.close_div()  # floatfolder

    def _show_subfolder_hoverarea(self, subfolder):
        # Only make folder openable when permitted to edit
        if subfolder.may("read"):
            html.open_div(class_="hoverarea",
                          onmouseover="cmk.wato.toggle_folder(event, this, true);",
                          onmouseout="cmk.wato.toggle_folder(event, this, false);")
            self._show_subfolder_buttons(subfolder)
            html.close_div()  # hoverarea
        else:
            html.icon(html.strip_tags(subfolder.reason_why_may_not("read")),
                      "autherr",
                      class_=["autherr"])
            html.div('', class_="hoverarea")

    def _show_subfolder_title(self, subfolder):
        title = subfolder.title()
        if not config.wato_hide_filenames:
            title += ' (%s)' % subfolder.name()

        html.open_div(class_="title", title=title)
        if subfolder.may("read"):
            html.a(subfolder.title(), href=subfolder.url())
        else:
            html.write_text(subfolder.title())
        html.close_div()

    def _show_subfolder_buttons(self, subfolder):
        self._show_subfolder_edit_button(subfolder)

        if not subfolder.locked_subfolders() and not subfolder.locked():
            if subfolder.may("write") and config.user.may("wato.manage_folders"):
                self._show_move_to_folder_action(subfolder)
                self._show_subfolder_delete_button(subfolder)

    def _show_subfolder_edit_button(self, subfolder):
        html.icon_button(
            subfolder.edit_url(subfolder.parent()),
            _("Edit the properties of this folder"),
            "edit",
            id_='edit_' + subfolder.name(),
            cssclass='edit',
            style='display:none',
        )

    def _show_subfolder_delete_button(self, subfolder):
        html.icon_button(
            watolib.make_action_link([("mode", "folder"), ("_delete_folder", subfolder.name())]),
            _("Delete this folder"),
            "delete",
            id_='delete_' + subfolder.name(),
            cssclass='delete',
            style='display:none',
        )

    def _show_subfolder_infos(self, subfolder):
        html.open_div(class_="infos")
        html.open_div(class_="infos_content")
        groups = load_contact_group_information()
        permitted_groups, _folder_contact_groups, _use_for_services = subfolder.groups()
        for num, pg in enumerate(permitted_groups):
            cgalias = groups.get(pg, {'alias': pg})['alias']
            html.icon(_("Contactgroups that have permission on this folder"), "contactgroups")
            html.write_text(' %s' % cgalias)
            html.br()
            if num > 1 and len(permitted_groups) > 4:
                html.write_text(
                    _('<i>%d more contact groups</i><br>') % (len(permitted_groups) - num - 1))
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
            html.render_icon("move",
                             title=_("Move this %s to another folder") % what_title,
                             cssclass="iconbutton"),
            ident="move_" + obj.name(),
            what="move_to_folder",
            url_vars=[
                ("what", what),
                ("ident", ident),
                ("back_url", html.makeactionuri([])),
            ],
            style=style,
        )

    def _show_hosts(self):
        if not self._folder.has_hosts():
            return

        show_checkboxes = html.request.var('show_checkboxes', '0') == '1'

        hostnames = self._folder.hosts().keys()
        hostnames.sort(key=utils.key_num_split)
        search_text = html.request.var("search")

        # Helper function for showing bulk actions. This is needed at the bottom
        # of the table of hosts and - if there are more than just a few - also
        # at the top of the table.
        search_shown = False

        # Show table of hosts in this folder
        html.begin_form("hosts", method="POST")
        with table_element("hosts", title=_("Hosts"), searchable=False,
                           omit_empty_columns=True) as table:

            # Remember if that host has a target folder (i.e. was imported with
            # a folder information but not yet moved to that folder). If at least
            # one host has a target folder, then we show an additional bulk action.
            at_least_one_imported = False
            more_than_ten_items = False
            for num, hostname in enumerate(hostnames):
                if search_text and (search_text.lower() not in hostname.lower()):
                    continue

                host = self._folder.host(hostname)
                effective = host.effective_attributes()

                if effective.get("imported_folder"):
                    at_least_one_imported = True

                if num == 11:
                    more_than_ten_items = True

            # Compute colspan for bulk actions
            colspan = 6
            for attr in host_attribute_registry.attributes():
                if attr.show_in_table():
                    colspan += 1
            if not self._folder.locked_hosts() and config.user.may(
                    "wato.edit_hosts") and config.user.may("wato.move_hosts"):
                colspan += 1
            if show_checkboxes:
                colspan += 1
            if self._folder.is_search_folder():
                colspan += 1

            # Add the bulk action buttons also to the top of the table when this
            # list shows more than 10 rows
            if more_than_ten_items and \
                (config.user.may("wato.edit_hosts") or config.user.may("wato.manage_hosts")):
                self._bulk_actions(table, at_least_one_imported, True, True, colspan,
                                   show_checkboxes)
                search_shown = True

            contact_group_names = load_contact_group_information()

            host_errors = self._folder.host_validation_errors()
            rendered_hosts = []

            # Now loop again over all hosts and display them
            for hostname in hostnames:
                self._show_host_row(rendered_hosts, table, hostname, search_text, show_checkboxes,
                                    colspan, host_errors, contact_group_names)

            if config.user.may("wato.edit_hosts") or config.user.may("wato.manage_hosts"):
                self._bulk_actions(table, at_least_one_imported, False, not search_shown, colspan,
                                   show_checkboxes)

        html.hidden_fields()
        html.end_form()

        selected = weblib.get_rowselection('wato-folder-/' + self._folder.path())

        row_count = len(rendered_hosts)
        headinfo = "%d %s" % (row_count, _("host") if row_count == 1 else _("hosts"))
        html.javascript("cmk.utils.update_header_info(%s);" % json.dumps(headinfo))

        if show_checkboxes:
            selection_properties = {
                "page_id": "wato-folder-%s" % ('/' + self._folder.path()),
                "selection_id": weblib.selection_id(),
                "selected_rows": selected,
            }
            html.javascript('cmk.selection.init_rowselect(%s);' %
                            (json.dumps(selection_properties)))

    def _show_host_row(self, rendered_hosts, table, hostname, search_text, show_checkboxes, colspan,
                       host_errors, contact_group_names):
        if search_text and (search_text.lower() not in hostname.lower()):
            return

        host = self._folder.host(hostname)
        rendered_hosts.append(hostname)
        effective = host.effective_attributes()

        table.row()

        # Column with actions (buttons)

        if show_checkboxes:
            table.cell(html.render_input("_toggle_group",
                                         type_="button",
                                         class_="checkgroup",
                                         onclick="cmk.selection.toggle_all_rows();",
                                         value='X'),
                       sortable=False,
                       css="checkbox")
            # Use CSS class "failed" in order to provide information about
            # selective toggling inventory-failed hosts for Javascript
            html.input(name="_c_%s" % hostname,
                       type_="checkbox",
                       value=colspan,
                       class_="failed" if host.discovery_failed() else None)
            html.label("", "_c_%s" % hostname)

        table.cell(_("Actions"), css="buttons", sortable=False)
        self._show_host_actions(host)

        # Hostname with link to details page (edit host)
        table.cell(_("Hostname"))
        errors = host_errors.get(hostname, []) + host.validation_errors()
        if errors:
            msg = _("Warning: This host has an invalid configuration: ")
            msg += ", ".join(errors)
            html.icon(msg, "validation_error")
            html.nbsp()

        if host.is_offline():
            html.icon(_("This host is disabled"), "disabled")
            html.nbsp()

        if host.is_cluster():
            html.icon(
                _("This host is a cluster of %s") % ", ".join(host.cluster_nodes()), "cluster")
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
                table.cell(attr.title(), html.attrencode(tdcontent), css=tdclass)

        # Am I authorized?
        reason = host.reason_why_may_not("read")
        if not reason:
            icon = "authok"
            title = _("You have permission to this host.")
        else:
            icon = "autherr"
            title = html.strip_tags(reason)

        table.cell(_('Auth'), html.render_icon(icon, title), css="buttons", sortable=False)

        # Permissions and Contact groups - through complete recursion and inhertance
        permitted_groups, host_contact_groups, _use_for_services = host.groups()
        table.cell(
            _("Permissions"),
            HTML(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in permitted_groups]))
        table.cell(
            _("Contact Groups"),
            HTML(", ").join(
                [self._render_contact_group(contact_group_names, g) for g in host_contact_groups]))

        if not config.wato_hide_hosttags:
            table.cell(_("Tags"), css="tag-ellipsis")
            tag_groups, show_all_code = self._limit_labels(host.tag_groups())
            html.write(cmk.gui.view_utils.render_tag_groups(tag_groups, "host", with_links=False))
            html.write(show_all_code)

        table.cell(_("Explicit labels"), css="tag-ellipsis")
        labels, show_all_code = self._limit_labels(host.labels())
        html.write(
            cmk.gui.view_utils.render_labels(labels,
                                             "host",
                                             with_links=False,
                                             label_sources={k: "explicit" for k in labels.keys()}))
        html.write(show_all_code)

        # Located in folder
        if self._folder.is_search_folder():
            table.cell(_("Folder"))
            html.a(host.folder().alias_path(), href=host.folder().url())

    def _limit_labels(self, labels):
        show_all, limit = "", 3
        if len(labels) > limit and html.request.var("_show_all") != "1":
            show_all = " %s" % html.render_a("... (%s)" % _("show all"),
                                             href=html.makeuri([("_show_all", "1")]))
            labels = dict(sorted(labels.items())[:limit])
        return labels, show_all

    def _render_contact_group(self, contact_group_names, c):
        display_name = contact_group_names.get(c, {'alias': c})['alias']
        return html.render_a(display_name, "wato.py?mode=edit_contact_group&edit=%s" % c)

    def _show_host_actions(self, host):
        html.icon_button(host.edit_url(), _("Edit the properties of this host"), "edit")
        if config.user.may("wato.rulesets"):
            html.icon_button(host.params_url(), _("View the rule based parameters of this host"),
                             "rulesets")

        if host.may('read'):
            if config.user.may("wato.services"):
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
            if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
                self._show_move_to_folder_action(host)

            if config.user.may("wato.manage_hosts"):
                if config.user.may("wato.clone_hosts"):
                    html.icon_button(host.clone_url(), _("Create a clone of this host"), "insert")
                delete_url = watolib.make_action_link([("mode", "folder"),
                                                       ("_delete_host", host.name())])
                html.icon_button(delete_url, _("Delete this host"), "delete")

    def _bulk_actions(self, table, at_least_one_imported, top, withsearch, colspan,
                      show_checkboxes):
        table.row(collect_headers=False, fixed=True)
        table.cell(css="bulksearch", colspan=3)

        if not show_checkboxes:
            onclick_uri = html.makeuri([('show_checkboxes', '1'),
                                        ('selection', weblib.selection_id())])
            checkbox_title = _('Show Checkboxes and bulk actions')
        else:
            onclick_uri = html.makeuri([('show_checkboxes', '0')])
            checkbox_title = _('Hide Checkboxes and bulk actions')

        html.toggle_button("checkbox_on",
                           show_checkboxes,
                           "checkbox",
                           title=checkbox_title,
                           onclick="location.href=\'%s\'" % onclick_uri,
                           is_context_button=False)

        if withsearch:
            html.text_input("search")
            html.button("_search", _("Search"))
            html.set_focus("search")
        table.cell(css="bulkactions", colspan=colspan - 3)
        html.write_text(' ' + _("Selected hosts:\n"))

        if not self._folder.locked_hosts():
            if config.user.may("wato.manage_hosts"):
                html.button("_bulk_delete", _("Delete"))
            if config.user.may("wato.edit_hosts"):
                html.button("_bulk_edit", _("Edit"))
                html.button("_bulk_cleanup", _("Cleanup"))

        if config.user.may("wato.services"):
            html.button("_bulk_inventory", _("Discovery"))

        if not self._folder.locked_hosts():
            if config.user.may("wato.parentscan"):
                html.button("_parentscan", _("Parentscan"))
            if config.user.may("wato.edit_hosts") and config.user.may("wato.move_hosts"):
                self._host_bulk_move_to_folder_combo(top)
                if at_least_one_imported:
                    html.button("_bulk_movetotarget", _("Move to Target Folders"))

    def _delete_hosts_after_confirm(self, host_names):
        c = wato_confirm(
            _("Confirm deletion of %d hosts") % len(host_names),
            _("Do you really want to delete the %d selected hosts?") % len(host_names))
        if c:
            self._folder.delete_hosts(host_names)
            return "folder", _("Successfully deleted %d hosts") % len(host_names)
        elif c is False:  # not yet confirmed
            return ""
        return None  # browser reload

    # FIXME: Cleanup
    def _host_bulk_move_to_folder_combo(self, top):
        choices = self._folder.choices_for_moving_host()
        if len(choices):
            choices = [("@", _("(select target folder)"))] + choices
            html.button("_bulk_move", _("Move to:"))
            html.write("&nbsp;")
            field_name = 'bulk_moveto'
            if top:
                field_name = '_top_bulk_moveto'
                if html.request.has_var('bulk_moveto'):
                    html.javascript('cmk.selection.update_bulk_moveto("%s")' %
                                    html.request.var('bulk_moveto', ''))
            html.dropdown(field_name,
                          choices,
                          deflt="@",
                          onchange="cmk.selection.update_bulk_moveto(this.value)",
                          class_='bulk_moveto')

    def _move_to_imported_folders(self, host_names_to_move):
        c = wato_confirm(
            _("Confirm moving hosts"),
            _('You are going to move the selected hosts to folders '
              'representing their original folder location in the system '
              'you did the import from. Please make sure that you have '
              'done an <b>inventory</b> before moving the hosts.'))
        if c is False:  # not yet confirmed
            return ""
        elif not c:
            return None  # browser reload

        # Create groups of hosts with the same target folder
        target_folder_names = {}
        for host_name in host_names_to_move:
            host = self._folder.host(host_name)
            imported_folder_name = host.attribute('imported_folder')
            if imported_folder_name is None:
                continue
            target_folder_names.setdefault(imported_folder_name, []).append(host_name)

            # Remove target folder information, now that the hosts are
            # at their target position.
            host.remove_attribute('imported_folder')

        # Now handle each target folder
        for imported_folder, host_names in target_folder_names.items():
            # Next problem: The folder path in imported_folder refers
            # to the Alias of the folders, not to the internal file
            # name. And we need to create folders not yet existing.
            target_folder = self._create_target_folder_from_aliaspath(imported_folder)
            self._folder.move_hosts(host_names, target_folder)

        return None, _("Successfully moved hosts to their original folder destinations.")

    def _create_target_folder_from_aliaspath(self, aliaspath):
        # The alias path is a '/' separated path of folder titles.
        # An empty path is interpreted as root path. The actual file
        # name is the host list with the name "Hosts".
        if aliaspath == "" or aliaspath == "/":
            folder = watolib.Folder.root_folder()
        else:
            parts = aliaspath.strip("/").split("/")
            folder = watolib.Folder.root_folder()
            while len(parts) > 0:
                # Look in current folder for subfolder with the target name
                subfolder = folder.subfolder_by_title(parts[0])
                if subfolder:
                    folder = subfolder
                else:
                    name = _create_wato_foldername(parts[0], folder)
                    folder = folder.create_subfolder(name, parts[0], {})
                parts = parts[1:]

        return folder


# TODO: Move to WatoHostFolderMode() once mode_edit_host has been migrated
def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        watolib.Folder.current().delete_hosts([delname])
        # Delete host files
        return "folder"
    elif c is False:  # not yet confirmed
        return ""
    return None  # browser reload


# TODO: Split this into one base class and one subclass for folder and hosts
@page_registry.register_page("ajax_popup_move_to_folder")
class ModeAjaxPopupMoveToFolder(AjaxPage):
    """Renders the popup menu contents for either moving a host or a folder to another folder"""
    def _from_vars(self):
        self._what = html.request.var("what")
        if self._what not in ["host", "folder"]:
            raise NotImplementedError()

        self._ident = html.request.var("ident")

        self._back_url = html.get_url_input("back_url")
        if not self._back_url or not self._back_url.startswith("wato.py"):
            raise MKUserError("back_url", _("Invalid back URL provided."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self.page()

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
            size='10',
            onchange="location.href='%s&_ident=%s&_move_%s_to=' + this.value;" %
            (self._back_url, self._ident, self._what),
        )

    def _move_title(self):
        if self._what == "host":
            return _('Move this host to:')
        return _('Move this folder to:')

    def _get_choices(self):
        choices = [
            ("@", _("(select target folder)")),
        ]

        if self._what == "host":
            obj = watolib.Host.host(self._ident)
            choices += obj.folder().choices_for_moving_host()

        elif self._what == "folder":
            obj = watolib.Folder.folder(self._ident)
            choices += obj.choices_for_moving_folder()

        else:
            raise NotImplementedError()

        return choices


class FolderMode(six.with_metaclass(abc.ABCMeta, WatoMode)):
    def __init__(self):
        super(FolderMode, self).__init__()
        self._folder = self._init_folder()

    @abc.abstractmethod
    def _init_folder(self):
        # TODO: Needed to make pylint know the correct type of the return value.
        # Will be cleaned up in future when typing is established
        return watolib.Folder(name=None)

    @abc.abstractmethod
    def _save(self, title, attributes):
        raise NotImplementedError()

    def buttons(self):
        if html.request.has_var("backfolder"):
            back_folder = watolib.Folder.folder(html.request.var("backfolder"))
        else:
            back_folder = self._folder
        html.context_button(_("Back"), back_folder.url(), "back")

    def action(self):
        if not html.check_transaction():
            return "folder"

        # Title
        title = TextUnicode().from_html_vars("title")
        TextUnicode(allow_empty=False).validate_value(title, "title")

        attributes = watolib.collect_attributes("folder", new=self._folder.name() is None)
        self._save(title, attributes)

        # Edit icon on subfolder preview should bring user back to parent folder
        if html.request.has_var("backfolder"):
            watolib.Folder.set_current(watolib.Folder.folder(html.request.var("backfolder")))
        return "folder"

    # TODO: Clean this method up! Split new/edit handling to sub classes
    def page(self):
        new = self._folder.name() is None

        watolib.Folder.current().show_breadcrump()
        watolib.Folder.current().need_permission("read")

        if new and watolib.Folder.current().locked():
            watolib.Folder.current().show_locking_information()

        html.begin_form("edit_host", method="POST")

        # title
        basic_attributes = [
            ("title", TextUnicode(title=_("Title")), self._folder.title()),
        ]
        html.set_focus("title")

        # folder name (omit this for root folder)
        if new or not watolib.Folder.current().is_root():
            if not config.wato_hide_filenames:
                basic_attributes += [
                    ("name",
                     TextAscii(
                         title=_("Internal directory name"),
                         help=_("This is the name of subdirectory where the files and "
                                "other folders will be created. You cannot change this later."),
                     ), self._folder.name()),
                ]

        # Attributes inherited to hosts
        if new:
            parent = watolib.Folder.current()
            myself = None
        else:
            parent = watolib.Folder.current().parent()
            myself = watolib.Folder.current()

        configure_attributes(new=new,
                             hosts={"folder": myself},
                             for_what="folder",
                             parent=parent,
                             myself=myself,
                             basic_attributes=basic_attributes)

        forms.end()
        if new or not watolib.Folder.current().locked():
            html.button("save", _("Save & Finish"), "submit")
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeEditFolder(FolderMode):
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
class ModeCreateFolder(FolderMode):
    @classmethod
    def name(cls):
        return "newfolder"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_folders"]

    def _init_folder(self):
        return watolib.Folder(name=None)

    def title(self):
        return _("Create new folder")

    def _save(self, title, attributes):
        if not config.wato_hide_filenames:
            name = html.request.var("name", "").strip()
            watolib.check_wato_foldername("name", name)
        else:
            name = _create_wato_foldername(title)

        watolib.Folder.current().create_subfolder(name, title, attributes)


# TODO: Move to Folder()?
def _create_wato_foldername(title, in_folder=None):
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
def _convert_title_to_filename(title):
    converted = ""
    for c in title.lower():
        if c == u'ä':
            converted += 'ae'
        elif c == u'ö':
            converted += 'oe'
        elif c == u'ü':
            converted += 'ue'
        elif c == u'ß':
            converted += 'ss'
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return str(converted)


@page_registry.register_page("ajax_set_foldertree")
class ModeAjaxSetFoldertree(AjaxPage):
    def page(self):
        request = self.webapi_request()
        config.user.save_file("foldertree", (request.get('topic'), request.get('target')))
