#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import re
from collections.abc import Callable
from typing import Any, Literal

import cmk.ccc.version as cmk_version
from cmk.ccc.plugin_registry import Registry

from cmk.utils import paths
from cmk.utils.notify_types import EventRule
from cmk.utils.regex import GROUP_NAME_PATTERN
from cmk.utils.timeperiod import timeperiod_spec_alias

from cmk.gui import hooks
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import AllGroupSpecs, GroupName, GroupSpec, GroupSpecs, GroupType
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.userdb import load_roles
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import DualListChoice
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.groups_io import (
    load_contact_group_information,
    load_group_information,
    save_group_information,
)
from cmk.gui.watolib.host_attributes import (
    ABCHostAttribute,
    HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS,
    HostAttributeTopic,
    HostContactGroupSpec,
)
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.watolib.timeperiods import load_timeperiods

ContactGroupUsageFinder = Callable[[GroupName, GlobalSettings], list[tuple[str, str]]]


class ContactGroupUsageFinderRegistry(Registry[ContactGroupUsageFinder]):
    def plugin_name(self, instance: ContactGroupUsageFinder) -> str:
        return instance.__name__


contact_group_usage_finder_registry = ContactGroupUsageFinderRegistry()


def add_group(
    name: GroupName, group_type: GroupType, extra_info: GroupSpec, pprint_value: bool
) -> None:
    check_modify_group_permissions(group_type)
    all_groups = load_group_information()
    groups = all_groups.get(group_type, {})

    # Check group name
    if len(name) == 0:
        raise MKUserError("name", _("Please specify a name of the new group."))
    if " " in name:
        raise MKUserError("name", _("Sorry, spaces are not allowed in group names."))
    if not re.match(GROUP_NAME_PATTERN, name):
        raise MKUserError(
            "name",
            _("Invalid group name. Only the characters a-z, A-Z, 0-9, _, . and - are allowed."),
        )
    if name in groups:
        raise MKUserError("name", _("Sorry, there is already a group with that name"))

    _set_group(all_groups, group_type, name, extra_info, pprint_value)
    _add_group_change(
        extra_info, "edit-%sgroups" % group_type, _l("Create new %s group %s") % (group_type, name)
    )


def edit_group(
    name: GroupName, group_type: GroupType, extra_info: GroupSpec, pprint_value: bool
) -> None:
    check_modify_group_permissions(group_type)
    all_groups = load_group_information()
    groups = all_groups.get(group_type, {})

    if name not in groups:
        raise MKUserError("name", _("Unknown group: %s") % name)

    old_group_backup = copy.deepcopy(groups[name])

    _set_group(all_groups, group_type, name, extra_info, pprint_value)
    customer = customer_api()
    if cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME:
        old_customer = customer.get_customer_id(old_group_backup)
        new_customer = customer.get_customer_id(extra_info)
        if old_customer != new_customer:
            _add_group_change(
                old_group_backup,
                "edit-%sgroups" % group_type,
                _l("Removed %sgroup %s from customer %s")
                % (
                    group_type,
                    name,
                    customer.get_customer_name_by_id(old_customer),
                ),
            )
            _add_group_change(
                extra_info,
                "edit-%sgroups" % group_type,
                _l("Moved %sgroup %s to customer %s. Additional properties may have changed.")
                % (
                    group_type,
                    name,
                    customer.get_customer_name_by_id(new_customer),
                ),
            )
        else:
            _add_group_change(
                old_group_backup,
                "edit-%sgroups" % group_type,
                _l("Updated properties of %sgroup %s") % (group_type, name),
            )
    else:
        _add_group_change(
            extra_info,
            "edit-%sgroups" % group_type,
            _l("Updated properties of %s group %s") % (group_type, name),
        )


class UnknownGroupException(Exception): ...


class GroupInUseException(Exception): ...


def delete_group(name: GroupName, group_type: GroupType, pprint_value: bool) -> None:
    check_modify_group_permissions(group_type)
    # Check if group exists
    all_groups = load_group_information()
    groups = all_groups.get(group_type, {})
    if name not in groups:
        raise UnknownGroupException(
            None,
            _("Unknown %s group: %s") % (group_type, name),
        )

    # Check if still used
    usages = find_usages_of_group(name, group_type)
    if usages:
        raise GroupInUseException(
            None,
            _("Unable to delete group. It is still in use by: %s")
            % ", ".join([e[0] for e in usages]),
        )

    # Delete group
    group = groups.pop(name)
    save_group_information(all_groups, pprint_value)
    _add_group_change(
        group, "edit-%sgroups" % group_type, _l("Deleted %s group %s") % (group_type, name)
    )


def _add_group_change(group: GroupSpec, action_name: str, text: LazyString) -> None:
    add_change(
        action_name=action_name,
        text=text,
        user_id=user.id,
        sites=customer_api().customer_group_sites(group),
        use_git=active_config.wato_use_git,
    )


def check_modify_group_permissions(group_type: GroupType) -> None:
    required_permissions = {
        "contact": ["wato.users"],
        "host": ["wato.groups"],
        "service": ["wato.groups"],
    }

    # Check permissions
    perms = required_permissions.get(group_type)
    if perms is None:
        raise Exception(f"invalid group type {group_type!r}")
    for permission in perms:
        user.need_permission(permission)


def _set_group(
    all_groups: AllGroupSpecs,
    group_type: GroupType,
    name: GroupName,
    extra_info: GroupSpec,
    pprint_value: bool,
) -> None:
    # Check if this alias is used elsewhere
    alias = extra_info.get("alias")
    if not alias:
        raise MKUserError("alias", "Alias is missing")

    unique, info = is_alias_used(group_type, name, alias)
    if not unique:
        assert info
        raise MKUserError("alias", info)

    all_groups.setdefault(group_type, {})
    all_groups[group_type].setdefault(name, {})
    all_groups[group_type][name] = extra_info
    save_group_information(all_groups, pprint_value)

    if group_type == "contact":
        hooks.call("contactgroups-saved", all_groups)


def find_usages_of_group(name: GroupName, group_type: GroupType) -> list[tuple[str, str]]:
    usages = []
    if group_type == "contact":
        usages = find_usages_of_contact_group(name)
    elif group_type == "host":
        usages = find_usages_of_host_group(name)
    elif group_type == "service":
        usages = find_usages_of_service_group(name)
    return usages


def find_usages_of_contact_group(name: GroupName) -> list[tuple[str, str]]:
    """Check if a group is currently in use and cannot be deleted
    Returns a list of occurrances.
    """
    global_config = load_configuration_settings()

    used_in = _find_usages_of_group_in_rules(name, ["host_contactgroups", "service_contactgroups"])
    for finder in contact_group_usage_finder_registry.values():
        used_in += finder(name, global_config)

    return used_in


def _used_in_notification_rule(name: str, rule: EventRule) -> bool:
    return name in rule.get("contact_groups", []) or name in rule.get("match_contactgroups", [])


def find_usages_of_host_group(name: GroupName) -> list[tuple[str, str]]:
    return _find_usages_of_group_in_rules(name, ["host_groups"])


def find_usages_of_service_group(name: GroupName) -> list[tuple[str, str]]:
    return _find_usages_of_group_in_rules(name, ["service_groups"])


def _find_usages_of_group_in_rules(name: GroupName, varnames: list[str]) -> list[tuple[str, str]]:
    used_in = []
    rulesets = AllRulesets.load_all_rulesets()
    for varname in varnames:
        ruleset = rulesets.get(varname)
        for _folder, _rulenr, rule in ruleset.get_rules():
            if rule.value == name:
                used_in.append(
                    (
                        "{}: {}".format(_("Rule set"), ruleset.title()),
                        folder_preserving_link([("mode", "edit_ruleset"), ("varname", varname)]),
                    )
                )
    return used_in


def is_alias_used(
    my_what: GroupType | Literal["roles", "timeperiods"], my_name: GroupName, my_alias: str
) -> tuple[bool, str | None]:
    # Host / Service / Contact groups
    all_groups = load_group_information()
    for what, groups in all_groups.items():
        for gid, group in groups.items():
            if group["alias"] == my_alias and (my_what != what or my_name != gid):
                return False, _("This alias is already used in the %s group %s.") % (what, gid)

    # Timeperiods
    timeperiods = load_timeperiods()
    for timeperiod_id, timeperiod_spec in timeperiods.items():
        if timeperiod_spec_alias(timeperiod_spec) == my_alias and (
            my_what != "timeperiods" or my_name != timeperiod_id
        ):
            return False, _("This alias is already used in time period %s.") % timeperiod_id

    # Roles
    roles = load_roles()
    for role_id, role_spec in roles.items():
        if role_spec.get("alias") == my_alias and (my_what != "roles" or my_name != role_id):
            return False, _("This alias is already used in the role %s.") % role_id

    return True, None


class HostAttributeContactGroups(ABCHostAttribute):
    """Attribute needed for folder permissions"""

    def __init__(self) -> None:
        ABCHostAttribute.__init__(self)
        self._contactgroups: GroupSpecs | None = None
        self._loaded_at: int | None = None

    def name(self) -> str:
        return "contactgroups"

    def title(self) -> str:
        return _("Permissions")

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    @classmethod
    def sort_index(cls) -> int:
        return 25

    def is_show_more(self) -> bool:
        return True

    def help(self) -> str:
        url = makeuri_contextless(
            request,
            [("mode", "edit_ruleset"), ("varname", "host_contactgroups")],
            filename="wato.py",
        )
        return (
            _(
                "Only members of the contact groups listed here have Setup "
                "permission for the host/folder. Optionally, you can make these "
                "contact groups automatically monitor contacts. The assignment "
                "of hosts to contact groups can also be defined by "
                "<a href='%s'>rules</a>."
            )
            % url
        )

    def show_in_table(self) -> bool:
        return False

    def show_in_folder(self) -> bool:
        return True

    def default_value(self) -> HostContactGroupSpec:
        return HostContactGroupSpec(
            {
                "groups": [],
                "recurse_perms": False,
                "use": False,
                "use_for_services": False,
                "recurse_use": False,
            }
        )

    def paint(self, value, hostname):
        texts: list[HTML] = []
        self.load_data()
        if self._contactgroups is None:  # conditional caused by horrible API
            raise Exception("invalid contact groups")
        items = self._contactgroups.items()
        for name, cgroup in sorted(items, key=lambda x: x[1]["alias"]):
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append(
                    HTMLWriter.render_a(
                        display_name,
                        href=makeuri_contextless(
                            request,
                            [("mode", "edit_contact_group"), ("edit", name)],
                            filename="wato.py",
                        ),
                    )
                )
        result: HTML = HTML.without_escaping(", ").join(texts)
        if texts and value["use"]:
            result += HTMLWriter.render_span(
                HTMLWriter.render_b("*"),
                title=_("These contact groups are also used in the monitoring configuration."),
            )
        return "", result

    def render_input(self, varprefix: str, value: Any) -> None:
        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = bool(request.var("host")) or request.var("mode") == "newhost"
        is_search = varprefix == "host_search"

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        self._vs_contactgroups().render_input(varprefix + self.name(), value["groups"])

        html.hr()

        if is_host:
            html.checkbox(
                varprefix + self.name() + "_use",
                value["use"],
                label=_("Add these contact groups to the host"),
            )

        elif not is_search:
            html.checkbox(
                varprefix + self.name() + "_recurse_perms",
                value["recurse_perms"],
                label=_("Give these groups also <b>permission on all subfolders</b>"),
            )
            html.hr()
            html.checkbox(
                varprefix + self.name() + "_use",
                value["use"],
                label=_("Add these groups as <b>contacts</b> to all hosts <b>in this folder</b>"),
            )
            html.br()
            html.checkbox(
                varprefix + self.name() + "_recurse_use",
                value["recurse_use"],
                label=_(
                    "Add these groups as <b>contacts</b> to all hosts <b>in all subfolders of this folder</b>"
                ),
            )

        html.hr()
        html.help(
            _(
                "With this option contact groups that are added to hosts are always "
                "being added to services, as well. This only makes a difference if you have "
                "assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. "
                "As long as you do not have any such rule a service always inherits all contact groups "
                "from its host."
            )
        )
        html.checkbox(
            varprefix + self.name() + "_use_for_services",
            value.get("use_for_services", False),
            label=(
                _("Always add host contact groups also to its services")
                if is_host
                else _(
                    "Always add these groups as <b>contacts</b> to all services <b>in all subfolders of this folder</b>"
                )
            ),
        )

    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)
        self._contactgroups = load_contact_group_information()

    def from_html_vars(self, varprefix: str) -> dict[str, Any]:
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
        # Just use the contact groups for searching
        for contact_group in crit["groups"]:
            if contact_group not in value["groups"]:
                return False
        return True

    def _vs_contactgroups(self):
        if self._contactgroups is None:  # conditional caused by horrible API
            raise Exception("invalid contact groups")
        cg_choices = sorted(
            [
                (cg_id, cg_attrs.get("alias", cg_id))
                for cg_id, cg_attrs in self._contactgroups.items()
            ],
            key=lambda x: x[1],
        )
        return DualListChoice(choices=cg_choices, rows=20, size=100)

    def validate_input(self, value, varprefix):
        if not isinstance(value, dict):
            raise MKUserError(self.name(), "Unknown format.")
        self.load_data()
        self._vs_contactgroups().validate_value(value.get("groups", []), varprefix)

    def openapi_field(self):
        # FIXME: due to cyclical imports which, when fixed, expose even more cyclical imports.
        from cmk.gui import fields as gui_fields

        from cmk import fields

        return fields.Nested(
            gui_fields.HostContactGroup,
            description=self.help(),
        )
