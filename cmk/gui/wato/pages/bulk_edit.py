#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Change the attributes of a number of selected hosts at once. Also the
cleanup is implemented here: the bulk removal of explicit attribute
values."""

from hashlib import sha256
from typing import Type, Optional

from six import ensure_binary

from cmk.gui.globals import html
from cmk.gui.i18n import _
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import PageMenu, make_simple_form_page_menu

from cmk.gui.plugins.wato.utils import (
    mode_registry,
    configure_attributes,
    get_hostnames_from_checkboxes,
    get_hosts_from_checkboxes,
)
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, ActionResult, redirect, mode_url
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.utils.flashed_messages import flash


@mode_registry.register
class ModeBulkEdit(WatoMode):
    @classmethod
    def name(cls):
        return "bulkedit"

    @classmethod
    def permissions(cls):
        return ["hosts", "edit_hosts"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def title(self):
        return _("Bulk edit hosts")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            breadcrumb,
            form_name="edit_host",
            button_name="_save",
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return None

        config.user.need_permission("wato.edit_hosts")

        changed_attributes = watolib.collect_attributes("bulk", new=False)
        host_names = get_hostnames_from_checkboxes()
        for host_name in host_names:
            host = watolib.Folder.current().host(host_name)
            host.update_attributes(changed_attributes)
            # call_hook_hosts_changed() is called too often.
            # Either offer API in class Host for bulk change or
            # delay saving until end somehow

        flash(_("Edited %d hosts") % len(host_names))
        return redirect(mode_url("folder", folder=watolib.Folder.current().path()))

    def page(self) -> None:
        host_names = get_hostnames_from_checkboxes()
        hosts = {host_name: watolib.Folder.current().host(host_name) for host_name in host_names}
        current_host_hash = sha256(ensure_binary(repr(hosts))).hexdigest()

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

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def _from_vars(self):
        self._folder = watolib.Folder.current()

    def title(self):
        return _("Bulk removal of explicit attributes")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        hosts = get_hosts_from_checkboxes()

        return make_simple_form_page_menu(
            breadcrumb,
            form_name="bulkcleanup",
            button_name="_save",
            save_is_enabled=bool(self._get_attributes_for_bulk_cleanup(hosts)),
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return None

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

        return redirect(mode_url("folder", folder=self._folder.path()))

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
        self._select_attributes_for_bulk_cleanup(hosts)
        html.hidden_fields()
        html.end_form()

    def _select_attributes_for_bulk_cleanup(self, hosts):
        attributes = self._get_attributes_for_bulk_cleanup(hosts)

        for attr, is_inherited, num_haveit in attributes:
            # Legend and Help
            forms.section(attr.title())

            if attr.is_mandatory() and not is_inherited:
                html.write_text(
                    _("This attribute is mandatory and there is no value "
                      "defined in the host list or any parent folder."))
            else:
                label = "clean this attribute on <b>%s</b> hosts" % \
                    (num_haveit == len(hosts) and "all selected" or str(num_haveit))
                html.checkbox("_clean_%s" % attr.name(), False, label=label)
            html.help(attr.help())

        forms.end()

        if not attributes:
            html.write_text(_("The selected hosts have no explicit attributes"))

    def _get_attributes_for_bulk_cleanup(self, hosts):
        attributes = []
        for attr in host_attribute_registry.get_sorted_host_attributes():
            attrname = attr.name()

            if not attr.show_in_host_cleanup():
                continue

            # only show attributes that at least on host have set
            num_haveit = 0
            for host in hosts:
                if host.has_explicit_attribute(attrname):
                    num_haveit += 1

            if not num_haveit:
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

            attributes.append((attr, is_inherited, num_haveit))
        return attributes
