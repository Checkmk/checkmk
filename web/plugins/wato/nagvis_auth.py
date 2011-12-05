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

# Generate the permissions file for the multisite authorization module
def generate_auth_file(users):
    import json

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
            nagvis_users[username] = { 'permissions': [] }

        if 'language' in user:
            nagvis_users[username]['language'] = user['language']

        #if user_may(username, ''):

        # WATO folder relatived permissions
        for mapname, wato_folder in g_target_maps.iteritems():
            if check_folder_permissions(wato_folder, 'read', False, user = username):
                nagvis_users[username]['permissions'].append(('Map', 'view', mapname))

            if check_folder_permissions(wato_folder, 'write', False, user = username):
                nagvis_users[username]['permissions'].append(('Map', 'edit', mapname))

    file(auth_file, 'w').write(json.dumps(nagvis_users))

# Only register this hook when configured to do so
# This works only in OMD for the moment
if config.wato_write_nagvis_auth and defaults.omd_root:
    api.register_hook('users-saved', generate_auth_file)
