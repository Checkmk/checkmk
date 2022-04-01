#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When the user wants to scan the services of multiple hosts at once
this mode is used."""

import copy
from typing import cast, List, Optional, Tuple, Type

import cmk.gui.forms as forms
import cmk.gui.sites as sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.globals import config, html, request, transactions
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_simple_form_page_menu, PageMenu
from cmk.gui.plugins.wato.utils import get_hostnames_from_checkboxes, mode_registry, WatoMode
from cmk.gui.type_defs import ActionResult
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    BulkSize,
    DiscoveryHost,
    DiscoveryMode,
    DoFullScan,
    IgnoreErrors,
    start_bulk_discovery,
    vs_bulk_discovery,
)
from cmk.gui.watolib.hosts_and_folders import Folder


@mode_registry.register
class ModeBulkDiscovery(WatoMode):
    @classmethod
    def name(cls):
        return "bulkinventory"

    @classmethod
    def permissions(cls):
        return ["hosts", "services"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    def _from_vars(self):
        self._start = bool(request.var("_save"))
        self._all = bool(request.var("all"))
        self._just_started = False
        self._get_bulk_discovery_params()
        self._job = BulkDiscoveryBackgroundJob()

    def _get_bulk_discovery_params(self):
        self._bulk_discovery_params = copy.deepcopy(config.bulk_discovery_default_settings)

        if self._start:
            # Only do this when the start form has been submitted
            bulk_discover_params = vs_bulk_discovery().from_html_vars("bulkinventory")
            vs_bulk_discovery().validate_value(bulk_discover_params, "bulkinventory")
            self._bulk_discovery_params.update(bulk_discover_params)

        # The cast is needed for the moment, because mypy does not understand our data structure here
        (self._recurse, self._only_failed, self._only_failed_invcheck, self._only_ok_agent) = cast(
            Tuple[bool, bool, bool, bool], self._bulk_discovery_params["selection"]
        )

        self._do_full_scan, self._bulk_size = self._get_performance_params()
        self._mode = DiscoveryMode(self._bulk_discovery_params["mode"])
        self._ignore_errors = IgnoreErrors(self._bulk_discovery_params["error_handling"])

    def _get_performance_params(self) -> Tuple[DoFullScan, BulkSize]:
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

    def title(self):
        return _("Bulk discovery")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Discovery"),
            breadcrumb,
            form_name="bulkinventory",
            button_name="_save",
            save_title=_("Start"),
        )

    def action(self) -> ActionResult:
        user.need_permission("wato.services")

        try:
            transactions.check_transaction()
            start_bulk_discovery(
                self._job,
                self._get_hosts_to_discover(),
                self._mode,
                self._do_full_scan,
                self._ignore_errors,
                self._bulk_size,
            )

        except Exception as e:
            if config.debug:
                raise
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(
                None, _("Failed to start discovery: %s") % ("%s" % e).replace("\n", "\n<br>")
            )

        raise HTTPRedirect(self._job.detail_url())

    def page(self):
        user.need_permission("wato.services")

        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            html.show_message(
                _('Bulk discovery currently running in <a href="%s">background</a>.')
                % self._job.detail_url()
            )
            return

        self._show_start_form()

    def _show_start_form(self):
        html.begin_form("bulkinventory", method="POST")

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
                Tuple[bool, bool, bool, bool], self._bulk_discovery_params["selection"]
            )
            self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

        msgs.append(
            _(
                "The Checkmk discovery will automatically find and configure services "
                "to be checked on your hosts and may also discover host labels."
            )
        )
        html.open_p()
        html.write_text(" ".join(msgs))
        vs.render_input("bulkinventory", self._bulk_discovery_params)
        forms.end()

        html.hidden_fields()
        html.end_form()

    def _get_hosts_to_discover(self) -> List[DiscoveryHost]:
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
            filterfunc = None
            if self._only_failed:
                filterfunc = lambda host: host.discovery_failed()

            for host_name in get_hostnames_from_checkboxes(filterfunc):
                if restrict_to_hosts and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = Folder.current().load_host(host_name)
                host.need_permission("write")
                hosts_to_discover.append(
                    DiscoveryHost(host.site_id(), host.folder().path(), host_name)
                )

        else:
            # all host in this folder, maybe recursively. New: we always group
            # a bunch of subsequent hosts of the same folder into one item.
            # That saves automation calls and speeds up mass inventories.
            entries = self._recurse_hosts(Folder.current())
            for host_name, folder in entries:
                if restrict_to_hosts is not None and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = folder.host(host_name)
                host.need_permission("write")
                hosts_to_discover.append(
                    DiscoveryHost(host.site_id(), host.folder().path(), host_name)
                )

        return hosts_to_discover

    def _recurse_hosts(self, folder):
        entries = []
        for host_name, host in folder.hosts().items():
            if not self._only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if self._recurse:
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts(subfolder)
        return entries

    def _find_hosts_with_failed_discovery_check(self):
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

    def _find_hosts_with_failed_agent(self):
        return sites.live().query_column(
            "GET services\n"
            "Filter: description = Check_MK\n"
            "Filter: state >= 2\n"
            "Columns: host_name"
        )
