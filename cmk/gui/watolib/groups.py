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
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

from cmk.gui.watolib.utils import convert_cgroups_from_tuple
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.utils import format_config_value
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.watolib.host_attributes import (
    host_attribute_registry,
    ABCHostAttribute,
    HostAttributeTopicBasicSettings,
)
from cmk.gui.plugins.watolib.utils import (
    config_variable_registry,
    wato_fileheader,
)
from cmk.gui.valuespec import DualListChoice

if cmk.is_managed_edition():
    import cmk.gui.cme.managed as managed


def load_host_group_information():
    return _load_group_information()["host"]


def load_service_group_information():
    return _load_group_information()["service"]


def load_contact_group_information():
    return _load_group_information()["contact"]


def _load_group_information():
    cmk_base_groups = _load_cmk_base_groups()
    gui_groups = _load_gui_groups()

    # Merge information from Check_MK and Multisite worlds together
    groups = {}
    for what in ["host", "service", "contact"]:
        groups[what] = {}
        for gid, alias in cmk_base_groups['define_%sgroups' % what].items():
            groups[what][gid] = {'alias': alias}

            if gid in gui_groups['multisite_%sgroups' % what]:
                groups[what][gid].update(gui_groups['multisite_%sgroups' % what][gid])

    return groups


def _load_cmk_base_groups():
    """Load group information from Check_MK world"""
    group_specs = {
        "define_hostgroups": {},
        "define_servicegroups": {},
        "define_contactgroups": {},
    }

    return store.load_mk_file(cmk.utils.paths.check_mk_config_dir + "/wato/groups.mk",
                              default=group_specs)


def _load_gui_groups():
    # Now load information from the Web world
    group_specs = {
        "multisite_hostgroups": {},
        "multisite_servicegroups": {},
        "multisite_contactgroups": {},
    }

    return store.load_mk_file(cmk.utils.paths.default_config_dir + "/multisite.d/wato/groups.mk",
                              default=group_specs)


def add_group(name, group_type, extra_info):
    _check_modify_group_permissions(group_type)
    all_groups = _load_group_information()
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
    all_groups = _load_group_information()
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
    all_groups = _load_group_information()
    groups = all_groups.get(group_type, {})
    if name not in groups:
        raise MKUserError(None, _("Unknown %s group: %s") % (group_type, name))

    # Check if still used
    usages = find_usages_of_group(name, group_type)
    if usages:
        raise MKUserError(
            None,
            _("Unable to delete group. It is still in use by: %s") %
            ", ".join([e[0] for e in usages]))

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
    store.makedirs(check_mk_config_dir)
    output = wato_fileheader()
    for what in ["host", "service", "contact"]:
        if check_mk_groups.get(what):
            output += "if type(define_%sgroups) != dict:\n    define_%sgroups = {}\n" % (what, what)
            output += "define_%sgroups.update(%s)\n\n" % (
                what, format_config_value(check_mk_groups[what]))
    cmk.utils.store.save_file("%s/groups.mk" % check_mk_config_dir, output)

    # Users with passwords for Multisite
    store.makedirs(multisite_config_dir)
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
    all_groups = _load_group_information()
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


@host_attribute_registry.register
class HostAttributeContactGroups(ABCHostAttribute):
    """Attribute needed for folder permissions"""
    def __init__(self):
        ABCHostAttribute.__init__(self)
        self._contactgroups = None
        self._loaded_at = None

    def name(self):
        return "contactgroups"

    def title(self):
        return _("Permissions")

    def topic(self):
        return HostAttributeTopicBasicSettings

    @classmethod
    def sort_index(cls):
        return 25

    def help(self):
        url = "wato.py?mode=rulesets&group=grouping"
        return _("Only members of the contact groups listed here have WATO permission "
                 "to the host / folder. If you want, you can make those contact groups "
                 "automatically also <b>monitoring contacts</b>. This is completely "
                 "optional. Assignment of host and services to contact groups "
                 "can be done by <a href='%s'>rules</a> as well.") % url

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def default_value(self):
        return (True, [])

    def paint(self, value, hostname):
        value = convert_cgroups_from_tuple(value)
        texts = []
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp=lambda a, b: cmp(a[1]['alias'], b[1]['alias']))
        for name, cgroup in items:
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append('<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' %
                             (name, display_name))
        result = ", ".join(texts)
        if texts and value["use"]:
            result += html.render_span(
                html.render_b("*"),
                title=_("These contact groups are also used in the monitoring configuration."))
        return "", result

    def render_input(self, varprefix, value):
        value = convert_cgroups_from_tuple(value)

        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = bool(html.request.var("host")) or html.request.var("mode") == "newhost"
        is_search = varprefix == "host_search"

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        self._vs_contactgroups().render_input(varprefix + self.name(), value['groups'])

        html.hr()

        if is_host:
            html.checkbox(varprefix + self.name() + "_use",
                          value["use"],
                          label=_("Add these contact groups to the host"))

        elif not is_search:
            html.checkbox(varprefix + self.name() + "_recurse_perms",
                          value["recurse_perms"],
                          label=_("Give these groups also <b>permission on all subfolders</b>"))
            html.hr()
            html.checkbox(
                varprefix + self.name() + "_use",
                value["use"],
                label=_("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.br()
            html.checkbox(varprefix + self.name() + "_recurse_use",
                          value["recurse_use"],
                          label=_("Add these groups as <b>contacts in all subfolders</b>"))

        html.hr()
        html.help(
            _("With this option contact groups that are added to hosts are always "
              "being added to services, as well. This only makes a difference if you have "
              "assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. "
              "As long as you do not have any such rule a service always inherits all contact groups "
              "from its host."))
        html.checkbox(varprefix + self.name() + "_use_for_services",
                      value.get("use_for_services", False),
                      label=_("Always add host contact groups also to its services"))

    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)
        self._contactgroups = load_contact_group_information()

    def from_html_vars(self, varprefix):
        self.load_data()

        cgs = self._vs_contactgroups().from_html_vars(varprefix + self.name())

        return {
            "groups": cgs,
            "recurse_perms": html.get_checkbox(varprefix + self.name() + "_recurse_perms"),
            "use": html.get_checkbox(varprefix + self.name() + "_use"),
            "use_for_services": html.get_checkbox(varprefix + self.name() + "_use_for_services"),
            "recurse_use": html.get_checkbox(varprefix + self.name() + "_recurse_use"),
        }

    def filter_matches(self, crit, value, hostname):
        value = convert_cgroups_from_tuple(value)
        # Just use the contact groups for searching
        for contact_group in crit["groups"]:
            if contact_group not in value["groups"]:
                return False
        return True

    def _vs_contactgroups(self):
        cg_choices = sorted([(cg_id, cg_attrs.get("alias", cg_id))
                             for cg_id, cg_attrs in self._contactgroups.items()],
                            key=lambda x: x[1])
        return DualListChoice(choices=cg_choices, rows=20, size=100)
