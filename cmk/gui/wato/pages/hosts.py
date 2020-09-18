#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for creating and editing hosts"""

import abc
from typing import Iterator, Optional, Type

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError, MKAuthException, MKGeneralException, HTTPRedirect
from cmk.gui.valuespec import (
    ListOfStrings,
    Hostname,
    FixedValue,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_form_submit_link,
    make_simple_form_page_menu,
)

from cmk.gui.plugins.wato.utils import (
    mode_registry,
    configure_attributes,
    ConfigHostname,
)
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.context_buttons import make_host_status_link
from cmk.gui.watolib.hosts_and_folders import CREHost
from cmk.gui.wato.pages.folders import delete_host_after_confirm, ModeFolder


class ABCHostMode(WatoMode, metaclass=abc.ABCMeta):
    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeFolder

    @abc.abstractmethod
    def _init_host(self):
        raise NotImplementedError()

    def __init__(self):
        self._host = self._init_host()
        self._mode = "edit"
        super(ABCHostMode, self).__init__()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb)
        menu.dropdowns.insert(
            0,
            PageMenuDropdown(
                name="save",
                title=_("Save"),
                topics=[
                    self._page_menu_save_topic(),
                ],
            ))
        return menu

    def _page_menu_save_topic(self) -> PageMenuTopic:
        return PageMenuTopic(
            title=_("Save this host and go to"),
            entries=list(self._page_menu_save_entries()),
        )

    def _page_menu_save_entries(self) -> Iterator[PageMenuEntry]:
        if watolib.Folder.current().locked_hosts():
            return

        yield PageMenuEntry(
            title=_("Save & go to service configuration"),
            shortcut_title=_("Save & go to service configuration"),
            icon_name="save_to_services",
            item=make_form_submit_link(form_name="edit_host", button_name="services"),
            is_shortcut=True,
            is_suggested=True,
        )

        yield PageMenuEntry(
            title=_("Save & go to folder"),
            icon_name="save_to_folder",
            item=make_form_submit_link(form_name="edit_host", button_name="save"),
            is_shortcut=True,
            is_suggested=True,
        )

        if not self._is_cluster():
            yield PageMenuEntry(
                title=_("Save & go to connection tests"),
                icon_name="save_to_diagnose",
                item=make_form_submit_link(form_name="edit_host", button_name="diag_host"),
                is_shortcut=True,
                is_suggested=True,
            )

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

            attributes = watolib.collect_attributes("cluster", new=False)
            cluster_agent_ds_type = attributes.get("tag_agent", "cmk-agent")
            cluster_snmp_ds_type = attributes.get("tag_snmp_ds", "no-snmp")

            node_agent_ds_type = watolib.hosts_and_folders.Host.host(cluster_node).tag_groups().get(
                "agent")
            node_snmp_ds_type = watolib.hosts_and_folders.Host.host(cluster_node).tag_groups().get(
                "snmp_ds")

            if node_agent_ds_type != cluster_agent_ds_type or \
                    node_snmp_ds_type != cluster_snmp_ds_type:
                raise MKUserError(
                    "nodes_%d" % nr,
                    _("Cluster and nodes must have the same "
                      "datasource! The node <b>%s</b> has datasources "
                      "<b>%s</b> and <b>%s</b> while the cluster has datasources "
                      "<b>%s</b> and <b>%s</b>.") % (
                          cluster_node,
                          node_agent_ds_type,
                          node_snmp_ds_type,
                          cluster_agent_ds_type,
                          cluster_snmp_ds_type,
                      ))

        return cluster_nodes

    # TODO: Extract cluster specific parts from this method
    def page(self):
        # Show outcome of host validation. Do not validate new hosts
        errors = None
        if self._mode == "edit":
            errors = watolib.validate_all_hosts([self._host.name()]).get(
                self._host.name(), []) + self._host.validation_errors()

        if errors:
            html.open_div(class_="info")
            html.open_table(class_="validationerror", boder="0", cellspacing="0", cellpadding="0")
            html.open_tr()

            html.open_td(class_="img")
            html.icon("validation_error")
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

        lock_message = u""
        locked_hosts = watolib.Folder.current().locked_hosts()
        if locked_hosts:
            if locked_hosts is True:
                lock_message = _("Host attributes locked (You cannot edit this host)")
            elif isinstance(locked_hosts, str):
                lock_message = locked_hosts
        if lock_message:
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
class ModeEditHost(ABCHostMode):
    @classmethod
    def name(cls):
        return "edit_host"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def _breadcrumb_url(self) -> str:
        return html.makeuri_contextless([("mode", self.name()), ("host", self._host.name())],
                                        filename="wato.py")

    def _init_host(self):
        hostname = html.request.get_ascii_input_mandatory("host")

        if not watolib.Folder.current().has_host(hostname):
            raise MKUserError("host", _("You called this page with an invalid host name."))

        return watolib.Folder.current().host(hostname)

    def title(self):
        return _("Properties of host") + " " + self._host.name()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="hosts",
                    title=_("Hosts"),
                    topics=[
                        self._page_menu_save_topic(),
                        PageMenuTopic(
                            title=_("For this host"),
                            entries=list(page_menu_host_entries(self.name(), self._host)),
                        ),
                        PageMenuTopic(
                            title=_("For all hosts on site %s") % self._host.site_id(),
                            entries=[
                                PageMenuEntry(
                                    title=_("Refresh DNS information"),
                                    icon_name="update",
                                    item=make_simple_link(
                                        html.makeactionuri([("_update_dns_cache", "1")])),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self):
        if html.request.var("_update_dns_cache"):
            if not html.check_transaction():
                return None
            config.user.need_permission("wato.update_dns_cache")
            num_updated, failed_hosts = watolib.check_mk_automation(self._host.site_id(),
                                                                    "update-dns-cache", [])
            infotext = _("Successfully updated IP addresses of %d hosts.") % num_updated
            if failed_hosts:
                infotext += "<br><br><b>Hostnames failed to lookup:</b> " \
                          + ", ".join(["<tt>%s</tt>" % h for h in failed_hosts])
            return None, infotext

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
        if html.request.var("diag_host"):
            html.request.set_var("_start_on_load", "1")
            return "diag_host"
        return "folder"

    def _vs_host_name(self):
        return FixedValue(
            self._host.name(),
            title=_("Hostname"),
        )


def page_menu_host_entries(mode_name: str, host: CREHost) -> Iterator[PageMenuEntry]:
    if mode_name != "edit_host":
        yield PageMenuEntry(
            title=_("Properties"),
            icon_name="edit",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "edit_host"), ("host", host.name())])),
        )

    if mode_name != "inventory":
        yield PageMenuEntry(
            title=_("Service configuration"),
            icon_name="services",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "inventory"), ("host", host.name())])),
        )

    if mode_name != "diag_host" and not host.is_cluster():
        yield PageMenuEntry(
            title=_("Connection tests"),
            icon_name="diagnose",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "diag_host"), ("host", host.name())])),
        )

    if mode_name != "object_parameters" and config.user.may('wato.rulesets'):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "object_parameters"),
                                                ("host", host.name())])),
        )

    yield make_host_status_link(host_name=host.name(), view_name="hoststatus")

    if config.user.may('wato.rulesets') and host.is_cluster():
        yield PageMenuEntry(
            title=_("Clustered services"),
            icon_name="rulesets",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                ("varname", "clustered_services")])),
        )

    if watolib.has_agent_bakery() and config.user.may('wato.download_agents'):
        yield PageMenuEntry(
            title=_("Monitoring agent"),
            icon_name="agents",
            item=make_simple_link(
                watolib.folder_preserving_link([("mode", "agent_of_host"), ("host", host.name())])),
        )

    if mode_name == "edit_host" and not host.locked():
        if config.user.may("wato.rename_hosts"):
            yield PageMenuEntry(
                title=_("Rename"),
                icon_name="rename_host",
                item=make_simple_link(
                    watolib.folder_preserving_link([("mode", "rename_host"),
                                                    ("host", host.name())])),
            )

        if config.user.may("wato.manage_hosts") and config.user.may("wato.clone_hosts"):
            yield PageMenuEntry(
                title=_("Clone"),
                icon_name="insert",
                item=make_simple_link(host.clone_url()),
            )

        yield PageMenuEntry(
            title=_("Delete"),
            icon_name="delete",
            item=make_simple_link(html.makeactionuri([("delete", "1")])),
        )


class CreateHostMode(ABCHostMode):
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
        clonename = html.request.get_ascii_input("clone")
        if not clonename:
            return self._init_new_host_object()
        if not watolib.Folder.current().has_host(clonename):
            raise MKUserError("host", _("You called this page with an invalid host name."))
        if not config.user.may("wato.clone_hosts"):
            raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))
        host = watolib.Folder.current().host(clonename)
        self._verify_host_type(host)
        return host

    def action(self):
        if not html.transaction_valid():
            return "folder"

        attributes = watolib.collect_attributes(self._host_type_name(), new=True)
        cluster_nodes = self._get_cluster_nodes()

        hostname = html.request.get_ascii_input_mandatory("host")
        Hostname().validate_value(hostname, "host")

        if html.check_transaction():
            watolib.Folder.current().create_hosts([(hostname, attributes, cluster_nodes)])

        self._host = watolib.Folder.current().host(hostname)

        inventory_url = watolib.folder_preserving_link([
            ("mode", "inventory"),
            ("host", self._host.name()),
            ("_scan", "1"),
        ])

        create_msg = None if self._host.is_ping_host() else (
            _('Successfully created the host. Now you should do a '
              '<a href="%s">service discovery</a> in order to auto-configure '
              'all services to be checked on this host.') % inventory_url)

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
