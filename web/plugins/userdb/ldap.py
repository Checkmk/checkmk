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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

import config, defaults
import time, copy

try:
    # docs: http://www.python-ldap.org/doc/html/index.html
    import ldap
    import ldap.filter
    from ldap.controls import SimplePagedResultsControl

    # be compatible to both python-ldap below 2.4 and above
    try:
        LDAP_CONTROL_PAGED_RESULTS = ldap.LDAP_CONTROL_PAGE_OID
        ldap_compat = False
    except:
        LDAP_CONTROL_PAGED_RESULTS = ldap.CONTROL_PAGEDRESULTS
        ldap_compat = True
except:
    pass
from lib import *

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
        'member':     'uniquemember',
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

# All these characters are replaced from user ids by default. Check_MK
# currently does not support special characters in user ids, so users
# not matching this specification are cleaned up with this map. When the
# user accounts still do not match the specification, they are skipped.
ldap_umlaut_translation = {
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
    def __init__(self, config):
        super(LDAPUserConnector, self).__init__(config)

        self._ldap_obj        = None
        self._ldap_obj_config = None

        self._user_cache  = {}
        self._group_cache = {}

        # File for storing the time of the last success event
        self._sync_time_file = defaults.var_dir + '/web/ldap_%s_sync_time.mk'% self._config['id']
        # Exists when last ldap sync failed, contains exception text
        self._sync_fail_file = defaults.var_dir + '/web/ldap_%s_sync_fail.mk' % self._config['id']


    @classmethod
    def type(self):
        return 'ldap'


    @classmethod
    def title(self):
        return _('LDAP (Active Directory, OpenLDAP)')


    @classmethod
    def short_title(self):
        return _('LDAP')

    def log(self, s):
        if self._config['debug_log']:
            logger(LOG_DEBUG, 'LDAP [%s]: %s' % (self._config['id'], s))

    def connect_server(self, server):
        try:
            uri = self.format_ldap_uri(server)
            conn = ldap.ldapobject.ReconnectLDAPObject(uri)
            conn.protocol_version = self._config.get('version', 3)
            conn.network_timeout  = self._config.get('connect_timeout', 2.0)
            conn.retry_delay      = 0.5

            # When using the domain top level as base-dn, the subtree search stumbles with referral objects.
            # whatever. We simply disable them here when using active directory. Hope this fixes all problems.
            if self.is_active_directory():
                conn.set_option(ldap.OPT_REFERRALS, 0)

            self.default_bind(conn)
            return conn, None
        except (ldap.SERVER_DOWN, ldap.TIMEOUT, ldap.LOCAL_ERROR, ldap.LDAPError), e:
            return None, '%s: %s' % (uri, e[0].get('info', e[0].get('desc', '')))
        except MKLDAPException, e:
            return None, str(e)


    def format_ldap_uri(self, server):
        if 'use_ssl' in self._config:
            uri = 'ldaps://'
        else:
            uri = 'ldap://'
        return uri + '%s:%d' % (server, self._config.get('port', 389))


    def connect(self, enforce_new = False, enforce_server = None):
        connection_id = self._config['id']

        if not enforce_new \
           and not "no_persistent" in self._config \
           and self._ldap_obj \
           and self._config == self._ldap_obj_config:
            self.log('LDAP CONNECT - Using existing connecting')
            return # Use existing connections (if connection settings have not changed)
        else:
            self.log('LDAP CONNECT - Connecting...')

        ldap_test_module()

        # Some major config var validations

        if not self._config['server']:
            raise MKLDAPException(_('The LDAP connector is enabled in global settings, but the '
                                    'LDAP server to connect to is not configured. Please fix this in the '
                                    '<a href="wato.py?mode=ldap_config">LDAP '
                                    'connection settings</a>.'))

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
                    break # got a connection!
                else:
                    errors.append(error_msg)

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
        self.log('LDAP_BIND %s' % user_dn)
        try:
            conn.simple_bind_s(user_dn, password)
            self.log('  SUCCESS')
        except ldap.LDAPError, e:
            self.log('  FAILED (%s)' % e)
            if catch:
                raise MKLDAPException(_('Unable to authenticate with LDAP (%s)' % e))
            else:
                raise


    def servers(self):
        servers = [self._config['server'] ]
        if self._config.get('failover_servers'):
            servers += self._config.get('failover_servers')
        return servers


    def active_plugins(self):
        return self._config['active_plugins']


    def is_active_directory(self):
        return self._config['directory_type'] == 'ad'


    def has_user_base_dn_configured(self):
        return self._config['user_dn'] != ''


    def user_id_attr(self):
        return self._config.get('user_id', self.ldap_attr('user_id'))


    def member_attr(self):
        return self._config.get('group_member', self.ldap_attr('member'))


    def has_bind_credentials_configured(self):
        return self._config.get('bind', ('', ''))[0] != ''


    def has_group_base_dn_configured(self):
        return self._config['group_dn'] != ''


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
        return self.object_exists(self.replace_macros(self._config['user_dn']))


    def group_base_dn_exists(self):
        return self.object_exists(self.replace_macros(self._config['group_dn']))


    def ldap_async_search(self, base, scope, filt, columns):
        self.log('  ASYNC SEARCH')
        msgid = self._ldap_obj.search_ext(base, scope, filt, columns)

        results = []
        while True:
            restype, resdata = self._ldap_obj.result(msgid = msgid,
                timeout = self._config.get('response_timeout', 5))

            results.extend(resdata)
            if restype == ldap.RES_SEARCH_RESULT or not resdata:
                break

            # no limit at the moment
            #if sizelimit and len(users) >= sizelimit:
            #    self._ldap_obj.abandon_ext(msgid)
            #    break
            time.sleep(0.1)

        return results


    def ldap_paged_async_search(self, base, scope, filt, columns):
        self.log('  PAGED ASYNC SEARCH')
        page_size = self._config.get('page_size', 100)

        if ldap_compat:
            lc = SimplePagedResultsControl(size = page_size, cookie = '')
        else:
            lc = SimplePagedResultsControl(
                LDAP_CONTROL_PAGED_RESULTS, True, (page_size, '')
            )

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
                if serverctrl.controlType == LDAP_CONTROL_PAGED_RESULTS:
                    if ldap_compat:
                        cookie = serverctrl.cookie
                        if cookie:
                            lc.cookie = cookie
                    else:
                        cookie = serverctrl.controlValue[1]
                        if cookie:
                            lc.controlValue = (page_size, cookie)
                    break
            if not cookie:
                break
        return results


    def ldap_search(self, base, filt='(objectclass=*)', columns=[], scope='subtree'):
        self.log('LDAP_SEARCH "%s" "%s" "%s" "%r"' % (base, scope, filt, columns))
        start_time = time.time()

        # In some environments, the connection to the LDAP server does not seem to
        # be as stable as it is needed. So we try to repeat the query for three times.
        tries_left = 2
        success = False
        last_exc = None
        while not success:
            tries_left -= 1
            try:
                self.connect()
                result = []
                try:
                    search_func = self._config.get('page_size') \
                                  and self.ldap_paged_async_search or self.ldap_async_search
                    for dn, obj in search_func(base, self.ldap_get_scope(scope), filt, columns):
                        if dn is None:
                            continue # skip unwanted answers
                        new_obj = {}
                        for key, val in obj.iteritems():
                            # Convert all keys to lower case!
                            new_obj[key.lower().decode('utf-8')] = [ i.decode('utf-8') for i in val ]
                        result.append((dn.lower(), new_obj))
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
                last_exc = e
                if tries_left:
                    self.log('  Received %r. Retrying with clean connection...' % e)
                    ldap_disconnect()
                    time.sleep(0.5)
                else:
                    self.log('  Giving up.')
                    break

        duration = time.time() - start_time

        if not success:
            self.log('  FAILED')
            if config.debug:
                raise MKLDAPException(_('Unable to successfully perform the LDAP search '
                                        '(Base: %s, Scope: %s, Filter: %s, Columns: %s): %s') %
                                        (html.attrencode(base), html.attrencode(scope),
                                        html.attrencode(filt), html.attrencode(','.join(columns)),
                                        last_exc))
            else:
                raise MKLDAPException(_('Unable to successfully perform the LDAP search (%s)') % last_exc)

        self.log('  RESULT length: %d, duration: %0.3f' % (len(result), duration))
        return result


    def ldap_get_scope(self, scope):
        if scope == 'sub':
            return ldap.SCOPE_SUBTREE
        elif scope == 'base':
            return ldap.SCOPE_BASE
        elif scope == 'one':
            return ldap.SCOPE_ONELEVEL
        else:
            raise Exception('Invalid scope specified: %s' % scope)


    # Returns the ldap filter depending on the configured ldap directory type
    def ldap_filter(self, key, handle_config = True):
        value = ldap_filter_map[self._config['directory_type']].get(key, '(objectclass=*)')
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
        return ldap_attr_map[self._config['directory_type']].get(key, key).lower()


    # Returns the given distinguished name template with replaced vars
    def replace_macros(self, tmpl):
        dn = tmpl

        for key, val in [ ('$OMD_SITE$', defaults.omd_site) ]:
            if val:
                dn = dn.replace(key, val)
            else:
                dn = dn.replace(key, '')

        return dn


    def sanitize_user_id(self, user_id):
        if self._config.get('lower_user_ids', False):
            user_id = user_id.lower()

        umlauts = self._config.get('user_id_umlauts', 'replace')
        new_user_id = user_id.translate(ldap_umlaut_translation)

        if umlauts == 'replace':
            user_id = new_user_id
        elif umlauts == 'skip' and user_id != new_user_id:
            return None # This makes the user being skipped

        # Now check whether or not the user id matches our specification
        try:
            str(user_id)
        except UnicodeEncodeError:
            # Skipping this user: not all "bad" characters were replaced before
            self.log('Skipped user: %s (contains not allowed special characters)' % user_id)
            return None

        return user_id


    def get_user(self, username, no_escape = False):
        if username in self._user_cache:
            return self._user_cache[username]

        user_id_attr = self.user_id_attr()

        # Check wether or not the user exists in the directory matching the username AND
        # the user search filter configured in the "LDAP User Settings".
        # It's only ok when exactly one entry is found. Returns the DN and user_id
        # as tuple in this case.
        result = self.ldap_search(
            self.replace_macros(self._config['user_dn']),
            '(&(%s=%s)%s)' % (user_id_attr, ldap.filter.escape_filter_chars(username),
                              self._config.get('user_filter', '')),
            [user_id_attr],
            self._config['user_scope']
        )

        if result:
            dn = result[0][0]
            user_id = self.sanitize_user_id(result[0][1][user_id_attr][0])
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
        member_filter = ''
        if filter_group_dn:
            member_attr = self.member_attr().lower()
            # posixGroup objects use the memberUid attribute to specify the group memberships.
            # This is the username instead of the users DN. So the username needs to be used
            # for filtering here.
            user_cmp_attr = member_attr == 'memberuid' and user_id_attr or 'distinguishedname'

            # Apply configured group ldap filter
            try:
                group = self.ldap_search(self.replace_macros(filter_group_dn), [member_attr], 'base')
            except MKLDAPException:
                group = None

            if not group:
                raise MKLDAPException(_('The configured ldap user filter group could not be found. '
                                        'Please check <a href="%s">your configuration</a>.') %
                                            'wato.py?mode=ldap_config&varname=ldap_userspec')

            members = group[0][1].values()[0]

            member_filter_items = []
            for member in members:
                member_filter_items.append('(%s=%s)' % (user_cmp_attr, member))
            add_filter += '(|%s)' % ''.join(member_filter_items)

        if add_filter:
            filt = '(&%s%s)' % (filt, add_filter)

        result = {}
        for dn, ldap_user in self.ldap_search(self.replace_macros(self._config['user_dn']),
                                         filt, columns, self._config['user_scope']):
            if user_id_attr not in ldap_user:
                raise MKLDAPException(_('The configured User-ID attribute "%s" does not '
                                        'exist for the user "%s"') % (user_id_attr, dn))
            user_id = self.sanitize_user_id(ldap_user[user_id_attr][0])
            if user_id:
                ldap_user['dn'] = dn # also add the DN
                result[user_id] = ldap_user

        return result


    def get_groups(self, specific_dn = None):
        filt = self.ldap_filter('groups')
        dn   = self.replace_macros(self._config['group_dn'])

        if specific_dn:
            # When using AD, the groups can be filtered by the DN attribute. With
            # e.g. OpenLDAP this is not possible. In that case, change the DN.
            if self.is_active_directory():
                filt = '(&%s(distinguishedName=%s))' % (filt, specific_dn)
            else:
                dn = specific_dn

        return self.ldap_search(dn, filt, ['cn'], self._config['group_scope'])


    def group_members(self, filters, filt_attr = 'cn', nested = False):
        cache_key = '%s-%s-%s' % (filters, nested and 'n' or 'f', filt_attr)
        if cache_key in self._group_cache:
            return self._group_cache[cache_key]

        # When not searching for nested memberships, it is easy when using the an AD base LDAP.
        # The group objects can be queried using the attribute distinguishedname. Therefor we
        # create an alternating match filter to match that attribute when searching by DNs.
        # In OpenLDAP the distinguishedname is no user attribute, therefor it can not be used
        # as filter expression. We have to do one ldap query per group. Maybe, in the future,
        # we change the role sync plugin parameters to snapins to make this part a little easier.
        if not nested:
            groups = {}
            filt = self.ldap_filter('groups')
            member_attr = self.member_attr().lower()

            if self.is_active_directory() or filt_attr != 'distinguishedname':
                if filters:
                    add_filt = '(|%s)' % ''.join([ '(%s=%s)' % (filt_attr, f) for f in filters ])
                    filt = '(&%s%s)' % (filt, add_filt)

                for dn, obj in self.ldap_search(self.replace_macros(self._config['group_dn']),
                                                filt, ['cn', member_attr], self._config['group_scope']):
                    groups[dn] = {
                        'cn'      : obj['cn'][0],
                        'members' : [ m.encode('utf-8').lower() for m in obj.get(member_attr,[]) ],
                    }
            else:
                # Special handling for OpenLDAP when searching for groups by DN
                for f_dn in filters:
                    for dn, obj in self.ldap_search(self.replace_macros(f_dn), filt,
                                                    ['cn', member_attr], 'base'):
                        groups[f_dn] = {
                            'cn'      : obj['cn'][0],
                            'members' : [ m.encode('utf-8').lower() for m in obj.get(member_attr,[]) ],
                        }

        else:
            # Nested querying is more complicated. We have no option to simply do a query for group objects
            # to make them resolve the memberships here. So we need to query all users with the nested
            # memberof filter to get all group memberships of that group. We need one query for each group.
            groups = {}
            for filter_val in filters:
                if filt_attr == 'cn':
                    result = self.ldap_search(self.replace_macros(self._config['group_dn']),
                                         '(&%s(cn=%s))' % (self.ldap_filter('groups'), filter_val),
                                         ['dn'], self._config['group_scope'])
                    if not result:
                        continue # Skip groups which can not be found
                    dn = result[0][0]
                    cn = filter_val
                else:
                    dn = filter_val
                    # in case of asking with DNs in nested mode, the resulting objects have the
                    # cn set to None for all objects. We do not need it in that case.
                    cn = None

                filt = '(&%s(memberOf:1.2.840.113556.1.4.1941:=%s))' % (self.ldap_filter('users'), dn)
                groups[dn] = {
                    'members' : [],
                    'cn'      : cn,
                }
                for user_dn, obj in self.ldap_search(self.replace_macros(self._config['user_dn']),
                                                     filt, ['dn'], self._config['user_scope']):
                    groups[dn]['members'].append(user_dn.lower())

        self._group_cache[cache_key] = groups
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

        # Create a default connection out of the old config format
        connection = {
            'id'             : 'default',
            'type'           : 'ldap',
            'description'    : _('This is the default LDAP connection.'),
            'disabled'       : 'ldap' not in getattr(config, 'user_connectors', []),
            'cache_livetime' : getattr(config, 'ldap_cache_livetime', 300),
            'active_plugins' : getattr(config, 'ldap_active_plugins', []) or {'email': {}, 'alias': {}, 'auth_expire': {}},
            'debug_log'      : getattr(config, 'ldap_debug_log', False),
            'directory_type' : getattr(config, 'ldap_connection', {}).get('type', 'ad'),
            'user_id_umlauts': 'replace',
            'user_dn'        : '',
            'user_scope'     : 'subtree',
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
        # Returns None when the user is not found or not uniq, else returns the
        # distinguished name and the username as tuple which are both needed for
        # the further login process.
        result = self.get_user(username, True)
        if not result:
            return None # The user does not exist. Skip this connector.

        user_dn, username = result

        # Try to bind with the user provided credentials. This unbinds the default
        # authentication which should be rebound again after trying this.
        try:
            ldap_bind(user_dn, password)
            result = username.encode('utf-8')
        except:
            result = False

        ldap_default_bind(self._ldap_obj)
        return result


    def do_sync(self, add_to_changelog, only_username):
        # Don't store after sync since parallel requests to e.g. the page hook
        # would cause duplicate calculations
        self.set_last_sync_time()

        if not self.has_user_base_dn_configured():
            return # silently skip sync without configuration

        # Flush ldap related before each sync to have a caching only for the
        # current sync process
        self.flush_caches()

        start_time = time.time()
        connection_id = self._config['id']

        self.log('SYNC STARTED')
        self.log('  SYNC PLUGINS: %s' % ', '.join(self._config['active_plugins'].keys()))

        # Unused at the moment, always sync all users
        #filt = None
        #if only_username:
        #    filt = '(%s=%s)' % (self.user_id_attr(), only_username)

        ldap_users = self.get_users()

        import wato
        users = load_users(lock = True)

        # Remove users which are controlled by this connector but can not be found in
        # LDAP anymore
        for user_id, user in users.items():
            user_connection_id = cleanup_connection_id(user.get('connector'))
            if user_connection_id == connection_id and user_id not in ldap_users:
                del users[user_id] # remove the user
                wato.log_pending(wato.SYNCRESTART, None, "edit-users",
                    _("LDAP [%s]: Removed user %s") % (connection_id, user_id), user_id = '')

        for user_id, ldap_user in ldap_users.items():
            if user_id in users:
                user = copy.deepcopy(users[user_id])
                mode_create = False
            else:
                user = new_user_template(connection_id)
                mode_create = True

            user_connection_id = cleanup_connection_id(user.get('connector'))

            # Skip all users not controlled by this connector
            if user_connection_id != connection_id:
                continue

            # Gather config from convert functions of plugins
            for key, params in self._config['active_plugins'].items():
                user.update(ldap_attribute_plugins[key]['convert'](self, key, params or {}, user_id, ldap_user, user))

            if not mode_create and user == users[user_id]:
                continue # no modification. Skip this user.

            # Gather changed attributes for easier debugging
            if not mode_create:
                set_new, set_old = set(user.keys()), set(users[user_id].keys())
                intersect = set_new.intersection(set_old)
                added = set_new - intersect
                removed = set_old - intersect
                changed = set(o for o in intersect if users[user_id][o] != user[o])

            users[user_id] = user # Update the user record

            if mode_create:
                wato.log_pending(wato.SYNCRESTART, None, "edit-users",
                                 _("LDAP [%s]: Created user %s") % (connection_id, user_id), user_id = '')
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
                    changed.remove('ldap_pw_last_changed')
                    pw_changed = True
                if 'serial' in changed:
                    changed.remove('serial')
                    pw_changed = True

                # Synchronize new user profile to remote sites if needed
                if pw_changed and not changed and wato.is_distributed():
                    synchronize_profile_to_sites(user_id, user)

                if changed:
                    details.append(('Changed: %s') % ', '.join(changed))

                if details:
                    wato.log_pending(wato.SYNCRESTART, None, "edit-users",
                         _("LDAP [%s]: Modified user %s (%s)") % (connection_id, user_id, ', '.join(details)),
                         user_id = '')

        duration = time.time() - start_time
        self.log('SYNC FINISHED - Duration: %0.3f sec' % duration)

        # delete the fail flag file after successful sync
        try:
            os.unlink(self._sync_fail_file)
        except OSError:
            pass

        save_users(users)


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


    # Is called on every multisite http request
    def on_page_load(self):
        register_user_attribute_sync_plugins()

        if self.sync_is_needed():
            try:
                self.do_sync(False, None)
            except:
                self.persist_sync_failure()


    def sync_is_needed(self):
        return self.get_last_sync_time() + self.get_cache_livetime() <= time.time()


    def get_last_sync_time(self):
        try:
            return float(file(self._sync_time_file).read().strip())
        except:
            return 0


    # in case of sync problems, synchronize all 20 seconds, instead of the configured
    # regular cache livetime
    def get_cache_livetime(self):
        if os.path.exists(self._sync_fail_file):
            return 20
        else:
            return self._config['cache_livetime']


    def persist_sync_failure(self):
        # Do not let the exception through to the user. Instead write last
        # error in a state file which is then visualized for the admin and
        # will be deleted upon next successful sync.
        file(self._sync_fail_file, 'w').write('%s\n%s' % (time.strftime('%Y-%m-%d %H:%M:%S'),
                                                        traceback.format_exc()))


    # Calculates the attributes of the users which are locked for users managed
    # by this connector
    def locked_attributes(self):
        locked = set([ 'password' ]) # This attributes are locked in all cases!
        for key in self._config['active_plugins'].keys():
            locked.update(ldap_attribute_plugins.get(key, {}).get('lock_attributes', []))
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
def ldap_attribute_plugins_elements():
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
                title    = plugin['title'],
                help     = plugin['help'],
                elements = plugin['parameters'],
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

    for attr, val in get_user_attributes():
        ldap_attribute_plugins[attr] = {
            'title': val['valuespec'].title(),
            'help':  val['valuespec'].help(),
            'needed_attributes': lambda connection, params: [ params.get('attr', connection.ldap_attr(attr)).lower() ],
            'convert':           lambda connection, plugin, params, user_id, ldap_user, user: \
                                         ldap_convert_simple(user_id, ldap_user, user, plugin,
                                                        params.get('attr', connection.ldap_attr(plugin)).lower()),
            'lock_attributes': [ attr ],
            'parameters': [
                ('attr', TextAscii(
                    title = _("LDAP attribute to sync"),
                    help  = _("The LDAP attribute whose contents shall be synced into this custom attribute."),
                    default_value = lambda: ldap_attr(attr),
                )),
            ],
        }


def ldap_convert_simple(user_id, ldap_user, user, user_attr, attr):
    if attr in ldap_user:
        return {user_attr: ldap_user[attr][0]}
    else:
        return {}


#.
#   .--Mail----------------------------------------------------------------.
#   |                          __  __       _ _                            |
#   |                         |  \/  | __ _(_) |                           |
#   |                         | |\/| |/ _` | | |                           |
#   |                         | |  | | (_| | | |                           |
#   |                         |_|  |_|\__,_|_|_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def ldap_convert_mail(connection, plugin, params, user_id, ldap_user, user):
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
    'convert'           : ldap_convert_mail,
    'lock_attributes'   : [ 'email' ],
    'parameters'        : [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the mail address of the user."),
            default_value = lambda: ldap_attr('mail'),
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


def ldap_convert_alias(connection, plugin, params, user_id, ldap_user, user):
    return ldap_convert_simple(user_id, ldap_user, user, 'alias',
                               params.get('attr', connection.ldap_attr('cn')).lower())


def ldap_needed_attributes_alias(connection, params):
    return [ params.get('attr', connection.ldap_attr('cn')).lower() ]


ldap_attribute_plugins['alias'] = {
    'title'             : _('Alias'),
    'help'              :  _('Populates the alias attribute of the WATO user by syncrhonizing an attribute '
                             'from the LDAP user account. By default the LDAP attribute <tt>cn</tt> is used.'),
    'needed_attributes' : ldap_needed_attributes_alias,
    'convert'           : ldap_convert_alias,
    'lock_attributes'   : [ 'alias' ],
    'parameters'        : [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the alias of the user."),
            default_value = lambda: ldap_attr('cn'),
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
#   | Checks wether or not the user auth must be invalidated (increasing   |
#   | the serial). In first instance, it must parse the pw-changed field,  |
#   | then check wether or not a date has been stored in the user before   |
#   | and then maybe increase the serial.                                  |
#   '----------------------------------------------------------------------'

def ldap_convert_auth_expire(connection, plugin, params, user_id, ldap_user, user):
    # Special handling for active directory: Is the user enabled / disabled?
    if connection.is_active_directory() and ldap_user.get('useraccountcontrol'):
        # see http://www.selfadsi.de/ads-attributes/user-userAccountControl.htm for details
        if saveint(ldap_user['useraccountcontrol'][0]) & 2 and not user.get("locked", False):
            return {
                'locked': True,
                'serial': user.get('serial', 0) + 1,
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
    'help'                   : _('This plugin fetches all information which are needed to check wether or '
                                 'not an already authenticated user should be deauthenticated, e.g. because '
                                 'the password has changed in LDAP or the account has been locked.'),
    'needed_attributes'      : ldap_needed_attributes_auth_expire,
    'convert'                : ldap_convert_auth_expire,
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
            default_value = lambda: ldap_attr('pw_changed'),
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

def ldap_convert_pager(connection, plugin, params, user_id, ldap_user, user):
    return ldap_convert_simple(user_id, ldap_user, user, 'pager',
                        params.get('attr', connection.ldap_attr('mobile')).lower())


def ldap_needed_attributes_pager(connection, params):
    return [ params.get('attr', connection.ldap_attr('mobile')).lower() ]


ldap_attribute_plugins['pager'] = {
    'title'             : _('Pager'),
    'help'              :  _('This plugin synchronizes a field of the users LDAP account to the pager attribute '
                             'of the WATO user accounts, which is then forwarded to the monitoring core and can be used'
                             'for notifications. By default the LDAP attribute <tt>mobile</tt> is used.'),
    'needed_attributes' : ldap_needed_attributes_pager,
    'convert'           : ldap_convert_pager,
    'lock_attributes'   : ['pager'],
    'parameters'        : [
        ('attr', TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the pager number of the user."),
            default_value = lambda: ldap_attr('mobile'),
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

def ldap_convert_groups_to_contactgroups(connection, plugin, params, user_id, ldap_user, user):
    # 0. Figure out how to check group membership.
    user_cmp_val = connection.member_attr().lower() == 'memberuid' and user_id or ldap_user['dn']

    # 1. Fetch all existing group names in WATO
    cg_names = load_group_information().get("contact", {}).keys()

    # 2. Load all LDAP groups which have a CN matching one contact
    #    group which exists in WATO
    ldap_groups = connection.group_members(cg_names, nested = params.get('nested', False))

    # 3. Only add groups which the user is member of
    return {'contactgroups': [ g['cn'] for dn, g in ldap_groups.items() if user_cmp_val in g['members']]}


ldap_attribute_plugins['groups_to_contactgroups'] = {
    'title': _('Contactgroup Membership'),
    'help':  _('Adds the user to contactgroups based on the group memberships in LDAP. This '
               'plugin adds the user only to existing contactgroups while the name of the '
               'contactgroup must match the common name (cn) of the LDAP group.'),
    'convert':           ldap_convert_groups_to_contactgroups,
    'lock_attributes':   ['contactgroups'],
    'parameters': [
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
    ],
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

def ldap_convert_groups_to_roles(connection, plugin, params, user_id, ldap_user, user):
    # Load the needed LDAP groups, which match the DNs mentioned in the role sync plugin config
    groups_to_fetch = []
    for role_id, distinguished_names in params.items():
        if type(distinguished_names) == list:
            groups_to_fetch += [ dn.lower() for dn in distinguished_names ]
        elif type(distinguished_names) == str:
            groups_to_fetch.append(distinguished_names.lower())

    ldap_groups = dict(connection.group_members(groups_to_fetch,
                                          filt_attr = 'distinguishedname',
                                          nested = params.get('nested', False)))

    # posixGroup objects use the memberUid attribute to specify the group
    # memberships. This is the username instead of the users DN. So the
    # username needs to be used for filtering here.
    user_cmp_val = connection.member_attr().lower() == 'memberuid' and user_id or ldap_user['dn']

    roles = set([])

    # Loop all roles mentioned in params (configured to be synchronized)
    for role_id, distinguished_names in params.items():
        if type(distinguished_names) != list:
            distinguished_names = [distinguished_names]

        for dn in distinguished_names:
            if not isinstance(dn, str):
                continue # skip non configured ones (old valuespecs allowed None)
            dn = dn.lower() # lower case matching for DNs!

            # if group could be found and user is a member, add the role
            if dn in ldap_groups and user_cmp_val in ldap_groups[dn]['members']:
                roles.add(role_id)

    # Load default roles from default user profile when the user got no role
    # by the role sync plugin
    if not roles:
        roles = config.default_user_profile['roles'][:]

    return {'roles': list(roles)}


def ldap_list_roles_with_group_dn():
    elements = []
    for role_id, role in load_roles().items():
        elements.append((role_id, Transform(
            ListOf(
                LDAPDistinguishedName(
                    size = 80,
                    allow_empty = False,
                ),
                title = role['alias'] + ' - ' + _("Specify the Group DN"),
                help  = _("Distinguished Names of the LDAP groups to add users this role. "
                          "e. g. <tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt><br> "
                          "This group must be defined within the scope of the "
                          "<a href=\"wato.py?mode=ldap_config&varname=ldap_groupspec\">LDAP Group Settings</a>."),
                movable = False,
            ),
            # Convert old single distinguished names to list of :Ns
            forth = lambda v: type(v) != list and [v] or v,
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
    'convert'         : ldap_convert_groups_to_roles,
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
def synchronize_profile_to_sites(user_id, profile):
    import wato # FIXME: Cleanup!
    sites = [(site_id, config.site(site_id))
              for site_id in config.sitenames()
              if not wato.site_is_local(site_id) ]

    self.log('Credentials changed: %s. Trying to sync to %d sites' % (user_id, len(sites)))

    num_disabled  = 0
    num_succeeded = 0
    num_failed    = 0
    for site_id, site in sites:
        if not site.get("replication"):
            num_disabled += 1
            continue

        if site.get("disabled"):
            num_disabled += 1
            continue

        status = html.site_status.get(site_id, {}).get("state", "unknown")
        if status == "dead":
            result = "Site is dead"
        else:
            try:
                result = wato.push_user_profile_to_site(site, user_id, profile)
            except Exception, e:
                result = str(e)

        if result == True:
            num_succeeded += 1
        else:
            num_failed += 1
            self.log('  FAILED [%s]: %s' % (site_id, result))
            # Add pending entry to make sync possible later for admins
            wato.update_replication_status(site_id, {"need_sync": True})
            wato.log_pending(wato.AFFECTED, None, "edit-users",
                            _('Password changed (sync failed: %s)') % result, user_id = '')

    self.log('  Disabled: %d, Succeeded: %d, Failed: %d' %
                    (num_disabled, num_succeeded, num_failed))

