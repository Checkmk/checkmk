#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
# user_groups(<USER_NAME>)
# Returns an array of names of contactgroups of the user
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
# may(<USER_NAME>, <PERMISSION>)
# Returns true/false whether or not the user is permitted

import copy
from pathlib import Path

import cmk.utils.paths
import cmk.utils.store as store

import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
from cmk.gui.config import active_config
from cmk.gui.groups import load_contact_group_information
from cmk.gui.utils.roles import get_role_permissions


def _auth_php():
    return Path(cmk.utils.paths.var_dir) / "wato" / "auth" / "auth.php"


# TODO: Fix copy-n-paste with cmk.gui.watolib.tags.
def _format_php(data, lvl=1):
    s = ""
    if isinstance(data, (list, tuple)):
        s += "array(\n"
        for item in data:
            s += "    " * lvl + _format_php(item, lvl + 1) + ",\n"
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, dict):
        s += "array(\n"
        for key, val in data.items():
            s += (
                "    " * lvl
                + _format_php(key, lvl + 1)
                + " => "
                + _format_php(val, lvl + 1)
                + ",\n"
            )
        s += "    " * (lvl - 1) + ")"
    elif isinstance(data, str):
        s += "'%s'" % data.replace("'", "\\'")
    elif isinstance(data, bool):
        s += data and "true" or "false"
    elif data is None:
        s += "null"
    else:
        s += str(data)

    return s


def _create_php_file(callee, users, role_permissions, groups):
    # Do not change WATO internal objects
    nagvis_users = copy.deepcopy(users)

    for user in nagvis_users.values():
        user.setdefault("language", active_config.default_language)  # Set a language for all users
        user.pop("session_info", None)  # remove the SessionInfo object

    content = """<?php
// Created by Multisite UserDB Hook (%s)
global $mk_users, $mk_roles, $mk_groups;
$mk_users   = %s;
$mk_roles   = %s;
$mk_groups  = %s;

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

function user_groups($username) {
    global $mk_users;
    if(!isset($mk_users[$username]) || !isset($mk_users[$username]['contactgroups']))
        return array();
    else
        return $mk_users[$username]['contactgroups'];
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

function permitted_maps($username) {
    global $mk_groups;
    $maps = array();
    foreach (user_groups($username) AS $groupname) {
        if (isset($mk_groups[$groupname])) {
            foreach ($mk_groups[$groupname] AS $mapname) {
                $maps[$mapname] = null;
            }
        }
    }
    return array_keys($maps);
}

?>
""" % (
        callee,
        _format_php(nagvis_users),
        _format_php(role_permissions),
        _format_php(groups),
    )

    store.makedirs(_auth_php().parent)
    store.save_text_to_file(_auth_php(), content)


def _create_auth_file(callee, users=None):
    if users is None:
        users = userdb.load_users()

    contactgroups = load_contact_group_information()
    groups = {}
    for gid, group in contactgroups.items():
        if "nagvis_maps" in group and group["nagvis_maps"]:
            groups[gid] = group["nagvis_maps"]

    _create_php_file(callee, users, get_role_permissions(), groups)


def _on_userdb_job():
    # Working around the problem that the auth.php file needed for multisite based
    # authorization of external addons might not exist when setting up a new installation
    # This is a good place to replace old api based files in the future.
    if not _auth_php().exists() or _auth_php().stat().st_size == 0:
        _create_auth_file("page_hook")


# TODO: Should we not execute this hook also when folders are modified?
hooks.register_builtin("userdb-job", _on_userdb_job)
hooks.register_builtin("users-saved", lambda users: _create_auth_file("users-saved", users))
hooks.register_builtin("roles-saved", lambda x: _create_auth_file("roles-saved"))
hooks.register_builtin("contactgroups-saved", lambda x: _create_auth_file("contactgroups-saved"))
hooks.register_builtin("activate-changes", lambda x: _create_auth_file("activate-changes"))
