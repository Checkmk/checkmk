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
"""Change the attributes of a number of selected hosts at once. Also the
cleanup is implemented here: the bulk removal of explicit attribute
values."""

from hashlib import sha256

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms

from cmk.gui.plugins.wato.utils import (
    mode_registry,
    configure_attributes,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
)
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.watolib.host_attributes import host_attribute_registry

from cmk.gui.globals import html
from cmk.gui.i18n import _


@mode_registry.register
class ModeBulkEdit(WatoMode):
    @classmethod
    def name(cls):
        return "bulkedit"

    @classmethod
    def permissions(cls):
        return ["hosts", "edit_hosts"]

    def title(self):
        return _("Bulk edit hosts")

    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]),
                            "back")

    def action(self):
        if not html.check_transaction():
            return

        config.user.need_permission("wato.edit_hosts")

        changed_attributes = watolib.collect_attributes("bulk", new=False)
        host_names = get_hostnames_from_checkboxes()
        for host_name in host_names:
            host = watolib.Folder.current().host(host_name)
            host.update_attributes(changed_attributes)
            # call_hook_hosts_changed() is called too often.
            # Either offer API in class Host for bulk change or
            # delay saving until end somehow

        return "folder", _("Edited %d hosts") % len(host_names)

    def page(self):
        host_names = get_hostnames_from_checkboxes()
        hosts = dict([
            (host_name, watolib.Folder.current().host(host_name)) for host_name in host_names
        ])
        current_host_hash = sha256(repr(hosts))

        # When bulk edit has been made with some hosts, then other hosts have been selected
        # and then another bulk edit has made, the attributes need to be reset before
        # rendering the form. Otherwise the second edit will have the attributes of the
        # first set.
        host_hash = html.request.var("host_hash")
        if not host_hash or host_hash != current_host_hash:
            html.request.del_vars(prefix="attr_")
            html.request.del_vars(prefix="bulk_change_")

        html.p("%s%s %s" %
               (_("You have selected <b>%d</b> hosts for bulk edit. You can now change "
                  "host attributes for all selected hosts at once. ") % len(hosts),
                _("If a select is set to <i>don't change</i> then currenty not all selected "
                  "hosts share the same setting for this attribute. "
                  "If you leave that selection, all hosts will keep their individual settings."),
                _("In case you want to <i>unset</i> attributes on multiple hosts, you need to "
                  "use the <i>bulk cleanup</i> action instead of bulk edit.")))

        html.begin_form("edit_host", method="POST")
        html.prevent_password_auto_completion()
        html.hidden_field("host_hash", current_host_hash)
        configure_attributes(False, hosts, "bulk", parent=watolib.Folder.current())
        forms.end()
        html.button("_save", _("Save & Finish"))
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeBulkCleanup(WatoMode):
    @classmethod
    def name(cls):
        return "bulkcleanup"

    @classmethod
    def permissions(cls):
        return ["hosts", "edit_hosts"]

    def _from_vars(self):
        self._folder = watolib.Folder.current()

    def title(self):
        return _("Bulk removal of explicit attributes")

    def buttons(self):
        html.context_button(_("Back"), self._folder.url(), "back")

    def action(self):
        if not html.check_transaction():
            return

        config.user.need_permission("wato.edit_hosts")
        to_clean = self._bulk_collect_cleaned_attributes()
        if "contactgroups" in to_clean:
            self._folder.need_permission("write")

        hosts = get_hosts_from_checkboxes()

        # Check all permissions before doing any edit
        for host in hosts:
            host.need_permission("write")

        for host in hosts:
            host.clean_attributes(to_clean)

        return "folder"

    def _bulk_collect_cleaned_attributes(self):
        to_clean = []
        for attr in host_attribute_registry.attributes():
            attrname = attr.name()
            if html.get_checkbox("_clean_" + attrname) is True:
                to_clean.append(attrname)
        return to_clean

    def page(self):
        hosts = get_hosts_from_checkboxes()

        html.p(
            _("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
              "explicit attribute values from hosts. The hosts will then inherit attributes "
              "configured at the host list or folders or simply fall back to the builtin "
              "default values.") % len(hosts))

        html.begin_form("bulkcleanup", method="POST")
        forms.header(_("Attributes to remove from hosts"))
        if not self._select_attributes_for_bulk_cleanup(hosts):
            forms.end()
            html.write_text(_("The selected hosts have no explicit attributes"))
        else:
            forms.end()
            html.button("_save", _("Save & Finish"))
        html.hidden_fields()
        html.end_form()

    def _select_attributes_for_bulk_cleanup(self, hosts):
        num_shown = 0
        for attr in host_attribute_registry.get_sorted_host_attributes():
            attrname = attr.name()

            if not attr.show_in_host_cleanup():
                continue

            # only show attributes that at least on host have set
            num_haveit = 0
            for host in hosts:
                if host.has_explicit_attribute(attrname):
                    num_haveit += 1

            if num_haveit == 0:
                continue

            # If the attribute is mandatory and no value is inherited
            # by file or folder, the attribute cannot be cleaned.
            container = self._folder
            is_inherited = False
            while container:
                if container.has_explicit_attribute(attrname):
                    is_inherited = True
                    break
                container = container.parent()

            num_shown += 1

            # Legend and Help
            forms.section(attr.title())

            if attr.is_mandatory() and not is_inherited:
                html.write_text(
                    _("This attribute is mandatory and there is no value "
                      "defined in the host list or any parent folder."))
            else:
                label = "clean this attribute on <b>%s</b> hosts" % \
                    (num_haveit == len(hosts) and "all selected" or str(num_haveit))
                html.checkbox("_clean_%s" % attrname, False, label=label)
            html.help(attr.help())

        return num_shown > 0
