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

"""When the user wants to scan the services of multiple hosts at once
this mode is used."""

import copy
import json
import traceback

import cmk.paths

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)

@mode_registry.register
class ModeBulkDiscovery(WatoMode):
    @classmethod
    def name(cls):
        return "bulkinventory"


    @classmethod
    def permissions(cls):
        return ["hosts", "services"]


    def _from_vars(self):
        self._start = bool(html.var("_start"))
        self._all =  bool(html.var("all"))
        self._item = html.var("_item") if html.var("_item") else None

        self._get_bulk_discovery_params()


    def _get_bulk_discovery_params(self):
        self._bulk_discovery_params = copy.deepcopy(config.bulk_discovery_default_settings)

        # start       : Rendering of the progress dialog
        # transaction : Single step processing
        if self._start or (html.is_transaction() and not html.has_var("_bulk_inventory")):
            bulk_discover_params = cmk.gui.plugins.wato.vs_bulk_discovery().from_html_vars("bulkinventory")
            cmk.gui.plugins.wato.vs_bulk_discovery().validate_value(bulk_discover_params, "bulkinventory")
            self._bulk_discovery_params.update(bulk_discover_params)

        self._recurse, self._only_failed, self._only_failed_invcheck, \
            self._only_ok_agent = self._bulk_discovery_params["selection"]
        self._use_cache, self._do_scan, self._bulk_size = \
            self._bulk_discovery_params["performance"]
        self._mode           = self._bulk_discovery_params["mode"]
        self._error_handling = self._bulk_discovery_params["error_handling"]


    def title(self):
        return _("Bulk Service Discovery")


    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")


    def action(self):
        config.user.need_permission("wato.services")
        if not self._item:
            return

        try:
            site_id, folderpath, hostnamesstring = self._item.split("|")
            hostnames         = hostnamesstring.split(";")
            num_hosts         = len(hostnames)
            num_skipped_hosts = 0
            num_failed_hosts  = 0
            folder            = watolib.Folder.folder(folderpath)

            if site_id not in config.sitenames():
                raise MKUserError(None, _("The requested site does not exist"))

            for host_name in hostnames:
                host = folder.host(host_name)
                if host is None:
                    raise MKUserError(None, _("The requested host does not exist"))
                host.need_permission("write")

            arguments         = [self._mode,] + hostnames

            if self._use_cache:
                arguments = [ "@cache" ] + arguments
            if self._do_scan:
                arguments = [ "@scan" ] + arguments
            if not self._error_handling:
                arguments = [ "@raiseerrors" ] + arguments

            timeout = html.request.request_timeout - 2

            watolib.unlock_exclusive() # Avoid freezing WATO when hosts do not respond timely
            counts, failed_hosts = watolib.check_mk_automation(site_id, "inventory",
                                                       arguments, timeout=timeout)
            watolib.lock_exclusive()
            watolib.Folder.invalidate_caches()
            folder = watolib.Folder.folder(folderpath)

            # sum up host individual counts to have a total count
            sum_counts = [ 0, 0, 0, 0 ] # added, removed, kept, new
            result_txt = ''
            for hostname in hostnames:
                sum_counts[0] += counts[hostname][0]
                sum_counts[1] += counts[hostname][1]
                sum_counts[2] += counts[hostname][2]
                sum_counts[3] += counts[hostname][3]
                host           = folder.host(hostname)

                if hostname in failed_hosts:
                    reason = failed_hosts[hostname]
                    if reason == None:
                        num_skipped_hosts += 1
                        result_txt += _("%s: discovery skipped: host not monitored<br>") % hostname
                    else:
                        num_failed_hosts += 1
                        result_txt += _("%s: discovery failed: %s<br>") % (hostname, failed_hosts[hostname])
                        if not host.locked():
                            host.set_discovery_failed()
                else:
                    result_txt += _("%s: discovery successful<br>\n") % hostname

                    watolib.add_service_change(host, "bulk-inventory",
                        _("Did service discovery on host %s: %d added, %d removed, %d kept, "
                          "%d total services") % tuple([hostname] + counts[hostname]))

                    if not host.locked():
                        host.clear_discovery_failed()

            result = json.dumps([ 'continue', num_hosts, num_failed_hosts, num_skipped_hosts ] + sum_counts) + "\n" + result_txt

        except Exception, e:
            result = json.dumps([ 'failed', num_hosts, num_hosts, 0, 0, 0, 0, ]) + "\n"
            if site_id:
                msg = _("Error during inventory of %s on site %s") % (", ".join(hostnames), site_id)
            else:
                msg = _("Error during inventory of %s") % (", ".join(hostnames))
            msg += html.render_div(e, class_="exc")
            if config.debug:
                msg += html.render_br() + html.render_pre(traceback.format_exc().replace("\n", "<br>")) + html.render_br()
            result += msg
        html.write(result)
        return ""


    def page(self):
        config.user.need_permission("wato.services")

        items, hosts_to_discover = self._fetch_items_for_interactive_progress()
        if html.var("_start"):
            # Start interactive progress
            # TODO: this will be fixed by next commit
            interactive_progress( # pylint: disable=undefined-variable
                items,
                _("Bulk Service Discovery"),  # title
                [ (_("Total hosts"),      0),
                  (_("Failed hosts"),     0),
                  (_("Skipped hosts"),    0),
                  (_("Services added"),   0),
                  (_("Services removed"), 0),
                  (_("Services kept"),    0),
                  (_("Total services"),   0) ], # stats table
                [ ("mode", "folder") ], # URL for "Stop/Finish" button
                50, # ms to sleep between two steps
                fail_stats = [ 1 ],
            )

        else:
            html.begin_form("bulkinventory", method="POST")
            html.hidden_fields()

            msgs = []
            if self._all:
                vs = cmk.gui.plugins.wato.vs_bulk_discovery(render_form=True)
            else:
                # "Include subfolders" does not make sense for a selection of hosts
                # which is already given in the following situations:
                # - in the current folder below 'Selected hosts: Discovery'
                # - Below 'Bulk import' a automatic service discovery for
                #   imported/selected hosts can be executed
                vs = cmk.gui.plugins.wato.vs_bulk_discovery(render_form=True, include_subfolders=False)
                msgs.append(_("You have selected <b>%d</b> hosts for bulk discovery.") % len(hosts_to_discover))
                selection = self._bulk_discovery_params["selection"]
                self._bulk_discovery_params["selection"] = [False] + list(selection[1:])

            msgs.append(_("Check_MK service discovery will automatically find and "
                          "configure services to be checked on your hosts."))
            html.open_p()
            html.write_text(" ".join(msgs))
            vs.render_input("bulkinventory", self._bulk_discovery_params)
            forms.end()

            html.button("_start", _("Start"))
            html.end_form()


    def _fetch_items_for_interactive_progress(self):
        if self._only_failed_invcheck:
            restrict_to_hosts = self._find_hosts_with_failed_inventory_check()
        else:
            restrict_to_hosts = None

        if self._only_ok_agent:
            skip_hosts = self._find_hosts_with_failed_agent()
        else:
            skip_hosts = []

        # 'all' not set -> only inventorize checked hosts
        hosts_to_discover = []

        if not self._all:
            if self._only_failed:
                filterfunc = lambda host: host.discovery_failed()
            else:
                filterfunc = None

            for host_name in watolib.get_hostnames_from_checkboxes(filterfunc):
                if restrict_to_hosts and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = watolib.Folder.current().host(host_name)
                host.need_permission("write")
                hosts_to_discover.append( (host.site_id(), host.folder(), host_name) )

        # all host in this folder, maybe recursively. New: we always group
        # a bunch of subsequent hosts of the same folder into one item.
        # That saves automation calls and speeds up mass inventories.
        else:
            entries                    = self._recurse_hosts(watolib.Folder.current())
            items                      = []
            for host_name, folder in entries:
                if restrict_to_hosts != None and host_name not in restrict_to_hosts:
                    continue
                if host_name in skip_hosts:
                    continue
                host = folder.host(host_name)
                host.need_permission("write")
                hosts_to_discover.append( (host.site_id(), host.folder(), host_name) )

        # Create a list of items for the progress bar, where we group
        # subsequent hosts that are in the same folder and site
        hosts_to_discover.sort()

        current_site_and_folder = None
        items                   = []
        hosts_in_this_item      = 0

        for site_id, folder, host_name in hosts_to_discover:
            if not items or (site_id, folder) != current_site_and_folder or \
               hosts_in_this_item >= self._bulk_size:
                items.append("%s|%s|%s" % (site_id, folder.path(), host_name))
                hosts_in_this_item = 1
            else:
                items[-1]          += ";" + host_name
                hosts_in_this_item += 1
            current_site_and_folder = site_id, folder
        return items, hosts_to_discover


    def _recurse_hosts(self, folder):
        entries = []
        for host_name, host in folder.hosts().items():
            if not self._only_failed or host.discovery_failed():
                entries.append((host_name, folder))
        if self._recurse:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts(subfolder)
        return entries


    def _find_hosts_with_failed_inventory_check(self):
        return sites.live().query_column(
            "GET services\n"
            "Filter: description = Check_MK inventory\n" # FIXME: Remove this one day
            "Filter: description = Check_MK Discovery\n"
            "Or: 2\n"
            "Filter: state > 0\n"
            "Columns: host_name")

    def _find_hosts_with_failed_agent(self):
        return sites.live().query_column(
            "GET services\n"
            "Filter: description = Check_MK\n"
            "Filter: state >= 2\n"
            "Columns: host_name")
