#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When the user wants to scan the services of multiple hosts at once
this mode is used."""

import copy
from collections.abc import Collection
from typing import cast, override

from cmk.ccc.hostaddress import HostName

from cmk.checkengine.discovery import DiscoverySettings

from cmk.gui import forms, sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    BulkSize,
    DiscoveryHost,
    DoFullScan,
    IgnoreErrors,
    start_bulk_discovery,
    vs_bulk_discovery,
)
from cmk.gui.watolib.hosts_and_folders import (
    disk_or_search_folder_from_request,
    Folder,
    SearchFolder,
)
from cmk.gui.watolib.mode import ModeRegistry, WatoMode

from ._bulk_actions import get_hostnames_from_checkboxes


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeBulkDiscovery)


class ModeBulkDiscovery(WatoMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "bulkinventory"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "services"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    @override
    def _from_vars(self) -> None:
        self._start = bool(request.var("_save"))
        self._all = bool(request.var("all"))
        self._just_started = False
        self._get_bulk_discovery_params()
        self._job = BulkDiscoveryBackgroundJob()
        self._folder = disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        )

    def _get_bulk_discovery_params(self) -> None:
        self._bulk_discovery_params = copy.deepcopy(active_config.bulk_discovery_default_settings)

        if self._start:
            # Only do this when the start form has been submitted
            bulk_discover_params = vs_bulk_discovery().from_html_vars("bulkinventory")
            vs_bulk_discovery().validate_value(bulk_discover_params, "bulkinventory")
            self._bulk_discovery_params.update(bulk_discover_params)

        # The cast is needed for the moment, because mypy does not understand our data structure here
        (self._recurse, self._only_failed, self._only_failed_invcheck, self._only_ok_agent) = cast(
            tuple[bool, bool, bool, bool], self._bulk_discovery_params["selection"]
        )

        self._do_full_scan, self._bulk_size = self._get_performance_params()
        self._mode = DiscoverySettings.from_vs(self._bulk_discovery_params.get("mode"))
        self._ignore_errors = IgnoreErrors(self._bulk_discovery_params["error_handling"])

    def _get_performance_params(self) -> tuple[DoFullScan, BulkSize]:
        performance_params = self._bulk_discovery_params["performance"]
        assert isinstance(performance_params, tuple)

        if len(performance_params) == 3:
            # In previous Checkmk versions (< 2.0) there was a third performance parameter:
            # 'use_cache' in the first place.
            do_scan, bulk_size = performance_params[1:]
        else:
            do_scan, bulk_size = performance_params

        assert isinstance(do_scan, bool)
        assert isinstance(bulk_size, int)
        return DoFullScan(do_scan), BulkSize(bulk_size)

    @override
    def title(self) -> str:
        return _("Bulk discovery")

    @override
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Discovery"),
            breadcrumb,
            form_name="bulkinventory",
            button_name="_save",
            save_title=_("Start"),
        )

    @override
    def action(self) -> ActionResult:
        check_csrf_token()

        user.need_permission("wato.services")

        try:
            transactions.check_transaction()
            if (
                result := start_bulk_discovery(
                    self._job,
                    self._get_hosts_to_discover(),
                    self._mode,
                    self._do_full_scan,
                    self._ignore_errors,
                    self._bulk_size,
                    pprint_value=active_config.wato_pprint_config,
                    debug=active_config.debug,
                )
            ).is_error():
                raise result.error

        except Exception as e:
            if active_config.debug:
                raise
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(
                None, _("Failed to start discovery: %s") % ("%s" % e).replace("\n", "\n<br>")
            )

        raise HTTPRedirect(self._job.detail_url())

    @override
    def page(self) -> None:
        user.need_permission("wato.services")

        if self._job.is_active():
            html.show_message(
                _('Bulk discovery currently running in <a href="%s">background</a>.')
                % self._job.detail_url()
            )
            return

        self._show_start_form()

    def _show_start_form(self) -> None:
        with html.form_context("bulkinventory", method="POST"):
            msgs = []
            if self._all:
                vs = vs_bulk_discovery(render_form=True)
            else:
                # "Include subfolders" does not make sense for a selection of hosts
                # which is already given in the following situations:
                # - in the current folder below 'Selected hosts: Discovery'
                # - Below 'Bulk import' a automatic service discovery for
                #   imported/selected hosts can be executed
                vs = vs_bulk_discovery(render_form=True, include_subfolders=False)
                msgs.append(
                    _("You have selected <b>%d</b> hosts for bulk discovery.")
                    % len(self._get_hosts_to_discover())
                )
                # The cast is needed for the moment, because mypy does not understand our data structure here
                selection = cast(
                    tuple[bool, bool, bool, bool], self._bulk_discovery_params["selection"]
                )
                self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

            msgs.append(
                _(
                    "The Checkmk discovery will automatically find and configure services "
                    "to be checked on your hosts and may also discover host labels."
                )
            )
            html.open_p()
            html.write_text_permissive(" ".join(msgs))
            vs.render_input("bulkinventory", self._bulk_discovery_params)
            forms.end()

            html.hidden_fields()

    def _get_hosts_to_discover(self) -> list[DiscoveryHost]:
        if self._only_failed_invcheck:
            restrict_to_hosts = self._find_hosts_with_failed_discovery_check()
        else:
            restrict_to_hosts = None

        if self._only_ok_agent:
            skip_hosts = self._find_hosts_with_failed_agent()
        else:
            skip_hosts = []

        # 'all' not set -> only inventorize checked hosts
        hosts_to_discover = []

        if not self._all:
            for host_name in get_hostnames_from_checkboxes(
                self._folder, (lambda host: host.discovery_failed()) if self._only_failed else None
            ):
                if restrict_to_hosts and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = self._folder.load_host(host_name)
                host.permissions.need_permission("write")
                hosts_to_discover.append(
                    DiscoveryHost(host.site_id(), host.folder().path(), host_name)
                )

        else:
            # all host in this folder, maybe recursively. New: we always group
            # a bunch of subsequent hosts of the same folder into one item.
            # That saves automation calls and speeds up mass inventories.
            entries = self._recurse_hosts(self._folder)
            for host_name, folder in entries:
                if restrict_to_hosts is not None and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = folder.load_host(host_name)
                host.permissions.need_permission("write")
                hosts_to_discover.append(
                    DiscoveryHost(host.site_id(), host.folder().path(), host_name)
                )

        return hosts_to_discover

    def _recurse_hosts(
        self, folder: Folder | SearchFolder
    ) -> list[tuple[HostName, Folder | SearchFolder]]:
        entries = []
        for host_name, host in folder.hosts().items():
            if not self._only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if self._recurse:
            assert isinstance(folder, Folder)
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts(subfolder)
        return entries

    def _find_hosts_with_failed_discovery_check(self) -> list[HostName]:
        # Old service name "Check_MK inventory" needs to be kept because old
        # installations may still use that name
        return sites.live().query_column(
            "GET services\n"
            "Filter: description = Check_MK inventory\n"
            "Filter: description = Check_MK Discovery\n"
            "Or: 2\n"
            "Filter: state > 0\n"
            "Columns: host_name"
        )

    def _find_hosts_with_failed_agent(self) -> list[HostName]:
        return sites.live().query_column(
            "GET services\nFilter: description = Check_MK\nFilter: state >= 2\nColumns: host_name"
        )
