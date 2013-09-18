#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

import config, defaults
import time, copy, traceback

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

g_ldap_user_cache  = {}
g_ldap_group_cache = {}

# File for storing the time of the last success event
g_ldap_sync_time_file = defaults.var_dir + '/web/ldap_sync_time.mk'
# Exists when last ldap sync failed, contains exception text
g_ldap_sync_fail_file = defaults.var_dir + '/web/ldap_sync_fail.mk'

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
}

#   .----------------------------------------------------------------------.
#   |                      _     ____    _    ____                         |
#   |                     | |   |  _ \  / \  |  _ \                        |
#   |                     | |   | | | |/ _ \ | |_) |                       |
#   |                     | |___| |_| / ___ \|  __/                        |
#   |                     |_____|____/_/   \_\_|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | General LDAP handling code                                           |
#   '----------------------------------------------------------------------'

def ldap_log(s):
    if config.ldap_debug_log is not None:
        file(ldap_replace_macros(config.ldap_debug_log), "a").write('%s %s\n' %
                                            (time.strftime('%Y-%m-%d %H:%M:%S'), s))

class MKLDAPException(MKGeneralException):
    pass

ldap_connection = None
ldap_connection_options = None

def ldap_uri(server):
    if 'use_ssl' in config.ldap_connection:
        uri = 'ldaps://'
    else:
        uri = 'ldap://'

    return uri + '%s:%d' % (server, config.ldap_connection['port'])

def ldap_test_module():
    try:
        ldap
    except:
        raise MKLDAPException(_("The python module python-ldap seems to be missing. You need to "
                                "install this extension to make the LDAP user connector work."))

def ldap_servers():
    servers = [ config.ldap_connection['server'] ]
    if config.ldap_connection.get('failover_servers'):
        servers += config.ldap_connection.get('failover_servers')
    return servers

def ldap_connect_server(server):
    try:
        uri = ldap_uri(server)
        conn = ldap.ldapobject.ReconnectLDAPObject(uri)
        conn.protocol_version = config.ldap_connection['version']
        conn.network_timeout  = config.ldap_connection.get('connect_timeout', 2.0)
        conn.retry_delay      = 0.5

        # When using the domain top level as base-dn, the subtree search stumbles with referral objects.
        # whatever. We simply disable them here when using active directory. Hope this fixes all problems.
        if config.ldap_connection['type'] == 'ad':
            conn.set_option(ldap.OPT_REFERRALS, 0)

        ldap_default_bind(conn)
        return conn, None
    except (ldap.SERVER_DOWN, ldap.TIMEOUT, ldap.LOCAL_ERROR, ldap.LDAPError), e:
        return None, '%s: %s' % (uri, e[0].get('info', e[0].get('desc', '')))
    except MKLDAPException, e:
        return None, str(e)

def ldap_disconnect():
    global ldap_connection, ldap_connection_options
    ldap_connection = None
    ldap_connection_options = None

def ldap_connect(enforce_new = False, enforce_server = None):
    global ldap_connection, ldap_connection_options

    if not enforce_new \
       and not "no_persistent" in config.ldap_connection \
       and ldap_connection \
       and config.ldap_connection == ldap_connection_options:
        ldap_log('LDAP CONNECT - Using existing connecting')
        return # Use existing connections (if connection settings have not changed)
    else:
        ldap_log('LDAP CONNECT - Connecting...')

    ldap_test_module()

    # Some major config var validations

    if not config.ldap_connection.get('server'):
        raise MKLDAPException(_('The LDAP connector is enabled in global settings, but the '
                                'LDAP server to connect to is not configured. Please fix this in the '
                                '<a href="wato.py?mode=ldap_config">LDAP '
                                'connection settings</a>.'))

    if not config.ldap_userspec.get('dn'):
        raise MKLDAPException(_('The distinguished name of the container object, which holds '
                                'the user objects to be authenticated, is not configured. Please '
                                'fix this in the <a href="wato.py?mode=ldap_config">'
                                'LDAP User Settings</a>.'))

    try:
        errors = []
        if enforce_server:
            servers = [ enforce_server ]
        else:
            servers = ldap_servers()

        for server in servers:
            ldap_connection, error_msg = ldap_connect_server(server)
            if ldap_connection:
                break # got a connection!
            else:
                errors.append(error_msg)

        # Got no connection to any server
        if ldap_connection is None:
            raise MKLDAPException(_('The LDAP connector is unable to connect to the LDAP server.\n%s') %
                                        ('<br />\n'.join(errors)))

        # on success, store the connection options the connection has been made with
        ldap_connection_options = config.ldap_connection

    except Exception:
        # Invalidate connection on failure
        ldap_connection         = None
        ldap_connection_options = None
        raise

# Bind with the default credentials
def ldap_default_bind(conn):
    try:
        if 'bind' in config.ldap_connection:
            ldap_bind(ldap_replace_macros(config.ldap_connection['bind'][0]),
                      config.ldap_connection['bind'][1], catch = False, conn = conn)
        else:
            ldap_bind('', '', catch = False, conn = conn) # anonymous bind
    except (ldap.INVALID_CREDENTIALS, ldap.INAPPROPRIATE_AUTH):
        raise MKLDAPException(_('Unable to connect to LDAP server with the configured bind credentials. '
                                'Please fix this in the '
                                '<a href="wato.py?mode=ldap_config">LDAP connection settings</a>.'))

def ldap_bind(username, password, catch = True, conn = None):
    if conn is None:
        conn = ldap_connection
    ldap_log('LDAP_BIND %s' % username)
    try:
        conn.simple_bind_s(username, password)
        ldap_log('  SUCCESS')
    except ldap.LDAPError, e:
        ldap_log('  FAILED (%s)' % e)
        if catch:
            raise MKLDAPException(_('Unable to authenticate with LDAP (%s)' % e))
        else:
            raise

def ldap_async_search(base, scope, filt, columns):
    ldap_log('  ASYNC SEARCH')
    # issue the ldap search command (async)
    msgid = ldap_connection.search_ext(base, scope, filt, columns)

    results = []
    while True:
        restype, resdata = ldap_connection.result(msgid = msgid,
            timeout = config.ldap_connection.get('response_timeout', 5))

        results.extend(resdata)
        if restype == ldap.RES_SEARCH_RESULT or not resdata:
            break

        # no limit at the moment
        #if sizelimit and len(users) >= sizelimit:
        #    ldap_connection.abandon_ext(msgid)
        #    break
        time.sleep(0.1)

    return results

def ldap_paged_async_search(base, scope, filt, columns):
    ldap_log('  PAGED ASYNC SEARCH')
    page_size = config.ldap_connection.get('page_size', 100)

    if ldap_compat:
        lc = SimplePagedResultsControl(size = page_size, cookie = '')
    else:
        lc = SimplePagedResultsControl(
            LDAP_CONTROL_PAGED_RESULTS, True, (page_size, '')
        )

    results = []
    while True:
        # issue the ldap search command (async)
        msgid = ldap_connection.search_ext(base, scope, filt, columns, serverctrls = [lc])

        unused_code, response, unused_msgid, serverctrls = ldap_connection.result3(
            msgid = msgid, timeout = config.ldap_connection.get('response_timeout', 5)
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

def ldap_search(base, filt = '(objectclass=*)', columns = [], scope = None):
    if scope:
        config_scope = scope
    else:
        config_scope = config.ldap_userspec.get('scope', 'sub')

    if config_scope == 'sub':
        scope = ldap.SCOPE_SUBTREE
    elif config_scope == 'base':
        scope = ldap.SCOPE_BASE
    elif config_scope == 'one':
        scope = ldap.SCOPE_ONELEVEL

    ldap_log('LDAP_SEARCH "%s" "%s" "%s" "%r"' % (base, scope, filt, columns))
    start_time = time.time()

    # In some environments, the connection to the LDAP server does not seem to
    # be as stable as it is needed. So we try to repeat the query for three times.
    tries_left = 2
    success = False
    while not success:
        tries_left -= 1
        try:
            ldap_connect()
            result = []
            try:
                search_func = config.ldap_connection.get('page_size') \
                              and ldap_paged_async_search or ldap_async_search
                for dn, obj in search_func(base, scope, filt, columns):
                    if dn is None:
                        continue # skip unwanted answers
                    new_obj = {}
                    for key, val in obj.iteritems():
                        # Convert all keys to lower case!
                        new_obj[key.lower().decode('utf-8')] = [ i.decode('utf-8') for i in val ]
                    result.append((dn, new_obj))
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
            if tries_left:
                ldap_log('  Received %r. Retrying with clean connection...' % e)
                ldap_disconnect()
                time.sleep(0.5)
            else:
                ldap_log('  Giving up.')
                break

    duration = time.time() - start_time

    if not success:
        ldap_log('  FAILED')
        raise MKLDAPException(_('Unable to successfully perform the LDAP search. '
                                'Maybe there is a connection problem with the LDAP server.'))

    ldap_log('  RESULT length: %d, duration: %0.3f' % (len(result), duration))
    return result

# Returns the ldap filter depending on the configured ldap directory type
def ldap_filter(key, handle_config = True):
    value = ldap_filter_map[config.ldap_connection['type']].get(key, '(objectclass=*)')
    if handle_config:
        if key == 'users':
            value = config.ldap_userspec.get('filter', value)
        elif key == 'groups':
            value = config.ldap_groupspec.get('filter', value)
    return ldap_replace_macros(value)

# Returns the ldap attribute name depending on the configured ldap directory type
# If a key is not present in the map, the assumption is, that the key matches 1:1
# Always use lower case here, just to prevent confusions.
def ldap_attr(key):
    return ldap_attr_map[config.ldap_connection['type']].get(key, key).lower()

# Returns the given distinguished name template with replaced vars
def ldap_replace_macros(tmpl):
    dn = tmpl

    for key, val in [ ('$OMD_SITE$', defaults.omd_site) ]:
        if val:
            dn = dn.replace(key, val)
        else:
            dn = dn.replace(key, '')

    return dn

def ldap_user_id_attr():
    return config.ldap_userspec.get('user_id', ldap_attr('user_id'))

def ldap_member_attr():
    return config.ldap_groupspec.get('member', ldap_attr('member'))

def ldap_user_base_dn_exists():
    try:
        result = ldap_search(ldap_replace_macros(config.ldap_userspec['dn']), columns = ['dn'], scope = 'base')
    except Exception, e:
        return False
    if not result:
        return False
    else:
        return len(result) == 1

def ldap_get_user(username, no_escape = False):
    if username in g_ldap_user_cache:
        return g_ldap_user_cache[username]

    # Check wether or not the user exists in the directory
    # It's only ok when exactly one entry is found.
    # Returns the DN and user_id as tuple in this case.
    result = ldap_search(
        ldap_replace_macros(config.ldap_userspec['dn']),
        '(%s=%s)' % (ldap_user_id_attr(), ldap.filter.escape_filter_chars(username)),
        [ldap_user_id_attr()],
    )

    if result:
        dn = result[0][0]
        user_id = result[0][1][ldap_user_id_attr()][0]

        if config.ldap_userspec.get('lower_user_ids', False):
            user_id = user_id.lower()

        g_ldap_user_cache[username] = (dn, user_id)

        if no_escape:
            return (dn, user_id)
        else:
            return (dn.replace('\\', '\\\\'), user_id)

def ldap_get_users(add_filter = ''):
    columns = [
        ldap_user_id_attr(), # needed in all cases as uniq id
    ] + ldap_needed_attributes()

    filt = ldap_filter('users')

    # Create filter by the optional filter_group
    filter_group_dn = config.ldap_userspec.get('filter_group', None)
    member_filter = ''
    if filter_group_dn:
        member_attr = ldap_member_attr().lower()
        # posixGroup objects use the memberUid attribute to specify the group memberships.
        # This is the username instead of the users DN. So the username needs to be used
        # for filtering here.
        user_cmp_attr = member_attr == 'memberuid' and ldap_user_id_attr() or 'distinguishedname'

        # Apply configured group ldap filter
        try:
            group = ldap_search(ldap_replace_macros(filter_group_dn),
                                columns = [member_attr],
                                scope = 'base')
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
    for dn, ldap_user in ldap_search(ldap_replace_macros(config.ldap_userspec['dn']),
                                     filt, columns = columns):
        if ldap_user_id_attr() not in ldap_user:
            raise MKLDAPException(_('The configured User-ID attribute "%s" does not '
                                    'exist for the user "%s"') % (ldap_user_id_attr(), dn))
        user_id = ldap_user[ldap_user_id_attr()][0]

        if config.ldap_userspec.get('lower_user_ids', False):
            user_id = user_id.lower()

        ldap_user['dn'] = dn # also add the DN
        result[user_id] = ldap_user

    return result

def ldap_group_base_dn_exists():
    try:
        result = ldap_search(ldap_replace_macros(config.ldap_groupspec['dn']), columns = ['dn'], scope = 'base')
    except Exception, e:
        return False
    if not result:
        return False
    else:
        return len(result) == 1

def ldap_get_groups(add_filt = None):
    filt = ldap_filter('groups')
    if add_filt:
        filt = '(&%s%s)' % (filt, add_filt)
    return ldap_search(ldap_replace_macros(config.ldap_groupspec['dn']), filt, ['cn'])

def ldap_user_groups(username, user_dn, attr = 'cn'):
    # When configured to convert user_ids to lower case, all user ids here are lower case.
    # Otherwise all user_ids are in the case which they are in LDAP. This should be ok
    # for this function! I removed the snippet below to reduce the number of ldap queries.
    # Before removal, this query was executed for every user again, just to fetch the DN
    # and the username.
    #   # The given username might be wrong case. The ldap search is case insensitive,
    #   # so the username read from ldap might differ. Fix it here.
    #   user_dn, username = ldap_get_user(username, True)

    if username in g_ldap_group_cache:
        if attr == 'cn':
            return g_ldap_group_cache[username][0]
        else:
            return g_ldap_group_cache[username][1]

    # posixGroup objects use the memberUid attribute to specify the group memberships.
    # This is the username instead of the users DN. So the username needs to be used
    # for filtering here.
    if ldap_member_attr().lower() == 'memberuid':
        user_filter = username
    else:
        user_filter = user_dn

    # Apply configured group ldap filter and only reply with groups
    # having the current user as member
    add_filt = '(%s=%s)' % (ldap_member_attr(), ldap.filter.escape_filter_chars(user_filter))

    # First get all groups
    groups_cn = []
    groups_dn = []
    for dn, group in ldap_get_groups(add_filt):
        groups_cn.append(group['cn'][0])
        groups_dn.append(dn)

    g_ldap_group_cache.setdefault(username, (groups_cn, groups_dn))

    if attr == 'cn':
        return groups_cn
    else:
        return groups_dn

#   .----------------------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Attribute plugin handling code goes here                             |
#   '----------------------------------------------------------------------'

ldap_attribute_plugins = {}

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
                value    = None,
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

# Returns a list of all needed LDAP attributes of all enabled plugins
def ldap_needed_attributes():
    attrs = set([])
    for key, params in config.ldap_active_plugins.items():
        plugin = ldap_attribute_plugins[key]
        if 'needed_attributes' in plugin:
            attrs.update(plugin['needed_attributes'](params))
    return list(attrs)

def ldap_convert_simple(user_id, ldap_user, user, user_attr, attr):
    if attr in ldap_user:
        return {user_attr: ldap_user[attr][0]}
    else:
        return {}

def ldap_convert_mail(params, user_id, ldap_user, user):
    mail = ''
    if ldap_user.get(params.get('attr', ldap_attr('mail'))):
        mail = ldap_user[params.get('attr', ldap_attr('mail'))][0].lower()
    if mail:
        return {'email': mail}
    else:
        return {}

ldap_attribute_plugins['email'] = {
    'title': _('Email address'),
    'help':  _('Synchronizes the email of the LDAP user account into Check_MK.'),
    # Attributes which must be fetched from ldap
    'needed_attributes': lambda params: [ params.get('attr', ldap_attr('mail')) ],
    # Calculating the value of the attribute based on the configuration and the values
    # gathered from ldap
    'convert': ldap_convert_mail,
    # User-Attributes to be written by this plugin and will be locked in WATO
    'lock_attributes': [ 'email' ],
    'parameters': [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the mail address of the user."),
            default_value = lambda: ldap_attr('mail'),
        )),
    ],
}

ldap_attribute_plugins['alias'] = {
    'title': _('Alias'),
    'help':  _('Populates the alias attribute of the WATO user by syncrhonizing an attribute '
               'from the LDAP user account. By default the LDAP attribute &quot;cn&quot; is used.'),
    'needed_attributes': lambda params: [ params.get('attr', ldap_attr('cn')) ],
    'convert':           lambda params, user_id, ldap_user, user: \
                             ldap_convert_simple(user_id, ldap_user, user, 'alias',
                                                 params.get('attr', ldap_attr('cn'))),
    'lock_attributes':   [ 'alias' ],
    'parameters': [
        ("attr", TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the alias of the user."),
            default_value = lambda: ldap_attr('cn'),
        )),
    ],
}

# Checks wether or not the user auth must be invalidated (increasing the serial).
# In first instance, it must parse the pw-changed field, then check wether or not
# a date has been stored in the user before and then maybe increase the serial.
def ldap_convert_auth_expire(params, user_id, ldap_user, user):
    changed_attr = params.get('attr', ldap_attr('pw_changed'))
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

ldap_attribute_plugins['auth_expire'] = {
    'title': _('Authentication Expiration'),
    'help':  _('This plugin fetches all information which are needed to check wether or '
               'not an already authenticated user should be deauthenticated, e.g. because '
               'the password has changed in LDAP or the account has been locked.'),
    'needed_attributes': lambda params: [ params.get('attr', ldap_attr('pw_changed')) ],
    'convert':           ldap_convert_auth_expire,
    # When a plugin introduces new user attributes, it should declare the output target for
    # this attribute. It can either be written to the multisites users.mk or the check_mk
    # contacts.mk to be forwarded to nagios. Undeclared attributes are stored in the check_mk
    # contacts.mk file.
    'multisite_attributes':   ['ldap_pw_last_changed'],
    'non_contact_attributes': ['ldap_pw_last_changed'],
    'parameters': [
        ("attr", TextAscii(
            title = _("LDAP attribute to be used as indicator"),
            help  = _("When the value of this attribute changes for a user account, all "
                      "current authenticated sessions of the user are invalidated and the "
                      "user must login again. By default this field uses the fields whcih "
                      "hold the time of the last password change of the user."),
            default_value = lambda: ldap_attr('pw_changed'),
        )),
    ],
}

ldap_attribute_plugins['pager'] = {
    'title': _('Pager'),
    'help':  _('This plugin synchronizes a field of the users ldap account to the pager attribute '
               'of the WATO user accounts, which is then forwarded to Nagios and can be used'
               'for notifications. By default the LDAP attribute &quot;mobile&quot; is used.'),
    'needed_attributes': lambda params: [ params.get('attr', ldap_attr('mobile')) ],
    'convert':           lambda params, user_id, ldap_user, user: \
                             ldap_convert_simple(user_id, ldap_user, user, 'pager',
                                                 params.get('attr', ldap_attr('mobile'))),
    'lock_attributes':   ['pager'],
    'parameters': [
        ('attr', TextAscii(
            title = _("LDAP attribute to sync"),
            help  = _("The LDAP attribute containing the pager number of the user."),
            default_value = lambda: ldap_attr('mobile'),
        )),
    ],
}

# Register sync plugins for all custom user attributes (assuming simple data types)
def register_user_attribute_sync_plugins():
    for attr, val in get_user_attributes():
        ldap_attribute_plugins[attr] = {
            'title': val['valuespec'].title(),
            'help':  val['valuespec'].help(),
            'needed_attributes': lambda params: [ params.get('attr', ldap_attr(attr)) ],
            'convert':           lambda params, user_id, ldap_user, user: \
                                         ldap_convert_simple(user_id, ldap_user, user, attr,
                                                        params.get('attr', ldap_attr(attr))),
            'lock_attributes': [ attr ],
            'parameters': [
                ('attr', TextAscii(
                    title = _("LDAP attribute to sync"),
                    help  = _("The LDAP attribute which contents shal be synced into this custom attribute."),
                    default_value = lambda: ldap_attr(attr),
                )),
            ],
        }

register_user_attribute_sync_plugins()

def ldap_convert_groups_to_contactgroups(params, user_id, ldap_user, user):
    groups = []
    # 1. Fetch CNs of all LDAP groups of the user (use group_dn, group_filter)
    ldap_groups = ldap_user_groups(user_id, ldap_user['dn'])

    # 2. Fetch all existing group names in WATO
    cg_names = load_group_information().get("contact", {}).keys()

    # Only add groups which are already contactgroups in wato
    return {'contactgroups': [ g for g in ldap_groups if g in cg_names]}

ldap_attribute_plugins['groups_to_contactgroups'] = {
    'title': _('Contactgroup Membership'),
    'help':  _('Adds the user to contactgroups based on the group memberships in LDAP. This '
               'plugin adds the user only to existing contactgroups while the name of the '
               'contactgroup must match the common name (cn) of the LDAP group.'),
    'convert':           ldap_convert_groups_to_contactgroups,
    'lock_attributes':   ['contactgroups'],
    'no_param_txt': _('Add user to all contactgroups where the common name matches the group name.'),
}

def ldap_convert_groups_to_roles(params, user_id, ldap_user, user):
    groups = []
    # 1. Fetch DNs of all LDAP groups of the user
    ldap_groups = [ g.lower() for g in ldap_user_groups(user_id, ldap_user['dn'], 'dn') ]

    # 2. Load default roles from default user profile
    roles = config.default_user_profile['roles'][:]

    # 3. Loop all roles mentioned in params (configured to be synchronized)
    for role_id, dn in params.items():
        if dn.lower() in ldap_groups and role_id not in roles:
            roles.append(role_id)

    return {'roles': roles}

def ldap_list_roles_with_group_dn():
    elements = []
    for role_id, role in load_roles().items():
        elements.append((role_id, LDAPDistinguishedName(
            title = role['alias'] + ' - ' + _("Specify the Group DN"),
            help  = _("Distinguished Name of the LDAP group to add users this role. This group must "
                      "be defined within the scope of the "
                      "<a href=\"wato.py?mode=ldap_config&varname=ldap_groupspec\">LDAP Group Settings</a>."),
            size  = 80,
            enforce_suffix = ldap_replace_macros(config.ldap_groupspec.get('dn', '')),
        )))
    return elements

ldap_attribute_plugins['groups_to_roles'] = {
    'title': _('Roles'),
    'help':  _('Configures the roles of the user depending on its group memberships '
               'in LDAP.'),
    'convert':           ldap_convert_groups_to_roles,
    'lock_attributes':   ['roles'],
    'parameters':        ldap_list_roles_with_group_dn,
}

#   .----------------------------------------------------------------------.
#   |                     _   _             _                              |
#   |                    | | | | ___   ___ | | _____                       |
#   |                    | |_| |/ _ \ / _ \| |/ / __|                      |
#   |                    |  _  | (_) | (_) |   <\__ \                      |
#   |                    |_| |_|\___/ \___/|_|\_\___/                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Hook functions used in this connector                                |
#   '----------------------------------------------------------------------'

# This function only validates credentials, no locked checking or similar
def ldap_login(username, password):
    ldap_connect()
    # Returns None when the user is not found or not uniq, else returns the
    # distinguished name and the username as tuple which are both needed for
    # the further login process.
    result = ldap_get_user(username, True)
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

    ldap_default_bind(ldap_connection)
    return result

def ldap_sync(add_to_changelog, only_username):
    # Store time of the last sync. Don't store after sync since parallel
    # requests to e.g. the page hook would cause duplicate calculations
    file(g_ldap_sync_time_file, 'w').write('%s\n' % time.time())

    if not config.ldap_connection:
        return # silently skip sync without configuration

    # Flush ldap related before each sync to have a caching only for the
    # current sync process
    global g_ldap_user_cache, g_ldap_group_cache
    g_ldap_user_cache = {}
    g_ldap_group_cache = {}

    start_time = time.time()

    ldap_log('  SYNC PLUGINS: %s' % ', '.join(config.ldap_active_plugins.keys()))

    # Unused at the moment, always sync all users
    #filt = None
    #if only_username:
    #    filt = '(%s=%s)' % (ldap_user_id_attr(), only_username)

    ldap_users = ldap_get_users()

    import wato
    users = load_users(lock = True)

    # Remove users which are controlled by this connector but can not be found in
    # LDAP anymore
    for user_id, user in users.items():
        if user.get('connector') == 'ldap' and user_id not in ldap_users:
            del users[user_id] # remove the user
            wato.log_pending(wato.SYNCRESTART, None, "edit-users", _("LDAP Connector: Removed user %s" % user_id))

    for user_id, ldap_user in ldap_users.items():
        if user_id in users:
            user = copy.deepcopy(users[user_id])
            mode_create = False
        else:
            user = new_user_template('ldap')
            mode_create = True

        # Skip all users not controlled by this connector
        if user.get('connector') != 'ldap':
            continue

        # Gather config from convert functions of plugins
        for key, params in config.ldap_active_plugins.items():
            user.update(ldap_attribute_plugins[key]['convert'](params, user_id, ldap_user, user))

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
                             _("LDAP Connector: Created user %s" % user_id))
        else:
            wato.log_pending(wato.SYNCRESTART, None, "edit-users",
                 _("LDAP Connector: Modified user %s (Added: %s, Removed: %s, Changed: %s)" %
                    (user_id, ', '.join(added), ', '.join(removed), ', '.join(changed))))

    duration = time.time() - start_time
    ldap_log('SYNC FINISHED - Duration: %0.3f sec' % duration)

    # delete the fail flag file after successful sync
    try:
        os.unlink(g_ldap_sync_fail_file)
    except OSError:
        pass

    save_users(users)

# Calculates the attributes of the users which are locked for users managed
# by this connector
def ldap_locked_attributes():
    locked = set([ 'password' ]) # This attributes are locked in all cases!
    for key in config.ldap_active_plugins.keys():
        locked.update(ldap_attribute_plugins.get(key, {}).get('lock_attributes', []))
    return list(locked)

# Calculates the attributes added in this connector which shal be written to
# the multisites users.mk
def ldap_multisite_attributes():
    attrs = set([])
    for key in config.ldap_active_plugins.keys():
        attrs.update(ldap_attribute_plugins.get(key, {}).get('multisite_attributes', []))
    return list(attrs)

# Calculates the attributes added in this connector which shal NOT be written to
# the check_mks contacts.mk
def ldap_non_contact_attributes():
    attrs = set([])
    for key in config.ldap_active_plugins.keys():
        attrs.update(ldap_attribute_plugins.get(key, {}).get('non_contact_attributes', []))
    return list(attrs)

# Is called on every multisite http request
def ldap_page():
    try:
        last_sync_time = float(file(g_ldap_sync_time_file).read().strip())
    except:
        last_sync_time = 0

    # in case of sync problems, synchronize all 20 seconds, instead of the configured
    # regular cache livetime
    if os.path.exists(g_ldap_sync_fail_file):
        cache_livetime = 20
    else:
        cache_livetime = config.ldap_cache_livetime

    if last_sync_time + cache_livetime > time.time():
        return # No action needed, cache is recent enough

    # ok, cache is too old. Act!
    try:
        ldap_sync(False, None)
    except:
        # Do not let the exception through to the user. Instead write last
        # error in a state file which is then visualized for the admin and
        # will be deleted upon next successful sync.
        file(g_ldap_sync_fail_file, 'w').write('%s\n%s' % (time.strftime('%Y-%m-%d %H:%M:%S'),
                                                            traceback.format_exc()))

multisite_user_connectors.append({
    'id':          'ldap',
    'title':       _('LDAP (Active Directory, OpenLDAP)'),
    'short_title': _('LDAP'),

    'login':             ldap_login,
    'sync':              ldap_sync,
    'page':              ldap_page,
    'locked':            user_locked, # no ldap check, just check the WATO attribute.
                                      # This handles setups where the locked attribute is not
                                      # synchronized and the user is enabled in LDAP and disabled
                                      # in Check_MK. When the user is locked in LDAP a login is
                                      # not possible.
    'locked_attributes':      ldap_locked_attributes,
    'multisite_attributes':   ldap_multisite_attributes,
    'non_contact_attributes': ldap_multisite_attributes,
})
