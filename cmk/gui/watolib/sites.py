#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import time
from pathlib import Path
from typing import Any, cast, NamedTuple

from livestatus import NetworkSocketDetails, SiteConfiguration, SiteConfigurations, SiteId

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.config_validation_layer.site_management import validate_sites
from cmk.utils.site import omd_site

import cmk.gui.hooks as hooks
import cmk.gui.sites
import cmk.gui.watolib.activate_changes
import cmk.gui.watolib.changes
import cmk.gui.watolib.sidebar_reload
from cmk.gui.config import (
    active_config,
    default_single_site_configuration,
    load_config,
    prepare_raw_site_config,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.site_config import has_wato_slave_sites, is_wato_slave_site, site_is_local
from cmk.gui.userdb import connection_choices
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    FixedValue,
    Float,
    HostAddress,
    Integer,
    IPNetwork,
    ListChoice,
    ListOfStrings,
    MigrateNotUpdated,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainGUI,
    ConfigDomainLiveproxy,
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

    def read_file_and_validate(self) -> None:
        cfg = self.load_for_reading()
        validate_sites(cfg)


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
                (None, _("Disable automatic user synchronization (use master site users)")),
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
    def validate_configuration(  # pylint: disable=too-many-branches
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

        if site_configuration.get("replication"):
            multisiteurl = site_configuration.get("multisiteurl")
            if not site_configuration.get("multisiteurl"):
                raise MKUserError(
                    "multisiteurl", _("Please enter the Multisite URL of the slave site.")
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

            if cmk_version.edition_supports_nagvis():
                _create_nagvis_backends(sites)

            # Call the sites saved hook
            hooks.call("sites-saved", sites)

    @classmethod
    def delete_site(cls, site_id):
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

        domains = cls._affected_config_domains()

        del all_sites[site_id]
        sites_config_file.save(all_sites)
        cmk.gui.watolib.activate_changes.clear_site_replication_status(site_id)
        cmk.gui.watolib.changes.add_change(
            "edit-sites", _("Deleted site %s") % site_id, domains=domains, sites=[omd_site()]
        )

    @classmethod
    def _affected_config_domains(cls):
        return [ConfigDomainGUI]


class SiteManagementFactory:
    @staticmethod
    def factory() -> SiteManagement:
        if cmk_version.edition() is cmk_version.Edition.CRE:
            cls: type[SiteManagement] = CRESiteManagement
        else:
            cls = CEESiteManagement

        return cls()


class CRESiteManagement(SiteManagement):
    pass


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plug-in hierarchy and
# move this to a CEE/CME specific watolib plugin
class CEESiteManagement(SiteManagement):
    @classmethod
    def livestatus_proxy_valuespec(cls):
        return Alternative(
            title=_("Use Livestatus Proxy Daemon"),
            elements=[
                FixedValue(
                    value=None,
                    title=_("Connect directly, without Livestatus Proxy"),
                    totext="",
                ),
                MigrateNotUpdated(
                    valuespec=Dictionary(
                        title=_("Use Livestatus Proxy Daemon"),
                        optional_keys=["tcp"],
                        columns=1,
                        elements=[
                            (
                                "params",
                                Alternative(
                                    title=_("Parameters"),
                                    elements=[
                                        FixedValue(
                                            value=None,
                                            title=_("Use global connection parameters"),
                                            totext=_(
                                                'Use the <a href="%s">global parameters</a> for this connection'
                                            )
                                            % "wato.py?mode=edit_configvar&site=&varname=liveproxyd_default_connection_params",
                                        ),
                                        Dictionary(
                                            title=_("Use custom connection parameters"),
                                            elements=cls.liveproxyd_connection_params_elements(),
                                        ),
                                    ],
                                ),
                            ),
                            ("tcp", _liveproxyd_via_tcp()),
                        ],
                    ),
                    migrate=cls.migrate_old_connection_params,
                ),
            ],
        )

    # Duplicate code with cmk.cee.liveproxy.Channel._transform_old_socket_spec
    @classmethod
    def _transform_old_socket_spec(cls, sock_spec):
        """Transforms pre 1.6 socket configs"""
        if isinstance(sock_spec, str):
            return "unix", {
                "path": sock_spec,
            }

        if isinstance(sock_spec, tuple) and len(sock_spec) == 2 and isinstance(sock_spec[1], int):
            return "tcp", {
                "address": sock_spec,
            }

        return sock_spec

    @classmethod
    def liveproxyd_connection_params_elements(cls):
        defaults = ConfigDomainLiveproxy.connection_params_defaults()

        return [
            (
                "channels",
                Integer(
                    title=_("Number of channels to keep open"),
                    minvalue=2,
                    maxvalue=50,
                    default_value=defaults["channels"],
                ),
            ),
            (
                "heartbeat",
                Tuple(
                    title=_("Regular heartbeat"),
                    orientation="float",
                    elements=[
                        Integer(
                            label=_("One heartbeat every"),
                            unit=_("sec"),
                            minvalue=1,
                            default_value=defaults["heartbeat"][0],
                        ),
                        Float(
                            label=_("with a timeout of"),
                            unit=_("sec"),
                            minvalue=0.1,
                            default_value=defaults["heartbeat"][1],
                        ),
                    ],
                ),
            ),
            (
                "channel_timeout",
                Float(
                    title=_("Timeout waiting for a free channel"),
                    minvalue=0.1,
                    default_value=defaults["channel_timeout"],
                    unit=_("sec"),
                ),
            ),
            (
                "query_timeout",
                Float(
                    title=_("Total query timeout"),
                    minvalue=0.1,
                    unit=_("sec"),
                    default_value=defaults["query_timeout"],
                ),
            ),
            (
                "connect_retry",
                Float(
                    title=_("Cooling period after failed connect/heartbeat"),
                    minvalue=0.1,
                    unit=_("sec"),
                    default_value=defaults["connect_retry"],
                ),
            ),
            (
                "cache",
                Checkbox(
                    title=_("Enable Caching"),
                    label=_("Cache several non-status queries"),
                    help=_(
                        "This option will enable the caching of several queries that "
                        "need no current data. This reduces the number of Livestatus "
                        "queries to sites and cuts down the response time of remote "
                        "sites with large latencies."
                    ),
                    default_value=defaults["cache"],
                ),
            ),
        ]

    # Each site had it's individual connection params set all time. Detect whether or
    # not a site is at the default configuration and set the config to
    # "use default connection params". In case the values are not similar to the current
    # defaults just change the data structure to the new one.
    @classmethod
    def migrate_old_connection_params(cls, value):
        if "params" in value:
            return value

        new_value = {
            "params": value,
        }

        defaults = ConfigDomainLiveproxy.connection_params_defaults()
        for key, val in list(value.items()):
            if val == defaults[key]:
                del value[key]

        if not value:
            new_value["params"] = None

        return new_value

    @classmethod
    def save_sites(cls, sites, activate=True):
        super().save_sites(sites, activate)

        if activate and active_config.liveproxyd_enabled:
            cls._save_liveproxyd_config(sites)

    @classmethod
    def _save_liveproxyd_config(cls, sites):
        path = cmk.utils.paths.default_config_dir + "/liveproxyd.mk"

        conf = {}
        for siteid, siteconf in sites.items():
            proxy_params = siteconf.get("proxy")
            if proxy_params is None:
                continue

            conf[siteid] = {
                "socket": siteconf["socket"],
            }

            if "tcp" in proxy_params:
                conf[siteid]["tcp"] = proxy_params["tcp"]

            if proxy_params["params"]:
                conf[siteid].update(proxy_params["params"])

        store.save_to_mk_file(path, "sites", conf)

        ConfigDomainLiveproxy().activate()

    @classmethod
    def _affected_config_domains(cls):
        domains = super()._affected_config_domains()
        if active_config.liveproxyd_enabled:
            domains.append(ConfigDomainLiveproxy)
        return domains


def _liveproxyd_via_tcp() -> Dictionary:
    return Dictionary(
        title=_("Allow access via TCP"),
        help=_(
            "This option can be useful to build a cascading distributed setup. "
            "The Livestatus Proxy of this site connects to the site configured "
            "here via Livestatus and opens up a TCP port for clients. The "
            "requests of the clients are forwarded to the destination site. "
            "You need to configure a TCP port here that is not used on the "
            "local system yet."
        ),
        elements=[
            (
                "port",
                Integer(
                    title=_("TCP port"),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=6560,
                ),
            ),
            (
                "only_from",
                ListOfStrings(
                    title=_("Restrict access to IP addresses"),
                    help=_(
                        "The access to the Livestatus Proxy via TCP will only be allowed from the "
                        "configured source IP addresses. For an IP address to be allowed it must "
                        "exactly match one of the specified values."
                    ),
                    valuespec=IPNetwork(),  # TODO: This is nonsense.
                    orientation="horizontal",
                    allow_empty=False,
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
        ],
        optional_keys=["only_from", "tls"],
    )


# Don't use or change this ValueSpec, it is out-of-date. It can't be removed due to CMK-12228.
class LivestatusViaTCP(Dictionary):
    def __init__(
        self,
        title: str | None = None,
        help: str | None = None,  # pylint: disable=redefined-builtin
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
        if site.get("replication"):
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

    return bool(site["replication"]) or site_is_local(active_config, site_id)


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
        sites = SiteManagementFactory.factory().load_sites()
        current_settings = sites.get(site_id, SiteConfiguration({})).get("globals", {})

    if varname in current_settings:
        return current_settings[varname]

    if varname in effective_global_settings:
        return effective_global_settings[varname]

    return default_values[varname]
