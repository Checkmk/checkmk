#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for creating and editing hosts"""

import abc
import copy
from collections.abc import Collection, Iterator
from dataclasses import asdict
from typing import Final, overload
from urllib.parse import unquote

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId

import cmk.utils.tags

from cmk.automations.results import DiagCmkAgentInput, PingHostCmd, PingHostInput

import cmk.gui.watolib.sites as watolib_sites
from cmk.gui import forms, user_sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.quick_setup.html import quick_setup_duplication_warning, quick_setup_locked_warning
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.agent_registration import remove_tls_registration_help
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri_contextless
from cmk.gui.valuespec import DropdownChoice, FixedValue, Hostname, ListOfStrings, ValueSpec
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib import bakery
from cmk.gui.watolib.agent_registration import remove_tls_registration
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.builtin_attributes import (
    HostAttributeIPv4Address,
    HostAttributeIPv6Address,
    HostAttributeSite,
)
from cmk.gui.watolib.check_mk_automations import (
    delete_hosts,
    diag_cmk_agent,
    ping_host,
    update_dns_cache,
)
from cmk.gui.watolib.config_hostname import ConfigHostname
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.host_attributes import collect_attributes
from cmk.gui.watolib.hosts_and_folders import (
    folder_from_request,
    folder_preserving_link,
    folder_tree,
    Host,
    validate_all_hosts,
)
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode

from cmk.shared_typing.mode_host import (
    I18nAgentConnection,
    I18nPingHost,
    ModeHost,
    ModeHostFormKeys,
    ModeHostSite,
)

from ._host_attributes import configure_attributes
from ._status_links import make_host_status_link


def register(mode_registry: ModeRegistry, page_registry: PageRegistry) -> None:
    mode_registry.register(ModeEditHost)
    mode_registry.register(ModeCreateHost)
    mode_registry.register(ModeCreateCluster)
    page_registry.register(PageEndpoint("ajax_ping_host", PageAjaxPingHost))
    page_registry.register(PageEndpoint("wato_ajax_diag_cmk_agent", PageAjaxDiagCmkAgent))


class ABCHostMode(WatoMode, abc.ABC):
    VAR_HOST: Final = "host"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    @abc.abstractmethod
    def _init_host(self) -> Host: ...

    def __init__(self) -> None:
        self._host = self._init_host()
        self._mode = "edit"
        super().__init__()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(_("Host"), breadcrumb)
        menu.dropdowns.insert(
            0,
            PageMenuDropdown(
                name="save",
                title=_("Host"),
                topics=[
                    self._page_menu_save_topic(),
                ],
            ),
        )
        return menu

    def _page_menu_save_topic(self) -> PageMenuTopic:
        return PageMenuTopic(
            title=_("Save this host and go to"),
            entries=list(self._page_menu_save_entries()),
        )

    def _page_menu_save_entries(self) -> Iterator[PageMenuEntry]:
        try:
            host_name = request.get_ascii_input(self.VAR_HOST)
        except MKUserError:
            host_name = None
        if folder_from_request(
            request.var("folder"),
            host_name,
        ).locked_hosts():
            return

        yield PageMenuEntry(
            title=_("Save & run service discovery"),
            shortcut_title=_("Save & run service discovery"),
            icon_name="save_to_services",
            item=make_form_submit_link(form_name="edit_host", button_name="_save"),
            is_shortcut=True,
            is_suggested=True,
            css_classes=["submit"],
        )

        yield PageMenuEntry(
            title=_("Save & view folder"),
            icon_name="save_to_folder",
            item=make_form_submit_link(form_name="edit_host", button_name="go_to_folder"),
            is_shortcut=True,
            is_suggested=True,
        )

        if not self._is_cluster():
            yield PageMenuEntry(
                title=_("Save & run connection tests"),
                icon_name="connection_tests",
                item=make_form_submit_link(form_name="edit_host", button_name="diag_host"),
                is_shortcut=True,
                is_suggested=True,
            )

    def _is_cluster(self) -> bool:
        return self._host.is_cluster()

    def _get_cluster_nodes(self):
        if not self._is_cluster():
            return None

        cluster_nodes = self._vs_cluster_nodes().from_html_vars("nodes")
        self._vs_cluster_nodes().validate_value(cluster_nodes, "nodes")
        if len(cluster_nodes) < 1:
            raise MKUserError("nodes_0", _("The cluster must have at least one node"))

        # Fake a cluster host in order to get calculated tag groups via effective attributes...
        cluster_computed_datasources = cmk.utils.tags.compute_datasources(
            Host(
                folder_from_request(request.var("folder"), request.get_ascii_input(self.VAR_HOST)),
                self._host.name(),
                collect_attributes("cluster", new=False),
                [],
            ).tag_groups()
        )

        for nr, cluster_node in enumerate(cluster_nodes):
            if cluster_node == self._host.name():
                raise MKUserError("nodes_%d" % nr, _("The cluster can not be a node of it's own"))

            if not Host.host_exists(cluster_node):
                raise MKUserError(
                    "nodes_%d" % nr,
                    _(
                        "The node <b>%s</b> does not exist "
                        "(must be a host that is configured via Setup)"
                    )
                    % cluster_node,
                )

            node_computed_datasources = cmk.utils.tags.compute_datasources(
                Host.load_host(cluster_node).tag_groups()
            )

            if datasource_differences := cluster_computed_datasources.get_differences_to(
                node_computed_datasources
            ):
                raise MKUserError(
                    "nodes_%d" % nr,
                    _("Cluster and nodes must have the same datasource. ")
                    + self._format_datasource_differences(cluster_node, datasource_differences),
                )

        return cluster_nodes

    def _format_datasource_differences(
        self,
        node_name: str,
        differences: cmk.utils.tags.DataSourceDifferences,
    ) -> str:
        def _get_is_or_is_not(is_ds: bool) -> str:
            return _("is") if is_ds else _("is <b>not</b>")

        return _("The cluster %s while the node <b>%s</b> %s") % (
            ", ".join(
                [
                    f"{_get_is_or_is_not(diff_ds.myself_is)} '{diff_ds.name}'"
                    for diff_ds in differences
                ]
            ),
            node_name,
            ", ".join(
                [
                    f"{_get_is_or_is_not(diff_ds.other_is)} '{diff_ds.name}'"
                    for diff_ds in differences
                ]
            ),
        )

    # TODO: Extract cluster specific parts from this method
    def page(self) -> None:
        # Show outcome of host validation. Do not validate new hosts
        errors = None
        if self._mode == "edit":
            errors = (
                validate_all_hosts(folder_tree(), [self._host.name()]).get(self._host.name(), [])
                + self._host.validation_errors()
            )

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

        lock_message = ""
        try:
            host_name = request.get_ascii_input(self.VAR_HOST)
        except MKUserError:
            host_name = None
        locked_hosts = folder_from_request(request.var("folder"), host_name).locked_hosts()
        if locked_hosts:
            if locked_hosts is True:
                lock_message = _("Host attributes locked (You cannot edit this host)")
            elif isinstance(locked_hosts, str):
                lock_message = locked_hosts
        if lock_message:
            html.div(lock_message, class_="info")

        self._page_form_quick_setup_warning()

        host_name_attribute_key: Final[str] = "host"
        form_name: Final[str] = "edit_host"
        html.vue_component(
            component_name="cmk-mode-host",
            data=asdict(
                ModeHost(
                    i18n_ping_host=I18nPingHost(
                        loading=_("Loading"),
                        error_host_not_dns_resolvable=_(
                            "Cannot resolve DNS. Enter a DNS-resolvable host name, an IP address "
                            "or set 'No IP' in the 'Network address' section."
                        ),
                        success_host_dns_resolvable=_("Name is DNS-resolvable"),
                        error_ip_not_pingable=_(
                            "Failed to ping the IP address. This could be due to an invalid IP, "
                            "network issues, or firewall restrictions."
                        ),
                        success_ip_pingable=_("Successfully pinged IP address"),
                    ),
                    i18n_agent_connection=I18nAgentConnection(
                        dialog_message=_(
                            "Already installed the agent? If so, please check your firewall settings"
                        ),
                        slide_in_title=_("Checkmk agent connection failed"),
                        msg_start=_("Test Checkmk agent connection"),
                        msg_success=_("Agent connection successful"),
                        msg_loading=_("Agent connection test running"),
                        msg_missing=_("Please enter a hostname to test Checkmk agent connection"),
                        msg_error=_(
                            "Connection failed, enter new hostname to check again "
                            "or download and install the Checkmk agent."
                        ),
                    ),
                    form_keys=ModeHostFormKeys(
                        form=form_name,
                        host_name=host_name_attribute_key,
                        ipv4_address=HostAttributeIPv4Address().name(),
                        ipv6_address=HostAttributeIPv6Address().name(),
                        site=HostAttributeSite().name(),
                        ip_address_family="tag_address_family",
                        tag_agent="tag_agent",
                        cb_change="cb_host_change"
                        if not self._is_cluster()
                        else "cb_cluster_change",
                    ),
                    sites=[
                        ModeHostSite(
                            id_hash=DropdownChoice.option_id(site_id),
                            site_id=site_id,
                        )
                        for site_id, _site_name in user_sites.get_activation_site_choices()
                    ],
                    url=folder_preserving_link([("mode", "agent_of_host"), ("host", "TEST")]),
                    host_name=self._host.name(),
                )
            ),
        )

        with html.form_context(form_name, method="POST"):
            html.prevent_password_auto_completion()

            basic_attributes: list[tuple[str, ValueSpec, object]] = [
                # attribute name, valuepec, default value
                (host_name_attribute_key, self._vs_host_name(), self._host.name()),
            ]

            if self._is_cluster():
                nodes = self._host.cluster_nodes()
                assert nodes is not None
                basic_attributes += [
                    # attribute name, valuepec, default value
                    ("nodes", self._vs_cluster_nodes(), nodes),
                ]
            try:
                host_name = request.get_ascii_input(self.VAR_HOST)
            except MKUserError:
                host_name = None
            configure_attributes(
                new=self._mode != "edit",
                hosts={self._host.name(): self._host} if self._mode != "new" else {},
                for_what="host" if not self._is_cluster() else "cluster",
                parent=folder_from_request(request.var("folder"), host_name),
                basic_attributes=basic_attributes,
            )

            if self._mode != "edit":
                html.set_focus(host_name_attribute_key)

            forms.end()
            html.hidden_fields()

    def _page_form_quick_setup_warning(self) -> None:
        if (
            (locked_by := self._host.locked_by())
            and is_locked_by_quick_setup(locked_by)
            and request.get_ascii_input("mode") != "edit_configuration_bundle"
        ):
            quick_setup_locked_warning(locked_by, "host")

    def _vs_cluster_nodes(self):
        return ListOfStrings(
            title=_("Nodes"),
            valuespec=ConfigHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
            orientation="horizontal",
            help=_(
                "Enter the host names of the cluster nodes. These hosts must be present in Setup."
            ),
        )

    @abc.abstractmethod
    def _vs_host_name(self):
        raise NotImplementedError()


# TODO: Split this into two classes ModeEditHost / ModeEditCluster. The problem with this is that
# we simply don't know whether or not a cluster or regular host is about to be edited. The GUI code
# simply wants to link to the "host edit page". We could try to use some factory to decide this when
# the edit_host mode is called.
class ModeEditHost(ABCHostMode):
    @classmethod
    def name(cls) -> str:
        return "edit_host"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]

    def ensure_permissions(self) -> None:
        super().ensure_permissions()
        self._host.permissions.need_permission("read")

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, host: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def _breadcrumb_url(self) -> str:
        return self.mode_url(host=self._host.name())

    @classmethod
    def set_vars(cls, host: HostName) -> None:
        request.set_var(cls.VAR_HOST, host)

    @property
    def host(self) -> Host:
        return self._host

    def _init_host(self) -> Host:
        hostname = request.get_validated_type_input_mandatory(HostName, self.VAR_HOST)
        folder = folder_from_request(request.var("folder"), hostname)
        if not folder.has_host(hostname):
            raise MKUserError(self.VAR_HOST, _("You called this page with an invalid host name."))
        host = folder.load_host(hostname)
        return host

    def title(self) -> str:
        return _("Properties of host") + " " + self._host.name()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="host",
                    title=_("Host"),
                    topics=[
                        self._page_menu_save_topic(),
                        PageMenuTopic(
                            title=_("For this host"),
                            entries=list(page_menu_host_entries(self.name(), self._host)),
                        ),
                        PageMenuTopic(
                            title=_("For all hosts on site %s") % self._host.site_id(),
                            entries=list(page_menu_all_hosts_entries(self._should_use_dns_cache())),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        folder = folder_from_request(request.var("folder"), request.get_ascii_input(self.VAR_HOST))
        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=folder.path()))

        if request.var("_update_dns_cache") and self._should_use_dns_cache():
            user.need_permission("wato.update_dns_cache")
            update_dns_cache_result = update_dns_cache(
                automation_config=make_automation_config(active_config.sites[self._host.site_id()]),
                debug=active_config.debug,
            )
            infotext = (
                _("Successfully updated IP addresses of %d hosts.")
                % update_dns_cache_result.n_updated
            )
            if update_dns_cache_result.failed_hosts:
                infotext += "<br><br><b>Host names failed to lookup:</b> " + ", ".join(
                    ["<tt>%s</tt>" % h for h in update_dns_cache_result.failed_hosts]
                )
            flash(infotext)
            return None

        if request.var("delete"):  # Delete this host
            folder.delete_hosts(
                [self._host.name()],
                automation=delete_hosts,
                pprint_value=active_config.wato_pprint_config,
                debug=active_config.debug,
            )
            return redirect(mode_url("folder", folder=folder.path()))

        if request.var("_remove_tls_registration"):
            remove_tls_registration(
                [
                    (
                        make_automation_config(active_config.sites[self._host.site_id()]),
                        [self._host.name()],
                    )
                ],
                debug=active_config.debug,
            )
            return None

        attributes = collect_attributes("host" if not self._is_cluster() else "cluster", new=False)
        host = Host.host(self._host.name())
        if host is None:
            flash(f"Host {self._host.name()} could not be found.")
            return None

        host.edit(
            attributes, self._get_cluster_nodes(), pprint_value=active_config.wato_pprint_config
        )
        self._host = folder.load_host(self._host.name())

        if request.var("_save"):
            return redirect(mode_url("inventory", folder=folder.path(), host=self._host.name()))
        if request.var("diag_host"):
            return redirect(
                mode_url(
                    "diag_host", folder=folder.path(), host=self._host.name(), _start_on_load="1"
                )
            )
        return redirect(mode_url("folder", folder=folder.path()))

    def _should_use_dns_cache(self) -> bool:
        site = self._host.effective_attributes()["site"]
        return watolib_sites.get_effective_global_setting(
            site,
            is_wato_slave_site(),
            "use_dns_cache",
        )

    def _vs_host_name(self):
        return FixedValue(
            value=self._host.name(),
            title=_("Host name"),
        )


def page_menu_all_hosts_entries(should_use_dns_cache: bool) -> Iterator[PageMenuEntry]:
    if should_use_dns_cache:
        yield PageMenuEntry(
            title=_("Update DNS cache"),
            icon_name="update",
            item=make_simple_link(
                makeactionuri(request, transactions, [("_update_dns_cache", "1")])
            ),
            shortcut_title=_("Update site DNS cache"),
            is_shortcut=True,
            is_suggested=True,
        )


def _host_page_menu_hook(host_name: HostName) -> Iterator[PageMenuEntry]:
    """Overridden in some editions to extend the page menu"""
    yield from []


def page_menu_host_entries(mode_name: str, host: Host) -> Iterator[PageMenuEntry]:
    if mode_name != "edit_host":
        yield PageMenuEntry(
            title=_("Properties"),
            icon_name="edit",
            item=make_simple_link(
                folder_preserving_link([("mode", "edit_host"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    if mode_name != "inventory":
        yield PageMenuEntry(
            title=_("Run service discovery"),
            icon_name="services",
            item=make_simple_link(
                folder_preserving_link([("mode", "inventory"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    if mode_name != "diag_host" and not host.is_cluster():
        yield PageMenuEntry(
            title=_("Test connection"),
            icon_name="analysis",
            item=make_simple_link(
                folder_preserving_link([("mode", "diag_host"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    yield PageMenuEntry(
        title=_("Test notifications"),
        icon_name="analysis",
        item=make_simple_link(
            makeuri_contextless(
                request,
                [
                    ("mode", "test_notifications"),
                    ("host_name", host.name()),
                ],
                filename="wato.py",
            )
        ),
    )

    if mode_name != "object_parameters" and user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                folder_preserving_link(
                    [("mode", "object_parameters"), (ABCHostMode.VAR_HOST, host.name())]
                )
            ),
        )

    if mode_name == "object_parameters" or mode_name == "edit_host" and user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Rules"),
            icon_name="rulesets",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [
                        ("mode", "rule_search"),
                        ("filled_in", "search"),
                        ("search_p_ruleset_deprecated", "OFF"),
                        ("search_p_rule_host_list_USE", "ON"),
                        ("search_p_rule_host_list", host.name()),
                    ],
                    filename="wato.py",
                )
            ),
        )

    yield make_host_status_link(host_name=host.name(), view_name="hoststatus")

    if user.may("wato.rulesets") and host.is_cluster():
        yield PageMenuEntry(
            title=_("Clustered services"),
            icon_name="rulesets",
            item=make_simple_link(
                folder_preserving_link(
                    [("mode", "edit_ruleset"), ("varname", "clustered_services")]
                )
            ),
        )

    yield from _host_page_menu_hook(host.name())

    if mode_name == "edit_host" and not host.locked():
        locked_by_quick_setup = is_locked_by_quick_setup(host.locked_by())
        if user.may("wato.rename_hosts") and not locked_by_quick_setup:
            yield PageMenuEntry(
                title=_("Rename"),
                icon_name="rename_host",
                item=make_simple_link(
                    folder_preserving_link(
                        [("mode", "rename_host"), (ABCHostMode.VAR_HOST, host.name())]
                    )
                ),
            )

        if user.may("wato.manage_hosts") and user.may("wato.clone_hosts"):
            yield PageMenuEntry(
                title=_("Clone"),
                icon_name="insert",
                item=make_simple_link(host.clone_url()),
            )

        if not locked_by_quick_setup:
            yield PageMenuEntry(
                title=_("Delete"),
                icon_name="delete",
                item=make_simple_link(
                    make_confirm_delete_link(
                        url=makeactionuri(request, transactions, [("delete", "1")]),
                        title=_("Delete host"),
                        suffix=host.name(),
                    )
                ),
            )

        if user.may("wato.auditlog"):
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name="auditlog",
                item=make_simple_link(make_object_audit_log_url(host.object_ref())),
            )

        if user.may("wato.manage_hosts"):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name={"icon": "tls", "emblem": "remove"},
                item=make_simple_link(
                    make_confirm_delete_link(
                        url=makeactionuri(
                            request, transactions, [("_remove_tls_registration", "1")]
                        ),
                        title=_("Remove TLS registration"),
                        message=remove_tls_registration_help(),
                        confirm_button=_("Remove"),
                        warning=True,
                    )
                ),
            )


class CreateHostMode(ABCHostMode):
    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts"]

    def ensure_permissions(self) -> None:
        super().ensure_permissions()
        if self._mode == "clone" and not user.may("wato.clone_hosts"):
            raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))

    @classmethod
    @abc.abstractmethod
    def _init_new_host_object(cls) -> Host:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def _host_type_name(cls):
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def _verify_host_type(cls, host):
        raise NotImplementedError()

    def _from_vars(self) -> None:
        if request.var("clone"):
            self._mode = "clone"
        else:
            self._mode = "new"

    def _init_host(self) -> Host:
        self._clone_source: Host | None = None
        clone_source_name = request.get_ascii_input("clone")
        if not clone_source_name:
            return self._init_new_host_object()

        folder = folder_from_request(request.var("folder"), request.get_ascii_input(self.VAR_HOST))
        if not folder.has_host(HostName(clone_source_name)):
            raise MKUserError(self.VAR_HOST, _("You called this page with an invalid host name."))

        # save the original host
        self._clone_source = folder.load_host(HostName(clone_source_name))

        host = copy.deepcopy(self._clone_source)

        # remove the quick setup lock from the clone
        if is_locked_by_quick_setup(host.locked_by()):
            host.attributes.pop("locked_by", None)
            host.attributes.pop("locked_attributes", None)

        self._verify_host_type(host)
        return host

    def action(self) -> ActionResult:
        if not transactions.transaction_valid():
            return redirect(mode_url("folder"))

        attributes = collect_attributes(self._host_type_name(), new=True)
        cluster_nodes = self._get_cluster_nodes()
        try:
            hostname = request.get_validated_type_input_mandatory(HostName, self.VAR_HOST)
        except MKUserError:
            hostname = HostName("")

        Hostname().validate_value(request.get_ascii_input_mandatory(self.VAR_HOST), self.VAR_HOST)

        folder = folder_from_request(request.var("folder"), hostname)
        if transactions.check_transaction():
            folder.create_hosts(
                [(hostname, attributes, cluster_nodes)],
                pprint_value=active_config.wato_pprint_config,
            )

        self._host = folder.load_host(hostname)
        bakery.try_bake_agents_for_hosts([hostname], debug=active_config.debug)

        inventory_url = folder_preserving_link(
            [
                ("mode", "inventory"),
                ("host", self._host.name()),
                ("_scan", "1"),
            ]
        )

        create_msg = (
            None
            if self._host.is_ping_host()
            else (
                _(
                    "Successfully created the host. Now you should do a "
                    '<a href="%s">service discovery</a> in order to auto-configure '
                    "all services to be checked on this host."
                )
                % inventory_url
            )
        )

        if request.var("_save"):
            return redirect(inventory_url)

        if create_msg:
            flash(create_msg)

        if request.var("diag_host"):
            return redirect(
                mode_url("diag_host", folder=folder.path(), host=self._host.name(), _try="1")
            )

        return redirect(mode_url("folder", folder=folder.path()))

    def _page_form_quick_setup_warning(self) -> None:
        if (
            self._clone_source
            and (locked_by := self._clone_source.locked_by())
            and is_locked_by_quick_setup(locked_by)
        ):
            quick_setup_duplication_warning(locked_by, "host")

    def _vs_host_name(self):
        return Hostname(
            title=_("Host name"),
        )


class ModeCreateHost(CreateHostMode):
    @classmethod
    def name(cls) -> str:
        return "newhost"

    def title(self) -> str:
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Add host")

    @classmethod
    def _init_new_host_object(cls) -> Host:
        try:
            host_name = request.get_validated_type_input_mandatory(
                HostName, cls.VAR_HOST, deflt=HostName("")
            )
        except MKUserError:
            host_name = HostName("")
        return Host(
            folder=folder_from_request(request.var("folder"), host_name),
            host_name=host_name,
            attributes={},
            cluster_nodes=None,
        )

    @classmethod
    def _host_type_name(cls):
        return "host"

    @classmethod
    def _verify_host_type(cls, host):
        if host.is_cluster():
            raise MKGeneralException(_("Can not clone a cluster host as regular host"))


class ModeCreateCluster(CreateHostMode):
    @classmethod
    def name(cls) -> str:
        return "newcluster"

    def _is_cluster(self) -> bool:
        return True

    def title(self) -> str:
        if self._mode == "clone":
            return _("Create clone of %s") % self._host.name()
        return _("Create cluster")

    @classmethod
    def _init_new_host_object(cls) -> Host:
        try:
            host_name = request.get_validated_type_input_mandatory(
                HostName, cls.VAR_HOST, deflt=HostName("")
            )
        except MKUserError:
            host_name = HostName("")
        return Host(
            folder=folder_from_request(request.var("folder"), host_name),
            host_name=host_name,
            attributes={},
            cluster_nodes=[],
        )

    @classmethod
    def _host_type_name(cls):
        return "cluster"

    @classmethod
    def _verify_host_type(cls, host):
        if not host.is_cluster():
            raise MKGeneralException(_("Can not clone a regular host as cluster host"))


class PageAjaxPingHost(AjaxPage):
    def page(self, config: Config) -> PageResult:
        site_id = request.get_validated_type_input(SiteId, "site_id", deflt=omd_site())
        ip_or_dns_name = request.get_ascii_input_mandatory("ip_or_dns_name")
        cmd = request.get_validated_type_input(PingHostCmd, "cmd", PingHostCmd.PING)

        result = ping_host(
            automation_config=make_automation_config(config.sites[site_id]),
            ping_host_input=PingHostInput(
                ip_or_dns_name=unquote(ip_or_dns_name),
                base_cmd=cmd,
            ),
        )
        return {
            "status_code": result.return_code,
            "output": result.response,
        }


class PageAjaxDiagCmkAgent(AjaxPage):
    def page(self, config: Config) -> PageResult:
        api_request = self.webapi_request()
        result = diag_cmk_agent(
            automation_config=make_automation_config(config.sites[api_request["site_id"]]),
            diag_cmk_agent_input=DiagCmkAgentInput(
                host_name=api_request["host_name"],
                ip_address=api_request["ipaddress"],
                address_family=api_request["address_family"],
                agent_port=api_request["agent_port"],
                timeout=api_request["timeout"],
            ),
        )

        return {
            "status_code": result.return_code,
            "output": result.response,
        }
