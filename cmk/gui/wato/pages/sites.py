#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for managing sites"""

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import socket
import traceback
from collections.abc import Collection, Iterable, Iterator, Mapping
from copy import deepcopy
from typing import Any, assert_never, cast, overload, override
from urllib.parse import urlparse

from livestatus import (
    BrokerConnection,
    BrokerConnections,
    BrokerSite,
    ConnectionId,
    NetworkSocketDetails,
    SiteConfiguration,
    SiteConfigurations,
    TLSParams,
)

import cmk.gui.sites
import cmk.gui.watolib.audit_log as _audit_log
import cmk.gui.watolib.changes as _changes
import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import FinalizeRequest, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import render_end_tag
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.site_config import (
    distributed_setup_remote_sites,
    has_distributed_setup_remote_sites,
    is_distributed_setup_remote_site,
    is_replication_enabled,
    site_is_local,
)
from cmk.gui.sites import SiteStatus
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.compatibility import make_site_version_info
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeactionuri_contextless,
    makeuri_contextless,
)
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    HTTPUrl,
    ID,
    Integer,
    MonitoredHostname,
    NetworkPort,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.wato.pages._html_elements import wato_html_head
from cmk.gui.wato.pages.global_settings import (
    ABCEditGlobalSettingMode,
    ABCGlobalSettingsMode,
    make_global_settings_context,
)
from cmk.gui.wato.piggyback_hub import CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT
from cmk.gui.watolib.activate_changes import get_free_message
from cmk.gui.watolib.automation_commands import OMDStatus
from cmk.gui.watolib.automations import (
    do_site_login,
    MKAutomationException,
    remote_automation_config_from_site_config,
)
from cmk.gui.watolib.broker_certificates import trigger_remote_certs_creation
from cmk.gui.watolib.broker_connections import BrokerConnectionsConfigFile
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_registry,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainGUI,
    finalize_all_settings_per_site,
)
from cmk.gui.watolib.global_settings import (
    load_configuration_settings,
    load_site_global_settings,
    save_global_settings,
    save_site_global_settings,
    STATIC_PERMISSIONS_GLOBAL_SETTINGS,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_preserving_link,
    folder_tree,
    FolderSiteStats,
    make_action_link,
)
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.piggyback_hub import (
    validate_piggyback_hub_config,
)
from cmk.gui.watolib.site_management import (
    add_changes_after_editing_broker_connection,
    add_changes_after_editing_site_connection,
)
from cmk.gui.watolib.sites import (
    is_livestatus_encrypted,
    ldap_connections_are_configurable,
    PingResult,
    ReplicationStatus,
    ReplicationStatusFetcher,
    site_globals_editable,
    site_management_registry,
    STATIC_PERMISSIONS_SITES,
)
from cmk.messaging import check_remote_connection, ConnectionFailed, ConnectionOK, ConnectionRefused
from cmk.utils.encryption import CertificateDetails, fetch_certificate_details
from cmk.utils.licensing.license_distribution_registry import distribute_license_to_remotes
from cmk.utils.licensing.registry import is_free
from cmk.utils.paths import omd_root


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    page_registry.register(PageEndpoint("wato_ajax_fetch_site_status", PageAjaxFetchSiteStatus()))
    mode_registry.register(ModeEditSite)
    mode_registry.register(ModeEditBrokerConnection)
    mode_registry.register(ModeDistributedMonitoring)
    mode_registry.register(ModeEditSiteGlobals)
    mode_registry.register(ModeEditSiteGlobalSetting)
    mode_registry.register(ModeSiteLivestatusEncryption)


class ModeEditSite(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_site"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_SITES

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeDistributedMonitoring

    @overload
    @classmethod
    def mode_url(cls, *, site: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def __init__(self) -> None:
        super().__init__()
        self._site_mgmt = site_management_registry["site_management"]

        _site_id_return = request.get_ascii_input("site")
        self._site_id = None if _site_id_return is None else SiteId(_site_id_return)
        _clone_id_return = request.get_ascii_input("clone")
        self._clone_id = None if _clone_id_return is None else SiteId(_clone_id_return)
        self._new = self._site_id is None

        if is_free() and (self._new or self._site_id != omd_site()):
            raise MKUserError(None, get_free_message())

        self._configured_sites = self._site_mgmt.load_sites()

        if self._clone_id:
            try:
                self._site = self._configured_sites[self._clone_id]
            except KeyError:
                raise MKUserError(None, _("The requested site does not exist"))

        elif self._new:
            self._site = SiteConfiguration(
                id=SiteId(""),
                alias="",
                url_prefix="",
                disabled=False,
                insecure=False,
                multisiteurl="",
                persist=False,
                proxy={},
                message_broker_port=5672,
                user_sync="all",
                status_host=None,
                replicate_mkps=True,
                replicate_ec=True,
                socket=(
                    "tcp",
                    NetworkSocketDetails(
                        address=("", 6557),
                        tls=(
                            "encrypted",
                            TLSParams(verify=True),
                        ),
                    ),
                ),
                timeout=5,
                disable_wato=True,
                user_login=True,
                replication=None,
                is_trusted=False,
            )

        else:
            assert self._site_id is not None
            try:
                self._site = self._configured_sites[self._site_id]
            except KeyError:
                raise MKUserError(None, _("The requested site does not exist"))

    def title(self) -> str:
        if self._new:
            return _("Add site connection")
        return _("Edit site connection %s") % self._site_id

    def _breadcrumb_url(self) -> str:
        assert self._site_id is not None
        return self.mode_url(site=self._site_id)

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Connection"), breadcrumb, form_name="site", button_name="_save"
        )
        if not self._new and isinstance(self._site_id, str):
            menu.dropdowns.insert(
                1,
                _page_menu_dropdown_site_details(
                    self._site_id, self._site, self._configured_sites, self.name()
                ),
            )
        return menu

    def _site_from_valuespec(self, config: Config) -> SiteConfiguration:
        vs = self._valuespec(config)
        raw_site_spec = vs.from_html_vars("site")
        vs.validate_value(raw_site_spec, "site")

        site_spec = cast(SiteConfiguration, raw_site_spec)
        if self._new:
            self._site_id = site_spec["id"]

        return site_spec

    def save_site_changes(
        self,
        site_spec: SiteConfiguration,
        configured_sites: SiteConfigurations,
        *,
        pprint_value: bool,
        use_git: bool,
    ) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("sites"))

        # Take over all unknown elements from existing site specs, like for
        # example, the replication secret
        if self._site_id is None:
            raise MKUserError(None, _("Site ID must be set"))

        for key, value in configured_sites.get(self._site_id, {}).items():
            # We need to review whether or not we still want to allow setting arbritrary keys
            site_spec.setdefault(key, value)  # type: ignore[misc]

        self._site_mgmt.validate_configuration(self._site_id, site_spec, configured_sites)

        sites_to_update = site_management_registry["site_management"].get_connected_sites_to_update(
            new_or_deleted_connection=self._new,
            modified_site=self._site_id,
            current_config=site_spec,
            old_config=self._site,
            site_configs=configured_sites,
        )

        self._site = configured_sites[self._site_id] = site_spec
        self._site_mgmt.save_sites(
            configured_sites,
            activate=True,
            pprint_value=pprint_value,
        )

        msg = add_changes_after_editing_site_connection(
            site_id=self._site_id,
            is_new_connection=self._new,
            replication_enabled=is_replication_enabled(site_spec),
            is_local_site=site_is_local(site_spec),
            connected_sites=sites_to_update,
            use_git=use_git,
        )

        flash(msg)
        return redirect(mode_url("sites"))

    def action(self, config: Config) -> ActionResult:
        site_spec = self._site_from_valuespec(config)
        return self.save_site_changes(
            site_spec,
            self._configured_sites,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )

    def page(self, config: Config) -> None:
        with html.form_context("site"):
            self._valuespec(config).render_input("site", dict(self._site))

            forms.end()
            html.hidden_fields()

    def _valuespec(self, config: Config) -> Dictionary:
        basic_elements = self._basic_elements(config)
        livestatus_elements = self._livestatus_elements()
        replication_elements = self._replication_elements()

        return Dictionary(
            elements=basic_elements + livestatus_elements + replication_elements,
            headers=[
                (_("Basic settings"), [key for key, _vs in basic_elements]),
                (_("Status connection"), [key for key, _vs in livestatus_elements]),
                (_("Configuration connection"), [key for key, _vs in replication_elements]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[],
        )

    def _basic_elements(self, config: Config) -> list[tuple[str, ValueSpec]]:
        if self._new:
            vs_site_id: TextInput | FixedValue = ID(
                title=_("Site ID"),
                size=60,
                allow_empty=False,
                help=_(
                    "The site ID must be identical (case sensitive) with the instance's exact name."
                ),
                validate=self._validate_site_id,
            )
        else:
            vs_site_id = FixedValue(
                value=self._site_id,
                title=_("Site ID"),
            )

        return [
            ("id", vs_site_id),
            (
                "alias",
                TextInput(
                    title=_("Alias"),
                    size=60,
                    help=_("An alias or description of the site."),
                    allow_empty=False,
                ),
            ),
        ]

    def _validate_site_id(self, value: str, varprefix: str) -> None:
        if value in self._site_mgmt.load_sites():
            raise MKUserError("id", _("This ID is already being used by another connection."))

        # Checkmk creates NagVis backends for all sites: For each site it creates two backends:
        # a) [site_id]    - Livestatus connection to the sites core
        # b) [site_id]_bi - Bacned to Checkmk BI for displaying aggregation states
        #
        # In case one tries to add a site with a Site-ID "[central_site]_bi" this will result
        # in a name conflict between the central site BI backend and the remote site livestatus
        # backend. See CMK-6968.
        if value == "%s_bi" % omd_site():
            raise MKUserError(
                varprefix,
                _(
                    "You cannot connect remote sites named <tt>[central_site]_bi</tt>. You will "
                    "have to rename your remote site to be able to connect it with this site."
                ),
            )

    def _livestatus_elements(self) -> list[tuple[str, ValueSpec]]:
        proxy_docu_url = "https://checkmk.com/checkmk_multisite_modproxy.html"
        status_host_docu_url = "https://checkmk.com/checkmk_multisite_statushost.html"
        site_choices = [
            (sk, si.get("alias", sk)) for (sk, si) in self._site_mgmt.load_sites().items()
        ]

        return [
            ("socket", self._site_mgmt.connection_method_valuespec()),
            ("proxy", self._site_mgmt.livestatus_proxy_valuespec()),
            (
                "timeout",
                Integer(
                    title=_("Connect timeout"),
                    size=2,
                    unit=_("Seconds"),
                    minvalue=0,
                    help=_(
                        "This sets the time that the GUI waits for a connection "
                        "to the site to be established before the site is "
                        "considered to be unreachable. It is highly recommended to set a value "
                        "as low as possible here because this setting directly affects the GUI "
                        "response time when the destination is not reachable. When using the "
                        "Livestatus proxy daemon the GUI connects to the local proxy, in this "
                        "situation a lower value, like 2 seconds is recommended."
                    ),
                ),
            ),
            (
                "persist",
                Checkbox(
                    title=_("Persistent connection"),
                    label=_("Use persistent connections"),
                    help=_(
                        "If you enable persistent connections then the GUI will try to keep open "
                        "the connection to the remote sites. This brings a great speed up in high-latency "
                        "situations but locks a number of threads in the Livestatus module of the target site."
                    ),
                ),
            ),
            (
                "url_prefix",
                TextInput(
                    title=_("URL prefix"),
                    size=60,
                    help=_(
                        "The URL prefix will be prepended to links of add-ons like NagVis "
                        "when a link to such applications points to a host or "
                        "service on that site. You can either use an absolute URL prefix like <tt>http://some.host/mysite/</tt> "
                        "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you need a mod_proxy "
                        "configuration in your local system Apache that proxies such URLs to the according remote site. "
                        "Please refer to the <a target=_blank href='%s'>User Guide</a> for details. "
                        "The prefix should end with a slash. Omit the <tt>/nagvis/</tt> from the prefix."
                    )
                    % proxy_docu_url,
                    allow_empty=True,
                ),
            ),
            (
                "status_host",
                Alternative(
                    title=_("Status host"),
                    elements=[
                        FixedValue(value=None, title=_("No status host"), totext=""),
                        Tuple(
                            title=_("Use the following status host"),
                            orientation="horizontal",
                            elements=[
                                DropdownChoice(
                                    title=_("Site:"),
                                    choices=site_choices,
                                    sorted=True,
                                ),
                                self._vs_host(),
                            ],
                        ),
                    ],
                    help=_(
                        "By specifying a status host for each non-local connection "
                        "you prevent graphical user interface (GUI) from running into timeouts when remote sites do not respond. "
                        "You need to add the remote monitoring servers as hosts into your local monitoring "
                        "site and use their host state as a reachability state of the remote site. Please "
                        "refer to the <a target=_blank href='%s'>online documentation</a> for details."
                    )
                    % status_host_docu_url,
                ),
            ),
            (
                "disabled",
                Checkbox(
                    title=_("Disable in status GUI"),
                    label=_("Temporarily disable this connection"),
                    help=_(
                        "If you disable a connection, then no data of this site will be shown in the status GUI. "
                        "The replication is not affected by this, however."
                    ),
                ),
            ),
        ]

    def _vs_host(self) -> MonitoredHostname:
        return MonitoredHostname(title=_("Host:"))

    def _replication_elements(self) -> list[tuple[str, ValueSpec]]:
        elements: list[tuple[str, ValueSpec]] = [
            (
                "replication",
                DropdownChoice(
                    title=_("Enable replication"),
                    choices=[
                        (None, _("No replication with this site")),
                        ("slave", _("Push configuration to this site")),
                    ],
                    help=_(
                        "Replication allows you to manage several monitoring sites with a "
                        "logically centralized setup. Remote sites receive their configuration "
                        "from the central sites. <br><br>Note: Remote sites "
                        "do not need any replication configuration. They will be remote-controlled "
                        "by the central sites."
                    ),
                ),
            ),
            (
                "message_broker_port",
                NetworkPort(title=_("Message broker port"), default_value=5672),
            ),
            (
                "multisiteurl",
                HTTPUrl(
                    title=_("URL of remote site"),
                    help=_(
                        "URL of the remote Checkmk including <tt>/check_mk/</tt>. "
                        "This URL is in many cases the same as the URL-Prefix but with <tt>check_mk/</tt> "
                        "appended, but it must always be an absolute URL. Please note, that "
                        "that URL will be fetched by the Apache server of the local "
                        "site itself, whilst the URL-Prefix is used by your local Browser."
                    ),
                    allow_empty=True,
                ),
            ),
            (
                "disable_wato",
                Checkbox(
                    title=_("Disable remote configuration"),
                    label=_("Disable configuration via Setup on this site"),
                    help=_(
                        "It is recommended to disable access to Setup completely on the remote site. "
                        "Otherwise a user who does not know about the replication could make local "
                        "changes that are overridden at the next configuration activation."
                    ),
                ),
            ),
            (
                "insecure",
                Checkbox(
                    title=_("Ignore TLS errors"),
                    label=_("Ignore SSL certificate errors"),
                    help=_(
                        "This might be needed to make the synchronization accept problems with "
                        "SSL certificates when using an SSL secured connection."
                    ),
                ),
            ),
            (
                "user_login",
                Checkbox(
                    title=_("Direct login to web GUI allowed"),
                    label=_("Users are allowed to directly log in into the web GUI of this site"),
                    help=_(
                        "When enabled, this site is marked for synchronization every time a web GUI "
                        "related option is changed and users are allowed to log in "
                        "to the web GUI of this site. "
                        "The access to the Rest API is unaffected by this option though."
                    ),
                ),
            ),
            (
                "is_trusted",
                Checkbox(
                    title=_("Trust this site completely"),
                    label=_("Trust this site completely"),
                    help=_(
                        "When this option is enabled the central site might get compromised by a rogue remote site. "
                        "If you disable this option, some features, such as HTML rendering in service descriptions for the services monitored on this remote site, will no longer work. "
                        "In case the sites are managed by different groups of people, especially when belonging to different organizations, we recommend to disable this setting."
                    ),
                ),
            ),
        ]

        if ldap_connections_are_configurable():
            elements.append(
                ("user_sync", self._site_mgmt.user_sync_valuespec(self._site_id, self._site))
            )

        elements.extend(
            [
                (
                    "replicate_ec",
                    Checkbox(
                        title=_("Replicate Event Console config"),
                        label=_("Replicate Event Console configuration to this site"),
                        help=_(
                            "This option enables the distribution of global settings and rules of the Event Console "
                            "to the remote site. Any change in the local Event Console settings will mark the site "
                            "as <i>need sync</i>. A synchronization will automatically reload the Event Console of "
                            "the remote site."
                        ),
                    ),
                ),
                (
                    "replicate_mkps",
                    Checkbox(
                        title=_("Replicate extensions"),
                        label=_("Replicate extensions (MKPs and files in <tt>~/local/</tt>)"),
                        help=_(
                            "If you enable the replication of MKPs then during each <i>Activate Changes</i> MKPs "
                            "that are installed on your central site and all other files below the <tt>~/local/</tt> "
                            "directory will be also transferred to the remote site. Note: <b>all other MKPs and files "
                            "below <tt>~/local/</tt> on the remote site will be removed</b>."
                        ),
                    ),
                ),
            ]
        )
        return elements


class ModeEditBrokerConnection(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_broker_connection"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_SITES

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeDistributedMonitoring

    @overload
    @classmethod
    def mode_url(cls, *, site: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    @property
    def _is_new(self) -> bool:
        return self._edit_id is None

    def __init__(self) -> None:
        super().__init__()
        self._site_mgmt = site_management_registry["site_management"]

        self._connection: BrokerConnection | None = None

        self._edit_id: ConnectionId | None = (
            ConnectionId(connection_id)
            if (connection_id := request.get_ascii_input("edit_connection_id"))
            else None
        )

        self._clone_id: ConnectionId | None = (
            ConnectionId(connection_id)
            if (connection_id := request.get_ascii_input("clone_connection_id"))
            else None
        )

        self._connections: BrokerConnections = BrokerConnectionsConfigFile().load_for_reading()

        for el_id in [self._edit_id, self._clone_id]:
            if not el_id:
                continue
            try:
                self._connection = self._connections[el_id]
            except IndexError:
                raise MKUserError(None, _("The requested connection %s does not exist") % el_id)

    def title(self) -> str:
        if self._is_new:
            return _("Add message broker connection")
        return _("Edit message broker connection %s") % self._edit_id

    def _breadcrumb_url(self) -> str:
        assert self._edit_id is not None
        return self.mode_url(site=self._edit_id)

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Connection"), breadcrumb, form_name="broker_connection", button_name="_save"
        )
        return menu

    def _validate_connection_id(self, connection_id: str, varprefix: str | None) -> None:
        if self._site_mgmt.broker_connection_id_exists(connection_id):
            raise MKUserError(
                None,
                _("Connection ID %s already exists.") % connection_id,
            )

    def action(self, config: Config) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("sites"))

        vs = self._valuespec(config)
        raw_site_spec = vs.from_html_vars("broker_connection")
        vs.validate_value(raw_site_spec, "broker_connection")

        try:
            source_site, dest_site = (
                SiteId(raw_site_spec["connecter"]),
                SiteId(raw_site_spec["connectee"]),
            )
        except KeyError:
            raise MKUserError(
                None, _("The sites initiating and accepting the connection must be specified.")
            )

        connection = BrokerConnection(
            connecter=BrokerSite(site_id=source_site),
            connectee=BrokerSite(site_id=dest_site),
        )

        self._site_mgmt.validate_and_save_broker_connection(
            raw_site_spec["unique_id"],
            connection,
            is_new=self._is_new,
            pprint_value=config.wato_pprint_config,
        )
        msg = add_changes_after_editing_broker_connection(
            connection_id=raw_site_spec["unique_id"],
            is_new_broker_connection=self._is_new,
            sites=[source_site, dest_site],
            use_git=config.wato_use_git,
        )

        flash(msg)
        return redirect(mode_url("sites"))

    def page(self, config: Config) -> None:
        with html.form_context("broker_connection"):
            connection_vs = (
                {
                    "unique_id": self._edit_id if self._edit_id else "",
                    "connecter": self._connection.connecter.site_id,
                    "connectee": self._connection.connectee.site_id,
                }
                if self._connection
                else {}
            )

            self._valuespec(config).render_input("broker_connection", connection_vs)
            forms.end()
            html.hidden_fields()

    def _valuespec(self, config: Config) -> Dictionary:
        basic_elements = self._basic_elements(config)

        return Dictionary(
            elements=basic_elements,
            headers=[
                (_("Connection"), [key for key, _vs in basic_elements]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[],
            help=_(
                "You can define pairs of sites here that will be able to directly "
                "communicate, without routing the messages via the central site. "
                "Messages themselves will be sent in both directions: from the "
                "connecter to the connectee and vice versa. "
                "Note that the order in which you choose the sites here still might matter, "
                "depending on your network restrictions: "
                "The initiating peer must be able to establish a TCP connection to the accepting "
                "peer."
            ),
        )

    def _basic_elements(self, config: Config) -> list[tuple[str, ValueSpec]]:
        replicated_sites_choices = [
            (sk, si.get("alias", sk))
            for sk, si in distributed_setup_remote_sites(config.sites).items()
        ]

        return [
            (
                (
                    "unique_id",
                    FixedValue(
                        value=self._edit_id,
                        title=_("Unique ID"),
                    ),
                )
                if self._edit_id
                else (
                    "unique_id",
                    ID(
                        title=_("Unique ID"),
                        size=60,
                        allow_empty=False,
                        validate=self._validate_connection_id,
                    ),
                )
            ),
            (
                "connecter",
                DropdownChoice(
                    title=_("Initiating peer"),
                    choices=replicated_sites_choices,
                    sorted=True,
                    help=_("Select the site that is establishing the TCP connection."),
                ),
            ),
            (
                "connectee",
                DropdownChoice(
                    title=_("Accepting peer"),
                    choices=replicated_sites_choices,
                    sorted=True,
                    help=_("Select the site that is accepting the TCP connection."),
                ),
            ),
        ]


class ModeDistributedMonitoring(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "sites"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_SITES

    def __init__(self) -> None:
        super().__init__()
        self._site_mgmt = site_management_registry["site_management"]

    def title(self) -> str:
        return _("Distributed monitoring")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        page_menu: PageMenu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="connections",
                    title=_("Connections"),
                    topics=[
                        PageMenuTopic(
                            title=_("Connections"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add connection"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        makeuri_contextless(request, [("mode", "edit_site")]),
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Add peer-to-peer message broker connection"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request, [("mode", "edit_broker_connection")]
                                        ),
                                    ),
                                    is_shortcut=False,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )
        page_menu.add_doc_reference(title=self.title(), doc_ref=DocReference.DISTRIBUTED_MONITORING)
        return page_menu

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        delete_id = request.get_ascii_input("_delete")
        if delete_id and transactions.check_transaction():
            return self._action_delete(
                SiteId(delete_id),
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        delete_folders_id = request.get_ascii_input("_delete_folders")
        if delete_folders_id and transactions.check_transaction():
            return self._action_delete_folders(
                SiteId(delete_folders_id), use_git=config.wato_use_git
            )

        delete_connection_id = request.get_ascii_input("_delete_connection_id")
        if delete_connection_id and transactions.check_transaction():
            return self._action_delete_broker_connection(
                ConnectionId(delete_connection_id),
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        logout_id = request.get_ascii_input("_logout")
        if logout_id:
            return self._action_logout(
                SiteId(logout_id),
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        login_id = request.get_ascii_input("_login")
        if login_id:
            return self._action_login(
                SiteId(login_id),
                debug=config.debug,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        if trigger_certs_site_id := request.get_ascii_input("_trigger_certs_creation"):
            return self._action_trigger_certs(SiteId(trigger_certs_site_id), debug=config.debug)

        return None

    def _action_trigger_certs(self, trigger_certs_site_id: SiteId, *, debug: bool) -> ActionResult:
        configured_sites = self._site_mgmt.load_sites()
        site = configured_sites[trigger_certs_site_id]
        trigger_remote_certs_creation(trigger_certs_site_id, site, force=True, debug=debug)
        flash(_("Remote broker certificates created for site %s.") % trigger_certs_site_id)
        return redirect(mode_url("sites"))

    def _action_delete(
        self, delete_id: SiteId, *, pprint_value: bool, use_git: bool
    ) -> ActionResult:
        # TODO: Can we delete this ancient code? The site attribute is always available
        # these days and the following code does not seem to have any effect.
        configured_sites = self._site_mgmt.load_sites()
        # The last connection can always be deleted. In that case we
        # fall back to non-distributed-Setup and the site attribute
        # will be removed.
        test_sites = dict(configured_sites.items())
        del test_sites[delete_id]

        # Prevent deletion of the local site. This does not make sense, even on
        # standalone sites or distributed remote sites.
        if delete_id == omd_site():
            raise MKUserError(None, _("You cannot delete the connection to the local site."))

        # Make sure that site is not being used by hosts and folders
        folder_site_stats = FolderSiteStats.build(folder_tree().root_folder())

        if delete_id in folder_site_stats.hosts.keys():
            search_url = makeactionuri_contextless(
                request,
                transactions,
                [
                    ("host_search_change_site", "on"),
                    ("host_search_site", DropdownChoice.option_id(delete_id)),
                    ("host_search", "1"),
                    ("folder", ""),
                    ("mode", "search"),
                    ("filled_in", "edit_host"),
                ],
            )
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It still has hosts related to the site "
                    'assigned to it. You can use the <a href="%s">host '
                    "search</a> to get a list of the hosts."
                )
                % search_url,
            )

        folders_related_to_site = folder_site_stats.folders.get(delete_id, set())
        empty_folders = {folder for folder in folders_related_to_site if folder.is_empty()}
        non_empty_folders = folders_related_to_site - empty_folders

        if non_empty_folders:
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It still has non-empty "
                    "folders/hosts assigned to it: %s"
                    "You need to first navigate to each folder and move/remove the nested "
                    "folders/hosts."
                )
                % self._build_urls_for_folders(non_empty_folders),
            )

        if empty_folders:
            delete_folders_url = makeactionuri_contextless(
                request, transactions, [("_delete_folders", delete_id), ("mode", "sites")]
            )
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It still has empty folders assigned "
                    "to it: %s"
                    'If you want us to remove these automatically, click <a href="%s">delete</a>.'
                )
                % (self._build_urls_for_folders(empty_folders), delete_folders_url),
            )

        self._site_mgmt.delete_site(
            delete_id,
            pprint_value=pprint_value,
            use_git=use_git,
        )
        return redirect(mode_url("sites"))

    def _action_delete_folders(self, delete_id: SiteId, *, use_git: bool) -> ActionResult:
        folder_site_stats = FolderSiteStats.build(folder_tree().root_folder())
        folders_related_to_site = folder_site_stats.folders.get(delete_id, set())
        empty_folders = {folder for folder in folders_related_to_site if folder.is_empty()}

        if not empty_folders:
            raise MKUserError(None, _("No empty folders for %s available to delete.") % delete_id)

        for empty_folder in empty_folders:
            if (parent := empty_folder.parent()) is not None:
                parent.delete_subfolder(empty_folder.name(), use_git=use_git)

        return redirect(mode_url("sites"))

    def _action_delete_broker_connection(
        self, delete_connection_id: ConnectionId, *, pprint_value: bool, use_git: bool
    ) -> ActionResult:
        source_site, dest_site = self._site_mgmt.delete_broker_connection(
            delete_connection_id, pprint_value=pprint_value
        )
        add_changes_after_editing_broker_connection(
            connection_id=delete_connection_id,
            is_new_broker_connection=False,
            sites=[source_site, dest_site],
            use_git=use_git,
        )
        return redirect(mode_url("sites"))

    def _action_logout(
        self, logout_id: SiteId, *, pprint_value: bool, use_git: bool
    ) -> ActionResult:
        configured_sites = self._site_mgmt.load_sites()
        site = configured_sites[logout_id]
        if "secret" in site:
            del site["secret"]
        self._site_mgmt.save_sites(
            configured_sites,
            activate=True,
            pprint_value=pprint_value,
        )
        _changes.add_change(
            action_name="edit-site",
            text=_("Logged out of remote site %s") % HTMLWriter.render_tt(site["alias"]),
            user_id=user.id,
            domains=[ConfigDomainGUI()],
            sites=[omd_site()],
            use_git=use_git,
        )
        flash(_("Logged out."))
        return redirect(mode_url("sites"))

    def _action_login(
        self, login_id: SiteId, *, debug: bool, pprint_value: bool, use_git: bool
    ) -> ActionResult:
        configured_sites = self._site_mgmt.load_sites()
        if request.get_ascii_input("_cancel"):
            return redirect(mode_url("sites"))

        if not transactions.check_transaction():
            return None

        site = configured_sites[login_id]
        error = None
        # Fetch name/password of admin account
        if request.has_var("_name"):
            name = request.get_validated_type_input_mandatory(UserId, "_name")
            passwd = request.get_ascii_input_mandatory("_passwd", "").strip()
            try:
                if not html.get_checkbox("_confirm"):
                    raise MKUserError(
                        "_confirm",
                        _(
                            "You need to confirm that you want to "
                            "overwrite the remote site configuration."
                        ),
                    )

                secret = do_site_login(site, name, passwd, debug=debug)

                site["secret"] = secret
                self._site_mgmt.save_sites(
                    configured_sites,
                    activate=True,
                    pprint_value=pprint_value,
                )
                message = _("Successfully logged into remote site %s.") % HTMLWriter.render_tt(
                    site["alias"]
                )
                trigger_remote_certs_creation(login_id, site, force=False, debug=debug)
                distribute_license_to_remotes(
                    logger,
                    remote_automation_configs=[remote_automation_config_from_site_config(site)],
                )

                _audit_log.log_audit(
                    action="edit-site",
                    message=message,
                    user_id=user.id,
                    use_git=use_git,
                )
                flash(message)
                return redirect(mode_url("sites"))

            except MKAutomationException as e:
                error = _("Cannot connect to remote site: %s") % e

            except MKUserError as e:
                user_errors.add(e)
                error = str(e)

            except Exception as e:
                logger.exception("error logging in")
                if debug:
                    raise
                error = (_("Internal error: %s\n%s") % (e, traceback.format_exc())).replace(
                    "\n", "\n<br>"
                )
                user_errors.add(MKUserError("_name", error))

        wato_html_head(
            title=_('Login into site "%s"') % site["alias"], breadcrumb=self.breadcrumb()
        )
        if error:
            html.show_error(error)

        html.p(
            _(
                "One manual login as administrator to the Multisite GUI of the remote site"
                ' "%s" is required to initialize the connection.'
                " The credentials will only be used for the initial handshake and not be stored."
                " If the login is successful then both sides will exchange a login secret"
                " which will be used for subsequent remote calls."
            )
            % HTMLWriter.render_tt(site["alias"])
        )

        with html.form_context("login", method="POST"):
            forms.header(_("Login credentials"))
            forms.section(_("Administrator name"))
            html.text_input("_name")
            html.set_focus("_name")
            forms.section(_("Administrator password"))
            html.password_input("_passwd")
            forms.section(_("Confirm overwrite"))
            html.checkbox(
                "_confirm", False, label=_("Confirm overwrite of the remote site configuration")
            )
            forms.end()
            html.button("_do_login", _("Login"))
            html.button("_cancel", _("Cancel"))
            html.hidden_field("_login", login_id)
            html.hidden_fields()
        html.footer()
        return FinalizeRequest(code=200)

    def page(self, config: Config) -> None:
        sites = sort_sites(site_configs := self._site_mgmt.load_sites())

        if is_free():
            html.show_message(get_free_message(format_html=True))

        html.div("", id_="message_container")
        with table_element(
            "sites",
            _("Connections"),
            empty_text=_(
                "You have not configured any local or remote sites. The graphical user interface (GUI) will "
                "implicitly add the data of the local monitoring site. If you add remote "
                "sites, please do not forget to add your local monitoring site also, if "
                "you want to display its data."
            ),
        ) as table:
            for site_id, site in sites:
                table.row()

                self._show_buttons(table, site_id, site, site_configs)
                self._show_basic_settings(table, site_id, site, config)
                self._show_status_connection_config(table, site_id, site)
                self._show_status_connection_status(table, site_id, site)
                self._show_config_connection_config(table, site_id, site)
                self._show_config_connection_status(table, site_id, site)
                self._show_message_broker_connection(table, site_id, site)

        # Message broker connections table
        connections = self._site_mgmt.get_broker_connections()
        if connections:
            with table_element(
                "brokers_connections",
                _("Peer-to-peer message broker connections"),
                empty_text=_("You have not configured any peer-to-peer connections."),
            ) as table:
                for conn_id, connection in connections.items():
                    table.row()

                    self._show_buttons_connection(table, conn_id)
                    self._show_basic_settings_connection(table, conn_id, connection)

        html.javascript("cmk.sites.fetch_site_status();")

    def _build_url_for_folder(self, folder: Folder) -> str:
        url = makeuri_contextless(request, [("folder", folder.path()), ("mode", "folder")])
        return f"<a href='{url}'>{folder.path()}</a>"

    def _build_urls_for_folders(self, folders: Iterable[Folder]) -> str:
        items = "".join(f"<li>{self._build_url_for_folder(folder)}</li>" for folder in folders)
        return f"<ul>{items}</ul>"

    def _show_buttons_connection(self, table: Table, connection_id: str) -> None:
        table.cell(_("Actions"), css=["buttons"])
        edit_url = folder_preserving_link(
            [("mode", "edit_broker_connection"), ("edit_connection_id", connection_id)]
        )
        html.icon_button(edit_url, _("Properties"), StaticIcon(IconNames.edit))

        clone_url = folder_preserving_link(
            [("mode", "edit_broker_connection"), ("clone_connection_id", connection_id)]
        )
        html.icon_button(
            clone_url,
            _("Clone this connection in order to create a new one"),
            StaticIcon(IconNames.clone),
        )

        delete_url = make_confirm_delete_link(
            url=makeactionuri(request, transactions, [("_delete_connection_id", connection_id)]),
            title=_("Delete peer-to-peer connection to site"),
            message=_("ID: %s") % connection_id,
        )
        html.icon_button(delete_url, _("Delete"), StaticIcon(IconNames.delete))

    def _show_buttons(
        self,
        table: Table,
        site_id: SiteId,
        site: SiteConfiguration,
        site_configs: SiteConfigurations,
    ) -> None:
        table.cell(_("Actions"), css=["buttons"])
        edit_url = folder_preserving_link([("mode", "edit_site"), ("site", site_id)])
        html.icon_button(edit_url, _("Properties"), StaticIcon(IconNames.edit))

        clone_url = folder_preserving_link([("mode", "edit_site"), ("clone", site_id)])
        html.icon_button(
            clone_url,
            _("Clone this connection in order to create a new one"),
            StaticIcon(IconNames.clone),
        )

        # Prevent deletion of the local site. This does not make sense, even on
        # standalone sites or distributed remote sites.
        if site_id == omd_site():
            html.empty_icon_button()
        else:
            delete_url = make_confirm_delete_link(
                url=makeactionuri(request, transactions, [("_delete", site_id)]),
                title=_("Delete connection to site"),
                suffix=site.get("alias", ""),
                message=_("ID: %s") % site_id,
            )
            html.icon_button(delete_url, _("Delete"), StaticIcon(IconNames.delete))

        if site_globals_editable(site_configs, site):
            globals_url = folder_preserving_link([("mode", "edit_site_globals"), ("site", site_id)])

            has_site_globals = bool(site.get("globals"))
            title = _("Site specific global configuration")
            if has_site_globals:
                icon = StaticIcon(IconNames.site_globals_modified)
                title += " (%s)" % (_("%d specific settings") % len(site.get("globals", {})))
            else:
                icon = StaticIcon(IconNames.site_globals)

            html.icon_button(globals_url, title, icon)

    def _show_basic_settings_connection(
        self, table: Table, connection_id: str, connection: BrokerConnection
    ) -> None:
        table.cell(_("ID"), connection_id)
        table.cell(_("Initiating peer"), connection.connecter.site_id)
        table.cell(_("Accepting peer"), connection.connectee.site_id)

    def _show_basic_settings(
        self, table: Table, site_id: SiteId, site: SiteConfiguration, config: Config
    ) -> None:
        table.cell(_("ID"), site_id)
        table.cell(_("Alias"), site.get("alias", ""))

    def _show_status_connection_config(
        self, table: Table, site_id: SiteId, site: SiteConfiguration
    ) -> None:
        table.cell(_("Status connection"))
        vs_connection = self._site_mgmt.connection_method_valuespec()
        html.write_text_permissive(vs_connection.value_to_html(site["socket"]))

    def _show_status_connection_status(
        self, table: Table, site_id: SiteId, site: SiteConfiguration
    ) -> None:
        table.cell("")

        encrypted_url = folder_preserving_link(
            [("mode", "site_livestatus_encryption"), ("site", site_id)]
        )
        html.icon_button(
            encrypted_url,
            _("Show details about Livestatus encryption"),
            StaticIcon(IconNames.encrypted),
        )

        # The status is fetched asynchronously for all sites. Show a temporary loading icon.
        html.open_div(id_="livestatus_status_%s" % site_id, class_="connection_status")
        html.static_icon(
            StaticIcon(IconNames.reload),
            title=_("Fetching Livestatus status"),
            css_classes=["reloading", "replication_status_loading"],
        )
        html.close_div()

    def _show_config_connection_config(
        self, table: Table, site_id: SiteId, site: SiteConfiguration
    ) -> None:
        table.cell(_("Configuration connection"))
        if not is_replication_enabled(site):
            html.write_text_permissive(_("Not enabled"))
            return

        html.write_text_permissive(_("Enabled"))
        parts = []
        if site.get("replicate_ec"):
            parts.append("EC")
        if site.get("replicate_mkps"):
            parts.append("MKPs")
        if parts:
            html.write_text_permissive(" (%s)" % ", ".join(parts))

    def _show_config_connection_status(
        self, table: Table, site_id: SiteId, site: SiteConfiguration
    ) -> None:
        table.cell("")

        if is_replication_enabled(site):
            if site.get("secret"):
                logout_url = make_confirm_delete_link(
                    url=make_action_link([("mode", "sites"), ("_logout", site_id)]),
                    title=_("Log out of site"),
                    suffix=site["alias"],
                    message=_("ID: %s") % site_id,
                    confirm_button=_("Log out"),
                )
                html.icon_button(logout_url, _("Logout"), StaticIcon(IconNames.autherr))
            else:
                login_url = make_action_link([("mode", "sites"), ("_login", site_id)])
                html.icon_button(login_url, _("Login"), StaticIcon(IconNames.authok))

        html.open_div(id_="replication_status_%s" % site_id, class_="connection_status")
        if is_replication_enabled(site):
            # The status is fetched asynchronously for all sites. Show a temporary loading icon.
            html.static_icon(
                StaticIcon(IconNames.reload),
                title=_("Fetching replication status"),
                css_classes=["reloading", "replication_status_loading"],
            )
        html.close_div()

    def _show_message_broker_connection(
        self, table: Table, site_id: SiteId, site: SiteConfiguration
    ) -> None:
        table.cell("Remote message broker")
        if is_replication_enabled(site):
            trigger_url = make_action_link(
                [("mode", "sites"), ("_trigger_certs_creation", site_id)]
            )
            html.open_ts_container(
                container="div",
                function_name="lock_and_redirect",
                arguments={"redirect_url": trigger_url},
            )
            html.icon_button(
                url="javascript:void(0)",
                title=_("Recreate certificates"),
                icon=StaticIcon(IconNames.recreate_broker_certificate),
                class_=["lockable"],
            )
            html.write_text_permissive(_("Recreate certificates"))
            html.write_html(render_end_tag("div"))

        html.open_div(id_=f"message_broker_status_{site_id}", class_="connection_status")
        if is_replication_enabled(site):
            # The status is fetched asynchronously for all sites. Show a temporary loading icon.
            html.static_icon(
                StaticIcon(IconNames.reload),
                title=_("Fetching message broker status"),
                css_classes=["reloading", "replication_status_loading"],
            )
        html.close_div()


class PageAjaxFetchSiteStatus(AjaxPage):
    """AJAX handler for asynchronous fetching of the site status"""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("wato.sites")

        site_states = {}

        sites = site_management_registry["site_management"].load_sites()

        replication_sites = []
        remote_status: dict[SiteId, ReplicationStatus] = {}
        for site_id, site_config in sites.items():
            if not is_replication_enabled(site_config):
                continue
            try:
                replication_sites.append(
                    (site_id, remote_automation_config_from_site_config(site_config))
                )
            except MKGeneralException as e:
                remote_status[site_id] = ReplicationStatus(
                    site_id=site_id, success=False, response=e
                )

        remote_status.update(
            ReplicationStatusFetcher().fetch(replication_sites, debug=ctx.config.debug)
        )

        for site_id, site in sites.items():
            site_id_str: str = site_id

            site_states[site_id_str] = {
                "livestatus": self._render_status_connection_status(site_id, site),
                "replication": self._render_configuration_connection_status(
                    site_id, site, remote_status
                ),
                "message_broker": self._render_message_broker_status(site_id, site, remote_status),
            }

        return site_states

    def _render_configuration_connection_status(
        self,
        site_id: SiteId,
        site: SiteConfiguration,
        replication_status: Mapping[SiteId, ReplicationStatus],
    ) -> str | HTML:
        """Check whether or not the replication connection is possible.

        This deals with these situations:
        - No connection possible
        - connection possible but site down
        - Not logged in
        - And of course: Everything is fine
        """
        if not is_replication_enabled(site):
            return ""

        status = replication_status[site_id]
        if status.success:
            assert not isinstance(status.response, Exception)
            icon = StaticIcon(IconNames.checkmark)
            msg = _("Online (%s)") % make_site_version_info(
                status.response.version,
                status.response.edition,
                status.response.license_state,
            )
        else:
            assert isinstance(status.response, Exception)
            icon = StaticIcon(IconNames.cross)
            msg = "%s" % status.response

        return html.render_static_icon(icon, title=msg) + HTMLWriter.render_span(
            msg, style="vertical-align:middle"
        )

    def _render_status_connection_status(self, site_id: SiteId, site: SiteConfiguration) -> HTML:
        site_status: SiteStatus = cmk.gui.sites.states().get(site_id, SiteStatus({}))
        if site.get("disabled", False) is True:
            status = status_msg = "disabled"
        else:
            status = status_msg = site_status.get("state", "unknown")

        if "exception" in site_status:
            message = "%s" % site_status["exception"]
        else:
            message = status_msg.title()

        icon = StaticIcon(IconNames.checkmark if status == "online" else IconNames.cross)
        return html.render_static_icon(icon, title=message) + HTMLWriter.render_span(
            message, style="vertical-align:middle"
        )

    def _render_message_broker_status(
        self,
        site_id: SiteId,
        site: SiteConfiguration,
        remote_omd_status: Mapping[SiteId, ReplicationStatus],
    ) -> str | HTML:
        if not is_replication_enabled(site) or not isinstance(
            ping_response := remote_omd_status[site_id].response, PingResult
        ):
            return ""

        icon, message = self._get_connection_status_icon_message(
            site_id, site, ping_response.omd_status
        )
        return html.render_static_icon(icon, title=message) + HTMLWriter.render_span(
            message, style="vertical-align:middle"
        )

    def _get_connection_status_icon_message(
        self,
        remote_site_id: SiteId,
        site: SiteConfiguration,
        remote_omd_status: OMDStatus,
    ) -> tuple[StaticIcon, str]:
        if (remote_host := urlparse(site["multisiteurl"]).hostname) is None:
            return StaticIcon(IconNames.cross), _(
                "Offline: No valid URL for graphical user interface (GUI) configured"
            )

        if remote_omd_status["rabbitmq"] == 5:
            return StaticIcon(IconNames.disabled), _("Disabled")

        remote_port = site["message_broker_port"]
        try:
            connection_status = check_remote_connection(
                omd_root, remote_host, remote_port, remote_site_id
            )
        except (MKTerminate, MKTimeout):
            raise
        except Exception as e:
            return StaticIcon(IconNames.alert), _("Unknown error: %s") % (e,)

        match connection_status:
            case ConnectionOK():
                return StaticIcon(IconNames.checkmark), _("Online")
            case ConnectionFailed(error):
                return StaticIcon(IconNames.cross), _("Failed to establish connection: %s") % (
                    error,
                )
            case ConnectionRefused.WRONG_SITE:
                return StaticIcon(IconNames.cross), _(
                    "Connection to port %s refused. You are probably connecting to the wrong site."
                ) % (remote_port,)
            case ConnectionRefused.SELF_SIGNED:
                return StaticIcon(IconNames.cross), _(
                    "Connection to port %s refused. The site is using a self-signed certificate. Are you logged in?"
                ) % (remote_port,)
            case ConnectionRefused.CERTIFICATE_VERIFY_FAILED:
                return StaticIcon(IconNames.cross), _(
                    "Connection to port %s refused: Invalid certificate"
                )
            case ConnectionRefused.CLOSED:
                return StaticIcon(IconNames.cross), _("Not available")

                return "cross", _("Connection to port %s refused") % (remote_port,)
            case _:
                assert_never(_)


class ModeEditSiteGlobals(ABCGlobalSettingsMode):
    @classmethod
    def name(cls) -> str:
        return "edit_site_globals"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_SITES

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditSite

    @overload
    @classmethod
    def mode_url(cls, *, site: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def __init__(self) -> None:
        super().__init__()
        self._site_id = SiteId(request.get_ascii_input_mandatory("site"))
        self._site_mgmt = site_management_registry["site_management"]
        self._configured_sites = self._site_mgmt.load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

        # 2. Values of global settings
        self._global_settings = load_configuration_settings()

        # 3. Site specific global settings

        if is_distributed_setup_remote_site(self._configured_sites):
            self._current_settings = dict(load_site_global_settings())
        else:
            self._current_settings = self._site.get("globals", {})

    def title(self) -> str:
        return _("Edit site specific global settings of %s") % self._site_id

    def _breadcrumb_url(self) -> str:
        return self.mode_url(site=self._site_id)

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                _page_menu_dropdown_site_details(
                    self._site_id, self._site, self._configured_sites, self.name()
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

        self._extend_display_dropdown(menu)
        return menu

    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self, config: Config) -> ActionResult:
        varname = request.get_ascii_input("_varname")
        action = request.get_ascii_input("_action")
        if not varname:
            return None

        if varname not in config_variable_registry:
            return None

        config_variable = config_variable_registry[varname]
        def_value = self._global_settings.get(varname, self._default_values[varname])

        if not transactions.check_transaction():
            return None

        if varname in self._current_settings:
            new_value = not self._current_settings[varname]
        else:
            new_value = not def_value

        if varname == CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT:
            site_specific_settings = {
                site_id: deepcopy(site_conf.get("globals", {}))
                for site_id, site_conf in config.sites.items()
            }
            site_specific_settings[self._site_id][varname] = new_value

            validate_piggyback_hub_config(
                config.sites,
                finalize_all_settings_per_site(
                    self._default_values, self._global_settings, site_specific_settings
                ),
            )

        self._current_settings[varname] = new_value

        msg = _("Changed site specific configuration variable %s to %s.") % (
            varname,
            _("on") if self._current_settings[varname] else _("off"),
        )

        self._site.setdefault("globals", {})[varname] = self._current_settings[varname]
        self._site_mgmt.save_sites(
            self._configured_sites,
            activate=False,
            pprint_value=config.wato_pprint_config,
        )

        if self._site_id == omd_site():
            save_site_global_settings(self._current_settings)

        _changes.add_change(
            action_name="edit-configvar",
            text=msg,
            user_id=user.id,
            sites=[self._site_id],
            domains=list(config_variable.all_domains()),
            need_restart=config_variable.need_restart(),
            use_git=config.wato_use_git,
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("edit_site_globals", site=self._site_id))

    def _groups(self) -> Iterable[ConfigVariableGroup]:
        return self._get_groups(show_all=True)

    @property
    def edit_mode_name(self) -> str:
        return "edit_site_configvar"

    def page(self, config: Config) -> None:
        html.help(
            _(
                "Here you can configure global settings, that should just be applied "
                "on that site. <b>Note</b>: this only makes sense if the site "
                "is part of a distributed setup."
            )
        )

        if not is_distributed_setup_remote_site(self._configured_sites):
            if not has_distributed_setup_remote_sites(self._configured_sites):
                html.show_error(
                    _(
                        "You cannot configure site specific global settings "
                        "in non-distributed setups."
                    )
                )
                return

            if not is_replication_enabled(self._site) and not site_is_local(
                self._configured_sites[self._site_id]
            ):
                html.show_error(
                    _(
                        "This site is not the central site nor a replication "
                        "remote site. You cannot configure specific settings for it."
                    )
                )
                return

        self._show_configuration_variables(config)

    @override
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext:
        return make_global_settings_context(self._site_id, config)


class ModeEditSiteGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    def name(cls) -> str:
        return "edit_site_configvar"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_GLOBAL_SETTINGS

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditSiteGlobals

    def _from_vars(self) -> None:
        super()._from_vars()
        self._site_id = SiteId(request.get_ascii_input_mandatory("site"))
        if self._site_id:
            self._configured_sites = site_management_registry["site_management"].load_sites()
            try:
                site = self._configured_sites[self._site_id]
            except KeyError:
                raise MKUserError("site", _("Invalid site"))

        self._current_settings = site.setdefault("globals", {})
        self._global_settings = load_configuration_settings()

    def title(self) -> str:
        return _("Site-specific global configuration for %s") % self._site_id

    def _affected_sites(self) -> list[SiteId]:
        return [self._site_id]

    def _save(self, *, pprint_value: bool, use_git: bool) -> None:
        site_management_registry["site_management"].save_sites(
            self._configured_sites,
            activate=False,
            pprint_value=pprint_value,
        )
        if self._site_id == omd_site():
            save_site_global_settings(self._current_settings)

    def _show_global_setting(self) -> None:
        forms.section(_("Global setting"))
        html.write_text_permissive(
            self._valuespec.value_to_html(self._global_settings[self._varname])
        )

    def _back_url(self) -> str:
        return ModeEditSiteGlobals.mode_url(site=self._site_id)

    @override
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext:
        return make_global_settings_context(self._site_id, config)


class ModeSiteLivestatusEncryption(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "site_livestatus_encryption"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_SITES

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditSite

    def __init__(self) -> None:
        super().__init__()
        self._site_id = SiteId(request.get_ascii_input_mandatory("site"))
        self._site_mgmt = site_management_registry["site_management"]
        self._configured_sites = self._site_mgmt.load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

    def title(self) -> str:
        return _("Livestatus encryption of %s") % self._site_id

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                _page_menu_dropdown_site_details(
                    self._site_id, self._site, self._configured_sites, self.name()
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self, config: Config) -> ActionResult:
        if not transactions.check_transaction():
            return None

        action = request.get_ascii_input_mandatory("_action")
        if action != "trust":
            return None

        digest_sha256 = request.get_ascii_input("_digest")

        try:
            cert_details = self._fetch_certificate_details()
        except Exception as e:
            logger.exception("Failed to fetch peer certificate")
            html.show_error(_("Failed to fetch peer certificate (%s)") % e)
            return None

        cert_pem = None
        for cert_detail in cert_details:
            if cert_detail.digest_sha256 == digest_sha256:
                cert_pem = cert_detail.verify_result.cert_pem

        if cert_pem is None:
            raise MKGeneralException(_("Failed to find matching certificate in chain"))

        config_variable = config_variable_registry["trusted_certificate_authorities"]

        global_settings = load_configuration_settings()
        trusted = global_settings.get(
            "trusted_certificate_authorities",
            ABCConfigDomain.get_all_default_globals()["trusted_certificate_authorities"],
        )
        trusted_cas = trusted.setdefault("trusted_cas", [])

        if (cert_str := cert_pem.decode()) in trusted_cas:
            raise MKUserError(
                None,
                _('The CA is already a <a href="%s">trusted CA</a>.')
                % "wato.py?mode=edit_configvar&varname=trusted_certificate_authorities",
            )

        trusted_cas.append(cert_str)

        _changes.add_change(
            action_name="edit-configvar",
            text=_("Added CA with fingerprint %s to trusted certificate authorities")
            % digest_sha256,
            user_id=user.id,
            domains=[config_variable.primary_domain()],
            need_restart=config_variable.need_restart(),
            use_git=config.wato_use_git,
        )
        save_global_settings(
            {
                **global_settings,
                "trusted_certificate_authorities": trusted,
            }
        )

        flash(_("Added CA with fingerprint %s to trusted certificate authorities") % digest_sha256)
        return None

    def page(self, config: Config) -> None:
        if not is_livestatus_encrypted(self._site):
            html.show_message(
                _("The livestatus connection to this site is configured not to be encrypted.")
            )
            return

        assert (
            isinstance(self._site["socket"], tuple)
            and self._site["socket"][1] is not None
            and "tls" in self._site["socket"][1]
        )
        if cast(NetworkSocketDetails, self._site["socket"][1])["tls"][1]["verify"] is False:
            html.show_warning(
                _("Encrypted connections to this site are made without certificate verification.")
            )

        try:
            cert_details = list(self._fetch_certificate_details())
        except Exception as e:
            logger.exception("Failed to fetch peer certificate")
            html.show_error(_("Failed to fetch peer certificate (%s)") % e)
            return

        html.h3(_("Certificate details"))
        html.open_table(class_=["data", "headerleft"])

        server_cert = cert_details[0]
        title: str
        css_class: None | str
        value: Any  # TODO: Should be HTMLContent! Bugs ahead...
        for title, css_class, value in [
            (_("Issued to"), None, server_cert.issued_to),
            (_("Issued by"), None, server_cert.issued_by),
            (_("Valid from"), None, server_cert.valid_from),
            (_("Valid till"), None, server_cert.valid_till),
            (_("Signature algorithm"), None, server_cert.signature_algorithm),
            (_("Fingerprint (SHA256)"), None, server_cert.digest_sha256),
            (_("Serial number"), None, server_cert.serial_number),
            (
                _("Trusted"),
                self._cert_trusted_css_class(server_cert),
                self._render_cert_trusted(server_cert),
            ),
        ]:
            html.open_tr()
            html.th(title)
            html.td(value, class_=css_class)
            html.close_tr()
        html.close_table()

        with table_element("certificate_chain", _("Certificate chain")) as table:
            for cert_detail in reversed(cert_details[1:]):
                table.row()
                table.cell(_("Actions"), css=["buttons"])
                if cert_detail.is_ca:
                    url = makeactionuri(
                        request,
                        transactions,
                        [
                            ("_action", "trust"),
                            ("_digest", cert_detail.digest_sha256),
                        ],
                    )
                    html.icon_button(
                        url=url, title=_("Add to trusted CAs"), icon=StaticIcon(IconNames.trust)
                    )
                table.cell(_("Issued to"), cert_detail.issued_to)
                table.cell(_("Issued by"), cert_detail.issued_by)
                table.cell(_("Is CA"), _("Yes") if cert_detail.is_ca else _("No"))
                table.cell(_("Fingerprint (SHA256)"), cert_detail.digest_sha256)
                table.cell(_("Valid till"), cert_detail.valid_till)
                table.cell(
                    _("Trusted"),
                    self._render_cert_trusted(cert_detail),
                    css=[self._cert_trusted_css_class(cert_detail)],
                )

    def _render_cert_trusted(self, cert: CertificateDetails) -> str:
        if cert.verify_result.is_valid:
            return _("Yes")

        return _("No (error: %s, code: %d, depth: %d)") % (
            cert.verify_result.error_message,
            cert.verify_result.error_number,
            cert.verify_result.error_depth,
        )

    def _cert_trusted_css_class(self, cert: CertificateDetails) -> str:
        return "state state0" if cert.verify_result.is_valid else "state state2"

    def _fetch_certificate_details(self) -> Iterable[CertificateDetails]:
        user.need_permission("general.server_side_requests")
        assert isinstance(self._site["socket"], tuple) and self._site["socket"][1] is not None
        family_spec, address_spec = self._site["socket"]
        address_family = socket.AF_INET if family_spec == "tcp" else socket.AF_INET6
        address = cast(NetworkSocketDetails, address_spec)["address"]
        return fetch_certificate_details(cmk.utils.paths.trusted_ca_file, address_family, address)


def _page_menu_dropdown_site_details(
    site_id: str, site: SiteConfiguration, site_configs: SiteConfigurations, current_mode: str
) -> PageMenuDropdown:
    return PageMenuDropdown(
        name="connections",
        title=_("Connections"),
        topics=[
            PageMenuTopic(
                title=_("This connection"),
                entries=list(
                    _page_menu_entries_site_details(site_id, site, site_configs, current_mode)
                ),
            ),
        ],
    )


def _page_menu_entries_site_details(
    site_id: str, site: SiteConfiguration, site_configs: SiteConfigurations, current_mode: str
) -> Iterator[PageMenuEntry]:
    if current_mode != "edit_site_globals" and site_globals_editable(site_configs, site):
        yield PageMenuEntry(
            title=_("Global settings"),
            icon_name=StaticIcon(IconNames.configuration),
            item=make_simple_link(
                makeuri_contextless(request, [("mode", "edit_site_globals"), ("site", site_id)]),
            ),
        )

    if current_mode != "edit_site":
        yield PageMenuEntry(
            title=_("Edit connection"),
            icon_name=StaticIcon(IconNames.edit),
            item=make_simple_link(
                makeuri_contextless(request, [("mode", "edit_site"), ("site", site_id)]),
            ),
        )

    if current_mode != "site_livestatus_encryption":
        yield PageMenuEntry(
            title=_("Status encryption"),
            icon_name=StaticIcon(IconNames.encrypted),
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "site_livestatus_encryption"), ("site", site_id)],
                )
            ),
        )


def sort_sites(sites: SiteConfigurations) -> list[tuple[SiteId, SiteConfiguration]]:
    """Sort given sites argument by local, followed by remote sites"""
    return sorted(
        sites.items(),
        key=lambda sid_s: (
            is_replication_enabled(sid_s[1]),
            sid_s[1]["alias"],
            sid_s[0],
        ),
    )
