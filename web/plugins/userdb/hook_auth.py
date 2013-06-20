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

# Creates a includable file for the needed programming languages.
# It can be used to use the multisite permissions in other addons
# for checking permissions.
#
# This declares the following API:
#
# all_users()
# Returns an assoziative array with the usernames as keys and user
# objects as value.
#
# users_with_role(<ROLE_NAME>)
# Returns an array of usernames
#
# user_roles(<USER_NAME>)
# Returns an array of rolenames of the user
#
# user_permissions(<USER_NAME>)
# Returns an array of all permissions of the user
#
# roles_with_permission(<PERMISSION>)
# Returns an array of rolenames with the given permission
#
# users_with_permission(<PERMISSION>)
# Returns an array of usernames with the given permission
#
# get_folder_permissions(<USERNAME>)
# Returns an array of all wato folder related permissions of the
# given user. The keys are the folder paths and the values are an
# array of "read" and "write" elements with boolean values.
#
# may(<USER_NAME>, <PERMISSION>)
# Returns true/false wether or not the user is permitted

g_auth_base_dir = defaults.var_dir + '/wato/auth'

def format_php(data, lvl = 1):
    s = ''
    if isinstance(data, tuple) or isinstance(data, list):
        s += 'array(\n'
        for item in data:
            s += '    ' * lvl + format_php(item, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, dict):
        s += 'array(\n'
        for key, val in data.iteritems():
            s += '    ' * lvl + format_php(key, lvl + 1) + ' => ' + format_php(val, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, str):
        s += '\'%s\'' % data.replace('\'', '\\\'')
    elif isinstance(data, unicode):
        s += '\'%s\'' % data.encode('utf-8').replace('\'', '\\\'')
    elif isinstance(data, bool):
        s += data and 'true' or 'false'
    elif data is None:
        s += 'null'
    else:
        s += str(data)

    return s


def create_php_file(callee, users, role_permissions, folder_permissions):
    # Set a language for all users
    for username in users:
        users[username].setdefault('language', config.default_language)

    file(g_auth_base_dir + '/auth.php', 'w').write('''<?php
// Created by Multisite UserDB Hook (%s)
global $mk_users, $mk_roles, $mk_folders;
$mk_users   = %s;
$mk_roles   = %s;
$mk_folders = %s;

function get_folder_permissions($username) {
    global $mk_folders;
    if(!isset($mk_folders[$username])) {
        return array();
    } else {
        return $mk_folders[$username];
    }
}

function all_users() {
    global $mk_users;
    return $mk_users;
}

function user_roles($username) {
    global $mk_users;
    if(!isset($mk_users[$username]))
        return array();
    else
        return $mk_users[$username]['roles'];
}

function user_permissions($username) {
    global $mk_roles;
    $permissions = array();

    foreach(user_roles($username) AS $role)
        $permissions = array_merge($permissions, $mk_roles[$role]);

    // Make the array uniq
    array_flip($permissions);
    array_flip($permissions);

    return $permissions;
}

function users_with_role($want_role) {
    global $mk_users, $mk_roles;
    $result = array();
    foreach($mk_users AS $username => $user) {
        foreach($user['roles'] AS $role) {
            if($want_role == $role) {
                $result[] = $username;
            }
        }
    }
    return $result;
}

function roles_with_permission($want_permission) {
    global $mk_roles;
    $result = array();
    foreach($mk_roles AS $rolename => $role) {
        foreach($role AS $permission) {
            if($permission == $want_permission) {
                $result[] = $rolename;
                break;
            }
        }
    }
    return $result;
}

function users_with_permission($need_permission) {
    global $mk_users;
    $result = array();
    foreach(roles_with_permission($need_permission) AS $rolename) {
        $result = array_merge($result, users_with_role($rolename));
    }
    return $result;
}

function may($username, $need_permission) {
    global $mk_roles;
    foreach(user_roles($username) AS $role) {
        foreach($mk_roles[$role] AS $permission) {
            if($need_permission == $permission) {
                return true;
            }
        }
    }
    return false;
}

?>
''' % (callee, format_php(users), format_php(role_permissions), format_php(folder_permissions)))

def create_auth_file(callee, users):
    make_nagios_directory(g_auth_base_dir)
    import wato # HACK: cleanup!
    create_php_file(callee, users, config.get_role_permissions(), wato.get_folder_permissions_of_users(users))

hooks.register('users-saved',      lambda users: create_auth_file("users-saved", users))
hooks.register('roles-saved',      lambda x: create_auth_file("roles-saved", load_users()))
hooks.register('activate-changes', lambda x: create_auth_file("activate-changes", load_users()))
