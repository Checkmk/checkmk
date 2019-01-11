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
import re
import copy

import cmk
import cmk.utils.store as store

import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.hooks as hooks
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.utils import format_config_value
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.plugins.watolib.utils import (
    config_variable_registry,
    wato_fileheader,
)

if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed


def add_group(name, group_type, extra_info):
    _check_modify_group_permissions(group_type)
    all_groups = userdb.load_group_information()
    groups = all_groups.get(group_type, {})

    # Check group name
    if len(name) == 0:
        raise MKUserError("name", _("Please specify a name of the new group."))
    if ' ' in name:
        raise MKUserError("name", _("Sorry, spaces are not allowed in group names."))
    if not re.match(r"^[-a-z0-9A-Z_\.]*$", name):
        raise MKUserError(
            "name",
            _("Invalid group name. Only the characters a-z, A-Z, 0-9, _, . and - are allowed."))
    if name in groups:
        raise MKUserError("name", _("Sorry, there is already a group with that name"))

    _set_group(all_groups, group_type, name, extra_info)
    _add_group_change(extra_info, "edit-%sgroups" % group_type,
                      _("Create new %s group %s") % (group_type, name))


def edit_group(name, group_type, extra_info):
    _check_modify_group_permissions(group_type)
    all_groups = userdb.load_group_information()
    groups = all_groups.get(group_type, {})

    if name not in groups:
        raise MKUserError("name", _("Unknown group: %s") % name)

    old_group_backup = copy.deepcopy(groups[name])

    _set_group(all_groups, group_type, name, extra_info)
    if cmk.is_managed_edition():
        old_customer = managed.get_customer_id(old_group_backup)
        new_customer = managed.get_customer_id(extra_info)
        if old_customer != new_customer:
            _add_group_change(
                old_group_backup, "edit-%sgroups" % group_type,
                _("Removed %sgroup %s from customer %s") %
                (group_type, name, managed.get_customer_name_by_id(old_customer)))
            _add_group_change(
                extra_info, "edit-%sgroups" % group_type,
                _("Moved %sgroup %s to customer %s. Additional properties may have changed.") %
                (group_type, name, managed.get_customer_name_by_id(new_customer)))
        else:
            _add_group_change(old_group_backup, "edit-%sgroups" % group_type,
                              _("Updated properties of %sgroup %s") % (group_type, name))
    else:
        _add_group_change(extra_info, "edit-%sgroups" % group_type,
                          _("Updated properties of %s group %s") % (group_type, name))


def delete_group(name, group_type):
    _check_modify_group_permissions(group_type)

    # Check if group exists
    all_groups = userdb.load_group_information()
    groups = all_groups.get(group_type, {})
    if name not in groups:
        raise MKUserError(None, _("Unknown %s group: %s") % (group_type, name))

    # Check if still used
    usages = find_usages_of_group(name, group_type)
    if usages:
        raise MKUserError(
            None,
            _("Unable to delete group. It is still in use by: %s") % ", ".join(
                [e[0] for e in usages]))

    # Delete group
    group = groups.pop(name)
    save_group_information(all_groups)
    _add_group_change(group, "edit-%sgroups", _("Deleted %s group %s") % (group_type, name))


# TODO: Consolidate all group change related functions in a class that can be overriden
# by the CME code for better encapsulation.
def _add_group_change(group, action_name, text):
    group_sites = None
    if cmk.is_managed_edition() and not managed.is_global(managed.get_customer_id(group)):
        group_sites = managed.get_sites_of_customer(managed.get_customer_id(group))

    add_change(action_name, text, sites=group_sites)


def _check_modify_group_permissions(group_type):
    required_permissions = {
        "contact": ["wato.users"],
        "host": ["wato.groups"],
        "service": ["wato.groups"],
    }

    # Check permissions
    for permission in required_permissions.get(group_type):
        config.user.need_permission(permission)


def _set_group(all_groups, group_type, name, extra_info):
    # Check if this alias is used elsewhere
    alias = extra_info.get("alias")
    if not alias:
        raise MKUserError("alias", "Alias is missing")

    unique, info = is_alias_used(group_type, name, alias)
    if not unique:
        raise MKUserError("alias", info)

    all_groups.setdefault(group_type, {})
    all_groups[group_type].setdefault(name, {})
    all_groups[group_type][name] = extra_info
    save_group_information(all_groups)

    if group_type == "contact":
        hooks.call('contactgroups-saved', all_groups)


def save_group_information(all_groups, custom_default_config_dir=None):
    # Split groups data into Check_MK/Multisite parts
    check_mk_groups = {}
    multisite_groups = {}

    if custom_default_config_dir:
        check_mk_config_dir = "%s/conf.d/wato" % custom_default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % custom_default_config_dir
    else:
        check_mk_config_dir = "%s/conf.d/wato" % cmk.utils.paths.default_config_dir
        multisite_config_dir = "%s/multisite.d/wato" % cmk.utils.paths.default_config_dir

    for what, groups in all_groups.items():
        check_mk_groups[what] = {}
        for gid, group in groups.items():
            check_mk_groups[what][gid] = group['alias']

            for attr, value in group.items():
                if attr != 'alias':
                    multisite_groups.setdefault(what, {})
                    multisite_groups[what].setdefault(gid, {})
                    multisite_groups[what][gid][attr] = value

    # Save Check_MK world related parts
    store.mkdir(check_mk_config_dir)
    output = wato_fileheader()
    for what in ["host", "service", "contact"]:
        if check_mk_groups.get(what):
            output += "if type(define_%sgroups) != dict:\n    define_%sgroups = {}\n" % (what, what)
            output += "define_%sgroups.update(%s)\n\n" % (
                what, format_config_value(check_mk_groups[what]))
    cmk.utils.store.save_file("%s/groups.mk" % check_mk_config_dir, output)

    # Users with passwords for Multisite
    store.mkdir(multisite_config_dir)
    output = wato_fileheader()
    for what in ["host", "service", "contact"]:
        if multisite_groups.get(what):
            output += "multisite_%sgroups = \\\n%s\n\n" % (
                what, format_config_value(multisite_groups[what]))
    cmk.utils.store.save_file("%s/groups.mk" % multisite_config_dir, output)


def find_usages_of_group(name, group_type):
    usages = []
    if group_type == 'contact':
        usages = find_usages_of_contact_group(name)
    elif group_type == 'host':
        usages = find_usages_of_host_group(name)
    elif group_type == 'service':
        usages = find_usages_of_service_group(name)
    return usages


# Check if a group is currently in use and cannot be deleted
# Returns a list of occurrances.
# Possible usages:
# - 1. rules: host to contactgroups, services to contactgroups
# - 2. user memberships
def find_usages_of_contact_group(name):
    # Part 1: Rules
    used_in = _find_usages_of_group_in_rules(name, ['host_contactgroups', 'service_contactgroups'])

    # Is the contactgroup assigned to a user?
    users = userdb.load_users()
    entries = users.items()
    for userid, user in sorted(entries, key=lambda x: x[1].get("alias", x[0])):
        cgs = user.get("contactgroups", [])
        if name in cgs:
            used_in.append(('%s: %s' % (_('User'), user.get('alias', userid)),
                            folder_preserving_link([('mode', 'edit_user'), ('edit', userid)])))

    global_config = load_configuration_settings()

    # Used in default_user_profile?
    config_variable = config_variable_registry['default_user_profile']()
    domain = config_variable.domain()
    configured = global_config.get('default_user_profile', {})
    default_value = domain().default_globals()["default_user_profile"]
    if (configured and name in configured['contactgroups']) \
       or name in  default_value['contactgroups']:
        used_in.append(('%s' % (_('Default User Profile')),
                        folder_preserving_link([('mode', 'edit_configvar'),
                                                ('varname', 'default_user_profile')])))

    # Is the contactgroup used in mkeventd notify (if available)?
    if 'mkeventd_notify_contactgroup' in config_variable_registry:
        config_variable = config_variable_registry['mkeventd_notify_contactgroup']()
        domain = config_variable.domain()
        configured = global_config.get('mkeventd_notify_contactgroup')
        default_value = domain().default_globals()["mkeventd_notify_contactgroup"]
        if (configured and name == configured) \
           or name == default_value:
            used_in.append(('%s' % (config_variable.valuespec().title()),
                            folder_preserving_link([('mode', 'edit_configvar'),
                                                    ('varname', 'mkeventd_notify_contactgroup')])))

    return used_in


def find_usages_of_host_group(name):
    return _find_usages_of_group_in_rules(name, ['host_groups'])


def find_usages_of_service_group(name):
    return _find_usages_of_group_in_rules(name, ['service_groups'])


def _find_usages_of_group_in_rules(name, varnames):
    used_in = []
    rulesets = AllRulesets()
    rulesets.load()
    for varname in varnames:
        ruleset = rulesets.get(varname)
        for _folder, _rulenr, rule in ruleset.get_rules():
            if rule.value == name:
                used_in.append(("%s: %s" % (_("Ruleset"), ruleset.title()),
                                folder_preserving_link([("mode", "edit_ruleset"),
                                                        ("varname", varname)])))
    return used_in


def is_alias_used(my_what, my_name, my_alias):
    # Host / Service / Contact groups
    all_groups = userdb.load_group_information()
    for what, groups in all_groups.items():
        for gid, group in groups.items():
            if group['alias'] == my_alias and (my_what != what or my_name != gid):
                return False, _("This alias is already used in the %s group %s.") % (what, gid)

    # Timeperiods
    timeperiods = cmk.gui.watolib.timeperiods.load_timeperiods()
    for key, value in timeperiods.items():
        if value.get("alias") == my_alias and (my_what != "timeperiods" or my_name != key):
            return False, _("This alias is already used in timeperiod %s.") % key

    # Roles
    roles = userdb.load_roles()
    for key, value in roles.items():
        if value.get("alias") == my_alias and (my_what != "roles" or my_name != key):
            return False, _("This alias is already used in the role %s.") % key

    return True, None
