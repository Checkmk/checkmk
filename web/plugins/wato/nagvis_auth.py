#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# This generates a file called auth.multisite which tells NagVis the
# permissions of the single users. NagVis reads the file when configured
# to use the autorisation module CoreAuthorizationModMultisite.
#
# It writes out a file which directly defines the permissions of the
# single users without telling NagVis anything about roles or similar.
# The permissions for each user are written out as list of permissions
# per user.
#
# The generation of the NagVis auth file must be enabled by setting
# the option "wato_write_nagvis_auth" to True in multisite.mk. This
# module only works in OMD environments at the moment.
#
# To use the auth.multisite file you need to configure NagVis to use
# CoreAuthorizationModMultisite as authorisation module by putting
# the following in the nagvis.ini.php:
#
#  [global]
#  authorisationmodule="CoreAuthorisationModMultisite"
#
# This feature is available since NagVis release 1.6.1.

# Generate the permissions file for the multisite authorization module
def generate_auth_file(users):
    import json

    # FIXME: Den Pfad hier konfigurierbar machen, damit das Feature
    # auch ausserhalb von OMD nutzbar wird.
    auth_file = '%s/etc/nagvis/auth.multisite' % defaults.omd_root

    #
    # 0. Data gathering - populate g_target_maps list
    #
    process_tree(api.get_folder_tree())

    #
    # 1. Write out the user permissions file
    #
    nagvis_users = {}

    for username, user in users.items():
        if not username in nagvis_users:
            nagvis_users[username] = {}

        if 'language' in user:
            nagvis_users[username]['language'] = user['language']

        perms = []

        # Add implicit permissions. These are basic permissions
        # which are needed for most users.
        perms += [
            ('Overview',  'view',               '*'),
            ('General',   'getContextTemplate', '*'),
            ('General',   'getHoverTemplate',   '*'),
            ('General',   'getCfgFileAges',     '*'),
            ('User',      'setOption',          '*'),
            ('Multisite', 'getMaps',            '*'),
        ]

        # Loop the declared NagVis permissions to check if the user is allowed.
        # Add the permissions to the NagVis permissions if the user is permitted.
        for level in nagvis_permissions:
            if config.user_may(username, 'nagvis.%s_%s_%s' % level):
                perms.append(level)

        # WATO folder related permissions
        for mapname, wato_folder in g_target_maps.iteritems():
            if check_folder_permissions(wato_folder, 'read', False, user = username):
                perms.append(('Map', 'view', mapname))

            if check_folder_permissions(wato_folder, 'write', False, user = username):
                perms.append(('Map', 'edit', mapname))

        nagvis_users[username]['permissions'] = perms

    file(auth_file, 'w').write(json.dumps(nagvis_users))

# Only register the hook and permissions when configured to do so
if config.wato_write_nagvis_auth and defaults.omd_root:
    config.declare_permission_section('nagvis', _('NagVis'))

    nagvis_permissions = [
        ('*', '*', '*'),
        ('Map', 'view', '*'),
        ('Map', 'edit', '*'),
        ('Map', 'delete', '*')
    ]

    config.declare_permission(
        'nagvis.*_*_*',
        _('Full access'),
        _('This permission grants full access to NagVis.'),
        [ 'admin' ]
    )

    config.declare_permission(
        'nagvis.Map_view_*',
        _('View all maps'),
        _('Grants read access to all maps.'),
        [ 'guest' ]
    )

    config.declare_permission(
        'nagvis.Map_edit_*',
        _('Edit all maps'),
        _('Grants modify access to all maps.'),
        []
    )

    config.declare_permission(
        'nagvis.Map_delete_*',
        _('Delete all maps'),
        _('Permits to delete all maps.'),
        []
    )

    api.register_hook('users-saved', generate_auth_file)
    api.register_hook('roles-saved', lambda x: generate_auth_file(load_users()))
