#!/usr/bin/python
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

# TODO FIXME: Change attribute sync plugins to classes. The current dict
# based approach is not very readable. Classes/objects make it a lot
# easier to understand the mechanics.

# TODO: Think about some subclassing for the different directory types.
# This would make some code a lot easier to understand.

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

import os
import time
import copy
import sys
import shutil

# docs: http://www.python-ldap.org/doc/html/index.html
import ldap
import ldap.filter
from ldap.controls import SimplePagedResultsControl

from multiprocessing.pool import ThreadPool
from multiprocessing.pool import TimeoutError

import cmk.paths

import sites
import config
import watolib
import log
import cmk.log
from lib import *


from htmllib import RequestTimeout

# LDAP attributes are case insensitive, we only use lower case!
# Please note: This are only default values. The user might override this
# by configuration.
ldap_attr_map = {
    'ad': {
        'user_id':    'samaccountname',
        'pw_changed': 'pwdlastset',
    },
    'openldap': {
        'user_id':    'uid',
        'pw_changed': 'pwdchangedtime',
        # group attributes
        'member':     'uniquemember',
    },
    '389directoryserver': {
        'user_id':    'uid',
        'pw_changed': 'krbPasswordExpiration',
        # group attributes
        'member':     'member',
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


def ldap_test_module():
    try:
        ldap
    except:
        raise MKLDAPException(_("The python module python-ldap seems to be missing. You need to "
                                "install this extension to make the LDAP user connector work."))


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

class LDAPUserConnector(UserConnector):
    # stores the ldap connection suffixes of all connections
    connection_suffixes = {}

    @classmethod
    def transform_config(cls, config):
        if not config:
            return config

        # For a short time in git master the directory_type could be:
        # ('ad', {'discover_nearest_dc': True/False})
        if type(config["directory_type"]) == tuple and config["directory_type"][0] == "ad" \
           and "discover_nearest_dc" in config["directory_type"][1]:
            auto_discover = config["directory_type"][1]["discover_nearest_dc"]

            if not auto_discover:
                config["directory_type"] = "ad"
            else:
                config["directory_type"] = (config["directory_type"][0], {
                    "connect_to": ("discover", {
                        "domain": config["server"],
                    }),
                })

        if type(config["directory_type"]) != tuple and "server" in config:
            # Old separate configuration of directory_type and server
            servers = {
                    "server": config["server"],
            }

            if "failover_servers" in config:
                servers["failover_servers"] = config["failover_servers"]

            config["directory_type"] = (config["directory_type"], {
                "connect_to": ("fixed_list", servers),
            })

        return config


    def __init__(self, config):
        super(LDAPUserConnector, self).__init__(self.transform_config(config))

        self._ldap_obj        = None
        self._ldap_obj_config = None
        self._logger          = log.logger.getChild("ldap.Connection(%s)" % self.id())

        self._user_cache  = {}
        self._group_cache = {}

        # File for storing the time of the last success event
        self._sync_time_file = cmk.paths.var_dir + '/web/ldap_%s_sync_time.mk'% self.id()

        self.save_suffix()


    @classmethod
    def type(self):
        return 'ldap'


    @classmethod
    def title(self):
        return _('LDAP (Active Directory, OpenLDAP)')


    @classmethod
    def short_title(self):
        return _('LDAP')


    @classmethod
    def get_connection_suffixes(self):
        return self.connection_suffixes


    def id(self):
        return self._config['id']


    def connect_server(self, server):
        try:
            trace_args = {}
            if self._logger.isEnabledFor(cmk.log.DEBUG):
                os.environ["GNUTLS_DEBUG_LEVEL"] = "99"
                ldap.set_option(ldap.OPT_DEBUG_LEVEL, 4095)
                trace_args["trace_level"] = 2

            uri = self.format_ldap_uri(server)
            conn = ldap.ldapobject.ReconnectLDAPObject(uri, **trace_args)
            conn.protocol_version = self._config.get('version', 3)
            conn.network_timeout  = self._config.get('connect_timeout', 2.0)
            conn.retry_delay      = 0.5

            # When using the domain top level as base-dn, the subtree search stumbles with referral objects.
            # whatever. We simply disable them here when using active directory. Hope this fixes all problems.
            if self.is_active_directory():
                conn.set_option(ldap.OPT_REFERRALS, 0)

            if 'use_ssl' in self._config:
                conn.set_option(ldap.OPT_X_TLS_CACERTFILE,
                            "%s/var/ssl/ca-certificates.crt" % cmk.paths.omd_root)

                # Caused trouble on older systems or systems with some special configuration or set of
                # libraries. For example we saw a Ubuntu 17.10 system with libldap  2.4.45+dfsg-1ubuntu1 and
                # libgnutls30 3.5.8-6ubuntu3 raising "ValueError: option error" while another system with
                # the exact same liraries did not. Try to do this on systems that support this call and ignore
                # the errors on other systems.
                try:
                    conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
                except ValueError:
                    pass

            self.default_bind(conn)
            return conn, None

        except (ldap.SERVER_DOWN, ldap.TIMEOUT, ldap.LOCAL_ERROR, ldap.LDAPError), e:
            self.clear_nearest_dc_cache()
            if type(e[0]) == dict:
                msg = e[0].get('info', e[0].get('desc', ''))
            else:
                msg = "%s" % e

            return None, "%s: %s" % (uri, msg)

        except MKLDAPException, e:
            self.clear_nearest_dc_cache()
            return None, "%s" % e


    def format_ldap_uri(self, server):
        if self.use_ssl():
            uri = 'ldaps://'
        else:
            uri = 'ldap://'

        if "port" in self._config:
            port_spec = ":%d" % self._config["port"]
        else:
            port_spec = ""

        return uri + server + port_spec


    def connect(self, enforce_new = False, enforce_server = None):
        connection_id = self.id()

        if not enforce_new \
           and self._ldap_obj \
           and self._config == self._ldap_obj_config:
            self._logger.info('LDAP CONNECT - Using existing connecting')
            return # Use existing connections (if connection settings have not changed)
        else:
            self._logger.info('LDAP CONNECT - Connecting...')
            self.disconnect()

        ldap_test_module()

        # Some major config var validations

        if not self._config['user_dn']:
            raise MKLDAPException(_('The distinguished name of the container object, which holds '
                                    'the user objects to be authenticated, is not configured. Please '
                                    'fix this in the <a href="wato.py?mode=ldap_config">'
                                    'LDAP User Settings</a>.'))

        try:
            errors = []
            if enforce_server:
                servers = [ enforce_server ]
            else:
                servers = self.servers()

            for server in servers:
                ldap_obj, error_msg = self.connect_server(server)

                if ldap_obj:
                    self._ldap_obj = ldap_obj
                else:
                    errors.append(error_msg)
                    continue # In case of an error, try the (optional) fallback servers

            # Got no connection to any server
            if self._ldap_obj is None:
                raise MKLDAPException(_('LDAP connection failed:\n%s') %
                                            ('\n'.join(errors)))

            # on success, store the connection options the connection has been made with
            self._ldap_obj_config = copy.deepcopy(self._config)

        except Exception:
            # Invalidate connection on failure
            ldap_obj = None
            self.disconnect()
            raise

    def disconnect(self):
        self._ldap_obj = None
        self._ldap_obj_config = None


    def _discover_nearest_dc(self, domain):
        cached_server = self._get_nearest_dc_from_cache()
        if cached_server:
            self._logger.info(_('Using cached DC %s') % cached_server)
            return cached_server

        import ad  # pylint: disable=import-error
        locator = ad.Locator()
        locator.m_logger = self._logger
        try:
            server = locator.locate(domain)
            self._cache_nearest_dc(server)
            self._logger.info('  DISCOVERY: Discovered server %r from %r' % (server, domain))
            return server
        except Exception:
            self._logger.info('  DISCOVERY: Failed to discover a server from domain %r' % domain)
            self._logger.exception("Exception details:")
            self._logger.info('  DISCOVERY: Try to use domain DNS name %r as server' % domain)
            return domain


    def _get_nearest_dc_from_cache(self):
        try:
            return file(self._nearest_dc_cache_filepath()).read()
        except IOError:
            pass


    def _cache_nearest_dc(self, server):
        self._logger.debug(_('Caching nearest DC %s') % server)
        cmk.store.save_file(self._nearest_dc_cache_filepath(), server)


    def clear_nearest_dc_cache(self):
        if not self._uses_discover_nearest_server():
            return

        try:
            os.unlink(self._nearest_dc_cache_filepath())
        except OSError:
            pass

    def _nearest_dc_cache_filepath(self):
        return os.path.join(self._ldap_caches_filepath(), "nearest_server.%s" % self.id())


    @classmethod
    def _ldap_caches_filepath(cls):
        return os.path.join(cmk.paths.tmp_dir, "ldap_caches")


    @classmethod
    def config_changed(cls):
        cls.clear_all_ldap_caches()


    @classmethod
    def clear_all_ldap_caches(cls):
        try:
            shutil.rmtree(cls._ldap_caches_filepath())
        except OSError, e:
            if e.errno != 2:
                raise


    # Bind with the default credentials
    def default_bind(self, conn):
        try:
            if 'bind' in self._config:
                self.bind(self.replace_macros(self._config['bind'][0]),
                          self._config['bind'][1], catch = False, conn = conn)
            else:
                self.bind('', '', catch = False, conn = conn) # anonymous bind
        except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH):
            raise MKLDAPException(_('Unable to connect to LDAP server with the configured bind credentials. '
                                    'Please fix this in the '
                                    '<a href="wato.py?mode=ldap_config">LDAP connection settings</a>.'))


    def bind(self, user_dn, password, catch = True, conn = None):
        if conn is None:
            conn = self._ldap_obj
        self._logger.info('LDAP_BIND %s' % user_dn)
        try:
            conn.simple_bind_s(user_dn.encode("utf-8"), password)
            self._logger.info('  SUCCESS')
        except ldap.LDAPError, e:
            self._logger.info('  FAILED (%s: %s)' % (e.__class__.__name__, e))
            if catch:
                raise MKLDAPException(_('Unable to authenticate with LDAP (%s)') % e)
            else:
                raise


    def servers(self):
        connect_params = self._get_connect_params()
        if self._uses_discover_nearest_server():
            servers = [ self._discover_nearest_dc(connect_params["domain"]) ]
        else:
            servers = [ connect_params['server'] ] + connect_params.get('failover_servers', [])

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


    def directory_type(self):
        return self._config['directory_type'][0]


    def is_active_directory(self):
        return self.directory_type() == 'ad'


    def has_user_base_dn_configured(self):
        return self._config['user_dn'] != ''


    def create_users_only_on_login(self):
        return self._config.get('create_only_on_login', False)


    def user_id_attr(self):
        return self._config.get('user_id', self.ldap_attr('user_id'))


    def member_attr(self):
        return self._config.get('group_member', self.ldap_attr('member'))


    def has_bind_credentials_configured(self):
        return self._config.get('bind', ('', ''))[0] != ''


    def has_group_base_dn_configured(self):
        return self._config['group_dn'] != ''


    def get_group_dn(self):
        return self.replace_macros(self._config['group_dn'])


    def get_user_dn(self):
        return self.replace_macros(self._config['user_dn'])


    def get_suffix(self):
        return self._config.get('suffix')


    def has_suffix(self):
        return self._config.get('suffix') != None


    def save_suffix(self):
        suffix = self.get_suffix()
        if suffix:
            if suffix in LDAPUserConnector.connection_suffixes \
               and LDAPUserConnector.connection_suffixes[suffix] != self.id():
                raise MKUserError(None, _("Found duplicate LDAP connection suffix. "
                                          "The LDAP connections %s and %s both use "
                                          "the suffix %s which is not allowed.") %
                                          (LDAPUserConnector.connection_suffixes[suffix],
                                           self.id(), suffix))
            else:
                LDAPUserConnector.connection_suffixes[suffix] = self.id()


    # Returns a list of all needed LDAP attributes of all enabled plugins
    def needed_attributes(self):
        attrs = set([])
        for key, params in self._config['active_plugins'].items():
            plugin = ldap_attribute_plugins[key]
            if 'needed_attributes' in plugin:
                attrs.update(plugin['needed_attributes'](self, params or {}))
        return list(attrs)


    def object_exists(self, dn):
        try:
            return bool(self.ldap_search(dn, columns = ['dn'], scope = 'base'))
        except Exception, e:
            return False


    def user_base_dn_exists(self):
        return self.object_exists(self.get_user_dn())


    def group_base_dn_exists(self):
        return self.object_exists(self.get_group_dn())


    def ldap_paged_async_search(self, base, scope, filt, columns):
        self._logger.info('  PAGED ASYNC SEARCH')
        page_size = self._config.get('page_size', 1000)

        lc = SimplePagedResultsControl(size = page_size, cookie = '')

        results = []
        while True:
            # issue the ldap search command (async)
            msgid = self._ldap_obj.search_ext(base, scope, filt, columns, serverctrls = [lc])

            unused_code, response, unused_msgid, serverctrls = self._ldap_obj.result3(
                msgid = msgid, timeout = self._config.get('response_timeout', 5)
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


    def ldap_search(self, base, filt='(objectclass=*)', columns=None, scope='sub', implicit_connect=True):
        if columns == None:
            columns = []

        self._logger.info('LDAP_SEARCH "%s" "%s" "%s" "%r"' % (base, scope, filt, columns))
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
                    for dn, obj in self.ldap_paged_async_search(make_utf8(base),
                                        self.ldap_get_scope(scope), make_utf8(filt), columns):
                        if dn is None:
                            continue # skip unwanted answers
                        new_obj = {}
                        for key, val in obj.iteritems():
                            # Convert all keys to lower case!
                            new_obj[key.decode('utf-8').lower()] = [ i.decode('utf-8') for i in val ]
                        result.append((dn.decode('utf-8').lower(), new_obj))
                    success = True
                except ldap.NO_SUCH_OBJECT, e:
                    raise MKLDAPException(_('The given base object "%s" does not exist in LDAP (%s))') % (base, e))

                except ldap.FILTER_ERROR, e:
                    raise MKLDAPException(_('The given ldap filter "%s" is invalid (%s)') % (filt, e))

                except ldap.SIZELIMIT_EXCEEDED:
                    raise MKLDAPException(_('The response reached a size limit. This could be due to '
                                            'a sizelimit configuration on the LDAP server.<br />Throwing away the '
                                            'incomplete results. You should change the scope of operation '
                                            'within the ldap or adapt the limit settings of the LDAP server.'))
            except (ldap.SERVER_DOWN, ldap.TIMEOUT, MKLDAPException), e:
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
                raise MKLDAPException(_('Unable to successfully perform the LDAP search '
                                        '(Base: %s, Scope: %s, Filter: %s, Columns: %s): %s') %
                                        (html.attrencode(base), html.attrencode(scope),
                                        html.attrencode(filt), html.attrencode(','.join(columns)),
                                        last_exc))
            else:
                raise MKLDAPException(_('Unable to successfully perform the LDAP search (%s)') % last_exc)

        self._logger.info('  RESULT length: %d, duration: %0.3f' % (len(result), duration))
        return result


    def ldap_get_scope(self, scope):
        # Had "subtree" in Check_MK for several weeks. Better be compatible to both definitions.
        if scope in [ 'sub', 'subtree' ]:
            return ldap.SCOPE_SUBTREE
        elif scope == 'base':
            return ldap.SCOPE_BASE
        elif scope == 'one':
            return ldap.SCOPE_ONELEVEL
        else:
            raise Exception('Invalid scope specified: %s' % scope)


    # Returns the ldap filter depending on the configured ldap directory type
    def ldap_filter(self, key, handle_config = True):
        value = ldap_filter_map[self.directory_type()].get(key, '(objectclass=*)')
        if handle_config:
            if key == 'users':
                value = self._config.get('user_filter', value)
            elif key == 'groups':
                value = self._config.get('group_filter', value)
        return self.replace_macros(value)


    # Returns the ldap attribute name depending on the configured ldap directory type
    # If a key is not present in the map, the assumption is, that the key matches 1:1
    # Always use lower case here, just to prevent confusions.
    def ldap_attr(self, key):
        return ldap_attr_map[self.directory_type()].get(key, key).lower()


    # Returns the given distinguished name template with replaced vars
    def replace_macros(self, tmpl):
        dn = tmpl

        for key, val in [ ('$OMD_SITE$', config.omd_site()) ]:
            if val:
                dn = dn.replace(key, val)
            else:
                dn = dn.replace(key, '')

        return dn


    def sanitize_user_id(self, user_id):
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


    def get_user(self, username, no_escape = False):
        if username in self._user_cache:
            return self._user_cache[username]

        user_id_attr = self.user_id_attr()

        # Check whether or not the user exists in the directory matching the username AND
        # the user search filter configured in the "LDAP User Settings".
        # It's only ok when exactly one entry is found. Returns the DN and user_id
        # as tuple in this case.
        result = self.ldap_search(
            self.get_user_dn(),
            '(&(%s=%s)%s)' % (user_id_attr, ldap.filter.escape_filter_chars(username),
                              self._config.get('user_filter', '')),
            [user_id_attr],
            self._config['user_scope']
        )

        if not result:
            return None

        dn = result[0][0]
        raw_user_id = result[0][1][user_id_attr][0]

        # Filter out users by the optional filter_group
        filter_group_dn = self._config.get('user_filter_group', None)
        if filter_group_dn:
            member_attr = self.member_attr().lower()
            is_member = False
            for member in self.get_filter_group_members(filter_group_dn):
                if member_attr == "memberuid" and raw_user_id == member:
                    is_member = True
                elif dn == member:
                    is_member = True

            if not is_member:
                return None

        user_id = self.sanitize_user_id(raw_user_id)
        if user_id is None:
            return None
        self._user_cache[username] = (dn, user_id)

        if no_escape:
            return (dn, user_id)
        else:
            return (dn.replace('\\', '\\\\'), user_id)



    def get_users(self, add_filter = ''):
        user_id_attr = self.user_id_attr()

        columns = [
            user_id_attr, # needed in all cases as uniq id
        ] + self.needed_attributes()

        filt = self.ldap_filter('users')

        # Create filter by the optional filter_group
        filter_group_dn = self._config.get('user_filter_group', None)
        if filter_group_dn:
            member_attr = self.member_attr().lower()
            # posixGroup objects use the memberUid attribute to specify the group memberships.
            # This is the username instead of the users DN. So the username needs to be used
            # for filtering here.
            user_cmp_attr = user_id_attr if member_attr == 'memberuid' else 'distinguishedname'

            member_filter_items = []
            for member in self.get_filter_group_members(filter_group_dn):
                member_filter_items.append('(%s=%s)' % (user_cmp_attr, member))
            add_filter += '(|%s)' % ''.join(member_filter_items)

        if add_filter:
            filt = '(&%s%s)' % (filt, add_filter)

        result = {}
        for dn, ldap_user in self.ldap_search(self.get_user_dn(),
                                         filt, columns, self._config['user_scope']):
            if user_id_attr not in ldap_user:
                raise MKLDAPException(_('The configured User-ID attribute "%s" does not '
                                        'exist for the user "%s"') % (user_id_attr, dn))
            user_id = self.sanitize_user_id(ldap_user[user_id_attr][0])
            if user_id:
                ldap_user['dn'] = dn # also add the DN
                result[user_id] = ldap_user

        return result


    # TODO: Use get_group_memberships()?
    def get_filter_group_members(self, filter_group_dn):
        member_attr = self.member_attr().lower()

        try:
            group = self.ldap_search(self.replace_macros(filter_group_dn), columns=[member_attr], scope='base')
        except MKLDAPException:
            group = None

        if not group:
            raise MKLDAPException(_('The configured ldap user filter group could not be found. '
                                    'Please check <a href="%s">your configuration</a>.') %
                                        'wato.py?mode=ldap_config&varname=ldap_userspec')

        return [ m.lower() for m in group[0][1].values()[0] ]


    def get_groups(self, specific_dn = None):
        filt = self.ldap_filter('groups')
        dn   = self.get_group_dn()

        if specific_dn:
            # When using AD, the groups can be filtered by the DN attribute. With
            # e.g. OpenLDAP this is not possible. In that case, change the DN.
            if self.is_active_directory():
                filt = '(&%s(distinguishedName=%s))' % (filt, specific_dn)
            else:
                dn = specific_dn

        return self.ldap_search(dn, filt, ['cn'], self._config['group_scope'])


    def get_group_memberships(self, filters, filt_attr = 'cn', nested = False):
        cache_key = (tuple(filters), nested, filt_attr)
        if cache_key in self._group_cache:
            return self._group_cache[cache_key]

        if not nested:
            groups = self.get_direct_group_memberships(filters, filt_attr)
        else:
            groups = self.get_nested_group_memberships(filters, filt_attr)

        self._group_cache[cache_key] = groups
        return groups


    # When not searching for nested memberships, it is easy when using the an AD base LDAP.
    # The group objects can be queried using the attribute distinguishedname. Therefor we
    # create an alternating match filter to match that attribute when searching by DNs.
    # In OpenLDAP the distinguishedname is no user attribute, therefor it can not be used
    # as filter expression. We have to do one ldap query per group. Maybe, in the future,
    # we change the role sync plugin parameters to snapins to make this part a little easier.
    def get_direct_group_memberships(self, filters, filt_attr):
        groups = {}
        filt = self.ldap_filter('groups')
        member_attr = self.member_attr().lower()

        if self.is_active_directory() or filt_attr != 'distinguishedname':
            if filters:
                add_filt = '(|%s)' % ''.join([ '(%s=%s)' % (filt_attr, f) for f in filters ])
                filt = '(&%s%s)' % (filt, add_filt)

            for dn, obj in self.ldap_search(self.get_group_dn(), filt, ['cn', member_attr],
                                            self._config['group_scope']):
                groups[dn] = {
                    'cn'      : obj['cn'][0],
                    'members' : [ m.lower() for m in obj.get(member_attr,[]) ],
                }
        else:
            # Special handling for OpenLDAP when searching for groups by DN
            for f_dn in filters:
                for dn, obj in self.ldap_search(self.replace_macros(f_dn), filt,
                                                ['cn', member_attr], 'base'):
                    groups[f_dn] = {
                        'cn'      : obj['cn'][0],
                        'members' : [ m.lower() for m in obj.get(member_attr,[]) ],
                    }

        return groups


    # Nested querying is more complicated. We have no option to simply do a query for group objects
    # to make them resolve the memberships here. So we need to query all users with the nested
    # memberof filter to get all group memberships of that group. We need one query for each group.
    def get_nested_group_memberships(self, filters, filt_attr):
        groups = {}
        for filter_val in filters:
            matched_groups = {}

            if filt_attr == 'cn':
                result = self.ldap_search(self.get_group_dn(),
                                     '(&%s(cn=%s))' % (self.ldap_filter('groups'), filter_val),
                                     ['dn', 'cn'], self._config['group_scope'])
                if not result:
                    continue # Skip groups which can not be found

                for dn, attrs in result:
                    matched_groups[dn] = attrs["cn"][0]
            else:
                # in case of asking with DNs in nested mode, the resulting objects have the
                # cn set to None for all objects. We do not need it in that case.
                matched_groups[filter_val] = None

            for dn, cn in matched_groups.items():
                filt = '(&%s(memberOf:1.2.840.113556.1.4.1941:=%s))' % \
                        (self.ldap_filter('users'), dn)
                groups[dn] = {
                    'members' : [],
                    'cn'      : cn,
                }
                for user_dn, obj in self.ldap_search(self.get_user_dn(),
                                                     filt, ['dn'], self._config['user_scope']):
                    groups[dn]['members'].append(user_dn.lower())

        return groups


    #
    # USERDB API METHODS
    #

    # With release 1.2.7i3 we introduced multi ldap server connection capabilities.
    # We had to change the configuration declaration to reflect the new possibilites.
    # This function migrates the former configuration to the new one.
    # TODO This code can be removed the day we decide not to migrate old configs anymore.
    @classmethod
    def migrate_config(self):
        if config.user_connections:
            return # Don't try to migrate anything when there is at least one connection configured

        if self.needs_config_migration():
            self.do_migrate_config()


    # Don't migrate anything when no ldap connection has been configured
    @classmethod
    def needs_config_migration(self):
        ldap_connection = getattr(config, 'ldap_connection', {})
        default_ldap_connection_config = {
            'type'      : 'ad',
            'page_size' : 1000,
        }
        return ldap_connection and ldap_connection != default_ldap_connection_config


    @classmethod
    def do_migrate_config(self):
        # Create a default connection out of the old config format
        connection = {
            'id'             : 'default',
            'type'           : 'ldap',
            'description'    : _('This is the default LDAP connection.'),
            'disabled'       : 'ldap' not in getattr(config, 'user_connectors', []),
            'cache_livetime' : getattr(config, 'ldap_cache_livetime', 300),
            'active_plugins' : getattr(config, 'ldap_active_plugins', []) or {'email': {}, 'alias': {}, 'auth_expire': {}},
            'directory_type' : getattr(config, 'ldap_connection', {}).get('type', 'ad'),
            'user_id_umlauts': 'keep',
            'user_dn'        : '',
            'user_scope'     : 'sub',
        }

        old_connection_cfg = getattr(config, 'ldap_connection', {})
        try:
            del old_connection_cfg['type']
        except KeyError:
            pass
        connection.update(old_connection_cfg)

        for what in ["user", "group"]:
            for key, val in getattr(config, 'ldap_'+what+'spec', {}).items():
                if key in ["dn", "scope", "filter", "filter_group", "member"]:
                    key = what + "_" + key
                connection[key] = val

        save_connection_config([connection])
        config.user_connections.append(connection)


    # This function only validates credentials, no locked checking or similar
    def check_credentials(self, username, password):
        self.connect()

        # Did the user provide an suffix with his username? This might enforce
        # LDAP connections to be choosen or skipped.
        # self.user_enforces_this_connection can return either:
        #   True:  This connection is enforced
        #   False: Another connection is enforced
        #   None:  No connection is enforced
        enforce_this_connection = self.user_enforces_this_connection(username)
        if enforce_this_connection == False:
            return None # Skip this connection, another one is enforced
        else:
            username = self.strip_suffix(username)

        # Returns None when the user is not found or not uniq, else returns the
        # distinguished name and the username as tuple which are both needed for
        # the further login process.
        result = self.get_user(username, True)
        if not result:
            # The user does not exist
            if enforce_this_connection:
                return False # Refuse login
            else:
                return None # Try next connection (if available)

        user_dn, username = result

        # Try to bind with the user provided credentials. This unbinds the default
        # authentication which should be rebound again after trying this.
        try:
            self.bind(user_dn, password)
            result = username
        except:
            self._logger.exception("  Exception during authentication (User: %s)", username)
            result = False

        self.default_bind(self._ldap_obj)
        return result


    def user_enforces_this_connection(self, username):
        suffixes = LDAPUserConnector.get_connection_suffixes()

        matched_connection_ids = []
        for suffix, connection_id in LDAPUserConnector.get_connection_suffixes().items():
            if self.username_matches_suffix(username, suffix):
                matched_connection_ids.append(connection_id)

        if not matched_connection_ids:
            return None
        elif len(matched_connection_ids) > 1:
            raise MKUserError(None, _("Unable to match connection"))
        else:
            return matched_connection_ids[0] == self.id()


    def username_matches_suffix(self, username, suffix):
        return username.endswith('@' + suffix)


    def strip_suffix(self, username):
        suffix = self.get_suffix()
        if suffix and self.username_matches_suffix(username, suffix):
            return username[:-(len(suffix)+1)]
        else:
            return username


    def add_suffix(self, username):
        suffix = self.get_suffix()
        return '%s@%s' % (username, suffix)


    def do_sync(self, add_to_changelog, only_username):
        if not self.has_user_base_dn_configured():
            self._logger.info("Not trying sync (no \"user base DN\" configured)")
            return # silently skip sync without configuration

        register_user_attribute_sync_plugins()

        # Flush ldap related before each sync to have a caching only for the
        # current sync process
        self.flush_caches()

        start_time = time.time()
        connection_id = self.id()

        self._logger.info('SYNC STARTED')
        self._logger.info('  SYNC PLUGINS: %s' % ', '.join(self._config['active_plugins'].keys()))

        ldap_users = self.get_users()

        users = load_users(lock = True)

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
            if user_connection_id == connection_id and self.strip_suffix(user_id) not in ldap_users:
                del users[user_id] # remove the user
                changes.append(_("LDAP [%s]: Removed user %s") % (connection_id, user_id))


        has_changed_passwords = False
        for user_id, ldap_user in ldap_users.items():
            mode_create, user = load_user(user_id)
            user_connection_id = cleanup_connection_id(user.get('connector'))

            if self.create_users_only_on_login() and mode_create:
                self._logger.info('  SKIP SYNC "%s" (Only create user of "%s" connector on login)' %
                                                                        (user_id, user_connection_id))
                continue


            if only_username and user_id != only_username:
                continue # Only one user should be synced, skip others.

            # Name conflict: Found a user that has an equal name, but is not controlled
            # by this connector. Don't sync it. When an LDAP connection suffix is configured
            # use this for constructing a unique username. If not or if the name+suffix is
            # already taken too, skip this user silently.
            if user_connection_id != connection_id:
                if self.has_suffix():
                    user_id = self.add_suffix(user_id)
                    mode_create, user = load_user(user_id)
                    user_connection_id = cleanup_connection_id(user.get('connector'))
                    if user_connection_id != connection_id:
                        self._logger.info('  SKIP SYNC "%s" (name conflict after adding suffix '
                                 'with user from "%s" connector)' % (user_id, user_connection_id))
                        continue # added suffix, still name conflict
                else:
                    self._logger.info('  SKIP SYNC "%s" (name conflict with user from "%s" connector)' % (user_id, user_connection_id))
                    continue # name conflict, different connector

            self.execute_active_sync_plugins(user_id, ldap_user, user)

            if not mode_create and user == users[user_id]:
                continue # no modification. Skip this user.

            # Gather changed attributes for easier debugging
            if not mode_create:
                set_new, set_old = set(user.keys()), set(users[user_id].keys())
                intersect = set_new.intersection(set_old)
                added = set_new - intersect
                removed = set_old - intersect

                changed = self.find_changed_user_keys(intersect, users[user_id], user) # returns a dict

            users[user_id] = user # Update the user record
            if mode_create:
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
                    synchronize_profile_to_sites(self, user_id, user)

                if changed:
                    for key, (old_value, new_value) in sorted(changed.items()):
                        details.append(('Changed %s from %s to %s' % (key, old_value, new_value)))

                if details:
                    changes.append(_("LDAP [%s]: Modified user %s (%s)") % (connection_id, user_id, ', '.join(details)))

        duration = time.time() - start_time
        self._logger.info('SYNC FINISHED - Duration: %0.3f sec', duration)

        if changes and config.wato_enabled and not watolib.is_wato_slave_site():
            watolib.add_change("edit-users", HTML("<br>\n").join(changes), add_user=False)

        if changes or has_changed_passwords:
            save_users(users)
        else:
            release_users_lock()

        self.set_last_sync_time()


    def find_changed_user_keys(self, keys, user, new_user):
        changed = {}
        for key in keys:
            value = user[key]
            new_value = new_user[key]
            if type(value) == list and type(new_value) == list:
                is_changed = sorted(value) != sorted(new_value)
            else:
                is_changed = value != new_value
            if is_changed:
                changed[key] = (value, new_value)
        return changed


    def execute_active_sync_plugins(self, user_id, ldap_user, user):
        for key, params in self._config['active_plugins'].items():
            user.update(ldap_attribute_plugins[key]['sync_func'](self, key, params or {}, user_id, ldap_user, user))


    def flush_caches(self):
        self._user_cache.clear()
        self._group_cache.clear()


    def set_last_sync_time(self):
        file(self._sync_time_file, 'w').write('%s\n' % time.time())


    # no ldap check, just check the WATO attribute. This handles setups where
    # the locked attribute is not synchronized and the user is enabled in LDAP
    # and disabled in Check_MK. When the user is locked in LDAP a login is
    # not possible.
    def is_locked(self, user_id):
        return user_locked(user_id)


    def is_enabled(self):
        sync_config = user_sync_config()
        if type(sync_config) == tuple and self.id() not in sync_config[1]:
            #self._ldap_logger('Skipping disabled connection %s' % (self.id()))
            return False
        return True


    def sync_is_needed(self):
        return self.get_last_sync_time() + self.get_cache_livetime() <= time.time()


    def get_last_sync_time(self):
        try:
            return float(file(self._sync_time_file).read().strip())
        except:
            return 0


    def get_cache_livetime(self):
        return self._config['cache_livetime']


    # Calculates the attributes of the users which are locked for users managed
    # by this connector
    def locked_attributes(self):
        locked = set([ 'password' ]) # This attributes are locked in all cases!
        for key, params in self._config['active_plugins'].items():
            lock_attrs = ldap_attribute_plugins.get(key, {}).get('lock_attributes', [])
            if type(lock_attrs) == list:
                locked.update(lock_attrs)
            else: # maby be a function which returns a list
                locked.update(lock_attrs(params))
        return list(locked)


    # Calculates the attributes added in this connector which shal be written to
    # the multisites users.mk
    def multisite_attributes(self):
        attrs = set([])
        for key in self._config['active_plugins'].keys():
            attrs.update(ldap_attribute_plugins.get(key, {}).get('multisite_attributes', []))
        return list(attrs)


    # Calculates the attributes added in this connector which shal NOT be written to
    # the check_mks contacts.mk
    def non_contact_attributes(self):
        attrs = set([])
        for key in self._config['active_plugins'].keys():
            attrs.update(ldap_attribute_plugins.get(key, {}).get('non_contact_attributes', []))
        return list(attrs)


multisite_user_connectors['ldap'] = LDAPUserConnector

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
#   | synchronized into Check_MK. The standard attribute plugins           |
#   | are defnied here.                                                    |
#   '----------------------------------------------------------------------'

ldap_attribute_plugins = {}
ldap_builtin_attribute_plugin_names = []

# Returns a list of pairs (key, title) of all available attribute plugins
def ldap_list_attribute_plugins():
    plugins = []
    for key, plugin in ldap_attribute_plugins.items():
        plugins.append((key, plugin['title']))
    return plugins

# Returns a list of pairs (key, parameters) of all available attribute plugins
def ldap_attribute_plugins_elements(connection_id):
    global g_editing_connection_id
    g_editing_connection_id = connection_id

    register_user_attribute_sync_plugins()

    elements = []
    items = sorted(ldap_attribute_plugins.items(), key = lambda x: x[1]['title'])
    for key, plugin in items:
        if 'parameters' not in plugin:
            param = []
            elements.append((key, FixedValue(
                title    = plugin['title'],
                help     = plugin['help'],
                value    = {},
                totext   = 'no_param_txt' in plugin and plugin['no_param_txt'] \
                              or _('This synchronization plugin has no parameters.'),
            )))
        else:
            elements.append((key, Dictionary(
                title         = plugin['title'],
                help          = plugin['help'],
                elements      = plugin['parameters'],
                required_keys = plugin.get('required_parameters', []),
            )))
    return elements


# Register sync plugins for all custom user attributes (assuming simple data types)
def register_user_attribute_sync_plugins():
    # Save the names of the builtin (shipped) attribute sync plugins. These names
    # are needed below to delete the dynamically create sync plugins which are based
    # on the custom user attributes
    global ldap_builtin_attribute_plugin_names
    if not ldap_builtin_attribute_plugin_names:
        ldap_builtin_attribute_plugin_names = ldap_attribute_plugins.keys()

    # Remove old user attribute plugins
    for attr_name in ldap_attribute_plugins.keys():
        if attr_name not in ldap_builtin_attribute_plugin_names:
            del ldap_attribute_plugins[attr_name]

    def default_attr_value(attr):
        return lambda: ldap_attr_of_connection(g_editing_connection_id, attr)

    def needed_attributes(attr):
        return lambda connection, params: [ params.get('attr', connection.ldap_attr(attr)).lower() ]

    for attr, val in get_user_attributes():
        ldap_attribute_plugins[attr] = {
            'title': val['valuespec'].title(),
            'help':  val['valuespec'].help(),
            'needed_attributes': needed_attributes(attr),
            'sync_func':         lambda connection, plugin, params, user_id, ldap_user, user: \
                                         ldap_sync_simple(user_id, ldap_user, user, plugin,
                                                        params.get('attr', connection.ldap_attr(plugin)).lower()),
            'lock_attributes': [ attr ],
            'parameters': [
                ('attr', TextAscii(
                    title = _("LDAP attribute to sync"),
                    help  = _("The LDAP attribute whose contents shall be synced into this custom attribute."),
                    default_value = default_attr_value(attr),
                )),
            ],
        }

# This hack is needed to make the connection_id of the connection currently
# being edited (or None if being created) available in the "default_value"
# handler functions of the valuespec. There is no other standard way to
# transport this info to these functions.
g_editing_connection_id = None

# Helper function for gathering the default LDAP attribute names of a connection.
def ldap_attr_of_connection(connection_id, attr):
    connection = get_connection(connection_id)
    if not connection:
        # Handle "new connection" situation where there is no connection object existant yet.
        # The default type is "Active directory", so we use it here.
        return ldap_attr_map["ad"].get(attr, attr).lower()

    return connection.ldap_attr(attr)


# Helper function for gathering the default LDAP filters of a connection.
def ldap_filter_of_connection(connection_id, *args, **kwargs):
    connection = get_connection(connection_id)
    if not connection:
        # Handle "new connection" situation where there is no connection object existant yet.
        # The default type is "Active directory", so we use it here.
        return ldap_filter_map["ad"].get(args[0], '(objectclass=*)')

    return connection.ldap_filter(*args, **kwargs)


def ldap_sync_simple(user_id, ldap_user, user, user_attr, attr):
    if attr in ldap_user:
        return {user_attr: ldap_user[attr][0]}
    else:
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
    return user_id if connection.member_attr().lower() == 'memberuid' else ldap_user['dn']


def get_groups_of_user(connection, user_id, ldap_user, cg_names, nested, other_connection_ids):
    # Figure out how to check group membership.
    user_cmp_val = get_group_member_cmp_val(connection, user_id, ldap_user)

    # Get list of LDAP connections to query
    connections = set([connection])
    for connection_id in other_connection_ids:
        c = get_connection(connection_id)
        if c:
            connections.add(c)

    # Load all LDAP groups which have a CN matching one contact
    # group which exists in WATO
    ldap_groups = {}
    for conn in connections:
        ldap_groups.update(conn.get_group_memberships(cg_names, nested=nested))

    # Now add the groups the user is a member off
    group_cns = []
    for dn, group in ldap_groups.items():
        if user_cmp_val in group['members']:
            group_cns.append(group['cn'])

    return group_cns


group_membership_parameters = [
    ('nested', FixedValue(
            title    = _('Handle nested group memberships (Active Directory only at the moment)'),
            help     = _('Once you enable this option, this plugin will not only handle direct '
                         'group memberships, instead it will also dig into nested groups and treat '
                         'the members of those groups as contact group members as well. Please mind '
                         'that this feature might increase the execution time of your LDAP sync.'),
            value    = True,
            totext   = _('Nested group memberships are resolved'),
        )
    ),
    ('other_connections', ListChoice(
        title = _("Sync group memberships from other connections"),
        help = _("This is a special feature for environments where user accounts are located "
                 "in one LDAP directory and groups objects having them as members are located "
                 "in other directories. You should only enable this feature when you are in this "
                 "situation and really need it. The current connection is always used."),
        choices = lambda: get_connection_choices(add_this=False),
        default_value = [None],
    )),
]


#.
#   .--Mail----------------------------------------------------------------.
#   |                          __  __       _ _                            |
#   |                         |  \/  | __ _(_) |                           |
#   |                         | |\/| |/ _` | | |                           |
#   |                         | |  | | (_| | | |                           |
#   |                         |_|  |_|\__,_|_|_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def ldap_sync_mail(connection, plugin, params, user_id, ldap_user, user):
    mail = ''
    mail_attr = params.get('attr', connection.ldap_attr('mail')).lower()
    if ldap_user.get(mail_attr):
        mail = ldap_user[mail_attr][0].lower()

    if mail:
        return {'email': mail}
    else:
        return {}


def ldap_needed_attributes_mail(connection, params):
    return [ params.get('attr', connection.ldap_attr('mail')).lower() ]


ldap_attribute_plugins['email'] = {
    'title'             : _('Email address'),
    'help'              :  _('Synchronizes the email of the LDAP user account into Check_MK.'),
    'needed_attributes' : ldap_needed_attributes_mail,
    'sync_func'         : ldap_sync_mail,
    'lock_attributes'   : [ 'email' ],
    'parameters'        : [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the mail address of the user."),
            default_value = lambda: ldap_attr_of_connection(g_editing_connection_id, 'mail'),
        )),
    ],
}

#.
#   .--Alias---------------------------------------------------------------.
#   |                           _    _ _                                   |
#   |                          / \  | (_) __ _ ___                         |
#   |                         / _ \ | | |/ _` / __|                        |
#   |                        / ___ \| | | (_| \__ \                        |
#   |                       /_/   \_\_|_|\__,_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def ldap_sync_alias(connection, plugin, params, user_id, ldap_user, user):
    return ldap_sync_simple(user_id, ldap_user, user, 'alias',
                               params.get('attr', connection.ldap_attr('cn')).lower())


def ldap_needed_attributes_alias(connection, params):
    return [ params.get('attr', connection.ldap_attr('cn')).lower() ]


ldap_attribute_plugins['alias'] = {
    'title'             : _('Alias'),
    'help'              :  _('Populates the alias attribute of the WATO user by syncrhonizing an attribute '
                             'from the LDAP user account. By default the LDAP attribute <tt>cn</tt> is used.'),
    'needed_attributes' : ldap_needed_attributes_alias,
    'sync_func'         : ldap_sync_alias,
    'lock_attributes'   : [ 'alias' ],
    'parameters'        : [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the alias of the user."),
            default_value = lambda: ldap_attr_of_connection(g_editing_connection_id, 'cn'),
        )),
    ],
}

#.
#   .--Auth Expire---------------------------------------------------------.
#   |           _         _   _       _____            _                   |
#   |          / \  _   _| |_| |__   | ____|_  ___ __ (_)_ __ ___          |
#   |         / _ \| | | | __| '_ \  |  _| \ \/ / '_ \| | '__/ _ \         |
#   |        / ___ \ |_| | |_| | | | | |___ >  <| |_) | | | |  __/         |
#   |       /_/   \_\__,_|\__|_| |_| |_____/_/\_\ .__/|_|_|  \___|         |
#   |                                           |_|                        |
#   +----------------------------------------------------------------------+
#   | Checks whether or not the user auth must be invalidated (increasing   |
#   | the serial). In first instance, it must parse the pw-changed field,  |
#   | then check whether or not a date has been stored in the user before   |
#   | and then maybe increase the serial.                                  |
#   '----------------------------------------------------------------------'

def ldap_sync_auth_expire(connection, plugin, params, user_id, ldap_user, user):
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
        elif not locked_in_ad and locked_in_cmk:
            return {
                'locked': False,
            }

    changed_attr = params.get('attr', connection.ldap_attr('pw_changed')).lower()
    if not changed_attr in ldap_user:
        raise MKLDAPException(_('The "Authentication Expiration" attribute (%s) could not be fetched '
                                'from the LDAP server for user %s.') % (changed_attr, ldap_user))

    # For keeping this thing simple, we don't parse the date here. We just store
    # the last value of the field in the user data and invalidate the auth if the
    # value has been changed.

    if 'ldap_pw_last_changed' not in user:
        return {'ldap_pw_last_changed': ldap_user[changed_attr][0]} # simply store

    # Update data (and invalidate auth) if the attribute has changed
    if user['ldap_pw_last_changed'] != ldap_user[changed_attr][0]:
        return {
            'ldap_pw_last_changed': ldap_user[changed_attr][0],
            'serial':               user.get('serial', 0) + 1,
        }

    return {}


def ldap_needed_attributes_auth_expire(connection, params):
    attrs = [ params.get('attr', connection.ldap_attr('pw_changed')).lower() ]

    # Fetch user account flags to check locking
    if connection.is_active_directory():
        attrs.append('useraccountcontrol')
    return attrs


ldap_attribute_plugins['auth_expire'] = {
    'title'                  : _('Authentication Expiration'),
    'help'                   : _('This plugin fetches all information which are needed to check whether or '
                                 'not an already authenticated user should be deauthenticated, e.g. because '
                                 'the password has changed in LDAP or the account has been locked.'),
    'needed_attributes'      : ldap_needed_attributes_auth_expire,
    'sync_func'              : ldap_sync_auth_expire,
    'lock_attributes'        : ['locked'],
    # When a plugin introduces new user attributes, it should declare the output target for
    # this attribute. It can either be written to the multisites users.mk or the check_mk
    # contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
    # contacts.mk file.
    'multisite_attributes'   : ['ldap_pw_last_changed'],
    'non_contact_attributes' : ['ldap_pw_last_changed'],
    'parameters'             : [
        ("attr", TextAscii(
            title = _("LDAP attribute to be used as indicator"),
            help  = _("When the value of this attribute changes for a user account, all "
                      "current authenticated sessions of the user are invalidated and the "
                      "user must login again. By default this field uses the fields which "
                      "hold the time of the last password change of the user."),
            default_value = lambda: ldap_attr_of_connection(g_editing_connection_id, 'pw_changed'),
        )),
    ],
}

#.
#   .--Pager---------------------------------------------------------------.
#   |                     ____                                             |
#   |                    |  _ \ __ _  __ _  ___ _ __                       |
#   |                    | |_) / _` |/ _` |/ _ \ '__|                      |
#   |                    |  __/ (_| | (_| |  __/ |                         |
#   |                    |_|   \__,_|\__, |\___|_|                         |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'

def ldap_sync_pager(connection, plugin, params, user_id, ldap_user, user):
    return ldap_sync_simple(user_id, ldap_user, user, 'pager',
                        params.get('attr', connection.ldap_attr('mobile')).lower())


def ldap_needed_attributes_pager(connection, params):
    return [ params.get('attr', connection.ldap_attr('mobile')).lower() ]


ldap_attribute_plugins['pager'] = {
    'title'             : _('Pager'),
    'help'              :  _('This plugin synchronizes a field of the users LDAP account to the pager attribute '
                             'of the WATO user accounts, which is then forwarded to the monitoring core and can be used'
                             'for notifications. By default the LDAP attribute <tt>mobile</tt> is used.'),
    'needed_attributes' : ldap_needed_attributes_pager,
    'sync_func'         : ldap_sync_pager,
    'lock_attributes'   : ['pager'],
    'parameters'        : [
        ('attr', TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the pager number of the user."),
            default_value = lambda: ldap_attr_of_connection(g_editing_connection_id, 'mobile'),
        )),
    ],
}

#.
#   .--Contactgroups-------------------------------------------------------.
#   |   ____            _             _                                    |
#   |  / ___|___  _ __ | |_ __ _  ___| |_ __ _ _ __ ___  _   _ _ __  ___   |
#   | | |   / _ \| '_ \| __/ _` |/ __| __/ _` | '__/ _ \| | | | '_ \/ __|  |
#   | | |__| (_) | | | | || (_| | (__| || (_| | | | (_) | |_| | |_) \__ \  |
#   |  \____\___/|_| |_|\__\__,_|\___|\__\__, |_|  \___/ \__,_| .__/|___/  |
#   |                                    |___/                |_|          |
#   '----------------------------------------------------------------------'

def ldap_sync_groups_to_contactgroups(connection, plugin, params, user_id, ldap_user, user):
    # Gather all group names to search for in LDAP
    cg_names = load_group_information().get("contact", {}).keys()

    return {"contactgroups": get_groups_of_user(connection, user_id, ldap_user, cg_names,
                                                params.get('nested', False),
                                                params.get("other_connections", [])) }


ldap_attribute_plugins['groups_to_contactgroups'] = {
    'title': _('Contactgroup Membership'),
    'help':  _('Adds the user to contactgroups based on the group memberships in LDAP. This '
               'plugin adds the user only to existing contactgroups while the name of the '
               'contactgroup must match the common name (cn) of the LDAP group.'),
    'sync_func':         ldap_sync_groups_to_contactgroups,
    'lock_attributes':   ['contactgroups'],
    'parameters':        group_membership_parameters,
}

#.
#   .--Group-Attrs.--------------------------------------------------------.
#   |      ____                               _   _   _                    |
#   |     / ___|_ __ ___  _   _ _ __         / \ | |_| |_ _ __ ___         |
#   |    | |  _| '__/ _ \| | | | '_ \ _____ / _ \| __| __| '__/ __|        |
#   |    | |_| | | | (_) | |_| | |_) |_____/ ___ \ |_| |_| |  \__ \_       |
#   |     \____|_|  \___/ \__,_| .__/     /_/   \_\__|\__|_|  |___(_)      |
#   |                          |_|                                         |
#   +----------------------------------------------------------------------+
#   | Populate user attributes based on group memberships within LDAP      |
#   '----------------------------------------------------------------------'

def ldap_sync_groups_to_attributes(connection, plugin, params, user_id, ldap_user, user):
    # Which groups need to be checked whether or not the user is a member?
    cg_names = list(set([ g["cn"] for g in params["groups"] ]))

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
            update[attr_name] = user_attrs[attr_name]['valuespec'].default_value()

    # Set the values of the groups the user is a member of
    for group_spec in params["groups"]:
        attr_name, value = group_spec["attribute"]
        if group_spec["cn"] in groups:
            # is member, set the configured value
            update[attr_name] = value

    return update


# find out locked attributes depending on configuration
def ldap_locked_attributes_groups_to_attributes(params):
    attrs = []
    for group_spec in params["groups"]:
        attr_name, value = group_spec["attribute"]
        attrs.append(attr_name)
    return attrs


def get_user_attribute_choices():
    choices = []
    for attr, val in get_user_attributes():
        choices.append((attr, val['valuespec'].title(), val['valuespec']))
    return choices


ldap_attribute_plugins['groups_to_attributes'] = {
    'title': _('Groups to custom user attributes'),
    'help':  _('Sets custom user attributes based on the group memberships in LDAP. This '
               'plugin can be used to set custom user attributes to specified values '
               'for all users which are member of a group in LDAP. The specified group '
               'name must match the common name (CN) of the LDAP group.'),
    'sync_func':         ldap_sync_groups_to_attributes,
    'lock_attributes':   ldap_locked_attributes_groups_to_attributes,
    'parameters': group_membership_parameters + [
        ('groups', ListOf(
            Dictionary(
                elements = [
                    ('cn', TextUnicode(
                        title = _("Group<nobr> </nobr>CN"),
                        size = 40,
                        allow_empty = False,
                    )),
                    ('attribute', CascadingDropdown(
                        title = _("Attribute to set"),
                        choices = get_user_attribute_choices,
                    )),
                ],
                optional_keys = [],
            ),
            title = _("Groups to synchronize"),
            help = _("Specify the groups to control the value of a given user attribute. If a user is "
                     "not a member of a group, the attribute will be left at it's default value. When "
                     "a single attribute is set by multiple groups and a user is member of multiple "
                     "of these groups, the later plugin in the list will override the others."),
            allow_empty=False,
        )),
    ],
    'required_parameters': ["groups"],
}

#.
#   .--Roles---------------------------------------------------------------.
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def ldap_sync_groups_to_roles(connection, plugin, params, user_id, ldap_user, user):
    # Load the needed LDAP groups, which match the DNs mentioned in the role sync plugin config
    groups_to_fetch = get_groups_to_fetch(connection, params)

    ldap_groups = {}
    for connection_id, group_dns in get_groups_to_fetch(connection, params).items():
        conn = get_connection(connection_id)
        ldap_groups.update(dict(conn.get_group_memberships(group_dns,
                                filt_attr = 'distinguishedname',
                                nested = params.get('nested', False))))

    # posixGroup objects use the memberUid attribute to specify the group
    # memberships. This is the username instead of the users DN. So the
    # username needs to be used for filtering here.
    user_cmp_val = get_group_member_cmp_val(connection, user_id, ldap_user)

    roles = set([])

    # Loop all roles mentioned in params (configured to be synchronized)
    for role_id, group_specs in params.items():
        if type(group_specs) != list:
            group_specs = [group_specs] # be compatible to old single group configs

        for group_spec in group_specs:
            if type(group_spec) in [ str, unicode ]:
                dn = group_spec # be compatible to old config without connection spec
            elif type(group_spec) != tuple:
                continue # skip non configured ones (old valuespecs allowed None)
            else:
                dn = group_spec[0]
            dn = dn.lower() # lower case matching for DNs!

            # if group could be found and user is a member, add the role
            if dn in ldap_groups and user_cmp_val in ldap_groups[dn]['members']:
                roles.add(role_id)

    # Load default roles from default user profile when the user got no role
    # by the role sync plugin
    if not roles:
        roles = config.default_user_profile['roles'][:]

    return {'roles': list(roles)}


def get_groups_to_fetch(connection, params):
    groups_to_fetch = {}
    for role_id, group_specs in params.items():
        if type(group_specs) == list:
            for group_spec in group_specs:
                if type(group_spec) == tuple:
                    this_conn_id = group_spec[1]
                    if this_conn_id == None:
                        this_conn_id = connection.id()
                    groups_to_fetch.setdefault(this_conn_id, [])
                    groups_to_fetch[this_conn_id].append(group_spec[0].lower())
                else:
                    # Be compatible to old config format (no connection specified)
                    this_conn_id = connection.id()
                    groups_to_fetch.setdefault(this_conn_id, [])
                    groups_to_fetch[this_conn_id].append(group_spec.lower())

        elif type(group_specs) in [ str, unicode ]:
            # Need to be compatible to old config formats
            this_conn_id = connection.id()
            groups_to_fetch.setdefault(this_conn_id, [])
            groups_to_fetch[this_conn_id].append(group_specs.lower())

    return groups_to_fetch


def ldap_list_roles_with_group_dn():
    elements = []
    for role_id, role in load_roles().items():
        elements.append((role_id, Transform(
            ListOf(
                Transform(
                    Tuple(
                        elements = [
                            LDAPDistinguishedName(
                                title = _("Group<nobr> </nobr>DN"),
                                size = 80,
                                allow_empty = False,
                            ),
                            DropdownChoice(
                                title = _("Search<nobr> </nobr>in"),
                                choices = get_connection_choices,
                                default_value = None,
                            ),
                        ],
                    ),
                    # convert old distinguished names to tuples
                    forth = lambda v: (v, ) if not isinstance(v, tuple) else v,
                ),
                title = role['alias'],
                help  = _("Distinguished Names of the LDAP groups to add users this role. "
                          "e. g. <tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt><br> "
                          "This group must be defined within the scope of the "
                          "<a href=\"wato.py?mode=ldap_config&varname=ldap_groupspec\">LDAP Group Settings</a>."),
                movable = False,
            ),
            # convert old single distinguished names to list of :Ns
            forth = lambda v: [v] if not isinstance(v, list) else v,
        )))

    elements.append(
        ('nested', FixedValue(
                title    = _('Handle nested group memberships (Active Directory only at the moment)'),
                help     = _('Once you enable this option, this plugin will not only handle direct '
                             'group memberships, instead it will also dig into nested groups and treat '
                             'the members of those groups as contact group members as well. Please mind '
                             'that this feature might increase the execution time of your LDAP sync.'),
                value    = True,
                totext   = _('Nested group memberships are resolved'),
            )
        )
    )
    return elements

ldap_attribute_plugins['groups_to_roles'] = {
    'title'           : _('Roles'),
    'help'            :  _('Configures the roles of the user depending on its group memberships '
                           'in LDAP.<br><br>'
                           'Please note: Additionally the user is assigned to the '
                           '<a href="wato.py?mode=edit_configvar&varname=default_user_profile&site=&folder=">Default Roles</a>. '
                           'Deactivate them if unwanted.'),
    'sync_func'       : ldap_sync_groups_to_roles,
    'lock_attributes' : ['roles'],
    'parameters'      : ldap_list_roles_with_group_dn,
}


#.
#   .--WATO-Sync-----------------------------------------------------------.
#   |       __        ___  _____ ___       ____                            |
#   |       \ \      / / \|_   _/ _ \     / ___| _   _ _ __   ___          |
#   |        \ \ /\ / / _ \ | || | | |____\___ \| | | | '_ \ / __|         |
#   |         \ V  V / ___ \| || |_| |_____|__) | |_| | | | | (__          |
#   |          \_/\_/_/   \_\_| \___/     |____/ \__, |_| |_|\___|         |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# In case the sync is done on the master of a distributed setup the auth serial
# is increased on the master, but not on the slaves. The user can not access the
# slave sites anymore with the master sites cookie since the serials differ. In
# case the slave sites sync with LDAP on their own this issue will be repaired after
# the next LDAP sync on the slave, but in case the slaves do not sync, this problem
# will be repaired automagically once an admin performs the next WATO sync for
# another reason.
# Now, to solve this issue, we issue a user profile sync in case the password has
# been changed. We do this only when only the password has changed.
# Hopefully we have no large bulks of users changing their passwords at the same
# time. In this case the implementation does not scale well. We would need to
# change this to some kind of profile bulk sync per site.

class SynchronizationResult(object):
    def __init__(self, site_id, error_text=None, disabled=False, succeeded=False, failed=False):
        self.site_id = site_id
        self.error_text = error_text
        self.failed = failed
        self.disabled = disabled
        self.succeeded = succeeded


def synchronize_profile_to_sites(connection, user_id, profile):
    import sites
    import wato # FIXME: Cleanup!

    remote_sites = [(site_id, config.site(site_id))
                    for site_id in config.sitenames()
                    if not config.site_is_local(site_id) ]

    connection._logger.info('Credentials changed: %s. Trying to sync to %d sites' %
                                                    (user_id, len(remote_sites)))

    states = sites.states()

    pool = ThreadPool()
    jobs = []
    for site_id, site in remote_sites:
        jobs.append(pool.apply_async(_sychronize_profile_worker, ((states, site_id, site, user_id, profile),)))


    results = []
    start_time = time.time()
    while time.time() - start_time < 30:
        for job in jobs[:]:
            try:
                results.append(job.get(timeout=0.5))
                jobs.remove(job)
            except TimeoutError:
                pass
        if not jobs:
            break


    contacted_sites = set([x[0] for x in remote_sites])
    working_sites = set([result.site_id for result in results])
    for site_id in contacted_sites - working_sites:
        results.append(SynchronizationResult(site_id, error_text=_("No response from update thread"), failed=True))

    for result in results:
        if result.error_text:
            connection._logger.info('  FAILED [%s]: %s' % (result.site_id, result.error_text))
            if config.wato_enabled:
                watolib.add_change("edit-users", _('Password changed (sync failed: %s)') % result.error_text,
                                    add_user=False, sites=[result.site_id], need_restart=False)

    pool.terminate()
    pool.join()

    num_failed = sum([1 for result in results if result.failed])
    num_disabled = sum([1 for result in results if result.disabled])
    num_succeeded = sum([1 for result in results if result.succeeded])
    connection._logger.info('  Disabled: %d, Succeeded: %d, Failed: %d' %
                    (num_disabled, num_succeeded, num_failed))


def _sychronize_profile_worker(site_configuration):
    states, site_id, site, user_id, profile = site_configuration

    if not site.get("replication"):
        return SynchronizationResult(site_id, disabled=True)

    if site.get("disabled"):
        return SynchronizationResult(site_id, disabled=True)

    status = states.get(site_id, {}).get("state", "unknown")
    if status == "dead":
        return SynchronizationResult(site_id, error_text=_("Site %s is dead") % site_id, failed=True)

    try:
        result = watolib.push_user_profile_to_site(site, user_id, profile)
        return SynchronizationResult(site_id, succeeded=True)
    except RequestTimeout:
        # This function is currently only used by the background job
        # which does not have any request timeout set, just in case...
        raise
    except Exception, e:
        return SynchronizationResult(site_id, error_text="%s" % e, failed=True)
