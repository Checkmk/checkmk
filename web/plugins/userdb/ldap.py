#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

import config

# FIXME: For some reason mod_python is missing /usr/lib/python2.7/dist-packages
# in sys.path. Therefor the ldap module can not be found. Need to fix this!
import sys ; sys.path.append('/usr/lib/python2.7/dist-packages')
try:
    import ldap
    import ldap.filter
except:
    pass
from lib import *

user_id_attribute = {
    'ad':       'samAccountName',
    'openldap': 'uid',
}

#
# GENERAL LDAP CODE
# FIXME: Maybe extract to central lib
#

class MKLDAPException(MKGeneralException):
    pass

ldap_connection = None

def ldap_uri():
    if config.ldap_connection.get('use_ssl', False):
        uri = 'ldaps://'
    else:
        uri = 'ldap://'

    return uri + '%s:%d' % (config.ldap_connection['server'], config.ldap_connection['port'])

def ldap_connect():
    global ldap_connection
    if ldap_connection:
        return # Only initialize once.

    try:
        ldap
    except:
        raise MKLDAPException(_("The python module python-ldap seem to be missing. You need to "
                                "install this extension to make the LDAP user connector work."))

    try:
        ldap_connection = ldap.ldapobject.ReconnectLDAPObject(ldap_uri())
        ldap_connection.protocol_version = config.ldap_connection['version']
        ldap_default_bind()

    except ldap.LDAPError, e:
        raise MKLDAPException(e)

# Bind with the default credentials
def ldap_default_bind():
    if config.ldap_connection['bind']:
        ldap_bind(config.ldap_connection['bind'][0],
                  config.ldap_connection['bind'][1])

def ldap_bind(username, password):
    try:
        ldap_connection.simple_bind_s(username, password)
    except ldap.LDAPError, e:
        raise MKLDAPException(_('Unable to authenticate with LDAP (%s)' % e))

def ldap_search(base, filter = None, columns = []):
    config_scope = config.ldap_userspec.get('scope', 'sub')
    if config_scope == 'sub':
        scope = ldap.SCOPE_SUBTREE
    elif config_scope == 'base':
        scope = ldap.SCOPE_BASE
    elif config_scope == 'one':
        scope = ldap.SCOPE_ONE

    return ldap_connection.search_s(base, scope, filter, columns)
    #for dn, obj in ldap_connection.search_s(base, scope, filter, columns):
    #    html.log(repr(dn) + ' ' + repr(obj))

def get_user_dn(username):
    key = user_id_attribute[config.ldap_connection['type']]
    # Check wether or not the user exists in the directory
    # It's only ok when exactly one entry is found.
    # Returns the DN in this case.
    result = ldap_search(
        config.ldap_userspec['user_dn'],
        '(%s=%s)' % (key, ldap.filter.escape_filter_chars(username)),
        [key],
    )

    if result:
        return result[0][0]

#
# Module specific code
#

def ldap_login(username, password):
    ldap_connect()
    # Returns None when the user is not found or not uniq, else returns the
    # distinguished name of the user as string which is needed for the login.
    user_dn = get_user_dn(username)
    if not user_dn:
        return None # The user does not exist. Skip this connector.

    # Try to bind with the user provided credentials. This unbinds the default
    # authentication which should be rebound again after trying this.
    try:
        ldap_bind(user_dn, password)
        result = True
    except:
        result = False

    ldap_default_bind()
    return result

multisite_user_connectors.append({
    'id':    'ldap',
    'title': _('LDAP (AD, OpenLDAP)'),

    'login': ldap_login,
    'locked_attributes': [ 'password', 'locked', 'alias', 'email', ],
})
