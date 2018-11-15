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
"""Mode for automatic scan of parents (similar to cmk --scan-parents)"""

import json
import traceback

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.utils as utils

from cmk.gui.plugins.wato.utils import mode_registry
from cmk.gui.plugins.wato.utils.base_modes import WatoMode

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.wato.pages.progress import interactive_progress


@mode_registry.register
class ModeParentScan(WatoMode):
    @classmethod
    def name(cls):
        return "parentscan"

    @classmethod
    def permissions(cls):
        return ["hosts", "parentscan"]

    def title(self):
        return _("Parent scan")

    def buttons(self):
        html.context_button(_("Folder"), watolib.Folder.current().url(), "back")

    def _from_vars(self):
        # Ignored during initial form display
        # TODO: Make dedicated class or class members
        self._settings = {
            "where": html.var("where"),
            "alias": html.get_unicode_input("alias", "").strip() or None,
            "recurse": html.get_checkbox("recurse"),
            "select": html.var("select"),
            "timeout": utils.saveint(html.var("timeout")) or 8,
            "probes": utils.saveint(html.var("probes")) or 2,
            "max_ttl": utils.saveint(html.var("max_ttl")) or 10,
            "force_explicit": html.get_checkbox("force_explicit"),
            "ping_probes": utils.saveint(html.var("ping_probes")) or 0,
        }

        if not html.var("all"):
            # 'all' not set -> only scan checked hosts in current folder, no recursion
            self._complete_folder = False
            self._items = []
            for host in watolib.get_hosts_from_checkboxes():
                if self._include_host(host, self._settings["select"]):
                    self._items.append("%s|%s" % (host.folder().path(), host.name()))

        else:
            # all host in this folder, maybe recursively
            self._complete_folder = True
            self._items = []
            for host in self._recurse_hosts(watolib.Folder.current(), self._settings["recurse"],
                                            self._settings["select"]):
                self._items.append("%s|%s" % (host.folder().path(), host.name()))

    def action(self):
        if not html.var("_item"):
            return

        try:
            folderpath, host_name = html.var("_item").split("|")
            folder = watolib.Folder.folder(folderpath)
            host = folder.host(host_name)
            site_id = host.site_id()
            params = map(str, [
                self._settings["timeout"], self._settings["probes"], self._settings["max_ttl"],
                self._settings["ping_probes"]
            ])
            gateways = watolib.check_mk_automation(site_id, "scan-parents", params + [host_name])
            gateway, state, skipped_gateways, error = gateways[0]

            if state in ["direct", "root", "gateway"]:
                message, pconf, gwcreat = \
                    self._configure_gateway(state, site_id, host, gateway)
            else:
                message = error
                pconf = False
                gwcreat = False

            # Possible values for state are:
            # failed, dnserror, garbled, root, direct, notfound, gateway
            counts = [
                'continue',
                1,  # Total hosts
                1 if gateway else 0,  # Gateways found
                1 if state in ["direct", "root"] else 0,  # Directly reachable hosts
                skipped_gateways,  # number of failed PING probes
                1 if state == "notfound" else 0,  # No gateway found
                1 if pconf else 0,  # New parents configured
                1 if gwcreat else 0,  # Gateway hosts created
                1 if state in ["failed", "dnserror", "garbled"] else 0,  # Errors
            ]
            result = "%s\n%s: %s<br>\n" % (json.dumps(counts), host_name, message)

        except Exception as e:
            result = json.dumps(['failed', 1, 0, 0, 0, 0, 0, 1]) + "\n"
            if site_id:
                msg = _("Error during parent scan of %s on site %s: %s") % (host_name, site_id, e)
            else:
                msg = _("Error during parent scan of %s: %s") % (host_name, e)
            if config.debug:
                msg += html.render_br()
                msg += html.render_pre(traceback.format_exc().replace("\n", "<br>"))
                msg += html.render_br()
            result += msg
        html.write(result)
        return ""

    def _configure_gateway(self, state, site_id, host, gateway):
        # Settings for configuration and gateway creation
        force_explicit = html.get_checkbox("force_explicit")
        where = html.var("where")
        alias = html.var("alias")

        # If we have found a gateway, we need to know a matching
        # host name from our configuration. If there is none,
        # we can create one, if the users wants this. The automation
        # for the parent scan already tries to find such a host
        # within the site.
        gwcreat = False

        if gateway:
            gw_host_name, gw_ip, dns_name = gateway
            if not gw_host_name:
                if where == "nowhere":
                    return _("No host %s configured, parents not set") % gw_ip, \
                        False, False

                # Determine folder where to create the host.
                elif where == "here":  # directly in current folder
                    gw_folder = watolib.Folder.current_disk_folder()

                elif where == "subfolder":
                    current = watolib.Folder.current_disk_folder()
                    # Put new gateways in subfolder "Parents" of current
                    # folder. Does this folder already exist?
                    if current.has_subfolder("parents"):
                        gw_folder = current.subfolder("parents")
                    else:
                        # Create new gateway folder
                        gw_folder = current.create_subfolder("parents", _("Parents"), {})

                elif where == "there":  # In same folder as host
                    gw_folder = host.folder()

                # Create gateway host
                if dns_name:
                    gw_host_name = dns_name
                elif site_id:
                    gw_host_name = "gw-%s-%s" % (site_id, gw_ip.replace(".", "-"))
                else:
                    gw_host_name = "gw-%s" % (gw_ip.replace(".", "-"))

                new_host_attributes = {"ipaddress": gw_ip}
                if alias:
                    new_host_attributes["alias"] = alias
                if gw_folder.site_id() != site_id:
                    new_host_attributes["site"] = site_id

                gw_folder.create_hosts([(gw_host_name, new_host_attributes, None)])
                gwcreat = True

            parents = [gw_host_name]

        else:
            parents = []

        if host.effective_attribute("parents") == parents:
            return _("Parents unchanged at %s") %  \
                    (",".join(parents) if parents else _("none")), False, gwcreat

        if force_explicit or host.folder().effective_attribute("parents") != parents:
            host.update_attributes({"parents": parents})
        else:
            # Check which parents the host would have inherited
            if host.has_explicit_attribute("parents"):
                host.clean_attributes(["parents"])

        if parents:
            message = _("Set parents to %s") % ",".join(parents)
        else:
            message = _("Removed parents")

        return message, True, gwcreat

    def page(self):
        if html.var("_start"):
            self._show_progress_dialog()
        else:
            self._show_parameter_form()

    def _show_progress_dialog(self):
        # Persist settings
        config.user.save_file("parentscan", self._settings)

        # Start interactive progress
        interactive_progress(
            self._items,
            _("Parent scan"),  # title
            [
                (_("Total hosts"), 0),
                (_("Gateways found"), 0),
                (_("Directly reachable hosts"), 0),
                (_("Unreachable gateways"), 0),
                (_("No gateway found"), 0),
                (_("New parents configured"), 0),
                (_("Gateway hosts created"), 0),
                (_("Errors"), 0),
            ],
            [("mode", "folder")],  # URL for "Stop/Finish" button
            50,  # ms to sleep between two steps
            fail_stats=[1],
        )

    def _show_parameter_form(self):
        html.begin_form("parentscan", method="POST")
        html.hidden_fields()

        # Mode of action
        html.open_p()
        if not self._complete_folder:
            html.write_text(
                _("You have selected <b>%d</b> hosts for parent scan. ") % len(self._items))
        html.p(
            _("The parent scan will try to detect the last gateway "
              "on layer 3 (IP) before a host. This will be done by "
              "calling <tt>traceroute</tt>. If a gateway is found by "
              "that way and its IP address belongs to one of your "
              "monitored hosts, that host will be used as the hosts "
              "parent. If no such host exists, an artifical ping-only "
              "gateway host will be created if you have not disabled "
              "this feature."))

        forms.header(_("Settings for Parent Scan"))

        self._settings = config.user.load_file(
            "parentscan", {
                "where": "subfolder",
                "alias": _("Created by parent scan"),
                "recurse": True,
                "select": "noexplicit",
                "timeout": 8,
                "probes": 2,
                "ping_probes": 5,
                "max_ttl": 10,
                "force_explicit": False,
            })

        # Selection
        forms.section(_("Selection"))
        if self._complete_folder:
            html.checkbox("recurse", self._settings["recurse"], label=_("Include all subfolders"))
            html.br()
        html.radiobutton("select", "noexplicit", self._settings["select"] == "noexplicit",
                         _("Skip hosts with explicit parent definitions (even if empty)") + "<br>")
        html.radiobutton("select", "no", self._settings["select"] == "no",
                         _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>")
        html.radiobutton("select", "ignore", self._settings["select"] == "ignore",
                         _("Scan all hosts") + "<br>")

        # Performance
        forms.section(_("Performance"))
        html.open_table()
        html.open_tr()
        html.open_td()
        html.write_text(_("Timeout for responses") + ":")
        html.close_td()
        html.open_td()
        html.number_input("timeout", self._settings["timeout"], size=2)
        html.write_text(_("sec"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of probes per hop") + ":")
        html.close_td()
        html.open_td()
        html.number_input("probes", self._settings["probes"], size=2)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Maximum distance (TTL) to gateway") + ":")
        html.close_td()
        html.open_td()
        html.number_input("max_ttl", self._settings["max_ttl"], size=2)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of PING probes") + ":")
        html.help(
            _("After a gateway has been found, Check_MK checks if it is reachable "
              "via PING. If not, it is skipped and the next gateway nearer to the "
              "monitoring core is being tried. You can disable this check by setting "
              "the number of PING probes to 0."))
        html.close_td()
        html.open_td()
        html.number_input("ping_probes", self._settings.get("ping_probes", 5), size=2)
        html.close_td()
        html.close_tr()
        html.close_table()

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox(
            "force_explicit",
            self._settings["force_explicit"],
            label=_(
                "Force explicit setting for parents even if setting matches that of the folder"))

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write_text(_("Create gateway hosts in"))
        html.open_ul()

        html.radiobutton(
            "where", "subfolder", self._settings["where"] == "subfolder",
            _("in the subfolder <b>%s/Parents</b>") % watolib.Folder.current_disk_folder().title())

        html.br()
        html.radiobutton(
            "where", "here", self._settings["where"] == "here",
            _("directly in the folder <b>%s</b>") % watolib.Folder.current_disk_folder().title())
        html.br()
        html.radiobutton("where", "there", self._settings["where"] == "there",
                         _("in the same folder as the host"))
        html.br()
        html.radiobutton("where", "nowhere", self._settings["where"] == "nowhere",
                         _("do not create gateway hosts"))
        html.close_ul()
        html.write_text(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", self._settings["alias"])

        # Start button
        forms.end()
        html.button("_start", _("Start"))

    # select: 'noexplicit' -> no explicit parents
    #         'no'         -> no implicit parents
    #         'ignore'     -> not important
    def _include_host(self, host, select):
        if select == 'noexplicit' and host.has_explicit_attribute("parents"):
            return False
        elif select == 'no':
            if host.effective_attribute("parents"):
                return False
        return True

    def _recurse_hosts(self, folder, recurse, select):
        entries = []
        for host in folder.hosts().values():
            if self._include_host(host, select):
                entries.append(host)

        if recurse:
            for subfolder in folder.all_subfolders().values():
                entries += self._recurse_hosts(subfolder, recurse, select)
        return entries
