#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO FIXME: Change attribute sync plugins to classes. The current dict
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

import abc
import copy
import errno
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, IO, Union, Dict, List, Set, Type

# docs: http://www.python-ldap.org/doc/html/index.html
import ldap  # type: ignore[import]
import ldap.filter  # type: ignore[import]
from ldap.controls import SimplePagedResultsControl  # type: ignore[import]
from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.hooks as hooks
import cmk.gui.config as config
import cmk.gui.log as log
import cmk.gui.escaping as escaping
from cmk.gui.valuespec import (
    FixedValue,
    Dictionary,
    Transform,
    ListOf,
    TextAscii,
    ListOfStrings,
    LDAPDistinguishedName,
    Tuple,
    DropdownChoice,
    Integer,
    Float,
    TextUnicode,
    CascadingDropdown,
    ListChoice,
    Age,
    Password,
    rule_option_elements,
)
from cmk.gui.valuespec import CascadingDropdownChoice, DictionaryEntry
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.plugins.userdb.utils import (
    UserConnector,
    user_connector_registry,
    get_user_attributes,
    user_sync_config,
    load_roles,
    load_connection_config,
    save_connection_config,
    new_user_template,
    load_cached_profile,
    get_connection,
    cleanup_connection_id,
    release_users_lock,
    CheckCredentialsResult,
    add_internal_attributes,
)

from cmk.utils.type_defs import UserId

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

# LDAP attributes are case insensitive, we only use lower case!
# Please note: This are only default values. The user might override this
# by configuration.
ldap_attr_map = {
    'ad': {
        'user_id': 'samaccountname',
        'pw_changed': 'pwdlastset',
    },
    'openldap': {
        'user_id': 'uid',
        'pw_changed': 'pwdchangedtime',
        # group attributes
        'member': 'uniquemember',
    },
    '389directoryserver': {
        'user_id': 'uid',
        'pw_changed': 'krbPasswordExpiration',
        # group attributes
        'member': 'member',
    },
}

# LDAP attributes are case insensitive, we only use lower case!
# Please note: This are only default values. The user might override this
# by configuration.
ldap_filter_map = {
    'ad': {
        'users': '(&(objectclass=user)(objectcategory=person))',
        'groups': '(objectclass=group)',
    },
    'openldap': {
        'users': '(objectclass=person)',
        'groups': '(objectclass=groupOfUniqueNames)',
    },
    '389directoryserver': {
        'users': '(objectclass=person)',
        'groups': '(objectclass=groupOfUniqueNames)',
    },
}


class MKLDAPException(MKGeneralException):
    pass


DistinguishedName = str
GroupMemberships = Dict[DistinguishedName, Dict[str, Union[str, List[str]]]]

#.
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


@user_connector_registry.register
class LDAPUserConnector(UserConnector):
    # TODO: Move this to another place. We should have some managing object for this
    # stores the ldap connection suffixes of all connections
    connection_suffixes: Dict[str, str] = {}

    @classmethod
    def transform_config(cls, cfg):
        if not cfg:
            return cfg

        # For a short time in git master the directory_type could be:
        # ('ad', {'discover_nearest_dc': True/False})
        if isinstance(cfg["directory_type"], tuple) and cfg["directory_type"][0] == "ad" \
           and "discover_nearest_dc" in cfg["directory_type"][1]:
            auto_discover = cfg["directory_type"][1]["discover_nearest_dc"]

            if not auto_discover:
                cfg["directory_type"] = "ad"
            else:
                cfg["directory_type"] = (cfg["directory_type"][0], {
                    "connect_to": ("discover", {
                        "domain": cfg["server"],
                    }),
                })

        if not isinstance(cfg["directory_type"], tuple) and "server" in cfg:
            # Old separate configuration of directory_type and server
            servers = {
                "server": cfg["server"],
            }

            if "failover_servers" in cfg:
                servers["failover_servers"] = cfg["failover_servers"]

            cfg["directory_type"] = (cfg["directory_type"], {
                "connect_to": ("fixed_list", servers),
            })

        return cfg

    def __init__(self, cfg):
        super(LDAPUserConnector, self).__init__(self.transform_config(cfg))

        self._ldap_obj: Optional[ldap.ldapobject.ReconnectLDAPObject] = None
        self._ldap_obj_config = None
        self._logger = log.logger.getChild("ldap.Connection(%s)" % self.id())

        self._num_queries = 0
        self._user_cache = {}
        self._group_cache = {}
        self._group_search_cache = {}

        # File for storing the time of the last success event
        self._sync_time_file = Path(cmk.utils.paths.var_dir).joinpath('web/ldap_%s_sync_time.mk' %
                                                                      self.id())

        self._save_suffix()

    @classmethod
    def type(cls):
        return 'ldap'

    @classmethod
    def title(cls):
        return _('LDAP (Active Directory, OpenLDAP)')

    @classmethod
    def short_title(cls):
        return _('LDAP')

    @classmethod
    def get_connection_suffixes(cls):
        return cls.connection_suffixes

    def id(self):
        return self._config['id']

    def connect_server(self, server):
        try:
            if self._logger.isEnabledFor(logging.DEBUG):
                os.environ["GNUTLS_DEBUG_LEVEL"] = "99"
                ldap.set_option(ldap.OPT_DEBUG_LEVEL, 4095)
                trace_level = 2
                trace_file: Optional[IO[str]] = sys.stderr
            else:
                trace_level = 0
                trace_file = None

            uri = self._format_ldap_uri(server)
            conn = ldap.ldapobject.ReconnectLDAPObject(uri,
                                                       trace_level=trace_level,
                                                       trace_file=trace_file)
            conn.protocol_version = self._config.get('version', 3)
            conn.network_timeout = self._config.get('connect_timeout', 2.0)
            conn.retry_delay = 0.5

            # When using the domain top level as base-dn, the subtree search stumbles with referral objects.
            # whatever. We simply disable them here when using active directory. Hope this fixes all problems.
            if self.is_active_directory():
                conn.set_option(ldap.OPT_REFERRALS, 0)

            if 'use_ssl' in self._config:
                conn.set_option(ldap.OPT_X_TLS_CACERTFILE,
                                "%s/var/ssl/ca-certificates.crt" % cmk.utils.paths.omd_root)

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
            self.clear_nearest_dc_cache()
            if isinstance(e[0], dict):
                msg = e[0].get('info', e[0].get('desc', ''))
            else:
                msg = "%s" % e

            return None, "%s: %s" % (uri, msg)

        except MKLDAPException as e:
            self.clear_nearest_dc_cache()
            return None, "%s" % e

    def _format_ldap_uri(self, server):
        if self.use_ssl():
            uri = 'ldaps://'
        else:
            uri = 'ldap://'

        if "port" in self._config:
            port_spec = ":%d" % self._config["port"]
        else:
            port_spec = ""

        return uri + server + port_spec

    def connect(self, enforce_new=False, enforce_server=None):
        if not enforce_new \
           and self._ldap_obj \
           and self._config == self._ldap_obj_config:
            self._logger.info('LDAP CONNECT - Using existing connecting')
            return  # Use existing connections (if connection settings have not changed)
        self._logger.info('LDAP CONNECT - Connecting...')
        self.disconnect()

        # Some major config var validations

        if not self._config['user_dn']:
            raise MKLDAPException(
                _('The distinguished name of the container object, which holds '
                  'the user objects to be authenticated, is not configured. Please '
                  'fix this in the <a href="wato.py?mode=ldap_config">'
                  'LDAP User Settings</a>.'))

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
                    errors.append(error_msg)
                    continue  # In case of an error, try the (optional) fallback servers

            # Got no connection to any server
            if self._ldap_obj is None:
                raise MKLDAPException(_('LDAP connection failed:\n%s') % ('\n'.join(errors)))

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
            self._logger.info('Using cached DC %s' % cached_server)
            return cached_server

        import activedirectory  # type: ignore[import] # pylint: disable=import-error
        locator = activedirectory.Locator()
        locator.m_logger = self._logger
        try:
            server = locator.locate(domain)
            self._cache_nearest_dc(server)
            self._logger.info('  DISCOVERY: Discovered server %r from %r' % (server, domain))
            return server
        except Exception:
            self._logger.info('  DISCOVERY: Failed to discover a server from domain %r' % domain)
            self._logger.exception("error discovering LDAP server")
            self._logger.info('  DISCOVERY: Try to use domain DNS name %r as server' % domain)
            return domain

    def _get_nearest_dc_from_cache(self) -> Optional[str]:
        try:
            return ensure_str(self._nearest_dc_cache_filepath().open(encoding="utf-8").read())
        except IOError:
            pass
        return None

    def _cache_nearest_dc(self, server: str) -> None:
        self._logger.debug('Caching nearest DC %s' % server)
        store.save_file(self._nearest_dc_cache_filepath(), server)

    def clear_nearest_dc_cache(self) -> None:
        if not self._uses_discover_nearest_server():
            return

        try:
            self._nearest_dc_cache_filepath().unlink()
        except OSError:
            pass

    def _nearest_dc_cache_filepath(self) -> Path:
        return self._ldap_caches_filepath() / ("nearest_server.%s" % self.id())

    @classmethod
    def _ldap_caches_filepath(cls) -> Path:
        return Path(cmk.utils.paths.tmp_dir) / "ldap_caches"

    @classmethod
    def config_changed(cls) -> None:
        cls.clear_all_ldap_caches()

    @classmethod
    def clear_all_ldap_caches(cls) -> None:
        try:
            shutil.rmtree(str(cls._ldap_caches_filepath()))
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    # Bind with the default credentials
    def _default_bind(self, conn):
        try:
            if 'bind' in self._config:
                self._bind(self._replace_macros(self._config['bind'][0]),
                           self._config['bind'][1],
                           catch=False,
                           conn=conn)
            else:
                self._bind('', '', catch=False, conn=conn)  # anonymous bind
        except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH):
            raise MKLDAPException(
                _('Unable to connect to LDAP server with the configured bind credentials. '
                  'Please fix this in the '
                  '<a href="wato.py?mode=ldap_config">LDAP connection settings</a>.'))

    def _bind(self, user_dn, password, catch=True, conn=None):
        if conn is None:
            conn = self._ldap_obj
        self._logger.info('LDAP_BIND %s' % user_dn)
        try:
            conn.simple_bind_s(ensure_str(user_dn), password)
            self._logger.info('  SUCCESS')
        except ldap.LDAPError as e:
            self._logger.info('  FAILED (%s: %s)' % (e.__class__.__name__, e))
            if catch:
                raise MKLDAPException(_('Unable to authenticate with LDAP (%s)') % e)
            raise

    def servers(self):
        connect_params = self._get_connect_params()
        if self._uses_discover_nearest_server():
            servers = [self._discover_nearest_dc(connect_params["domain"])]
        else:
            servers = [connect_params['server']] + connect_params.get('failover_servers', [])

        return servers

    def _uses_discover_nearest_server(self):
        # 'directory_type': ('ad', {'connect_to': ('discover', {'domain': 'corp.de'})}),
        return self._config['directory_type'][1]["connect_to"][0] == "discover"

    def _get_connect_params(self):
        # 'directory_type': ('ad', {'connect_to': ('discover', {'domain': 'corp.de'})}),
        return self._config['directory_type'][1]["connect_to"][1]

    def use_ssl(self):
        return 'use_ssl' in self._config

    def active_plugins(self):
        return self._config['active_plugins']

    def _directory_type(self):
        return self._config['directory_type'][0]

    def is_active_directory(self):
        return self._directory_type() == 'ad'

    def has_user_base_dn_configured(self):
        return self._config['user_dn'] != ''

    def _create_users_only_on_login(self):
        return self._config.get('create_only_on_login', False)

    def _user_id_attr(self):
        return self._config.get('user_id', self.ldap_attr('user_id'))

    # TODO: Add .lower() here and remove at call sites
    def _member_attr(self):
        return self._config.get('group_member', self.ldap_attr('member'))

    def has_bind_credentials_configured(self):
        return self._config.get('bind', ('', ''))[0] != ''

    def has_group_base_dn_configured(self):
        return self._config['group_dn'] != ''

    def get_group_dn(self) -> DistinguishedName:
        return self._replace_macros(self._config['group_dn'])

    def _get_user_dn(self) -> DistinguishedName:
        return self._replace_macros(self._config['user_dn'])

    def _get_suffix(self):
        return self._config.get('suffix')

    def _has_suffix(self):
        return self._config.get('suffix') is not None

    def _save_suffix(self):
        suffix = self._get_suffix()
        if suffix:
            if suffix in LDAPUserConnector.connection_suffixes \
               and LDAPUserConnector.connection_suffixes[suffix] != self.id():
                raise MKUserError(
                    None,
                    _("Found duplicate LDAP connection suffix. "
                      "The LDAP connections %s and %s both use "
                      "the suffix %s which is not allowed.") %
                    (LDAPUserConnector.connection_suffixes[suffix], self.id(), suffix))
            LDAPUserConnector.connection_suffixes[suffix] = self.id()

    def needed_attributes(self) -> List[str]:
        """Returns a list of all needed LDAP attributes of all enabled plugins"""
        attrs: Set[str] = set()
        for key, params in self._config['active_plugins'].items():
            plugin = ldap_attribute_plugin_registry[key]()
            attrs.update(plugin.needed_attributes(self, params or {}))
        return list(attrs)

    def object_exists(self, dn: DistinguishedName) -> bool:
        try:
            return bool(self._ldap_search(dn, columns=['dn'], scope='base'))
        except Exception:
            return False

    def user_base_dn_exists(self) -> bool:
        return self.object_exists(self._get_user_dn())

    def group_base_dn_exists(self) -> bool:
        return self.object_exists(self.get_group_dn())

    def _ldap_paged_async_search(self, base, scope, filt, columns):
        self._logger.info('  PAGED ASYNC SEARCH')
        page_size = self._config.get('page_size', 1000)

        lc = SimplePagedResultsControl(size=page_size, cookie='')

        base = ensure_str(base)
        filt = ensure_str(filt)

        results = []
        while True:
            # issue the ldap search command (async)
            assert self._ldap_obj is not None
            msgid = self._ldap_obj.search_ext(base, scope, filt, columns, serverctrls=[lc])

            unused_code, response, unused_msgid, serverctrls = self._ldap_obj.result3(
                msgid=msgid, timeout=self._config.get('response_timeout', 5))

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

    def _ldap_search(self,
                     base,
                     filt='(objectclass=*)',
                     columns=None,
                     scope='sub',
                     implicit_connect=True):
        if columns is None:
            columns = []

        self._logger.info('LDAP_SEARCH "%s" "%s" "%s" "%r"' % (base, scope, filt, columns))
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
                    for dn, obj in self._ldap_paged_async_search(base, self._ldap_get_scope(scope),
                                                                 filt, columns):
                        if dn is None:
                            continue  # skip unwanted answers
                        new_obj = {}
                        for key, val in obj.items():
                            # Convert all keys to lower case!
                            new_obj[ensure_str(key).lower()] = [ensure_str(i) for i in val]
                        result.append((ensure_str(dn).lower(), new_obj))
                    success = True
                except ldap.NO_SUCH_OBJECT as e:
                    raise MKLDAPException(
                        _('The given base object "%s" does not exist in LDAP (%s))') % (base, e))

                except ldap.FILTER_ERROR as e:
                    raise MKLDAPException(
                        _('The given ldap filter "%s" is invalid (%s)') % (filt, e))

                except ldap.SIZELIMIT_EXCEEDED:
                    raise MKLDAPException(
                        _('The response reached a size limit. This could be due to '
                          'a sizelimit configuration on the LDAP server.<br />Throwing away the '
                          'incomplete results. You should change the scope of operation '
                          'within the ldap or adapt the limit settings of the LDAP server.'))
            except (ldap.SERVER_DOWN, ldap.TIMEOUT, MKLDAPException) as e:
                self.clear_nearest_dc_cache()

                last_exc = e
                if implicit_connect and tries_left:
                    self._logger.info('  Received %r. Retrying with clean connection...' % e)
                    self.disconnect()
                    time.sleep(0.5)
                else:
                    self._logger.info('  Giving up.')
                    break

        duration = time.time() - start_time

        if not success:
            self._logger.info('  FAILED')
            if config.debug:
                raise MKLDAPException(
                    _('Unable to successfully perform the LDAP search '
                      '(Base: %s, Scope: %s, Filter: %s, Columns: %s): %s') %
                    (escaping.escape_attribute(base), escaping.escape_attribute(scope),
                     escaping.escape_attribute(filt), escaping.escape_attribute(
                         ','.join(columns)), last_exc))
            raise MKLDAPException(
                _('Unable to successfully perform the LDAP search (%s)') % last_exc)

        self._logger.info('  RESULT length: %d, duration: %0.3f' % (len(result), duration))
        return result

    def _ldap_get_scope(self, scope):
        # Had "subtree" in Checkmk for several weeks. Better be compatible to both definitions.
        if scope in ['sub', 'subtree']:
            return ldap.SCOPE_SUBTREE
        if scope == 'base':
            return ldap.SCOPE_BASE
        if scope == 'one':
            return ldap.SCOPE_ONELEVEL
        raise Exception('Invalid scope specified: %s' % scope)

    # Returns the ldap filter depending on the configured ldap directory type
    def ldap_filter(self, key, handle_config=True):
        value = ldap_filter_map[self._directory_type()].get(key, '(objectclass=*)')
        if handle_config:
            if key == 'users':
                value = self._config.get('user_filter', value)
            elif key == 'groups':
                value = self._config.get('group_filter', value)
        return self._replace_macros(value)

    # Returns the ldap attribute name depending on the configured ldap directory type
    # If a key is not present in the map, the assumption is, that the key matches 1:1
    # Always use lower case here, just to prevent confusions.
    def ldap_attr(self, key):
        return ldap_attr_map[self._directory_type()].get(key, key).lower()

    # Returns the given distinguished name template with replaced vars
    def _replace_macros(self, tmpl):
        dn = tmpl

        for key, val in [('$OMD_SITE$', config.omd_site())]:
            if val:
                dn = dn.replace(key, val)
            else:
                dn = dn.replace(key, '')

        return dn

    def _sanitize_user_id(self, user_id):
        if self._config.get('lower_user_ids', False):
            user_id = user_id.lower()

        umlauts = self._config.get('user_id_umlauts', 'keep')

        # Be compatible to old user_id umlaut replacement. These days user_ids support special
        # characters, so the replacement would not be needed anymore. But we keep this for
        # compatibility reasons. FIXME TODO Remove this one day.
        if umlauts == 'replace':
            user_id = user_id.translate({
                ord(u'ü'): u'ue',
                ord(u'ö'): u'oe',
                ord(u'ä'): u'ae',
                ord(u'ß'): u'ss',
                ord(u'Ü'): u'UE',
                ord(u'Ö'): u'OE',
                ord(u'Ä'): u'AE',
                ord(u'å'): u'aa',
                ord(u'Å'): u'Aa',
                ord(u'Ø'): u'Oe',
                ord(u'ø'): u'oe',
                ord(u'Æ'): u'Ae',
                ord(u'æ'): u'ae',
            })

        return user_id

    def _get_user(self, username, no_escape=False):
        if username in self._user_cache:
            return self._user_cache[username]

        user_id_attr = self._user_id_attr()

        # Check whether or not the user exists in the directory matching the username AND
        # the user search filter configured in the "LDAP User Settings".
        # It's only ok when exactly one entry is found. Returns the DN and user_id
        # as tuple in this case.
        result = self._ldap_search(
            self._get_user_dn(),
            '(&(%s=%s)%s)' % (user_id_attr, ldap.filter.escape_filter_chars(username),
                              self._config.get('user_filter', '')),
            [user_id_attr],
            self._config['user_scope'],
        )

        if not result:
            return None

        dn = result[0][0]
        raw_user_id = result[0][1][user_id_attr][0]

        # Filter out users by the optional filter_group
        filter_group_dn = self._config.get('user_filter_group', None)
        if filter_group_dn:
            member_attr = self._member_attr().lower()
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
        return (dn.replace('\\', '\\\\'), user_id)

    def get_users(self, add_filter=''):
        user_id_attr = self._user_id_attr()

        columns = [
            user_id_attr,  # needed in all cases as uniq id
        ] + self.needed_attributes()

        filt = self.ldap_filter('users')

        # Create filter by the optional filter_group
        filter_group_dn = self._config.get('user_filter_group', None)
        if filter_group_dn:
            member_attr = self._member_attr().lower()
            # posixGroup objects use the memberUid attribute to specify the group memberships.
            # This is the username instead of the users DN. So the username needs to be used
            # for filtering here.
            user_cmp_attr = user_id_attr if member_attr == 'memberuid' else 'distinguishedname'

            member_filter_items = []
            for member in self._get_filter_group_members(filter_group_dn):
                member_filter_items.append('(%s=%s)' % (user_cmp_attr, member))
            add_filter += '(|%s)' % ''.join(member_filter_items)

        if add_filter:
            filt = '(&%s%s)' % (filt, add_filter)

        result = {}
        for dn, ldap_user in self._ldap_search(self._get_user_dn(), filt, columns,
                                               self._config['user_scope']):
            if user_id_attr not in ldap_user:
                raise MKLDAPException(
                    _('The configured User-ID attribute "%s" does not '
                      'exist for the user "%s"') % (user_id_attr, dn))
            user_id = self._sanitize_user_id(ldap_user[user_id_attr][0])
            if user_id:
                ldap_user['dn'] = dn  # also add the DN
                result[user_id] = ldap_user

        return result

    def get_groups(self, specific_dn=None):
        filt = self.ldap_filter('groups')
        dn = self.get_group_dn()

        if specific_dn:
            # When using AD, the groups can be filtered by the DN attribute. With
            # e.g. OpenLDAP this is not possible. In that case, change the DN.
            if self.is_active_directory():
                filt = '(&%s(distinguishedName=%s))' % (filt, specific_dn)
            else:
                dn = specific_dn

        return self._ldap_search(dn, filt, ['cn'], self._config['group_scope'])

    # TODO: Use get_group_memberships()?
    def _get_filter_group_members(self, filter_group_dn):
        member_attr = self._member_attr().lower()

        try:
            group = self._ldap_search(
                self._replace_macros(filter_group_dn),
                columns=[member_attr],
                scope='base',
            )
        except MKLDAPException:
            group = None

        if not group:
            raise MKLDAPException(
                _('The configured ldap user filter group could not be found. '
                  'Please check <a href="%s">your configuration</a>.') %
                'wato.py?mode=ldap_config&varname=ldap_userspec')

        return [m.lower() for m in list(group[0][1].values())[0]]

    def get_group_memberships(self,
                              filters: List[str],
                              filt_attr: str = 'cn',
                              nested: bool = False) -> GroupMemberships:
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
    # we change the role sync plugin parameters to snapins to make this part a little easier.
    def _get_direct_group_memberships(self, filters: List[str], filt_attr: str) -> GroupMemberships:
        groups: GroupMemberships = {}
        filt = self.ldap_filter('groups')
        member_attr = self._member_attr().lower()

        if self.is_active_directory() or filt_attr != 'distinguishedname':
            if filters:
                add_filt = '(|%s)' % ''.join(['(%s=%s)' % (filt_attr, f) for f in filters])
                filt = '(&%s%s)' % (filt, add_filt)

            for dn, obj in self._ldap_search(self.get_group_dn(), filt, ['cn', member_attr],
                                             self._config['group_scope']):
                groups[dn] = {
                    'cn': obj['cn'][0],
                    'members': sorted([m.lower() for m in obj.get(member_attr, [])]),
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

                for dn, obj in self._ldap_search(self._replace_macros(f_dn), filt,
                                                 ['cn', member_attr], 'base'):
                    groups[f_dn] = {
                        'cn': obj['cn'][0],
                        'members': sorted([m.lower() for m in obj.get(member_attr, [])]),
                    }

        self._group_cache[False].update(groups)

        return groups

    # Nested querying is more complicated. We have no option to simply do a query for group objects
    # to make them resolve the memberships here. So we need to query all users with the nested
    # memberof filter to get all group memberships of that group. We need one query for each group.
    def _get_nested_group_memberships(self, filters: List[str], filt_attr: str) -> GroupMemberships:
        groups: GroupMemberships = {}

        # Search group members in common ancestor of group and user base DN to be able to use a single
        # query instead of one for groups and one for users below when searching for the members.
        base_dn = self._group_and_user_base_dn()

        for filter_val in filters:
            matched_groups = {}

            # The memberof query below is only possible when knowing the DN of groups. We need
            # to look for the DN when the caller gives us CNs (e.g. when using the the groups
            # to contact groups plugin).
            if filt_attr == 'cn':
                result = self._ldap_search(
                    self.get_group_dn(), '(&%s(cn=%s))' % (self.ldap_filter('groups'), filter_val),
                    ['dn', 'cn'], self._config['group_scope'])
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
                # Try to get members from group cache
                try:
                    groups[dn] = self._group_cache[True][dn]
                    continue
                except KeyError:
                    pass

                # In case we don't have the cn we need to fetch it. It may be needed, e.g. by the contact group
                # sync plugin
                if cn is None:
                    group = self._ldap_search(dn,
                                              filt="(objectclass=group)",
                                              columns=['cn'],
                                              scope='base')
                    if group:
                        cn = group[0][1]["cn"][0]

                filt = '(memberof=%s)' % dn
                groups[dn] = {
                    'members': [],
                    'cn': cn,
                }

                members = groups[dn]['members']
                assert isinstance(members, list)

                # Register the group construct, collect the members later. This way we can also
                # catch the case where a group refers to itself, which is prevented by some LDAP
                # editing tools, like "Active Directory Users & Computers", but can somehow be
                # configured, e.g. when configuring universal distribution lists using ADSIEdit
                # it was possible to configure something like this at least in older directories.
                self._group_cache[True][dn] = groups[dn]

                sub_group_filters = []
                for obj_dn, obj in self._ldap_search(base_dn, filt, ['dn', 'objectclass'], 'sub'):
                    if "user" in obj['objectclass']:
                        members.append(obj_dn)

                    elif "group" in obj['objectclass']:
                        sub_group_filters.append(obj_dn)

                # TODO: This could be optimized by first collecting all sub groups of all searched
                # groups, then collecting them all together
                for _sub_group_dn, sub_group in self.get_group_memberships(sub_group_filters,
                                                                           filt_attr='dn',
                                                                           nested=True).items():
                    members += sub_group["members"]

                members.sort()

        return groups

    def _group_and_user_base_dn(self):
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
                _("Unable to synchronize nested groups (Found no common base DN for user base "
                  "DN \"%s\" and group base DN \"%s\")") %
                (self._get_user_dn(), self.get_group_dn()))

        return ldap.dn.dn2str(base_dn)

    #
    # USERDB API METHODS
    #

    # With release 1.2.7i3 we introduced multi ldap server connection capabilities.
    # We had to change the configuration declaration to reflect the new possibilites.
    # This function migrates the former configuration to the new one.
    # TODO This code can be removed the day we decide not to migrate old configs anymore.
    @classmethod
    def migrate_config(cls):
        if config.user_connections:
            return  # Don't try to migrate anything when there is at least one connection configured

        if cls._needs_config_migration():
            cls._do_migrate_config()

    # Don't migrate anything when no ldap connection has been configured
    @classmethod
    def _needs_config_migration(cls):
        ldap_connection = getattr(config, 'ldap_connection', {})
        default_ldap_connection_config = {
            'type': 'ad',
            'page_size': 1000,
        }
        return ldap_connection and ldap_connection != default_ldap_connection_config

    @classmethod
    def _do_migrate_config(cls):
        # Create a default connection out of the old config format
        connection = {
            'id': 'default',
            'type': 'ldap',
            'description': _('This is the default LDAP connection.'),
            'disabled': 'ldap' not in getattr(config, 'user_connectors', []),
            'cache_livetime': getattr(config, 'ldap_cache_livetime', 300),
            'active_plugins': getattr(config, 'ldap_active_plugins', []) or {
                'email': {},
                'alias': {},
                'auth_expire': {}
            },
            'directory_type': getattr(config, 'ldap_connection', {}).get('type', 'ad'),
            'user_id_umlauts': 'keep',
            'user_dn': '',
            'user_scope': 'sub',
        }

        old_connection_cfg = getattr(config, 'ldap_connection', {})
        try:
            del old_connection_cfg['type']
        except KeyError:
            pass
        connection.update(old_connection_cfg)

        for what in ["user", "group"]:
            for key, val in getattr(config, 'ldap_' + what + 'spec', {}).items():
                if key in ["dn", "scope", "filter", "filter_group", "member"]:
                    key = what + "_" + key
                connection[key] = val

        save_connection_config([connection])
        config.user_connections.append(connection)

    # This function only validates credentials, no locked checking or similar
    def check_credentials(self, user_id, password) -> CheckCredentialsResult:
        self.connect()

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
        user_id = self._strip_suffix(user_id)

        # Returns None when the user is not found or not uniq, else returns the
        # distinguished name and the user_id as tuple which are both needed for
        # the further login process.
        fetch_user_result = self._get_user(user_id, True)
        if not fetch_user_result:
            # The user does not exist
            if enforce_this_connection:
                return False  # Refuse login
            return None  # Try next connection (if available)

        user_dn, user_id = fetch_user_result

        # Try to bind with the user provided credentials. This unbinds the default
        # authentication which should be rebound again after trying this.
        try:
            self._bind(user_dn, password)
            if not self._has_suffix():
                result = user_id
            else:
                # Does the user without suffix exist and is it related to this connection? Always
                # use it in case it exists. If not, use the user with the suffix. A connection may
                # have created users while the connection had no suffix and a suffix has been added
                # to the connection later.
                if self._connection_id_of_user(user_id) == self.id():
                    result = user_id
                else:
                    result = self._add_suffix(user_id)
        except Exception:
            self._logger.exception("  Exception during authentication (User: %s)", user_id)
            result = False

        self._default_bind(self._ldap_obj)
        return result

    def _connection_id_of_user(self, user_id: UserId) -> Optional[str]:
        user = load_cached_profile(user_id)
        if user is None:
            return None
        return user.get("connector")

    def _user_enforces_this_connection(self, username):
        matched_connection_ids = []
        for suffix, connection_id in LDAPUserConnector.get_connection_suffixes().items():
            if self._username_matches_suffix(username, suffix):
                matched_connection_ids.append(connection_id)

        if not matched_connection_ids:
            return None
        if len(matched_connection_ids) > 1:
            raise MKUserError(None, _("Unable to match connection"))
        return matched_connection_ids[0] == self.id()

    def _username_matches_suffix(self, username, suffix):
        return username.endswith('@' + suffix)

    def _strip_suffix(self, username):
        suffix = self._get_suffix()
        if suffix and self._username_matches_suffix(username, suffix):
            return username[:-(len(suffix) + 1)]
        return username

    def _add_suffix(self, username):
        suffix = self._get_suffix()
        return '%s@%s' % (username, suffix)

    def do_sync(self, add_to_changelog, only_username, load_users_func, save_users_func):
        if not self.has_user_base_dn_configured():
            self._logger.info("Not trying sync (no \"user base DN\" configured)")
            return  # silently skip sync without configuration

        # Flush ldap related before each sync to have a caching only for the
        # current sync process
        self._flush_caches()

        start_time = time.time()
        connection_id = self.id()

        self._logger.info('SYNC STARTED')
        self._logger.info('  SYNC PLUGINS: %s' % ', '.join(self._config['active_plugins'].keys()))

        ldap_users = self.get_users()

        users = load_users_func(lock=True)

        changes = []

        def load_user(user_id):
            if user_id in users:
                user = copy.deepcopy(users[user_id])
                mode_create = False
            else:
                user = new_user_template(self.id())
                mode_create = True
            return mode_create, user

        # Remove users which are controlled by this connector but can not be found in
        # LDAP anymore
        for user_id, user in users.items():
            user_connection_id = cleanup_connection_id(user.get('connector'))
            if user_connection_id == connection_id and self._strip_suffix(
                    user_id) not in ldap_users:
                del users[user_id]  # remove the user
                changes.append(_("LDAP [%s]: Removed user %s") % (connection_id, user_id))

        has_changed_passwords = False
        profiles_to_synchronize = {}
        for user_id, ldap_user in ldap_users.items():
            mode_create, user = load_user(user_id)
            user_connection_id = cleanup_connection_id(user.get('connector'))

            if self._create_users_only_on_login() and mode_create:
                self._logger.info('  SKIP SYNC "%s" (Only create user of "%s" connector on login)' %
                                  (user_id, user_connection_id))
                continue

            if only_username and user_id != only_username:
                continue  # Only one user should be synced, skip others.

            # Name conflict: Found a user that has an equal name, but is not controlled
            # by this connector. Don't sync it. When an LDAP connection suffix is configured
            # use this for constructing a unique username. If not or if the name+suffix is
            # already taken too, skip this user silently.
            if user_connection_id != connection_id:
                if self._has_suffix():
                    user_id = self._add_suffix(user_id)
                    mode_create, user = load_user(user_id)
                    user_connection_id = cleanup_connection_id(user.get('connector'))
                    if user_connection_id != connection_id:
                        self._logger.info('  SKIP SYNC "%s" (name conflict after adding suffix '
                                          'with user from "%s" connector)' %
                                          (user_id, user_connection_id))
                        continue  # added suffix, still name conflict
                else:
                    self._logger.info(
                        '  SKIP SYNC "%s" (name conflict with user from "%s" connector)' %
                        (user_id, user_connection_id))
                    continue  # name conflict, different connector

            self._execute_active_sync_plugins(user_id, ldap_user, user)

            if not mode_create and user == users[user_id]:
                continue  # no modification. Skip this user.

            # Gather changed attributes for easier debugging
            if not mode_create:
                set_new, set_old = set(user.keys()), set(users[user_id].keys())
                intersect = set_new.intersection(set_old)
                added = set_new - intersect
                removed = set_old - intersect

                changed = self._find_changed_user_keys(intersect, users[user_id],
                                                       user)  # returns a dict

            users[user_id] = user  # Update the user record
            if mode_create:
                add_internal_attributes(users[user_id])
                changes.append(_("LDAP [%s]: Created user %s") % (connection_id, user_id))
            else:
                details = []
                if added:
                    details.append(_('Added: %s') % ', '.join(added))
                if removed:
                    details.append(_('Removed: %s') % ', '.join(removed))

                # Password changes found in LDAP should not be logged as "pending change".
                # These changes take effect imediately (pw already changed in AD, auth serial
                # is increaed by sync plugin) on the local site, so no one needs to active this.
                pw_changed = False
                if 'ldap_pw_last_changed' in changed:
                    del changed['ldap_pw_last_changed']
                    pw_changed = True
                if 'serial' in changed:
                    del changed['serial']
                    pw_changed = True

                if pw_changed:
                    has_changed_passwords = True

                # Synchronize new user profile to remote sites if needed
                if pw_changed and not changed and config.has_wato_slave_sites():
                    profiles_to_synchronize[user_id] = user

                if changed:
                    for key, (old_value, new_value) in sorted(changed.items()):
                        details.append(('Changed %s from %s to %s' % (key, old_value, new_value)))

                if details:
                    changes.append(
                        _("LDAP [%s]: Modified user %s (%s)") %
                        (connection_id, user_id, ', '.join(details)))

        hooks.call("ldap-sync-finished", self._logger, profiles_to_synchronize, changes)

        duration = time.time() - start_time
        self._logger.info('SYNC FINISHED - Duration: %0.3f sec, Queries: %d' %
                          (duration, self._num_queries))

        if changes or has_changed_passwords:
            save_users_func(users)
        else:
            release_users_lock()

        self._set_last_sync_time()

    def _find_changed_user_keys(self, keys, user, new_user):
        changed = {}
        for key in keys:
            value = user[key]
            new_value = new_user[key]
            if isinstance(value, list) and isinstance(new_value, list):
                is_changed = sorted(value) != sorted(new_value)
            else:
                is_changed = value != new_value
            if is_changed:
                changed[key] = (value, new_value)
        return changed

    def _execute_active_sync_plugins(self, user_id, ldap_user, user):
        for key, params in self._config['active_plugins'].items():
            plugin = ldap_attribute_plugin_registry[key]()
            user.update(plugin.sync_func(self, key, params or {}, user_id, ldap_user, user))

    def _flush_caches(self):
        self._num_queries = 0
        self._user_cache.clear()
        self._group_cache.clear()
        self._group_search_cache.clear()

    def _set_last_sync_time(self) -> None:
        with self._sync_time_file.open('w', encoding="utf-8") as f:
            f.write('%s\n' % time.time())

    def is_enabled(self) -> bool:
        sync_config = user_sync_config()
        if isinstance(sync_config, tuple) and self.id() not in sync_config[1]:
            #self._ldap_logger('Skipping disabled connection %s' % (self.id()))
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
        return self._config['cache_livetime']

    # Calculates the attributes of the users which are locked for users managed
    # by this connector
    def locked_attributes(self) -> List[str]:
        locked = {'password'}  # This attributes are locked in all cases!
        for key, params in self._config['active_plugins'].items():
            plugin = ldap_attribute_plugin_registry[key]()
            locked.update(plugin.lock_attributes(params))
        return list(locked)

    # Calculates the attributes added in this connector which shal be written to
    # the multisites users.mk
    def multisite_attributes(self) -> List[str]:
        attrs: Set[str] = set()
        for key in self._config['active_plugins'].keys():
            plugin = ldap_attribute_plugin_registry[key]()
            attrs.update(plugin.multisite_attributes)
        return list(attrs)

    # Calculates the attributes added in this connector which shal NOT be written to
    # the check_mks contacts.mk
    def non_contact_attributes(self) -> List[str]:
        attrs: Set[str] = set()
        for key in self._config['active_plugins'].keys():
            plugin = ldap_attribute_plugin_registry[key]()
            attrs.update(plugin.non_contact_attributes)
        return list(attrs)


#.
#   .--Valuespec-----------------------------------------------------------.
#   |           __     __    _                                             |
#   |           \ \   / /_ _| |_   _  ___  ___ _ __   ___  ___             |
#   |            \ \ / / _` | | | | |/ _ \/ __| '_ \ / _ \/ __|            |
#   |             \ V / (_| | | |_| |  __/\__ \ |_) |  __/ (__             |
#   |              \_/ \__,_|_|\__,_|\___||___/ .__/ \___|\___|            |
#   |                                         |_|                          |
#   '----------------------------------------------------------------------'


class LDAPConnectionValuespec(Transform):
    def __init__(self, new, connection_id):
        self._new = new
        self._connection_id = connection_id
        self._connection = get_connection(self._connection_id)

        general_elements = self._general_elements()
        connection_elements = self._connection_elements()
        user_elements = self._user_elements()
        group_elements = self._group_elements()
        other_elements = self._other_elements()

        valuespec = Dictionary(
            title=_('LDAP Connection'),
            elements=general_elements + connection_elements + user_elements + group_elements +
            other_elements,
            headers=[
                (_("General Properties"), [key for key, _vs in general_elements]),
                (_("LDAP Connection"), [key for key, _vs in connection_elements]),
                (_("Users"), [key for key, _vs in user_elements]),
                (_("Groups"), [key for key, _vs in group_elements]),
                (_("Attribute Sync Plugins"), ["active_plugins"]),
                (_("Other"), ["cache_livetime"]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[
                'port',
                'use_ssl',
                'bind',
                'page_size',
                'response_timeout',
                'failover_servers',
                'user_filter',
                'user_filter_group',
                'user_id',
                'lower_user_ids',
                'connect_timeout',
                'version',
                'group_filter',
                'group_member',
                'suffix',
                'create_only_on_login',
            ],
            validate=self._validate_ldap_connection,
        )

        super(LDAPConnectionValuespec, self).__init__(valuespec,
                                                      forth=LDAPUserConnector.transform_config)

    def _general_elements(self) -> List[DictionaryEntry]:
        general_elements: List[DictionaryEntry] = []

        if self._new:
            id_element: DictionaryEntry = (
                "id",
                TextAscii(
                    title=_("ID"),
                    help=_(
                        "The ID of the connection must be a unique text. It will be used as an internal key "
                        "when objects refer to the connection."),
                    allow_empty=False,
                    size=12,
                    validate=self._validate_ldap_connection_id,
                ))
        else:
            id_element = ("id", FixedValue(
                self._connection_id,
                title=_("ID"),
            ))

        general_elements += [id_element]

        if cmk_version.is_managed_edition():
            general_elements += managed.customer_choice_element()

        general_elements += rule_option_elements()

        return general_elements

    def _connection_elements(self):
        connection_elements = [
            ("directory_type",
             CascadingDropdown(
                 title=_("Directory Type"),
                 help=_("Select the software the LDAP directory is based on. Depending on "
                        "the selection e.g. the attribute names used in LDAP queries will "
                        "be altered."),
                 choices=[
                     ("ad", _("Active Directory"), self._vs_directory_options("ad")),
                     ("openldap", _("OpenLDAP"), self._vs_directory_options("openldap")),
                     ("389directoryserver", _("389 Directory Server"),
                      self._vs_directory_options("389directoryserver")),
                 ],
             )),
            ("bind",
             Tuple(
                 title=_("Bind Credentials"),
                 help=_("Set the credentials to be used to connect to the LDAP server. The "
                        "used account must not be allowed to do any changes in the directory "
                        "the whole connection is read only. "
                        "In some environment an anonymous connect/bind is allowed, in this "
                        "case you don't have to configure anything here."
                        "It must be possible to list all needed user and group objects from the "
                        "directory."),
                 elements=[
                     LDAPDistinguishedName(
                         title=_("Bind DN"),
                         help=_(
                             "Specify the distinguished name to be used to bind to "
                             "the LDAP directory, e. g. <tt>CN=ldap,OU=users,DC=example,DC=com</tt>"
                         ),
                         size=63,
                     ),
                     Password(
                         title=_("Bind Password"),
                         help=_("Specify the password to be used to bind to "
                                "the LDAP directory."),
                     ),
                 ],
             )),
            ("port",
             Integer(
                 title=_("TCP Port"),
                 help=_("This variable allows to specify the TCP port to "
                        "be used to connect to the LDAP server. "),
                 minvalue=1,
                 maxvalue=65535,
                 default_value=389,
             )),
            ("use_ssl",
             FixedValue(
                 title=_("Use SSL"),
                 help=
                 _("Connect to the LDAP server with a SSL encrypted connection. The "
                   "<a href=\"wato.py?mode=edit_configvar&site=&varname=trusted_certificate_authorities\">trusted "
                   "certificates authorities</a> configured in Check_MK will be used to validate the "
                   "certificate provided by the LDAP server."),
                 value=True,
                 totext=_("Encrypt the network connection using SSL."),
             )),
            ("connect_timeout",
             Float(
                 title=_("Connect Timeout"),
                 help=_("Timeout for the initial connection to the LDAP server in seconds."),
                 unit=_("Seconds"),
                 minvalue=1.0,
                 default_value=2.0,
             )),
            ("version",
             DropdownChoice(
                 title=_("LDAP Version"),
                 help=_("Select the LDAP version the LDAP server is serving. Most modern "
                        "servers use LDAP version 3."),
                 choices=[(2, "2"), (3, "3")],
                 default_value=3,
             )),
            ("page_size",
             Integer(
                 title=_("Page Size"),
                 help=_(
                     "LDAP searches can be performed in paginated mode, for example to improve "
                     "the performance. This enables pagination and configures the size of the pages."
                 ),
                 minvalue=1,
                 default_value=1000,
             )),
            ("response_timeout",
             Integer(
                 title=_("Response Timeout"),
                 unit=_("Seconds"),
                 help=_("Timeout for LDAP query responses."),
                 minvalue=0,
                 default_value=5,
             )),
            ("suffix",
             TextUnicode(
                 allow_empty=False,
                 title=_("LDAP connection suffix"),
                 help=
                 _("The LDAP connection suffix can be used to distinguish equal named objects "
                   "(name conflicts), for example user accounts, from different LDAP connections.<br>"
                   "It is used in the following situations:<br><br>"
                   "During LDAP synchronization, the LDAP sync might discover that a user to be "
                   "synchronized from from the current LDAP is already being synchronized from "
                   "another LDAP connection. Without the suffix configured this results in a name "
                   "conflict and the later user not being synchronized. If the connection has a "
                   "suffix configured, this suffix is added to the later username in case of the name "
                   "conflict to resolve it. The user will then be named <tt>[username]@[suffix]</tt> "
                   "instead of just <tt>[username]</tt>.<br><br>"
                   "In the case a user which users name is existing in multiple LDAP directories, "
                   "but associated to different persons, your user can insert <tt>[username]@[suffix]</tt>"
                   " during login instead of just the plain <tt>[username]</tt> to tell which LDAP "
                   "directory he is assigned to. Users without name conflict just need to provide their "
                   "regular username as usual."),
                 regex=re.compile(r'^[A-Z0-9.-]+(?:\.[A-Z]{2,24})?$', re.I),
                 validate=self._validate_ldap_connection_suffix,
             )),
        ]

        return connection_elements

    def _vs_directory_options(self, ty: str) -> Dictionary:
        connect_to_choices: List[CascadingDropdownChoice] = [
            ("fixed_list", _("Manually specify list of LDAP servers"),
             Dictionary(
                 elements=[
                     ("server",
                      TextAscii(
                          title=_("LDAP Server"),
                          help=_(
                              "Set the host address of the LDAP server. Might be an IP address or "
                              "resolvable hostname."),
                          allow_empty=False,
                      )),
                     ("failover_servers",
                      ListOfStrings(
                          title=_('Failover Servers'),
                          help=
                          _('When the connection to the first server fails with connect specific errors '
                            'like timeouts or some other network related problems, the connect mechanism '
                            'will try to use this server instead of the server configured above. If you '
                            'use persistent connections (default), the connection is being used until the '
                            'LDAP is not reachable or the local webserver is restarted.'),
                          allow_empty=False,
                      )),
                 ],
                 optional_keys=["failover_servers"],
             )),
        ]

        if ty == "ad":
            connect_to_choices.append((
                "discover", _("Automatically discover LDAP server"),
                Dictionary(
                    elements=[
                        ("domain",
                         TextAscii(
                             title=_("DNS domain name to discover LDAP servers of"),
                             help=
                             _("Configure the DNS domain name of your Active directory domain here, Check_MK "
                               "will then query this domain for it's closest domain controller to communicate "
                               "with."),
                             allow_empty=False,
                         )),
                    ],
                    optional_keys=[],
                )),)

        return Dictionary(
            elements=[
                ("connect_to", CascadingDropdown(
                    title=_("Connect to"),
                    choices=connect_to_choices,
                )),
            ],
            optional_keys=[],
        )

    def _user_elements(self):
        user_elements = [
            ("user_dn",
             LDAPDistinguishedName(
                 title=_("User Base DN"),
                 help=_(
                     "Give a base distinguished name here, e. g. <tt>OU=users,DC=example,DC=com</tt><br> "
                     "All user accounts to synchronize must be located below this one."),
                 size=80,
             )),
            ("user_scope",
             DropdownChoice(
                 title=_("Search Scope"),
                 help=_(
                     "Scope to be used in LDAP searches. In most cases <i>Search whole subtree below "
                     "the base DN</i> is the best choice. "
                     "It searches for matching objects recursively."),
                 choices=[
                     ("sub", _("Search whole subtree below the base DN")),
                     ("base", _("Search only the entry at the base DN")),
                     ("one", _("Search all entries one level below the base DN")),
                 ],
                 default_value="sub",
             )),
            ("user_filter",
             TextUnicode(
                 title=_("Search Filter"),
                 help=
                 _("Using this option you can define an optional LDAP filter which is used during "
                   "LDAP searches. It can be used to only handle a subset of the users below the given "
                   "base DN.<br><br>Some common examples:<br><br> "
                   "All user objects in LDAP:<br> "
                   "<tt>(&(objectclass=user)(objectcategory=person))</tt><br> "
                   "Members of a group:<br> "
                   "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br> "
                   "Members of a nested group:<br> "
                   "<tt>(&(objectclass=user)(objectcategory=person)(memberof:1.2.840.113556.1.4.1941:=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"
                  ),
                 size=80,
                 default_value=lambda: ldap_filter_of_connection(self._connection_id, 'users', False
                                                                ),
                 attrencode=True,
             )),
            ("user_filter_group",
             LDAPDistinguishedName(
                 title=_("Filter Group (Only use in special situations)"),
                 help=
                 _("Using this option you can define the DN of a group object which is used to filter the users. "
                   "Only members of this group will then be synchronized. This is a filter which can be "
                   "used to extend capabilities of the regular \"Search Filter\". Using the search filter "
                   "you can only define filters which directly apply to the user objects. To filter by "
                   "group memberships, you can use the <tt>memberOf</tt> attribute of the user objects in some "
                   "directories. But some directories do not have such attributes because the memberships "
                   "are stored in the group objects as e.g. <tt>member</tt> attributes. You should use the "
                   "regular search filter whenever possible and only use this filter when it is really "
                   "neccessary. Finally you can say, you should not use this option when using Active Directory. "
                   "This option is neccessary in OpenLDAP directories when you like to filter by group membership.<br><br>"
                   "If using, give a plain distinguished name of a group here, e. g. "
                   "<tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt>"),
                 size=80,
             )),
            ("user_id",
             TextAscii(
                 title=_("User-ID Attribute"),
                 help=_("The attribute used to identify the individual users. It must have "
                        "unique values to make an user identifyable by the value of this "
                        "attribute."),
                 default_value=lambda: ldap_attr_of_connection(self._connection_id, 'user_id'),
                 attrencode=True,
             )),
            ("lower_user_ids",
             FixedValue(
                 title=_("Lower Case User-IDs"),
                 help=_("Convert imported User-IDs to lower case during synchronization."),
                 value=True,
                 totext=_("Enforce lower case User-IDs."),
             )),
            ("user_id_umlauts",
             Transform(DropdownChoice(
                 title=_("Translate Umlauts in User-IDs (deprecated)"),
                 help=_("Checkmk was not not supporting special characters (like Umlauts) in "
                        "User-IDs. To deal with LDAP users having umlauts in their User-IDs "
                        "you had the choice to replace umlauts with other characters. This option "
                        "is still available for compatibility reasons, but you are adviced to use "
                        "the \"keep\" option for new installations."),
                 choices=[
                     ("keep", _("Keep special characters")),
                     ("replace", _("Replace umlauts like \"&uuml;\" with \"ue\"")),
                 ],
                 default_value="keep",
             ),
                       forth=lambda x: "keep" if (x == "skip") else x)),
            ("create_only_on_login",
             FixedValue(
                 title=_("Create users only on login"),
                 value=True,
                 totext=_("Instead of creating the user accounts during the regular sync, create "
                          "the user on the first login."),
             )),
        ]

        return user_elements

    def _group_elements(self):
        group_elements = [
            ("group_dn",
             LDAPDistinguishedName(
                 title=_("Group Base DN"),
                 help=_(
                     "Give a base distinguished name here, e. g. <tt>OU=groups,DC=example,DC=com</tt><br> "
                     "All groups used must be located below this one."),
                 size=80,
             )),
            ("group_scope",
             DropdownChoice(
                 title=_("Search Scope"),
                 help=_("Scope to be used in group related LDAP searches. In most cases "
                        "<i>Search whole subtree below the base DN</i> "
                        "is the best choice. It searches for matching objects in the given base "
                        "recursively."),
                 choices=[
                     ("sub", _("Search whole subtree below the base DN")),
                     ("base", _("Search only the entry at the base DN")),
                     ("one", _("Search all entries one level below the base DN")),
                 ],
                 default_value="sub",
             )),
            ("group_filter",
             TextUnicode(
                 title=_("Search Filter"),
                 help=_("Using this option you can define an optional LDAP filter which is used "
                        "during group related LDAP searches. It can be used to only handle a "
                        "subset of the groups below the given base DN.<br><br>"
                        "e.g. <tt>(objectclass=group)</tt>"),
                 size=80,
                 default_value=lambda: ldap_filter_of_connection(self._connection_id, 'groups',
                                                                 False),
                 attrencode=True,
             )),
            ("group_member",
             TextAscii(
                 title=_("Member Attribute"),
                 help=_("The attribute used to identify users group memberships."),
                 default_value=lambda: ldap_attr_of_connection(self._connection_id, 'member'),
                 attrencode=True,
             )),
        ]

        return group_elements

    def _other_elements(self):
        other_elements = [
            ("active_plugins",
             Dictionary(
                 title=_('Attribute Sync Plugins'),
                 help=
                 _('It is possible to fetch several attributes of users, like Email or full names, '
                   'from the LDAP directory. This is done by plugins which can individually enabled '
                   'or disabled. When enabling a plugin, it is used upon the next synchonisation of '
                   'user accounts for gathering their attributes. The user options which get imported '
                   'into Check_MK from LDAP will be locked in WATO.'),
                 elements=lambda: ldap_attribute_plugins_elements(self._connection),
                 default_keys=['email', 'alias', 'auth_expire'],
             )),
            ("cache_livetime",
             Age(
                 title=_('Sync Interval'),
                 help=
                 _('This option defines the interval of the LDAP synchronization. This setting is only '
                   'used by sites which have the '
                   '<a href="wato.py?mode=sites">Automatic User '
                   'Synchronization</a> enabled.<br><br>'
                   'Please note: Passwords of the users are never stored in WATO and therefor never cached!'
                  ),
                 minvalue=60,
                 default_value=300,
                 display=["days", "hours", "minutes"],
             )),
        ]

        return other_elements

    def _validate_ldap_connection_id(self, value, varprefix):
        if value in [c['id'] for c in config.user_connections]:
            raise MKUserError(
                varprefix,
                _("This ID is already used by another connection. Please choose another one."))

    def _validate_ldap_connection(self, value, varprefix):
        for role_id, group_specs in value["active_plugins"].get("groups_to_roles", {}).items():
            if role_id == "nested":
                continue  # This is the option to enabled/disable nested group handling, not a role to DN entry

            for index, group_spec in enumerate(group_specs):
                dn, connection_id = group_spec

                if connection_id is None:
                    group_dn = value["group_dn"]

                else:
                    connection = get_connection(connection_id)
                    if not connection:
                        continue
                    assert isinstance(connection, LDAPUserConnector)
                    group_dn = connection.get_group_dn()

                if not group_dn:
                    raise MKUserError(
                        varprefix,
                        _("You need to configure the group base DN to be able to "
                          "use the roles synchronization plugin."))

                if not dn.lower().endswith(group_dn.lower()):
                    varname = "connection_p_active_plugins_p_groups_to_roles_p_%s_1_%d" % (role_id,
                                                                                           index)
                    raise MKUserError(varname,
                                      _("The configured DN does not match the group base DN."))

    def _validate_ldap_connection_suffix(self, value, varprefix):
        for connection in config.user_connections:
            suffix = connection.get("suffix")
            if suffix is None:
                continue

            connection_id = connection["id"]
            if connection_id != self._connection_id and value == suffix:
                raise MKUserError(
                    varprefix,
                    _("This suffix is already used by connection %s."
                      "Please choose another one.") % connection_id)


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The LDAP User Connector provides some kind of plugin mechanism to    |
#   | modulize which ldap attributes are synchronized and how they are     |
#   | synchronized into Checkmk. The standard attribute plugins           |
#   | are defnied here.                                                    |
#   '----------------------------------------------------------------------'


class LDAPAttributePlugin(metaclass=abc.ABCMeta):
    """Base class for all LDAP attribute synchronization plugins"""
    @abc.abstractproperty
    def ident(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self) -> str:
        raise NotImplementedError()

    @abc.abstractproperty
    def is_builtin(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def lock_attributes(self, params: Dict) -> List[str]:
        """List of user attributes to lock

        Normally the attributes that are modified by the sync_func()"""
        raise NotImplementedError()

    @abc.abstractmethod
    def needed_attributes(self, connection: LDAPUserConnector, params: Dict) -> List[str]:
        """Gathers the LDAP user attributes that are needed by this plugin"""
        raise NotImplementedError()

    # TODO: plugin is not needed anymore?
    @abc.abstractmethod
    def sync_func(self, connection: LDAPUserConnector, plugin: dict, params: dict, user_id: str,
                  ldap_user: dict, user: dict) -> dict:
        """Executed during user synchronization to modify the "user" structure"""
        raise NotImplementedError()

    def parameters(self, connection: LDAPUserConnector) -> Union[FixedValue, Dictionary]:
        return FixedValue(
            title=self.title,
            help=self.help,
            value={},
            totext=_('This synchronization plugin has no parameters.'),
        )

    #Dictionary(
    #    title=plugin['title'],
    #    help=plugin['help'],
    #    elements=plugin['parameters'],
    #    required_keys=plugin.get('required_parameters', []),
    #)))

    @property
    def multisite_attributes(self) -> List[str]:
        """When a plugin introduces new user attributes, it should declare the output target for
        this attribute. It can either be written to the multisites users.mk or the check_mk
        contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
        contacts.mk file."""
        return []

    @property
    def non_contact_attributes(self) -> List[str]:
        """When a plugin introduces new user attributes, it should declare the output target for
        this attribute. It can either be written to the multisites users.mk or the check_mk
        contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
        contacts.mk file."""
        return []


class LDAPAttributePluginRegistry(cmk.utils.plugin_registry.Registry[Type[LDAPAttributePlugin]]):
    def plugin_name(self, instance):
        return instance().ident


class LDAPBuiltinAttributePlugin(LDAPAttributePlugin):
    """Base class for all builtin based sync plugins"""
    @property
    def is_builtin(self):
        return True


class LDAPUserAttributePlugin(LDAPAttributePlugin):
    """Base class for all custom user attribute based sync plugins"""
    @property
    def is_builtin(self):
        return False


ldap_attribute_plugin_registry = LDAPAttributePluginRegistry()


def ldap_attribute_plugins_elements(connection):
    """Returns a list of pairs (key, parameters) of all available attribute plugins"""
    elements = []
    items = sorted(
        [(ident, plugin_class()) for ident, plugin_class in ldap_attribute_plugin_registry.items()],
        key=lambda x: x[1].title)
    for key, plugin in items:
        elements.append((key, plugin.parameters(connection)))
    return elements


def register_user_attribute_sync_plugins():
    """Register sync plugins for all custom user attributes (assuming simple data types)"""
    # Remove old user attribute plugins
    for ident, plugin_class in list(ldap_attribute_plugin_registry.items()):
        plugin = plugin_class()
        if not plugin.is_builtin:
            ldap_attribute_plugin_registry.unregister(ident)

    for name, attr in get_user_attributes():
        plugin_class = type(
            "LDAPUserAttributePlugin%s" % name.title(), (LDAPUserAttributePlugin,), {
                "ident": name,
                "title": attr.valuespec().title(),
                "help": attr.valuespec().help(),
                'needed_attributes': lambda self, connection, params:
                                     [params.get("attr", connection.ldap_attr(self.ident)).lower()],
                'lock_attributes': lambda self, params: [self.ident],
                'parameters': lambda self, connection: Dictionary(
                    title=self.title,
                    help=self.help,
                    elements=[
                        ('attr',
                         TextAscii(
                             title=_("LDAP attribute to sync"),
                             help=
                             _("The LDAP attribute whose contents shall be synced into this custom attribute."
                              ),
                             default_value=lambda: ldap_attr_of_connection(
                                 connection.id(), self.ident),
                         )),
                    ],
                ),
                'sync_func': lambda self, connection, plugin, params, user_id, ldap_user, user:
                             ldap_sync_simple(user_id, ldap_user, user, plugin,
                                              self.needed_attributes(connection, params)[0]),
            })
        ldap_attribute_plugin_registry.register(plugin_class)


# Helper function for gathering the default LDAP attribute names of a connection.
def ldap_attr_of_connection(connection_id, attr):
    connection = get_connection(connection_id)
    if not connection:
        # Handle "new connection" situation where there is no connection object existant yet.
        # The default type is "Active directory", so we use it here.
        return ldap_attr_map["ad"].get(attr, attr).lower()

    assert isinstance(connection, LDAPUserConnector)
    return connection.ldap_attr(attr)


# Helper function for gathering the default LDAP filters of a connection.
def ldap_filter_of_connection(connection_id, *args, **kwargs):
    connection = get_connection(connection_id)
    if not connection:
        # Handle "new connection" situation where there is no connection object existant yet.
        # The default type is "Active directory", so we use it here.
        return ldap_filter_map["ad"].get(args[0], '(objectclass=*)')

    assert isinstance(connection, LDAPUserConnector)
    return connection.ldap_filter(*args, **kwargs)


def ldap_sync_simple(user_id, ldap_user, user, user_attr, attr):
    if attr in ldap_user:
        attr_value = ldap_user[attr][0]
        # LDAP attribute in boolean format sends str "TRUE" or "FALSE"
        if user_attr == 'disable_notifications':
            return {user_attr: {'disable': attr_value == "TRUE"}}
        return {user_attr: attr_value}
    return {}


def get_connection_choices(add_this=True):
    choices = []

    if add_this:
        choices.append((None, _("This connection")))

    for connection in load_connection_config():
        descr = connection['description']
        if not descr:
            descr = connection['id']
        choices.append((connection['id'], descr))

    return choices


# This is either the user id or the user distinguished name,
# depending on the LDAP server to communicate with
def get_group_member_cmp_val(connection, user_id, ldap_user):
    return user_id if connection._member_attr().lower() == 'memberuid' else ldap_user['dn']


def get_groups_of_user(connection, user_id, ldap_user, cg_names, nested, other_connection_ids):
    # Figure out how to check group membership.
    user_cmp_val = get_group_member_cmp_val(connection, user_id, ldap_user)

    # Get list of LDAP connections to query
    connections = {connection}
    for connection_id in other_connection_ids:
        c = get_connection(connection_id)
        if c:
            connections.add(c)

    # Load all LDAP groups which have a CN matching one contact
    # group which exists in WATO
    ldap_groups: GroupMemberships = {}
    for conn in connections:
        ldap_groups.update(conn.get_group_memberships(cg_names, nested=nested))

    # Now add the groups the user is a member off
    group_cns = []
    for group in ldap_groups.values():
        if user_cmp_val in group['members']:
            group_cns.append(group['cn'])

    return group_cns


def _group_membership_parameters():
    return [
        ('nested',
         FixedValue(
             title=_('Handle nested group memberships (Active Directory only at the moment)'),
             help=_('Once you enable this option, this plugin will not only handle direct '
                    'group memberships, instead it will also dig into nested groups and treat '
                    'the members of those groups as contact group members as well. Please mind '
                    'that this feature might increase the execution time of your LDAP sync.'),
             value=True,
             totext=_('Nested group memberships are resolved'),
         )),
        ('other_connections',
         ListChoice(
             title=_("Sync group memberships from other connections"),
             help=_(
                 "This is a special feature for environments where user accounts are located "
                 "in one LDAP directory and groups objects having them as members are located "
                 "in other directories. You should only enable this feature when you are in this "
                 "situation and really need it. The current connection is always used."),
             choices=lambda: get_connection_choices(add_this=False),
             default_value=[None],
         )),
    ]


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginMail(LDAPBuiltinAttributePlugin):
    @property
    def ident(self):
        return "email"

    @property
    def title(self):
        return _('Email address')

    @property
    def help(self):
        return _('Synchronizes the email of the LDAP user account into Checkmk.')

    def lock_attributes(self, params):
        return ['email']

    def needed_attributes(self, connection, params):
        return [params.get('attr', connection.ldap_attr('mail')).lower()]

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        mail = ''
        mail_attr = params.get('attr', connection.ldap_attr('mail')).lower()
        if ldap_user.get(mail_attr):
            mail = ldap_user[mail_attr][0].lower()

        if mail:
            return {'email': mail}
        return {}

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                ("attr",
                 TextAscii(
                     title=_("LDAP attribute to sync"),
                     help=_("The LDAP attribute containing the mail address of the user."),
                     default_value=lambda: ldap_attr_of_connection(connection.id(), 'mail'),
                 )),
            ],
        )


#.
#   .--Alias---------------------------------------------------------------.
#   |                           _    _ _                                   |
#   |                          / \  | (_) __ _ ___                         |
#   |                         / _ \ | | |/ _` / __|                        |
#   |                        / ___ \| | | (_| \__ \                        |
#   |                       /_/   \_\_|_|\__,_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginAlias(LDAPBuiltinAttributePlugin):
    @property
    def ident(self):
        return "alias"

    @property
    def title(self):
        return _('Alias')

    @property
    def help(self):
        return _('Populates the alias attribute of the WATO user by synchronizing an attribute '
                 'from the LDAP user account. By default the LDAP attribute <tt>cn</tt> is used.')

    def lock_attributes(self, params):
        return ['alias']

    def needed_attributes(self, connection, params):
        return [params.get('attr', connection.ldap_attr('cn')).lower()]

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        return ldap_sync_simple(user_id, ldap_user, user, 'alias',
                                params.get('attr', connection.ldap_attr('cn')).lower())

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                ("attr",
                 TextAscii(
                     title=_("LDAP attribute to sync"),
                     help=_("The LDAP attribute containing the alias of the user."),
                     default_value=lambda: ldap_attr_of_connection(connection.id(), 'cn'),
                 )),
            ],
        )


#.
#   .--Auth Expire---------------------------------------------------------.
#   |           _         _   _       _____            _                   |
#   |          / \  _   _| |_| |__   | ____|_  ___ __ (_)_ __ ___          |
#   |         / _ \| | | | __| '_ \  |  _| \ \/ / '_ \| | '__/ _ \         |
#   |        / ___ \ |_| | |_| | | | | |___ >  <| |_) | | | |  __/         |
#   |       /_/   \_\__,_|\__|_| |_| |_____/_/\_\ .__/|_|_|  \___|         |
#   |                                           |_|                        |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginAuthExpire(LDAPBuiltinAttributePlugin):
    """Checks whether or not the user auth must be invalidated

    This is done by increasing the auth serial of the user. In first instance, it must parse
    the pw-changed field, then check whether or not a date has been stored in the user before
    and then maybe increase the serial."""
    @property
    def ident(self):
        return "auth_expire"

    @property
    def title(self):
        return _('Authentication Expiration')

    @property
    def help(self):
        return _('This plugin fetches all information which are needed to check whether or '
                 'not an already authenticated user should be deauthenticated, e.g. because '
                 'the password has changed in LDAP or the account has been locked.')

    def lock_attributes(self, params):
        return ['locked']

    @property
    def multisite_attributes(self) -> List[str]:
        return ["ldap_pw_last_changed"]

    @property
    def non_contact_attributes(self) -> List[str]:
        return ["ldap_pw_last_changed"]

    def needed_attributes(self, connection, params):
        attrs = [params.get('attr', connection.ldap_attr('pw_changed')).lower()]

        # Fetch user account flags to check locking
        if connection.is_active_directory():
            attrs.append('useraccountcontrol')
        return attrs

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        # Special handling for active directory: Is the user enabled / disabled?
        if connection.is_active_directory() and ldap_user.get('useraccountcontrol'):
            # see http://www.selfadsi.de/ads-attributes/user-userAccountControl.htm for details
            locked_in_ad = int(ldap_user['useraccountcontrol'][0]) & 2
            locked_in_cmk = user.get("locked", False)

            if locked_in_ad and not locked_in_cmk:
                return {
                    'locked': True,
                    'serial': user.get('serial', 0) + 1,
                }
            if not locked_in_ad and locked_in_cmk:
                return {
                    'locked': False,
                }

        changed_attr = params.get('attr', connection.ldap_attr('pw_changed')).lower()
        if changed_attr not in ldap_user:
            raise MKLDAPException(
                _('The "Authentication Expiration" attribute (%s) could not be fetched '
                  'from the LDAP server for user %s.') % (changed_attr, ldap_user))

        # For keeping this thing simple, we don't parse the date here. We just store
        # the last value of the field in the user data and invalidate the auth if the
        # value has been changed.

        if 'ldap_pw_last_changed' not in user:
            return {'ldap_pw_last_changed': ldap_user[changed_attr][0]}  # simply store

        # Update data (and invalidate auth) if the attribute has changed
        if user['ldap_pw_last_changed'] != ldap_user[changed_attr][0]:
            return {
                'ldap_pw_last_changed': ldap_user[changed_attr][0],
                'serial': user.get('serial', 0) + 1,
            }

        return {}

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                ("attr",
                 TextAscii(
                     title=_("LDAP attribute to be used as indicator"),
                     help=_("When the value of this attribute changes for a user account, all "
                            "current authenticated sessions of the user are invalidated and the "
                            "user must login again. By default this field uses the fields which "
                            "hold the time of the last password change of the user."),
                     default_value=lambda: ldap_attr_of_connection(connection.id(), 'pw_changed'),
                 )),
            ],
        )


#.
#   .--Pager---------------------------------------------------------------.
#   |                     ____                                             |
#   |                    |  _ \ __ _  __ _  ___ _ __                       |
#   |                    | |_) / _` |/ _` |/ _ \ '__|                      |
#   |                    |  __/ (_| | (_| |  __/ |                         |
#   |                    |_|   \__,_|\__, |\___|_|                         |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginPager(LDAPBuiltinAttributePlugin):
    @property
    def ident(self):
        return "pager"

    @property
    def title(self):
        return _('Pager')

    @property
    def help(self):
        return _(
            'This plugin synchronizes a field of the users LDAP account to the pager attribute '
            'of the WATO user accounts, which is then forwarded to the monitoring core and can be used'
            'for notifications. By default the LDAP attribute <tt>mobile</tt> is used.')

    def lock_attributes(self, params):
        return ['pager']

    def needed_attributes(self, connection, params):
        return [params.get('attr', connection.ldap_attr('mobile')).lower()]

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        return ldap_sync_simple(user_id, ldap_user, user, 'pager',
                                params.get('attr', connection.ldap_attr('mobile')).lower())

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=[
                ('attr',
                 TextAscii(
                     title=_("LDAP attribute to sync"),
                     help=_("The LDAP attribute containing the pager number of the user."),
                     default_value=lambda: ldap_attr_of_connection(connection.id(), 'mobile'),
                 )),
            ],
        )


#.
#   .--Contactgroups-------------------------------------------------------.
#   |   ____            _             _                                    |
#   |  / ___|___  _ __ | |_ __ _  ___| |_ __ _ _ __ ___  _   _ _ __  ___   |
#   | | |   / _ \| '_ \| __/ _` |/ __| __/ _` | '__/ _ \| | | | '_ \/ __|  |
#   | | |__| (_) | | | | || (_| | (__| || (_| | | | (_) | |_| | |_) \__ \  |
#   |  \____\___/|_| |_|\__\__,_|\___|\__\__, |_|  \___/ \__,_| .__/|___/  |
#   |                                    |___/                |_|          |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginGroupsToContactgroups(LDAPBuiltinAttributePlugin):
    @property
    def ident(self):
        return "groups_to_contactgroups"

    @property
    def title(self):
        return _('Contactgroup Membership')

    @property
    def help(self):
        return _('Adds the user to contactgroups based on the group memberships in LDAP. This '
                 'plugin adds the user only to existing contactgroups while the name of the '
                 'contactgroup must match the common name (cn) of the LDAP group.')

    def lock_attributes(self, params):
        return ['contactgroups']

    def needed_attributes(self, connection, params):
        return []

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        # Gather all group names to search for in LDAP
        from cmk.gui.groups import load_contact_group_information
        cg_names = load_contact_group_information().keys()

        return {
            "contactgroups": get_groups_of_user(connection, user_id, ldap_user, cg_names,
                                                params.get('nested', False),
                                                params.get("other_connections", []))
        }

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=_group_membership_parameters(),
        )


#.
#   .--Group-Attrs.--------------------------------------------------------.
#   |      ____                               _   _   _                    |
#   |     / ___|_ __ ___  _   _ _ __         / \ | |_| |_ _ __ ___         |
#   |    | |  _| '__/ _ \| | | | '_ \ _____ / _ \| __| __| '__/ __|        |
#   |    | |_| | | | (_) | |_| | |_) |_____/ ___ \ |_| |_| |  \__ \_       |
#   |     \____|_|  \___/ \__,_| .__/     /_/   \_\__|\__|_|  |___(_)      |
#   |                          |_|                                         |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginGroupAttributes(LDAPBuiltinAttributePlugin):
    """Populate user attributes based on group memberships within LDAP"""
    @property
    def ident(self):
        return "groups_to_attributes"

    @property
    def title(self):
        return _('Groups to custom user attributes')

    @property
    def help(self):
        return _('Sets custom user attributes based on the group memberships in LDAP. This '
                 'plugin can be used to set custom user attributes to specified values '
                 'for all users which are member of a group in LDAP. The specified group '
                 'name must match the common name (CN) of the LDAP group.')

    def lock_attributes(self, params):
        attrs = []
        for group_spec in params["groups"]:
            attr_name, _value = group_spec["attribute"]
            attrs.append(attr_name)
        return attrs

    def needed_attributes(self, connection, params):
        return []

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        # Which groups need to be checked whether or not the user is a member?
        cg_names = list({g["cn"] for g in params["groups"]})

        # Get the group names the user is member of
        groups = get_groups_of_user(connection, user_id, ldap_user, cg_names,
                                    params.get('nested', False),
                                    params.get("other_connections", []))

        # Now construct the user update dictionary
        update = {}

        # First clean all previously set values from attributes to be synced where
        # user is not a member of
        user_attrs = dict(get_user_attributes())
        for group_spec in params["groups"]:
            attr_name, value = group_spec["attribute"]
            if group_spec["cn"] not in groups \
               and attr_name in user \
               and attr_name in user_attrs:
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

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=_group_membership_parameters() + [
                ('groups',
                 ListOf(
                     Dictionary(
                         elements=[
                             ('cn',
                              TextUnicode(
                                  title=_("Group<nobr> </nobr>CN"),
                                  size=40,
                                  allow_empty=False,
                              )),
                             ('attribute',
                              CascadingDropdown(
                                  title=_("Attribute to set"),
                                  choices=self._get_user_attribute_choices,
                              )),
                         ],
                         optional_keys=[],
                     ),
                     title=_("Groups to synchronize"),
                     help=
                     _("Specify the groups to control the value of a given user attribute. If a user is "
                       "not a member of a group, the attribute will be left at it's default value. When "
                       "a single attribute is set by multiple groups and a user is member of multiple "
                       "of these groups, the later plugin in the list will override the others."),
                     allow_empty=False,
                 )),
            ],
            required_keys=["groups"],
        )

    def _get_user_attribute_choices(self):
        return [(name, attr.valuespec().title(), attr.valuespec())
                for name, attr in get_user_attributes()]


#.
#   .--Roles---------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@ldap_attribute_plugin_registry.register
class LDAPAttributePluginGroupsToRoles(LDAPBuiltinAttributePlugin):
    @property
    def ident(self):
        return "groups_to_roles"

    @property
    def title(self):
        return _('Roles')

    @property
    def help(self):
        return _(
            'Configures the roles of the user depending on its group memberships '
            'in LDAP.<br><br>'
            'Please note: Additionally the user is assigned to the '
            '<a href="wato.py?mode=edit_configvar&varname=default_user_profile&site=&folder=">Default Roles</a>. '
            'Deactivate them if unwanted.')

    def lock_attributes(self, params):
        return ['roles']

    def needed_attributes(self, connection, params):
        return []

    def sync_func(self, connection, plugin, params, user_id, ldap_user, user):
        ldap_groups = self.fetch_needed_groups_for_groups_to_roles(connection, params)

        # posixGroup objects use the memberUid attribute to specify the group
        # memberships. This is the username instead of the users DN. So the
        # username needs to be used for filtering here.
        user_cmp_val = get_group_member_cmp_val(connection, user_id, ldap_user)

        roles = set()

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
                if dn in ldap_groups and user_cmp_val in ldap_groups[dn]['members']:
                    roles.add(role_id)

        # Load default roles from default user profile when the user got no role
        # by the role sync plugin
        if not roles:
            roles = config.default_user_profile['roles'][:]

        return {'roles': list(roles)}

    def fetch_needed_groups_for_groups_to_roles(self, connection, params):
        # Load the needed LDAP groups, which match the DNs mentioned in the role sync plugin config
        ldap_groups = {}
        for connection_id, group_dns in self._get_groups_to_fetch(connection, params).items():
            conn = get_connection(connection_id)
            if conn is None:
                continue
            assert isinstance(conn, LDAPUserConnector)

            ldap_groups.update(
                dict(
                    conn.get_group_memberships(group_dns,
                                               filt_attr='distinguishedname',
                                               nested=params.get('nested', False))))

        return ldap_groups

    def _get_groups_to_fetch(self, connection, params):
        groups_to_fetch: Dict[str, List[str]] = {}
        for group_specs in params.values():
            if isinstance(group_specs, list):
                for group_spec in group_specs:
                    if isinstance(group_spec, tuple):
                        this_conn_id = group_spec[1]
                        if this_conn_id is None:
                            this_conn_id = connection.id()
                        groups_to_fetch.setdefault(this_conn_id, [])
                        groups_to_fetch[this_conn_id].append(group_spec[0].lower())
                    else:
                        # Be compatible to old config format (no connection specified)
                        this_conn_id = connection.id()
                        groups_to_fetch.setdefault(this_conn_id, [])
                        groups_to_fetch[this_conn_id].append(group_spec.lower())

            elif isinstance(group_specs, str):
                # Need to be compatible to old config formats
                this_conn_id = connection.id()
                groups_to_fetch.setdefault(this_conn_id, [])
                groups_to_fetch[this_conn_id].append(group_specs.lower())

        return groups_to_fetch

    def parameters(self, connection):
        return Dictionary(
            title=self.title,
            help=self.help,
            elements=self._list_roles_with_group_dn,
        )

    def _list_roles_with_group_dn(self):
        elements: List[DictionaryEntry] = []
        for role_id, role in load_roles().items():
            elements.append((
                role_id,
                Transform(
                    ListOf(
                        Transform(
                            Tuple(elements=[
                                LDAPDistinguishedName(
                                    title=_("Group<nobr> </nobr>DN"),
                                    size=80,
                                    allow_empty=False,
                                ),
                                DropdownChoice(
                                    title=_("Search<nobr> </nobr>in"),
                                    choices=get_connection_choices,
                                    default_value=None,
                                ),
                            ],),
                            # convert old distinguished names to tuples
                            forth=lambda v: (v,) if not isinstance(v, tuple) else v,
                        ),
                        title=role['alias'],
                        help=_(
                            "Distinguished Names of the LDAP groups to add users this role. "
                            "e. g. <tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt><br> "
                            "This group must be defined within the scope of the "
                            "<a href=\"wato.py?mode=ldap_config&varname=ldap_groupspec\">LDAP Group Settings</a>."
                        ),
                        movable=False,
                    ),
                    # convert old single distinguished names to list of :Ns
                    forth=lambda v: [v] if not isinstance(v, list) else v,
                )))

        elements.append(
            ('nested',
             FixedValue(
                 title=_('Handle nested group memberships (Active Directory only at the moment)'),
                 help=_('Once you enable this option, this plugin will not only handle direct '
                        'group memberships, instead it will also dig into nested groups and treat '
                        'the members of those groups as contact group members as well. Please mind '
                        'that this feature might increase the execution time of your LDAP sync.'),
                 value=True,
                 totext=_('Nested group memberships are resolved'),
             )))
        return elements
