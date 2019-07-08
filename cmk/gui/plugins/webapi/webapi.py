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

# TODO CLEANUP: Replace MKUserError by MKAPIError or something like that

import copy
from functools import partial
import os

import cmk

import cmk.utils.tags
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError, MKAuthException, MKException
from cmk.gui.plugins.userdb.htpasswd import hash_password
import cmk.gui.watolib.users
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.tags import (
    TagConfigFile,)
from cmk.gui.watolib.groups import (
    load_contact_group_information,
    load_host_group_information,
    load_service_group_information,
)

import cmk.gui.bi as bi

from cmk.gui.plugins.webapi import (
    APICallCollection,
    api_call_collection_registry,
    validate_host_attributes,
    validate_config_hash,
    check_hostname,
    add_configuration_hash,
    compute_config_hash,
)

#.
#   .--Folders-------------------------------------------------------------.
#   |                   _____     _     _                                  |
#   |                  |  ___|__ | | __| | ___ _ __ ___                    |
#   |                  | |_ / _ \| |/ _` |/ _ \ '__/ __|                   |
#   |                  |  _| (_) | | (_| |  __/ |  \__ \                   |
#   |                  |_|  \___/|_|\__,_|\___|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallFolders(APICallCollection):
    def get_api_calls(self):
        return {
            "get_folder": {
                "handler": self._get,
                "required_keys": ["folder"],
                "optional_keys": ["effective_attributes"],
                "locking": False,
            },
            "add_folder": {
                "handler": self._add,
                "required_keys": ["folder", "attributes"],
                "optional_keys": ["create_parent_folders"],
            },
            "edit_folder": {
                "handler": self._edit,
                "required_keys": ["folder"],
                "optional_keys": ["attributes", "configuration_hash"],
            },
            "delete_folder": {
                "handler": self._delete,
                "required_keys": ["folder"],
                "optional_keys": ["configuration_hash"],
            },
            "get_all_folders": {
                "handler": self._get_all,
                "optional_keys": ["effective_attributes"],
                "locking": False,
            },
        }

    def _get(self, request):
        folder_path = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)

        folder = watolib.Folder.folder(folder_path)
        if bool(int(request.get("effective_attributes", "0"))):
            attributes = folder.effective_attributes()
        else:
            attributes = folder.attributes()

        response = {"attributes": attributes}
        add_configuration_hash(response, attributes)
        return response

    def _add(self, request):
        folder_path = request["folder"]
        watolib.check_wato_foldername(None, os.path.basename(folder_path), just_name=True)

        folder_attributes = request.get("attributes", {})
        if "alias" in folder_attributes:
            folder_alias = folder_attributes.pop("alias") or os.path.basename(folder_path)
        else:
            folder_alias = os.path.basename(folder_path)

        # Validates host and folder attributes, since there are no real folder attributes, at all...
        validate_host_attributes(folder_attributes, new=True)

        # Check existance of parent folder, create it when configured
        create_parent_folders = bool(int(request.get("create_parent_folders", "1")))
        if create_parent_folders or watolib.Folder.folder_exists(os.path.dirname(folder_path)):
            watolib.Folder.root_folder().create_missing_folders(folder_path)
            watolib.Folder.folder(folder_path).edit(folder_alias, folder_attributes)
        else:
            raise MKUserError(None, _("Unable to create parent folder(s)."))

    def _edit(self, request):
        folder_path = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)

        folder = watolib.Folder.folder(folder_path)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], folder.attributes())

        folder_attributes = request.get("attributes", {})
        if "alias" in folder_attributes:
            folder_alias = folder_attributes.pop("alias") or os.path.basename(folder_path)
        else:
            folder_alias = os.path.basename(folder_path)

        # Validates host and folder attributes, since there are no real folder attributes, at all...
        validate_host_attributes(folder_attributes, new=False)

        folder.edit(folder_alias, folder_attributes)

    def _delete(self, request):
        folder_path = request["folder"]
        if not watolib.Folder.folder_exists(folder_path):
            raise MKUserError(None, _("Folder %s does not exist") % folder_path)

        folder = watolib.Folder.folder(folder_path)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], folder.attributes())

        if folder.is_root():
            raise MKUserError(None, _("Unable to delete root folder"))

        folder.parent().delete_subfolder(folder.name())

    def _get_all(self, request):
        folders = {}
        effective_attributes = bool(int(request.get("effective_attributes", "0")))

        for folder_path, folder in watolib.Folder.all_folders().items():
            if effective_attributes:
                folders[folder_path] = folder.effective_attributes()
            else:
                folders[folder_path] = folder.attributes()

        return folders


#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallHosts(APICallCollection):
    def get_api_calls(self):
        return {
            "add_host": {
                "handler": self._add,
                "required_keys": ["hostname", "folder"],
                "optional_keys": ["attributes", "nodes", "create_folders"],
            },
            "add_hosts": {
                "handler": self._add_hosts,
                "required_keys": ["hosts"],
            },
            "edit_host": {
                "handler": self._edit,
                "required_keys": ["hostname"],
                "optional_keys": ["unset_attributes", "attributes", "nodes"],
            },
            "edit_hosts": {
                "handler": self._edit_hosts,
                "required_keys": ["hosts"],
            },
            "get_host": {
                "handler": self._get,
                "required_keys": ["hostname"],
                "optional_keys": ["effective_attributes"],
                "locking": False,
            },
            "delete_host": {
                "handler": self._delete,
                "required_keys": ["hostname"],
            },
            "delete_hosts": {
                "handler": self._delete_hosts,
                "required_keys": ["hostnames"],
            },
            "get_all_hosts": {
                "handler": self._get_all,
                "optional_keys": ["effective_attributes"],
                "locking": False,
            },
        }

    def _add(self, request):
        create_parent_folders_var = request.get("create_parent_folders",
                                                request.get("create_folders", "1"))
        create_parent_folders = bool(int(create_parent_folders_var))

        hostname = request.get("hostname")
        folder_path = request.get("folder")
        attributes = request.get("attributes", {})
        cluster_nodes = request.get("nodes")

        check_hostname(hostname, should_exist=False)

        # Validate folder
        if folder_path != "" and folder_path != "/":
            folders = folder_path.split("/")
            for foldername in folders:
                watolib.check_wato_foldername(None, foldername, just_name=True)
        else:
            folder_path = ""
            folders = [""]

        # Deprecated, but still supported
        # Nodes are now specified in an extra key
        if ".nodes" in attributes:
            cluster_nodes = attributes[".nodes"]
            del attributes[".nodes"]
        validate_host_attributes(attributes, new=True)

        # Create folder(s)
        if not watolib.Folder.folder_exists(folder_path):
            if not create_parent_folders:
                raise MKUserError(None, _("Unable to create parent folder(s)."))
            watolib.Folder.create_missing_folders(folder_path)

        # Add host
        if cluster_nodes:
            cluster_nodes = map(str, cluster_nodes)
        watolib.Folder.folder(folder_path).create_hosts([(hostname, attributes, cluster_nodes)])

    def _add_hosts(self, request):
        for host_request in request["hosts"]:
            self._add(host_request)

    def _edit(self, request):
        hostname = request.get("hostname")
        attributes = request.get("attributes", {})
        unset_attribute_names = request.get("unset_attributes", [])
        cluster_nodes = request.get("nodes")

        check_hostname(hostname, should_exist=True)

        host = watolib.Host.host(hostname)

        # Deprecated, but still supported
        # Nodes are now specified in an extra key
        if ".nodes" in attributes:
            cluster_nodes = attributes[".nodes"]
            del attributes[".nodes"]
        validate_host_attributes(attributes, new=False)

        # Update existing attributes. Add new, remove unset_attributes
        current_attributes = host.attributes().copy()
        for attrname in unset_attribute_names:
            if attrname in current_attributes:
                del current_attributes[attrname]
        current_attributes.update(attributes)

        if not cluster_nodes:
            cluster_nodes = host.cluster_nodes()

        if cluster_nodes:
            cluster_nodes = map(str, cluster_nodes)

        host.edit(current_attributes, cluster_nodes)

    def _edit_hosts(self, request):
        for host_request in request["hosts"]:
            self._edit(host_request)

    def _get(self, request):
        hostname = request.get("hostname")

        check_hostname(hostname, should_exist=True)

        host = watolib.Host.host(hostname)
        host.need_permission("read")
        if bool(int(request.get("effective_attributes", "0"))):
            attributes = host.effective_attributes()
        else:
            attributes = host.attributes()

        response = {"attributes": attributes, "path": host.folder().path(), "hostname": host.name()}
        if host.is_cluster():
            response["nodes"] = host.cluster_nodes()
        return response

    def _get_all(self, request):
        effective_attributes = bool(int(request.get("effective_attributes", "0")))

        response = {}
        all_hosts = watolib.Folder.root_folder().all_hosts_recursively()

        for hostname, host in all_hosts.items():
            host.need_permission("read")
            if effective_attributes:
                attributes = host.effective_attributes()
            else:
                attributes = host.attributes()
            response[hostname] = {
                "attributes": attributes,
                "path": host.folder().path(),
                "hostname": host.name()
            }
            if host.is_cluster():
                response[hostname]["nodes"] = host.cluster_nodes()

        return response

    def _delete(self, request):
        hostname = request["hostname"]
        check_hostname(hostname, should_exist=True)

        host = watolib.Host.host(hostname)
        host.folder().delete_hosts([host.name()])

    def _delete_hosts(self, request):
        all_hosts = watolib.Host.all()
        delete_hostnames = set(request["hostnames"])
        all_hostnames = set(all_hosts.keys())

        unknown_hosts = delete_hostnames - all_hostnames
        if unknown_hosts:
            raise MKUserError(None, _("No such host(s): %s") % ", ".join(unknown_hosts))

        grouped_by_folders = {}
        for hostname in delete_hostnames:
            grouped_by_folders.setdefault(all_hosts[hostname].folder(), []).append(hostname)

        for folder, hostnames in grouped_by_folders.iteritems():
            folder.delete_hosts(hostnames)


#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallGroups(APICallCollection):
    def get_api_calls(self):
        return {
            "get_all_contactgroups": {
                "handler": self._get_all_contactgroups,
                "locking": False,
            },
            "delete_contactgroup": {
                "handler": partial(self._delete_group, "contact"),
                "required_keys": ["groupname"],
            },
            "add_contactgroup": {
                "handler": partial(self._add_group, "contact"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer", "nagvis_maps"],
            },
            "edit_contactgroup": {
                "handler": partial(self._edit_group, "contact"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer", "nagvis_maps"],
            },
            "get_all_hostgroups": {
                "handler": self._get_all_hostgroups,
                "locking": False,
            },
            "delete_hostgroup": {
                "handler": partial(self._delete_group, "host"),
                "required_keys": ["groupname"],
            },
            "add_hostgroup": {
                "handler": partial(self._add_group, "host"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer"],
            },
            "edit_hostgroup": {
                "handler": partial(self._edit_group, "host"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer"],
            },
            "get_all_servicegroups": {
                "handler": self._get_all_servicegroups,
                "locking": False,
            },
            "delete_servicegroup": {
                "handler": partial(self._delete_group, "service"),
                "required_keys": ["groupname"],
            },
            "add_servicegroup": {
                "handler": partial(self._add_group, "service"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer"],
            },
            "edit_servicegroup": {
                "handler": partial(self._edit_group, "service"),
                "required_keys": ["groupname", "alias"],
                "optional_keys": ["customer"],
            },
        }

    def _get_all_servicegroups(self, request):
        return load_service_group_information()

    def _get_all_contactgroups(self, request):
        return load_contact_group_information()

    def _get_all_hostgroups(self, request):
        return load_host_group_information()

    def _delete_group(self, group_type, request):
        groupname = request.get("groupname")
        watolib.delete_group(groupname, group_type)

    def _add_group(self, group_type, request):
        self._check_customer(request)
        watolib.add_group(
            request.get("groupname"),
            group_type,
            self._get_group_extra_info(group_type, request),
        )

    def _edit_group(self, group_type, request):
        self._check_customer(request)
        watolib.edit_group(
            request.get("groupname"),
            group_type,
            self._get_group_extra_info(group_type, request),
        )

    # TODO: An API with a syntax depending on the edition is a very bad idea.
    # We work around this wart by making "customer" an optional key formally
    # and doing some manual a posteriori validation here.  :-P
    def _check_customer(self, request):
        if cmk.is_managed_edition():
            if "customer" not in request.keys():
                raise MKUserError(None, _("Missing required key(s): %s") % "customer")
        else:
            if "customer" in request.keys():
                raise MKUserError(None, _("Invalid key(s): %s") % "customer")

    def _get_group_extra_info(self, group_type, request):
        extra_info = {}
        extra_info["alias"] = request.get("alias")

        if group_type == "contact" and "nagvis_maps" in request:
            extra_info["nagvis_maps"] = request["nagvis_maps"]

        if cmk.is_managed_edition():
            extra_info["customer"] = request["customer"]

        return extra_info


#.
#   .--Users---------------------------------------------------------------.
#   |                       _   _                                          |
#   |                      | | | |___  ___ _ __ ___                        |
#   |                      | | | / __|/ _ \ '__/ __|                       |
#   |                      | |_| \__ \  __/ |  \__ \                       |
#   |                       \___/|___/\___|_|  |___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallUsers(APICallCollection):
    def get_api_calls(self):
        return {
            "get_all_users": {
                "handler": self._get_all_users,
                "locking": False,
            },
            "delete_users": {
                "handler": self._delete_users,
                "required_keys": ["users"],
            },
            "add_users": {
                "handler": self._add_users,
                "required_keys": ["users"],
            },
            "edit_users": {
                "handler": self._edit_users,
                "required_keys": ["users"],
            }
        }

    def _get_all_users(self, request):
        return userdb.load_users(lock=False)

    def _delete_users(self, request):
        cmk.gui.watolib.users.delete_users(request.get("users"))

    def _add_users(self, request):
        users_from_request = request.get("users")
        new_user_objects = {}
        for user_id, values in users_from_request.items():
            user_template = userdb.new_user_template("htpasswd")
            if "password" in values:
                values["password"] = hash_password(values["password"])
                values["serial"] = 1

            user_template.update(values)
            new_user_objects[user_id] = {"attributes": user_template, "is_new_user": True}
        cmk.gui.watolib.users.edit_users(new_user_objects)

    def _edit_users(self, request):
        # A dictionary with the userid as key
        # Each value is a {"set_attributes": {"alias": "test"},
        #                  "unset_attributes": ["pager", "email"]}
        user_settings = request.get("users")
        all_users = userdb.load_users()

        edit_user_objects = {}
        for user_id, settings in user_settings.items():
            if user_id not in all_users:
                raise MKUserError(None, _("Unknown user: %s") % user_id)

            if all_users[user_id].get("connector", "htpasswd") != "htpasswd":
                raise MKUserError(None, _("This user is not a htpasswd user: %s") % user_id)

            user_attrs = copy.deepcopy(all_users[user_id])
            user_attrs.update(settings.get("set_attributes", {}))
            for entry in settings.get("unset_attributes", []):
                if entry not in user_attrs:
                    continue
                del user_attrs[entry]

            new_password = settings.get("set_attributes", {}).get("password")
            if new_password:
                user_attrs["password"] = hash_password(new_password)
                user_attrs["serial"] = user_attrs.get("serial", 0) + 1

            edit_user_objects[user_id] = {"attributes": user_attrs, "is_new_user": False}

        cmk.gui.watolib.users.edit_users(edit_user_objects)


#.
#   .--Rules---------------------------------------------------------------.
#   |                       ____        _                                  |
#   |                      |  _ \ _   _| | ___  ___                        |
#   |                      | |_) | | | | |/ _ \/ __|                       |
#   |                      |  _ <| |_| | |  __/\__ \                       |
#   |                      |_| \_\\__,_|_|\___||___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallRules(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.rulesets"]  # wato.services ?
        return {
            "get_ruleset": {
                "handler": self._get,
                "required_keys": ["ruleset_name"],
                "required_permissions": required_permissions,
                "required_output_format": "python",
            },
            "set_ruleset": {
                "handler": self._set,
                "required_keys": ["ruleset_name", "ruleset"],
                "optional_keys": ["configuration_hash"],
                "required_permissions": required_permissions,
                "required_input_format": "python",
            },
            "get_rulesets_info": {
                "handler": self._get_rulesets_info,
                "required_permissions": required_permissions,
                "locking": False,
            }
        }

    def _get_ruleset_configuration(self, ruleset_name):
        collection = watolib.SingleRulesetRecursively(ruleset_name)
        collection.load()
        ruleset = collection.get(ruleset_name)

        ruleset_dict = {}
        for folder, _rule_index, rule in ruleset.get_rules():
            ruleset_dict.setdefault(folder.path(), []).append(rule.to_web_api())

        return ruleset_dict

    def _get(self, request):
        ruleset_name = request["ruleset_name"].encode("utf-8")
        ruleset_dict = self._get_ruleset_configuration(ruleset_name)
        response = {"ruleset": ruleset_dict}
        add_configuration_hash(response, ruleset_dict)
        return response

    def _set(self, request):
        # NOTE: This encoding here should be kept
        # Otherwise and unicode encoded text will be written into the
        # configuration file with unknown side effects
        ruleset_name = request["ruleset_name"].encode("utf-8")

        # Future validation, currently the rule API actions are admin only, so the check is pointless
        # may_edit_ruleset(ruleset_name)

        # Check if configuration hash has changed in the meantime
        ruleset_dict = self._get_ruleset_configuration(ruleset_name)
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], ruleset_dict)

        # Check permissions of new rules and rules we are going to delete
        new_ruleset = request["ruleset"]
        folders_set_ruleset = set(new_ruleset.keys())
        folders_obsolete_ruleset = set(ruleset_dict.keys()) - folders_set_ruleset

        for check_folders in [folders_set_ruleset, folders_obsolete_ruleset]:
            for folder_path in check_folders:
                if not watolib.Folder.folder_exists(folder_path):
                    raise MKUserError(None, _("Folder %s does not exist") % folder_path)
                rule_folder = watolib.Folder.folder(folder_path)
                rule_folder.need_permission("write")

        tag_to_group_map = ruleset_matcher.get_tag_to_group_map(config.tags)

        # Verify all rules
        rule_vs = watolib.Ruleset(ruleset_name, tag_to_group_map).rulespec.valuespec

        # Binary rulesets currently don't have a valuespec attribute set.
        if rule_vs is None:
            rule_vs = Checkbox()

        for folder_path, rules in new_ruleset.items():
            for rule in rules:
                value = rule["value"]

                try:
                    rule_vs.validate_datatype(value, "test_value")
                    rule_vs.validate_value(value, "test_value")
                except MKException as e:
                    # TODO: The abstract MKException should never be instanciated directly
                    # Change this call site and make MKException an abstract base class
                    raise MKException("ERROR: %s. Affected Rule %r" % (str(e), rule))

        # Add new rulesets
        for folder_path, rules in new_ruleset.items():
            folder = watolib.Folder.folder(folder_path)

            new_ruleset = watolib.Ruleset(ruleset_name, tag_to_group_map)
            new_ruleset.from_config(folder, rules)

            folder_rulesets = watolib.FolderRulesets(folder)
            folder_rulesets.load()
            # TODO: This add_change() call should be made by the data classes
            watolib.add_change("edit-ruleset",
                               _("Set ruleset '%s' for '%s' with %d rules") % (
                                   new_ruleset.title(),
                                   folder.title(),
                                   len(rules),
                               ),
                               sites=folder.all_site_ids())
            folder_rulesets.set(ruleset_name, new_ruleset)
            folder_rulesets.save()

        # Remove obsolete rulesets
        for folder_path in folders_obsolete_ruleset:
            folder = watolib.Folder.folder(folder_path)

            folder_rulesets = watolib.FolderRulesets(folder)
            folder_rulesets.load()
            # TODO: This add_change() call should be made by the data classes
            watolib.add_change("edit-ruleset",
                               _("Deleted ruleset '%s' for '%s'") % (
                                   watolib.Ruleset(ruleset_name, tag_to_group_map).title(),
                                   folder.title(),
                               ),
                               sites=folder.all_site_ids())

            new_ruleset = watolib.Ruleset(ruleset_name, tag_to_group_map)
            new_ruleset.from_config(folder, [])
            folder_rulesets.set(ruleset_name, new_ruleset)
            folder_rulesets.save()

    def _get_rulesets_info(self, request):
        rulesets_info = {}
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()

        for varname, ruleset in all_rulesets.get_rulesets().items():
            rulesets_info[varname] = {
                "title": ruleset.title(),
                "help": ruleset.help(),
                "number_of_rules": ruleset.num_rules(),
            }
            item_help = ruleset.item_help()
            if item_help:
                rulesets_info[varname]["item_help"] = item_help

        return rulesets_info


#.
#   .--Hosttags------------------------------------------------------------.
#   |               _   _           _   _                                  |
#   |              | | | | ___  ___| |_| |_ __ _  __ _ ___                 |
#   |              | |_| |/ _ \/ __| __| __/ _` |/ _` / __|                |
#   |              |  _  | (_) \__ \ |_| || (_| | (_| \__ \                |
#   |              |_| |_|\___/|___/\__|\__\__,_|\__, |___/                |
#   |                                            |___/                     |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallHosttags(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.hosttags"]
        return {
            "get_hosttags": {
                "handler": self._get,
                "required_permissions": required_permissions,
            },
            "set_hosttags": {
                "handler": self._set,
                "required_keys": ["tag_groups", "aux_tags"],
                "optional_keys": ["configuration_hash", "builtin"],
                "required_permissions": required_permissions,
            }
        }

    def _get(self, request):
        hosttags_config = cmk.utils.tags.TagConfig()
        hosttags_config.parse_config(TagConfigFile().load_for_reading())

        hosttags_dict = hosttags_config.get_dict_format()

        # The configuration hash is computed for the configurable hosttags
        add_configuration_hash(hosttags_dict, hosttags_dict)  # Looks strange, but is OK

        hosttags_dict["builtin"] = self._get_builtin_tags_configuration()
        return hosttags_dict

    def _get_builtin_tags_configuration(self):
        return cmk.utils.tags.BuiltinTagConfig().get_dict_format()

    def _set(self, request):
        tag_config_file = TagConfigFile()
        hosttags_config = cmk.utils.tags.TagConfig()
        hosttags_config.parse_config(tag_config_file.load_for_modification())

        hosttags_dict = hosttags_config.get_dict_format()
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], hosttags_dict)
            del request["configuration_hash"]

        # Check for conflicts with existing configuration
        # Tags may be either specified grouped in a host/folder configuration, e.g agent/cmk-agent,
        # or specified as the plain id in rules. We need to check both variants..
        used_tags = self._get_used_grouped_tags()
        used_tags.update(self._get_used_rule_tags())

        changed_hosttags_config = cmk.utils.tags.TagConfig()
        changed_hosttags_config.parse_config(request)
        changed_hosttags_config.validate_config()

        new_tags = changed_hosttags_config.get_tag_ids()
        new_tags.update(changed_hosttags_config.get_tag_ids_with_group_prefix())

        # Remove the builtin hoststags from the list of used_tags
        builtin_config = cmk.utils.tags.BuiltinTagConfig()
        used_tags.discard(builtin_config.get_tag_ids_with_group_prefix())

        missing_tags = used_tags - new_tags
        if missing_tags:
            raise MKUserError(
                None,
                _("Unable to apply new hosttag configuration. The following tags "
                  "are still in use, but not mentioned in the updated "
                  "configuration: %s") % ", ".join(missing_tags))

        tag_config_file.save(changed_hosttags_config.get_dict_format())
        watolib.add_change("edit-hosttags", _("Updated host tags through Web-API"))

    def _get_used_grouped_tags(self):
        used_tags = set([])

        # This requires a lot of computation power..
        for folder in watolib.Folder.all_folders().values():
            for attr_name, value in folder.attributes().items():
                if attr_name.startswith("tag_"):
                    used_tags.add("%s/%s" % (attr_name[4:], value))

        for host in watolib.Host.all().values():
            # NOTE: Do not use tags() function
            for attr_name, value in host.attributes().items():
                if attr_name.startswith("tag_"):
                    used_tags.add("%s/%s" % (attr_name[4:], value))
        return used_tags

    def _get_used_rule_tags(self):
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()
        used_tags = set()
        for ruleset in all_rulesets.get_rulesets().itervalues():
            for _folder, _rulenr, rule in ruleset.get_rules():
                for tag_spec in rule.tag_specs:
                    used_tags.add(tag_spec.lstrip("!"))

        used_tags.discard(None)
        return used_tags


#.
#   .--Sites---------------------------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallSites(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["wato.sites"]
        return {
            "get_site": {
                "handler": self._get,
                "required_keys": ["site_id"],
                "required_permissions": required_permissions,
                "required_output_format": "python",
                "locking": False,
            },
            "get_all_sites": {
                "handler": self._get_all,
                "required_permissions": required_permissions,
                "required_output_format": "python",
                "locking": False,
            },
            "set_site": {
                "handler": self._set,
                "required_keys": ["site_config", "site_id"],
                "optional_keys": ["configuration_hash"],
                "required_permissions": required_permissions,
                "required_input_format": "python",
            },
            "set_all_sites": {
                "handler": self._set_all,
                "required_keys": ["sites"],
                "optional_keys": ["configuration_hash"],
                "required_permissions": required_permissions,
                "required_input_format": "python",
            },
            "delete_site": {
                "handler": self._delete,
                "required_keys": ["site_id"],
                "optional_keys": ["configuration_hash"],
                "required_permissions": required_permissions,
            },
            "login_site": {
                "handler": self._login,
                "required_keys": ["site_id", "username", "password"],
                "required_permissions": required_permissions,
            },
            "logout_site": {
                "handler": self._logout,
                "required_keys": ["site_id"],
                "required_permissions": required_permissions,
            },
        }

    def _get(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()

        all_sites = site_mgmt.load_sites()
        existing_site = all_sites.get(request["site_id"])

        if not existing_site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        sites_dict = {"site_config": existing_site, "site_id": request["site_id"]}
        sites_dict["configuration_hash"] = compute_config_hash(existing_site)
        return sites_dict

    def _get_all(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()
        all_sites = site_mgmt.load_sites()
        sites_dict = {"sites": all_sites}
        sites_dict["configuration_hash"] = compute_config_hash(all_sites)
        return sites_dict

    def _set(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()

        all_sites = site_mgmt.load_sites()
        existing_site = all_sites.get(request["site_id"])
        if existing_site and "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], existing_site)

        site_mgmt.validate_configuration(request["site_id"], request["site_config"], all_sites)

        sites = config.migrate_old_site_config({request["site_id"]: request["site_config"]})

        all_sites.update(sites)
        site_mgmt.save_sites(all_sites)

    def _set_all(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()

        all_sites = site_mgmt.load_sites()
        if "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], all_sites)

        for site_id, site_config in request["sites"].iteritems():
            site_mgmt.validate_configuration(site_id, site_config, request["sites"])

        site_mgmt.save_sites(config.migrate_old_site_config(request["sites"]))

    def _delete(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()

        all_sites = site_mgmt.load_sites()
        existing_site = all_sites.get(request["site_id"])
        if existing_site and "configuration_hash" in request:
            validate_config_hash(request["configuration_hash"], existing_site)

        site_mgmt.delete_site(request["site_id"])

    def _login(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()
        all_sites = site_mgmt.load_sites()
        site = all_sites.get(request["site_id"])
        if not site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        secret = watolib.do_site_login(request["site_id"], request["username"], request["password"])
        site["secret"] = secret
        site_mgmt.save_sites(all_sites)

    def _logout(self, request):
        site_mgmt = watolib.SiteManagementFactory().factory()
        all_sites = site_mgmt.load_sites()
        site = all_sites.get(request["site_id"])
        if not site:
            raise MKUserError(None, _("Site id not found: %s") % request["site_id"])

        if "secret" in site:
            del site["secret"]
            site_mgmt.save_sites(all_sites)


@api_call_collection_registry.register
class APICallBIAggregationState(APICallCollection):
    def get_api_calls(self):
        required_permissions = ["bi.see_all"]
        return {
            "get_bi_aggregations": {
                "handler": self._get,
                "optional_keys": ["filter"],
                "required_permissions": required_permissions,
            },
        }

    def _get(self, request):
        return bi.api_get_aggregation_state(filter_names=request.get("filter", {}).get("names"),
                                            filter_groups=request.get("filter", {}).get("groups"))


#.
#   .--Other---------------------------------------------------------------.
#   |                       ___  _   _                                     |
#   |                      / _ \| |_| |__   ___ _ __                       |
#   |                     | | | | __| '_ \ / _ \ '__|                      |
#   |                     | |_| | |_| | | |  __/ |                         |
#   |                      \___/ \__|_| |_|\___|_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@api_call_collection_registry.register
class APICallOther(APICallCollection):
    def get_api_calls(self):
        return {
            "discover_services": {
                "handler": self._discover_services,
                "required_keys": ["hostname"],
                "optional_keys": ["mode"],
                "required_permissions": ["wato.services"],
            },
            "activate_changes": {
                "handler": self._activate_changes,
                "optional_keys": ["mode", "sites", "allow_foreign_changes", "comment"],
            }
        }

    def _discover_services(self, request):
        mode = request.get("mode", "new")
        hostname = request.get("hostname")

        check_hostname(hostname, should_exist=True)

        host = watolib.Host.host(hostname)

        host_attributes = host.effective_attributes()

        if host.is_cluster():
            # This is currently the only way to get some actual discovery statitics.
            # Start a dry-run -> Get statistics
            # Do an actual discovery on the nodes -> data is written
            result = watolib.check_mk_automation(host_attributes.get("site"), "try-inventory",
                                                 ["@scan"] + [hostname])
            counts = {"new": 0, "old": 0}
            for entry in result["check_table"]:
                if entry[0] in counts:
                    counts[entry[0]] += 1

            counts = {
                hostname: (
                    counts["new"],
                    0,  # this info is not available for clusters
                    counts["old"],
                    counts["new"] + counts["old"])
            }

            # A cluster cannot fail, just the nodes. This information is currently discarded
            failed_hosts = None
            watolib.check_mk_automation(host_attributes.get("site"), "inventory",
                                        ["@scan", mode] + host.cluster_nodes())
        else:
            counts, failed_hosts = watolib.check_mk_automation(host_attributes.get("site"),
                                                               "inventory",
                                                               ["@scan", mode] + [hostname])

        if failed_hosts:
            if not host.discovery_failed():
                host.set_discovery_failed()
            raise MKUserError(
                None,
                _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

        if host.discovery_failed():
            host.clear_discovery_failed()

        if mode == "refresh":
            message = _("Refreshed check configuration of host [%s] with %d services") % (
                hostname, counts[hostname][3])
            watolib.add_service_change(host, "refresh-autochecks", message)
        else:
            message = _("Saved check configuration of host [%s] with %d services") % (
                hostname, counts[hostname][3])
            watolib.add_service_change(host, "set-autochecks", message)

        msg = _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d"
               ) % tuple(counts[hostname])
        return msg

    def _activate_changes(self, request):
        mode = request.get("mode", "dirty")
        if request.get("allow_foreign_changes"):
            allow_foreign_changes = bool(int(request.get("allow_foreign_changes")))
        else:
            allow_foreign_changes = False

        sites = request.get("sites")

        changes = watolib.ActivateChanges()
        changes.load()

        if changes.has_foreign_changes():
            if not config.user.may("wato.activateforeign"):
                raise MKAuthException(_("You are not allowed to activate changes of other users."))
            if not allow_foreign_changes:
                raise MKAuthException(_("There are changes from other users and foreign changes "\
                                        "are not allowed in this API call."))

        if mode == "specific":
            for site in sites:
                if site not in config.allsites().keys():
                    raise MKUserError(None, _("Unknown site %s") % html.attrencode(site))

        manager = watolib.ActivateChangesManager()
        manager.load()

        if not manager.has_changes():
            raise MKUserError(None, _("Currently there are no changes to activate."))

        if not sites:
            sites = manager.dirty_and_active_activation_sites()

        comment = request.get("comment", "").strip()
        if comment == "":
            comment = None

        manager.start(sites, comment=comment, activate_foreign=allow_foreign_changes)
        manager.wait_for_completion()
        return manager.get_state()
