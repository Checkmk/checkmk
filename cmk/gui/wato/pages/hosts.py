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
"""Modes for creating and editing hosts"""

import abc
import six

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms

from cmk.gui.plugins.wato.utils import (
    mode_registry,
    configure_attributes,
    ConfigHostname,
)
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.context_buttons import host_status_button

from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError, MKAuthException, MKGeneralException, HTTPRedirect
from cmk.gui.valuespec import (
    ListOfStrings,
    Hostname,
    FixedValue,
)
from cmk.gui.wato.pages.folders import delete_host_after_confirm


class HostMode(six.with_metaclass(abc.ABCMeta, WatoMode)):
    @abc.abstractmethod
    def _init_host(self):
        raise NotImplementedError()

    def __init__(self):
        self._host = self._init_host()
        self._mode = "edit"
        super(HostMode, self).__init__()

    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]),
                            "back")

    def _is_cluster(self):
        return self._host.is_cluster()

    def _get_cluster_nodes(self):
        if not self._is_cluster():
            return None

        cluster_nodes = self._vs_cluster_nodes().from_html_vars("nodes")
        self._vs_cluster_nodes().validate_value(cluster_nodes, "nodes")
        if len(cluster_nodes) < 1:
            raise MKUserError("nodes_0", _("The cluster must have at least one node"))
        for nr, cluster_node in enumerate(cluster_nodes):
            if cluster_node == self._host.name():
                raise MKUserError("nodes_%d" % nr, _("The cluster can not be a node of it's own"))

            if not watolib.Host.host_exists(cluster_node):
                raise MKUserError(
                    "nodes_%d" % nr,
                    _("The node <b>%s</b> does not exist "
                      " (must be a host that is configured with WATO)") % cluster_node)
        return cluster_nodes

    # TODO: Extract cluster specific parts from this method
    def page(self):
        # Show outcome of host validation. Do not validate new hosts
        errors = None
        if self._mode != "edit":
            watolib.Folder.current().show_breadcrump()
        else:
            errors = watolib.validate_all_hosts([self._host.name()]).get(
                self._host.name(), []) + self._host.validation_errors()

        if errors:
            html.open_div(class_="info")
            html.open_table(class_="validationerror", boder=0, cellspacing=0, cellpadding=0)
            html.open_tr()

            html.open_td(class_="img")
            html.icon(title=None, icon="validation_error")
            html.close_td()

            html.open_td()
            html.open_p()
            html.h3(_("Warning: This host has an invalid configuration!"))
            html.open_ul()
            for error in errors:
                html.li(error)
            html.close_ul()
            html.close_p()

            if html.form_submitted():
                html.br()
                html.b(_("Your changes have been saved nevertheless."))
            html.close_td()

            html.close_tr()
            html.close_table()
            html.close_div()

        lock_message = ""
        if watolib.Folder.current().locked_hosts():
            if watolib.Folder.current().locked_hosts() is True:
                lock_message = _("Host attributes locked (You cannot edit this host)")
            else:
                lock_message = watolib.Folder.current().locked_hosts()
        if len(lock_message) > 0:
            html.div(lock_message, class_="info")

        html.begin_form("edit_host", method="POST")
        html.prevent_password_auto_completion()

        basic_attributes = [
            # attribute name, valuepec, default value
            ("host", self._vs_host_name(), self._host.name()),
        ]

        if self._is_cluster():
            basic_attributes += [
                # attribute name, valuepec, default value
                ("nodes", self._vs_cluster_nodes(),
                 self._host.cluster_nodes() if self._host else []),
            ]

        configure_attributes(
            new=self._mode != "edit",
            hosts={self._host.name(): self._host} if self._mode != "new" else {},
            for_what="host" if not self._is_cluster() else "cluster",
            parent=watolib.Folder.current(),
            basic_attributes=basic_attributes,
        )

        if self._mode != "edit":
            html.set_focus("host")

        forms.end()
        if not watolib.Folder.current().locked_hosts():
            html.button("services", _("Save & go to Services"), "submit")
            html.button("save", _("Save & Finish"), "submit")
            if not self._is_cluster():
                html.button("diag_host", _("Save & Test"), "submit")
        html.hidden_fields()
        html.end_form()

    def _vs_cluster_nodes(self):
        return ListOfStrings(
            title=_("Nodes"),
            valuespec=ConfigHostname(),
            orientation="horizontal",
            help=_(
                'Enter the host names of the cluster nodes. These hosts must be present in WATO.'),
        )

    @abc.abstractmethod
    def _vs_host_name(self):
        raise NotImplementedError()


# TODO: Split this into two classes ModeEditHost / ModeEditCluster. The problem with this is that
# we simply don't know whether or not a cluster or regular host is about to be edited. The GUI code
# simply wants to link to the "host edit page". We could try to use some factory to decide this when
# the edit_host mode is called.
@mode_registry.register
class ModeEditHost(HostMode):
    @classmethod
    def name(cls):
        return "edit_host"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def _init_host(self):
        hostname = html.get_ascii_input("host")  # may be empty in new/clone mode

        if not watolib.Folder.current().has_host(hostname):
            raise MKUserError("host", _("You called this page with an invalid host name."))

        return watolib.Folder.current().host(hostname)

    def title(self):
        return _("Properties of host") + " " + self._host.name()

    def buttons(self):
        super(ModeEditHost, self).buttons()

        host_status_button(self._host.name(), "hoststatus")

        html.context_button(
            _("Services"),
            watolib.folder_preserving_link([("mode", "inventory"), ("host", self._host.name())]),
            "services")
        if watolib.has_agent_bakery() and config.user.may('wato.download_agents'):
            html.context_button(
                _("Monitoring Agent"),
                watolib.folder_preserving_link([("mode", "agent_of_host"),
                                                ("host", self._host.name())]), "agents")

        if config.user.may('wato.rulesets'):
            html.context_button(
                _("Parameters"),
                watolib.folder_preserving_link([("mode", "object_parameters"),
                                                ("host", self._host.name())]), "rulesets")
            if self._is_cluster():
                html.context_button(
                    _("Clustered Services"),
                    watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                    ("varname", "clustered_services")]), "rulesets")

        if not watolib.Folder.current().locked_hosts():
            if config.user.may("wato.rename_hosts"):
                html.context_button(
                    self._is_cluster() and _("Rename cluster") or _("Rename host"),
                    watolib.folder_preserving_link([("mode", "rename_host"),
                                                    ("host", self._host.name())]), "rename_host")
            html.context_button(self._is_cluster() and _("Delete cluster") or _("Delete host"),
                                html.makeactionuri([("delete", "1")]), "delete")

        if not self._is_cluster():
            html.context_button(
                _("Diagnostic"),
                watolib.folder_preserving_link([("mode", "diag_host"),
                                                ("host", self._host.name())]), "diagnose")
        html.context_button(_("Update DNS Cache"), html.makeactionuri([("_update_dns_cache", "1")]),
                            "update")

    def action(self):
        if html.request.var("_update_dns_cache"):
            if html.check_transaction():
                config.user.need_permission("wato.update_dns_cache")
                num_updated, failed_hosts = watolib.check_mk_automation(
                    self._host.site_id(), "update-dns-cache", [])
                infotext = _("Successfully updated IP addresses of %d hosts.") % num_updated
                if failed_hosts:
                    infotext += "<br><br><b>Hostnames failed to lookup:</b> " \
                              + ", ".join(["<tt>%s</tt>" % h for h in failed_hosts])
                return None, infotext
            else:
                return None

        if html.request.var("delete"):  # Delete this host
            if not html.transaction_valid():
                return "folder"
            return delete_host_after_confirm(self._host.name())

        if html.check_transaction():
            attributes = watolib.collect_attributes("host" if not self._is_cluster() else "cluster",
                                                    new=False)
            watolib.Host.host(self._host.name()).edit(attributes, self._get_cluster_nodes())
            self._host = watolib.Folder.current().host(self._host.name())

        if html.request.var("services"):
            return "inventory"
        elif html.request.var("diag_host"):
            html.request.set_var("_try", "1")
            return "diag_host"
        return "folder"

    def _vs_host_name(self):
        return FixedValue(
            self._host.name(),
            title=_("Hostname"),
        )


class CreateHostMode(HostMode):
    @classmethod
    @abc.abstractmethod
    def _init_new_host_object(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def _host_type_name(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def _verify_host_type(cls, host):
        raise NotImplementedError()

    def _from_vars(self):
        if html.request.var("clone") and self._init_host():
            self._mode = "clone"
        else:
            self._mode = "new"

    def _init_host(self):
        clonename = html.get_ascii_input("clone")
        if clonename:
            if not watolib.Folder.current().has_host(clonename):
                raise MKUserError("host", _("You called this page with an invalid host name."))

            if not config.user.may("wato.clone_hosts"):
                raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))

            host = watolib.Folder.current().host(clonename)
            self._verify_host_type(host)
            return host
        else:
            return self._init_new_host_object()

    def action(self):
        if not html.transaction_valid():
            return "folder"

        attributes = watolib.collect_attributes(self._host_type_name(), new=True)
        cluster_nodes = self._get_cluster_nodes()

        hostname = html.request.var("host")
        Hostname().validate_value(hostname, "host")

        if html.check_transaction():
            watolib.Folder.current().create_hosts([(hostname, attributes, cluster_nodes)])

        self._host = watolib.Folder.current().host(hostname)

        inventory_url = watolib.folder_preserving_link([
            ("mode", "inventory"),
            ("host", self._host.name()),
            ("_scan", "1"),
        ])

        if not self._host.is_ping_host():
            create_msg = _('Successfully created the host. Now you should do a '
                           '<a href="%s">service discovery</a> in order to auto-configure '
                           'all services to be checked on this host.') % inventory_url
        else:
            create_msg = None

        if html.request.var("services"):
            raise HTTPRedirect(inventory_url)

        if html.request.var("diag_host"):
            html.request.set_var("_try", "1")
            return "diag_host", create_msg

        return "folder", create_msg

    def _vs_host_name(self):
        return Hostname(title=_("Hostname"),)


@mode_registry.register
class ModeCreateHost(CreateHostMode):
    @classmethod
    def name(cls):
        return "newhost"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]

    def title(self):
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Create new host")

    @classmethod
    def _init_new_host_object(cls):
        return watolib.Host(folder=watolib.Folder.current(),
                            host_name=html.request.var("host"),
                            attributes={},
                            cluster_nodes=None)

    @classmethod
    def _host_type_name(cls):
        return "host"

    @classmethod
    def _verify_host_type(cls, host):
        if host.is_cluster():
            raise MKGeneralException(_("Can not clone a cluster host as regular host"))


@mode_registry.register
class ModeCreateCluster(CreateHostMode):
    @classmethod
    def name(cls):
        return "newcluster"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts"]

    def _is_cluster(self):
        return True

    def title(self):
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Create new cluster")

    @classmethod
    def _init_new_host_object(cls):
        return watolib.Host(folder=watolib.Folder.current(),
                            host_name=html.request.var("host"),
                            attributes={},
                            cluster_nodes=[])

    @classmethod
    def _host_type_name(cls):
        return "cluster"

    @classmethod
    def _verify_host_type(cls, host):
        if not host.is_cluster():
            raise MKGeneralException(_("Can not clone a regular host as cluster host"))
