#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""When the user wants to scan the services of multiple hosts at once
this mode is used."""

import copy
from typing import List, Tuple, cast, Type, Optional

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.forms as forms
from cmk.gui.log import logger
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import PageMenu, make_simple_form_page_menu
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.bulk_discovery import (
    BulkDiscoveryBackgroundJob,
    vs_bulk_discovery,
    DiscoveryHost,
    get_tasks,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    get_hostnames_from_checkboxes,
)


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
        self._start = bool(html.request.var("_start"))
        self._all = bool(html.request.var("all"))
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
        (self._recurse, self._only_failed, self._only_failed_invcheck,
         self._only_ok_agent) = cast(Tuple[bool, bool, bool, bool],
                                     self._bulk_discovery_params["selection"])

        # The cast is needed for the moment, because mypy does not understand our data structure here
        (self._do_scan, self._bulk_size) = cast(Tuple[bool, int],
                                                self._bulk_discovery_params["performance"])

        self._mode = self._bulk_discovery_params["mode"]
        self._error_handling = self._bulk_discovery_params["error_handling"]

    def title(self):
        return _("Bulk discovery")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            breadcrumb,
            form_name="bulkinventory",
            button_name="_start",
            save_title=_("Start"),
        )

    def action(self) -> ActionResult:
        config.user.need_permission("wato.services")

        tasks = get_tasks(self._get_hosts_to_discover(), self._bulk_size)

        try:
            html.check_transaction()
            self._job.set_function(self._job.do_execute, self._mode, self._do_scan,
                                   self._error_handling, tasks)
            self._job.start()
        except Exception as e:
            if config.debug:
                raise
            logger.exception("Failed to start bulk discovery")
            raise MKUserError(
                None,
                _("Failed to start discovery: %s") % ("%s" % e).replace("\n", "\n<br>"))

        raise HTTPRedirect(self._job.detail_url())

    def page(self):
        config.user.need_permission("wato.services")

        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            html.show_message(
                _("Bulk discovery currently running in <a href=\"%s\">background</a>.") %
                self._job.detail_url())
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
                _("You have selected <b>%d</b> hosts for bulk discovery.") %
                len(self._get_hosts_to_discover()))
            # The cast is needed for the moment, because mypy does not understand our data structure here
            selection = cast(Tuple[bool, bool, bool, bool],
                             self._bulk_discovery_params["selection"])
            self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

        msgs.append(
            _("The Checkmk discovery will automatically find and configure services "
              "to be checked on your hosts and may also discover host labels."))
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
                host = Folder.current().host(host_name)
                host.need_permission("write")
                hosts_to_discover.append(
                    DiscoveryHost(host.site_id(),
                                  host.folder().path(), host_name))

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
                    DiscoveryHost(host.site_id(),
                                  host.folder().path(), host_name))

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
        return sites.live().query_column("GET services\n"
                                         "Filter: description = Check_MK inventory\n"
                                         "Filter: description = Check_MK Discovery\n"
                                         "Or: 2\n"
                                         "Filter: state > 0\n"
                                         "Columns: host_name")

    def _find_hosts_with_failed_agent(self):
        return sites.live().query_column("GET services\n"
                                         "Filter: description = Check_MK\n"
                                         "Filter: state >= 2\n"
                                         "Columns: host_name")
