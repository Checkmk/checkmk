#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Change the attributes of a number of selected hosts at once. Also the
cleanup is implemented here: the bulk removal of explicit attribute
values."""

from collections.abc import Collection, Sequence
from hashlib import sha256
from typing import override

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.host_attributes import (
    ABCHostAttribute,
    all_host_attributes,
    collect_attributes,
    sorted_host_attributes,
)
from cmk.gui.watolib.hosts_and_folders import (
    disk_or_search_folder_from_request,
    Folder,
    Host,
    SearchFolder,
)
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode

from ._bulk_actions import get_hostnames_from_checkboxes, get_hosts_from_checkboxes
from ._host_attributes import configure_attributes


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeBulkEdit)
    mode_registry.register(ModeBulkCleanup)


class ModeBulkEdit(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "bulkedit"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "edit_hosts"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    @override
    def _from_vars(self) -> None:
        self._folder = disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        )

    @override
    def title(self) -> str:
        return _("Bulk edit hosts")

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Hosts"), breadcrumb, form_name="edit_host", button_name="_save"
        )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        user.need_permission("wato.edit_hosts")

        changed_attributes = collect_attributes("bulk", new=False)
        host_names = get_hostnames_from_checkboxes(self._folder)
        for host_name in host_names:
            host = self._folder.load_host(host_name)
            host.update_attributes(
                changed_attributes, pprint_value=active_config.wato_pprint_config
            )
            # call_hook_hosts_changed() is called too often.
            # Either offer API in class Host for bulk change or
            # delay saving until end somehow

        flash(_("Edited %d hosts") % len(host_names))
        return redirect(self._folder.url())

    @override
    def page(self) -> None:
        host_names = get_hostnames_from_checkboxes(self._folder)
        hosts = {host_name: self._folder.load_host(host_name) for host_name in host_names}
        current_host_hash = sha256(repr(hosts).encode()).hexdigest()

        # When bulk edit has been made with some hosts, then other hosts have been selected
        # and then another bulk edit has made, the attributes need to be reset before
        # rendering the form. Otherwise the second edit will have the attributes of the
        # first set.
        host_hash = request.var("host_hash")
        if not host_hash or host_hash != current_host_hash:
            request.del_vars(prefix="attr_")
            request.del_vars(prefix="bulk_change_")

        html.p(
            "%s%s %s"
            % (
                _(
                    "You have selected <b>%d</b> hosts for bulk edit. You can now change "
                    "host attributes for all selected hosts at once. "
                )
                % len(hosts),
                _(
                    "If a selection is set to <i>This value differs between the selected hosts.</i> "
                    "then currenty not all selected hosts share the same setting for this attribute. "
                    "If you keep that selection, all hosts will keep their individual settings."
                ),
                _(
                    "In case you want to <i>unset</i> attributes on multiple hosts, you need to "
                    "use the <i>Remove explicit attribute settings</i> option instead of bulk edit."
                ),
            )
        )

        with html.form_context("edit_host", method="POST"):
            html.prevent_password_auto_completion()
            html.hidden_field("host_hash", current_host_hash)
            configure_attributes(
                False, {str(k): v for k, v in hosts.items()}, "bulk", parent=self._folder
            )
            forms.end()
            html.hidden_fields()


class ModeBulkCleanup(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "bulkcleanup"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "edit_hosts"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    @override
    def _from_vars(self) -> None:
        self._folder = disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        )

    @override
    def title(self) -> str:
        return _("Bulk removal of explicit attributes")

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        hosts = get_hosts_from_checkboxes(self._folder)

        return make_simple_form_page_menu(
            _("Attributes"),
            breadcrumb,
            form_name="bulkcleanup",
            button_name="_save",
            save_is_enabled=bool(self._get_attributes_for_bulk_cleanup(hosts)),
        )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        user.need_permission("wato.edit_hosts")
        to_clean = self._bulk_collect_cleaned_attributes()
        if "contactgroups" in to_clean:
            self._folder.permissions.need_permission("write")

        hosts = get_hosts_from_checkboxes(self._folder)

        # Check all permissions before doing any edit
        for host in hosts:
            host.permissions.need_permission("write")

        for host in hosts:
            host.clean_attributes(to_clean, pprint_value=active_config.wato_pprint_config)

        return redirect(self._folder.url())

    def _bulk_collect_cleaned_attributes(self) -> list[str]:
        to_clean = []
        for attrname in all_host_attributes(active_config).keys():
            if html.get_checkbox("_clean_" + attrname) is True:
                to_clean.append(attrname)
        return to_clean

    @override
    def page(self) -> None:
        hosts = get_hosts_from_checkboxes(self._folder)

        html.p(
            _(
                "You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
                "explicit attribute values from hosts. The hosts will then inherit attributes "
                "configured at the host list or folders or simply fall back to the built-in "
                "default values."
            )
            % len(hosts)
        )

        with html.form_context("bulkcleanup", method="POST"):
            forms.header(_("Attributes to remove from hosts"))
            self._select_attributes_for_bulk_cleanup(hosts)
            html.hidden_fields()

    def _select_attributes_for_bulk_cleanup(self, hosts: Sequence[Host]) -> None:
        attributes = self._get_attributes_for_bulk_cleanup(hosts)

        for attr, is_inherited, num_haveit in attributes:
            # Legend and Help
            forms.section(attr.title())

            if attr.is_mandatory() and not is_inherited:
                html.write_text_permissive(
                    _(
                        "This attribute is mandatory and there is no value "
                        "defined in the host list or any parent folder."
                    )
                )
            else:
                label = "clean this attribute on <b>%s</b> hosts" % (
                    num_haveit == len(hosts) and "all selected" or str(num_haveit)
                )
                html.checkbox("_clean_%s" % attr.name(), False, label=label)
            html.help(attr.help())

        forms.end()

        if not attributes:
            html.write_text_permissive(_("The selected hosts have no explicit attributes"))

    def _get_attributes_for_bulk_cleanup(
        self, hosts: Sequence[Host]
    ) -> list[tuple[ABCHostAttribute, bool, int]]:
        attributes = []
        for attr in sorted_host_attributes():
            attrname = attr.name()

            if not attr.show_in_host_cleanup():
                continue

            # only show attributes that at least on host have set
            num_haveit = 0
            for host in hosts:
                if attrname in host.attributes:
                    num_haveit += 1

            if not num_haveit:
                continue

            # If the attribute is mandatory and no value is inherited
            # by file or folder, the attribute cannot be cleaned.
            container: Folder | SearchFolder | None = self._folder
            is_inherited = False
            while container:
                if attrname in container.attributes:
                    is_inherited = True
                    break
                container = container.parent()

            attributes.append((attr, is_inherited, num_haveit))
        return attributes
