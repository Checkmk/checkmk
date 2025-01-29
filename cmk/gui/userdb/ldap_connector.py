#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# TODO FIXME: Change attribute sync plug-ins to classes. The current dict
# based approach is not very readable. Classes/objects make it a lot
# easier to understand the mechanics.

# TODO: Move low level LDAP actions to helper class

# TODO: Think about some subclassing for the different directory types.
# This would make some code a lot easier to understand.

# TODO: Change ldap bytes_mode to False and remove all decoding stuff from
# the ldap connector code.

#   .--Declarations--------------------------------------------------------.
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some basic declarations and module loading etc.                      |
#   '----------------------------------------------------------------------'

from __future__ import annotations

import abc
import copy
import logging
import os
import shutil
import sys
import time
import traceback
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast, IO, Literal

# docs: http://www.python-ldap.org/doc/html/index.html
import ldap  # type: ignore[import-untyped]
import ldap.filter  # type: ignore[import-untyped]
from ldap.controls import SimplePagedResultsControl  # type: ignore[import-untyped]

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils import password_store
from cmk.utils.log.security_event import log_security_event
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.user import UserId

from cmk.gui import hooks, log
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user as logged_in_user
from cmk.gui.site_config import has_wato_slave_sites
from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.utils import escaping
from cmk.gui.utils.security_log_events import UserManagementEvent
from cmk.gui.valuespec import (
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    LDAPDistinguishedName,
    ListChoice,
    ListOf,
    MigrateNotUpdated,
    TextInput,
    Tuple,
)
from cmk.gui.watolib.groups_io import load_contact_group_information

from cmk.crypto.password import Password

from ._connections import (
    active_connections,
    ActivePlugins,
    get_connection,
    get_ldap_connections,
    LDAPUserConnectionConfig,
)
from ._connector import CheckCredentialsResult, ConnectorType, UserConnector, UserConnectorRegistry
from ._roles import load_roles
from ._user_attribute import get_user_attributes
from ._user_spec import add_internal_attributes, new_user_template
from ._user_sync_config import user_sync_config
from .store import load_cached_profile, load_users, release_users_lock, save_users


class CantSyncLDAPUserException(MKGeneralException):
    pass


def register(
    user_connector_registry: UserConnectorRegistry,
) -> None:
    user_connector_registry.register(LDAPUserConnector)

    ldap_attribute_plugin_registry.register(LDAPAttributePluginMail)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginAlias)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginAuthExpire)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginPager)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginGroupsToContactgroups)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginGroupAttributes)
    ldap_attribute_plugin_registry.register(LDAPAttributePluginGroupsToRoles)


# LDAP attributes are case insensitive, we only use lower case!
# Please note: This are only default values. The user might override this
# by configuration.
ldap_attr_map = {
    "ad": {
        "user_id": "samaccountname",
        "pw_changed": "pwdlastset",
    },
    "openldap": {
        "user_id": "uid",
        "pw_changed": "pwdchangedtime",
        # group attributes
        "member": "uniquemember",
    },
    "389directoryserver": {
        "user_id": "uid",
        "pw_changed": "krbPasswordExpiration",
        # group attributes
        "member": "member",
    },
}

# LDAP attributes are case insensitive, we only use lower case!
# Please note: This are only default values. The user might override this
# by configuration.
ldap_filter_map = {
    "ad": {
        "users": "(&(objectclass=user)(objectcategory=person))",
        "groups": "(objectclass=group)",
    },
    "openldap": {
        "users": "(objectclass=person)",
        "groups": "(objectclass=groupOfUniqueNames)",
    },
    "389directoryserver": {
        "users": "(objectclass=person)",
        "groups": "(objectclass=groupOfUniqueNames)",
    },
}


def logged_in_user_id() -> UserId | None:
    """LDAP user sync within a REST-API context can happen before the user session
    is created which would cause a crash when trying to get the logged in user id."""
    try:
        return logged_in_user.id
    except AttributeError:
        return None


class MKLDAPException(MKGeneralException):
    pass


LdapUsername = str  # the UserId, but after stripping the potential suffix


DistinguishedName = str
SearchResult = list[tuple[DistinguishedName, dict[str, list[str]]]]
GroupMemberships = dict[DistinguishedName, dict[str, str | list[str]]]
LDAPUserSpec = dict[str, list[str]]


# .
#   .--UserConnector-------------------------------------------------------.
#   | _   _                ____                            _               |
#   || | | |___  ___ _ __ / ___|___  _ __  _ __   ___  ___| |_ ___  _ __   |
#   || | | / __|/ _ \ '__| |   / _ \| '_ \| '_ \ / _ \/ __| __/ _ \| '__|  |
#   || |_| \__ \  __/ |  | |__| (_) | | | | | | |  __/ (__| || (_) | |     |
#   | \___/|___/\___|_|   \____\___/|_| |_|_| |_|\___|\___|\__\___/|_|     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This class realizes the ldap connection and communication            |
#   '----------------------------------------------------------------------'


def _get_ad_locator():
    import activedirectory  # type: ignore[import-untyped]
    from activedirectory.protocol import netlogon  # type: ignore[import-untyped]

    class FasterDetectLocator(activedirectory.Locator):  # type: ignore[misc]
        def _detect_site(self, domain):
            """Detect our site using the netlogon protocol.
            This modified function only changes the number of parallel queried servers from 3 to 60
            """
            self.m_logger.debug("detecting site")
            query = "_ldap._tcp.%s" % domain.lower()
            answer = self._dns_query(query, "SRV")
            servers = self._order_dns_srv(answer)
            addresses = self._extract_addresses_from_srv(servers)
            replies = []
            client = netlogon.Client()
            max_servers_parallel = 60
            for i in range(0, len(addresses), max_servers_parallel):
                for addr in addresses[i : i + max_servers_parallel]:
                    self.m_logger.debug("NetLogon query to %s", addr[0])
                    try:
                        client.query(addr, domain)
                    except Exception:
                        continue
                replies += client.call()
                self.m_logger.debug("%d replies", len(replies))
                if len(replies) >= 1:
                    break
            if not replies:
                self.m_logger.error("could not detect site")
                return None
            found_sites: dict[str, int] = {}
            for reply in replies:
                try:
                    found_sites[reply.client_site] += 1
                except KeyError:
                    found_sites[reply.client_site] = 1
            sites_list = [(value, key) for key, value in found_sites.items()]
            sites_list.sort()
            self.m_logger.debug("site detected as %s", sites_list[-1][1])
            return str(sites_list[0][1])

    return FasterDetectLocator()


def _show_exception(connection_id: str, title: str, e: Exception, debug: bool = True) -> None:
    try:
        html.show_error(
            "<b>" + connection_id + " - " + title + "</b>"
            "<pre>%s</pre>" % (debug and traceback.format_exc() or e)
        )
    except AttributeError:
        pass


class LDAPUserConnector(UserConnector[LDAPUserConnectionConfig]):
    # TODO: Move this to another place. We should have some managing object for this
    # stores the ldap connection suffixes of all connections
    connection_suffixes: dict[str, str] = {}

    def __init__(self, cfg: LDAPUserConnectionConfig) -> None:
        super().__init__(cfg)

        self._ldap_obj: ldap.ldapobject.ReconnectLDAPObject | None = None
        self._ldap_obj_config: LDAPUserConnectionConfig | None = None
        self._logger = log.logger.getChild("ldap.Connection(%s)" % self.id)

        self._num_queries = 0
        self._user_cache: dict[LdapUsername, tuple[str, LdapUsername]] = {}
        self._group_cache: dict = {}
        self._group_search_cache: dict = {}

        # File for storing the time of the last success event
        self._sync_time_file = Path(cmk.utils.paths.var_dir).joinpath(
            "web/ldap_%s_sync_time.mk" % self.id
        )

        self._save_suffix()

    @classmethod
    def type(cls) -> str:
        return ConnectorType.LDAP

    @classmethod
    def title(cls):
        return _("LDAP (Active Directory, OpenLDAP)")

    @classmethod
    def short_title(cls):
        return _("LDAP")

    @classmethod
    def get_connection_suffixes(cls):
        return cls.connection_suffixes

    @property
    def id(self):
        return self._config["id"]

    @property
    def customer_id(self) -> None | str:
        if "customer" not in self._config:
            return None
        return self._config["customer"]

    def connect_server(self, server: str) -> tuple[ldap.ldapobject.ReconnectLDAPObject, str | None]:
        """Connects to an LDAP server using the provided server uri"""
        try:
            # Set up debug logging if enabled
            if self._logger.isEnabledFor(logging.DEBUG):
                os.environ["GNUTLS_DEBUG_LEVEL"] = "99"
                ldap.set_option(ldap.OPT_DEBUG_LEVEL, 4095)
                trace_level = 2
                trace_file: IO[str] | None = sys.stderr
            else:
                trace_level = 0
                trace_file = None

            # Format the LDAP URI and create the connection object
            uri = self._format_ldap_uri(server)
            conn = ldap.ldapobject.ReconnectLDAPObject(
                uri, trace_level=trace_level, trace_file=trace_file
            )
            conn.protocol_version = self._config.get("version", 3)
            conn.network_timeout = self._config.get("connect_timeout", 2.0)
            conn.retry_delay = 0.5

            # When using the domain top level as base-dn, the subtree search stumbles with referral objects.
            # whatever. We simply disable them here when using active directory. Hope this fixes all problems.
            if self._is_active_directory():
                conn.set_option(ldap.OPT_REFERRALS, 0)

            if "use_ssl" in self._config:
                conn.set_option(ldap.OPT_X_TLS_CACERTFILE, str(cmk.utils.paths.trusted_ca_file))

                # Caused trouble on older systems or systems with some special configuration or set of
                # libraries. For example we saw a Ubuntu 17.10 system with libldap  2.4.45+dfsg-1ubuntu1 and
                # libgnutls30 3.5.8-6ubuntu3 raising "ValueError: option error" while another system with
                # the exact same liraries did not. Try to do this on systems that support this call and ignore
                # the errors on other systems.
                try:
                    conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
                except ValueError:
                    pass

            self._default_bind(conn)
            return conn, None

        except (ldap.SERVER_DOWN, ldap.TIMEOUT, ldap.LOCAL_ERROR, ldap.LDAPError) as e:
            self._clear_nearest_dc_cache()
            if hasattr(e, "message") and "desc" in e.message:
                msg = e.message["desc"]
            else:
                msg = "%s" % e

            return None, f"{uri}: {msg}"

        except MKLDAPException as e:
            self._clear_nearest_dc_cache()
            return None, "%s" % e

    def _format_ldap_uri(self, server: str) -> str:
        uri = "ldaps://" if self.use_ssl() else "ldap://"
        port_spec = ":%d" % self._config["port"] if "port" in self._config else ""
        srv = server[:-1] if server.endswith(".") else server
        return uri + srv + port_spec

    def connect(self, enforce_new: bool = False, enforce_server: str | None = None) -> None:
        if not enforce_new and self._ldap_obj and self._config == self._ldap_obj_config:
            self._logger.info("LDAP CONNECT - Using existing connecting")
            return  # Use existing connections (if connection settings have not changed)
        self._logger.info("LDAP CONNECT - Connecting...")
        self.disconnect()

        # Some major config var validations

        if not self._config["user_dn"]:
            raise MKLDAPException(
                _(
                    "The distinguished name of the container object, which holds "
                    "the user objects to be authenticated, is not configured. Please "
                    'fix this in the <a href="wato.py?mode=ldap_config">'
                    "LDAP User Settings</a>."
                )
            )

        try:
            errors = []
            if enforce_server:
                servers = [enforce_server]
            else:
                servers = self.servers()

            for server in servers:
                ldap_obj, error_msg = self.connect_server(server)

                if ldap_obj:
                    self._ldap_obj = ldap_obj
                else:
                    if error_msg is not None:  # it should be, though
                        errors.append(error_msg)
                    continue  # In case of an error, try the (optional) fallback servers

            # Got no connection to any server
            if self._ldap_obj is None:
                raise MKLDAPException(_("LDAP connection failed:\n%s") % ("\n".join(errors)))

            # on success, store the connection options the connection has been made with
            self._ldap_obj_config = copy.deepcopy(self._config)

        except Exception:
            # Invalidate connection on failure
            ldap_obj = None
            self.disconnect()
            raise

    def disconnect(self) -> None:
        self._ldap_obj = None
        self._ldap_obj_config = None

    def _discover_nearest_dc(self, domain: str) -> str:
        cached_server = self._get_nearest_dc_from_cache()
        if cached_server:
            self._logger.info("Using cached DC %s" % cached_server)
            return cached_server

        locator = _get_ad_locator()
        locator.m_logger = self._logger
        try:
            server = locator.locate(domain)
            self._cache_nearest_dc(server)
            self._logger.info(f"  DISCOVERY: Discovered server {server!r} from {domain!r}")
            return server
        except Exception:
            self._logger.info("  DISCOVERY: Failed to discover a server from domain %r" % domain)
            self._logger.exception("error discovering LDAP server")
            self._logger.info("  DISCOVERY: Try to use domain DNS name %r as server" % domain)
            return domain

    def _get_nearest_dc_from_cache(self) -> str | None:
        try:
            return self._nearest_dc_cache_filepath().open(encoding="utf-8").read()
        except OSError:
            pass
        return None

    def _cache_nearest_dc(self, server: str) -> None:
        self._logger.debug("Caching nearest DC %s" % server)
        store.save_text_to_file(self._nearest_dc_cache_filepath(), server)

    def _clear_nearest_dc_cache(self) -> None:
        if not self._uses_discover_nearest_server():
            return

        try:
            self._nearest_dc_cache_filepath().unlink()
        except OSError:
            pass

    def _nearest_dc_cache_filepath(self) -> Path:
        return self._ldap_caches_filepath() / ("nearest_server.%s" % self.id)

    @classmethod
    def _ldap_caches_filepath(cls) -> Path:
        return cmk.utils.paths.tmp_dir / "ldap_caches"

    @classmethod
    def config_changed(cls) -> None:
        cls._clear_all_ldap_caches()

    @classmethod
    def _clear_all_ldap_caches(cls) -> None:
        try:
            shutil.rmtree(str(cls._ldap_caches_filepath()))
        except FileNotFoundError:
            pass

    # Bind with the default credentials
    def _default_bind(self, conn: ldap.ldapobject.ReconnectLDAPObject | None) -> None:
        try:
            if "bind" in self._config:
                bind_dn, password_id = self._config["bind"]
                self._bind(
                    self._replace_macros(bind_dn),
                    password_id,
                    catch=False,
                    conn=conn,
                )
            else:
                self._bind("", ("password", ""), catch=False, conn=conn)  # anonymous bind
        except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH):
            raise MKLDAPException(
                _(
                    "Unable to connect to LDAP server with the configured bind credentials. "
                    "Please fix this in the "
                    '<a href="wato.py?mode=ldap_config">LDAP connection settings</a>.'
                )
            )

    def _bind(
        self,
        user_dn: str,
        password_id: password_store.PasswordId,
        catch: bool = True,
        conn: ldap.ldapobject.ReconnectLDAPObject | None = None,
    ) -> None:
        if conn is None:
            assert self._ldap_obj is not None
            conn = self._ldap_obj
        self._logger.info("LDAP_BIND %s" % user_dn)
        try:
            conn.simple_bind_s(user_dn, password_store.extract(password_id))
            self._logger.info("  SUCCESS")
        except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH):
            raise
        except ldap.LDAPError as e:
            self._logger.info(f"  FAILED ({e.__class__.__name__}: {e})")
            if catch:
                raise MKLDAPException(_("Unable to authenticate with LDAP (%s)") % e)
            raise

    def servers(self) -> list[str]:
        connect_params = self._get_connect_params()
        if self._uses_discover_nearest_server():
            servers = [self._discover_nearest_dc(connect_params["domain"])]
        else:
            servers = [connect_params["server"]] + connect_params.get("failover_servers", [])

        return servers

    def _uses_discover_nearest_server(self) -> bool:
        # 'directory_type': ('ad', {'connect_to': ('discover', {'domain': 'corp.de'})}),
        return self._config["directory_type"][1]["connect_to"][0] == "discover"

    def _get_connect_params(self):
        # 'directory_type': ('ad', {'connect_to': ('discover', {'domain': 'corp.de'})}),
        return self._config["directory_type"][1]["connect_to"][1]

    def use_ssl(self) -> bool:
        return "use_ssl" in self._config

    def active_plugins(self) -> ActivePlugins:
        return self._config["active_plugins"]

    def _active_sync_plugins(self) -> Iterator[tuple[str, dict[str, Any], LDAPAttributePlugin]]:
        plugins = dict(all_attribute_plugins())
        for key, params in self._config["active_plugins"].items():
            try:
                plugin = plugins[key]()
            except KeyError:
                continue
            if not params:
                params = {}
            if not isinstance(params, dict):
                raise TypeError(
                    _(
                        'The configuration of the LDAP attribute plugin "%s" is invalid. '
                        "Please check the configuration."
                    )
                    % key
                )
            yield key, params, plugin

    def _directory_type(self):
        return self._config["directory_type"][0]

    def _is_active_directory(self) -> bool:
        return self._directory_type() == "ad"

    def has_user_base_dn_configured(self) -> bool:
        return self._config["user_dn"] != ""

    def _create_users_only_on_login(self):
        return self._config.get("create_only_on_login", False)

    def _user_id_attr(self) -> str:
        return self._config.get("user_id", self._ldap_attr("user_id")).lower()

    def _member_attr(self) -> str:
        return self._config.get("group_member", self._ldap_attr("member")).lower()

    def has_bind_credentials_configured(self) -> bool:
        return self._config.get("bind", ("", ""))[0] != ""

    def has_group_base_dn_configured(self) -> bool:
        return self._config["group_dn"] != ""

    def get_group_dn(self) -> DistinguishedName:
        return self._replace_macros(self._config["group_dn"])

    def _get_user_dn(self) -> DistinguishedName:
        return self._replace_macros(self._config["user_dn"])

    def _get_suffix(self) -> str | None:
        return self._config.get("suffix")

    def _has_suffix(self) -> bool:
        return self._config.get("suffix") is not None

    def _save_suffix(self) -> None:
        suffix = self._get_suffix()
        if suffix:
            if (
                suffix in LDAPUserConnector.connection_suffixes
                and LDAPUserConnector.connection_suffixes[suffix] != self.id
            ):
                raise MKUserError(
                    None,
                    _(
                        "Found duplicate LDAP connection suffix. "
                        "The LDAP connections %s and %s both use "
                        "the suffix %s which is not allowed."
                    )
                    % (LDAPUserConnector.connection_suffixes[suffix], self.id, suffix),
                )
            LDAPUserConnector.connection_suffixes[suffix] = self.id

    def _needed_attributes(self) -> list[str]:
        """Returns a list of all needed LDAP attributes of all enabled plugins"""
        attrs: set[str] = set()
        for _key, params, plugin in self._active_sync_plugins():
            attrs.update(plugin.needed_attributes(self, params))
        return list(attrs)

    def _object_exists(self, dn: DistinguishedName) -> bool:
        try:
            return bool(self._ldap_search(dn, columns=["dn"], scope="base"))
        except Exception:
            return False

    def user_base_dn_exists(self) -> bool:
        return self._object_exists(self._get_user_dn())

    def group_base_dn_exists(self) -> bool:
        return self._object_exists(self.get_group_dn())

    def _ldap_paged_async_search(
        self,
        base: DistinguishedName,
        scope: str,
        filt: str,
        columns: Sequence[str],
    ) -> list[tuple[str, dict[str, list[bytes]]]]:
        self._logger.info("  PAGED ASYNC SEARCH")
        page_size = self._config.get("page_size", 1000)

        lc = SimplePagedResultsControl(size=page_size, cookie="")

        results = []
        while True:
            # issue the ldap search command (async)
            assert self._ldap_obj is not None
            msgid = self._ldap_obj.search_ext(
                _escape_dn(base), scope, filt, columns, serverctrls=[lc]
            )
            unused_code, response, unused_msgid, serverctrls = self._ldap_obj.result3(
                msgid=msgid, timeout=self._config.get("response_timeout", 5)
            )

            for result in response:
                results.append(result)

            # Mark current position in pagination control for next loop
            cookie = None
            for serverctrl in serverctrls:
                if serverctrl.controlType == ldap.CONTROL_PAGEDRESULTS:
                    cookie = serverctrl.cookie
                    if cookie:
                        lc.cookie = cookie
                    break
            if not cookie:
                break
        return results

    def _ldap_search(
        self,
        base: DistinguishedName,
        filt: str = "(objectclass=*)",
        columns: Sequence[str] | None = None,
        scope: str = "sub",
        implicit_connect: bool = True,
    ) -> list[tuple[str, dict[str, list[str]]]]:
        if columns is None:
            columns = []

        self._logger.info(f'LDAP_SEARCH "{base}" "{scope}" "{filt}" "{columns!r}"')
        self._num_queries += 1
        start_time = time.time()

        # In some environments, the connection to the LDAP server does not seem to
        # be as stable as it is needed. So we try to repeat the query for three times.
        # -> Don't retry when implicit connect is disabled
        tries_left = 2
        success = False
        last_exc = None
        while not success:
            tries_left -= 1
            try:
                if implicit_connect:
                    self.connect()

                result = []
                try:
                    for dn, obj in self._ldap_paged_async_search(
                        base, self._ldap_get_scope(scope), filt, columns
                    ):
                        if dn is None:
                            continue  # skip unwanted answers
                        new_obj = {}
                        for key, val in obj.items():
                            new_obj[key.lower()] = [v.decode("utf-8") for v in val]
                        result.append((dn.lower(), new_obj))
                    success = True
                except ldap.NO_SUCH_OBJECT as e:
                    raise MKLDAPException(
                        _('The given base object "%s" does not exist in LDAP (%s))') % (base, e)
                    )

                except ldap.FILTER_ERROR as e:
                    raise MKLDAPException(
                        _('The given ldap filter "%s" is invalid (%s)') % (filt, e)
                    )

                except ldap.SIZELIMIT_EXCEEDED:
                    raise MKLDAPException(
                        _(
                            "The response reached a size limit. This could be due to "
                            "a sizelimit configuration on the LDAP server.<br />Throwing away the "
                            "incomplete results. You should change the scope of operation "
                            "within the ldap or adapt the limit settings of the LDAP server."
                        )
                    )
            except (ldap.SERVER_DOWN, ldap.TIMEOUT, MKLDAPException) as e:
                self._clear_nearest_dc_cache()

                last_exc = e
                if implicit_connect and tries_left:
                    self._logger.info("  Received %r. Retrying with clean connection..." % e)
                    self.disconnect()
                    time.sleep(0.5)
                else:
                    self._logger.info("  Giving up.")
                    break

        duration = time.time() - start_time

        if not success:
            self._logger.info("  FAILED")
            if active_config.debug:
                raise MKLDAPException(
                    _(
                        "Unable to successfully perform the LDAP search "
                        "(Base: %s, Scope: %s, Filter: %s, Columns: %s): %s"
                    )
                    % (
                        escaping.escape_attribute(base),
                        escaping.escape_attribute(scope),
                        escaping.escape_attribute(filt),
                        escaping.escape_attribute(",".join(columns)),
                        last_exc,
                    )
                )
            raise MKLDAPException(
                _("Unable to successfully perform the LDAP search (%s)") % last_exc
            )

        self._logger.info("  RESULT length: %d, duration: %0.3f" % (len(result), duration))
        return result

    def _ldap_get_scope(self, scope):
        # Had "subtree" in Checkmk for several weeks. Better be compatible to both definitions.
        if scope in ["sub", "subtree"]:
            return ldap.SCOPE_SUBTREE
        if scope == "base":
            return ldap.SCOPE_BASE
        if scope == "one":
            return ldap.SCOPE_ONELEVEL
        raise Exception("Invalid scope specified: %s" % scope)

    # Returns the ldap filter depending on the configured ldap directory type
    def _ldap_filter(self, key: str, handle_config: bool = True) -> str:
        value = ldap_filter_map[self._directory_type()].get(key, "(objectclass=*)")
        if handle_config:
            if key == "users":
                value = self._config.get("user_filter", value)
            elif key == "groups":
                value = self._config.get("group_filter", value)
        return self._replace_macros(value)

    # Returns the ldap attribute name depending on the configured ldap directory type
    # If a key is not present in the map, the assumption is, that the key matches 1:1
    # Always use lower case here, just to prevent confusions.
    def _ldap_attr(self, key):
        return ldap_attr_map[self._directory_type()].get(key, key).lower()

    # Returns the given distinguished name template with replaced vars
    def _replace_macros(self, tmpl: str) -> str:
        return replace_macros_in_str(tmpl, {"$OMD_SITE$": omd_site() or ""})

    def _sanitize_user_id(self, user_id: str) -> UserId:
        if self._config.get("lower_user_ids", False):
            user_id = user_id.lower()

        umlauts = self._config.get("user_id_umlauts", "keep")

        # Be compatible to old user_id umlaut replacement. These days user_ids support special
        # characters, so the replacement would not be needed anymore. But we keep this for
        # compatibility reasons. FIXME TODO Remove this one day.
        if umlauts == "replace":
            user_id = user_id.translate(
                {
                    ord("ü"): "ue",
                    ord("ö"): "oe",
                    ord("ä"): "ae",
                    ord("ß"): "ss",
                    ord("Ü"): "UE",
                    ord("Ö"): "OE",
                    ord("Ä"): "AE",
                    ord("å"): "aa",
                    ord("Å"): "Aa",
                    ord("Ø"): "Oe",
                    ord("ø"): "oe",
                    ord("Æ"): "Ae",
                    ord("æ"): "ae",
                }
            )

        return UserId(user_id)

    def _get_user(
        self, username: LdapUsername, no_escape: bool = False
    ) -> tuple[str, LdapUsername] | None:
        if username in self._user_cache:
            return self._user_cache[username]

        user_id_attr = self._user_id_attr()

        # Check whether or not the user exists in the directory matching the username AND
        # the user search filter configured in the "LDAP User Settings".
        # It's only ok when exactly one entry is found. Returns the DN and user_id
        # as tuple in this case.
        result = self._ldap_search(
            self._get_user_dn(),
            "(&(%s=%s)%s)"
            % (
                user_id_attr,
                ldap.filter.escape_filter_chars(username),
                self._config.get("user_filter", ""),
            ),
            [user_id_attr],
            self._config["user_scope"],
        )

        if not result:
            return None

        dn = result[0][0]
        raw_user_id = result[0][1][user_id_attr][0]

        # Filter out users by the optional filter_group
        filter_group_dn = self._config.get("user_filter_group", None)
        if filter_group_dn:
            member_attr = self._member_attr()
            is_member = False
            for member in self._get_filter_group_members(filter_group_dn):
                if member_attr == "memberuid" and raw_user_id == member:
                    is_member = True
                elif dn == member:
                    is_member = True

            if not is_member:
                return None

        user_id = self._sanitize_user_id(raw_user_id)
        if user_id is None:
            return None
        self._user_cache[username] = (dn, user_id)

        if no_escape:
            return (dn, user_id)
        return (dn.replace("\\", "\\\\"), user_id)

    def get_users(self, add_filter: str = "") -> dict[UserId, LDAPUserSpec]:
        user_id_attr = self._user_id_attr()

        columns = [
            user_id_attr,  # needed in all cases as uniq id
        ] + self._needed_attributes()

        filt = self._ldap_filter("users")

        # Create filter by the optional filter_group
        filter_group_dn = self._config.get("user_filter_group", None)
        if filter_group_dn:
            member_attr = self._member_attr()
            # posixGroup objects use the memberUid attribute to specify the group memberships.
            # This is the username instead of the users DN. So the username needs to be used
            # for filtering here.
            user_cmp_attr = user_id_attr if member_attr == "memberuid" else "distinguishedname"

            member_filter_items = []
            for member in self._get_filter_group_members(filter_group_dn):
                member_filter_items.append(
                    "(%s=%s)"
                    % (
                        user_cmp_attr,
                        ldap.filter.escape_filter_chars(
                            _escape_dn(member) if member_attr == "distinguishedname" else member
                        ),
                    )
                )
            add_filter += "(|%s)" % "".join(member_filter_items)

        if add_filter:
            filt = f"(&{filt}{add_filter})"

        result = {}
        for dn, ldap_user in self._ldap_search(
            self._get_user_dn(), filt, columns, self._config["user_scope"]
        ):
            if user_id_attr not in ldap_user:
                raise MKLDAPException(
                    _('The configured User-ID attribute "%s" does not exist for the user "%s"')
                    % (user_id_attr, dn)
                )

            try:
                user_id = self._sanitize_user_id(ldap_user[user_id_attr][0])
            except ValueError as e:
                self._logger.warning(f"  SKIP SYNC {e}")
                continue

            if user_id:
                result[user_id] = cast(LDAPUserSpec, ldap_user)
                result[user_id]["dn"] = [dn]  # also add the DN

        return result

    def get_groups(self, specific_dn: DistinguishedName | None = None) -> SearchResult:
        filt = self._ldap_filter("groups")
        dn = self.get_group_dn()

        if specific_dn:
            # When using AD, the groups can be filtered by the DN attribute. With
            # e.g. OpenLDAP this is not possible. In that case, change the DN.
            if self._is_active_directory():
                filt = f"(&{filt}(distinguishedName={ldap.filter.escape_filter_chars(_escape_dn(specific_dn))}))"
            else:
                dn = specific_dn

        return self._ldap_search(dn, filt, ["cn"], self._config["group_scope"])

    # TODO: Use get_group_memberships()?
    def _get_filter_group_members(self, filter_group_dn: DistinguishedName) -> list[str]:
        member_attr = self._member_attr()

        try:
            group = self._ldap_search(
                self._replace_macros(filter_group_dn),
                columns=[member_attr],
                scope="base",
            )
        except MKLDAPException:
            group = None

        if not group:
            raise MKLDAPException(
                _(
                    "The configured ldap user filter group could not be found. "
                    'Please check <a href="%s">your configuration</a>.'
                )
                % "wato.py?mode=ldap_config&varname=ldap_userspec"
            )

        return [m.lower() for m in list(group[0][1].values())[0]]

    def _get_group_memberships(
        self, filters: Sequence[str], filt_attr: str = "cn", nested: bool = False
    ) -> GroupMemberships:
        cache_key = (tuple(filters), nested, filt_attr)
        if cache_key in self._group_search_cache:
            return self._group_search_cache[cache_key]

        self._group_cache.setdefault(nested, {})

        if not nested:
            groups = self._get_direct_group_memberships(filters, filt_attr)
        else:
            groups = self._get_nested_group_memberships(filters, filt_attr)

        self._group_search_cache[cache_key] = groups
        return groups

    # When not searching for nested memberships, it is easy when using the an AD base LDAP.
    # The group objects can be queried using the attribute distinguishedname. Therefor we
    # create an alternating match filter to match that attribute when searching by DNs.
    # In OpenLDAP the distinguishedname is no user attribute, therefor it can not be used
    # as filter expression. We have to do one ldap query per group. Maybe, in the future,
    # we change the role sync plug-in parameters to snap-ins to make this part a little easier.
    def _get_direct_group_memberships(
        self, filters: Sequence[str], filt_attr: str
    ) -> GroupMemberships:
        groups: GroupMemberships = {}
        filt = self._ldap_filter("groups")
        member_attr = self._member_attr()

        if self._is_active_directory() or filt_attr != "distinguishedname":
            if filters:
                add_filt = "(|%s)" % "".join(
                    [
                        "(%s=%s)"
                        % (
                            filt_attr,
                            ldap.filter.escape_filter_chars(
                                _escape_dn(f) if filt_attr == "distinguishedname" else f
                            ),
                        )
                        for f in filters
                    ]
                )
                filt = f"(&{filt}{add_filt})"

            for dn, obj in self._ldap_search(
                self.get_group_dn(), filt, ["cn", member_attr], self._config["group_scope"]
            ):
                groups[_unescape_dn(dn)] = {
                    "cn": obj["cn"][0],
                    "members": sorted([m.lower() for m in obj.get(member_attr, [])]),
                }
        else:
            # Special handling for OpenLDAP when searching for groups by DN
            for f_dn in filters:
                # Try to get members from group cache
                try:
                    groups[f_dn] = self._group_cache[False][f_dn]
                    continue
                except KeyError:
                    pass

                for dn, obj in self._ldap_search(
                    self._replace_macros(f_dn), filt, ["cn", member_attr], "base"
                ):
                    groups[f_dn] = {
                        "cn": obj["cn"][0],
                        "members": sorted([m.lower() for m in obj.get(member_attr, [])]),
                    }

        self._group_cache[False].update(groups)

        return groups

    # Nested querying is more complicated. We have no option to simply do a query for group objects
    # to make them resolve the memberships here. So we need to query all users with the nested
    # memberof filter to get all group memberships of that group. We need one query for each group.
    def _get_nested_group_memberships(
        self,
        filters: Sequence[str],
        filt_attr: str,
    ) -> GroupMemberships:
        groups: GroupMemberships = {}

        # Search group members in common ancestor of group and user base DN to be able to use a single
        # query instead of one for groups and one for users below when searching for the members.
        base_dn = self._group_and_user_base_dn()

        for filter_val in filters:
            matched_groups: dict[str, str | None] = {}

            # The memberof query below is only possible when knowing the DN of groups. We need
            # to look for the DN when the caller gives us CNs (e.g. when using the the groups
            # to contact groups plugin).
            if filt_attr == "cn":
                result = self._ldap_search(
                    self.get_group_dn(),
                    f"(&{self._ldap_filter('groups')}(cn={ldap.filter.escape_filter_chars(filter_val)}))",
                    ["dn", "cn"],
                    self._config["group_scope"],
                )
                if not result:
                    continue  # Skip groups which can not be found

                for dn, attrs in result:
                    matched_groups[dn] = attrs["cn"][0]
            else:
                # in case of asking with DNs in nested mode, the resulting objects have the
                # cn set to None for all objects. We do not need it in that case.
                dn = filter_val
                matched_groups[dn] = None

            # Now lookup the memberships. Previously we used the filter "memberOf:1.2.840.113556.1.4.1941:"
            # here which seemed to be a performance problem. Resolving the nesting involves more single
            # queries but performs much better.
            for dn, cn in matched_groups.items():
                # Avoid double escaping:
                # self._ldap_search escapes the 'dn' but here we've got already escaped 'dn', ie.
                # >>> s = u'cn=#my cn,ou=my_groups,ou=my_u,dc=my_dc,dc=my_dc'
                # >>> s = s.replace("#", r"\#")
                # u'cn=\\#my cn,ou=my_groups,ou=my_u,dc=my_dc,dc=my_dc'
                # >>> s = s.replace("#", r"\#")
                # u'cn=\\\\#my cn,ou=my_groups,ou=my_u,dc=my_dc,dc=my_dc'
                # => Results in 'No such object'
                dn = _unescape_dn(dn)

                # Try to get members from group cache
                try:
                    groups[dn] = self._group_cache[True][dn]
                    continue
                except KeyError:
                    pass

                # In case we don't have the cn we need to fetch it. It may be needed, e.g. by the contact group
                # sync plugin
                if cn is None:
                    group = self._ldap_search(
                        dn, filt="(objectclass=group)", columns=["cn"], scope="base"
                    )
                    if group:
                        cn = group[0][1]["cn"][0]
                assert cn is not None

                filt = "(memberof=%s)" % ldap.filter.escape_filter_chars(_escape_dn(dn))
                groups[dn] = {
                    "members": [],
                    "cn": cn,
                }

                members = groups[dn]["members"]
                assert isinstance(members, list)

                # Register the group construct, collect the members later. This way we can also
                # catch the case where a group refers to itself, which is prevented by some LDAP
                # editing tools, like "Active Directory Users & Computers", but can somehow be
                # configured, e.g. when configuring universal distribution lists using ADSIEdit
                # it was possible to configure something like this at least in older directories.
                self._group_cache[True][dn] = groups[dn]

                sub_group_filters = []
                for obj_dn, obj in self._ldap_search(base_dn, filt, ["dn", "objectclass"], "sub"):
                    if "user" in obj["objectclass"]:
                        members.append(obj_dn)

                    elif "group" in obj["objectclass"]:
                        sub_group_filters.append(obj_dn)

                # TODO: This could be optimized by first collecting all sub groups of all searched
                # groups, then collecting them all together
                for _sub_group_dn, sub_group in self._get_group_memberships(
                    sub_group_filters, filt_attr="dn", nested=True
                ).items():
                    members += sub_group["members"]

                members.sort()

        return groups

    def _group_and_user_base_dn(self) -> str:
        user_dn = ldap.dn.str2dn(self._get_user_dn())
        group_dn = ldap.dn.str2dn(self.get_group_dn())

        common_len = min(len(user_dn), len(group_dn))
        user_dn, group_dn = user_dn[-common_len:], group_dn[-common_len:]

        base_dn = None
        for i in range(common_len):
            if user_dn[i:] == group_dn[i:]:
                base_dn = user_dn[i:]
                break

        if base_dn is None:
            raise MKLDAPException(
                _(
                    "Unable to synchronize nested groups (Found no common base DN for user base "
                    'DN "%s" and group base DN "%s")'
                )
                % (self._get_user_dn(), self.get_group_dn())
            )

        return ldap.dn.dn2str(base_dn)

    def create_ldap_user_on_login(self, userid: UserId, existing_users: Users) -> None:
        new_user = self._create_checkmk_user_for_this_ldap_connection(userid, existing_users)
        existing_users[userid] = new_user
        save_users(existing_users, datetime.now())

        try:
            # logged_in_user_id() can return None when a user is created on login
            # via the REST-API.
            log_security_event(
                UserManagementEvent(
                    event="user created",
                    affected_user=userid,
                    acting_user=logged_in_user_id(),
                    connector=self.type(),
                    connection_id=self.id,
                )
            )

            self.do_sync(
                add_to_changelog=False,
                only_username=userid,
                load_users_func=load_users,
                save_users_func=save_users,
            )

            # When a user is created on login via the REST-API, the user may or may not
            # be authorized for the request that triggered the user creation. If they
            # are authorized, the active_config.multisite_users has not yet been updated
            # when the response is formed. So we need to update it here.
            active_config.multisite_users[userid] = new_user

        except MKLDAPException as e:
            _show_exception(self.id, _("Error during sync"), e, debug=active_config.debug)
        except Exception as e:
            _show_exception(self.id, _("Error during sync"), e)

    def get_matching_user_profile(self, user_id: UserId) -> UserId | None:
        """This function will try to match an existing user profile, or create a new one if
        it doesn't exist yet. If no user_id can be matched/created, return None."""
        existing_users = load_users(lock=True)

        def get_user_id_create_user_if_neccessary(user_id_to_check: UserId) -> UserId | None:
            if (user_from_config := existing_users.get(user_id_to_check, None)) is None:
                self.create_ldap_user_on_login(user_id_to_check, existing_users)
                return user_id_to_check
            return user_id_to_check if user_from_config.get("connector") == self.id else None

        matched_user_id = get_user_id_create_user_if_neccessary(user_id)
        if matched_user_id is None and self._has_suffix():
            return get_user_id_create_user_if_neccessary(UserId(f"{user_id}@{self._get_suffix()}"))

        return matched_user_id

    #
    # USERDB API METHODS
    #

    # This function only validates credentials, no locked checking or similar
    def check_credentials(self, user_id: UserId, password: Password) -> CheckCredentialsResult:
        # Connect only to servers of connections, the user is configured for,
        # to avoid connection errors for unrelated servers
        user_connection_id = self._connection_id_of_user(user_id)

        if user_connection_id is not None and user_connection_id != self.id:
            return None

        try:
            self.connect()
        except Exception:
            self._logger.exception("Failed to connect to LDAP:")
            # Could not connect to any of the LDAP servers, or unknown error. Skip this connection.
            return None

        enforce_this_connection = None
        # Also honor users that are currently not known, e.g. when sync did not
        # already happened
        if user_connection_id is None:
            # Did the user provide an suffix with his user_id? This might enforce
            # LDAP connections to be choosen or skipped.
            # self._user_enforces_this_connection can return either:
            #   True:  This connection is enforced
            #   False: Another connection is enforced
            #   None:  No connection is enforced
            enforce_this_connection = self._user_enforces_this_connection(user_id)
            if enforce_this_connection is False:
                return None  # Skip this connection, another one is enforced
        # Always use the stripped user ID for communication with the LDAP server
        ldap_user_id = self._strip_suffix(user_id)

        # Returns None when the user is not found or not uniq, else returns the
        # distinguished name and the ldap_user_id as tuple which are both needed for
        # the further login process.
        fetch_user_result = self._get_user(ldap_user_id, True)
        if not fetch_user_result:
            # The user does not exist
            if enforce_this_connection:
                return False  # Refuse login
            return None  # Try next connection (if available)

        user_dn, ldap_user_id = fetch_user_result

        # Try to bind with the user provided credentials. This unbinds the default
        # authentication which should be rebound again after trying this.
        try:
            self._bind(user_dn, ("password", password.raw))
            userid = self.get_matching_user_profile(UserId(ldap_user_id))
            result: CheckCredentialsResult = False if userid is None else userid
        except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH) as e:
            self._logger.warning(
                "Unable to authenticate user %s. Reason: %s", user_id, e.args[0].get("desc", e)
            )
            result = False
        except Exception:
            self._logger.exception("  Exception during authentication (User: %s)", user_id)
            result = False

        self._default_bind(self._ldap_obj)
        return result

    def _connection_id_of_user(self, user_id: UserId) -> str | None:
        if not Path.exists(cmk.utils.paths.profile_dir / user_id):
            return None

        user = load_cached_profile(user_id)
        if user is None:
            return None
        return user.get("connector")

    def _user_enforces_this_connection(self, username: UserId) -> bool | None:
        matched_connection_ids = []
        for suffix, connection_id in LDAPUserConnector.get_connection_suffixes().items():
            if self._username_matches_suffix(username, suffix):
                matched_connection_ids.append(connection_id)

        if not matched_connection_ids:
            return None
        if len(matched_connection_ids) > 1:
            raise MKUserError(None, _("Unable to match connection"))
        return matched_connection_ids[0] == self.id

    def _username_matches_suffix(self, username: UserId, suffix: str) -> bool:
        return username.endswith("@" + suffix)

    def _strip_suffix(self, username: UserId) -> LdapUsername:
        suffix = self._get_suffix()
        if suffix and self._username_matches_suffix(username, suffix):
            return username[: -(len(suffix) + 1)]
        return username

    def _add_suffix(self, username: LdapUsername) -> UserId:
        suffix = self._get_suffix()
        if username.endswith(f"@{suffix}"):
            return UserId(username)
        return UserId(f"{username}@{suffix}")

    def _set_customer_for_user(self, user: UserSpec) -> None:
        if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CME:
            user["customer"] = self._config.get("customer", customer_api().default_customer_id())

    def _create_checkmk_user_for_this_ldap_connection(
        self,
        new_user_id: UserId,
        existing_users: Users,
    ) -> UserSpec:
        if new_user_id in existing_users:
            raise MKUserError(
                None,
                _("The user id '%s' already exists") % new_user_id,
            )
        new_user = new_user_template(self.id)
        self._set_customer_for_user(new_user)
        new_user.setdefault("alias", new_user_id)
        add_internal_attributes(new_user)
        return new_user

    def _remove_checkmk_users_that_are_no_longer_in_the_ldap_instance(
        self,
        users: Users,
        ldap_users: dict[UserId, LDAPUserSpec],
    ) -> list[str]:
        changes = []
        for user_id, user in list(users.items()):
            user_connection_id = user.get("connector")
            if user_connection_id == self.id and self._strip_suffix(user_id) not in ldap_users:
                del users[user_id]  # remove the user
                changes.append(_("LDAP [%s]: Removed user %s") % (self.id, user_id))
                # When a user is created on login via the REST-API, and then we do the
                # user sync, logged_in_user_id() can return None.
                log_security_event(
                    UserManagementEvent(
                        event="user deleted",
                        affected_user=user_id,
                        acting_user=logged_in_user_id(),
                        connector=self.type(),
                        connection_id=self.id,
                    )
                )
        return changes

    def do_sync(
        self,
        *,
        add_to_changelog: bool,  # unused
        only_username: UserId | None,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        if not self.has_user_base_dn_configured():
            self._logger.info('Not trying sync (no "user base DN" configured)')
            return  # silently skip sync without configuration

        # Flush ldap related before each sync to have a caching only for the
        # current sync process
        self._flush_caches()

        start_time = time.time()

        self._logger.info("SYNC STARTED")
        self._logger.info("  SYNC PLUGINS: %s" % ", ".join(self._config["active_plugins"].keys()))

        ldap_users = self.get_users()

        users = load_users_func(True)  # too lazy to add a protocol for the "lock" kwarg...

        def load_existing_user(uid: UserId) -> tuple[UserId, UserSpec] | None:
            if uid in users and users[uid].get("connector") == self.id:
                return uid, copy.deepcopy(users[uid])

            if self._has_suffix():
                userid_with_suffix = self._add_suffix(uid)
                if (
                    userid_with_suffix in users
                    and users[userid_with_suffix].get("connector") == self.id
                ):
                    return userid_with_suffix, copy.deepcopy(users[userid_with_suffix])
            return None

        def create_temp_user(uid: UserId) -> tuple[UserId, UserSpec] | None:
            if uid not in users:
                return uid, self._create_checkmk_user_for_this_ldap_connection(uid, users)

            user_id_with_suffix = self._add_suffix(uid)
            if self._has_suffix() and user_id_with_suffix not in users:
                return user_id_with_suffix, self._create_checkmk_user_for_this_ldap_connection(
                    user_id_with_suffix, users
                )

            return None

        def get_checkmk_user_for_this_ldap_user_id(uid: UserId) -> tuple[bool, UserId, UserSpec]:
            if (userid_and_user := load_existing_user(uid)) is not None:
                user_id, user = userid_and_user
                return False, user_id, user

            if (userid_and_new_user := create_temp_user(uid)) is not None:
                user_id, user = userid_and_new_user
                return True, user_id, user

            raise CantSyncLDAPUserException(
                f"Could not find an existing user or create a new user for the ldap user: '{uid}' with the user_connection_id: '{self.id}'",
            )

        changes = self._remove_checkmk_users_that_are_no_longer_in_the_ldap_instance(
            users=users,
            ldap_users=ldap_users,
        )

        has_changed_passwords = False
        profiles_to_synchronize = {}
        if self.id not in [connection[0] for connection in active_connections()]:
            self._logger.info('  SKIP SYNC connector "%s" is disabled', self.id)
            return

        for ldap_user_id, ldap_user in ldap_users.items():
            try:
                mode_create, checkmk_user_id, checkmk_user = get_checkmk_user_for_this_ldap_user_id(
                    ldap_user_id
                )
            except CantSyncLDAPUserException:
                cant_sync_msg = (
                    '  SKIP SYNC "{}" name conflict with user from "{}" connector.'.format(
                        ldap_user_id,
                        self.id,
                    )
                )
                if not self._has_suffix():
                    cant_sync_msg += " A suffix should be added to this connector."
                self._logger.info(cant_sync_msg)
                continue

            if self._create_users_only_on_login() and mode_create:
                self._logger.info(
                    f'  SKIP SYNC "{checkmk_user_id}" (Only create user of "{self.id}" connector on login)'
                )
                continue

            if only_username and checkmk_user_id != only_username:
                continue  # Only one user should be synced, skip others.

            self._execute_active_sync_plugins(checkmk_user_id, ldap_user, checkmk_user)

            if not mode_create and checkmk_user == users[checkmk_user_id]:
                continue  # no modification. Skip this user.

            # Gather changed attributes for easier debugging
            if not mode_create:
                set_new, set_old = set(checkmk_user.keys()), set(users[checkmk_user_id].keys())
                intersect = set_new.intersection(set_old)
                added = set_new - intersect
                removed = set_old - intersect

                changed = self._find_changed_user_keys(
                    intersect, users[checkmk_user_id], checkmk_user
                )

            users[checkmk_user_id] = checkmk_user
            if mode_create:
                changes.append(_("LDAP [%s]: Created user %s") % (self.id, checkmk_user_id))
                log_security_event(
                    UserManagementEvent(
                        event="user created",
                        affected_user=checkmk_user_id,
                        acting_user=logged_in_user.id,
                        connector=self.type(),
                        connection_id=self.id,
                    )
                )
            else:
                details = []
                if added:
                    details.append(_("Added: %s") % ", ".join(added))
                if removed:
                    details.append(_("Removed: %s") % ", ".join(removed))
                if added or removed or changed:
                    # When a user is created on login via the REST-API, and then we do the
                    # user sync, logged_in_user_id() can return None.
                    log_security_event(
                        UserManagementEvent(
                            event="user modified",
                            affected_user=checkmk_user_id,
                            acting_user=logged_in_user_id(),
                            connector=self.type(),
                            connection_id=self.id,
                        )
                    )
                # Password changes found in LDAP should not be logged as "pending change".
                # These changes take effect imediately (pw already changed in AD, auth serial
                # is increaed by sync plugin) on the local site, so no one needs to active this.
                pw_changed = False
                if "ldap_pw_last_changed" in changed:
                    del changed["ldap_pw_last_changed"]
                    pw_changed = True
                if "serial" in changed:
                    del changed["serial"]
                    pw_changed = True

                if pw_changed:
                    has_changed_passwords = True

                # Synchronize new user profile to remote sites if needed
                if pw_changed and not changed and has_wato_slave_sites():
                    profiles_to_synchronize[checkmk_user_id] = checkmk_user

                if changed:
                    for key, (old_value, new_value) in sorted(changed.items()):
                        details.append(_("Changed %s from %s to %s") % (key, old_value, new_value))

                if details:
                    changes.append(
                        _("LDAP [%s]: Modified user %s (%s)")
                        % (self.id, checkmk_user_id, ", ".join(details))
                    )

        try:
            hooks.call("ldap-sync-finished", self._logger, profiles_to_synchronize, changes)
        except AttributeError:
            # The hooks can fail if a user is created on login via the REST-API and is then
            # modified by the ldap sync process but the user has been updated correctly.
            pass

        duration = time.time() - start_time
        self._logger.info(
            "SYNC FINISHED - Duration: %0.3f sec, Queries: %d" % (duration, self._num_queries)
        )

        if changes or has_changed_passwords:
            save_users_func(users, datetime.now())
        else:
            release_users_lock()

        self._set_last_sync_time()

    def _find_changed_user_keys(self, keys: set[str], user: Mapping, new_user: Mapping) -> dict:
        changed = {}
        for key in keys:
            # Skip user notification rules, not relevant here
            if key == "notification_rules":
                continue
            value = user[key]
            new_value = new_user[key]
            if isinstance(value, list) and isinstance(new_value, list):
                is_changed = sorted(value) != sorted(new_value)
            else:
                is_changed = value != new_value
            if is_changed:
                changed[key] = (value, new_value)
        return changed

    def _execute_active_sync_plugins(
        self, user_id: UserId, ldap_user: LDAPUserSpec, user: UserSpec
    ) -> None:
        for key, params, plugin in self._active_sync_plugins():
            # sync_func doesn't expect UserSpec yet. In fact, it will access some LDAP-specific
            # attributes that aren't defined by UserSpec.
            user.update(plugin.sync_func(self, key, params, user_id, ldap_user, user))  # type: ignore[arg-type, typeddict-item]

    def _flush_caches(self):
        self._num_queries = 0
        self._user_cache.clear()
        self._group_cache.clear()
        self._group_search_cache.clear()

    def _set_last_sync_time(self) -> None:
        with self._sync_time_file.open("w", encoding="utf-8") as f:
            f.write("%s\n" % time.time())

    def is_enabled(self) -> bool:
        sync_config = user_sync_config()
        if isinstance(sync_config, tuple) and self.id not in sync_config[1]:
            # self._ldap_logger('Skipping disabled connection %s' % (self.id))
            return False
        return True

    def sync_is_needed(self) -> bool:
        return self._get_last_sync_time() + self._get_cache_livetime() <= time.time()

    def _get_last_sync_time(self) -> float:
        try:
            with self._sync_time_file.open(encoding="utf-8") as f:
                return float(f.read().strip())
        except Exception:
            return 0

    def _get_cache_livetime(self):
        return self._config["cache_livetime"]

    # Calculates the attributes of the users which are locked for users managed
    # by this connector
    def locked_attributes(self) -> Sequence[str]:
        locked = {"password"}  # This attributes are locked in all cases!
        for _key, params, plugin in self._active_sync_plugins():
            locked.update(plugin.lock_attributes(params))
        return list(locked)

    # Calculates the attributes added in this connector which shal be written to
    # the multisites users.mk
    def multisite_attributes(self) -> list[str]:
        attrs: set[str] = set()
        for _key, _params, plugin in self._active_sync_plugins():
            attrs.update(plugin.multisite_attributes)
        return list(attrs)

    # Calculates the attributes added in this connector which shal NOT be written to
    # the check_mks contacts.mk
    def non_contact_attributes(self) -> list[str]:
        attrs: set[str] = set()
        for _key, _params, plugin in self._active_sync_plugins():
            attrs.update(plugin.non_contact_attributes)
        return list(attrs)


def _escape_dn(dn):
    """Handle "#" in DNs (as allowed by Active Directory)

    This is obviously not a full featured escaping function for the DNs. This
    might be ldap.dn.escape_dn_chars for the single component parts of the DN.
    It might also be a good way to use ldap.dn.str2dn/dn2str to really parse
    the DN and ensure it is a valid one. But this is nothing for a small bug
    fix in the current stable.
    """
    return dn.replace("#", r"\#")


def _unescape_dn(dn):
    """Inverse of _escape_dn()"""
    return dn.replace(r"\#", "#")


# .
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The LDAP User Connector provides some kind of plug-in mechanism to    |
#   | modulize which ldap attributes are synchronized and how they are     |
#   | synchronized into Checkmk. The standard attribute plug-ins           |
#   | are defnied here.                                                    |
#   '----------------------------------------------------------------------'


class LDAPAttributePlugin(abc.ABC):
    """Base class for all LDAP attribute synchronization plugins"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def help(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def is_builtin(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def lock_attributes(self, params: dict) -> list[str]:
        """List of user attributes to lock

        Normally the attributes that are modified by the sync_func()"""
        raise NotImplementedError()

    @abc.abstractmethod
    def needed_attributes(self, connection: LDAPUserConnector, params: dict) -> list[str]:
        """Gathers the LDAP user attributes that are needed by this plug-in"""
        raise NotImplementedError()

    @abc.abstractmethod
    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        """Executed during user synchronization to modify the "user" structure"""
        raise NotImplementedError()

    def parameters(self, connection: LDAPUserConnector | None) -> FixedValue | Dictionary:
        return FixedValue(
            title=self.title,
            help=self.help,
            value={},
            totext=_("This synchronization plug-in has no parameters."),
        )

    # Dictionary(
    #    title=plugin['title'],
    #    help=plugin['help'],
    #    elements=plugin['parameters'],
    #    required_keys=plugin.get('required_parameters', []),
    # )))

    @property
    def multisite_attributes(self) -> list[str]:
        """When a plug-in introduces new user attributes, it should declare the output target for
        this attribute. It can either be written to the multisites users.mk or the check_mk
        contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
        contacts.mk file."""
        return []

    @property
    def non_contact_attributes(self) -> list[str]:
        """When a plug-in introduces new user attributes, it should declare the output target for
        this attribute. It can either be written to the multisites users.mk or the check_mk
        contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
        contacts.mk file."""
        return []


class LDAPAttributePluginRegistry(cmk.ccc.plugin_registry.Registry[type[LDAPAttributePlugin]]):
    def plugin_name(self, instance):
        return instance().ident


class LDAPBuiltinAttributePlugin(LDAPAttributePlugin):
    """Base class for all built-in based sync plugins"""

    @property
    def is_builtin(self) -> bool:
        return True


class LDAPUserAttributePlugin(LDAPAttributePlugin):
    """Base class for all custom user attribute based sync plugins"""

    @property
    def is_builtin(self) -> bool:
        return False


ldap_attribute_plugin_registry = LDAPAttributePluginRegistry()


def all_attribute_plugins() -> list[tuple[str, type[LDAPAttributePlugin]]]:
    return [
        *ldap_attribute_plugin_registry.items(),
        *config_based_custom_user_attribute_sync_plugins(),
    ]


def ldap_attribute_plugins_elements(
    connection: LDAPUserConnector | None,
) -> list[tuple[str, FixedValue | Dictionary]]:
    """Returns a list of pairs (key, parameters) of all available attribute plugins"""
    elements = []
    items = sorted(
        [(ident, plugin_class()) for ident, plugin_class in all_attribute_plugins()],
        key=lambda x: x[1].title,
    )
    for key, plugin in items:
        elements.append((key, plugin.parameters(connection)))
    return elements


def config_based_custom_user_attribute_sync_plugins() -> list[
    tuple[str, type[LDAPUserAttributePlugin]]
]:
    """Register sync plug-ins for all custom user attributes (assuming simple data types)"""
    return [
        (
            name,
            type(
                "LDAPUserAttributePlugin%s" % name.title(),
                (LDAPUserAttributePlugin,),
                {
                    "ident": name,
                    "title": attr.valuespec().title(),
                    "help": attr.valuespec().help(),
                    "needed_attributes": lambda self, connection, params: [
                        params.get("attr", connection._ldap_attr(self.ident)).lower()
                    ],
                    "lock_attributes": lambda self, params: [self.ident],
                    "parameters": lambda self, connection: Dictionary(
                        title=self.title,
                        help=self.help,
                        elements=[
                            (
                                "attr",
                                TextInput(
                                    title=_("LDAP attribute to sync"),
                                    help=_(
                                        "The LDAP attribute whose contents shall be synced into this custom attribute."
                                    ),
                                    default_value=lambda: ldap_attr_of_connection(
                                        connection, self.ident
                                    ),
                                ),
                            ),
                        ],
                    ),
                    "sync_func": lambda self,
                    connection,
                    plugin,
                    params,
                    user_id,
                    ldap_user,
                    user: _ldap_sync_simple(
                        user_id,
                        ldap_user,
                        user,
                        plugin,
                        self.needed_attributes(connection, params)[0],
                    ),
                },
            ),
        )
        for name, attr in get_user_attributes()
    ]


# Helper function for gathering the default LDAP attribute names of a connection.
def ldap_attr_of_connection(connection: LDAPUserConnector | None, attr: str) -> str:
    if not connection:
        # Handle "new connection" situation where there is no connection object existant yet.
        # The default type is "Active directory", so we use it here.
        return ldap_attr_map["ad"].get(attr, attr).lower()
    return connection._ldap_attr(attr)


# Helper function for gathering the default LDAP filters of a connection.
def ldap_filter_of_connection(
    connection: LDAPUserConnector | None, key: str, handle_config: bool
) -> str:
    if not connection:
        # Handle "new connection" situation where there is no connection object existent yet.
        # The default type is "Active directory", so we use it here.
        return ldap_filter_map["ad"].get(key, "(objectclass=*)")
    return connection._ldap_filter(key, handle_config)


def _ldap_sync_simple(
    user_id: UserId, ldap_user: LDAPUserSpec, user: dict, user_attr: str, attr: str
) -> dict:
    if attr in ldap_user:
        attr_value = ldap_user[attr][0]
        # LDAP attribute in boolean format sends str "TRUE" or "FALSE"
        if user_attr == "disable_notifications":
            return {user_attr: {"disable": attr_value == "TRUE"}}
        return {user_attr: attr_value}
    return {}


def _get_connection_choices(add_this: bool = True) -> list[tuple[str | None, str]]:
    choices: list[tuple[str | None, str]] = []

    if add_this:
        choices.append((None, _("This connection")))

    for connection in get_ldap_connections().values():
        descr = connection["description"]
        if not descr:
            descr = connection["id"]
        choices.append((connection["id"], descr))

    return choices


# This is either the user id or the user distinguished name,
# depending on the LDAP server to communicate with
# OPENLDAP _member_attr() -> memberuid
# AD _member_attr() -> member
def _get_group_member_cmp_val(
    connection: LDAPUserConnector, user_id: UserId, ldap_user: LDAPUserSpec
) -> str:
    return user_id.lower() if connection._member_attr() == "memberuid" else ldap_user["dn"][0]


def _get_groups_of_user(
    connection: LDAPUserConnector,
    user_id: UserId,
    ldap_user: LDAPUserSpec,
    cg_names: Sequence[str],
    nested: bool,
    other_connection_ids: Sequence[str],
) -> list[str]:
    # Figure out how to check group membership.
    user_cmp_val = _get_group_member_cmp_val(connection, user_id, ldap_user)

    # Get list of LDAP connections to query
    connections = {connection}
    for connection_id in other_connection_ids:
        c = get_connection(connection_id)
        if c:
            assert isinstance(c, LDAPUserConnector)
            connections.add(c)

    # Load all LDAP groups which have a CN matching one contact
    # group which exists in WATO
    ldap_groups: GroupMemberships = {}
    for conn in connections:
        ldap_groups.update(conn._get_group_memberships(cg_names, nested=nested))

    # Now add the groups the user is a member off
    group_cns = []
    for group in ldap_groups.values():
        if user_cmp_val in group["members"]:
            assert isinstance(group["cn"], str)
            group_cns.append(group["cn"])

    return group_cns


def _group_membership_parameters():
    return [
        (
            "nested",
            FixedValue(
                title=_("Handle nested group memberships (Active Directory only at the moment)"),
                help=_(
                    "Once you enable this option, this plug-in will not only handle direct "
                    "group memberships, instead it will also dig into nested groups and treat "
                    "the members of those groups as contact group members as well. Please bear in mind "
                    "that this feature might increase the execution time of your LDAP sync."
                ),
                value=True,
                totext=_("Nested group memberships are resolved"),
            ),
        ),
        (
            "other_connections",
            ListChoice(
                title=_("Sync group memberships from other connections"),
                help=_(
                    "This is a special feature for environments where user accounts are located "
                    "in one LDAP directory and groups objects having them as members are located "
                    "in other directories. You should only enable this feature when you are in this "
                    "situation and really need it. The current connection is always used."
                ),
                # TODO typing: ListChoice doesn't actually allow None in the choice tuples
                # (aka ListChoiceChoice), yet that's what we get here.
                choices=lambda: _get_connection_choices(add_this=False),  # type: ignore[arg-type]
            ),
        ),
    ]


class LDAPAttributePluginMail(LDAPBuiltinAttributePlugin):
    @property
    def ident(self) -> str:
        return "email"

    @property
    def title(self) -> str:
        return _("Email address")

    @property
    def help(self):
        return _("Synchronizes the email of the LDAP user account into Checkmk.")

    def lock_attributes(self, params):
        return ["email"]

    def needed_attributes(self, connection, params):
        return [params.get("attr", connection._ldap_attr("mail")).lower()]

    def sync_func(
        self,
        connection: LDAPUserConnector,
        _plugin: str,
        params: dict,
        _user_id: UserId,
        ldap_user: LDAPUserSpec,
        _user: dict,
    ) -> dict:
        mail = ""
        mail_attr = params.get("attr", connection._ldap_attr("mail")).lower()
        if ldap_user.get(mail_attr):
            mail = ldap_user[mail_attr][0].lower()

        if mail:
            return {"email": mail}
        return {}

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                (
                    "attr",
                    TextInput(
                        title=_("LDAP attribute to sync"),
                        help=_("The LDAP attribute containing the mail address of the user."),
                        default_value=lambda: ldap_attr_of_connection(connection, "mail"),
                    ),
                ),
            ],
        )


# .
#   .--Alias---------------------------------------------------------------.
#   |                           _    _ _                                   |
#   |                          / \  | (_) __ _ ___                         |
#   |                         / _ \ | | |/ _` / __|                        |
#   |                        / ___ \| | | (_| \__ \                        |
#   |                       /_/   \_\_|_|\__,_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginAlias(LDAPBuiltinAttributePlugin):
    @property
    def ident(self) -> str:
        return "alias"

    @property
    def title(self) -> str:
        return _("Alias")

    @property
    def help(self):
        return _(
            "Populates the alias attribute of the Setup user by synchronizing an attribute "
            "from the LDAP user account. By default the LDAP attribute <tt>cn</tt> is used."
        )

    def lock_attributes(self, params):
        return ["alias"]

    def needed_attributes(self, connection, params):
        return [params.get("attr", connection._ldap_attr("cn")).lower()]

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        return _ldap_sync_simple(
            user_id,
            ldap_user,
            user,
            "alias",
            params.get("attr", connection._ldap_attr("cn")).lower(),
        )

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                (
                    "attr",
                    TextInput(
                        title=_("LDAP attribute to sync"),
                        help=_("The LDAP attribute containing the alias of the user."),
                        default_value=lambda: ldap_attr_of_connection(connection, "cn"),
                    ),
                ),
            ],
        )


# .
#   .--Auth Expire---------------------------------------------------------.
#   |           _         _   _       _____            _                   |
#   |          / \  _   _| |_| |__   | ____|_  ___ __ (_)_ __ ___          |
#   |         / _ \| | | | __| '_ \  |  _| \ \/ / '_ \| | '__/ _ \         |
#   |        / ___ \ |_| | |_| | | | | |___ >  <| |_) | | | |  __/         |
#   |       /_/   \_\__,_|\__|_| |_| |_____/_/\_\ .__/|_|_|  \___|         |
#   |                                           |_|                        |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginAuthExpire(LDAPBuiltinAttributePlugin):
    """Checks whether or not the user auth must be invalidated

    This is done by increasing the auth serial of the user. In first instance, it must parse
    the pw-changed field, then check whether or not a date has been stored in the user before
    and then maybe increase the serial."""

    @property
    def ident(self) -> str:
        return "auth_expire"

    @property
    def title(self) -> str:
        return _("Authentication Expiration")

    @property
    def help(self):
        return _(
            "This plug-in fetches all information which are needed to check whether or "
            "not an already authenticated user should be deauthenticated, e.g. because "
            "the password has changed in LDAP or the account has been locked."
        )

    def lock_attributes(self, params):
        return []

    @property
    def multisite_attributes(self) -> list[str]:
        return ["ldap_pw_last_changed"]

    @property
    def non_contact_attributes(self) -> list[str]:
        return ["ldap_pw_last_changed"]

    def needed_attributes(self, connection, params):
        attrs = [params.get("attr", connection._ldap_attr("pw_changed")).lower()]

        # Fetch user account flags to check locking
        if connection._is_active_directory():
            attrs.append("useraccountcontrol")
        return attrs

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        # Special handling for active directory: Is the user enabled / disabled?
        if connection._is_active_directory() and ldap_user.get("useraccountcontrol"):
            # see http://www.selfadsi.de/ads-attributes/user-userAccountControl.htm for details
            locked_in_ad = int(ldap_user["useraccountcontrol"][0]) & 2
            locked_in_cmk = user["locked"]

            if locked_in_ad and not locked_in_cmk:
                return {
                    "locked": True,
                    "serial": user.get("serial", 0) + 1,
                }

        changed_attr = params.get("attr", connection._ldap_attr("pw_changed")).lower()
        if changed_attr not in ldap_user:
            raise MKLDAPException(
                _(
                    'The "authentication expiration" attribute (%s) could not be fetched '
                    "from the LDAP server for user %s."
                )
                % (changed_attr, ldap_user)
            )

        # For keeping this thing simple, we don't parse the date here. We just store
        # the last value of the field in the user data and invalidate the auth if the
        # value has been changed.

        if "ldap_pw_last_changed" not in user:
            return {"ldap_pw_last_changed": ldap_user[changed_attr][0]}  # simply store

        # Update data (and invalidate auth) if the attribute has changed
        if user["ldap_pw_last_changed"] != ldap_user[changed_attr][0]:
            return {
                "ldap_pw_last_changed": ldap_user[changed_attr][0],
                "serial": user.get("serial", 0) + 1,
            }

        return {}

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                (
                    "attr",
                    TextInput(
                        title=_("LDAP attribute to be used as indicator"),
                        help=_(
                            "When the value of this attribute changes for a user account, all "
                            "current authenticated sessions of the user are invalidated and the "
                            "user must login again. By default this field uses the fields which "
                            "hold the time of the last password change of the user."
                        ),
                        default_value=lambda: ldap_attr_of_connection(connection, "pw_changed"),
                    ),
                ),
            ],
        )


# .
#   .--Pager---------------------------------------------------------------.
#   |                     ____                                             |
#   |                    |  _ \ __ _  __ _  ___ _ __                       |
#   |                    | |_) / _` |/ _` |/ _ \ '__|                      |
#   |                    |  __/ (_| | (_| |  __/ |                         |
#   |                    |_|   \__,_|\__, |\___|_|                         |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginPager(LDAPBuiltinAttributePlugin):
    @property
    def ident(self) -> str:
        return "pager"

    @property
    def title(self) -> str:
        return _("Pager")

    @property
    def help(self):
        return _(
            "This plug-in synchronizes a field of the users LDAP account to the pager attribute "
            "of the Setup user accounts, which is then forwarded to the monitoring core and can be used "
            "for notifications. By default the LDAP attribute <tt>mobile</tt> is used."
        )

    def lock_attributes(self, params):
        return ["pager"]

    def needed_attributes(self, connection, params):
        return [params.get("attr", connection._ldap_attr("mobile")).lower()]

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        return _ldap_sync_simple(
            user_id,
            ldap_user,
            user,
            "pager",
            params.get("attr", connection._ldap_attr("mobile")).lower(),
        )

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                (
                    "attr",
                    TextInput(
                        title=_("LDAP attribute to sync"),
                        help=_("The LDAP attribute containing the pager number of the user."),
                        default_value=lambda: ldap_attr_of_connection(connection, "mobile"),
                    ),
                ),
            ],
        )


# .
#   .--Contactgroups-------------------------------------------------------.
#   |   ____            _             _                                    |
#   |  / ___|___  _ __ | |_ __ _  ___| |_ __ _ _ __ ___  _   _ _ __  ___   |
#   | | |   / _ \| '_ \| __/ _` |/ __| __/ _` | '__/ _ \| | | | '_ \/ __|  |
#   | | |__| (_) | | | | || (_| | (__| || (_| | | | (_) | |_| | |_) \__ \  |
#   |  \____\___/|_| |_|\__\__,_|\___|\__\__, |_|  \___/ \__,_| .__/|___/  |
#   |                                    |___/                |_|          |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginGroupsToContactgroups(LDAPBuiltinAttributePlugin):
    @property
    def ident(self) -> str:
        return "groups_to_contactgroups"

    @property
    def title(self) -> str:
        return _("Contact group membership")

    @property
    def help(self):
        return _(
            "Adds the user to contact groups based on the group memberships in LDAP. This "
            "plug-in adds the user only to existing contact groups while the name of the "
            "contact group must match the common name (cn) of the LDAP group."
        )

    def lock_attributes(self, params):
        return ["contactgroups"]

    def needed_attributes(self, connection, params):
        return []

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        cg_names = list(load_contact_group_information().keys())

        return {
            "contactgroups": _get_groups_of_user(
                connection,
                user_id,
                ldap_user,
                cg_names,
                params.get("nested", False),
                params.get("other_connections", []),
            )
        }

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=_group_membership_parameters(),
        )


# .
#   .--Group-Attrs.--------------------------------------------------------.
#   |      ____                               _   _   _                    |
#   |     / ___|_ __ ___  _   _ _ __         / \ | |_| |_ _ __ ___         |
#   |    | |  _| '__/ _ \| | | | '_ \ _____ / _ \| __| __| '__/ __|        |
#   |    | |_| | | | (_) | |_| | |_) |_____/ ___ \ |_| |_| |  \__ \_       |
#   |     \____|_|  \___/ \__,_| .__/     /_/   \_\__|\__|_|  |___(_)      |
#   |                          |_|                                         |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginGroupAttributes(LDAPBuiltinAttributePlugin):
    """Populate user attributes based on group memberships within LDAP"""

    @property
    def ident(self) -> str:
        return "groups_to_attributes"

    @property
    def title(self) -> str:
        return _("Groups to custom user attributes")

    @property
    def help(self):
        return _(
            "Sets custom user attributes based on the group memberships in LDAP. This "
            "plug-in can be used to set custom user attributes to specified values "
            "for all users which are member of a group in LDAP. The specified group "
            "name must match the common name (CN) of the LDAP group."
        )

    def lock_attributes(self, params):
        attrs = []
        for group_spec in params["groups"]:
            attr_name, _value = group_spec["attribute"]
            attrs.append(attr_name)
        return attrs

    def needed_attributes(self, connection, params):
        return []

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict:
        # Which groups need to be checked whether or not the user is a member?
        cg_names = list({g["cn"] for g in params["groups"]})

        # Get the group names the user is member of
        groups = _get_groups_of_user(
            connection,
            user_id,
            ldap_user,
            cg_names,
            params.get("nested", False),
            params.get("other_connections", []),
        )

        # Now construct the user update dictionary
        update = {}

        # First clean all previously set values from attributes to be synced where
        # user is not a member of
        user_attrs = dict(get_user_attributes())
        for group_spec in params["groups"]:
            attr_name, value = group_spec["attribute"]
            if group_spec["cn"] not in groups and attr_name in user and attr_name in user_attrs:
                # not member, but set -> set to default. Maybe it would be cleaner
                # to just remove the attribute from the user, but the sync plugin
                # API does not support this at the moment.
                update[attr_name] = user_attrs[attr_name].valuespec().default_value()

        # Set the values of the groups the user is a member of
        for group_spec in params["groups"]:
            attr_name, value = group_spec["attribute"]
            if group_spec["cn"] in groups:
                # is member, set the configured value
                update[attr_name] = value

        return update

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=_group_membership_parameters()
            + [
                (
                    "groups",
                    ListOf(
                        valuespec=Dictionary(
                            elements=[
                                (
                                    "cn",
                                    TextInput(
                                        title=_("Group<nobr> </nobr>CN"),
                                        size=40,
                                        allow_empty=False,
                                    ),
                                ),
                                (
                                    "attribute",
                                    CascadingDropdown(
                                        title=_("Attribute to set"),
                                        choices=self._get_user_attribute_choices,
                                    ),
                                ),
                            ],
                            optional_keys=[],
                        ),
                        title=_("Groups to synchronize"),
                        help=_(
                            "Specify the groups to control the value of a given user attribute. If a user is "
                            "not a member of a group, the attribute will be left at its default value. When "
                            "a single attribute is set by multiple groups and a user is a member of multiple "
                            "of these groups, the later plug-in in the list will override the others."
                        ),
                        allow_empty=False,
                    ),
                ),
            ],
            required_keys=["groups"],
        )

    def _get_user_attribute_choices(self) -> Sequence[CascadingDropdownChoice]:
        return [
            (name, title, attr.valuespec())
            for name, attr in get_user_attributes()
            if (title := attr.valuespec().title()) is not None  # TODO: Hmmm...
        ]


# .
#   .--Roles---------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class LDAPAttributePluginGroupsToRoles(LDAPBuiltinAttributePlugin):
    @property
    def ident(self) -> str:
        return "groups_to_roles"

    @property
    def title(self) -> str:
        return _("Roles")

    @property
    def help(self):
        return _(
            "Configures the roles of the user depending on its group memberships "
            "in LDAP.<br><br>"
            "Please note: Additionally the user is assigned to the "
            '<a href="wato.py?mode=edit_configvar&varname=default_user_profile&site=&folder=">Default Roles</a>. '
            "Deactivate them if unwanted."
        )

    def lock_attributes(self, params):
        return ["roles"]

    def needed_attributes(self, connection, params):
        return []

    def sync_func(
        self,
        connection: LDAPUserConnector,
        plugin: str,
        params: dict,
        user_id: UserId,
        ldap_user: LDAPUserSpec,
        user: dict,
    ) -> dict[Literal["roles"], list[str]]:
        ldap_groups = self.fetch_needed_groups_for_groups_to_roles(connection, params)

        # posixGroup objects use the memberUid attribute to specify the group
        # memberships. This is the username instead of the users DN. So the
        # username needs to be used for filtering here.
        user_cmp_val = _get_group_member_cmp_val(connection, user_id, ldap_user)

        roles = []

        # Loop all roles mentioned in params (configured to be synchronized)
        for role_id, group_specs in params.items():
            if not isinstance(group_specs, list):
                group_specs = [group_specs]  # be compatible to old single group configs

            for group_spec in group_specs:
                if isinstance(group_spec, str):
                    dn = group_spec  # be compatible to old config without connection spec
                elif not isinstance(group_spec, tuple):
                    continue  # skip non configured ones (old valuespecs allowed None)
                else:
                    dn = group_spec[0]
                dn = dn.lower()  # lower case matching for DNs!

                # if group could be found and user is a member, add the role
                if dn in ldap_groups and user_cmp_val in ldap_groups[dn]["members"]:
                    roles.append(role_id)

        # Load default roles from default user profile when the user got no role
        # by the role sync plugin
        if not roles:
            roles = active_config.default_user_profile["roles"][:]

        return {"roles": roles}

    def fetch_needed_groups_for_groups_to_roles(self, connection, params):
        # Load the needed LDAP groups, which match the DNs mentioned in the role sync plug-in config
        ldap_groups = {}
        for connection_id, group_dns in self._get_groups_to_fetch(connection, params).items():
            conn = get_connection(connection_id)
            if conn is None:
                continue
            assert isinstance(conn, LDAPUserConnector)

            ldap_groups.update(
                dict(
                    conn._get_group_memberships(
                        group_dns, filt_attr="distinguishedname", nested=params.get("nested", False)
                    )
                )
            )

        return ldap_groups

    def _get_groups_to_fetch(self, connection, params):
        groups_to_fetch: dict[str, list[str]] = {}
        for group_specs in params.values():
            if isinstance(group_specs, list):
                for group_spec in group_specs:
                    if isinstance(group_spec, tuple):
                        this_conn_id = group_spec[1]
                        if this_conn_id is None:
                            this_conn_id = connection.id
                        groups_to_fetch.setdefault(this_conn_id, [])
                        groups_to_fetch[this_conn_id].append(group_spec[0].lower())
                    else:
                        # Be compatible to old config format (no connection specified)
                        this_conn_id = connection.id
                        groups_to_fetch.setdefault(this_conn_id, [])
                        groups_to_fetch[this_conn_id].append(group_spec.lower())

            elif isinstance(group_specs, str):
                # Need to be compatible to old config formats
                this_conn_id = connection.id
                groups_to_fetch.setdefault(this_conn_id, [])
                groups_to_fetch[this_conn_id].append(group_specs.lower())

        return groups_to_fetch

    def parameters(self, connection: LDAPUserConnector | None) -> Dictionary:
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=self._list_roles_with_group_dn,
        )

    def _list_roles_with_group_dn(self):
        elements: list[DictionaryEntry] = []
        for role_id, role in load_roles().items():
            elements.append(
                (
                    role_id,
                    MigrateNotUpdated(
                        valuespec=ListOf(
                            valuespec=MigrateNotUpdated(
                                valuespec=Tuple(
                                    elements=[
                                        LDAPDistinguishedName(
                                            title=_("Group<nobr> </nobr>DN"),
                                            size=80,
                                            allow_empty=False,
                                        ),
                                        DropdownChoice(
                                            title=_("Search<nobr> </nobr>in"),
                                            choices=_get_connection_choices,
                                            default_value=None,
                                        ),
                                    ],
                                ),
                                # convert old distinguished names to tuples
                                migrate=lambda v: (v,) if not isinstance(v, tuple) else v,
                            ),
                            title=role["alias"],
                            help=_(
                                "Distinguished Names of the LDAP groups to add users this role. "
                                "e. g. <tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt><br> "
                                "This group must be defined within the scope of the "
                                '<a href="wato.py?mode=ldap_config&varname=ldap_groupspec">LDAP Group Settings</a>.'
                            ),
                            movable=False,
                        ),
                        # convert old single distinguished names to list of :Ns
                        migrate=lambda v: [v] if not isinstance(v, list) else v,
                    ),
                )
            )

        elements.append(
            (
                "nested",
                FixedValue(
                    title=_(
                        "Handle nested group memberships (Active Directory only at the moment)"
                    ),
                    help=_(
                        "Once you enable this option, this plug-in will not only handle direct "
                        "group memberships, instead it will also dig into nested groups and treat "
                        "the members of those groups as contact group members as well. Please bear in mind "
                        "that this feature might increase the execution time of your LDAP sync."
                    ),
                    value=True,
                    totext=_("Nested group memberships are resolved"),
                ),
            )
        )
        return elements
