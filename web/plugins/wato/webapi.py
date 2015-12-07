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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# This code wraps some of WATO's internal APIs into a class. This class
# is only being used by the WATO webservice (htdocs/webapi.py).


#   |                       _____ ___  ____   ___                          |
#   |                      |_   _/ _ \|  _ \ / _ \                         |
#   |                        | || | | | | | | | | |                        |
#   |                        | || |_| | |_| | |_| |                        |
#   |                        |_| \___/|____/ \___/                         |
#   |                                                                      |
#
# THIS IS CURRENTLY ALL BROKEN. NEED TO CONVERT IT TO new Folder()/Host() API

class API:
    __all_hosts            = None
    __prepared_folder_info = False

    def __init_wato_datastructures(self, force = False):
        if not self.__prepared_folder_info or force:
            init_wato_datastructures()
            self.__prepared_folder_info = True

    def __get_all_hosts(self, force = False):
        if not self.__all_hosts or force:
            self.__all_hosts = load_all_hosts()
        return self.__all_hosts

    def __validate_host_parameters(self, host_foldername, hostname, attributes, all_hosts, create_folders, validate):
        if "hostname" in validate:
            check_new_hostname(None, hostname)

        if "foldername" in validate:
            if not os.path.exists(host_foldername) and not create_folders:
                raise MKUserError(None, _("Folder does not exist and no permission to create folders"))

            if host_foldername != "":
                host_folder_tokens = host_foldername.split("/")
                for dir_token in host_folder_tokens:
                    check_wato_foldername(None, dir_token, just_name = True)

        if "host_exists" in validate:
            if hostname in all_hosts:
                raise MKUserError(None, _("Hostname %s already exists") % html.attrencode(hostname))

        if "host_missing" in validate:
            if hostname not in all_hosts:
                raise MKUserError(None, _("Hostname %s does not exist") % html.attrencode(hostname))


        # Returns the closest parent of an upcoming folder
        def get_closest_parent():
            if host_foldername in g_folders:
                return g_folders[host_foldername]

            host_folder_tokens = host_foldername.split("/")
            for i in range(len(host_folder_tokens), -1, -1):
                check_path = "/".join(host_folder_tokens[:i])
                if check_path in g_folders:
                    return g_folders[check_path]

        def check_folder_lock(check_folder):
            # Check if folder or host file is locked
            if check_folder == host_foldername: # Target folder exists
                if check_folder.get(".lock_hosts"):
                    raise MKAuthException(_("You are not allowed to modify hosts in this folder. The host configuration in the folder "
                                            "is locked, because it has been created by an external application."))
            else:
                if check_folder.get(".lock_subfolders"):
                    raise MKAuthException(_("Not allowed to create subfolders in this folder. The Folder has been "
                                            "created by an external application and is locked."))

        if "permissions_create" in validate:
            # Find the closest parent folder. If we can write there, we can also write in our new folder
            check_folder = get_closest_parent()
            check_new_host_permissions(check_folder, attributes, hostname)
            check_folder_lock(check_folder)

        if "permissions_edit" in validate:
            check_folder = all_hosts[hostname][".folder"]
            check_edit_host_permissions(check_folder, attributes, hostname)
            check_folder_lock(check_folder)

        if "permissions_read" in validate:
            check_folder = all_hosts[hostname][".folder"]
            check_host_permissions(hostname, folder = check_folder)

        if "tags" in validate:
            check_host_tags(dict((key[4:], value) for key, value in attributes.items() if key.startswith("tag_") and value != False))

        if "site" in validate:
            if attributes.get("site"):
                if attributes.get("site") not in config.allsites().keys():
                    raise MKUserError(None, _("Unknown site %s") % html.attrencode(attributes.get("site")))

        return True

    def __get_valid_api_host_attributes(self, attributes):
        result = {}

        host_attribute_names = map(lambda (x, y): x.name(), all_host_attributes()) + ["inventory_failed", ".nodes"]

        for key, value in attributes.items():
            if key in host_attribute_names:
                result[key] = value

        return result

    def lock_wato(self):
        lock_exclusive()

    def validate_host_parameters(self, host_foldername, hostname, host_attr, validate = [], create_folders = True):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        if host_foldername:
            host_foldername = host_foldername.strip("/")
        else:
            if hostname in all_hosts:
                host_foldername = all_hosts[hostname][".folder"][".path"]
        attributes = self.__get_valid_api_host_attributes(host_attr)
        self.__validate_host_parameters(host_foldername, hostname, attributes, all_hosts, create_folders, validate)

    # hosts: [ { "attributes": {attr}, "hostname": "hostA", "folder": "folder1" }, .. ]
    def add_hosts(self, hosts, create_folders = True, validate_hosts = True):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        # Sort hosts into folders
        target_folders = {}
        for host_data in hosts:
            host_foldername = host_data["folder"]
            hostname        = host_data["hostname"]
            host_attr       = host_data["attributes"]

            # Tidy up foldername
            host_foldername = host_foldername.strip("/")
            attributes      = self.__get_valid_api_host_attributes(host_attr)
            if validate_hosts:
                self.__validate_host_parameters(host_foldername, hostname, host_attr, all_hosts, create_folders,
                                            ["hostname", "foldername", "host_exists", "tags", "site", "permissions_create"])
            target_folders.setdefault(host_foldername, {})[hostname] = attributes

        for target_foldername, new_hosts in target_folders.items():
            # Create target folder(s) if required...
            self.__create_wato_folders(target_foldername)

            folder = g_folders[target_foldername]
            add_hosts_to_folder(folder, new_hosts)

        # As long as some hooks are able to invalidate the
        # entire g_folders variable we need to enforce a reload
        self.__init_wato_datastructures(force = True)
        self.__get_all_hosts(force = True)


    # hosts: [ { "attributes": {attr}, "unset_attributes": {attr}, "hostname": "hostA"}, .. ]

    # Create wato folders up to the given path if they don't exists
    def __create_wato_folders(path):
        path_tokens = path.split("/")
        current_folder = g_root_folder
        for i in range(0, len(path_tokens)):
            check_path = "/".join(path_tokens[:i+1])
            if check_path in g_folders:
                current_folder = g_folders[check_path]
            else:
                check_folder_permissions(current_folder, "write")
                current_folder = create_wato_folder(current_folder, path_tokens[i], path_tokens[i])


    def edit_hosts(self, hosts, validate_hosts = True):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        target_folders = {}
        for host_data in hosts:
            hostname        = host_data["hostname"]
            host_attr       = host_data.get("attributes", {})
            host_unset_attr = host_data.get("unset_attributes", [])

            attributes = self.__get_valid_api_host_attributes(host_attr)
            if validate_hosts:
                self.__validate_host_parameters(None, hostname, attributes, all_hosts, True,
                                           ["host_missing", "tags", "site", "permissions_edit"])
            host_foldername = all_hosts[hostname][".folder"][".path"]
            new_attr = dict([(k, v) for (k, v) in all_hosts[hostname].iteritems() \
                                    if (not k.startswith('.'))])
            new_attr.update(attributes)

            target_folders.setdefault(host_foldername, {})[hostname] = {"set":   new_attr,
                                                                        "unset": host_unset_attr}

        for target_foldername, update_hosts in target_folders.items():
            update_hosts_in_folder(g_folders[target_foldername], update_hosts)

        # As long as some hooks are able to invalidate the
        # entire g_folders variable we need to enforce a reload
        self.__init_wato_datastructures(force = True)
        self.__get_all_hosts(force = True)
#
#        for host_foldername, update_hosts in target_folders.items():
#            for hostname in update_hosts.keys():
#                all_hosts[hostname] = g_folders[host_foldername][".hosts"][hostname]


    def get_host(self, hostname, effective_attr = False):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing", "permissions_read"])

        the_host = all_hosts[hostname]
        if effective_attr:
            the_host = effective_attributes(the_host, the_host[".folder"])

        cleaned_host = dict([(k, v) for (k, v) in the_host.iteritems() if not k.startswith('.') ])

        return { "attributes": cleaned_host, "path": the_host[".folder"][".path"], "hostname": hostname }

    # hosts: [ "hostA", "hostB", "hostC" ]
    def delete_hosts(self, hosts, validate_hosts = True):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        target_folders = {}
        for hostname in hosts:
            if validate_hosts:
                self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing", "permissions_edit"])

            host_foldername = all_hosts[hostname][".folder"][".path"]
            target_folders.setdefault(host_foldername, [])
            target_folders[host_foldername].append(hostname)

        for target_foldername, hosts in target_folders.items():
            folder = g_folders[target_foldername]
            delete_hosts_in_folder(folder, hosts)

        # As long as some hooks are able to invalidate the
        # entire g_folders variable we need to enforce a reload
        self.__init_wato_datastructures(force = True)
        self.__get_all_hosts(force = True)

    def discover_services(self, hostname, mode = "new"):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()

        host   = all_hosts[hostname]
        folder = host[".folder"]

        config.need_permission("wato.services")
        self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing"])
        check_host_permissions(hostname, folder=folder)

        ### Start inventory
        counts, failed_hosts = check_mk_automation(host[".siteid"], "inventory", [ "@scan", mode ] + [hostname])
        if failed_hosts:
            if not host.get("inventory_failed") and not folder.get(".lock_hosts"):
                host["inventory_failed"] = True
                save_hosts(folder)
            raise MKUserError(None, _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

        if host.get("inventory_failed") and not folder.get(".lock_hosts"):
            del host["inventory_failed"]
            save_hosts(folder)

        msg = _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d") % \
                                                                        tuple(counts[hostname])

        mark_affected_sites_dirty(folder, hostname, sync=False, restart=True)
        log_pending(AFFECTED, hostname, "api-inventory", msg)

        return msg

    def activate_changes(self, sites, mode = "dirty", allow_foreign_changes = False):
        self.__init_wato_datastructures()

        config.need_permission("wato.activate")

        if foreign_changes():
            if not config.may("wato.activateforeign"):
                raise MKAuthException(_("You are not allowed to activate changes of other users."))
            if not allow_foreign_changes:
                raise MKAuthException(_("There are changes from other users and foreign changes "\
                                        "are not allowed in this API call."))

        if mode == "specific":
            for site in sites:
                if site not in config.allsites().keys():
                    raise MKUserError(None, _("Unknown site %s") % html.attrencode(site))



        ### Start activate changes
        repstatus = load_replication_status()
        errors = []
        if is_distributed():
            for site in config.allsites().values():
                if mode == "all" or (mode == "dirty" and repstatus.get(site["id"],{}).get("need_restart")) or\
                   (sites and site["id"] in sites):
                    try:
                        synchronize_site(site, True)
                    except Exception, e:
                        errors.append("%s: %s" % (site["id"], e))

                    if not config.site_is_local(site["id"]):
                        remove_sync_snapshot(site["id"])
        else: # Single site
            if mode == "all" or (mode == "dirty" and log_exists("pending")):
                try:
                    activate_changes()
                except Exception, e:
                    errors.append("Exception: %s" % e)

        if not errors:
            log_commit_pending()
        else:
            raise MKUserError(None, ", ".join(errors))

    def get_all_hosts(self, effective_attr = False):
        self.__init_wato_datastructures()
        all_hosts = self.__get_all_hosts()
        return_hosts = {}

        for hostname in all_hosts.keys():
            self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing", "permissions_read"])

            the_host = all_hosts[hostname]
            if effective_attr:
                the_host = effective_attributes(the_host, the_host[".folder"])
            cleaned_host = dict([(k, v) for (k, v) in the_host.iteritems() if not k.startswith('.') ])

            return_hosts[hostname] = { "attributes": cleaned_host, "path": the_host[".folder"][".path"], "hostname": hostname }

        return return_hosts


# TODO: These functions do not work anymore. use new Folder() class API

# new_hosts: {"hostA": {attr}, "hostB": {attr}}
def add_hosts_to_folder(folder, new_hosts):
    load_hosts(folder)
    folder[".hosts"].update(new_hosts)
    folder["num_hosts"] = len(folder[".hosts"])

    for hostname in new_hosts.keys():
        log_pending(AFFECTED, hostname, "create-host",_("Created new host %s.") % hostname)

    save_folder_and_hosts(folder)

    reload_hosts(folder)
    mark_affected_sites_dirty(folder, hostname)
    call_hook_hosts_changed(folder)


# hosts: {"hostname": {"set": {attr}, "unset": [attr]}}
def update_hosts_in_folder(folder, hosts):
    updated_hosts = {}

    for hostname, attributes in hosts.items():
        cleaned_attr = dict([
            (k, v) for
            (k, v) in
            attributes.get("set", {}).iteritems()
            if (not k.startswith('.') or k == ".nodes") ])
        # unset keys
        for key in attributes.get("unset", []):
            if key in cleaned_attr:
                del cleaned_attr[key]

        updated_hosts[hostname] = cleaned_attr

        # The site attribute might change. In that case also
        # the old site of the host must be marked dirty.
        mark_affected_sites_dirty(folder, hostname)

    load_hosts(folder)
    folder[".hosts"].update(updated_hosts)

    for hostname in updated_hosts.keys():
        mark_affected_sites_dirty(folder, hostname)
        log_pending(AFFECTED, hostname, "edit-host", _("edited properties of host [%s]") % hostname)

    save_folder_and_hosts(folder)
    reload_hosts(folder)
    call_hook_hosts_changed(folder)


# hosts: ["hostA", "hostB", "hostC"]
def delete_hosts_in_folder(folder, hosts):
    if folder.get(".lock_hosts"):
        raise MKUserError(None, _("Cannot delete host. Hosts in this folder are locked"))

    for hostname in hosts:
        del folder[".hosts"][hostname]
        folder["num_hosts"] -= 1
        mark_affected_sites_dirty(folder, hostname)
        log_pending(AFFECTED, hostname, "delete-host", _("Deleted host %s") % hostname)

    save_folder_and_hosts(folder)
    call_hook_hosts_changed(folder)


# Checks if the given host_tags are all in known host tag groups and have a valid value
def check_host_tags(host_tags):
    for key, value in host_tags.items():
        for group_entry in configured_host_tags():
            if group_entry[0] == key:
                for value_entry in group_entry[2]:
                    if value_entry[0] == value:
                        break
                else:
                    raise MKUserError(None, _("Unknown host tag %s") % html.attrencode(value))
                break
        else:
            raise MKUserError(None, _("Unknown host tag group %s") % html.attrencode(key))


def check_edit_host_permissions(folder, host, hostname):
    config.need_permission("wato.edit_hosts")

    # Check which attributes have changed. For a change in the contact groups
    # we need permissions on the folder. For a change in the rest we need
    # permissions on the host
    old_host = dict(folder[".hosts"][hostname].items())
    del old_host[".tags"] # not contained in new host
    cgs_changed = get_folder_cgconf_from_attributes(host) != \
                  get_folder_cgconf_from_attributes(old_host)
    other_changed = old_host != host and not cgs_changed
    if other_changed:
        check_host_permissions(hostname, folder = folder)
    if cgs_changed \
         and True != check_folder_permissions(folder, "write", False):
         raise MKAuthException(_("Sorry. In order to change the permissions of a host you need write "
                                 "access to the folder it is contained in."))
    if cgs_changed:
        check_user_contactgroups(host.get("contactgroups", (False, [])))


# Creates and returns an empty wato folder with the given title
# Write permissions are NOT checked!
# TODO: This is totally broken and needs to be removed by Folder()...create_subfolder()
def create_wato_folder(parent, name, title, attributes={}):
    # CLEANUP: Replaced by Folder.create_subfolder()
    if parent and parent[".path"]:
        newpath = parent[".path"] + "/" + name
    else:
        newpath = name

    new_folder = {
        ".name"      : name,
        ".path"      : newpath,
        "title"      : title or name,
        "attributes" : attributes,
        ".folders"   : {},
        ".hosts"     : {},
        "num_hosts"  : 0,
        ".lock"      : False,
        ".parent"    : parent,
    }

    save_folder(new_folder)
    new_folder = reload_folder(new_folder)

    call_hook_folder_created(new_folder)

    # Note: sites are not marked as dirty.
    # The creation of a folder without hosts has not effect on the
    # monitoring.
    log_pending(AFFECTED, new_folder, "new-folder", _("Created new folder %s") % title)

    return new_folder


