#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import time
from pathlib import Path
from typing import Any, cast, NamedTuple

from livestatus import (
    BrokerConnection,
    BrokerConnections,
    ConnectionId,
    NetworkSocketDetails,
    SiteConfiguration,
    SiteConfigurations,
    SiteId,
)

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site

from cmk.utils import paths

import cmk.gui.sites
import cmk.gui.watolib.activate_changes
import cmk.gui.watolib.changes
import cmk.gui.watolib.sidebar_reload
from cmk.gui import hooks
from cmk.gui.config import (
    active_config,
    default_single_site_configuration,
    load_config,
    prepare_raw_site_config,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.site_config import (
    has_wato_slave_sites,
    is_replication_enabled,
    is_wato_slave_site,
    site_is_local,
    wato_slave_sites,
)
from cmk.gui.userdb import connection_choices
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    Dictionary,
    FixedValue,
    HostAddress,
    Integer,
    IPNetwork,
    ListChoice,
    ListOfStrings,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.watolib.broker_connections import BrokerConnectionsConfigFile
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainGUI,
)
from cmk.gui.watolib.config_sync import create_distributed_wato_files
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import ldap_connections_are_configurable


class SitesConfigFile(WatoSingleConfigFile[SiteConfigurations]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=Path(cmk.utils.paths.default_config_dir + "/multisite.d/sites.mk"),
            config_variable="sites",
            spec_class=SiteConfigurations,
        )

    def _load_file(self, lock: bool) -> SiteConfigurations:
        if not self._config_file_path.exists():
            return default_single_site_configuration()

        sites_from_file = store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default={},
            lock=lock,
        )

        if not sites_from_file:
            return default_single_site_configuration()

        return prepare_raw_site_config(sites_from_file)


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(SitesConfigFile())


class SiteManagement:
    @classmethod
    def connection_method_valuespec(cls):
        return CascadingDropdown(
            title=_("Connection"),
            orientation="horizontal",
            choices=cls._connection_choices(),
            render=CascadingDropdown.Render.foldable,
            help=_(
                "When connecting to remote site please make sure "
                "that Livestatus over TCP is activated there. You can use UNIX sockets "
                "to connect to foreign sites on localhost. Please make sure that this "
                "site has proper read and write permissions to the UNIX socket of the "
                "foreign site."
            ),
        )

    @classmethod
    def livestatus_proxy_valuespec(cls):
        return FixedValue(
            value=None,
            title=_("Use Livestatus Proxy Daemon"),
            totext=_("Connect directly (not available in CRE)"),
        )

    @classmethod
    def _connection_choices(cls):
        conn_choices = [
            (
                "local",
                _("Connect to the local site"),
                FixedValue(
                    value=None,
                    totext="",
                ),
            ),
            ("tcp", _("Connect via TCP (IPv4)"), cls._tcp_socket_valuespec(ipv6=False)),
            ("tcp6", _("Connect via TCP (IPv6)"), cls._tcp_socket_valuespec(ipv6=True)),
            (
                "unix",
                _("Connect via UNIX socket"),
                Dictionary(
                    elements=[
                        (
                            "path",
                            TextInput(
                                label=_("Path:"),
                                size=40,
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
        ]
        return conn_choices

    @classmethod
    def _tcp_socket_valuespec(cls, ipv6):
        return Dictionary(
            elements=[
                (
                    "address",
                    Tuple(
                        title=_("TCP address to connect to"),
                        orientation="float",
                        elements=[
                            HostAddress(
                                label=_("Host:"),
                                allow_empty=False,
                                size=15,
                                allow_ipv4_address=not ipv6,
                                allow_ipv6_address=ipv6,
                            ),
                            Integer(
                                label=_("Port:"),
                                minvalue=1,
                                maxvalue=65535,
                                default_value=6557,
                            ),
                        ],
                    ),
                ),
                ("tls", cls._tls_valuespec()),
            ],
            optional_keys=False,
        )

    @classmethod
    def _tls_valuespec(cls):
        return CascadingDropdown(
            title=_("Encryption"),
            choices=[
                (
                    "plain_text",
                    _("Plain text (Unencrypted)"),
                    FixedValue(value={}, totext=_("Use plain text, unencrypted transport")),
                ),
                (
                    "encrypted",
                    _("Encrypt data using TLS"),
                    Dictionary(
                        elements=[
                            (
                                "verify",
                                Checkbox(
                                    title=_("Verify server certificate"),
                                    label=_(
                                        "Verify the Livestatus server certificate using the local site CA"
                                    ),
                                    default_value=True,
                                    help=_(
                                        "Either verify the server certificate using the site local CA or accept "
                                        "any certificate offered by the server. It is highly recommended to "
                                        "leave this enabled."
                                    ),
                                ),
                            ),
                        ],
                        optional_keys=False,
                    ),
                ),
            ],
            help=_(
                "When connecting to Checkmk versions older than 1.6 you can only use plain text "
                "transport. Starting with Checkmk 1.6 it is possible to use encrypted Livestatus "
                "communication. Sites created with 1.6 will automatically use encrypted communication "
                "by default. Sites created with previous versions need to be configured manually to "
                'enable the encryption. Have a look at <a href="werk.py?werk=7017">werk #7017</a> '
                "for further information."
            ),
        )

    @classmethod
    def user_sync_valuespec(cls, site_id):
        return CascadingDropdown(
            title=_("Sync with LDAP connections"),
            orientation="horizontal",
            choices=[
                (None, _("Disable automatic user synchronization (use central site users)")),
                ("all", _("Sync users with all connections")),
                (
                    "list",
                    _("Sync with the following LDAP connections"),
                    ListChoice(
                        choices=connection_choices,
                        allow_empty=False,
                    ),
                ),
            ],
            default_value="all" if site_is_local(active_config, site_id) else None,
            help=_(
                "By default the users are synchronized automatically in the interval configured "
                "in the connection. For example the LDAP connector synchronizes the users every "
                "five minutes by default. The interval can be changed for each connection "
                'individually in the <a href="wato.py?mode=ldap_config">connection settings</a>. '
                "Please note that the synchronization is only performed on the central site in "
                "distributed setups by default.<br>"
                "The remote sites don't perform automatic user synchronizations with the "
                "configured connections. But you can configure each site to either "
                "synchronize the users with all configured connections or a specific list of "
                "connections."
            ),
        )

    @classmethod
    def is_site_in_broker_connections(cls, site_id: SiteId) -> bool:
        connections = BrokerConnectionsConfigFile().load_for_modification()
        connections_ids = {
            site_id
            for connection in connections.values()
            for site_id in (connection.connectee.site_id, connection.connecter.site_id)
        }

        return site_id in connections_ids

    @classmethod
    def _change_affects_broker_connection(
        cls, current_config: SiteConfiguration, old_config: SiteConfiguration
    ) -> bool:
        return (
            is_replication_enabled(old_config) != is_replication_enabled(current_config)
            or old_config["message_broker_port"] != current_config["message_broker_port"]
            or old_config["multisiteurl"] != current_config["multisiteurl"]
        )

    @classmethod
    def get_connected_sites_to_update(
        cls,
        new_or_deleted_connection: bool,
        modified_site: SiteId,
        current_config: SiteConfiguration,
        old_config: SiteConfiguration | None = None,
    ) -> set[SiteId]:
        connected = {omd_site()}

        if new_or_deleted_connection or (
            old_config
            and is_replication_enabled(old_config) != is_replication_enabled(current_config)
        ):
            connected |= set(wato_slave_sites().keys())
            return connected

        if old_config is None:
            raise MKUserError(None, _("An old configuration is required for existing connections."))

        if not cls._change_affects_broker_connection(current_config, old_config):
            return set()

        connections = BrokerConnectionsConfigFile().load_for_reading()
        for connection in connections.values():
            if modified_site in (
                connection.connectee.site_id,
                connection.connecter.site_id,
            ):
                connected |= {
                    connection.connectee.site_id,
                    connection.connecter.site_id,
                }

        return connected

    @classmethod
    def get_broker_connections(cls) -> BrokerConnections:
        return BrokerConnectionsConfigFile().load_for_reading()

    @classmethod
    def broker_connection_id_exists(cls, connection_id: str) -> bool:
        return connection_id in cls.get_broker_connections()

    @classmethod
    def _validate_broker_connection(
        cls, connection_id: ConnectionId, connection: BrokerConnection, is_new: bool
    ) -> None:
        if not re.match("^[-a-z0-9A-Z_]+$", connection_id):
            raise MKUserError(
                "id", _("The connection id must consist only of letters, digit and the underscore.")
            )

        if connection.connecter.site_id == connection.connectee.site_id:
            raise MKUserError(
                None,
                _("Connecter and connectee sites must be different."),
            )

        if is_new and cls.broker_connection_id_exists(connection_id):
            raise MKUserError(
                None,
                _("Connection id %s already exists.") % connection_id,
            )

        old_connection_sites = {connection.connecter.site_id, connection.connectee.site_id}
        for _conn_id, conn in cls.get_broker_connections().items():
            if _conn_id == connection_id:
                continue

            if old_connection_sites == {conn.connecter.site_id, conn.connectee.site_id}:
                raise MKUserError(
                    None,
                    _("A connection with the same sites already exists."),
                )

    @classmethod
    def _save_broker_connection_config(
        cls, save_id: str, connection: BrokerConnection
    ) -> tuple[SiteId, SiteId]:
        broker_connections = cls.get_broker_connections()
        broker_connections[ConnectionId(save_id)] = connection
        BrokerConnectionsConfigFile().save(broker_connections)
        return connection.connectee.site_id, connection.connecter.site_id

    @classmethod
    def validate_and_save_broker_connection(
        cls, connection_id: ConnectionId, connection: BrokerConnection, is_new: bool
    ) -> tuple[SiteId, SiteId]:
        cls._validate_broker_connection(connection_id, connection, is_new)
        return cls._save_broker_connection_config(connection_id, connection)

    @classmethod
    def delete_broker_connection(cls, connection_id: ConnectionId) -> tuple[SiteId, SiteId]:
        broker_connections = cls.get_broker_connections()
        if connection_id not in broker_connections:
            raise MKUserError(None, _("Unable to delete unknown connection id: %s") % connection_id)

        connection = broker_connections[connection_id]
        del broker_connections[connection_id]
        BrokerConnectionsConfigFile().save(broker_connections)

        return connection.connectee.site_id, connection.connecter.site_id

    @classmethod
    def validate_configuration(
        cls,
        site_id,
        site_configuration,
        all_sites,
    ):
        if not re.match("^[-a-z0-9A-Z_]+$", site_id):
            raise MKUserError(
                "id", _("The site id must consist only of letters, digit and the underscore.")
            )

        if not site_configuration.get("alias"):
            raise MKUserError(
                "alias", _("Please enter an alias name or description for the site %s.") % site_id
            )

        if site_configuration.get("url_prefix") and site_configuration.get("url_prefix")[-1] != "/":
            raise MKUserError("url_prefix", _("The URL prefix must end with a slash."))

        # Connection
        if site_configuration["socket"][0] == "local" and site_id != omd_site():
            raise MKUserError(
                "method_sel",
                _(
                    "You can only configure a local site connection for "
                    "the local site. The site IDs ('%s' and '%s') are "
                    "not equal."
                )
                % (site_id, omd_site()),
            )

        # Timeout
        if "timeout" in site_configuration:
            timeout = site_configuration["timeout"]
            try:
                int(timeout)
            except ValueError:
                raise MKUserError(
                    "timeout", _("The timeout %s is not a valid integer number.") % timeout
                )

        # Status host
        status_host = site_configuration.get("status_host")
        if status_host:
            status_host_site, status_host_name = status_host
            if status_host_site not in all_sites:
                raise MKUserError("sh_site", _("The site of the status host does not exist."))
            if status_host_site == site_id:
                raise MKUserError(
                    "sh_site", _("You cannot use the site itself as site of the status host.")
                )
            if not status_host_name:
                raise MKUserError("sh_host", _("Please specify the name of the status host."))

        if is_replication_enabled(site_configuration):
            multisiteurl = site_configuration.get("multisiteurl")
            if not site_configuration.get("multisiteurl"):
                raise MKUserError(
                    "multisiteurl", _("Please enter the Multisite URL of the remote site.")
                )

            if not multisiteurl.endswith("/check_mk/"):
                raise MKUserError("multisiteurl", _("The Multisite URL must end with /check_mk/"))

            if not multisiteurl.startswith("http://") and not multisiteurl.startswith("https://"):
                raise MKUserError(
                    "multisiteurl",
                    _("The Multisites URL must begin with <tt>http://</tt> or <tt>https://</tt>."),
                )

            if site_configuration["socket"][0] == "local":
                raise MKUserError(
                    "replication", _("You cannot do replication with the local site.")
                )

        if not is_replication_enabled(site_configuration) and cls.is_site_in_broker_connections(
            site_id
        ):
            raise MKUserError(
                "replication",
                _(
                    "You cannot disable the replication on this site. It is used in a broker peer to peer connection."
                ),
            )

        # User synchronization
        if ldap_connections_are_configurable():
            user_sync_valuespec = cls.user_sync_valuespec(site_id)
            user_sync_valuespec.validate_value(site_configuration.get("user_sync"), "user_sync")

    @classmethod
    def load_sites(cls) -> SiteConfigurations:
        return SitesConfigFile().load_for_reading()

    @classmethod
    def save_sites(cls, sites: SiteConfigurations, activate: bool = True) -> None:
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import folder_tree

        SitesConfigFile().save(sites)

        # Do not activate when just the site's global settings have
        # been edited
        if activate:
            load_config()  # make new site configuration active
            _update_distributed_wato_file(sites)
            folder_tree().invalidate_caches()
            cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

            if cmk_version.edition_supports_nagvis(cmk_version.edition(paths.omd_root)):
                _create_nagvis_backends(sites)

            # Call the sites saved hook
            hooks.call("sites-saved", sites)

    @classmethod
    def delete_site(cls, site_id: SiteId) -> None:
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import folder_tree

        sites_config_file = SitesConfigFile()
        all_sites = sites_config_file.load_for_modification()
        if site_id not in all_sites:
            raise MKUserError(None, _("Unable to delete unknown site id: %s") % site_id)

        # Make sure that site is not being used by hosts and folders
        if site_id in folder_tree().root_folder().all_site_ids():
            search_url = makeactionuri(
                request,
                transactions,
                [
                    ("host_search_change_site", "on"),
                    ("host_search_site", site_id),
                    ("host_search", "1"),
                    ("folder", ""),
                    ("mode", "search"),
                    ("filled_in", "edit_host"),
                ],
            )
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It has folders/hosts "
                    'assigned to it. You can use the <a href="%s">host '
                    "search</a> to get a list of the hosts."
                )
                % search_url,
            )

        if cls.is_site_in_broker_connections(site_id):
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It is used in a broker peer to peer connection."
                ),
            )

        domains = cls._affected_config_domains()

        connected_sites = cls.get_connected_sites_to_update(
            new_or_deleted_connection=True, modified_site=site_id, current_config=all_sites[site_id]
        )

        del all_sites[site_id]
        sites_config_file.save(all_sites)

        cmk.gui.watolib.changes.add_change(
            "edit-sites",
            _("Deleted site %s") % site_id,
            domains=domains,
            # Exclude site which is about to be removed. The activation won't be executed for that
            # site anymore, so there is no point in adding a change for this site
            sites=list(connected_sites - {site_id}),
            need_restart=True,
        )
        cmk.gui.watolib.activate_changes.clear_site_replication_status(site_id)

    @classmethod
    def _affected_config_domains(cls) -> list[ABCConfigDomain]:
        return [ConfigDomainGUI()]


class SiteManagementRegistry(Registry[SiteManagement]):
    def plugin_name(self, instance: SiteManagement) -> str:
        return "site_management"


site_management_registry = SiteManagementRegistry()


# Don't use or change this ValueSpec, it is out-of-date. It can't be removed due to CMK-12228.
class LivestatusViaTCP(Dictionary):
    def __init__(
        self,
        title: str | None = None,
        help: str | None = None,
        tcp_port: int = 6557,
    ) -> None:
        elements: list[tuple[str, ValueSpec]] = [
            (
                "port",
                Integer(
                    title=_("TCP port"),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=tcp_port,
                ),
            ),
            (
                "only_from",
                ListOfStrings(
                    title=_("Restrict access to IP addresses"),
                    help=_(
                        "The access to Livestatus via TCP will only be allowed from the "
                        "configured source IP addresses. You can either configure specific "
                        "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."
                    ),
                    valuespec=IPNetwork(),
                    orientation="horizontal",
                    allow_empty=False,
                    default_value=["0.0.0.0", "::/0"],
                ),
            ),
            (
                "tls",
                FixedValue(
                    value=True,
                    title=_("Encrypt communication"),
                    totext=_("Encrypt TCP Livestatus connections"),
                    help=_(
                        "Since Checkmk 1.6 it is possible to encrypt the TCP Livestatus "
                        "connections using SSL. This is enabled by default for sites that "
                        "enable Livestatus via TCP with 1.6 or newer. Sites that already "
                        "have this option enabled keep the communication unencrypted for "
                        "compatibility reasons. However, it is highly recommended to "
                        "migrate to an encrypted communication."
                    ),
                ),
            ),
        ]
        super().__init__(
            title=title,
            help=help,
            elements=elements,
            optional_keys=["only_from", "tls"],
        )


def _create_nagvis_backends(sites_config):
    cfg = [
        "; MANAGED BY CHECK_MK Setup - Last Update: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    for site_id, site in sites_config.items():
        if site_id == omd_site():
            continue  # skip local site, backend already added by omd

        socket = _encode_socket_for_nagvis(site_id, site)

        cfg += [
            "",
            "[backend_%s]" % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if site.get("status_host"):
            cfg.append('statushost="%s:%s"' % site["status_host"])

        if site["proxy"] is None and is_livestatus_encrypted(site):
            address_spec = site["socket"][1]
            tls_settings = address_spec["tls"][1]
            cfg.append("verify_tls_peer=%d" % tls_settings["verify"])
            cfg.append("verify_tls_ca_path=%s" % ConfigDomainCACertificates.trusted_cas_file)

    store.save_text_to_file(
        "%s/etc/nagvis/conf.d/cmk_backends.ini.php" % cmk.utils.paths.omd_root, "\n".join(cfg)
    )


def _encode_socket_for_nagvis(site_id: SiteId, site: SiteConfiguration) -> str:
    if site["proxy"] is None and is_livestatus_encrypted(site):
        assert isinstance(site["socket"], tuple) and site["socket"][0] in ["tcp", "tcp6"]
        return "tcp-tls:%s:%d" % cast(NetworkSocketDetails, site["socket"][1])["address"]
    return cmk.gui.sites.encode_socket_for_livestatus(site_id, site)


# Makes sure, that in distributed mode we monitor only
# the hosts that are directly assigned to our (the local)
# site.
def _update_distributed_wato_file(sites):
    # Note: we cannot access config.sites here, since we
    # are currently in the process of saving the new
    # site configuration.
    distributed = False
    for siteid, site in sites.items():
        if is_replication_enabled(site):
            distributed = True
        if site_is_local(active_config, siteid):
            create_distributed_wato_files(
                base_dir=cmk.utils.paths.omd_root,
                site_id=siteid,
                is_remote=False,
            )

    # Remove the distributed wato file
    # a) If there is no distributed Setup setup
    # b) If the local site could not be gathered
    if not distributed:  # or not found_local:
        _delete_distributed_wato_file()


def is_livestatus_encrypted(site: SiteConfiguration) -> bool:
    if not isinstance(site["socket"], tuple):
        return False
    family_spec, address_spec = site["socket"]
    return (
        family_spec in ["tcp", "tcp6"]
        and cast(NetworkSocketDetails, address_spec)["tls"][0] != "plain_text"
    )


def site_globals_editable(site_id: SiteId, site: SiteConfiguration) -> bool:
    # Site is a remote site of another site. Allow to edit probably pushed site
    # specific globals when remote Setup is enabled
    if is_wato_slave_site():
        return True

    # Local site: Don't enable site specific locals when no remote sites configured
    if not has_wato_slave_sites():
        return False

    return is_replication_enabled(site) or site_is_local(active_config, site_id)


def _delete_distributed_wato_file():
    p = cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk"
    # We do not delete the file but empty it. That way
    # we do not need write permissions to the conf.d
    # directory!
    if os.path.exists(p):
        store.save_text_to_file(p, "")


class PushSnapshotRequest(NamedTuple):
    site_id: SiteId
    tar_content: bytes


def get_effective_global_setting(site_id: SiteId, is_remote_site: bool, varname: str) -> Any:
    effective_global_settings = load_configuration_settings()
    default_values = ABCConfigDomain.get_all_default_globals()

    if is_remote_site:
        current_settings = load_configuration_settings(site_specific=True)
    else:
        sites = site_management_registry["site_management"].load_sites()
        current_settings = sites.get(site_id, SiteConfiguration({})).get("globals", {})

    if varname in current_settings:
        return current_settings[varname]

    if varname in effective_global_settings:
        return effective_global_settings[varname]

    return default_values[varname]
