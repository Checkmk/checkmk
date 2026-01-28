#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for creating and editing hosts"""

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Collection, Iterator, Sequence
from dataclasses import asdict
from typing import Final, Literal, overload, override
from urllib.parse import unquote, urlparse

from livestatus import SiteConfigurations

import cmk.gui.watolib.sites as watolib_sites
import cmk.utils.tags
from cmk.automations.results import DiagCmkAgentInput, PingHostCmd, PingHostInput
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.version import omd_version
from cmk.gui import forms, user_sites
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
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
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.quick_setup.html import quick_setup_duplication_warning, quick_setup_locked_warning
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.agent_commands import (
    agent_commands_registry,
)
from cmk.gui.utils.agent_registration import remove_tls_registration_help
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.loading_transition import LoadingTransition
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    make_confirm_delete_link,
    makeactionuri,
    makeuri_contextless,
)
from cmk.gui.valuespec import (
    DropdownChoice,
    FixedValue,
    HostAddress,
    Hostname,
    ListOfStrings,
    ValueSpec,
)
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
from cmk.gui.watolib.host_attributes import (
    all_host_attributes,
    collect_attributes,
    HostAttributes,
)
from cmk.gui.watolib.hosts_and_folders import (
    folder_from_request,
    folder_preserving_link,
    folder_tree,
    Host,
    strip_hostname_whitespace_chars,
    validate_all_hosts,
)
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.shared_typing.mode_host import (
    AgentInstallCmds,
    AgentRegistrationCmds,
    AgentSlideout,
    I18nPingHost,
    ModeHost,
    ModeHostAgentConnectionMode,
    ModeHostFormKeys,
    ModeHostServerPerSite,
    ModeHostSite,
)
from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.paths import omd_root

from ._host_attributes import configure_attributes
from ._status_links import make_host_status_link


def register(mode_registry: ModeRegistry, page_registry: PageRegistry) -> None:
    mode_registry.register(ModeEditHost)
    mode_registry.register(ModeCreateHost)
    mode_registry.register(ModeCreateCluster)
    page_registry.register(PageEndpoint("ajax_ping_host", PageAjaxPingHost()))
    page_registry.register(PageEndpoint("wato_ajax_diag_cmk_agent", PageAjaxDiagCmkAgent()))


class UpdateDnsCacheLoadingContainer:
    """Class grouping the elements and logic to show a loading container when updating the
    site DNS cache.

    The different parts are spread at different locations, so we group them here for better
    maintainability (this is still not nice but accepted as we will migrate the page at some point)
    """

    a_tag_id = "update_site_dns_cache"
    div_load_container_id = "container_load_update_dns_container"

    @classmethod
    def render_load_container(cls) -> None:
        html.open_div(id=cls.div_load_container_id, style="display: none")
        html.show_message_by_msg_type(
            msg=_("Updating site DNS cache"),
            msg_type="waiting",
            flashed=True,
        )
        html.close_div()

    @classmethod
    def include_catch_link_script(cls) -> None:
        html.javascript(
            f"""
        document.getElementById('menu_suggestion_{cls.a_tag_id}').addEventListener('click', function (event) {{
            document.getElementById('{cls.div_load_container_id}').style.display = 'block';
        }});
        """
        )


class ABCHostMode(WatoMode, abc.ABC):
    VAR_HOST: Final = "host"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    @abc.abstractmethod
    def _init_host(self) -> Host: ...

    def __init__(self) -> None:
        self._host = self._init_host()
        self._mode: Literal["edit", "new", "clone", "prefill"] = "edit"
        super().__init__()

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
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
            title=_("Save & edit"),
            icon_name=StaticIcon(IconNames.save),
            item=make_form_submit_link(form_name="edit_host", button_name="save_and_edit"),
        )

        yield PageMenuEntry(
            title=_("Save & run service discovery"),
            shortcut_title=_("Save & run service discovery"),
            icon_name=StaticIcon(IconNames.save_to_services),
            item=make_form_submit_link(form_name="edit_host", button_name="_save"),
            is_shortcut=True,
            is_suggested=True,
            css_classes=["submit"],
        )

        yield PageMenuEntry(
            title=_("Save & view folder"),
            icon_name=StaticIcon(IconNames.save_to_folder),
            item=make_form_submit_link(form_name="edit_host", button_name="go_to_folder"),
            is_shortcut=True,
            is_suggested=True,
        )

        if not self._is_cluster():
            yield PageMenuEntry(
                title=_("Save & run connection tests"),
                icon_name=StaticIcon(IconNames.connection_tests),
                item=make_form_submit_link(form_name="edit_host", button_name="diag_host"),
                is_shortcut=True,
                is_suggested=True,
            )

    def _is_cluster(self) -> bool:
        return self._host.is_cluster()

    def _get_cluster_nodes(self, attributes: HostAttributes) -> Sequence[HostName] | None:
        if not self._is_cluster():
            return None

        cluster_nodes_str = self._vs_cluster_nodes().from_html_vars("nodes")
        self._vs_cluster_nodes().validate_value(cluster_nodes_str, "nodes")
        if len(cluster_nodes_str) < 1:
            raise MKUserError("nodes_0", _("The cluster must have at least one node"))

        cluster_nodes = [HostName(node) for node in cluster_nodes_str]

        # Fake a cluster host in order to get calculated tag groups via effective attributes...
        cluster_computed_datasources = cmk.utils.tags.compute_datasources(
            Host(
                folder_from_request(request.var("folder"), request.get_ascii_input(self.VAR_HOST)),
                self._host.name(),
                attributes,
                [],
            ).tag_groups()
        )

        for nr, cluster_node in enumerate(cluster_nodes):
            if cluster_node == self._host.name():
                raise MKUserError("nodes_%d" % nr, _("The cluster cannot be a node of itself"))

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
                    _("Cluster and nodes must have the same data source. ")
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
    def page(self, config: Config) -> None:
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
            html.static_icon(StaticIcon(IconNames.validation_error))
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
                lock_message = _("Host attributes locked (you cannot edit this host)")
            elif isinstance(locked_hosts, str):
                lock_message = locked_hosts
        if lock_message:
            html.div(lock_message, class_="info")

        self._page_form_quick_setup_warning()

        host_name_attribute_key: Final[str] = "host"
        form_name: Final[str] = "edit_host"
        version = ".".join(omd_version(omd_root).split(".")[:-1])
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
                    form_keys=ModeHostFormKeys(
                        form=form_name,
                        host_name=host_name_attribute_key,
                        ipv4_address=HostAttributeIPv4Address().name(),
                        ipv6_address=HostAttributeIPv6Address().name(),
                        site=HostAttributeSite().name(),
                        relay="relay",
                        ip_address_family="tag_address_family",
                        cmk_agent_connection="cmk_agent_connection",
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
                        for site_id, _site_name in user_sites.get_activation_site_choices(
                            config.sites
                        )
                    ],
                    default_relay_id_hash=DropdownChoice.option_id(""),
                    server_per_site=[
                        ModeHostServerPerSite(
                            site_id=site_id,
                            server=server_name
                            if config_key.get("multisiteurl")
                            and (server_name := urlparse(config_key["multisiteurl"]).hostname)
                            else request.host,
                        )
                        for site_id, config_key in config.sites.items()
                    ],
                    agent_connection_modes=[
                        ModeHostAgentConnectionMode(
                            id_hash=DropdownChoice.option_id(mode.value),
                            mode=mode.value,
                        )
                        for mode in HostAgentConnectionMode
                    ],
                    agent_slideout=AgentSlideout(
                        all_agents_url=folder_preserving_link([("mode", "agents")]),
                        host_name=self._host.name(),
                        agent_install_cmds=AgentInstallCmds(
                            **asdict(
                                agent_commands_registry["agent_commands"].install_cmds(version)
                            )
                        ),
                        agent_registration_cmds=AgentRegistrationCmds(
                            **asdict(agent_commands_registry["agent_commands"].registration_cmds())
                        ),
                        legacy_agent_url=agent_commands_registry[
                            "agent_commands"
                        ].legacy_agent_url(),
                        save_host=self._mode in ["new", "prefill", "clone"],
                        host_exists=Host.host_exists(self._host.name()),
                    ),
                    host_name=self._host.name(),
                )
            ),
        )
        UpdateDnsCacheLoadingContainer.render_load_container()

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
                all_host_attributes(config.wato_host_attrs, config.tags.get_tag_groups_by_topic()),
                new=self._mode != "edit",
                hosts={self._host.name(): self._host} if self._mode != "new" else {},
                for_what="host" if not self._is_cluster() else "cluster",
                parent=folder_from_request(request.var("folder"), host_name),
                basic_attributes=basic_attributes,
                aux_tags_by_tag=config.tags.get_aux_tags_by_tag(),
                config=config,
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

    def _vs_cluster_nodes(self) -> ListOfStrings:
        return ListOfStrings(
            title=_("Nodes"),
            valuespec=ConfigHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
            orientation="horizontal",
            help=_(
                "Enter the host names of the cluster nodes. These hosts must be present in Setup."
            ),
        )

    @abc.abstractmethod
    def _vs_host_name(self) -> ValueSpec:
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

    def page(self, config: Config) -> None:
        super().page(config)
        UpdateDnsCacheLoadingContainer.include_catch_link_script()

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
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
                            entries=list(
                                page_menu_all_hosts_entries(
                                    self._should_use_dns_cache(config.sites)
                                )
                            ),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self, config: Config) -> ActionResult:
        folder = folder_from_request(request.var("folder"), request.get_ascii_input(self.VAR_HOST))
        if not transactions.check_transaction():
            return redirect(mode_url("folder", folder=folder.path()))

        if request.var("_update_dns_cache") and self._should_use_dns_cache(config.sites):
            user.need_permission("wato.update_dns_cache")
            update_dns_cache_result = update_dns_cache(
                automation_config=make_automation_config(config.sites[self._host.site_id()]),
                debug=config.debug,
            )
            n = update_dns_cache_result.n_updated
            infotext = (
                _("Site DNS cache is already up to date.")
                if n == 0
                else _("Site DNS cache updated for 1 host.")
                if n == 1
                else _("Site DNS cache updated for %d hosts.") % n
            )
            flash(infotext)

            if update_dns_cache_result.failed_hosts:
                failed_hosts = update_dns_cache_result.failed_hosts
                display_limit = 5

                if len(failed_hosts) <= display_limit:
                    hosts_display = ", ".join([str(h) for h in failed_hosts])
                else:
                    hosts_display = ", ".join([str(h) for h in failed_hosts[:display_limit]])
                    remaining = len(failed_hosts) - display_limit
                    hosts_display += _(", +%d more") % remaining

                failed_warning_message = _(
                    "<b>Lookup IPv4 addresses of %d hosts failed.</b><br>"
                    "Monitoring for these hosts may be incomplete.<br><br>"
                    "<b>Affected hosts:</b> %s"
                ) % (len(failed_hosts), hosts_display)

                flash(failed_warning_message, msg_type="warning")
            return None

        if request.var("delete"):  # Delete this host
            folder.delete_hosts(
                [self._host.name()],
                automation=delete_hosts,
                pprint_value=config.wato_pprint_config,
                debug=config.debug,
                use_git=config.wato_use_git,
            )
            return redirect(mode_url("folder", folder=folder.path()))

        if request.var("_remove_tls_registration"):
            remove_tls_registration(
                [
                    (
                        make_automation_config(config.sites[self._host.site_id()]),
                        [self._host.name()],
                    )
                ],
                debug=config.debug,
            )
            return None

        attributes = collect_attributes(
            all_host_attributes(config.wato_host_attrs, config.tags.get_tag_groups_by_topic()),
            "host" if not self._is_cluster() else "cluster",
            new=False,
        )
        host = Host.host(self._host.name())
        if host is None:
            flash(f"Host {self._host.name()} could not be found.")
            return None

        host.edit(
            attributes,
            self._get_cluster_nodes(attributes),
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
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
        if request.var("go_to_folder"):
            return redirect(mode_url("folder", folder=folder.path()))

        return redirect(mode_url("edit_host", folder=folder.path(), host=self._host.name()))

    def _should_use_dns_cache(self, site_configs: SiteConfigurations) -> bool:
        site = self._host.effective_attributes()["site"]
        return watolib_sites.get_effective_global_setting(
            site,
            is_distributed_setup_remote_site(site_configs),
            "use_dns_cache",
        )

    def _vs_host_name(self) -> FixedValue:
        return FixedValue(
            value=self._host.name(),
            title=_("Host name"),
        )


def page_menu_all_hosts_entries(should_use_dns_cache: bool) -> Iterator[PageMenuEntry]:
    if should_use_dns_cache:
        yield PageMenuEntry(
            name=UpdateDnsCacheLoadingContainer.a_tag_id,
            title=_("Update DNS cache"),
            icon_name=StaticIcon(IconNames.update),
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
            icon_name=StaticIcon(IconNames.edit),
            item=make_simple_link(
                folder_preserving_link([("mode", "edit_host"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    if mode_name != "inventory":
        yield PageMenuEntry(
            title=_("Run service discovery"),
            icon_name=StaticIcon(IconNames.services),
            item=make_simple_link(
                folder_preserving_link([("mode", "inventory"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    if mode_name != "diag_host" and not host.is_cluster():
        yield PageMenuEntry(
            title=_("Test connection"),
            icon_name=StaticIcon(IconNames.analysis),
            item=make_simple_link(
                folder_preserving_link([("mode", "diag_host"), (ABCHostMode.VAR_HOST, host.name())])
            ),
        )

    yield PageMenuEntry(
        title=_("Test notifications"),
        icon_name=StaticIcon(IconNames.analysis),
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
            icon_name=StaticIcon(IconNames.rulesets),
            item=make_simple_link(
                folder_preserving_link(
                    [("mode", "object_parameters"), (ABCHostMode.VAR_HOST, host.name())]
                ),
                transition=LoadingTransition.catalog,
            ),
        )

    if mode_name == "object_parameters" or mode_name == "edit_host" and user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Rules"),
            icon_name=StaticIcon(IconNames.rulesets),
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
            icon_name=StaticIcon(IconNames.rulesets),
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
                icon_name=StaticIcon(IconNames.rename_host),
                item=make_simple_link(
                    folder_preserving_link(
                        [("mode", "rename_host"), (ABCHostMode.VAR_HOST, host.name())]
                    )
                ),
            )

        if user.may("wato.manage_hosts") and user.may("wato.clone_hosts"):
            yield PageMenuEntry(
                title=_("Clone"),
                icon_name=StaticIcon(IconNames.insert),
                item=make_simple_link(host.clone_url()),
            )

        if not locked_by_quick_setup:
            yield PageMenuEntry(
                title=_("Delete"),
                icon_name=StaticIcon(IconNames.delete),
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
                icon_name=StaticIcon(IconNames.auditlog),
                item=make_simple_link(make_object_audit_log_url(host.object_ref())),
            )

        if user.may("wato.manage_hosts"):
            yield PageMenuEntry(
                title=_("Remove TLS registration"),
                icon_name=StaticIcon(IconNames.tls, emblem="remove"),
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
    def _host_type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def _verify_host_type(cls, host: Host) -> None:
        raise NotImplementedError()

    def _from_vars(self) -> None:
        if request.var("clone"):
            self._mode = "clone"
        elif request.var("prefill"):
            self._mode = "prefill"
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

        self._clone_source = folder.load_host(HostName(clone_source_name))

        # Used to render the form with the cloned hosts attributes. On form submissions this will
        # be overridden by the action method.
        host = Host(
            folder=folder,
            host_name=self._clone_source.name(),
            attributes=self._clone_source.attributes.copy(),
            cluster_nodes=(
                list(nodes) if (nodes := self._clone_source.cluster_nodes()) is not None else None
            ),
        )

        # remove the quick setup lock from the clone
        if is_locked_by_quick_setup(host.locked_by()):
            host.attributes.pop("locked_by", None)
            host.attributes.pop("locked_attributes", None)

        self._verify_host_type(host)
        return host

    def action(self, config: Config) -> ActionResult:
        if not transactions.transaction_valid():
            return redirect(mode_url("folder"))

        attributes = collect_attributes(
            all_host_attributes(config.wato_host_attrs, config.tags.get_tag_groups_by_topic()),
            self._host_type_name(),
            new=True,
        )
        cluster_nodes = self._get_cluster_nodes(attributes)
        try:
            hostname = strip_hostname_whitespace_chars(
                request.get_ascii_input_mandatory(self.VAR_HOST)
            )
            hostname = HostName(hostname)
        except MKUserError:
            hostname = HostName("")

        Hostname().validate_value(request.get_ascii_input_mandatory(self.VAR_HOST), self.VAR_HOST)

        folder = folder_from_request(request.var("folder"), hostname)
        if transactions.check_transaction():
            folder.create_hosts(
                [(hostname, attributes, cluster_nodes)],
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        self._host = folder.load_host(hostname)
        bakery.try_bake_agents_for_hosts([hostname], debug=config.debug)

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

        if request.var("go_to_folder"):
            return redirect(mode_url("folder", folder=folder.path()))

        return redirect(mode_url("edit_host", folder=folder.path(), host=self._host.name()))

    def _page_form_quick_setup_warning(self) -> None:
        if (
            self._clone_source
            and (locked_by := self._clone_source.locked_by())
            and is_locked_by_quick_setup(locked_by)
        ):
            quick_setup_duplication_warning(locked_by, "host")

    def _vs_host_name(self) -> ValueSpec:
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
            host_name = strip_hostname_whitespace_chars(
                request.get_ascii_input_mandatory(cls.VAR_HOST)
            )
            host_name = HostName(host_name)
        except MKUserError:
            host_name = HostName("")
        if prefill := request.get_ascii_input("prefill"):
            match prefill:
                case "snmp":
                    return Host(
                        folder=folder_from_request(request.var("folder"), host_name),
                        host_name=host_name,
                        attributes=HostAttributes(
                            tag_snmp_ds="snmp-v2",
                            tag_agent="no-agent",
                            snmp_community="",
                        ),
                        cluster_nodes=None,
                    )
                case "relay":
                    return Host(
                        folder=folder_from_request(request.var("folder"), host_name),
                        host_name=host_name,
                        attributes=HostAttributes(
                            relay=request.get_str_input_mandatory("relay"),
                        ),
                        cluster_nodes=None,
                    )
        return Host(
            folder=folder_from_request(request.var("folder"), host_name),
            host_name=host_name,
            attributes={},
            cluster_nodes=None,
        )

    @classmethod
    def _host_type_name(cls) -> str:
        return "host"

    @classmethod
    def _verify_host_type(cls, host: Host) -> None:
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
            host_name = strip_hostname_whitespace_chars(
                request.get_ascii_input_mandatory(cls.VAR_HOST)
            )
            host_name = HostName(host_name)
        except MKUserError:
            host_name = HostName("")
        return Host(
            folder=folder_from_request(request.var("folder"), host_name),
            host_name=host_name,
            attributes={},
            cluster_nodes=[],
        )

    @classmethod
    def _host_type_name(cls) -> str:
        return "cluster"

    @classmethod
    def _verify_host_type(cls, host: Host) -> None:
        if not host.is_cluster():
            raise MKGeneralException(_("Can not clone a regular host as cluster host"))


class PageAjaxPingHost(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        site_id = request.get_validated_type_input(SiteId, "site_id", deflt=omd_site())
        cmd = request.get_validated_type_input(PingHostCmd, "cmd", PingHostCmd.PING)

        if cmd == PingHostCmd.PING6:
            ip_or_dns_name = unquote(request.get_ascii_input_mandatory("ip_or_dns_name"))

            if not HostAddress()._is_valid_ipv6_address(ip_or_dns_name):
                return {
                    "status_code": 99,
                    "message": "Not a valid IPv6 address.",
                }

        else:
            try:
                ip_or_dns_name = request.get_validated_type_input_mandatory(
                    HostName, "ip_or_dns_name"
                )
            except MKUserError as e:
                return {
                    "status_code": 99,
                    "message": str(e),
                }

        result = ping_host(
            automation_config=make_automation_config(ctx.config.sites[site_id]),
            ping_host_input=PingHostInput(
                ip_or_dns_name=unquote(ip_or_dns_name),
                base_cmd=cmd,
            ),
            debug=ctx.config.debug,
        )
        return {
            "status_code": result.return_code,
            "message": result.response,
        }


class PageAjaxDiagCmkAgent(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        api_request = ctx.request.get_request()
        result = diag_cmk_agent(
            automation_config=make_automation_config(ctx.config.sites[api_request["site_id"]]),
            diag_cmk_agent_input=DiagCmkAgentInput(
                host_name=api_request["host_name"],
                ip_address=api_request["ipaddress"],
                address_family=api_request["address_family"],
                agent_port=api_request["agent_port"],
                timeout=api_request["timeout"],
            ),
            debug=ctx.config.debug,
        )

        return {
            "status_code": result.return_code,
            "output": result.response,
        }
