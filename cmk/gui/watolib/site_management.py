#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator, Mapping, Set
from dataclasses import dataclass, field
from typing import Any, cast, Literal

from livestatus import (
    BrokerConnection,
    BrokerConnections,
    ConnectionId,
    LocalSocketInfo,
    NetworkSocketDetails,
    NetworkSocketInfo,
    ProxyConfig,
    ProxyConfigParams,
    ProxyConfigTcp,
    SiteConfiguration,
    SiteConfigurations,
    TLSInfo,
    TLSParams,
    UnixSocketDetails,
    UnixSocketInfo,
)

from cmk.ccc import version
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId

from cmk.utils import paths

from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.site_config import is_replication_enabled, site_is_local
from cmk.gui.watolib.activate_changes import clear_site_replication_status
from cmk.gui.watolib.audit_log import LogMessage
from cmk.gui.watolib.automations import do_site_login
from cmk.gui.watolib.broker_certificates import trigger_remote_certs_creation
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.sites import site_management_registry

DEFAULT_MESSAGE_BROKER_PORT = 5672


class SiteDoesNotExistException(Exception): ...


class SiteAlreadyExistsException(Exception): ...


class SiteVersionException(Exception): ...


class LoginException(Exception): ...


@dataclass
class Socket:
    socket_type: Literal["unix", "tcp6", "tcp", "local"] | None = None
    host: str | None = None
    port: int | None = None
    encrypted: bool | None = None
    verify: bool | None = None
    path: str | None = None

    @classmethod
    def from_external(cls, external_config: dict[str, Any]) -> Socket:
        if external_config["socket_type"] in ("tcp", "tcp6"):
            if not external_config["encrypted"]:
                external_config.pop("verify", None)
        return cls(**external_config)

    @classmethod
    def from_internal(
        cls, internal_config: str | UnixSocketInfo | NetworkSocketInfo | LocalSocketInfo
    ) -> Socket:
        if isinstance(internal_config, str):
            return cls(socket_type="local")

        if internal_config[0] == "local":
            return cls(socket_type=internal_config[0])

        if internal_config[0] == "unix":
            return cls(socket_type=internal_config[0], path=internal_config[1].get("path"))

        host, port = internal_config[1]["address"]
        encrypt, verify_dict = internal_config[1]["tls"]
        encrypted = encrypt == "encrypted"
        verify = verify_dict.get("verify")

        return cls(
            socket_type=internal_config[0], host=host, port=port, verify=verify, encrypted=encrypted
        )

    def to_external(self) -> Iterator[tuple[str, str | int | bool]]:
        for k, v in self.__dict__.items():
            if v is not None:
                yield k, v

    def to_internal(self) -> NetworkSocketInfo | UnixSocketInfo | LocalSocketInfo:
        if self.socket_type in ("tcp", "tcp6"):
            if self.host and self.port:
                tls_params = TLSParams()

                if self.verify is not None:
                    tls_params["verify"] = self.verify

                encrypt_status: Literal["encrypted", "plain_text"] = (
                    "encrypted" if self.encrypted else "plain_text"
                )
                tls_info: TLSInfo = (encrypt_status, tls_params)

                networksockdetails: NetworkSocketDetails = {
                    "tls": tls_info,
                    "address": (self.host, self.port),
                }
                socket_type = cast(Literal["tcp", "tcp6"], self.socket_type)
                networksockinfo: NetworkSocketInfo = (socket_type, networksockdetails)
                return networksockinfo

        if self.path:
            details: UnixSocketDetails = {"path": self.path}
            unixsocketinfo: UnixSocketInfo = ("unix", details)
            return unixsocketinfo

        localsocketinfo: LocalSocketInfo = ("local", None)
        return localsocketinfo


@dataclass
class StatusHost:
    site: SiteId | None = None
    host: str | None = None
    status_host_set: Literal["enabled", "disabled"] = "disabled"

    @classmethod
    def from_internal(cls, internal_config: tuple[SiteId, str] | None) -> StatusHost:
        if internal_config is None:
            return cls(status_host_set="disabled")

        return cls(site=internal_config[0], host=str(internal_config[1]), status_host_set="enabled")

    def to_external(self) -> Iterator[tuple[str, str | bool | None]]:
        yield "status_host_set", self.status_host_set

        if self.status_host_set == "enabled":
            yield "site", self.site
            yield "host", self.host

    def to_internal(self) -> tuple[SiteId, str] | None:
        if self.site and self.host:
            return (self.site, self.host)
        return None


@dataclass
class Heartbeat:
    interval: int
    timeout: float

    def __iter__(self) -> Iterator[tuple[str, int]]:
        yield from self.__dict__.items()


@dataclass
class ProxyParams:
    channels: int | None = None
    heartbeat: Heartbeat | None = None
    channel_timeout: float | None = None
    query_timeout: float | None = None
    connect_retry: float | None = None
    cache: bool | None = None

    @classmethod
    def from_internal(cls, internal_config: ProxyConfigParams | None) -> ProxyParams:
        if internal_config is None:
            return cls()

        hb = internal_config.get("heartbeat")
        return cls(
            channels=internal_config.get("channels"),
            heartbeat=Heartbeat(*hb) if hb else None,
            channel_timeout=internal_config.get("channel_timeout"),
            query_timeout=internal_config.get("query_timeout"),
            connect_retry=internal_config.get("connect_retry"),
            cache=internal_config.get("cache"),
        )

    def to_external(self) -> Iterator[tuple[str, dict[str, int] | int | bool | float]]:
        for k, v in self.__dict__.items():
            if k == "heartbeat" and self.heartbeat is not None:
                yield k, dict(self.heartbeat)
                continue

            if v is not None:
                yield k, v

    def to_internal(self) -> ProxyConfigParams:
        proxyconfigparams: ProxyConfigParams = {}
        if self.channels is not None:
            proxyconfigparams["channels"] = self.channels

        if self.heartbeat:
            proxyconfigparams["heartbeat"] = (self.heartbeat.interval, self.heartbeat.timeout)

        if self.channel_timeout is not None:
            proxyconfigparams["channel_timeout"] = self.channel_timeout

        if self.query_timeout is not None:
            proxyconfigparams["query_timeout"] = self.query_timeout

        if self.connect_retry is not None:
            proxyconfigparams["connect_retry"] = self.connect_retry

        if self.cache is not None:
            proxyconfigparams["cache"] = self.cache

        return proxyconfigparams


@dataclass
class ProxyTcp:
    port: int | None = None
    only_from: list[str] = field(default_factory=list)
    tls: bool = False

    def to_external(self) -> Iterator[tuple[str, int | list[str] | bool]]:
        if self.port:
            yield from self.__dict__.items()

    def to_internal(self) -> ProxyConfigTcp:
        proxyconfigtcp: ProxyConfigTcp = {}
        if self.port:
            proxyconfigtcp["port"] = self.port
            proxyconfigtcp["only_from"] = self.only_from

            if self.tls:
                proxyconfigtcp["tls"] = self.tls

        return proxyconfigtcp


@dataclass
class Proxy:
    direct_or_with_proxy: Literal["with_proxy", "direct"]
    params: ProxyParams | None = None
    tcp: ProxyTcp | None = None
    global_settings: bool | None = None

    @classmethod
    def from_external(cls, external_config: Mapping[str, Any]) -> Proxy:
        direct_or_with_proxy = external_config["use_livestatus_daemon"]
        global_settings = (
            external_config["global_settings"] if direct_or_with_proxy == "with_proxy" else None
        )

        params = external_config.get("params", {})
        if heartbeat := params.get("heartbeat"):
            params["heartbeat"] = Heartbeat(**heartbeat)

        return cls(
            direct_or_with_proxy=direct_or_with_proxy,
            global_settings=global_settings,
            params=ProxyParams(**params),
            tcp=ProxyTcp(**external_config.get("tcp", {})),
        )

    @classmethod
    def from_internal(cls, internal_config: ProxyConfig | None) -> Proxy:
        if internal_config is None:
            return cls(direct_or_with_proxy="direct")

        direct_or_with_proxy: Literal["with_proxy", "direct"] = (
            "with_proxy" if "params" in internal_config else "direct"
        )

        return cls(
            direct_or_with_proxy=direct_or_with_proxy,
            global_settings=bool(internal_config.get("params") is None),
            params=ProxyParams.from_internal(internal_config.get("params", {})),
            tcp=ProxyTcp(**internal_config.get("tcp", {})),
        )

    def to_external(self) -> Iterator[tuple[str, str | bool | None | dict]]:
        yield "use_livestatus_daemon", self.direct_or_with_proxy

        if self.direct_or_with_proxy == "with_proxy":
            yield "global_settings", self.global_settings

            if self.params:
                if paramsdict := dict(self.params.to_external()):
                    yield "params", paramsdict

            if self.tcp:
                if tcpdict := dict(self.tcp.to_external()):
                    yield "tcp", tcpdict

    def to_internal(self) -> ProxyConfig | None:
        if self.direct_or_with_proxy == "direct":
            return None

        proxyconfig: ProxyConfig = {}
        proxyconfig["params"] = {}

        if self.global_settings:
            proxyconfig["params"] = None

        if self.params:
            if paramsdict := self.params.to_internal():
                proxyconfig["params"] = paramsdict

        if self.tcp:
            if tcpdict := self.tcp.to_internal():
                proxyconfigtcp: ProxyConfigTcp = tcpdict
                proxyconfig["tcp"] = proxyconfigtcp

        return proxyconfig


@dataclass
class BasicSettings:
    alias: str
    site_id: str
    customer: str | None = None

    @classmethod
    def from_internal(cls, site_id: SiteId, internal_config: SiteConfiguration) -> BasicSettings:
        if version.edition(paths.omd_root) is version.Edition.CME:
            return cls(
                alias=internal_config["alias"],
                site_id=site_id,
                customer=internal_config.get("customer", customer_api().default_customer_id()),
            )
        return cls(alias=internal_config["alias"], site_id=site_id)

    def to_external(self) -> Iterator[tuple[str, str]]:
        yield "alias", self.alias
        yield "site_id", self.site_id
        if version.edition(paths.omd_root) is version.Edition.CME and self.customer is not None:
            yield "customer", self.customer

    def to_internal(self, internal_config: SiteConfiguration) -> None:
        internal_config["alias"] = self.alias
        internal_config["id"] = SiteId(self.site_id)

        if version.edition(paths.omd_root) is version.Edition.CME and self.customer is not None:
            internal_config["customer"] = self.customer


@dataclass
class StatusConnection:
    connection: Socket
    proxy: Proxy
    connect_timeout: int
    persistent_connection: bool
    url_prefix: str
    status_host: StatusHost
    disable_in_status_gui: bool

    @classmethod
    def from_internal(cls, internal_config: SiteConfiguration) -> StatusConnection:
        return cls(
            connection=Socket.from_internal(internal_config["socket"]),
            proxy=Proxy.from_internal(internal_config=internal_config.get("proxy")),
            connect_timeout=internal_config["timeout"],
            persistent_connection=internal_config["persist"],
            url_prefix=internal_config.get("url_prefix", ""),
            status_host=StatusHost.from_internal(
                internal_config=internal_config.get("status_host")
            ),
            disable_in_status_gui=internal_config["disabled"],
        )

    @classmethod
    def from_external(cls, external_config: Mapping[str, Any]) -> StatusConnection:
        return cls(
            connection=Socket.from_external(external_config["connection"]),
            proxy=Proxy.from_external(external_config["proxy"]),
            connect_timeout=external_config["connect_timeout"],
            persistent_connection=external_config["persistent_connection"],
            url_prefix=external_config["url_prefix"],
            status_host=StatusHost(**external_config["status_host"]),
            disable_in_status_gui=external_config["disable_in_status_gui"],
        )

    def to_external(self) -> Iterator[tuple[str, dict | bool | int]]:
        for k, v in self.__dict__.items():
            if k == "status_host":
                yield k, dict(self.status_host.to_external())
                continue

            if k == "connection":
                yield k, dict(self.connection.to_external())
                continue

            if k == "proxy":
                yield k, dict(self.proxy.to_external())
                continue

            yield k, v

    def to_internal(self, internal_config: SiteConfiguration) -> None:
        internal_config.update(
            {
                "status_host": self.status_host.to_internal(),
                "socket": self.connection.to_internal(),
                "proxy": self.proxy.to_internal(),
                "disabled": self.disable_in_status_gui,
                "timeout": self.connect_timeout,
                "persist": self.persistent_connection,
                "url_prefix": self.url_prefix,
            }
        )


@dataclass
class UserSync:
    sync_with_ldap_connections: str
    ldap_connections: list[str] = field(default_factory=list)

    @classmethod
    def from_internal(cls, internal_config: tuple | str | None) -> UserSync:
        if isinstance(internal_config, tuple):
            return cls(sync_with_ldap_connections="ldap", ldap_connections=internal_config[1])

        if internal_config == "all":
            return cls(sync_with_ldap_connections="all")

        return cls(sync_with_ldap_connections="disabled")

    @classmethod
    def from_external(cls, external_config: dict[str, Any] | None) -> UserSync:
        if external_config is None:
            return cls(sync_with_ldap_connections="disabled")

        return cls(**external_config)

    def to_external(self) -> Iterator[tuple[str, str | None | list[str]]]:
        yield "sync_with_ldap_connections", self.sync_with_ldap_connections
        if self.ldap_connections:
            yield "ldap_connections", self.ldap_connections

    def to_internal(self) -> Literal["all"] | tuple[Literal["list"], list[str]] | None:
        if self.sync_with_ldap_connections == "all":
            return "all"

        if self.sync_with_ldap_connections == "ldap":
            return ("list", self.ldap_connections)

        return None


@dataclass
class ConfigurationConnection:
    enable_replication: bool
    user_sync: UserSync
    url_of_remote_site: str = ""
    disable_remote_configuration: bool = True
    ignore_tls_errors: bool = False
    direct_login_to_web_gui_allowed: bool = True
    replicate_event_console: bool = True
    replicate_extensions: bool = True
    message_broker_port: int = DEFAULT_MESSAGE_BROKER_PORT

    @classmethod
    def from_internal(
        cls, site_id: SiteId, internal_config: SiteConfiguration
    ) -> ConfigurationConnection:
        return cls(
            enable_replication=is_replication_enabled(internal_config),
            url_of_remote_site=internal_config["multisiteurl"],
            disable_remote_configuration=internal_config["disable_wato"],
            ignore_tls_errors=internal_config["insecure"],
            direct_login_to_web_gui_allowed=internal_config["user_login"],
            user_sync=UserSync.from_internal(
                internal_config=internal_config.get(
                    "user_sync", "all" if site_is_local(internal_config) else "disabled"
                )
            ),
            replicate_event_console=internal_config["replicate_ec"],
            replicate_extensions=internal_config.get("replicate_mkps", False),
            message_broker_port=internal_config.get(
                "message_broker_port", DEFAULT_MESSAGE_BROKER_PORT
            ),
        )

    @classmethod
    def from_external(cls, external_config: dict[str, Any]) -> ConfigurationConnection:
        external_config["user_sync"] = UserSync.from_external(
            external_config["user_sync"] if "user_sync" in external_config else None
        )
        return cls(**external_config)

    def to_external(self) -> Iterator[tuple[str, dict[str, str | list[str] | None] | bool | str]]:
        for k, v in self.__dict__.items():
            if k == "user_sync":
                yield k, dict(self.user_sync.to_external())
                continue

            yield k, v

    def to_internal(self, internal_config: SiteConfiguration) -> None:
        internal_config.update(
            {
                "replication": "slave" if self.enable_replication else None,
                "multisiteurl": self.url_of_remote_site,
                "disable_wato": self.disable_remote_configuration,
                "insecure": self.ignore_tls_errors,
                "user_login": self.direct_login_to_web_gui_allowed,
                "user_sync": self.user_sync.to_internal(),
                "replicate_ec": self.replicate_event_console,
                "replicate_mkps": self.replicate_extensions,
                "message_broker_port": self.message_broker_port,
            }
        )


@dataclass
class SiteConfig:
    basic_settings: BasicSettings
    status_connection: StatusConnection
    configuration_connection: ConfigurationConnection
    secret: str | None = None

    @classmethod
    def from_internal(cls, site_id: SiteId, internal_config: SiteConfiguration) -> SiteConfig:
        return cls(
            basic_settings=BasicSettings.from_internal(site_id, internal_config),
            status_connection=StatusConnection.from_internal(internal_config),
            configuration_connection=ConfigurationConnection.from_internal(
                site_id, internal_config
            ),
            secret=internal_config.get("secret"),
        )

    @classmethod
    def from_external(cls, external_config: dict[str, Any]) -> SiteConfig:
        return cls(
            basic_settings=BasicSettings(**external_config["basic_settings"]),
            status_connection=StatusConnection.from_external(external_config["status_connection"]),
            configuration_connection=ConfigurationConnection.from_external(
                external_config["configuration_connection"]
            ),
            secret=external_config.get("secret"),
        )

    def to_external(self) -> Iterator[tuple[str, dict | None | str]]:
        yield "basic_settings", dict(self.basic_settings.to_external())
        yield "status_connection", dict(self.status_connection.to_external())
        yield "configuration_connection", dict(self.configuration_connection.to_external())
        if self.secret:
            yield "secret", self.secret

    def to_internal(self) -> SiteConfiguration:
        internal_config = SiteConfiguration(
            {
                "id": SiteId(""),
                "alias": "",
                "url_prefix": "",
                "disabled": False,
                "insecure": False,
                "multisiteurl": "",
                "persist": False,
                "proxy": {},
                "message_broker_port": 5672,
                "user_sync": "all",
                "status_host": None,
                "replicate_mkps": True,
                "replicate_ec": True,
                "socket": (
                    "tcp",
                    NetworkSocketDetails(
                        address=("", 6557),
                        tls=(
                            "encrypted",
                            TLSParams(verify=True),
                        ),
                    ),
                ),
                "timeout": 5,
                "disable_wato": True,
                "user_login": True,
                "replication": None,
            }
        )
        self.basic_settings.to_internal(internal_config)
        self.status_connection.to_internal(internal_config)
        self.configuration_connection.to_internal(internal_config)
        if self.secret:
            internal_config["secret"] = self.secret
        return internal_config


class SitesApiMgr:
    def __init__(self) -> None:
        self.site_mgmt = site_management_registry["site_management"]
        self.all_sites = self.site_mgmt.load_sites()

    def get_all_sites(self) -> SiteConfigurations:
        return self.all_sites

    def get_a_site(self, site_id: SiteId) -> SiteConfiguration:
        if not (existing_site := self.all_sites.get(site_id)):
            raise SiteDoesNotExistException
        return existing_site

    def delete_a_site(self, site_id: SiteId, *, pprint_value: bool, use_git: bool) -> None:
        if self.all_sites.get(site_id):
            self.site_mgmt.delete_site(site_id, pprint_value=pprint_value, use_git=use_git)
        raise SiteDoesNotExistException

    def login_to_site(
        self, site_id: SiteId, username: str, password: str, *, pprint_value: bool, debug: bool
    ) -> None:
        site = self.get_a_site(site_id)
        try:
            site["secret"] = do_site_login(site, UserId(username), password, debug=debug)
        except Exception as exc:
            raise LoginException(str(exc))

        self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)
        trigger_remote_certs_creation(site_id, site, force=False, debug=debug)

    def logout_of_site(self, site_id: SiteId, *, pprint_value: bool) -> None:
        site = self.get_a_site(site_id)
        if "secret" in site:
            del site["secret"]
            self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)

    def validate_and_save_site(
        self, site_id: SiteId, site_config: SiteConfiguration, *, pprint_value: bool
    ) -> None:
        self.site_mgmt.validate_configuration(site_id, site_config, self.all_sites)
        self.all_sites[site_id] = site_config
        self.site_mgmt.save_sites(self.all_sites, activate=True, pprint_value=pprint_value)

    def get_connected_sites_to_update(
        self,
        new_or_deleted_connection: bool,
        modified_site: SiteId,
        current_site_config: SiteConfiguration,
        old_site_config: SiteConfiguration | None,
    ) -> set[SiteId]:
        return self.site_mgmt.get_connected_sites_to_update(
            new_or_deleted_connection, modified_site, current_site_config, old_site_config
        )

    def get_broker_connections(self) -> BrokerConnections:
        return self.site_mgmt.get_broker_connections()

    def validate_and_save_broker_connection(
        self,
        connection_id: ConnectionId,
        broker_connection: BrokerConnection,
        *,
        is_new: bool,
        pprint_value: bool,
    ) -> tuple[SiteId, SiteId]:
        return self.site_mgmt.validate_and_save_broker_connection(
            connection_id,
            broker_connection,
            is_new=is_new,
            pprint_value=pprint_value,
        )

    def delete_broker_connection(
        self, connection_id: ConnectionId, pprint_value: bool
    ) -> tuple[SiteId, SiteId]:
        return self.site_mgmt.delete_broker_connection(connection_id, pprint_value)


def add_changes_after_editing_broker_connection(
    *,
    connection_id: str,
    is_new_broker_connection: bool,
    sites: list[SiteId],
) -> LogMessage:
    change_message = (
        _("Created new peer-to-peer broker connection ID %s") % connection_id
        if is_new_broker_connection
        else _("Modified peer-to-peer broker connection ID %s") % connection_id
    )

    add_change(
        action_name="edit-sites",
        text=change_message,
        user_id=user.id,
        need_sync=True,
        need_restart=True,
        sites=[omd_site()] + sites,
        domains=[ConfigDomainGUI()],
        use_git=active_config.wato_use_git,
    )

    return change_message


def add_changes_after_editing_site_connection(
    *,
    site_id: SiteId,
    is_new_connection: bool,
    replication_enabled: bool,
    connected_sites: Set[SiteId] | None = None,
) -> LogMessage:
    change_message = (
        _("Created new connection to site %s") % site_id
        if is_new_connection
        else _("Modified site connection %s") % site_id
    )

    sites_to_update = list((connected_sites or set()) | {site_id})
    add_change(
        action_name="edit-sites",
        text=change_message,
        user_id=user.id,
        sites=sites_to_update,
        # This was ABCConfigDomain.enabled_domains() before. Since e.g. apache config domain takes
        # significant more time to restart than the other domains, we now try to be more specific
        # and mention potentially affected domains instead. The idea here is to first hard code
        # the list of config domains produced by enabled_domains and then reduce it step by step.
        #
        # One the list is minimized, we can turn it into an explicit positive list.
        #
        # If you extend this, please also check the other "add_change" calls triggered by the site
        # management.
        domains=[
            d
            for d in ABCConfigDomain.enabled_domains()
            if d.ident()
            not in {
                "apache",
                "ca-certificates",
                "check_mk",
                "diskspace",
                "ec",
                "omd",
                "otel_collector",
                "rrdcached",
                # Can we remove more here? Investigate further to minimize the domains:
                # "liveproxyd",
                # "multisite",
                # "piggyback_hub",
                # "dcd",
                # "mknotifyd",
            }
        ],
        use_git=active_config.wato_use_git,
    )

    # In case a site is not being replicated anymore, confirm all changes for this site!
    if not replication_enabled and not site_is_local(active_config.sites[site_id]):
        clear_site_replication_status(site_id)

    if site_id != omd_site():
        # On central site issue a change only affecting the GUI
        add_change(
            action_name="edit-sites",
            text=change_message,
            user_id=user.id,
            sites=[omd_site()],
            domains=[ConfigDomainGUI()],
            use_git=active_config.wato_use_git,
        )

    return change_message
