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

#   +----------------------------------------------------------------------+
#   |               ____                _                                  |
#   |              |  _ \ ___  __ _  __| |  _ __ ___   ___                 |
#   |              | |_) / _ \/ _` |/ _` | | '_ ` _ \ / _ \                |
#   |              |  _ <  __/ (_| | (_| | | | | | | |  __/                |
#   |              |_| \_\___|\__,_|\__,_| |_| |_| |_|\___|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A few words about the implementation details of WATO.                |
#   +----------------------------------------------------------------------+

# [1] Files and Folders
# WATO organizes hosts in folders. A wato folder is represented by a 
# OS directory. If the folder contains host definitions, then in that
# directory a file name "hosts.mk" is kept.
# The directory hierarchy of WATO is rooted at etc/check_mk/conf.d/wato.
# All files in and below that directory are kept by WATO. WATO does not
# touch any other files or directories in conf.d.
# A *path* in WATO means a relative folder path to that directory. The
# root folder has the empty path (""). Folders are separated by slashes.
# Each directory contains a file ".wato" which keeps information needed
# by WATO but not by Check_MK itself.

# [2] Global variables
# Yes. Global variables are bad. But we use them anyway. Please go away
# if you do not like this. Global variables - if properly used - can make
# implementation a lot easier and clearer. Of course we could pack everything
# into a class and use class variables. But what's the difference?
#
# g_folders -> A dictionary of all folders, the key are there paths,
#              the values are dictionaries. Keys beginning
#              with a period are not persisted. Important keys are:
#
#   ".folders"        -> List of subfolders. This key is present even for leaf folders.
#   ".parent"         -> parent folder (not name, but Python reference!). Missing for the root folder
#   ".name"           -> OS name of the folder
#   ".path"           -> absolute path of folder
#   ".hosts"          -> Hosts in that folder. This key is present even if there are no hosts.
#                        If the hosts in the folder have not been loaded yet, then the key 
#                        is missing.
#   "title"           -> Title/alias of that folder
#   "attributes"      -> Attributes to be inherited to subfolders and hosts
#   "num_hosts"       -> number of hosts in this folder (this is identical to 
#                        to len() of the entry ".hosts" but is persisted for
#                        performance issues.
#   ".total_hosts"    -> recursive number of hosts, computed on demand by
#                        num_hosts_in()
#                        
# 
# g_folder -> The folder object representing the folder the user is 
#             currently operating in. 
#
# g_root_folder -> The folder object representing the root folder
#
# At the beginning of each page, those three global variables are
# set. All folders are loaded, but only their meta-data, not the
# actual Check_MK files (hosts.mk). WATO is designed for managing
# 100.000 hosts. So operations on all hosts might last a while...
#
# g_hook -> dictionary of hooks (i.e. user supplied functions) to
#           be called in various situations.
#
# g_configvars -> dictionary of variables in main.mk that can be configured 
#           via WATO.
#
# g_html_head_open -> True, if the HTML head has already been rendered.


#   +----------------------------------------------------------------------+
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Importing, Permissions, global variables                             |
#   +----------------------------------------------------------------------+

import sys, pprint, socket, re, subprocess, time, datetime, shutil, tarfile, StringIO, math
import config, htmllib
from lib import *

# Declare WATO-specific permissions
config.declare_permission_section("wato", _("WATO - Check_MK's Web Administration Tool"))

config.declare_permission("wato.use",
     _("Use WATO"),
     _("This permissions allows users to use WATO - Check_MK's "
       "Web Administration Tool. Without this "
       "permission all references to WATO (buttons, links,"
       "snapins) will be unvisible."),
     [ "admin", "user" ])

config.declare_permission("wato.edit",
     _("Make changes, perform actions"),
     _("This permission is needed in order to make any "
       "changes or perform any actions at all. "
       "Without this permission, the user is only "
       "able to view data, and that only in modules he "
       "has explicit permissions for."),
     [ "admin", "user" ])

config.declare_permission("wato.seeall",
     _("Read access to all modules"),
     _("When this permission is set then the user sees "
       "also such modules he has no explicit "
       "access to (see below)."),
     [ "admin", ])

config.declare_permission("wato.activate",
     _("Activate Configuration"),
     _("This permission is needed for activating the "
       "current configuration (and thus rewriting the "
       "monitoring configuration and restart the monitoring daemon.)"),
     [ "admin", "user", ])

config.declare_permission("wato.auditlog",
     _("Audit log"),
     _("Access to the historic audit log. A user with write "
       "access can delete the audit log. "
       "The currently pending changes can be seen by all users "
       "with access to WATO."),
     [ "admin", ])

config.declare_permission("wato.hosts",
     _("Host management"),
     _("Access to the management of hosts and folders. This "
       "module has some additional permissions (see below)."),
     [ "admin", "user" ])

config.declare_permission("wato.edit_hosts",
     _("Modify existing hosts"),
     _("Modify the properties of existing hosts. Please note: "
       "for the management of services (inventory) there is "
       "a separate permission (see below)"),
     [ "admin", "user" ])

config.declare_permission("wato.manage_hosts",
     _("Add & remove hosts"),
     _("Add hosts to the monitoring and remove hosts "
       "from the monitoring. Please also add the permissions "
       "<i>Modify existing hosts</i>."),
     [ "admin", "user" ])

config.declare_permission("wato.services",
     _("Manage services"),
     _("Do inventory and service configuration on existing hosts."),
     [ "admin", "user" ])

config.declare_permission("wato.edit_folders",
     _("Modify existing folders"),
     _("Modify the properties of existing folders."),
     [ "admin", "user" ])

config.declare_permission("wato.manage_folders", 
     _("Add & remove folders"),
     _("Add new folders and delete existing folders. If a folder to be deleted contains hosts then "
       "the permission to delete hosts is also required."),
     [ "admin", "user" ])

config.declare_permission("wato.see_all_folders",
     _("Read access to all hosts and folders"),
     _("Users without this permissions can only see folders with a contact group they are in. "),
     [ "admin" ])

config.declare_permission("wato.all_folders",
     _("Write access to all hosts and folders"),
     _("Without this permission, operations on folders can only be done by users that are members of "
       "one of the folders contact groups. This permission grants full access to all folders and hosts. "),
     [ "admin" ])

config.declare_permission("wato.hosttags",
     _("Manage host tags"),
     _("Create, remove and edit host tags. Removing host tags also might remove rules, "
       "so this permission should not be available to normal users. "),
     [ "admin" ])

config.declare_permission("wato.global",
     _("Global settings"),
     _("Access to the module <i>Global settings</i>"),
     [ "admin", ])

config.declare_permission("wato.rulesets",
     _("Rulesets"),
     _("Access to the module for managing Check_MK rules. Please note that a user can only "
       "manage rules in folders he has permissions to. "),
     [ "admin", "user" ])

config.declare_permission("wato.groups",
     _("Host & Service Groups"),
     _("Access to the modules for managing host and service groups."),
     [ "admin", ])

config.declare_permission("wato.timeperiods",
     _("Timeperiods"),
     _("Access to the module <i>Timeperiods</i>"),
     [ "admin", ])

config.declare_permission("wato.sites",
     _("Site management"),
     _("Access to the module for managing connections to remote monitoring sites."),
     [ "admin", ])

config.declare_permission("wato.users",
     _("User management"),
     _("This permission is needed for the modules <b>Users & Contacts</b>, <b>Roles</b> and <b>Contact Groups</b>"),
     [ "admin", ])

config.declare_permission("wato.snapshots",
     _("Backup & Restore"),
     _("Access to the module <i>Backup & Restore</i>. Please note: a user with write access to this module "
       "can make arbitrary changes to the configuration by restoring uploaded snapshots!"),
     [ "admin",  ])


root_dir      = defaults.check_mk_configdir + "/wato/"
multisite_dir = defaults.default_config_dir + "/multisite.d/wato/"
var_dir       = defaults.var_dir + "/wato/"
log_dir       = var_dir + "log/"
snapshot_dir  = var_dir + "/snapshots/"

ALL_HOSTS    = [ '@all' ]
ALL_SERVICES = [ "" ]
NEGATE       = '@negate'

g_folder = None
g_root_folder = None
g_folders = {}
g_html_head_open = False


#   +----------------------------------------------------------------------+
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Der Seitenaufbau besteht aus folgenden Teilen:                       |
#   | 1. Kontextbuttons: wo kann man von hier aus hinspringen, ohne Aktion |
#   | 2. Verarbeiten einer Aktion, falls eine gültige Transaktion da ist   |
#   | 3. Anzeigen von Inhalten                                             |
#   |                                                                      |
#   | Der Trick: welche Inhalte angezeigt werden, hängt vom Ausgang der    |
#   | Aktion ab. Wenn man z.B. bei einem Host bei "Create new host" auf    |
#   | [Save] klickt, dann kommt bei Erfolg die Inventurseite, bei Miss-    |
#   | bleibt man auf der Neuanlegen-Seite                                  |
#   |                                                                      | 
#   | Dummerweise kann ich aber die Kontextbuttons erst dann anzeigen,     |
#   | wenn ich den Ausgang der Aktion kenne. Daher wird zuerst die Aktion  |
#   | ausgeführt, welche aber keinen HTML-Code ausgeben darf.              |
#   +----------------------------------------------------------------------+

def page_handler():
    global g_html_head_open
    g_html_head_open = False

    if not config.wato_enabled:
        raise MKGeneralException(_("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
                                   " in your <tt>multisite.mk</tt> if you want to use WATO."))
    if not config.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    # Make information about current folder and hosts avaiable
    prepare_folder_info()

    current_mode = html.var("mode") or "main"
    modeperms, modefunc = modes.get(current_mode, ([], None))
    if modefunc == None:
        html.header(_("Sorry"))
        html.begin_context_buttons()
        html.context_button(_("Home"), make_link([("mode", "main")]), "home")
        html.end_context_buttons()
        html.message(_("This module has not yet been implemented."))
        html.footer()
        return

    # Check general permission for this mode
    if not config.may("wato.seeall"):
        for pname in modeperms:
            config.need_permission("wato." + pname)

    # Do actions (might switch mode)
    action_message = None
    if html.has_var("_transid"):
        try:
            config.need_permission("wato.edit")

            # Even if the user has seen this mode because auf "seeall", 
            # he needs an explicit access permission for doing changes:
            if config.may("wato.seeall"):
                for pname in modeperms:
                    config.need_permission("wato." + pname)

            result = modefunc("action")
            if type(result) == tuple:
                newmode, action_message = result
            else:
                newmode = result

            # If newmode is False, then we shall immediately abort.
            # This is e.g. the case, if the page outputted non-HTML
            # data, such as a tarball (in the export function). We must
            # be sure not to output *any* further data in that case.
            if newmode == False:
                return

            # if newmode is not None, then the mode has been changed
            elif newmode != None:
                if newmode == "": # no further information: configuration dialog, etc.
                    if action_message:
                        html.message(action_message)
                    if g_html_head_open:
                        html.write("</div>")
                        html.footer()
                    return
                modeperms, modefunc = modes.get(newmode)
                current_mode = newmode
                html.set_var("mode", newmode) # will be used by makeuri

                # Check general permissions for the new mode
                if not config.may("wato.seeall"):
                    for pname in modeperms:
                        config.need_permission("wato." + pname)

        except MKUserError, e:
            action_message = e.message
            html.add_user_error(e.varname, e.message)

        except MKAuthException, e:
            action_message = e.reason
            html.add_user_error(None, e.reason)

    # Title
    html.header(modefunc("title"))
    html.write("<script type='text/javascript' src='js/wato.js'></script>")
    html.write("<div class=wato>\n")

    try:
        # Show contexts buttons
        html.begin_context_buttons()
        modefunc("buttons")
        for inmode, buttontext, target in extra_buttons:
            if inmode == current_mode:
                if hasattr(target, '__call__'):
                    target = target()
                    if not target:
                        continue
                if '/' == target[0] or target.startswith('../') or '://' in target:
                    html.context_button(buttontext, target)
                else:
                    html.context_button(buttontext, make_link([("mode", target)]))
        html.end_context_buttons()
        html.write("<br>")

        # Show outcome of action
        if html.has_users_errors():
            html.show_error(action_message)
        elif action_message:
            html.message(action_message)

        # Show content
        modefunc("content")

    except MKGeneralException:
        raise

    except MKInternalError:
        raise

    except MKAuthException:
        raise

    except Exception, e:
        import traceback
        html.show_error(traceback.format_exc().replace('\n', '<br />'))

    html.write("</div>\n")
    if g_need_sidebar_reload == id(html):
        html.reload_sidebar()

    html.footer()


def set_current_folder(folder = None):
    global g_folder
    
    if folder:
        g_folder = folder
    else:
        if html.has_var("folder"):
            path = html.var("folder")
            g_folder = g_folders.get(path)
        else:
            host = html.var("host")
            if host: # find host with full scan. Expensive operation
                g_folder = find_host(host)
                if not g_folder:
                    raise MKGeneralException(_("The host <b>%s</b> is not managed by WATO.") % host)
            else: # fall back to root folder
                g_folder = g_root_folder

        if not g_folder:
            raise MKGeneralException(_('You called this page with a non-existing folder! '
                                     'Go back to the <a href="wato.py">main index</a>.'))
    html.set_var("folder", g_folder['.path']) # in case of implizit folder selection
    load_hosts(g_folder)          # load information about hosts

g_need_sidebar_reload = None
def need_sidebar_reload():
    global g_need_sidebar_reload
    g_need_sidebar_reload = id(html)

#   +----------------------------------------------------------------------+
#   |          _                    _    ______                            |
#   |         | |    ___   __ _  __| |  / / ___|  __ ___   _____           |
#   |         | |   / _ \ / _` |/ _` | / /\___ \ / _` \ \ / / _ \          |
#   |         | |__| (_) | (_| | (_| |/ /  ___) | (_| |\ V /  __/          |
#   |         |_____\___/ \__,_|\__,_/_/  |____/ \__,_| \_/ \___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Helper functions for loading and saving folder and hosts data.       |
#   | Hosts are loaded separately from the folders. This is for perfor-    |
#   | mance reasons. In most cases information about the hosts is needed   |
#   | only for the current folder. Keep in mind: WATO is designed for      |
#   | handling 100k hosts.                                                 |
#   +----------------------------------------------------------------------+

def folder_dir(the_folder):
    return root_dir + the_folder[".path"]

# Save one folder (i.e. make sure the directory exist and write its .wato file)
def save_folder(folder):
    # Remove temporary entries from the dictionary
    cleaned = dict([(k, v) for (k, v) in folder.iteritems() if not k.startswith('.') ])

    # Create the directory with the correct permissions (in case it doesn't exist)
    dir = folder_dir(folder)
    make_nagios_directory(dir)

    wato_filename = dir + "/.wato"
    config.write_settings_file(wato_filename, cleaned)

def save_folder_and_hosts(folder):
    save_folder(folder)
    save_hosts(folder)


# Save a folder and all of its subfolders (recursively)
def save_folders(folder):
    save_folder(folder)
    for subfolder in folder[".folders"].values():
        save_folders(subfolder)


def save_all_folders():
    save_folders(g_root_folder)

# Load the meta-data of a folder (it's .wato file), register
# it in g_folders, load recursively all subfolders and then
# return the folder object. The case the .wato file is missing 
# it will be assume to contain default values.
def load_folder(dir, name="", path=""):
    fn = dir + "/.wato"
    try:
        folder = eval(file(fn).read())
    except:
        # .wato missing or invalid
        folder = { 
            "title"      : name and name or _("Main directory"),
            "num_hosts"  : 0,
        }

    folder[".name"]    = name
    folder[".path"]    = path
    folder[".folders"] = {}

    if "attributes" not in folder: # Make sure, attributes are always present
        folder["attributes"] = {}

    # Now look subdirectories
    for entry in os.listdir(dir):
        if entry[0] == '.': # entries '.' and '..'
            continue

        p = dir + "/" + entry

        if os.path.isdir(p):
            if path == "":
                subpath = entry
            else:
                subpath = path + "/" + entry
            f = load_folder(p, entry, subpath)
            f[".parent"] = folder
            folder[".folders"][entry] = f
    
    g_folders[path] = folder
    return folder

# Load the information about all folders - except the hosts
def load_all_folders():
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    global g_root_folder, g_folders
    g_folders = {}
    g_root_folder = load_folder(root_dir)


# Load all hosts from all configuration files.
def load_all_hosts(base_folder = None):
    if base_folder == None:
        base_folder = g_root_folder
    hosts = {}
    for f in base_folder[".folders"].values():
        hosts.update(load_all_hosts(f))
    hosts.update(load_hosts(base_folder))
    return hosts

def load_hosts(folder = None):
    if folder == None:
        folder = g_folder
    folder[".hosts"] = load_hosts_file(folder)
    folder["num_hosts"] = len(folder[".hosts"])
    return folder[".hosts"]


def load_hosts_file(folder):
    hosts = {}

    filename = root_dir + folder[".path"] + "/hosts.mk"
    if os.path.exists(filename):
        variables = {
            "FOLDER_PATH"         : "",
            "ALL_HOSTS"           : ALL_HOSTS,
            "all_hosts"           : [],
            "ipaddresses"         : {},
            "extra_host_conf"     : { "alias" : [] },
            "extra_service_conf"  : { "_WATO" : [] },
            "host_attributes"     : {},
            "host_contactgroups"  : [],
        }
        execfile(filename, variables, variables)
        for h in variables["all_hosts"]:

            parts = h.split('|')
            hostname = parts[0]

            # Get generic attributes of that host
            host = variables["host_attributes"].get(hostname)
            if host == None: # Legacy file: reconstruct values
                host = {}
                # Some of the attributes are handled with special care. We do not 
                # want them to be redundant in the configuration file. We 
                # want to stay compatible with check_mk.
                ipaddress = variables["ipaddresses"].get(hostname)
                aliases = host_extra_conf(hostname, variables["extra_host_conf"]["alias"]) 
                if len(aliases) > 0:
                    alias = aliases[0]
                else:
                    alias = None
                host["alias"]     = alias 
                host["ipaddress"] = ipaddress

                # Retrieve setting for each individual host tag
                tags = set([ tag for tag in parts[1:] if tag != 'wato' and not tag.endswith('.mk') ])
                for attr, topic in host_attributes:
                    if isinstance(attr, HostTagAttribute):
                        tagvalue = attr.get_tag_value(tags)
                        host[attr.name()] = tagvalue

            # access to "raw" tags, needed for rule engine, remove implicit tags
            host[".tags"] = [ p for p in parts[1:] if p not in [ "wato", "//" ] ]

            # access to name of host, if key is not present
            host[".name"] = hostname

            # access to the folder object
            host['.folder'] = folder

            hosts[hostname] = host


    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))
    return hosts

def save_hosts(folder = None):
    if folder == None:
        folder = g_folder
    folder_path = folder[".path"]
    dirname = root_dir + folder_path
    filename = dirname + "/hosts.mk"
    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    out = file(filename, "w")

    hosts = folder.get(".hosts", [])
    if len(hosts) == 0:
        if os.path.exists(filename):
            os.remove(filename)
        return


    all_hosts = [] # pair-list of (hostname, tags)
    ipaddresses = {}
    hostnames = hosts.keys()
    hostnames.sort()
    custom_macros = {} # collect value for attributes that are to be present in Nagios
    cleaned_hosts = {}
    for hostname in hostnames:
        # Remove temporary entries from the dictionary
        cleaned_hosts[hostname] = dict([(k, v) for (k, v) in hosts[hostname].iteritems() if not k.startswith('.') ])

        host = cleaned_hosts[hostname]
        effective = effective_attributes(host, folder)
        ipaddress = effective.get("ipaddress")

        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag.
        tags = set([])
        for attr, topic in host_attributes:
            if isinstance(attr, HostTagAttribute):
                value = effective.get(attr.name())
                tags.update(attr.get_tag_list(value))

        all_hosts.append((hostname, list(tags)))
        if ipaddress:
            ipaddresses[hostname] = ipaddress


        # Create contact group rule entries for hosts with explicitely set values
        # Note: since the type if this entry is a list, not a single contact group, all other list
        # entries coming after this one will be ignored. That way the host-entries have
        # precedence over the folder entries.

        if "contactgroups" in host:
            use, cgs = host["contactgroups"]
            if use and cgs:
                out.write("\nhost_contactgroups.append(( %r, [%r] ))\n" % (cgs, hostname))

        for attr, topic in host_attributes:
            attrname = attr.name()
            if attrname in effective:
                nag_varname = attr.nagios_name()
                if nag_varname:
                    value = effective.get(attrname)
                    nagstring = attr.to_nagios(value)
                    if nagstring != None:
                        if nag_varname not in custom_macros:
                            custom_macros[nag_varname] = {}
                        custom_macros[nag_varname][hostname] = nagstring

    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    if len(all_hosts) > 0:
        out.write("all_hosts += [\n")
        for hostname, taglist in all_hosts:
            tagstext = "|".join(taglist)
            if tagstext:
                tagstext += "|"
            out.write('  "%s|%swato|/" + FOLDER_PATH + "/",\n' % (hostname, tagstext))
        out.write("]\n")
        if len(ipaddresses) > 0:
            out.write("\n# Explicit IP addresses\n")
            out.write("ipaddresses.update(")
            out.write(pprint.pformat(ipaddresses))
            out.write(")")
        out.write("\n")

    for nag_varname, entries in custom_macros.items():
        macrolist = []
        for hostname, nagstring in entries.items():
            macrolist.append((nagstring, [hostname]))
        if len(macrolist) > 0:
            out.write("\n# Settings for %s\n" % nag_varname)
            out.write("extra_host_conf.setdefault(%r, []).extend(\n" % nag_varname)
            out.write("  %s)\n" % pprint.pformat(macrolist))
    
    # If the contact groups of the host are set to be used for the monitoring,
    # we create an according rule for the folder and an according rule for
    # each host that has an explicit setting for that attribute.
    use, cgs = effective.get("contactgroups", (False, [])) 
    if use and cgs: 
        out.write("\nhost_contactgroups.append(\n"
                  "  ( %r, [ '/' + FOLDER_PATH + '/' ], ALL_HOSTS ))\n" % cgs)


    # Write information about all host attributes into special variable - even
    # values stored for check_mk as well.
    out.write("\n# Host attributes (needed for WATO)\n")
    out.write("host_attributes.update(\n%s)\n" % pprint.pformat(cleaned_hosts))


def delete_configuration_file(folder, thefile):
    path = folder_dir(folder, thefile)
    if os.path.exists(path):
        os.remove(path) # remove the actual configuration file
    if os.path.exists(path + ".wato"):
        os.remove(path + ".wato") # remove the .wato file


# If folder attributes change, configuration files below
# need to be re-written, as they contain the gross product
# all all folder-attributes (due to inheritance). Check_MK
# is presented with the result of the inheritance.
def rewrite_config_files_below(folder):
    for fo in folder[".folders"].values():
        rewrite_config_files_below(fo)
    rewrite_config_file(folder)

def rewrite_config_file(folder):
    load_hosts(folder)
    save_hosts(folder)


# returns the aliaspath of the given folder
def get_folder_aliaspath(folder, show_main = True):
    aliaspath = [folder['title']]
    while '.parent' in folder:
        folder = folder['.parent']
        if folder != g_root_folder or show_main:
            aliaspath.insert(0,folder['title'])
    return ' / '.join(aliaspath)

#   +----------------------------------------------------------------------+
#   |                   _____     _     _                                  |
#   |                  |  ___|__ | | __| | ___ _ __ ___                    |
#   |                  | |_ / _ \| |/ _` |/ _ \ '__/ __|                   |
#   |                  |  _| (_) | | (_| |  __/ |  \__ \                   |
#   |                  |_|  \___/|_|\__,_|\___|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for showing a folder, bulk actions on hosts.                    |
#   +----------------------------------------------------------------------+

def mode_folder(phase):
    if phase == "title":
        return g_folder["title"]

    elif phase == "buttons":
        global_buttons()
        if config.may("wato.rulesets") or config.may("wato.seeall"):
            html.context_button(_("Rulesets"),        make_link([("mode", "rulesets")]), "rulesets")
        html.context_button(_("Folder Properties"), make_link_to([("mode", "editfolder")], g_folder), "properties")
        if config.may("wato.manage_folders"):
            html.context_button(_("New folder"),        make_link([("mode", "newfolder")]), "newfolder")
        if config.may("wato.manage_hosts"):
            html.context_button(_("New host"),          make_link([("mode", "newhost")]), "new")
        search_button()
        folder_status_button()
    
    elif phase == "action":
        if html.var("_search"): # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.var("_delete_folder") and html.transaction_valid():
            delname = html.var("_delete_folder")
            if delname in g_folder[".folders"]:
                del_folder = g_folder[".folders"][delname]
                if len(del_folder[".folders"]) > 0:
                    raise MKUserError(None, _("The folder %s cannot be deleted, it still contains some subfolders.")
                    % del_folder["title"])
                config.need_permission("wato.manage_folders")
                if True != check_folder_permissions(g_folder, "write", False):
                    raise MKAuthException(_("Sorry. In order to delete a folder you need write permissions to its "
                                            "parent folder."))
                return delete_folder_after_confirm(del_folder)
            else:
                raise MKGeneralException(_("You called this page with a non-existing folder/file %s") % delname)

        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.var("_delete_host")
        if delname and delname in g_folder[".hosts"]:
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(g_folder, "write")
            return delete_host_after_confirm(delname)

        # Move single hosts to other folders
        if html.has_var("_move_host_to"):
            config.need_permission("wato.edit_hosts")
            hostname = html.var("host")
            check_folder_permissions(g_folder, "write")
            if hostname:
                move_host_to(hostname, html.var("_move_host_to"))
                return

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        if html.var("_bulk_inventory"):
            return "bulkinventory"

        selected_hosts = get_hostnames_from_checkboxes()
        if len(selected_hosts) == 0:
            raise MKUserError(None,
            _("Please select some hosts before doing bulk operations on hosts."))

        # Deletion
        if html.var("_bulk_delete"):
            config.need_permission("wato.manage_hosts")
            return delete_hosts_after_confirm(selected_hosts)

        # Move
        elif html.var("_bulk_move"):
            config.need_permission("wato.edit_hosts")
            target_folder_name = html.var("bulk_moveto")
            if target_folder_name == "@":
                raise MKUserError("bulk_moveto", _("Please select the destination folder"))
            target_folder = g_folders[target_folder_name]
            num_moved = move_hosts_to(selected_hosts, target_folder_name)
            return None, _("Successfully moved %d hosts to %s") % (num_moved, target_folder["title"])

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
            config.need_permission("wato.edit_hosts")
            return move_to_imported_folders(selected_hosts)

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"

    else:
        render_folder_path()
        have_something = show_subfolders(g_folder)
        have_something = show_hosts(g_folder) or have_something
        if not have_something:
            url = "wato.py?mode=view_ruleset&varname=snmp_communities"
            render_main_menu([
                ("newhost", _("Create new host"), "new", "hosts", 
                  _("Click here to create a host to be monitored. Please make sure that " 
                    "you first have installed the Check_MK agent on that host. If that "
                    "host shall be monitored via SNMP, please make sure, that the monitoring "
                    "system has access and the <a href='%s'>SNMP community</a> has been set.") % url),
                ("newfolder", _("Create new folder"), "newfolder", "hosts",
                  _("Hosts are organized in folders. The folders construct a tree which can also "
                    "be used to navigate in the status GUI. Attributes can be inherited along the "
                    "paths of that tree. The usage of folders is optional."))])


def prepare_folder_info():
    declare_host_tag_attributes() # create attributes out of tag definitions
    load_all_folders()            # load information about all folders
    set_current_folder()          # set g_folder from HTML variable


def check_host_permissions(hostname, exception=True):
    if config.may("wato.all_folders"):
        return True
    host = g_folder[".hosts"][hostname]
    effective = effective_attributes(host, g_folder)
    use, cgs = effective.get("contactgroups", (None, []))
    # Get contact groups of user
    users = load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id]["contactgroups"]

    for c in user_cgs:
        if c in cgs:
            return True

    reason = _("Sorry, you have no permission on the host '<b>%s</b>'. The host's contact "
               "groups are <b>%s</b>, your contact groups are <b>%s</b>.") % \
               (hostname, ", ".join(cgs), ", ".join(user_cgs))
    if exception:
        raise MKAuthException(reason)
    return reason


def check_folder_permissions(folder, how, exception=True):
    if config.may("wato.all_folders"):
        return True
    if how == "read" and config.may("wato.see_all_folders"):
        return True

    # Get contact groups of that folder
    effective = effective_attributes(None, folder)
    use, cgs = effective.get("contactgroups", (None, []))

    # Get contact groups of user
    users = load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id]["contactgroups"]

    for c in user_cgs:
        if c in cgs:
            return True

    reason = _("Sorry, you have no permission on the folder '<b>%s</b>'. The folder's contact "
               "groups are <b>%s</b>, your contact groups are <b>%s</b>.") % \
               (folder["title"], ", ".join(cgs), ", ".join(user_cgs))
    if exception:
        raise MKAuthException(reason)
    else:
        return reason

# Make sure that the user is in all of cgs contact groups.
# This is needed when the user assigns contact groups to
# objects. He may only assign such groups he is member himself.
def check_user_contactgroups(cgspec):
    if config.may("wato.all_folders"):
        return

    use, cgs = cgspec
    users = load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id]["contactgroups"]
    for c in cgs:
        if c not in user_cgs:
            raise MKAuthException(_("Sorry, you cannot assign the contact group '<b>%s</b>' "
              "because you are not member in that group. Your groups are: <b>%s</b>") % 
                 ( c, ", ".join(user_cgs)))



def show_subfolders(folder):
    if len(folder[".folders"]) == 0:
        return False

    html.write("<h3>" + _("Subfolders") + "</h3>")
    html.write("<table class=data>\n")
    html.write("<tr><th class=left>" 
               + _("Actions") + "</th><th>" 
               + _("Title") + "</th><th>"
               + _("Auth") + "</th>")

    for attr, topic in host_attributes:
        if attr.show_in_table() and attr.show_in_folder():
            html.write("<th>%s</th>" % attr.title())

    if not config.wato_hide_filenames:
        html.write("<th>%s</th>" % _("Directory"))
    html.write("<th class=right>" + _("Hosts") + "</th>")
    html.write("<th class=right>" + _("Subfolders") + "</th></tr>\n")

    odd = "even"

    for entry in api.sort_by_title(folder[".folders"].values()):
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)

        name = entry[".name"]
        folder_path = entry[".path"]

        edit_url     = make_link_to([("mode", "editfolder"), ("backfolder", g_folder[".path"])], entry)
        delete_url   = make_action_link([("mode", "folder"), 
                       ("_delete_folder", entry[".name"])])
        enter_url    = make_link_to([("mode", "folder")], entry)

        html.write("<td class=buttons>")
        icon_button(edit_url, _("Edit the properties of this folder"), "folderproperties")
        if config.may("wato.manage_folders"):
            icon_button(delete_url, _("Delete this folder"), "delete")
        html.write("</td>")


        # Title and filename
        html.write('<td class=takeall><a href="%s">%s</a></td>' % 
                    (enter_url, entry["title"]))

        # Am I authorized?
        auth = check_folder_permissions(entry, "write", False)
        if auth == True:
            icon = "authok"
            title = _("You have permission to this folder.") 
        else:
            icon = "autherr"
            title = htmllib.strip_tags(auth)
        html.write('<td><img class=icon src="images/icon_%s.png" title="%s"></td>' % (icon, title))


        # Attributes for Hosts
        effective = effective_attributes(None, folder)
        for attr, topic in host_attributes:
            if attr.show_in_table() and attr.show_in_folder():
                attrname = attr.name()
                if attrname in entry.get("attributes", {}):
                    tdclass, content = attr.paint(entry["attributes"][attrname], "")
                else:
                    tdclass, content = attr.paint(effective.get(attrname), "")
                    tdclass += " inherited"
                html.write('<td class="%s">%s</td>' % (tdclass, content))

        # Internal foldername
        if not config.wato_hide_filenames:
            html.write("<td>%s</td>" % name)

        # Number of hosts
        html.write("<td class=number>%d</td>" % num_hosts_in(entry, recurse=True))

        # Number of subfolders
        html.write("<td class=number>%d</td>" % len(entry[".folders"]))

        html.write("</tr>")
    html.write("</table>")
    return True
    
def show_hosts(folder):
    load_hosts(folder)
    if len(folder[".hosts"]) == 0:
        return False

    html.write("<h3>" + _("Hosts") + "</h3>")
    html.begin_form("search")
    html.text_input("search")
    html.button("_search", _("Search"))
    html.set_focus("search")
    html.hidden_fields()
    html.end_form()
    html.write("<p>")

    hostnames = folder[".hosts"].keys()
    hostnames.sort()

    # Show table of hosts in this folder
    colspan = 6
    html.begin_form("hosts", None, "POST", onsubmit = 'add_row_selections(this);')
    html.write("<table class=data>\n")
    html.write("<tr><th class=left></th><th></th><th>"
               + _("Hostname") + "</th><th>"
               + _("Auth") + "</th>"
               + "<th>" + _("Tags") + "</th>")


    for attr, topic in host_attributes:
        if attr.show_in_table():
            html.write("<th>%s</th>" % attr.title())
            colspan += 1

    html.write("<th class=right>" + _("Move To") + "</th>")
    html.write("</tr>\n")
    odd = "odd"

    def bulk_actions(at_least_one_imported, top = False):
        # bulk actions
        html.write('<tr class="data %s0">' % odd)
        html.write("<td colspan=%d>" % colspan)
        html.jsbutton('_markall', _('X'), 'javascript:toggle_all_rows();')
        html.write(' ' + _("On all selected hosts:\n"))
        if config.may("wato.manage_hosts"):
            html.button("_bulk_delete", _("Delete"))
        if config.may("wato.edit_hosts"):
            html.button("_bulk_edit", _("Edit"))
            html.button("_bulk_cleanup", _("Cleanup"))
        if config.may("wato.services"):
            html.button("_bulk_inventory", _("Inventory"))
        if config.may("wato.edit_hosts"):
            host_move_combo(None, top)
            if at_least_one_imported:
                html.button("_bulk_movetotarget", _("Move to Target Folders"))
        html.write("</td></tr>\n")

    search_text = html.var("search")

    # Remember if that host has a target folder (i.e. was imported with
    # a folder information but not yet moved to that folder). If at least
    # one host has a target folder, then we show an additional bulk action.
    at_least_one_imported = False
    more_than_ten_items = False
    for num, hostname in enumerate(hostnames):
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder)

        if effective.get("imported_folder"):
            at_least_one_imported = True

        if num == 11:
            more_than_ten_items = True

    # Add the bulk action buttons also to the top of the table when this
    # list shows more than 10 rows
    if more_than_ten_items and \
        (config.may("wato.edit_hosts") or config.may("wato.manage_hosts")):
        bulk_actions(at_least_one_imported, top = True)

    # Now loop again over all hosts and display them
    for hostname in hostnames:
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder)

        # Rows with alternating odd/even styles
        html.write('<tr class="data %s0">' % odd)
        odd = odd == "odd" and "even" or "odd" 

        # Column with actions (buttons)
        edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
        services_url = make_link([("mode", "inventory"), ("host", hostname)])
        clone_url    = make_link([("mode", "newhost"), ("clone", hostname)])
        delete_url   = make_action_link([("mode", "folder"), ("_delete_host", hostname)])

        html.write('<td class=checkbox>')
        html.write("<input type=checkbox name=\"%s\" value=%d />" % (hostname, colspan))
        html.write('</td>\n')

        html.write("<td class=buttons>")
        icon_button(edit_url, _("Edit the properties of this host"), "edithost")
        icon_button(services_url, _("Edit the services of this host, do an inventory"), "services")
        if config.may("wato.manage_hosts"):
            icon_button(clone_url, _("Create a clone of this host"), "insert")
            icon_button(delete_url, _("Delete this host"), "delete")
        html.write("</td>\n")

        # Hostname with link to details page (edit host)
        html.write('<td><a href="%s">%s</a></td>\n' % (edit_url, hostname))

        # Am I authorized?
        auth = check_host_permissions(hostname, False)
        if auth == True:
            icon = "authok"
            title = _("You have permission to this host.") 
        else:
            icon = "autherr"
            title = htmllib.strip_tags(auth)
        html.write('<td><img class=icon src="images/icon_%s.png" title="%s"></td>' % (icon, title))
        
        # Raw tags
        html.write("<td>%s</td>" % "<b style='color: #888;'>|</b>".join(host[".tags"]))

        # Show attributes
        for attr, topic in host_attributes:
            if attr.show_in_table():
                attrname = attr.name()
                if attrname in host:
                    tdclass, tdcontent = attr.paint(host.get(attrname), hostname)
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                html.write('<td class="%s">' % tdclass)
                html.write(tdcontent)
                html.write("</td>\n")

        # Move to
        html.write("<td>")
        if config.may("wato.edit_hosts"):
            host_move_combo(hostname)
        html.write("</td>\n")
        html.write("</tr>\n")

    if config.may("wato.edit_hosts") or config.may("wato.manage_hosts"):
        bulk_actions(at_least_one_imported)
    html.write("</table>\n")

    html.hidden_fields()
    html.end_form()

    html.javascript('g_selected_rows = %s;\n'
                    'init_rowselect();' % repr(hostnames))
    return True


def host_move_combo(host = None, top = False):
    other_folders = []
    for path, afolder in g_folders.items():
        # TODO: Check permisssions
        if afolder != g_folder:
            os_path = afolder[".path"]
            msg = afolder["title"]
            if os_path:
                msg += " (%s)" % os_path
            other_folders.append((os_path, msg))

    if len(other_folders) > 0:
        selections = [("@", _("(select folder)"))] + other_folders
        if host == None:
            html.button("_bulk_move", _("Move To:"))
            field_name = 'bulk_moveto'
            if top:
                field_name = '_top_bulk_moveto'
                if html.has_var('bulk_moveto'):
                    html.javascript('update_bulk_moveto("%s")' % html.var('bulk_moveto', ''))
            html.select(field_name, selections, "@",
                        onchange = "update_bulk_moveto(this.value)",
                        attrs = {'class': 'bulk_moveto'})
        else:
            html.hidden_field("host", host)
            uri = html.makeuri([("host", host), ("_transid", html.current_transid() )])
            html.sorted_select("host_move_%s" % host, selections, "@", 
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri);


def move_hosts_to(hostnames, path):
    if path not in g_folders: # non-existing folder
        return

    target_folder = g_folders[path]
    check_folder_permissions(target_folder, "write")

    if target_folder == g_folder:
        return 0 # target and source are the same

    # read hosts currently in target file
    load_hosts(target_folder)
    target_hosts = target_folder[".hosts"]

    num_moved = 0
    for hostname in hostnames:
        if hostname not in g_folder[".hosts"]: # non-existant host
            continue

        target_hosts[hostname] = g_folder[".hosts"][hostname]
        target_folder["num_hosts"] += 1
        g_folder["num_hosts"] -= 1
        del g_folder[".hosts"][hostname]
        if len(hostnames) == 1:
            log_pending(hostname, "move-host", _("Moved host from %s to %s") %
                (g_folder[".path"], target_folder[".path"]))
        num_moved += 1

    save_folder_and_hosts(target_folder)
    save_folder_and_hosts(g_folder)
    call_hook_hosts_changed(g_root_folder)
    if len(hostnames) > 1:
        log_pending(target_folder, "move-host", _("Moved %d hosts from %s to %s") %
            (num_moved, g_folder[".path"], target_folder[".path"]))
    return num_moved 
        

def move_host_to(hostname, target_filename):
    return move_hosts_to([hostname], target_filename)

def delete_hosts_after_confirm(hosts):
    c = wato_confirm(_("Confirm deletion of %d hosts") % len(hosts),
                     _("Do you really want to delete the %d selected hosts?") % len(hosts))
    if c:
        for delname in hosts:
            del g_folder[".hosts"][delname]
            g_folder["num_hosts"] -= 1
            check_mk_automation("delete-host", [delname])
            log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        save_folder_and_hosts(g_folder)
        call_hook_hosts_changed(g_folder)
        return "folder", _("Successfully deleted %d hosts") % len(hosts)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 
        
def delete_folder_after_confirm(del_folder):
    msg = _("Do you really want to delete the folder %s?") % del_folder["title"]
    if not config.wato_hide_filenames:
        msg += "<br>" + _("(The directory <tt>%s</tt>)") % folder_dir(del_folder)
    c = wato_confirm(_("Confirm folder deletion"), msg)
                     
    if c:
        del g_folder[".folders"][del_folder[".name"]]
        folder_path = folder_dir(del_folder)
        try:
            for ext in [ ".wato", "hosts.mk", "rules.mk" ]:
                if os.path.exists(folder_path + "/" + ext):
                    os.remove(folder_path + "/" + ext)
            os.rmdir(folder_path)
        except:
            pass
        if os.path.exists(folder_path):
            raise MKGeneralException(_("Cannot remove the folder '%s': probably there are "
                                       "still non-WATO files contained in this directory.") % folder_path)

        log_pending(del_folder, "delete-folder", _("Deleted empty folder %s")% folder_dir(del_folder))
        call_hook_folder_deleted(del_folder)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

# Create list of all hosts that are select with checkboxes in the current file.
# This is needed for bulk operations.
def get_hostnames_from_checkboxes():
    hostnames = g_folder[".hosts"].keys()
    hostnames.sort()

    selected = []
    if html.var('selected_rows', '') != '':
        selected = html.var('selected_rows', '').split(',')

    selected_hosts = []
    search_text = html.var("search")
    for name in hostnames:
        if (not search_text or (search_text.lower() in name.lower())) \
            and name in selected:
            selected_hosts.append(name)
    return selected_hosts

#   +----------------------------------------------------------------------+
#   |           _____    _ _ _     _____     _     _                       |
#   |          | ____|__| (_) |_  |  ___|__ | | __| | ___ _ __             |
#   |          |  _| / _` | | __| | |_ / _ \| |/ _` |/ _ \ '__|            |
#   |          | |__| (_| | | |_  |  _| (_) | | (_| |  __/ |               |
#   |          |_____\__,_|_|\__| |_|  \___/|_|\__,_|\___|_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for editing the properties of a folder. This includes the       |
#   | creation of new folders.                                             |
#   +----------------------------------------------------------------------+

def mode_editfolder(phase, new):
    global g_folder

    if new:
        page_title = _("Create new folder")
        name, title = None, None
        mode = "new"
    else:
        page_title = _("Folder Properties")
        name  = g_folder[".name"]
        title = g_folder["title"]
        mode = "edit"

    if phase == "title":
        return page_title

    elif phase == "buttons":
        linkvars = [("mode", "folder")]
        if html.has_var("backfolder"):
            link = make_link_to(linkvars, g_folders[html.var("backfolder")])
        else:
            link = make_link(linkvars)
        html.context_button(_("Back"), link, "back")
            
    elif phase == "action":
        if new:
            config.need_permission("wato.manage_folders")
        else:
            config.need_permission("wato.edit_folders")

        if not html.check_transaction():
            return "folder"

        # Title
        title = html.var_utf8("title")
        if not title:
            raise MKUserError("title", _("Please supply a title."))

        # OS filename
        if new:
            if not config.wato_hide_filenames:
                name = html.var("name", "").strip()
                check_wato_foldername("name", name)
            else:
                name = create_wato_foldername(title)

        # Attributes
        attributes = collect_attributes()
        attributes_changed = not new and attributes != g_folder.get("attributes", {})

        if new:
            check_folder_permissions(g_folder, "write")
            check_user_contactgroups(attributes.get("contactgroups", (False, [])))
            if g_folder[".path"]:
                newpath = g_folder[".path"] + "/" + name
            else:
                newpath = name
            new_folder = { 
                ".name"       : name,
                ".path"       : newpath,
                "title"      : title, 
                "attributes" : attributes,
                ".folders"   : {},
                ".hosts"     : {},
                "num_hosts"  : 0,
            }
            g_folders[newpath] = new_folder
            g_folder[".folders"][name] = new_folder
            save_folder(new_folder)
            call_hook_folder_created(new_folder)
            log_pending(new_folder, "new-folder", _("Created new folder %s") % title)

        else:
            cgs_changed = attributes.get("contactgroups") != g_folder["attributes"].get("contactgroups")
            other_changed = attributes != g_folder["attributes"] and not cgs_changed
            if other_changed:
                check_folder_permissions(g_folder, "write")
            if g_folder.get(".parent") \
                 and cgs_changed \
                 and True != check_folder_permissions(g_folder.get(".parent"), "write", False):
                 raise MKAuthException(_("Sorry. In order to change the permissions of a folder you need write "
                                         "access to the parent folder."))

            if cgs_changed:
                check_user_contactgroups(attributes.get("contactgroups"))
            log_pending(g_folder, "edit-folder", "Edited properties of folder %s" % title)

            g_folder["title"]      = title
            g_folder["attributes"] = attributes

            # Due to changes in folder/file attributes, host files
            # might need to be rewritten in order to reflect Changes
            # in Nagios-relevant attributes.
            if attributes_changed:
                rewrite_config_files_below(g_folder) # due to inherited attributes
                log_pending(g_folder, "edit-folder", _("Changed attributes of folder %s") % title)
                call_hook_hosts_changed(g_folder)

        
        need_sidebar_reload()
        save_folder_and_hosts(g_folder) # save folder metainformation


        if html.has_var("backfolder"):
            set_current_folder(g_folders[html.var("backfolder")])
        return "folder"


    else:
        render_folder_path()
        check_folder_permissions(g_folder, "read")

        html.begin_form("editfolder")
        html.write('<table class="form nomargin">\n')
        
        # title
        html.write("<tr class=top><td class=legend>Title</td><td class=checkbox></td><td class=content>")
        html.text_input("title", title)
        html.set_focus("title")
        html.write("</td></tr>\n")

        # folder name (omit this for root folder)
        if not (not new and g_folder == g_root_folder):
            if not config.wato_hide_filenames:
                html.write("<tr><td class=legend colspan=2>" 
                    + _("Internal directory name") + "<br><i>"
                    + _("This is the name of subdirectory where the files and "
                    "other folders will be created. You cannot change this later.") +
                    "</i></td><td class=content>")

                if new:
                    html.text_input("name")
                else:
                    html.write(name)

                html.write("</td></tr>\n")

        # Attributes inherited to hosts
        if have_folder_attributes():
            if new:
                attributes = {}
                parent = g_folder
                myself = None
            else:
                attributes = g_folder.get("attributes", {})
                parent = g_folder.get(".parent")
                myself = g_folder

            configure_attributes({"folder": attributes}, "folder", parent, myself)

        html.write('<tr><td colspan=3 class="buttons">')
        html.button("save", _("Save &amp; Finish"), "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()
        

def check_wato_foldername(htmlvarname, name):
    if name in g_folder[".folders"]:
        raise MKUserError(htmlvarname, _("A folder with that name already exists."))
    if not name:
        raise MKUserError(htmlvarname, _("Please specify a name."))
    if not re.match("^[-a-z0-9A-Z_]*$", name):
        raise MKUserError(htmlvarname, _("Invalid folder name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))


def create_wato_foldername(title, in_folder = None):
    if in_folder == None:
        in_folder = g_folder

    basename = convert_title_to_filename(title)
    c = 1
    name = basename
    while True:
        if name not in in_folder[".folders"]:
            break
        c += 1
        name = "%s-%d" % (basename, c)
    return name


def convert_title_to_filename(title):
    converted = ""
    for c in title.lower():
        if c == u'ä':
            converted += 'ae'
        elif c == u'ö':
            converted += 'oe'
        elif c == u'ü':
            converted += 'ue'
        elif c == u'ß':
            converted += 'ss'
        elif c in "abcdefghijklmnopqrstuvwxyz0123456789-_":
            converted += c
        else:
            converted += "_"
    return str(converted)


#   +----------------------------------------------------------------------+
#   |               _____    _ _ _     _   _           _                   |
#   |              | ____|__| (_) |_  | | | | ___  ___| |_                 |
#   |              |  _| / _` | | __| | |_| |/ _ \/ __| __|                |
#   |              | |__| (_| | | |_  |  _  | (_) \__ \ |_                 |
#   |              |_____\__,_|_|\__| |_| |_|\___/|___/\__|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for host details (new, clone, edit)                             |
#   +----------------------------------------------------------------------+

def mode_edithost(phase, new):
    hostname = html.var("host") # may be empty in new/clone mode

    clonename = html.var("clone")
    if clonename and clonename not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page with an invalid host name."))
    
    if clonename:
        title = _("Create clone of %s") % clonename
        host = g_folder[".hosts"][clonename]
        mode = "clone"
    elif not new and hostname in g_folder[".hosts"]:
        title = _("Edit host") + " " + hostname
        host = g_folder[".hosts"][hostname]
        mode = "edit"
    else:
        title = _("Create new host")
        host = {}
        mode = "new"

    if phase == "title":
        return title

    elif phase == "buttons":
        if not new:
            host_status_button(hostname, "hoststatus")
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        if not new:
            html.context_button(_("Services"), 
                  make_link([("mode", "inventory"), ("host", hostname)]), "services")
            html.context_button(_("Rulesets"),  
                  make_link([("mode", "rulesets"), ("host", hostname), ("local", "on")]), "rulesets")

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(g_folder, "write")
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_host_after_confirm(hostname)

        host = collect_attributes()

        # handle clone & new
        if new:
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(g_folder, "write")
            check_user_contactgroups(host.get("contactgroups", (False, [])))
            if not hostname:
                raise MKUserError("host", _("Please specify a host name."))
            elif hostname in g_folder[".hosts"]:
                raise MKUserError("host", _("A host with this name already exists."))
            elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                raise MKUserError("host", _("Invalid host name: must contain only characters, digits, dash, underscore and dot."))
        else:
            config.need_permission("wato.edit_hosts")

            # Check which attributes have changed. For a change in the contact groups
            # we need permissions on the folder. For a change in the rest we need
            # permissions on the host
            old_host = dict(g_folder[".hosts"][hostname].items())
            del old_host[".tags"] # not contained in new host
            cgs_changed = host.get("contactgroups") != old_host.get("contactgroups")
            other_changed = old_host != host and not cgs_changed
            if other_changed:
                check_host_permissions(hostname)
            if cgs_changed \
                 and True != check_folder_permissions(g_folder, "write", False):
                 raise MKAuthException(_("Sorry. In order to change the permissions of a host you need write "
                                         "access to the folder it is contained in."))
            if cgs_changed:
                check_user_contactgroups(host.get("contactgroups", (False, [])))

        if hostname:
            go_to_services = html.var("services")
            if html.check_transaction():
                g_folder[".hosts"][hostname] = host
                if new:
                    message = _("Created new host %s.") % hostname
                    log_pending(hostname, "create-host", message) 
                    g_folder["num_hosts"] += 1
                else:
                    log_pending(hostname, "edit-host", _("Edited properties of host [%s]") % hostname)
                save_folder_and_hosts(g_folder)
                call_hook_hosts_changed(g_folder)
            if new:
                return go_to_services and "firstinventory" or "folder"
            else:
                return go_to_services and "inventory" or "folder"


    else:
        if new:
            render_folder_path()

        html.begin_form("edithost")
        html.write('<table class="form nomargin">\n')

        # host name
        html.write("<tr class=top><td class=legend>" + _("Hostname") + "</td><td class=checkbox></td><td class=content>")
        if hostname and mode == "edit":
            html.write(hostname)
        else:
            html.text_input("host")
            html.set_focus("host")
        html.write("</td></tr>\n")

        configure_attributes({hostname: host}, "host", parent = g_folder)

        html.write('<tr><td class="buttons" colspan=3>')
        html.button("save", _("Save &amp; Finish"), "submit")
        if not new:
            html.button("delete", _("Delete host!"), "submit")
        html.button("services", _("Save &amp; go to Services"), "submit")
        html.write("</td></tr>\n")
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()


def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        del g_folder[".hosts"][delname]
        g_folder["num_hosts"] -= 1
        save_folder_and_hosts(g_folder)
        log_pending(delname, "delete-host", _("Deleted host %s") % delname)
        check_mk_automation("delete-host", [delname])
        call_hook_hosts_changed(g_folder)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

#   +----------------------------------------------------------------------+
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for doing the inventory on a single host and/or showing and     |
#   | editing the current services of a host.                              |
#   +----------------------------------------------------------------------+

def mode_inventory(phase, firsttime):
    hostname = html.var("host")
    if hostname not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page for a non-existing host."))

    if phase == "title":
        title = _("Services of host %s") % hostname
        if html.var("_scan"):
            title += _(" (live scan)")
        else:
            title += _(" (cached data)")
        return title

    elif phase == "buttons":
        host_status_button(hostname, "host")
        html.context_button(_("Folder"), 
                            make_link([("mode", "folder")]), "back")
        html.context_button(_("Host properties"), 
                            make_link([("mode", "edithost"), ("host", hostname)]), "back")
        html.context_button(_("Full Scan"), html.makeuri([("_scan", "yes")]))

    elif phase == "action":
        config.need_permission("wato.services")
        if html.check_transaction():
            cache_options = not html.var("_scan") and [ '--cache' ] or []
            table = check_mk_automation("try-inventory", cache_options + [hostname])
            table.sort()
            active_checks = {}
            new_target = "folder"
            for st, ct, checkgroup, item, paramstring, params, descr, state, output, perfdata in table:
                if (html.has_var("_cleanup") or html.has_var("_fixall")) \
                    and st in [ "vanished", "obsolete" ]:
                    pass
                elif (html.has_var("_activate_all") or html.has_var("_fixall")) \
                    and st == "new":
                    active_checks[(ct, item)] = paramstring
                else:
                    varname = "_%s_%s" % (ct, item)
                    if html.var(varname, "") != "":
                        active_checks[(ct, item)] = paramstring

            check_mk_automation("set-autochecks", [hostname], active_checks)
            message = _("Saved check configuration of host [%s] with %d services") % \
                        (hostname, len(active_checks)) 
            log_pending(hostname, "set-autochecks", message) 
            return new_target, message
        return "folder"

    else:
        show_service_table(hostname, firsttime)


def show_service_table(hostname, firsttime):
    # Read current check configuration
    cache_options = not html.var("_scan") and [ '--cache' ] or []
    try:
        table = check_mk_automation("try-inventory", cache_options + [hostname])
    except Exception, e:
        html.show_error("Inventory failed for this host: %s" % e)
        return

    table.sort()

    html.begin_form("checks", None, "POST")
    fixall = 0
    if config.may("wato.services"):
        for entry in table:
            if entry[0] == 'new' and not html.has_var("_activate_all") and not firsttime:
                html.button("_activate_all", _("Activate missing"))
                fixall += 1
                break
        for entry in table:
            if entry[0] in [ 'obsolete', 'vanished', ]:
                html.button("_cleanup", _("Remove exceeding"))
                fixall += 1
                break

        if fixall == 2:
            html.button("_fixall", _("Fix all missing/exceeding"))

        if len(table) > 0:
            html.button("_save", _("Save manual check configuration"))

    html.hidden_fields()
    if html.var("_scan"):
        html.hidden_field("_scan", "on")

    html.write("<table class=data>\n")

    for state_name, state_type, checkbox in [ 
        ( _("Available (missing) services"), "new", firsttime ),
        ( _("Already configured services"), "old", True, ),
        ( _("Obsolete services (being checked, but should be ignored)"), "obsolete", True ),
        ( _("Ignored services (configured away by admin)"), "ignored", False ),
        ( _("Vanished services (checked, but no longer exist)"), "vanished", True ),
        ( _("Manual services (defined in main.mk)"), "manual", None ),
        ( _("Legacy services (defined in main.mk)"), "legacy", None )
        ]:
        first = True
        trclass = "even"
        for st, ct, checkgroup, item, paramstring, params, descr, state, output, perfdata in table:
            if state_type != st:
                continue
            if first:
                html.write('<tr class=groupheader><td colspan=7><br>%s</td></tr>\n' % state_name)
                html.write("<tr><th>" + _("Status") + "</th><th>" + _("Checktype") + "</th><th>" + _("Item") + "</th>"
                           "<th>" + _("Service Description") + "</th><th>" 
                           + _("Current check") + "</th><th></th><th></th></tr>\n")
                first = False
            trclass = trclass == "even" and "odd" or "even"
            statename = nagios_short_state_names.get(state, "PEND")
            if statename == "PEND":
                stateclass = "state svcstate statep"
                state = 0 # for tr class
            else:
                stateclass = "state svcstate state%s" % state
            html.write("<tr class=\"data %s%d\">" % (trclass, state))

            # Status, Checktype, Item, Description, Check Output
            html.write("<td class=\"%s\">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>" %
                    (stateclass, statename, ct, item, descr, output))

            # Icon for Rule editor, Check parameters
            html.write("<td>")
            if checkgroup:
                varname = "checkgroup_parameters:" + checkgroup
                url = make_link([("mode", "edit_ruleset"), 
                                 ("varname", varname),
                                 ("host", hostname),
                                 ("item", repr(item))]) 
                title = _("Edit rules for this check parameter")
                rulespec = g_rulespecs.get(varname)
                if rulespec:
                    title = "Check parameters for this service: " + \
                      rulespec["valuespec"].value_to_text(params)
                html.write('<a href="%s"><img title="%s" class=icon src="images/icon_rulesets.png"></a>' %
                   (url, title))
                           
            html.write("</td>")

            # Checkbox
            html.write("<td>")
            if checkbox != None:
                varname = "_%s_%s" % (ct, item)
                html.checkbox(varname, checkbox)
            html.write("</td></tr>\n")
    html.write("</table>\n")
    html.end_form()


#   +----------------------------------------------------------------------+
#   |                   ____                      _                        |
#   |                  / ___|  ___  __ _ _ __ ___| |__                     |
#   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
#   |                   ___) |  __/ (_| | | | (__| | | |                   |
#   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Dialog for searching for hosts - globally in all files               |
#   +----------------------------------------------------------------------+

def mode_search(phase):
    if phase == "title":
        return _("Search for hosts in %s and below" % (g_folder["title"]))

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")

    elif phase == "action":
        pass

    else:
        render_folder_path()
        html.write("<table><tr><td>\n")

        ## # Show search form
        html.begin_form("search")
        html.write("<table class=form>")

        # host name
        html.write("<tr><td class=legend colspan=2>" + _("Hostname") + "</td><td class=content>")
        html.text_input("host")
        html.set_focus("host")
        html.write("</td></tr>\n")

        # Attributes
        configure_attributes({}, "search", parent = None)
        
        # Button
        html.write('<tr><td class="buttons" colspan=3>')
        html.button("_global", _("Search globally"), "submit")
        html.button("_local", _("Search in %s") % g_folder["title"], "submit")
        html.write("</td></tr>\n")
        
        html.write("</table>\n")
        html.hidden_fields()
        html.end_form()

        # Show search results
        if html.transaction_valid():
            html.write("</td><td>")
            crit = {
                ".name" : html.var("host"),
            }
            crit.update(collect_attributes(do_validate = False))

            html.write("<h3>" + _("Search results:") + "</h3>")
            if html.has_var("_local"):
                folder = g_folder
            else:
                folder = g_root_folder

            # html.write("<pre>%s</pre>" % pprint.pformat(crit))
            if not search_hosts_in_folders(folder, crit):
                html.message(_("No matching hosts found."))

        html.write("</td></tr></table>")



def search_hosts_in_folders(folder, crit):
    num_found = 0

    num_found = search_hosts_in_folder(folder, crit)
    for f in folder[".folders"].values():
        num_found += search_hosts_in_folders(f, crit)

    return num_found


def search_hosts_in_folder(folder, crit):
    found = []
    hosts = load_hosts(folder)
    for hostname, host in hosts.items():
        if crit[".name"] and crit[".name"].lower() not in hostname.lower():
            continue

        # Compute inheritance
        effective = effective_attributes(host, folder)

        # Check attributes
        dont_match = False
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attrname in crit and  \
                not attr.filter_matches(crit[attrname], effective.get(attrname), hostname):
                dont_match = True
                break
        if dont_match: 
           continue

        found.append((hostname, host, effective))

    if found:
        render_folder_path(folder, True)
        found.sort()
        html.write("<table class=data><tr><th>%s</th>" % (_("Hostname"), ))
        for attr, topic in host_attributes:
            if attr.show_in_table():
                html.write("<th>%s</th>" % attr.title())
        html.write("</tr>")

        even = "even"
        for hostname, host, effective in found:
            even = even == "even" and "odd" or "even"
            host_url =  make_link_to([("mode", "edithost"), ("host", hostname)], folder)
            html.write('<tr class="data %s0"><td><a href="%s">%s</a></td>\n' % 
               (even, host_url, hostname))
            for attr, topic in host_attributes:
                attrname = attr.name()
                if attr.show_in_table():
                    if attrname in host:
                        tdclass, content = attr.paint(host[attrname], hostname)
                    else:
                        tdclass, content = attr.paint(effective[attrname], hostname)
                        tdclass += " inherited"
                    html.write('<td class="%s">%s</td>' % (tdclass, content))
        html.write("</tr>\n")
        html.write("</table><br>\n")

    return len(found)

#   +----------------------------------------------------------------------+
#   |       ____ ______     __   ___                            _          |
#   |      / ___/ ___\ \   / /  |_ _|_ __ ___  _ __   ___  _ __| |_        |
#   |     | |   \___ \\ \ / /____| || '_ ` _ \| '_ \ / _ \| '__| __|       |
#   |     | |___ ___) |\ V /_____| || | | | | | |_) | (_) | |  | |_        |
#   |      \____|____/  \_/     |___|_| |_| |_| .__/ \___/|_|   \__|       |
#   |                                         |_|                          |
#   +----------------------------------------------------------------------+
#   | The following functions help implementing an import of hosts from    |
#   | third party applications, such as from CVS files. The import itsself |
#   | is not yet coded, but functions for dealing with the imported hosts. |
#   +----------------------------------------------------------------------+

def move_to_imported_folders(hosts):
    c = wato_confirm( 
              _("Confirm moving hosts"),
              _('You are going to move the selected hosts to folders ' 
                'representing their original folder location in the system '
                'you did the import from. Please make sure that you have '
                'done an <b>inventory</b> before moving the hosts.'))
    if c == False: # not yet confirmed
        return ""
    elif not c:
        return None # browser reload 
    
    # Create groups of hosts with the same target folder
    targets = {}
    for hostname in hosts:
        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder) 
        imported_folder = effective.get('imported_folder')
        if imported_folder == None:
            continue
        targets.setdefault(imported_folder, []).append(hostname)

        # Remove target folder information, now that the hosts are
        # at their target position.
        del host['imported_folder']

    # Now handle each target folder
    num_moved = 0
    for imported_folder, hosts in targets.items():
        # Next problem: The folder path in imported_folder refers 
        # to the Alias of the folders, not to the internal file
        # name. And we need to create folders not yet existing.
        target_folder = create_target_folder_from_aliaspath(imported_folder)
        num_moved += move_hosts_to(hosts, target_folder[".path"])
        save_folder(target_folder)
    save_folder(g_folder)
    log_pending(g_folder, "move-hosts", _("Moved %d imported hosts to their original destination.") % num_moved)
    return None, _("Successfully moved %d hosts to their original folder destinations.") % num_moved


def create_target_folder_from_aliaspath(aliaspath):
    # The alias path is a '/' separated path of folder titles.
    # An empty path is interpreted as root path. The actual file
    # name is the host list with the name "Hosts". 
    if aliaspath == "" or aliaspath == "/":
        folder = g_root_folder
    else:
        parts = aliaspath.strip("/").split("/")
        folder = g_root_folder
        while len(parts) > 0: 
            # Look in current folder for subfolder with the target name
            for name, f in folder.get(".folders", {}).items(): 
                if f["title"] == parts[0]:
                    folder = f
                    parts = parts[1:]
                    break
            else: # not found. Create this folder
                name = create_wato_foldername(parts[0], folder)
                new_path = folder[".path"]
                if new_path:
                    new_path += "/"
                new_path += name

                new_folder = {
                    ".name"      : name,
                    ".path"      : new_path,
                    "title"      : parts[0],
                    "attributes" : {}, 
                    ".folders"   : {},
                    ".files"     : {},
                    ".parent"    : folder
                }
                folder[".folders"][name] = new_folder
                g_folders[new_path] = new_folder
                folder = new_folder
                parts = parts[1:]
                save_folder(folder) # make sure, directory is created

    return folder



#   +----------------------------------------------------------------------+
#   |  ____        _ _      ___                      _                     |
#   | | __ ) _   _| | | __ |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _   |
#   | |  _ \| | | | | |/ /  | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |  |
#   | | |_) | |_| | |   <   | || | | \ V /  __/ | | | || (_) | |  | |_| |  |
#   | |____/ \__,_|_|_|\_\ |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |  |
#   |                                                              |___/   |
#   +----------------------------------------------------------------------+
#   | When the user wants to scan the services of multiple hosts at once   |
#   | this function is used. There is no fine-tuning possibility. We       |
#   | simply do something like -I or -II on the list of hosts.             |
#   +----------------------------------------------------------------------+

def mode_bulk_inventory(phase):
    if phase == "title":
        return _("Bulk service detection (inventory)")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.var("_item"):
            how = html.var("how")
            hostname = html.var("_item")
            try:
                counts = check_mk_automation("inventory", [how, hostname])
                result = repr([ 'continue', 1, 0 ] + list(counts)) + "\n"
                result += _("Inventorized %s<br>\n") % hostname
                log_pending(hostname, "bulk-inventory", 
                    _("Inventorized host: %d added, %d removed, %d kept, %d total services") % counts)
            except Exception, e:
                result = repr([ 'failed', 1, 1, 0, 0, 0, 0, ]) + "\n"
                result += _("Error during inventory of %s: %s<br>\n") % (hostname, e)
            html.write(result)
            return ""
        return

    # interactive progress is *not* done in action phase. It
    # renders the page content itself.
    hostnames = get_hostnames_from_checkboxes()

    if html.var("_start"):
        # Start interactive progress
        interactive_progress(
            hostnames,         # list of items
            _("Bulk inventory"),  # title
            [ (_("Total hosts"),      0),
              (_("Failed hosts"),     0), 
              (_("Services added"),   0), 
              (_("Services removed"), 0), 
              (_("Services kept"),    0), 
              (_("Total services"),   0) ], # stats table
            [ ("mode", "folder") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
        )

    else:
        html.begin_form("bulkinventory", None, "POST")
        html.hidden_fields()

        # Mode of action
        html.write(_("<p>You have selected <b>%d</b> hosts for bulk inventory. "
                   "Check_MK inventory will automatically find and configure "
                   "services to be checked on your hosts.</p>") % len(hostnames))
        html.write("<table class=form>")
        html.write("<tr><td class=legend>" + _("Mode") + "</td><td class=content>")
        html.radiobutton("how", "new",     True,  _("Find only new services") + "<br>")
        html.radiobutton("how", "remove",  False, _("Remove obsolete services") + "<br>")
        html.radiobutton("how", "fixall",  False, _("Find new &amp; remove obsolete") + "<br>")
        html.radiobutton("how", "refresh", False, _("Refresh all services (tabula rasa)") + "<br>")
        html.write("</td></tr>")

        # Check type (first we need a Check_MK automation service for getting the list of checktype)
        # html.write("<tr><td class=legend>Checktype</td><td class=content>")
        # selection = check_mk_automation('get-checktypes')
        # html.sorted_select("check_command", [("", "all types")] + [(x,x) for x in selection])
        # html.write("</td></tr>")

        # Start button 
        html.write('<tr><td colspan=2 class="buttons">')
        html.button("_start", _("Start"))
        html.write("</tr>")

        html.write("</table>")

#   +----------------------------------------------------------------------+
#   |                ____        _ _      _____    _ _ _                   |
#   |               | __ ) _   _| | | __ | ____|__| (_) |_                 |
#   |               |  _ \| | | | | |/ / |  _| / _` | | __|                |
#   |               | |_) | |_| | |   <  | |__| (_| | | |_                 |
#   |               |____/ \__,_|_|_|\_\ |_____\__,_|_|\__|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Change the attributes of a number of selected host at once. Also the |
#   | cleanup is implemented here: the bulk removal of explicit attribute  |
#   | values.                                                              |
#   +----------------------------------------------------------------------+

def mode_bulk_edit(phase):
    if phase == "title":
        return _("Bulk edit hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            changed_attributes = collect_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_folder[".hosts"][hostname]
                host.update(changed_attributes)
                log_pending(hostname, "bulk-edit", _("Changed attributes of host %s in bulk mode") % hostname)
            save_folder_and_hosts(g_folder)
            call_hook_hosts_changed(g_folder)
            return "folder"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_folder[".hosts"][hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk edit. You can now change "
               "host attributes for all selected hosts at once. ") % len(hostnames))
    html.write(_("If a select is set to <i>don't change</i> then currenty not all selected "
    "hosts share the same setting for this attribute. If you leave that selection, all hosts "
    "will keep their individual settings.") + "</p>")

    html.begin_form("bulkedit", None, "POST")
    html.write("<table class=form>")
    configure_attributes(hosts, "bulk", parent = g_folder)
    html.write('<tr><td colspan=3 class="buttons">')
    html.button("_save", _("Save &amp; Finish"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


#   +----------------------------------------------------------------------+
#   |      ____        _ _       ____ _                                    |
#   |     | __ ) _   _| | | __  / ___| | ___  __ _ _ __  _   _ _ __        |
#   |     |  _ \| | | | | |/ / | |   | |/ _ \/ _` | '_ \| | | | '_ \       |
#   |     | |_) | |_| | |   <  | |___| |  __/ (_| | | | | |_| | |_) |      |
#   |     |____/ \__,_|_|_|\_\  \____|_|\___|\__,_|_| |_|\__,_| .__/       |
#   |                                                         |_|          |
#   +----------------------------------------------------------------------+
#   | Mode for removing attributes from host in bulk mode.                 |
#   +----------------------------------------------------------------------+

def mode_bulk_cleanup(phase):
    if phase == "title":
        return _("Bulk removal of explicit attributes")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            to_clean = bulk_collect_cleaned_attributes()
            hostnames = get_hostnames_from_checkboxes()
            for hostname in hostnames:
                host = g_folder[".hosts"][hostname]
                num_cleaned = 0
                for attrname in to_clean:
                    num_cleaned += 1
                    if attrname in host:
                        del host[attrname]
                if num_cleaned > 0:
                    log_pending(hostname, "bulk-cleanup", _("Cleaned %d attributes of host %s in bulk mode") % (
                    num_cleaned, hostname))
            save_hosts(g_folder)
            return "folder"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_folder[".hosts"][hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
    "explicit attribute values from hosts. The hosts will then inherit attributes "
    "configured at the host list or folders or simply fall back to the builin "
    "default values.") % len(hostnames))
    html.write("</p>")

    html.begin_form("bulkcleanup", None, "POST")
    html.write("<table class=form>")
    if not bulk_cleanup_attributes(g_folder, hosts):
        html.write("<tr><td class=buttons>")
        html.write(_("The selected hosts have no explicit attributes"))
        html.write("</td></tr>\n")
    else:
        html.write('<tr><td colspan=2 class="buttons">')
        html.button("_save", _("Save &amp; Finish"))
        html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


def bulk_collect_cleaned_attributes():
    to_clean = []
    for attr, topic in host_attributes:
        attrname = attr.name()
        if html.get_checkbox("_clean_" + attrname) == True:
            to_clean.append(attrname)
    return to_clean


def bulk_cleanup_attributes(the_file, hosts):
    num_shown = 0
    for attr, topic in host_attributes:
        attrname = attr.name()

        # only show attributes that at least on host have set
        num_haveit = 0
        for hostname, host in hosts.items():
            if attrname in host:
                num_haveit += 1

        if num_haveit == 0:
            continue

        # If the attribute is mandatory and no value is inherited
        # by file or folder, the attribute cannot be cleaned.
        container = the_file
        is_inherited = False
        while container:
            if "attributes" in container and attrname in container["attributes"]:
                is_inherited = True
                inherited_value = container["attributes"][attrname]
                break
            container = container.get(".parent")


        num_shown += 1

        # Legend and Help
        html.write("<tr><td class=legend>%s" % attr.title())
        if attr.help():
            html.write("<br><i>%s</i>" % attr.help())
        html.write("</td>")
        html.write("<td class=content>")

        if attr.is_mandatory() and not is_inherited:
            html.write(_("This attribute is mandatory and there is no value "
                         "defined in the host list or any parent folder."))
        else:
            html.checkbox("_clean_%s" % attrname, False)
            html.write(" clean this attribute on <b>%s</b> hosts" % 
                (num_haveit == len(hosts) and "all selected" or str(num_haveit)))
        html.write("</td></tr>")

    return num_shown > 0



#   +----------------------------------------------------------------------+
#   |                    _                 __ _ _                          |
#   |                   | |    ___   __ _ / _(_) | ___                     |
#   |                   | |   / _ \ / _` | |_| | |/ _ \                    |
#   |                   | |__| (_) | (_| |  _| | |  __/                    |
#   |                   |_____\___/ \__, |_| |_|_|\___|                    |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Handling of the audit logfiles                                       |
#   +----------------------------------------------------------------------+

def mode_changelog(phase):
    if phase == "title":
        return _("ChangeLog")

    elif phase == "buttons":
        home_button()
        if log_exists("pending") and config.may("wato.activate"):
            html.context_button(_("Activate Changes!"), 
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())]), "apply", True)
        if log_exists("audit") and config.may("wato.auditlog") and config.may("wato.edit"):
            html.context_button(_("Download Audit Log"),
                html.makeuri([("_action", "csv"), ("_transid", html.current_transid())]), "download")
            if config.may("wato.edit"):
                html.context_button(_("Clear Audit Log"),
                    html.makeuri([("_action", "clear"), ("_transid", html.current_transid())]), "trash")

    elif phase == "action":
        if html.var("_action") == "clear":
            config.need_permission("wato.auditlog")
            config.need_permission("wato.edit")
            return clear_audit_log_after_confirm()

        elif html.var("_action") == "csv":
            config.need_permission("wato.auditlog")
            return export_audit_log()

        elif html.check_transaction():
            config.need_permission("wato.activate")
            create_snapshot()
            try:
                check_mk_automation("restart")
                call_hook_activate_changes()
            except Exception, e:
                if config.debug:
                    raise
                else:
                    raise MKUserError(None, "Error executing hooks: %s" % str(e))
            log_commit_pending() # flush logfile with pending actions
            log_audit(None, "activate-config", _("Configuration activated, monitoring server restarted"))
            return None, _("The new configuration has been successfully activated.")

    else:
        pending = parse_audit_log("pending")
        render_audit_log(pending, "pending")

        if config.may("wato.auditlog"):
            audit = parse_audit_log("audit")
            render_audit_log(audit, "audit")
            if len(pending) + len(audit) == 0:
                html.write("<div class=info>" + _("There are no pending or old changes.") + "</div>")
        elif len(pending) == 0:
                html.write("<div class=info>" + _("There are no pending changes.") + "</div>")



def log_entry(linkinfo, action, message, logfilename):
    if type(message) == unicode:
        message = message.encode("utf-8")
    message = message.strip()

    # linkinfo is either a folder, or a hostname or None
    if type(linkinfo) == dict and linkinfo[".path"] in g_folders:
        link = linkinfo[".path"] + ":"
    elif linkinfo == None:
        link = "-"
    elif linkinfo and ".hosts" in g_folder and linkinfo in g_folder[".hosts"]: # hostname in current folder
        link = g_folder[".path"] + ":" + linkinfo
    else:
        link = ":" + linkinfo

    log_file = log_dir + logfilename
    make_nagios_directory(log_dir)
    f = create_user_file(log_file, "ab")
    f.write("%d %s %s %s " % (int(time.time()), link, config.user_id, action))
    f.write(message)
    f.write("\n")


def log_audit(linkinfo, what, message):
    log_entry(linkinfo, what, message, "audit.log")

def log_pending(linkinfo, what, message):
    log_entry(linkinfo, what, message, "pending.log")
    log_entry(linkinfo, what, message, "audit.log")
    need_sidebar_reload()

def log_commit_pending():
    pending = log_dir + "pending.log"
    if os.path.exists(pending):
        os.remove(pending)
    need_sidebar_reload()

def clear_audit_log():
    path = log_dir + "audit.log"
    if os.path.exists(path):
        newpath = path + time.strftime(".%Y-%m-%d")
        if os.path.exists(newpath):
            n = 1
            while True:
                n += 1
                with_num = newpath + "-%d" % n
                if not os.path.exists(with_num):
                    newpath = with_num
                    break
        os.rename(path, newpath)

def clear_audit_log_after_confirm():
    c = wato_confirm(_("Confirm deletion of audit logfile"),
                     _("Do you really want to clear audit logfile?"))
    if c:
        clear_audit_log()
        return None, _("Cleared audit logfile.")
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload 

def parse_audit_log(what):
    path = log_dir + what + ".log"
    if os.path.exists(path):
        entries = []
        for line in file(path):
            line = line.rstrip().decode("utf-8")
            splitted = line.split(None, 4)
            if len(splitted) == 5 and is_integer(splitted[0]):
                splitted[0] = int(splitted[0])
                entries.append(splitted)
        entries.reverse()
        return entries
    return []

def is_integer(i):
    try:
        int(i)
        return True
    except:
        return False

def log_exists(what):
    path = log_dir + what + ".log"
    return os.path.exists(path)

def render_linkinfo(linkinfo):
    if ':' in linkinfo: # folder:host
        path, hostname = linkinfo.split(':', 1)
        if path in g_folders:
            folder = g_folders[path]
            if hostname:
                hosts = load_hosts(folder)
                if hostname in hosts:
                    url = html.makeuri_contextless([("mode", "edithost"), 
                              ("folder", path), ("host", hostname)])
                    title = hostname
                else:
                    return hostname
            else: # only folder
                url = html.makeuri_contextless([("mode", "folder"), ("folder", path)])
                title = g_folders[path]["title"]
        else:
            return linkinfo
    else:
        return ""

    return '<a href="%s">%s</a>' % (url, title)

def get_timerange(t):
    st    = time.localtime(int(t))
    start = int(time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
    end   = start + 86399
    return start, end

def fmt_date(t):
    return time.strftime('%Y-%m-%d', time.localtime(t))

def fmt_time(t):
    return time.strftime('%H:%M:%S', time.localtime(t))

def paged_log(log):
    start = html.var('start', None)
    if not start:
        start = time.time()
    start_time, end_time = get_timerange(int(start))

    previous_log_time = None
    next_log_time     = None
    first_log_index   = None
    last_log_index    = None
    for index, (t, linkinfo, user, action, text) in enumerate(log):
        if t >= end_time:
            # This log is too new
            continue
        elif first_log_index is None \
              and t < end_time \
              and t >= start_time:
            # This is a log for this day. Save the first index
            if first_log_index is None:
                first_log_index = index

                # When possible save the timestamp of the previous log
                if index > 0:
                    next_log_time = int(log[index - 1][0])

        elif t < start_time and last_log_index is None:
            last_log_index = index
            # This is the next log after this day
            previous_log_time = int(log[index][0])
            # Finished!
            break

    if last_log_index is None:
        last_log_index = len(log)

    return log[first_log_index:last_log_index], (start_time, end_time, previous_log_time, next_log_time)

def display_paged((start_time, end_time, previous_log_time, next_log_time)):
    html.write('<div class=paged_controls>')

    html.write(' <b>%s</b> ' % (_('%s to %s') % (fmt_date(start_time),
                                                 fmt_date(end_time))))

    if previous_log_time is not None:
        html.buttonlink(html.makeuri([('start', previous_log_time)]), _("<"),
                        title = '%s: %s' % (_("Older events"), fmt_date(previous_log_time)))
    else:
        html.buttonlink(html.makeuri([]), _("<"), disabled = True)

    html.buttonlink(html.makeuri([('start', get_timerange(int(time.time()))[0])]), _("o"),
                    title = _("Todays events"))

    if next_log_time is not None:
        html.buttonlink(html.makeuri([('start', next_log_time)]), _(">"),
                        title = '%s: %s' % (_("Newer events"), fmt_date(next_log_time)))
    else:
        html.buttonlink(html.makeuri([]), _(">"), disabled = True)
    html.write('</div>')


def render_audit_log(log, what, with_filename = False):
    htmlcode = ''
    if what == 'audit':
        log, times = paged_log(log)
        empty_msg = _("The logfile is empty. No host has been created or changed yet.")
    elif what == 'pending':
        empty_msg = _("No pending changes, monitoring server is up to date.")

    if len(log) == 0:
        htmlcode += "<div class=info>%s</div>" % empty_msg
        return
    elif what == 'audit':
        htmlcode += "<b>" + _("Audit log") + "</b>"
    elif what == 'pending':
        htmlcode += "<h1>" + _("Changes which are not yet activated:") + "</h1>"

    if what == 'audit':
        display_paged(times)

    htmlcode += '<table class="wato auditlog">'
    even = "even"
    for t, linkinfo, user, action, text in log:
        even = even == "even" and "odd" or "even"
        htmlcode += '<tr class="%s0">' % even
        htmlcode += '<td>%s</td>' % render_linkinfo(linkinfo)
        htmlcode += '<td class=nobreak>%s</td>' % fmt_date(float(t))
        htmlcode += '<td class=nobreak>%s</td>' % fmt_time(float(t))
        htmlcode += '<td>%s</td><td width="100%%">%s</td></tr>\n' % \
                  (user, text)
    htmlcode += "</table>"

    if what == 'audit':
        html.write(htmlcode)
        display_paged(times)
    else:
        html.show_warning(htmlcode)

def export_audit_log():
    html.req.content_type = "text/csv; charset=UTF-8"
    filename = 'wato-auditlog-%s_%s.csv' % (fmt_date(time.time()), fmt_time(time.time()))
    html.req.headers_out['Content-Disposition'] = 'attachment; filename=%s' % filename
    titles = (
        _('Date'),
        _('Time'),
        _('Linkinfo'),
        _('User'),
        _('Action'),
        _('Text'),
    )
    html.write(','.join(titles) + '\n')
    for t, linkinfo, user, action, text in parse_audit_log("audit"):
        if linkinfo == '-':
            linkinfo = ''
        html.write(','.join((fmt_date(int(t)), fmt_time(int(t)), linkinfo,
                             user, action, '"' + text + '"')) + '\n')
    return False


#   +----------------------------------------------------------------------+
#   |          _         _                        _   _                    |
#   |         / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __         |
#   |        / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \        |
#   |       / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |       |
#   |      /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This code section deals with the interaction of Check_MK. It is used |
#   | for doing inventory, showing the services of a host, deletion of a   |
#   | host and similar things.                                             |
#   +----------------------------------------------------------------------+

def check_mk_automation(command, args=[], indata=""):
    # Gather the command to use for executing --automation calls to check_mk
    # - First try to use the check_mk_automation option from the defaults
    # - When not set try to detect the command for OMD or non OMD installations
    #   - OMD 'own' apache mode or non OMD: check_mk --automation
    #   - OMD 'shared' apache mode: Full path to the binary and the defaults
    sudoline = None
    if defaults.check_mk_automation:
        commandargs = defaults.check_mk_automation.split()
        cmd = commandargs + [ command, '--' ] + args
    else:
        omd_mode, omd_site = html.omd_mode()
        if not omd_mode or omd_mode == 'own':
            commandargs = [ 'check_mk', '--automation' ]
            cmd = commandargs  + [ command, '--' ] + args
        else: # OMD shared mode
            commandargs = [ 'sudo', '/bin/su', '-', omd_site, '-c', 'check_mk --automation' ]
            cmd = commandargs[:-1] + [ commandargs[-1] + ' ' + ' '.join([ command, '--' ] + args) ]
            sudoline = "%s ALL = (root) NOPASSWD: /bin/su - %s -c check_mk\\ --automation\\ *" % (html.apache_user(), omd_site)

    sudo_msg = ''
    if commandargs[0] == 'sudo':
        if not sudoline:
            if commandargs[1] == '-u': # skip -u USER in /etc/sudoers
                sudoline = "%s ALL = (%s) NOPASSWD: %s *" % (html.apache_user(), commandargs[2], " ".join(commandargs[3:]))
            else:
                sudoline = "%s ALL = (root) NOPASSWD: %s *" % (html.apache_user(), commandargs[0], " ".join(commandargs[1:]))
            
        sudo_msg = ("<p>The webserver is running as user which has no rights on the "
                    "needed Check_MK/Nagios files.<br />Please ensure you have set-up "
                    "the sudo environment correctly. e.g. proceed as follows:</p>\n"
                    "<ol><li>install sudo package</li>\n"
                    "<li>Append the following to the <code>/etc/sudoers</code> file:\n"
                    "<pre># Needed for WATO - the Check_MK Web Administration Tool\n"
                    "Defaults:%s !requiretty\n"
                    "%s\n"
                    "</pre></li>\n"
                    "<li>Retry this operation</li></ol>\n" %
                    (html.apache_user(), sudoline))

    if config.debug:
        log_audit(None, "automation", "Automation: %s" % " ".join(cmd))
    try:
        # This debug output makes problems when doing bulk inventory, because
        # it garbles the non-HTML response output
        # if config.debug:
        #     html.write("<div class=message>Running <tt>%s</tt></div>\n" % " ".join(cmd))
        p = subprocess.Popen(cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception, e:
        if commandargs[0] == 'sudo':
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s<br /><br >%s" % (commandargs[0], e, sudo_msg))
        else:
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s" % (commandargs[0], e))
    p.stdin.write(repr(indata))
    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    if exitcode != 0:
        log_audit(None, "automation", "Automation command %s failed with exit code %d: %s" % (" ".join(cmd), exitcode, outdata))
        raise MKGeneralException("Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>%s" %
              (" ".join(cmd), exitcode, hilite_errors(outdata), sudo_msg))
    try:
        if config.debug:
            log_audit(None, "automation", "Result from automation: %s" % outdata)
        return eval(outdata)
    except Exception, e:
        log_audit(None, "automation", "Automation command %s failed: invalid output: %s" % (" ".join(cmd), outdata)) 
        raise MKGeneralException("Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
                      (" ".join(cmd), e, outdata))



def hilite_errors(outdata):
    return re.sub("\nError: *([^\n]*)", "\n<div class=err>Error: \\1</div>", outdata)




#   +----------------------------------------------------------------------+
#   |               ____                                                   |
#   |              |  _ \ _ __ ___   __ _ _ __ ___  ___ ___                |
#   |              | |_) | '__/ _ \ / _` | '__/ _ \/ __/ __|               |
#   |              |  __/| | | (_) | (_| | | |  __/\__ \__ \               |
#   |              |_|   |_|  \___/ \__, |_|  \___||___/___/               |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Bulk inventory and other longer procedures are separated in single   |
#   | steps and run by an JavaScript scheduler showing a progress bar and  |
#   | buttons for aborting and pausing.                                    |
#   +----------------------------------------------------------------------+

def interactive_progress(items, title, stats, finishvars, timewait, success_stats = [], termvars = []):
    if not termvars:
        termvars = finishvars;
    html.write("<center>")
    html.write("<table class=progress>")
    html.write("<tr><th colspan=2>%s</th></tr>" % title)
    html.write("<tr><td colspan=2 class=log><div id=progress_log></div></td></tr>")
    html.write("<tr><td colspan=2 class=bar>")
    html.write("  <table id=progress_bar><tbody><tr><td class=left></td>"
               "<td class=right></td></tr></tbody></table>")
    html.write("  <div id=progress_title></div>")
    html.write("  <img class=glass src=images/perfometer-bg.png />")
    html.write("</td></tr>")
    html.write("<tr><td class=stats>")
    html.write("  <table>")
    for num, (label, value) in enumerate(stats):
        html.write("    <tr><th>%s</th><td id='progress_stat%d'>%d</td></tr>" % (label, num, value))
    html.write("  </table>")
    html.write("</td>")
    html.write("<td class=buttons>")
    html.jsbutton('progress_pause',    _('Pause'),   'javascript:progress_pause()')
    html.jsbutton('progress_proceed',  _('Proceed'), 'javascript:progress_proceed()',  'display:none')
    html.jsbutton('progress_finished', _('Finish'),  'javascript:progress_end()', 'display:none')
    html.jsbutton('progress_retry',    _('Retry Failed Hosts'), 'javascript:progress_retry()', 'display:none')
    html.jsbutton('progress_restart',  _('Restart'), 'javascript:location.reload()')
    html.jsbutton('progress_abort',    _('Abort'),   'javascript:progress_end()')
    html.write("</td></tr>")
    html.write("</table>")
    html.write("</center>")
    json_items    = '[ %s ]' % ','.join([ "'" + h + "'" for h in items ])
    success_stats = '[ %s ]' % ','.join(map(str, success_stats))
    # Remove all sel_* variables. We do not need them for our ajax-calls.
    # They are just needed for the Abort/Finish links. Those must be converted
    # to POST.
    base_url = html.makeuri([], remove_prefix = "sel_")
    html.javascript(('progress_scheduler("%s", "%s", 50, %s, "%s", %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json_items, html.makeuri(finishvars), success_stats, html.makeuri(termvars),))

#   +----------------------------------------------------------------------+
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Attributes of hosts are based on objects and are extendable via      |
#   | WATO plugins.                                                        |
#   +----------------------------------------------------------------------+
class Attribute:
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self, name=None, title=None, help=None, default_value=None):
        self._name = name
        self._title = title
        self._help = help
        self._default_value = default_value

    # Return the name (= identifier) of the attribute
    def name(self):
        return self._name

    # Return the name of the Nagios configuration variable
    # if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")
    def nagios_name(self):
        return None

    # Return the title to be displayed to the user
    def title(self):
        return self._title

    # Return an optional help text
    def help(self):
        return self._help

    # Return the default value for new hosts
    def default_value(self):
        return self._default_value

    # Render HTML code displaying a value
    def paint(self, value, hostname):
        return "", value

    # Wether or not to show this attribute in tables.
    # This value is set by declare_host_attribute
    def show_in_table(self):
        return self._show_in_table
        
    # Wether or not to show this attribute in the edit form.
    # This value is set by declare_host_attribute
    def show_in_form(self):
        return self._show_in_form

    # Wether or not to make this attribute configurable in
    # files and folders (as defaule value for the hosts)
    def show_in_folder(self):
        return self._show_in_folder

    # Wether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory 
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Render HTML input fields displaying the value and 
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, value):
        pass

    # Create value from HTML variables.     
    def from_html_vars(self):
        return None
    
    # Check if the value entered by the user is valid.
    # This method may raise MKUserError in case of invalid user input.
    def validate_input(self):
        pass

    # If this attribute should be present in Nagios as 
    # a host custom macro, then the value of that macro
    # should be returned here - otherwise None
    def to_nagios(self, value):
        return None

    # Checks if the give value matches the search attributes
    # that are represented by the current HTML variables.
    def filter_matches(self, crit, value, hostname):
        return crit == value


# A simple text attribute. It is stored in 
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self, name, title, help = None, default_value="", mandatory=False, allow_empty=True):
        Attribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory
        self._allow_empty = allow_empty

    def paint(self, value, hostname):
        if not value:
            return "", ""
        else:
            return "", value

    def is_mandatory(self):
        return self._mandatory

    def render_input(self, value):
        if value == None: 
            value = ""
        html.text_input("attr_" + self.name(), value)

    def from_html_vars(self):
        value = html.var_utf8("attr_" + self.name())
        if value == None:
            value = ""
        return value.strip()

    def validate_input(self):
        value = self.from_html_vars()
        if self._mandatory and not value:
            raise MKUserError("attr_" + self.name(), 
                  _("Please specify a value for %s") % self.title())
        if value.strip() == "" and not self._allow_empty:
            raise MKUserError("attr_" + self.name(),
                  _("%s may be missing, if must not be empty if it is set.") % self.title())
                  

    def filter_matches(self, crit, value, hostname):
        if value == None:  # Host does not have this attribute
            value = ""
        return crit.lower() in value.lower() 

# A simple text attribute that is not editable by the user.
# It can be used to store context information from other
# systems (e.g. during an import of a host database from
# another system).
class FixedTextAttribute(TextAttribute): 
    def __init__(self, name, title, help = None):
        TextAttribute.__init__(self, name, title, help, None)
        self._mandatory = False

    def render_input(self, value):
        if value != None:
            html.hidden_field("attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self):
        return html.var("attr_" + self.name())


# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self, name, nag_name, title, help = None, default_value="", mandatory = False, allow_empty=True):
        TextAttribute.__init__(self, name, title, help, default_value, mandatory, allow_empty)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        if value:
            return value.encode("utf-8")
        else:
            return None

# An attribute for selecting one item out of list using
# a drop down box (<select>). Enumlist is a list of
# pairs of keyword / title. The type of value is string.
# In all cases where no value is defined or the value is
# not in the enumlist, the default value is being used.
class EnumAttribute(Attribute):
    def __init__(self, name, title, help, default_value, enumlist):
        Attribute.__init__(self, name, title, help, default_value)
        self._enumlist = enumlist
        self._enumdict = dict(enumlist)

    def paint(self, value, hostname):
        return "", self._enumdict.get(value, self.default_value())

    def render_input(self, value):
        html.select("attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self):
        return html.var("attr_" + self.name(), self.default_value())


# A selection dropdown for a host tag
class HostTagAttribute(Attribute):
    def __init__(self, tag_definition):
        tag_id, title, self._taglist = tag_definition
        name = "tag_" + tag_id
        if len(self._taglist) == 1:
            def_value = None
        else:
            def_value = self._taglist[0][0]
        Attribute.__init__(self, name, title, "", def_value)

    def paint(self, value, hostname):
        if len(self._taglist) == 1:
            title = self._taglist[0][1]
            if value:
                return "", title
            else:
                return "", "%s %s" % (_("not"), title)
        for entry in self._taglist:
            if value == entry[0]:
                return "", entry[1]
        return "", "" # Should never happen, at least one entry should match
                      # But case could occur if tags definitions have been changed.

    def render_input(self, value):
        # Tag groups with just one entry are being displayed
        # as checkboxes
        choices = [e[:2] for e in self._taglist]
        varname = "attr_" + self.name()
        if len(choices) == 1:
            html.checkbox(varname, value != None)
            html.write(" " + choices[0][1])
        else:
            html.select(varname, choices, value)

    def from_html_vars(self):
        varname = "attr_" + self.name()
        if len(self._taglist) == 1:
            if html.get_checkbox(varname):
                return self._taglist[0][0]
            else:
                return None
        else:
            value = html.var(varname)
            if not value:
                value = None
            return value
    
    # Special function for computing the setting of a specific
    # tag group from the total list of tags of a host
    def get_tag_value(self, tags):
        for entry in self._taglist:
            if entry[0] in tags:
                return entry[0]
        return None

    # Return list of host tags to set (handles
    # secondary tags)
    def get_tag_list(self, value):
        for entry in self._taglist:
            if entry[0] == value:
                if len(entry) >= 3:
                    taglist = [ value ] + entry[2]
                else:
                    taglist =  [ value ]
                if taglist[0] == None:
                    taglist = taglist[1:]
                return taglist
        return [] # No matching tag


# Attribute needed for folder permissions
class ContactGroupsAttribute(Attribute):
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self):
        url = "wato.py?mode=rulesets"
        Attribute.__init__(self, "contactgroups", _("Permissions"), 
          _("Only members of the contact groups listed here have WATO permission "
            "to the host / folder. If you want, you can make those contact groups "
            "automatically also <b>monitoring contacts</b>. This is completely "
            "optional. Assignment of host and services to contact groups "
            "can be done by <a href='%s'>rules</a> as well.") % url)
        self._default_value = ( True, [] ) 
        self._contactgroups = None
        self._users = None
        self._loaded_at = None

    def paint(self, value, hostname):
        texts = []
        use, cgs = value
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1], b[1]))
        for name, alias in items:
            if name in cgs:
                texts.append(alias and alias or name)
        result = ", ".join(texts)
        if texts:
            result += "<span title='%s'><b>*</b></span>" % \
                  _("These contact groups are also used in the monitoring configuration.")
        return "", result

    def render_input(self, value):
        # Only show contact groups I'm currently in and contact
        # groups already listed here. 
        use, cgs = value
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1], b[1]))
        for name, alias in items:
            html.checkbox(self._name + "_" + name, name in cgs)
            html.write(" %s<br>" % (alias and alias or name))
        html.write("<hr>")
        html.checkbox(self._name + "_use", use)
        html.write( " " + _("Add these contact groups to the host's contact groups in the monitoring configuration"))

    def load_data(self): 
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)

        self._contactgroups = load_group_information().get("contact", {})

    def from_html_vars(self): 
        cgs = []
        self.load_data()
        for name in self._contactgroups:
            if html.get_checkbox(self._name + "_" + name):
                cgs.append(name)
        return html.get_checkbox(self._name + "_use"), cgs

    def filter_matches(self, crit, value, hostname):
        for c in crit[1]:
            if c in value[1]:
                return True
        return False


# Declare an attribute for each host tag configured in multisite.mk
# Also make sure that the tags are reconfigured as soon as the
# configuration of the tags has changed.
configured_host_tags = None
def declare_host_tag_attributes():
    global configured_host_tags
    global host_attributes

    if configured_host_tags != config.wato_host_tags:
        # Remove host tag attributes from list, if existing
        host_attributes = [ (attr, topic) for (attr, topic) in host_attributes if not attr.name().startswith("tag_") ]

        # Also remove those attributes from the speed-up dictionary host_attribute
        for attr in host_attribute.values():
            if attr.name().startswith("tag_"):
                del host_attribute[attr.name()]

        for entry in config.wato_host_tags:
            declare_host_attribute(HostTagAttribute(entry), 
                show_in_table = False, show_in_folder = True, topic = _("Host tags"))

        configured_host_tags = config.wato_host_tags

def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    attr = host_attribute[attrname]
    del host_attribute[attrname]
    global host_attributes
    host_attributes = [ ha for ha in host_attributes if ha[0] != attr ]


# Global datastructure holding all attributes (in a defined order)
# as pairs of (attr, topic). Topic is the title under which the 
# attribute is being displayed. All builtin attributes use the
# topic None. As long as only one topic is used, no topics will
# be displayed. They are useful if you have a great number of 
# custom attributes.
host_attributes = []

# Dictionary for quick access
host_attribute = {}

# Declare attributes with this method
def declare_host_attribute(a, show_in_table = True, show_in_folder = True, topic = None, show_in_form = True):
    host_attributes.append((a, topic))
    host_attribute[a.name()] = a
    a._show_in_table  = show_in_table
    a._show_in_folder = show_in_folder
    a._show_in_form   = show_in_form

# Read attributes from HTML variables
def collect_attributes(do_validate = True):
    host = {}
    for attr, topic in host_attributes:
        attrname = attr.name()
        if not html.var("_change_%s" % attrname, False):
            continue

        if do_validate:
            attr.validate_input()
        host[attrname] = attr.from_html_vars()
    return host

def have_folder_attributes():
    for attr, topic in host_attributes:
        if attr.show_in_folder():
            return True
    return False

# Show HTML form for editing attributes. for_what can be:
# "host"   -> normal host edit dialog
# "folder" -> properies of folder or file
# "search" -> search dialog
# "bulk"   -> bulk change
# parent: The parent folder of the objects to configure
# myself: For mode "folder" the folder itself or None, if we edit a new folder
#         This is needed for handling mandatory attributes.
def configure_attributes(hosts, for_what, parent, myself=None, without_attributes = []):
    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    topics = []
    for attr, topic in host_attributes:
        if topic not in topics and attr.show_in_form():
            topics.append(topic)

    for topic in topics:
        if len(topics) > 1:
            if topic == None:
                title = _("Basic settings")
            else:
                title = topic
            if topic == topics[0]:
                html.write("</table>")

            html.begin_foldable_container("wato_attributes", title, 
                                          topic == None, title, indent = "form")
            html.write('<table class="form nomargin">')

        for attr, atopic in host_attributes:
            if atopic != topic:
                continue
            attrname = attr.name()
            if attrname in without_attributes:
                continue # e.g. needed to skip ipaddress in CSV-Import

            # Skip hidden attributes
            if not attr.show_in_form():
                continue

            # In folder not all attributes are shown
            if for_what == "folder" and not attr.show_in_folder():
                continue

            # "bulk": determine, if this attribute has the same setting for all hosts.
            values = []
            num_haveit = 0
            for hostname, host in hosts.items():
                if attrname in host:
                    num_haveit += 1
                    if host[attrname] not in values:
                        values.append(host[attrname])

            # The value of this attribute is unique amongst all hosts if
            # either no host has a value for this attribute, or all have
            # one and have the same value
            unique = num_haveit == 0 or (len(values) == 1 and num_haveit == len(hosts))

            if for_what in [ "host", "folder" ]:
                host = hosts.values()[0]

            # Collect information about attribute values inherited from folder.
            # This information is just needed for informational display to the user.
            # This does not apply in "search" mode. 
            inherited_from = None
            inherited_value = None
            has_inherited = False

            if for_what == "host":
                url = make_link_to([("mode", "editfolder")], g_folder)

            container = parent
            while container:
                if attrname in container.get("attributes", {}):
                    url = make_link_to([("mode", "editfolder")], container)
                    inherited_from = _("Inherited from ") + '<a href="%s">%s</a>' % (url, container["title"])
                    inherited_value = container["attributes"][attrname]
                    has_inherited = True
                    break

                container = container.get(".parent")
                what = "folder"

            if not container: # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
                inherited_value = attr.default_value()

            # Legend and Help
            html.write("<tr><td class=legend><h3>%s</h3>" % attr.title())
            if attr.help():
                html.write("<i>%s</i>" % attr.help())
            html.write("</td>")

            # Checkbox for activating this attribute

            # Determine current state of visibility: If the form has already been submitted (i.e. search
            # or input error), then we take the previous state of the box. In search mode we make those
            # boxes active that have an empty string as default value (simple text boxed). In bulk
            # mode we make those attributes active that have an explicitely set value over all hosts.
            # In host and folder mode we make those attributes active that are currently set.

            # Also determine, if the attribute can be switched off at all. Problematic here are
            # mandatory attributes. We must make sure, that at least one folder/file/host in the
            # chain defines an explicit value for that attribute. If we show a host and no folder/file
            # inherits an attribute to that host, the checkbox will be always active and locked.
            # The same is the case if we show a file/folder and at least one host below this
            # has not set that attribute. In case of bulk edit we never lock: During bulk edit no
            # attribute ca be removed anyway.

            checkbox_name = "_change_%s" % attrname
            cb = html.get_checkbox(checkbox_name)
            force_entry = False

            # first handle mandatory cases
            if for_what == "folder" and attr.is_mandatory() \
                and myself \
                and some_host_hasnt_set(myself, attrname) \
                and not has_inherited:
                force_entry = True
                active = True
            elif for_what == "host" and attr.is_mandatory() and not has_inherited:
                    force_entry = True
                    active = True
            elif cb != None:
                active = cb # get previous state of checkbox
            elif for_what == "search":
                active = attr.default_value() == "" # show empty text search fields always
            elif for_what == "bulk":
                active = unique and len(values) > 0
            elif for_what == "folder":
                active = attrname in host
            else: # "host"
                active = attrname in host

            html.write('<td class=checkbox>')
            if force_entry:
                html.write("<input type=checkbox name=\"ignored_%s\" CHECKED DISABLED></div>" % checkbox_name)
                html.hidden_field(checkbox_name, "on")
            else:
                html.checkbox(checkbox_name, active, 
                    onclick = "wato_toggle_attribute(this, '%s');" % attrname ) # Only select if value is unique
            html.write("</td>")

            # Now comes the input fields and the inherited / default values
            # as two DIV elements, one of which is visible at one time.
            html.write('<td class=content>')

            # DIV with the input elements
            html.write('<div id="attr_entry_%s" style="%s">' 
              % (attrname, (not active) and "display: none" or ""))
            if len(values) == 1:
                defvalue = values[0]
            else:
                defvalue = attr.default_value()
            attr.render_input(defvalue)
            html.write("</div>")

            # DIV with actual / inherited / default value
            html.write('<div class="inherited" id="attr_default_%s" style="%s">' 
              % (attrname, active and "display: none" or ""))

            # in bulk mode we show inheritance only if *all* hosts inherit
            if for_what == "bulk":
                if num_haveit == 0:
                    html.write("<h3>" + inherited_from + "</h3>")
                    value = inherited_value
                elif not unique:
                    html.write(_("<i>This value differs between the selected hosts.</i>")) 
                else:
                    value = values[0]

            elif for_what in [ "host", "folder" ]:
                html.write("<h3>" + inherited_from + "</h3>")
                value = inherited_value

            if for_what != "search" and not (for_what == "bulk" and not unique):
                tdclass, content = attr.paint(value, "")
                if not content:
                    content = "<i>" + _("(empty)") + "</i>"
                html.write(content)

            html.write("</div>")
            
            html.write("</td></tr>\n")

        if len(topics) > 1:
            html.write("</table>")
            html.end_foldable_container()
            if topic == topics[-1]:
                html.write('<table class="form nomargin">')


# Check if at least one host in a folder (or its subfolders)
# has not set a certain attribute. This is needed for the validation
# of mandatory attributes.
def some_host_hasnt_set(folder, attrname):
    # Check subfolders
    for subfolder in folder[".folders"].values():
        # If the attribute is not set in the subfolder, we need
        # to check all hosts and that folder.
        if attrname not in subfolder["attributes"] \
            and some_host_hasnt_set(subfolder, attrname):
            return True

    # Check hosts in this folder
    load_hosts(folder) # make sure hosts are loaded
    for host in folder[".hosts"].values():
        if attrname not in host:
            return True

    return False

# Compute effective (explicit and inherited) attributes
# for a host. This returns a dictionary with a value for
# each host attribute
def effective_attributes(host, folder):
    if host:
        chain = [ host ]
    else:
        chain = [ ]
    while folder:
        chain.append(folder.get("attributes", {}))
        folder = folder.get(".parent")

    eff = {}
    for a in chain[::-1]:
        eff.update(a)

    # now add default values of attributes for all missing values
    for attr, topic in host_attributes:
        attrname = attr.name()
        if attrname not in eff:
            eff.setdefault(attrname, attr.default_value())

    return eff
    

#   +----------------------------------------------------------------------+
#   |           ____                        _           _                  |
#   |          / ___| _ __   __ _ _ __  ___| |__   ___ | |_ ___            |
#   |          \___ \| '_ \ / _` | '_ \/ __| '_ \ / _ \| __/ __|           |
#   |           ___) | | | | (_| | |_) \__ \ | | | (_) | |_\__ \           |
#   |          |____/|_| |_|\__,_| .__/|___/_| |_|\___/ \__|___/           |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Mode for backup/restore/creation of snapshots                        |
#   +----------------------------------------------------------------------+

def mode_snapshot(phase):
    if phase == "title":
        return _("Backup/Restore")
    elif phase == "buttons":
        home_button()
        changelog_button()
        html.context_button(_("Create Snapshot"), 
                make_action_link([("mode", "snapshot"),("_create_snapshot","Yes")]), "snapshot")
        return
    elif phase == "action":
        if html.has_var("_download_file"):
            download_file = html.var("_download_file")
            if not download_file.startswith('wato-snapshot') and download_file != 'latest':
                raise MKUserError(None, _("Invalid download file specified"))

            # Find the latest snapshot file
            if download_file == 'latest':
                snapshots = os.listdir(snapshot_dir)
                if not snapshots:
                    return False
                download_file = snapshots[-1]

            download_file = os.path.join(snapshot_dir, download_file)
            if os.path.exists(download_file):
                html.req.headers_out['Content-Disposition'] = 'Attachment; filename=' + download_file
                html.req.headers_out['content_type'] = 'application/x-tar'
                html.write(open(download_file).read())
                return False

        # create snapshot
        elif html.has_var("_create_snapshot"):
            if html.check_transaction():
                create_snapshot()
                return None, _("Snapshot created.")
            else:
                return None
        # upload snapshot
        elif html.has_var("_upload_file"):
            if html.var("_upload_file") == "":
                raise MKUserError(None, _("You need to select a file for upload"))

                return None
            if html.check_transaction():
                restore_snapshot(None, html.var('_upload_file'))
                return None, _("Successfully uploaded configuration.")
            else:
                return None
        # delete file
        elif html.has_var("_delete_file"):
            delete_file = html.var("_delete_file")
            c = wato_confirm(_("Confirm delete snapshot"),
                             _("Are you sure you want to delete the snapshot <br><br>%s?") %
                                delete_file
                            )
            if c:
                # FIXME: kein join verwenden
                os.remove(os.path.join(snapshot_dir, delete_file))
                return None, _("Snapshot deleted.")
            elif c == False: # not yet confirmed
                return ""
            else:
                return None  # browser reload
        # restore snapshot
        elif html.has_var("_restore_snapshot"):
            snapshot_file = html.var("_restore_snapshot")
            c = wato_confirm(_("Confirm restore snapshot"),
                             _("Are you sure you want to restore the snapshot <br><br>%s ?") %
                                snapshot_file
                            )
            if c:
                restore_snapshot(snapshot_file)
                return None, _("Snapshot restored.")
            elif c == False: # not yet confirmed
                return ""
            else:
                return None  # browser reload
        return False
    else:
        snapshots = []
        if os.path.exists(snapshot_dir):
            for f in os.listdir(snapshot_dir):
                snapshots.append(f)
        snapshots.sort(reverse=True)

        if len(snapshots) == 0:
            html.write("<div class=info>" + _("There are no snapshots available.") + "</div>")
        else:
            html.write('<table class=data>')
            html.write('<h3>' + _("Snapshots") + '</h3>')

            odd = "odd"
            for name in snapshots:
                odd = odd == "odd" and "even" or "odd"
                html.write('<tr class="data %s0"><td>' % odd)
                html.buttonlink(make_action_link([("mode","snapshot"),("_restore_snapshot", name)]), _("Restore"))
                html.buttonlink(make_action_link([("mode","snapshot"),("_delete_file", name)]), _("Delete"))
                html.write("<td>")
                html.write('<a href="%s">%s</a>' % (make_action_link([("mode","snapshot"),("_download_file", name)]), name))
            html.write('</table>')

        html.write("<h3>" + _("Restore from uploaded file") + "</h3>")
        html.begin_form("upload_form", None, "POST")
        html.upload_file("_upload_file")
        html.button("upload_button", _("Restore from file"), "submit")
        html.hidden_fields()
        html.end_form()


def create_snapshot():
    if not os.path.exists(snapshot_dir):
       os.mkdir(snapshot_dir)

    snapshot_name = "wato-snapshot-%s.tar.gz" %  \
                    time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    tar = tarfile.open(snapshot_dir + snapshot_name,"w:gz")

    len_abs = len(root_dir)
    for root, dirs, files in os.walk(defaults.check_mk_configdir):
        for filename in files:
            tar.add(root + "/" + filename, root[len_abs:] + "/" + filename)
    tar.close()

    log_audit(None, "snapshot-created", _("Created snapshot %s") % snapshot_name)

    # Maintenance, remove old snapshots
    snapshots = []
    for f in os.listdir(snapshot_dir):
        snapshots.append(f)
    snapshots.sort(reverse=True)
    while len(snapshots) > config.wato_max_snapshots:
        log_pending(None, "snapshot-removed", _("Removed snapshot %s") % snapshots[-1])
        os.remove(snapshot_dir + snapshots.pop())

def restore_snapshot( filename, tarstream = None ):
    if not os.path.exists(snapshot_dir):
       os.mkdir(snapshot_dir)

    delete_root_dir()
    if filename:
        if not os.path.exists(snapshot_dir + filename):
            raise MKGeneralException(_("Snapshot does not exist %s" % filename))
        snapshot = tarfile.open(snapshot_dir + filename, "r:gz")
    elif tarstream:
        stream = StringIO.StringIO()
        stream.write(tarstream)
        stream.seek(0)
        snapshot = tarfile.open(None, "r:gz", stream)
    else:
        return

    snapshot.extractall(root_dir)
    snapshot.close()
    log_pending(None, "snapshot-restored", _("Restored snapshot %s") % (filename or _('from uploaded file')))

def delete_root_dir():
    if not "/conf.d/" in root_dir:
        raise MKGeneralException("ERROR: config directory seems incorrect. check_mk_configdir %s" % defaults.check_mk_configdir)
    shutil.rmtree(root_dir)


#   +----------------------------------------------------------------------+
#   |       __     __    _              _____    _ _ _                     |
#   |       \ \   / /_ _| |_   _  ___  | ____|__| (_) |_ ___  _ __         |
#   |        \ \ / / _` | | | | |/ _ \ |  _| / _` | | __/ _ \| '__|        |
#   |         \ V / (_| | | |_| |  __/ | |__| (_| | | || (_) | |           |
#   |          \_/ \__,_|_|\__,_|\___| |_____\__,_|_|\__\___/|_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The value editor is used in the configuration and rules module for   |
#   | editing single values (e.g. configuration parameter for main.mk or   |
#   | check parameters).                                                   |
#   +----------------------------------------------------------------------+

# Abstract base class of all value declaration classes.
class ValueSpec:
    def __init__(self, **kwargs):
        self._title         = kwargs.get("title")
        self._help          = kwargs.get("help")
        if "default_value" in kwargs:
            self._default_value = kwargs.get("default_value")

    def title(self): 
        return self._title

    def help(self):
        return self._help

    # Create HTML-form elements that represent a given
    # value and let the user edit that value. The varprefix
    # is prepended to the HTML variable names and is needed
    # in order to make the variable unique in case that another
    # Value of the same type is being used as well.
    def render_input(self, varprefix, value):
        pass

    # Sets the input focus (cursor) into the most promiment
    # field of the HTML code previously rendered with render_input()
    def set_focus(self, varprefix):
        html.set_focus(varprefix)

    # Create a canonical, minimal, default value that 
    # matches the datatype of the value specification and
    # fullfills also data validation.
    def canonical_value(self):
        return None

    # Return a default value for this variable. This
    # is optional and only used in the value editor
    # for same cases where the default value is known.
    def default_value(self):
        try:
            return self._default_value
        except:
            return self.canonical_value()

    # Creates a text-representation of the value that can be
    # used in tables and other contextes. It is to be read 
    # by the user and need not to be parsable.
    def value_to_text(self, value):
        return repr(value)

    # Create a value from the current settings of the
    # HTML variables. This function must also check the validity
    # and may raise a MKUserError in case of invalid set variables.
    def from_html_vars(self, varprefix):
        return None

    # Check if a given value matches the
    # datatype of described by this class. This method will
    # be used by cmk -X on the command line in order to
    # validate main.mk (some happy day in future)
    def validate_datatype(self, value, varprefix):
        pass

    # Check if a given value is within the ranges that are
    # allowed for this type of value. This function should
    # assume that the data type is valid (either because it
    # has been returned by from_html_vars() or because it has
    # been checked with validate_datatype()).
    def validate_value(self, value, varprefix):
        pass

# A fixed non-editable value, e.g. to be use in "Alternative"
class FixedValue(ValueSpec):
    def __init__(self, value, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._value = value
        self._totext = kwargs.get("totext")

    def canonical_value(self):
        return self._value

    def render_input(self, varprefix, value):
        html.write(self.value_to_text(value))

    def value_to_text(self, value):
        if self._totext != None:
            return self._totext
        else:
            return self.title()

    def from_html_vars(self, varprefix):
        return self._value

    def validate_datatype(self, value, varprefix):
        if not self._value == value:
            raise MKUserError(varprefix, _("Invalid value, must be '%r' but is '%r'" % (self._value, value)))

    def validate_value(self, value, varprefix):
        self.validate_datatype(value, varprefix)
        

# Editor for a single integer
class Integer(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size     = kwargs.get("size", 5)
        self._minvalue = kwargs.get("minvalue") 
        self._maxvalue = kwargs.get("maxvalue")
        self._label    = kwargs.get("label")
        self._unit     = kwargs.get("unit", "")
        if "size" not in kwargs and "maxvalue" in kwargs:
            self._size = 1 + int(math.log10(self._maxvalue))

    def canonical_value(self):
        if self._minvalue:
            return self._minvalue
        else:
            return 0

    def render_input(self, varprefix, value):
        html.number_input(varprefix, str(value), size = self._size)
        if self._label or self._unit:
            html.write(" ")
            if self._label:
                html.write(self._label)
            elif self._unit:
                html.write(self._unit)

    def from_html_vars(self, varprefix):
        try:
            return int(html.var(varprefix))
        except:
            raise MKUserError(varprefix, 
                  _("The text <b><tt>%s</tt></b> is not a valid integer number." % html.var(varprefix)))

    def value_to_text(self, value):
        text = str(value)
        if self._unit:
            text += " " + self._unit
        return text

    def validate_datatype(self, value, varprefix): 
        if type(value) != int:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type int") % (type(value)))
 
    def validate_value(self, value, varprefix):
        if self._minvalue != None and value < self._minvalue:
            raise MKUserError(varprefix, _("%s is too low. The minimum allowed value is %s." % (
                                     value, self._minvalue)))
        if self._maxvalue != None and value > self._maxvalue:
            raise MKUserError(varprefix, _("%s is too high. The maximum allowed value is %s." % (
                                     value, self._maxvalue)))

# Editor for a line of text
class TextAscii(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size     = kwargs.get("size", 30)
        self._allow_empty = kwargs.get("allow_empty", True)

    def canonical_value(self):
        return ""

    def render_input(self, varprefix, value):
        html.text_input(varprefix, str(value), size = self._size)

    def value_to_text(self, value):
        return value

    def from_html_vars(self, varprefix):
        return html.var(varprefix, "").strip()

    def validate_datatype(self, value, varprefix): 
        if type(value) != str:
            raise MKUserError(varprefix, _("The value must be of type str, but it has type %s") % type(value)) 

    def validate_value(self, value, varprefix):
        if not self._allow_empty and value == "":
            raise MKUserError(varprefix, _("An empty value is not allowed here."))

class TextUnicode(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)

    def from_html_vars(self, varprefix):
        return html.var_utf8(varprefix, "").strip()

    def validate_datatype(self, value, varprefix): 
        if type(value) not in [ str, unicode ]:
            raise MKUserError(varprefix, _("The value must be of type str or unicode, but it has type %s") % type(value)) 


# A variant of TextAscii() that validates a path to a filename that 
# lies in an existing directory.
class Filename(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        if "default" in kwargs:
            self._default_path = kwargs["default"]
        else:
            self._default_path = "/tmp/foo"

    def canonical_value(self):
        return self._default_path

    def validate_value(self, value, varprefix):
        if len(value) == 0:
            raise MKUserError(varprefix, _("Please enter a filename."))
        
        if value[0] != "/":
            raise MKUserError(varprefix, _("Sorry, only absolute filenames are allowed. "
                                           "Your filename must begin with a slash."))
        if value[-1] == "/":
            raise MKUserError(varprefix, _("Your filename must not end with a slash.")) 

        dir = value.rsplit("/", 1)[0]
        if not os.path.isdir(dir):
            raise MKUserError(varprefix, _("The directory %s does not exist or is not a directory." % dir))

        # Write permissions to the file cannot be checked here since we run with Apache
        # permissions and the file might be created with Nagios permissions (on OMD this
        # is the same, but for others not)


# Same but for floating point values
class Float(Integer):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)
    
    def canonical_value(self):
        return float(Integer.canonical_value(self))

    def from_html_vars(self, varprefix):
        try:
            return float(html.var(varprefix))
        except:
            raise MKUserError(varprefix, 
            _("The text <b><tt>%s</tt></b> is not a valid floating point number." % html.var(varprefix)))

    def validate_datatype(self, value, varprefix): 
        if type(value) != float:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type float") % (type(value)))


class Percentage(Float):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)
        if "min_value" not in kwargs:
            self._minvalue = 0.0
        if "max_value" not in kwargs:
            self._maxvalue = 101.0
        if "unit" not in kwargs:
            self._unit = "%"

    def value_to_text(self, value):
        return "%.1f%%" % value


class Checkbox(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs) 
        self._label = kwargs.get("label")

    def canonical_value(self):
        return False

    def render_input(self, varprefix, value):
        html.checkbox(varprefix, value)
        if self._label:
            html.write(" %s" % self._label)

    def value_to_text(self, value):
        return value and _("on") or _("off")

    def from_html_vars(self, varprefix):
        if html.var(varprefix):
            return True
        else:
            return False

    def validate_datatype(self, value, varprefix): 
        if type(value) != bool:
            raise MKUserError(varprefix, _("The value has type %s, but must be either True or False") % (type(value))) 

# A type-save dropdown choice
class DropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs["choices"]

    def canonical_value(self):
        return self._choices[0][0]

    def render_input(self, varprefix, value):
        # Convert values from choices to keys 
        defval = "0"
        options = []
        for n, (val, title) in enumerate(self._choices):
            options.append((str(n), title))
            if val == value:
                defval = str(n)
        html.select(varprefix, options, defval)

    def value_to_text(self, value):
        for val, title in self._choices:
            if value == val:
                return title

    def from_html_vars(self, varprefix):
        sel = html.var(varprefix)
        for n, (val, title) in enumerate(self._choices):
            if sel == str(n):
                return val
        return self._choices[0][0] # can only happen if user garbled URL

    def validate_datatype(self, value, varprefix): 
        for val, title in self._choices:
            if val == value: 
                return
        raise MKUserError(varprefix, _("Invalid value %s, must be in %s") % 
            ", ".join([v for (v,t) in self._choices]))

# Represents a dict of dicts, which is dynamic
###class DictionaryTable(ValueSpec):
###    def __init__(self, key, elements, **kwargs):
###        ValueSpec.__init__(self, **kwargs)
###        self._key = key
###        self._elements = elements
###        # _value_vs must have variable _elements
###
###    def canonical_value(self):
###        return {}
###
###    def render_input(self, varprefix, value):
###        html.write("<table class=data>") 
###        html.write("<tr>")
###        html.write("<th>%s</th>\n" % self._key.title())
###        for elkey, elem in self._elements:
###            html.write("<th>%s</th>\n" % elem.title())
###        html.write("</tr>")
###        odd = "even"
###        for nr, (key, val) in enumerate(value.items()): 
###            vp = "%s_%d" % (varprefix, nr)
###            html.write("<tr>")
###            odd = odd == "odd" and "even" or "odd" 
###            html.write('<tr class="data %s0">' % odd)
###            html.write("<td>")
###            self._key.render_input(vp + "_key", key)
###            html.write("</td>")
###            for nnr, (elkey, elem) in enumerate(self._elements):
###                html.write("<td>")
###                elem.render_input("%s_%d" % (vp, nnr), val.get(elkey))
###                html.write("</td>")
###            html.write("</tr>")
###        html.write("</table>")
###
###    def value_to_text(self, value): 
###        texts = []
###        for key, val in value.items():
###            text = "%s: " % self._key.value_to_text(key)
###            settings = []
###            for elkey, elem in self._elements:  
###                settings.append("%s=%s" % (elkey, elem.value_to_text(val.get(elkey))))
###            text += ";".join(settings)
###            texts.append(text) 
###        return ", ".join(texts)
###
###    def from_html_vars(self, varprefix):
###        value = {}
###        nr = 0
###        while True: 
###            vp = "%s_%d" % (varprefix, nr)
###            if not html.has_var(vp + "_key"):
###                break
###            keyval = self._key.from_html_vars(vp + "_key")
###            element = {}
###            value[keyval] = element
###            for nnr, (elkey, elem) in enumerate(self._elements):
###                elvalue = elem.from_html_vars("%s_%d" % (vp, nnr))
###                element[elkey] = elvalue
###            nr += 1
###        return value
###
###
###    def validate_datatype(self, value, varprefix): 
###        pass
###
###    def validate_value(self, value, varprefix): 
###        pass



# A list of checkboxes representing a list of values
class ListChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs.get("choices")
        self._columns = kwargs.get("columns", 1)
        self._loaded_at = None

    # In case of overloaded functions with dynamic elements
    def load_elements(self):
        if self._choices:
            self._elements = self._choices
            return

        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def canonical_value(self):
        return []

    def render_input(self, varprefix, value):
        self.load_elements()
        html.write("<table>")
        for nr, (key, title) in enumerate(self._elements):
            if nr % self._columns == 0:
                if nr > 0:
                    html.write("</tr>")
                html.write("<tr>")
            html.write("<td>")
            html.checkbox("%s_%d" % (varprefix, nr), key in value)
            html.write("&nbsp;%s</td>\n" % title)
        html.write("</tr></table>")

    def value_to_text(self, value): 
        self.load_elements()
        d = dict(self._elements)
        return ", ".join([ str(d.get(v,v)) for v in value ])

    def from_html_vars(self, varprefix):
        self.load_elements()
        value = []

        for nr, (key, title) in enumerate(self._elements):
            if html.get_checkbox("%s_%d" % (varprefix, nr)):
                value.append(key)
        return value

    def validate_datatype(self, value, varprefix):
        self.load_elements()
        if type(value) != list:
            raise MKUserError(varprefix, _("The datatype must be list, but is %s") % type(value)) 
        d = dict(self._elements)
        for v in value:
            if v not in d:
                raise MKUserError(varprefix, _("%s is not an allowed value") % v)



# A type-save dropdown choice with one extra field that
# opens a further value spec for entering an alternative
# Value.
class OptionalDropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs["choices"]
        self._explicit = kwargs["explicit"] 
        self._otherlabel = kwargs.get("otherlabel", _("Other"))

    def canonical_value(self):
        return self._explicit.canonical_value()

    def value_is_explicit(self, value):
        return value not in [ c[0] for c in self._choices ]

    def render_input(self, varprefix, value):
        defval = "other"
        options = []
        for n, (val, title) in enumerate(self._choices):
            options.append((str(n), title))
            if val == value:
                defval = str(n)
        options.append(("other", self._otherlabel))
        html.select(varprefix, options, defval, attrs={"style":"float:left;"}, 
                    onchange="wato_toggle_dropdown(this, '%s_ex');" % varprefix )

        if html.form_submitted():
            div_is_open = html.var(varprefix) == "other"
        else:
            div_is_open = self.value_is_explicit(value)

        html.write('<div id="%s_ex" style="white-space: nowrap; %s">' % (
            varprefix, not div_is_open and "display: none;" or ""))
        html.write("&nbsp;&nbsp;&nbsp;") 
        self._explicit.render_input(varprefix + "_ex", value)
        html.write("</div>")

    def value_to_text(self, value):
        return self._explicit.value_to_text(value)

    def from_html_vars(self, varprefix):
        sel = html.var(varprefix)
        if sel == "other":
            return self._explicit.from_html_vars(varprefix + "_ex")

        for n, (val, title) in enumerate(self._choices):
            if sel == str(n):
                return val
        return self._choices[0][0] # can only happen if user garbled URL

    def validate_value(self, value, varprefix):
        if self.value_is_explicit(value):
            self._explicit.validate_value(value, varprefix)
        # else valid_datatype already has made the job

    def validate_datatype(self, value, varprefix): 
        for val, title in self._choices:
            if val == value: 
                return
        self._explicit.validate_datatype(self, value, varprefix + "_ex")



# Make a configuration value optional, i.e. it may be None.
# The user has a checkbox for activating the option. Example:
# debug_log: it is either None or set to a filename.
class Optional(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = valuespec
        self._label = kwargs.get("label")
        self._negate = kwargs.get("negate", False)
        self._none_label = kwargs.get("none_label", _("(unset)"))
        self._sameline = kwargs.get("sameline", False)

    def canonical_value(self):
        return None

    def render_input(self, varprefix, value): 
        div_id = "option_" + varprefix
        if html.has_var(varprefix + "_use"):
            checked = html.get_checkbox(varprefix + "_use")
        else:
            checked = self._negate != (value != None)
        html.write("<div style=\"float: none;\">")
        html.checkbox(varprefix + "_use" , checked,
                      onclick="wato_toggle_option(this, %r, %r)" % 
                         (div_id, self._negate and 1 or 0))
        if self._label:
            html.write(self._label)
        elif self.title():
            html.write(_(self.title()))
        elif self._negate:
            html.write(_(" Ignore this option"))
        else:
            html.write(_(" Activate this option"))
        if self._sameline:
            html.write("&nbsp;")
        else:
            html.write("<br><br>")
        html.write("</div>")
        html.write('<div id="%s" style="float: left; display: %s">' % (
                div_id, checked == self._negate and "none" or ""))
        if value == None:
            value = self._valuespec.default_value()
        if self._valuespec.title():
            html.write(self._valuespec.title() + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.write('</div>\n')

    def value_to_text(self, value):
        if value == None:
            return self._none_label
        else:
            return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix): 
        if html.get_checkbox(varprefix + "_use") != self._negate:
            return self._valuespec.from_html_vars(varprefix + "_value")
        else:
            return None

    def validate_datatype(self, value, varprefix): 
        if value != None:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def validate_value(self, value, varprefix):
        if value != None:
            self._valuespec.validate_value(value, varprefix + "_value")

# Handle case when there are several possible allowed formats
# for the value (e.g. strings, 4-tuple or 6-tuple like in SNMP-Communities)
# The different alternatives must have different data types that can
# be distinguished with validate_datatype.
class Alternative(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]

    # Return the alternative (i.e. valuespec)
    # that matches the datatype of a given value. We assume
    # that always one matches. No error handling here.
    def matching_alternative(self, value):
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return vs
            except:
                pass

    def render_input(self, varprefix, value):
        mvs = self.matching_alternative(value)
        for nr, vs in enumerate(self._elements):
            if html.has_var(varprefix + "_use"):
                checked = html.var(varprefix + "_use") == str(nr)
            else:
                checked = vs == mvs

            html.radiobutton(varprefix + "_use", str(nr), checked, vs.title())
            html.write("<ul>")
            if vs == mvs:
                val = value
            else:
                val = vs.canonical_value()
            vs.render_input(varprefix + "_%d" % nr, val)
            html.write("</ul>\n")

    def set_focus(self, varprefix):
        # TODO: Set focus to currently active option
        pass

    def canonical_value(self):
        return self._elements[0].canonical_value()

    def value_to_text(self, value):
        vs = self.matching_alternative(value)
        if vs:
            return vs.value_to_text(value)
        else:
            return _("invalid:") + " " + str(value)

    def from_html_vars(self, varprefix):
        nr = int(html.var(varprefix + "_use"))
        vs = self._elements[nr] 
        return vs.from_html_vars(varprefix + "_%d" % nr)

    def validate_datatype(self, value, varprefix):
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return
            except:
                pass
        raise MKUserError(varprefix, 
            _("The data type of the value does not match any of the "
              "allowed alternatives."))

    def validate_value(self, value, varprefix):
        vs = self.matching_alternative(value)
        for nr, v in enumerate(self._elements):
            if vs == v:
                vs.validate_value(value, varprefix + "_%d" % nr)
    

# Edit a n-tuple (with fixed size) of values
class Tuple(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]
        self._show_titles = kwargs.get("show_titles", True)

    def canonical_value(self):
        return tuple([x.canonical_value() for x in self._elements])

    def render_input(self, varprefix, value):
        html.write('<table class="valuespec_tuple">')
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            if element.help():
                help = "<br><i>%s</i>" % element.help()
            else:
                help = ""
            html.write("<tr>")
            if self._show_titles:
                title = element.title()[0].upper() + element.title()[1:]
                html.write("<td class=left>%s:%s</td>" % (title, help))
            html.write("<td class=right>")
            element.render_input(vp, val)
            html.write("</td></tr>")
        html.write("</table>")

    def set_focus(self, varprefix):
        self._elements[0].set_focus(varprefix + "_0")

    def value_to_text(self, value): 
        return "" + ", ".join([ element.value_to_text(val) 
                         for (element, val)
                         in zip(self._elements, value)]) + ""

    def from_html_vars(self, varprefix):
        value = []
        for no, element in enumerate(self._elements):
            vp = varprefix + "_" + str(no)
            value.append(element.from_html_vars(vp))
        return tuple(value)

    def validate_value(self, value, varprefix):
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_value(val, vp)

    def validate_datatype(self, value, varprefix):
        if type(value) != tuple:
            raise MKUserError(varprefix, 
            _("The datatype must be a tuple, but is %s") % type(value))
        if len(value) != len(self._elements):
            raise MKUserError(varprefix, 
            _("The number of elements in the tuple must be exactly %d.") % len(self._elements))

        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_datatype(val, vp)

class Dictionary(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]

##    def help(self):
##        h = []
##        for key, vs in self._elements:
##            hh = vs.help()
##            if hh:
##              h.append("</i>%s<br><i>%s" % (vs.title(), hh))
##        return "<br><br>".join(h)

    def render_input(self, varprefix, value):
        html.write("<table class=dictionary>")
        for param, vs in self._elements:
            html.write("<tr><td>")
            vp = varprefix + "_" + param
            div_id = vp
            html.checkbox(vp + "_USE", param in value,
                          onclick="wato_toggle_option(this, %r)" % div_id)
            html.write(" %s<br>" % vs.title())
            html.write('<div class=dictelement id="%s" style="display: %s">' % ( 
                div_id, param not in value and "none" or ""))
            if vs.help():
                html.write("<ul class=help>%s</ul>" % vs.help())
            vs.render_input(vp, value.get(param, vs.canonical_value()))
            html.write("</div></td></tr>")
        html.write("</table>")

    def set_focus(self, varprefix):
        self._elements[0][1].set_focus(varprefix + self._elements[0][0])

    def canonical_value(self):
        return {}

    def value_to_text(self, value):
        parts = []
        for param, vs in self._elements:
            if param in value:
                parts.append("%s: %s" % (vs.title(), vs.value_to_text(value[param])))
        return ", ".join(parts)

    def from_html_vars(self, varprefix):
        value = {}
        for param, vs in self._elements:
            vp = varprefix + "_" + param
            if html.get_checkbox(vp + "_USE"):
                value[param] = vs.from_html_vars(vp)
        return value

    def validate_datatype(self, value, varprefix):
        if type(value) != dict:
            raise MKUserError(varprefix, _("The type must be a dictionary, but it is a %s") % type(value))

        for param, vs in self._elements:
            if param in value:
                vp = varprefix + "_" + param
                vs.validate_datatype(value[param], vp)

        # Check for exceeding keys
        allowed_keys = [ p for (p,v) in self._elements ]
        for param in value.keys():
            if param not in allowed_keys:
                raise MKUserError(varprefix, _("Undefined key '%s' in the dictionary. Allowed are %s.") %
                        ", ".join(allowed_keys))

    def validate_value(self, value, varprefix):
        for param, vs in self._elements:
            if param in value:
                vp = varprefix + "_" + param
                vs.validate_value(value[param], vp)
            

# Base class for selection of a Nagios element out
# of a given list that must be loaded from a file.
# Examples: GroupSelection, TimeperiodSelection. Child
# class must define a function get_elements() that
# returns a dictionary from element keys to element
# titles.
class ElementSelection(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._loaded_at = None

    def load_elements(self):
        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def canonical_value(self):
        self.load_elements()
        if len(self._elements) > 0:
            return self._elements.keys()[0]
        else:
            return ""

    def render_input(self, varprefix, value):
        self.load_elements()
        if len(self._elements) == 0:
            html.write(_("There are not defined any elements for this selection yet."))
        else:
            html.sorted_select(varprefix, self._elements.items(), value) 

    def value_to_text(self, value):
        self.load_elements()
        return self._elements.get(value, value)

    def from_html_vars(self, varprefix):
        return html.var(varprefix)

    def validate_value(self, value, varprefix):
        self.load_elements()
        if len(self._elements) == 0:
            raise MKUserError(varprefix, 
              _("You cannot save this rule. There are not defined any elements for this selection yet."))
        if value not in self._elements:
            raise MKUserError(varprefix, _("%s is not an existing element in this selection.") % (value,))

    def validate_datatype(self, value, varprefix):
        if type(value) != str:
            raise MKUserError(varprefix, _("The datatype must be str (string), but is %s") % type(value))



class CheckTypeSelection(ListChoice):
    def __init__(self, **kwargs):
        ListChoice.__init__(self, columns=3, **kwargs)

    def get_elements(self):
        checks = check_mk_automation("get-check-information")
        elements = [ (cn, "<span title=\"%s\">%s</span>" % (c["title"], cn)) for (cn, c) in checks.items()]
        elements.sort()
        return elements


def edit_value(valuespec, value):
    help = valuespec.help() or ""
    html.write('<tr><td class=legend><i>%s</i></td>' % help)

    html.write("<td class=content>")
    valuespec.render_input("ve", value) 
    html.write("</td></tr>")

def get_edited_value(valuespec):
    value = valuespec.from_html_vars("ve")
    valuespec.validate_value(value, "ve")
    return value

#   +----------------------------------------------------------------------+
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   | Main entry page for configuration of global variables, rules, groups,| 
#   | timeperiods, users, etc.                                             |
#   +----------------------------------------------------------------------+
def mode_main(phase):
    if phase == "title":
        return _("WATO - Check_MK's Web Administration Tool")

    elif phase == "buttons":
        changelog_button()
        snapshots_button()
        return

    elif phase == "action":
        return

    render_main_menu(modules)

def render_main_menu(some_modules, columns = 2):
    html.write("<table class=configmodules>")
    for nr, (mode, title, icon, permission, help) in enumerate(some_modules):
        if not config.may("wato." + permission) and not config.may("wato.seeall"):
            continue

        if nr % columns == 0:
            html.write("<tr>")
        url = make_link([("mode", mode)])
        html.write('<td class=icon><a href="%s"><img src="images/icon_%s.png"></a></td>' % 
              (url, icon))
        html.write('</td><td class=text><a href="%s">%s</a><br><i class=help>%s</i></td>' % 
           (url, title, help))
        if nr % columns == columns - 1:
            html.write("</tr>")
    html.write("</table>")
        




#   +----------------------------------------------------------------------+
#   |          ____ _       _           _  __     __                       |
#   |         / ___| | ___ | |__   __ _| | \ \   / /_ _ _ __ ___           |
#   |        | |  _| |/ _ \| '_ \ / _` | |  \ \ / / _` | '__/ __|          |
#   |        | |_| | | (_) | |_) | (_| | |   \ V / (_| | |  \__ \          |
#   |         \____|_|\___/|_.__/ \__,_|_|    \_/ \__,_|_|  |___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Editor for global settings in main.mk                                |
#   +----------------------------------------------------------------------+

def mode_globalvars(phase):
    if phase == "title":
        return _("Global configuration settings for Check_MK")

    elif phase == "buttons":
        global_buttons()
        return
    
    # Get default settings of all configuration variables of interest in the domain
    # "check_mk". (this also reflects the settings done in main.mk)
    check_mk_vars = [ varname for (varname, var) in g_configvars.items() if var[0] == "check_mk" ]
    default_values = check_mk_automation("get-configuration", [], check_mk_vars)
    current_settings = load_configuration_settings()

    if phase == "action":
        varname = html.var("_reset")
        if varname:
            domain, valuespec = g_configvars[varname]
            def_value = default_values.get(varname, valuespec.canonical_value())

            c = wato_confirm(
                _("Resetting configuration variable"),
                _("Do you really want to reset the configuration variable <b>%s</b> "
                  "back to the default value of <b><tt>%s</tt></b>?") % 
                   (varname, valuespec.value_to_text(def_value)))
            if c:
                del current_settings[varname]
                save_configuration_settings(current_settings)
                msg = _("Resetted configuration variable %s to its default.") % varname
                log_pending(None, "edit-configvar", msg)
                return "globalvars", msg 
            elif c == False:
                return ""
            else:
                return None

    groupnames = g_configvar_groups.keys()
    groupnames.sort()
    html.write("<table class=data>")
    for groupname in groupnames:
        html.write("<tr><td colspan=5><h3>%s</h3></td></tr>\n" % groupname) 
        html.write("<tr><th>" + _("Configuration variable") + 
                   "</th><th>" +_("Check_MK variable") + "</th><th>" + 
                   _("Default") + "</th><th>" + _("Your setting") + "</th><th></th></tr>\n")
        odd = "even"
            
        for domain, varname, valuespec in g_configvar_groups[groupname]: 
            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)
            if domain == "check_mk" and varname not in default_values:
                if config.debug:
                    raise MKGeneralException("The configuration variable <tt>%s</tt> is unknown to "
                                          "your local Check_MK installation" % varname)
                else:
                    continue
                
            defaultvalue = default_values.get(varname, valuespec.default_value())

            edit_url = make_link([("mode", "edit_configvar"), ("varname", varname)])

            html.write('<td><a href="%s">%s</a></td>' % (edit_url, valuespec.title()))
            html.write('<td><tt>%s</tt></td>' % varname)
            if varname in current_settings: 
                html.write('<td class=inherited>%s</td>' % valuespec.value_to_text(defaultvalue))
                html.write('<td><b>%s</b></td>'          % valuespec.value_to_text(current_settings[varname]))
            else:
                html.write('<td><b>%s</b></td>'          % valuespec.value_to_text(defaultvalue))
                html.write('<td></td>')

            html.write("<td class=buttons>")
            # html.buttonlink(edit_url, _("Edit"))
            if varname in current_settings: 
                reset_url = make_action_link([("mode", "globalvars"), ("_reset", varname)])
                html.buttonlink(reset_url, _("Reset"))
            html.write("</td>")

            html.write('</tr>')
    html.write("</table>")


def mode_edit_configvar(phase):
    if phase == "title":
        return "Global configuration settings for Check_MK"

    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "globalvars")]), "abort")
        return

    varname = html.var("varname")
    domain, valuespec = g_configvars[varname]
    current_settings = load_configuration_settings() 

    if phase == "action":
        new_value = get_edited_value(valuespec)
        current_settings[varname] = new_value
        save_configuration_settings(current_settings)
        msg = _("Changed global configuration variable %s to %s.") \
              % (varname, valuespec.value_to_text(new_value)) 
        log_pending(None, "edit-configvar", msg)
        return "globalvars"
    
    if varname in current_settings:
        value = current_settings[varname]
    else:
        check_mk_vars = check_mk_automation("get-configuration", [], [varname])
        value = check_mk_vars.get(varname, valuespec.default_value())

    html.begin_form("value_editor")
    html.write("<h3>%s</h3>" % valuespec.title())
    html.write("<table class=form>")
    edit_value(valuespec, value)
    valuespec.set_focus("ve")
    html.write("<tr><td class=buttons colspan=2>")
    html.button("save", _("Save"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()

g_configvars = {}
g_configvar_groups = {}

# domain is one of "check_mk", "multisite" or "nagios"
def register_configvar(group, varname, valuespec, domain="check_mk"):
    g_configvar_groups.setdefault(group, []).append((domain, varname, valuespec))
    g_configvars[varname] = domain, valuespec
 

# Persistenz: Speicherung der Werte
# - WATO speichert seine Variablen für main.mk in conf.d/wato/global.mk
# - Daten, die der User in main.mk einträgt, müssen WATO auch bekannt sein.
#   Sie werden als Defaultwerte verwendet.
# - Daten, die der User in final.mk oder local.mk einträgt, werden von WATO
#   völlig ignoriert. Der Admin kann hier Werte überschreiben, die man mit
#   WATO dann nicht ändern kann. Und man sieht auch nicht, dass der Wert
#   nicht änderbar ist.
# - WATO muss irgendwie von Check_MK herausbekommen, welche Defaultwerte
#   Variablen haben bzw. welche Einstellungen diese Variablen nach main.mk
#   haben.
# - WATO kann main.mk nicht selbst einlesen, weil dann der Kontext fehlt
#   (Default-Werte der Variablen aus Check_MK und aus den Checks)
# - --> Wir machen eine automation, die alle Konfigurationsvariablen
#   ausgibt.

def load_configuration_settings():
    settings = {}
    load_configuration_vars(multisite_dir + "wato.mk",   settings)
    load_configuration_vars(root_dir      + "global.mk", settings)
    return settings


def load_configuration_vars(filename, settings):
    if not os.path.exists(filename):
        return {}
    try:
        execfile(filename, settings, settings)
        for varname in settings.keys():
            if varname not in g_configvars:
                del settings[varname]
        return settings
    except Exception, e: 
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return {}


def save_configuration_settings(vars):
    per_domain = {}
    for varname, (domain, valuespec) in g_configvars.items():
        if varname not in vars:
            continue
        per_domain.setdefault(domain, {})[varname] = vars[varname]

    make_nagios_directory(root_dir)
    save_configuration_vars(per_domain.get("check_mk", {}), root_dir + "global.mk")
    make_nagios_directory(multisite_dir)
    save_configuration_vars(per_domain.get("multisite", {}), multisite_dir + "wato.mk")

def save_configuration_vars(vars, filename):
    out = file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for varname, value in vars.items():
        out.write("%s = %r\n" % (varname, value))
    

#   +----------------------------------------------------------------------+
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   | Mode for editing host-, service- and contact groups                  |
#   +----------------------------------------------------------------------+
def mode_groups(phase, what):
    if what == "host":
        what_name = _("host groups")
    elif what == "service":
        what_name = _("service groups")
    elif what == "contact":
        what_name = _("contact groups")

    if phase == "title":
        return what_name.title()

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New group"), make_link([("mode", "edit_%s_group" % what)]), "new")
        if what == "contact":
            pass
        else:
            varname = what + "_groups"
            html.context_button(_("Rules"), make_link([("mode", "edit_ruleset"), ("varname", varname)]), "rulesets")
        return

    all_groups = load_group_information()
    groups = all_groups.get(what, {})

    if phase == "action":
        delname = html.var("_delete")
        c = wato_confirm(_("Confirm deletion of group %s" % delname),
                         _("Do you really want to delete the group %s? If there are still objects "
                           "assigned to that group, the group will kept up (but without an alias). "
                           "Removing all objects from the will make the group disappear completely. " % what))
        if c: 
            del groups[delname]
            save_group_information(all_groups)
            log_pending(None, "edit-%sgroups", _("Deleted %s group %s" % (what, delname)))
            return None
        elif c == False:
            return ""
        else:
            return None

    sorted = groups.items()
    sorted.sort()
    html.write("<h3>%s</h3>" % what_name.title())
    if len(sorted) == 0:
        if what == "contact":
            render_main_menu([
              ( "edit_contact_group", _("Create new contact group"), "new", 
              what == "contact" and "users" or "groups",
              _("In order to assign objects (hosts and services) to people (contacts), "
                "you need first to define contact groups. When you put a user into a contact "
                "group then that user gets a monitoring contact. When you then also assign "
                "hosts and services to a contact group, all members of that group will be "
                "responsible for that objects, can receive notification for and see those objects "
                "in the status GUI."))])
        else:
            html.write("<div class=info>" + _("There are not defined any groups yet.") + "</div>")
        return

    html.write("<table class=data>")
    html.write("<tr><th>" + _("Actions") 
                + "</th><th>" + _("Name") 
                + "</th><th>" + _("Alias"))

    if what == "contact":
        html.write("</th><th>" + _("Members"))

    html.write("</th></tr>\n")

    # Show member of contact groups
    if what == "contact":
        users = load_users()
        members = {}
        for userid, user in users.items():
            cgs = user.get("contactgroups", [])
            for cg in cgs:
                members.setdefault(cg, []).append(userid)

    odd = "even"
    for name, alias in sorted:
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)
        edit_url = make_link([("mode", "edit_%s_group" % what), ("edit", name)])
        delete_url = html.makeactionuri([("_delete", name)])
        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td><td>%s</td><td>%s</td>" % (name, alias))
        if what == "contact":
            html.write("<td>%s</td>" % ", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_user"), ("edit", n)]), n) 
                 for n in members.get(name, [])]))
        html.write("</tr>")
    html.write("</table>")


def mode_edit_group(phase, what):
    name = html.var("edit") # missing -> new group
    new = name == None

    if phase == "title":
        if new:
            if what == "host":
                return _("Create new host group")
            elif what == "service":
                return _("Create new service group")
            elif what == "contact":
                return _("Create new contact group")
        else:
            if what == "host":
                return _("Edit host group")
            elif what == "service":
                return _("Edit service group")
            elif what == "contact":
                return _("Edit contact group")

    elif phase == "buttons":
        html.context_button(_("All groups"), make_link([("mode", "%s_groups" % what)]), "back")
        return

    all_groups = load_group_information()
    groups = all_groups.setdefault(what, {})

    if phase == "action":
        if html.check_transaction():
            alias = html.var_utf8("alias").strip()
            if new:
                name = html.var("name").strip()
                if len(name) == 0:
                    raise MKUserError("name", _("Please specify a name of the new group."))
                if ' ' in name:
                    raise MKUserError("name", _("Sorry, spaces are not allowed in group names."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid group name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                groups[name] = alias
                log_pending(None, "edit-%sgroups" % what, _("Create new %s group %s" % (what, name)))
            else:
                groups[name] = alias
                log_pending(None, "edit-%sgroups" % what, _("Changed alias of %s group %s" % (what, name)))
            save_group_information(all_groups)

        return what + "_groups"


    html.begin_form("group")
    html.write("<table class=form>")
    html.write("<tr><td class=legend>") 
    html.write(_("Name<br><i>The name of the group is used as an internal key. It cannot be "
                 "changed later. It is also visible in the status GUI.</i>"))
    html.write("</td><td class=content>") 
    if new:
        html.text_input("name")
        html.set_focus("name")
    else:
        html.write(name)
        html.set_focus("alias")
    html.write("</td></tr>")

    html.write("<tr><td class=legend>")
    html.write(_("Alias<br><i>A description of this group.</i>"))  
    html.write("</td><td class=content>")
    html.text_input("alias", name and groups.get(name, "") or "")
    html.write("</td></tr>") 
    html.write("<tr><td class=buttons colspan=2>")
    html.button("save", _("Save"))
    html.write("</td></tr></table>")
    html.hidden_fields()
    html.end_form()



    # Formular malen für neue / bestehende Gruppe 

def load_group_information():
    try:
        filename = root_dir + "groups.mk"
        if not os.path.exists(filename):
            return {}

        vars = {}
        for what in ["host", "service", "contact" ]:
            vars["define_%sgroups" % what] = {}
        
        execfile(filename, vars, vars)
        groups = {}
        for what in ["host", "service", "contact" ]:
            groups[what] = vars.get("define_%sgroups" % what, {})
        return groups

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return {}

def save_group_information(groups):
    make_nagios_directory(root_dir)
    out = file(root_dir + "groups.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for what in [ "host", "service", "contact" ]:
        if what in groups and len(groups[what]) > 0:
            out.write("if not define_%sgroups:\n    define_%sgroups = {}\n" % (what, what))
            out.write("define_%sgroups.update(%s)\n\n" % (what, pprint.pformat(groups[what])))


class GroupSelection(ElementSelection):
    def __init__(self, what, **kwargs):
        ElementSelection.__init__(self, **kwargs)
        self._what = what

    def get_elements(self):
        all_groups = load_group_information()
        this_group = all_groups.get(self._what, {})
        # replace the title with the key if the title is empty
        return dict([ (k, t and ("%s - %s" % (k,t)) or k) for (k, t) in this_group.items() ])


class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        ElementSelection.__init__(self, **kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = check_mk_automation("get-check-information")
        elements = dict([ (cn, "%s - %s" % (cn, c["title"])) for (cn, c) in checks.items() 
                     if c.get("group") == self._checkgroup ])
        return elements

    def value_to_text(self, value):
        return "<tt>%s</tt>" % value




#   +----------------------------------------------------------------------+
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Modes for managing Nagios' timeperiod definitions.                   |
#   +----------------------------------------------------------------------+
def mode_timeperiods(phase):
    if phase == "title":
        return _("Timeperiod definitions")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Timeperiod"), make_link([("mode", "edit_timeperiod")]), "new")
        return

    timeperiods = load_timeperiods()

    if phase == "action":
        delname = html.var("_delete")
        c = wato_confirm(_("Confirm deletion of time period %s") % delname,
              _("Do you really want to delete the time period '%s'? If it "
                "is still in use by an object, you will not be able to "
                "activate your changed configuration?") % delname)
        if c:
            del timeperiods[delname]
            save_timeperiods(timeperiods)
            log_pending(None, "edit-timeperiods", _("Deleted timeperiod %s") % delname)
            return None
        elif c == False:
            return ""
        else:
            return None

    html.write("<h3>" + _("Timeperiod definitions") + "</h3>")

    if len(timeperiods) == 0: 
        html.write("<div class=info>" + _("There are no timeperiods defined yet.") + "</div>") 
        return

    html.write("<table class=data>")
    html.write("<tr><th>" 
               + _("Actions") + "</th><th>"
               + _("Name") + "</th><th>"
               + _("Alias") + "</th></tr>")

    odd = "even" 
    names = timeperiods.keys()
    names.sort()
    for name in names: 
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)

        timeperiod = timeperiods[name]
        edit_url     = make_link([("mode", "edit_timeperiod"), ("edit", name)])
        delete_url   = html.makeactionuri([("_delete", name)])

        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td>")

        html.write("<td>%s</td>" % name)
        html.write("<td>%s</td>" % timeperiod.get("alias", ""))
        html.write("</tr>")

    html.write("</table>")


def load_timeperiods():
    filename = root_dir + "timeperiods.mk"
    if not os.path.exists(filename):
        return {}
    try:
        vars = { "timeperiods" : {} }
        execfile(filename, vars, vars)
        return vars["timeperiods"]
    
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return {}


def save_timeperiods(timeperiods):
    make_nagios_directory(root_dir)
    out = file(root_dir + "timeperiods.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("timeperiods.update(%s)\n" % pprint.pformat(timeperiods))


def mode_edit_timeperiod(phase):
    num_columns = 3
    num_exceptions = 10

    def timeperiod_ranges(vp, keyname):
        ranges = timeperiod.get(keyname, [])
        for c in range(num_columns): 
            if c < len(ranges):
                fromto = ranges[c]
            elif new and c == 0:
                fromto = "00:00", "24:00"
            else:
                fromto = "", ""
            html.write("<td>")
            var_prefix = vp + "_%d_" % c
            html.text_input(var_prefix + "from", fromto[0], cssclass = "timeperioddate")
            html.write(" - ")
            val = c == 0 and "24:00" or ""
            html.text_input(var_prefix + "to", fromto[1], cssclass = "timeperioddate")
            if c != num_columns - 1:
                html.write("&nbsp; &nbsp; &nbsp;")
            html.write("</td>")

    def get_ranges(varprefix):
        ranges = []
        for c in range(num_columns):
            vp = "%s_%d_" % (varprefix, c)
            begin = html.var(vp + "from", "").strip()
            end  = html.var(vp + "to", "").strip()
            if not begin and not end:
                continue
            if not begin:
                begin = "00:00"
            if not end:
                end = "24:00"

            begin, end = [ parse_bound(w, b) for (w,b) in [ ("from", begin), ("to", end) ]]
            ranges.append((begin, end))
        return ranges


    def parse_bound(what, bound):
        # Fully specified
        if re.match("^(24|[0-1][0-9]|2[0-3]):[0-5][0-9]$", bound):
            return bound
        # only hours
        try:
            b = int(bound)
            if b <= 24 and b >= 0:
                return "%02d:00" % b
        except:
            pass

        raise MKUserError(vp + what,
               _("Invalid time format '<tt>%s</tt>', please use <tt>24:00</tt> format.") % bound)


    name = html.var("edit") # missing -> new group
    new = name == None

    if phase == "title":
        if new:
            return _("Create new time period")
        else:
            return _("Edit time period")

    elif phase == "buttons":
        html.context_button(_("All Timeperiods"), make_link([("mode", "timeperiods")]), "back")
        return

    timeperiods = load_timeperiods() 
    if new:
        timeperiod = {}
    else:
        timeperiod = timeperiods.get(name, {})

    weekdays = [
      ( "monday",    _("Monday") ),
      ( "tuesday",   _("Tuesday") ),
      ( "wednesday", _("Wednesday") ),
      ( "thursday",  _("Thursday") ),
      ( "friday",    _("Friday") ),
      ( "saturday",  _("Saturday") ),
      ( "sunday",    _("Sunday") ),
    ]

    if phase == "action":
        if html.check_transaction():
            alias = html.var_utf8("alias").strip()
            if not alias:
                raise MKUserError("alias", _("Please specify an alias name for your timeperiod."))
        
            # extract time ranges of weekdays
            for weekday, weekday_name in weekdays:
                ranges = get_ranges(weekday)
                if ranges:
                    timeperiod[weekday] = ranges

            # extract ranges for custom days
            for e in range(0, num_exceptions): 
                varprefix = "ex%d" % e
                exname = html.var(varprefix + "_name", "").strip() 
                if exname in [ w[0] for w in weekdays ]:
                    raise MKUserError(varprefix + "_name", 
                           _("You may not specify a weekday's name as an exception."))
                if exname and exname not in [ "alias", "timeperiod_name" ]:
                    if not re.match("^[-a-z0-9A-Z /]*$", exname):
                        raise MKUserError(varprefix + "_name", 
                            _("'%s' is not a valid Nagios timeperiod day specification.") % exname)
                    ranges = get_ranges(varprefix)
                    timeperiod[exname] = ranges

            if new:
                name = html.var("name")
                if len(name) == 0:
                    raise MKUserError("name", _("Please specify a name of the new timeperiod."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid timeperiod name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if name in timeperiods:
                    raise MKUserError("name", _("This name is already being used by another timeperiod."))
                if name == "7X24":
                    raise MKUserError("name", _("The time period name 7X24 cannot be used. It is always autmatically defined."))
                timeperiods[name] = timeperiod
                log_pending(None, "edit-timeperiods", _("Created new time period %s" % name))
            else:
                log_pending(None, "edit-timeperiods", _("Modified time period %s" % name))
            timeperiod["alias"] = alias 
            save_timeperiods(timeperiods)
            return "timeperiods"
        return

    html.begin_form("timeperiod", method="POST")
    html.write("<table class=form>")

    # Name
    html.write("<tr><td class=legend>")
    html.write(_("Internal name"))
    html.write("</td><td class=content>")
    if new:
        html.text_input("name")
        html.set_focus("name")
    else:
        html.write(name) 
    html.write("</td></tr>")

    # Alias
    if not new:
        alias = timeperiods[name].get("alias", "")
    else:
        alias = ""
    html.write("<tr><td class=legend>")
    html.write(_("Alias") + "<br><i>" + _("A description of the timeperiod</i>"))
    html.write("</td><td class=content>")
    html.text_input("alias", alias, size = 50)
    if not new:
        html.set_focus("alias")
    html.write("</td></tr>")

    # Week days
    html.write("<tr><td class=legend>")
    html.write(_("Weekdays<br><i>For each weekday you can setup no, one or several "
                 "time ranges in the format <tt>23:39</tt>, in which the time period "
                 "should be active."))
    html.write("</td><td class=content>")
    html.write("<table class=timeperiod>")

    for weekday, weekday_alias in weekdays:
        ranges = timeperiod.get(weekday)
        html.write("<tr><td class=name>%s</td>" % weekday_alias)
        timeperiod_ranges(weekday, weekday)
        html.write("</tr>")
    html.write("</table></td></tr>")

    # Exceptions
    html.write("<tr><td class=legend>")
    nagurl = "../nagios/docs/objectdefinitions.html#timeperiod"
    html.write(_("Exceptions<br><i>Here you can specify exceptional time ranges for certain "
                 "relative or absolute dates. Please consult the <a target='_blank' href='%s'>Nagios documentation about "
                 "timeperiods</a> for examples." % nagurl))
    html.write("</td><td class=content>") 
    html.write("<table class=timeperiod>")

    exnames =  []
    for k in timeperiod:
        if k not in [ w[0] for w in weekdays ] and k != "alias":
            exnames.append(k)
    exnames.sort()
            
    for e in range(num_exceptions): 
        if e < len(exnames):
            exname = exnames[e]
            ranges = timeperiod[exname]
        else:
            exname = ""
            ranges = []
        varprefix = "ex%d" % e
        html.write("<tr><td class=name>")
        html.text_input(varprefix + "_name", exname)
        html.write("</td>")
        timeperiod_ranges(varprefix, exname)
        html.write("</tr>")
    html.write("</table></td></tr>")

    html.write("<tr><td colspan=2 class=buttons>")
    html.button("save", _("Save"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


class TimeperiodSelection(ElementSelection):
    def __init__(self, **kwargs):
        ElementSelection.__init__(self, **kwargs)

    def get_elements(self):
        timeperiods = load_timeperiods()
        elements = dict([ (name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items() ])
        return elements

#   +----------------------------------------------------------------------+
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing sites.                                             |
#   +----------------------------------------------------------------------+
def mode_sites(phase):
    if phase == "title":
        return _("Manage Multisite connections")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New connection"), make_link([("mode", "edit_site")]), "new")
        return

    sites = load_sites()

    if phase == "action":
        delid = html.var("_delete")
        c = wato_confirm(_("Confirm deletion of site %s" % delid),
                         _("Do you really want to delete the connection to the site %s?" % delid))
        if c: 
            del sites[delid]
            save_sites(sites)
            log_pending(None, "edit-sites", _("Deleted site %s" % (delid)))
            return None
        elif c == False:
            return ""
        else:
            return None

    if len(sites) == 0:
        html.write("<div class=info>" + 
           _("You have not configured any local or remotes sites. Multisite will " 
             "implicitely add the data of the local monitoring site. If you add remotes "
             "sites, please do not forget to add your local monitoring site also, if "
             "you want to display its data.") + "</div>")
        return


    html.write("<h3>" + _("Multisite connections") + "</h3>")
    html.write("<table class=data>")
    html.write("<tr><th>" + _("Actions") + "<th>" 
                + _("Site-ID") 
                + "</th><th>" + _("Alias / Description")
                + "</th><th>" + _("Connection")
                + "</th><th>" + _("Status host")
                + "</th><th>" + _("Disabled")
                + "</th><th>" + _("Timeout")
                + "</th><th>" + _("Pers.")
                + "</th></tr>\n")

    odd = "even"
    entries = sites.items()
    entries.sort(cmp = lambda a, b: cmp(a[1].get("alias"), b[1].get("alias")))
    for id, site in entries:
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)
        edit_url = make_link([("mode", "edit_site"), ("edit", id)])
        delete_url = html.makeactionuri([("_delete", id)])
        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td><td>%s</td><td>%s</td>" % (id, site.get("alias", "")))
        html.write("<td>%s</td>" % site.get("socket", _("local site")))
        if "status_host" in site:
            sh_site, sh_host = site["status_host"]
            html.write("<td>%s/%s</td>" % (sh_site, sh_host))
        else:
            html.write("<td></td>")
        if site.get("disabled", False) == True:
            html.write("<td><b>" + _("yes") + "</b></td>")
        else:
            html.write("<td>" + _("no") + "</td>")
        if "timeout" in site:
            html.write("<td class=number>%d sec</td>" % site["timeout"])
        else:
            html.write("<td></td>")
        if site.get("persist", False):
            html.write("<td><b>" + _("yes") + "</b></td>")
        else:
            html.write("<td>" + _("no") + "</td>")

        html.write("</tr>")
    html.write("</table>")

def mode_edit_site(phase):
    sites = load_sites()
    siteid = html.var("edit", None) # missing -> new site
    new = siteid == None
    if phase == "title":
        if new:
            return _("Create new site connection")
        else:
            return _("Edit site connection %s" % siteid)

    elif phase == "buttons":
        html.context_button(_("All Sites"), make_link([("mode", "sites")]), "back")
        return

    if new:
        site = {}
    else:
        site = sites.get(siteid, {})

    if phase == "action":
        if not html.check_transaction():
            return "sites"

        id = html.var("id").strip()
        if (new or id != siteid) and id in sites:
            raise MKUserError("id", _("This id is already being used by another connection."))
        if not re.match("^[-a-z0-9A-Z_]+$", id):
            raise MKUserError("id", _("The site id must consist only of letters, digit and the underscore."))

        if not new and id != siteid:
            del sites[siteid]

        new_site = {}
        sites[id] = new_site
        alias = html.var_utf8("alias", "").strip()
        if not alias:
            raise MKUserError("alias", _("Please enter an alias name or description of this site."))

        new_site["alias"] = alias
        url_prefix = html.var("url_prefix", "").strip()
        if url_prefix and url_prefix[-1] != '/':
            raise MKUserError("url_prefix", _("The URL prefix must end with a slash."))
        if url_prefix:
            new_site["url_prefix"] = url_prefix
        new_site["disabled"] = html.get_checkbox("disabled")

        # Connection
        method = html.var("method")
        if method == "unix":
            socket = html.var("conn_socket").strip()
            if not socket:
                raise MKUserError("conn_socket", _("Please specify the path to the UNIX socket to connect to."))
            # We do not check for the existance of the socket here. The matching
            # OMD site might be down. The admin might just want to disable the site for
            # that reason.
            new_site["socket"] = "unix:" + socket 

        elif method == "tcp":
            host = html.var("conn_host").strip()
            if not host:
                raise MKUserError("conn_host", _("Please specify the host or IP address to connect to."))
            port = html.var("conn_port").strip()
            try:
                port = int(port)
            except:
                raise MKUserError("conn_port", _("The port '%s' is not a valid number") % port)
            if port < 1 or port > 65535:
                raise MKUserError("conn_port{", _("The port number must be between 1 and 65535"))
            new_site["socket"] = "tcp:%s:%d" % (host, port)
        else:
            method = "local"

        # Timeout
        timeout = html.var("timeout", "").strip()
        if timeout != "":
            try:
                timeout = int(timeout)
            except:
                raise MKUserError("timeout", _("%s is not a valid integer number.") % timeout)
            new_site["timeout"] = timeout

        # Persist
        new_site["persist"] = html.get_checkbox("persist")

        # Status host
        sh_site = html.var("sh_site")
        if sh_site:
            if sh_site not in sites:
                raise MKUserError("sh_site", _("The site of the status host does not exist."))
            if sh_site in [ siteid, id ]:
                raise MKUserError("sh_site", _("You cannot use the site itself as site of the status host."))
            sh_host = html.var("sh_host")
            if not sh_host:
                raise MKUserError("sh_host", _("Please specify the name of the status host."))
            new_site["status_host"] = ( sh_site, sh_host )

        save_sites(sites)
        if new:
            log_pending(None, "edit-sites", _("Create new connection to site %s" % id))
        else:
            log_pending(None, "edit-sites", _("Modified connection to site %s" % id))
        return "sites"



    html.begin_form("site")
    html.write("<table class=form>")

    # ID
    html.write("<tr><td class=legend>")
    html.write(_("Site ID"))
    html.write("</td><td class=content>")
    html.text_input("id", siteid) 
    html.set_focus("id")
    html.write("</td></tr>")

    # Alias
    html.write("<tr><td class=legend>")
    html.write(_("Alias") + "<br><i>" + _("A name or description of the site</i>"))
    html.write("</td><td class=content>")
    html.text_input("alias", site.get("alias", ""), size = 50)
    html.write("</td></tr>")

    # Disabled
    html.write("<tr><td class=legend>")
    html.write(_("<i>If you disable a site, it will vanish from the status display, but the "
                 "connection configuration is still available for later use.</i>")) 
    html.write("</td><td class=content>")
    html.checkbox("disabled", False)
    html.write(_(" disable this connection"))
    html.write("</td></tr>")

    # Connection
    html.write("<tr><td class=legend>")
    html.write(_("Connection<br><i>When connecting to remote site please make sure "
               "that Livestatus over TCP is activated there. You can use UNIX sockets "
               "to connect to foreign sites on localhost. Please make sure that this "
               "site has proper read and write permissions to the UNIX socket of the "
               "foreign site."))
    html.write("</td><td class=content>")
    if html.has_var("method"):
        conn_socket = ""
        conn_host = ""
        conn_port = ""
        method = html.var("method")
    else:
        try:
            conn_socket = ""
            conn_host = ""
            conn_port = 6557 
            sock = site.get("socket")

            if not sock:
                method = "local"
            elif sock.startswith("unix:"):
                method = "unix"
                conn_socket = sock[5:]
            else:
                method = "tcp"
                parts = sock.split(":")
                conn_host = parts[1]
                conn_port = int(parts[2])
        except:
            method = "local"

    html.radiobutton("method", "local", method == "local", _("Connect to the local site")) 
    html.write("<p>")
    html.radiobutton("method", "tcp", method == "tcp", _("Connect via TCP to host: "))
    html.text_input("conn_host", conn_host, size=20)
    html.write(_(" port: "))
    html.number_input("conn_port", conn_port)
    html.write("<p>")
    html.radiobutton("method", "unix",  method == "unix", _("Connect via UNIX socket: "))
    html.text_input("conn_socket", conn_socket)
    html.write("</td></tr>")

    # Timeout
    html.write("<tr><td class=legend>")
    html.write(_("Connect Timeout<br><i>This setting limits the time Multisites waits for a connection "
                 "to the site to be established before the site is considered to be unreachable. "
                 "If not set, the operating system defaults are begin used."
                 "connection configuration is still available for later use.</i>")) 
    html.write("</td><td class=content>")
    timeout = site.get("timeout", "")
    html.number_input("timeout", timeout, size=2)
    html.write(_(" seconds"))
    html.write("</td></tr>")

    # Persistent connections
    html.write("<tr><td class=legend>")
    html.write(_("<i>If you enable persistent connections then Multisite will try to keep open "
                 "the connection to the remote sites. This brings a great speed up in high-latency "
                 "situations but locks a number of threads in the Livestatus module of the target site. "))
    html.write("</td><td class=content>")
    html.checkbox("persist", site.get("persist", False))
    html.write(_(" use persistent connections"))
    html.write("</td></tr>")

    # URL-Prefix
    html.write("<tr><td class=legend>")
    docu_url = "http://mathias-kettner.de/checkmk_multisite_modproxy.html"
    html.write(_("URL prefix<br><i>The URL prefix will be prepended to links of addons like PNP4Nagios "
                 "or the classical Nagios GUI when a link to such applications points to a host or "
                 "service on that site. You can either use an absole URL prefix like <tt>http://some.host/mysite/</tt> "
                 "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you needed a mod_proxy "
                 "configuration in your local system apache that proxies such URLs ot the according remote site. "
                 "Please refer to the <a target=_blank href='%s'>online documentation</a> for details. "
                 "The prefix should end with a slash. Omit the <tt>/pnp4nagios/</tt> from the prefix.") % docu_url) 
    html.write("</td><td class=content>")
    html.text_input("url_prefix", site.get("url_prefix", ""), size = 50)
    html.write("</td></tr>")

    # Status-Host
    html.write("<tr><td class=legend>")
    docu_url = "http://mathias-kettner.de/checkmk_multisite_statushost.html"
    html.write(_("Status host<br><i>By specifying a status host for each non-local connection "
                 "you prevent Multisite from running into timeouts when remote sites do not respond. "
                 "You need to add the remote monitoring servers as hosts into your local monitoring "
                 "site and use their host state as a reachability state of the remote site. Please "
                 "refer to the <a target=_blank href='%s'>online documentation</a> for details.") % docu_url)

    html.write("</td><td class=content>")
    sh = site.get("status_host")
    if sh:
        sh_site, sh_host = sh
    else:
        sh_site = ""
        sh_host = ""
    html.write(_("host: "))
    html.text_input("sh_host", sh_host)
    html.write(_(" on monitoring site: "))  
    html.sorted_select("sh_site", 
       [ ("", _("(no status host)")) ] + [ (sk, si.get("alias", sk)) for (sk, si) in sites.items() ], sh_site)
    html.write("</td></tr>")

    html.write("</table>")
    html.hidden_fields()
    html.button("save", _("Save"))
    html.end_form()


def load_sites():
    try:
        filename = multisite_dir + "sites.mk"
        if not os.path.exists(filename):
            return {}

        vars = { "sites" : {} }
        execfile(filename, vars, vars)
        return vars["sites"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return {}


def save_sites(sites):
    make_nagios_directory(multisite_dir)
    filename = multisite_dir + "sites.mk"
    if len(sites) == 0:
        if os.path.exists(filename):
            os.remove(filename)
    else:
        out = file(filename, "w")
        out.write("# Written by WATO\n# encoding: utf-8\n\n")
        out.write("sites = \\\n%s\n" % pprint.pformat(sites))

#   +----------------------------------------------------------------------+
#   | _   _                      ______            _             _         |
#   || | | |___  ___ _ __ ___   / / ___|___  _ __ | |_ __ _  ___| |_ ___   |
#   || | | / __|/ _ \ '__/ __| / / |   / _ \| '_ \| __/ _` |/ __| __/ __|  |
#   || |_| \__ \  __/ |  \__ \/ /| |__| (_) | | | | || (_| | (__| |_\__ \  |
#   | \___/|___/\___|_|  |___/_/  \____\___/|_| |_|\__\__,_|\___|\__|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing users and contacts.                                |
#   +----------------------------------------------------------------------+
def mode_users(phase): 
    if phase == "title":
        return _("Manage Users & Contacts")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New user"), make_link([("mode", "edit_user")]), "new")
        return

    users = load_users()
    timeperiods = load_timeperiods()

    if phase == "action":
        delid = html.var("_delete")
        if delid == config.user_id:
            raise MKUserError(None, _("You cannot delete your own account!"))

        c = wato_confirm(_("Confirm deletion of user %s" % delid),
                         _("Do you really want to delete the user %s?" % delid))
        if c: 
            del users[delid]
            save_users(users)
            log_pending(None, "edit-users", _("Deleted user %s" % (delid)))
            return None
        elif c == False:
            return ""
        else:
            return None

    if len(users) == 0:
        html.write("<div class=info>" + 
            _("There are not defined any contacts/users yet.") + "</div>")

    html.write("<h3>" + _("Users & Contacts") + "</h3>")
    html.write("<table class=data>")
    html.write("<tr><th>" + _("Actions") + "<th>" 
                + _("ID") 
                + "</th><th>" + _("Locked")
                + "</th><th>" + _("Full Name")
                + "</th><th>" + _("Email")
                + "</th><th>" + _("Roles")
                + "</th><th>" + _("Contact groups")
                + "</th><th>" + _("Notifications")
                + "</th></tr>\n")

    odd = "even"
    entries = users.items()
    entries.sort(cmp = lambda a, b: cmp(a[1].get("alias"), b[1].get("alias")))
    for id, user in entries:
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)

        # Buttons
        edit_url = make_link([("mode", "edit_user"), ("edit", id)])
        delete_url = html.makeactionuri([("_delete", id)])
        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td>")

        # ID
        html.write("<td>%s</td>" % id)

        # Locked
        locked = user.get("locked", False)
        html.write("<td>%s</td>" % (locked and ("<b>" + _("yes") + "</b>") or _("no")))

        # Full name / Alias
        html.write("<td>%s</td>" % user.get("alias", ""))

        # Email
        html.write("<td>%s</td>" % user.get("email", ""))

        # Roles
        if user.get("roles", []):
            html.write("<td>%s</td>" % ", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_role"), ("edit", r)]), r) for r in user["roles"]]))
        else:
            html.write("<td></td>")

        # contact groups
        html.write("<td>")
        cgs = user.get("contactgroups", [])
        if cgs:
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_contact_group"), ("edit", c)]), c) for c in cgs]))
        else:
            html.write("<i>" + _("none") + "</i>")
        html.write("</td>")

        # notifications
        html.write("<td>")
        if not cgs:
            html.write(_("<i>not a contact</i>"))
        elif not user.get("notifications_enabled", True):
            html.write(_("disabled"))
        elif "" == user.get("host_notification_options", "") \
            and "" == user.get("service_notification_options", ""):
            html.write(_("all events disabled"))
        else:
            tp = user.get("notification_period", "24X7")
            if tp != "24X7" and tp not in timeperiods:
                tp = tp + _(" (invalid)")
            elif tp != "24X7":
                url = make_link([("mode", "edit_timeperiod"), ("edit", tp)])
                tp = '<a href="%s">%s</a>' % (url, timeperiods[tp].get("alias", tp))
            html.write(tp)
        html.write("</td>")
        html.write("</tr>")
    html.write("</table>")

    if not load_group_information().get("contact", {}):
        url = "wato.py?mode=contact_groups"
        html.write("<div class=info>" + 
            _("Note: you haven't defined any contact groups yet. If you <a href='%s'>"
              "create some contact groups</a> you can assign users to them und thus "
              "make them monitoring contacts. Only monitoring contacts can receive "
              "notifications.") % url + "</div>")



def mode_edit_user(phase):
    users = load_users()
    userid = html.var("edit", None) # missing -> new user
    new = userid == None
    if phase == "title":
        if new:
            return _("Create new user")
        else:
            return _("Edit user %s" % userid)

    elif phase == "buttons":
        html.context_button(_("All Users"), make_link([("mode", "users")]), "back")
        return

    if new:
        user = {}
    else:
        user = users.get(userid, {})

    # Load data that is referenced - in order to display dropdown
    # boxes and to check for validity.
    contact_groups = load_group_information().get("contact", {})
    timeperiods = load_timeperiods()
    roles = load_roles()

    if phase == "action":
        if not html.check_transaction():
            return "users"

        id = html.var("userid").strip()
        if new and id in users:
            raise MKUserError("userid", _("This id is already being used by another user."))
        if not re.match("^[-a-z0-9A-Z_]+$", id):
            raise MKUserError("userid", _("The user id must consist only of letters, digit and the underscore."))

        if new:
            new_user = {}
            users[id] = new_user
        else:
            new_user = users[id]

        # Full name
        alias = html.var("alias").strip()
        if not alias:
            raise MKUserError("alias", 
            _("Please specify a full name or descriptive alias for the user."))
        new_user["alias"] = alias

        # Password
        password = html.var("password").strip()
        password2 = html.var("password2").strip()
            
        # Locking
        if id == config.user_id and html.get_checkbox("locked"):
            raise MKUserError(_("You cannot lock your own account!"))
        new_user["locked"] = html.get_checkbox("locked")

        # We compare both passwords only, if the user has supplied
        # the repeation! We are so nice to our power users...
        if password2 and password != password2:
            raise MKUserError("password2", _("The both passwords do not match."))

        if password:
            new_user["password"] = encrypt_password(password)

        # Email address
        email = html.var("email").strip()
        regex_email = '^[-a-zA-Z0-9_.]+@[-a-zA-Z0-9]+(\.[a-zA-Z]+)*$'
        if email and not re.match(regex_email, email):
            raise MKUserError("email", _("'%s' is not a valid email address." % email))
        new_user["email"] = email

        # Roles
        new_user["roles"] = filter(lambda role: html.get_checkbox("role_" + role), 
                                   roles.keys())

        # Contact groups
        cgs = []
        for c in contact_groups:
            if html.get_checkbox("cg_" + c):
                cgs.append(c)
        new_user["contactgroups"] = cgs

        # Notifications
        new_user["notifications_enabled"] = html.get_checkbox("notifications_enabled")
        ntp = html.var("notification_period")
        if ntp not in timeperiods:
            ntp = "24X7"
        new_user["notification_period"] = ntp
    
        for what, opts in [ ( "host", "durfs"), ("service", "wucrfs") ]:
            new_user[what + "_notification_options"] = "".join(
              [ opt for opt in opts if html.get_checkbox(what + "_" + opt) ])


        # Saving
        save_users(users)
        if new:
            log_pending(None, "edit-users", _("Create new user %s" % id))
        else:
            log_pending(None, "edit-users", _("Modified user %s" % id))
        return "users"


    html.begin_form("user")
    html.write("<table class=form>")

    # ID
    html.write("<tr><td class=legend>")
    html.write(_("User ID"))
    html.write("</td><td class=content>")
    if new:
        html.text_input("userid", userid) 
        html.set_focus("userid")
    else:
        html.write(userid)
        html.hidden_field("userid", userid)
    html.write("</td></tr>")

    # Full name
    html.write("<tr><td class=legend>")
    html.write(_("Full name") + "<br><i>" + _("Full name or alias of the user</i>"))
    html.write("</td><td class=content>")
    html.text_input("alias", user.get("alias", ""), size = 50)
    if not new:
        html.set_focus("alias")
    html.write("</td></tr>")

    # Password
    html.write("<tr><td class=legend>")
    html.write(_("Password<br><i>If you want to user to be able to login "
                 "then specify a password here. Users without a login make sense "
                 "if they are monitoring contacts that are just used for "
                 "notifications.<br><br>The repetition of the password is optional. "
                 "If you think you can type the password correctly, simply leave out "
                 "the repetition."))
    html.write("</td><td class=content>")
    html.password_input("password", autocomplete="off")
    html.write(_(" repeat: "))
    html.password_input("password2", autocomplete="off")
    html.write(" (%s)" % _("optional, if you like to be sure"))
    html.write("</td></tr>")

    # Locking
    html.write("<tr><td class=legend>")
    html.write(_("<i>Locking the password prevents a user from logging in without "
                 "the need of changing the password.</i>"))
    html.write("</td><td class=content>")
    html.checkbox("locked", user.get("locked", False))
    html.write(_(" lock the password of this account"))
    html.write("</td></tr>")

    # Email address
    html.write("<tr><td class=legend>")
    html.write(_("Email address<br><i>The email address is optional and is needed "
                 "if the user is a monitoring contact and receives notifications "
                 "via Email."))
    html.write("</td><td class=content>")
    html.text_input("email", user.get("email", ""), size = 50)
    html.write("</td></tr>")

    # Roles
    html.write("<tr><td class=legend>")
    html.write(_("Roles<br><i>By assigning roles to a user he obtains permissions. "
                 "If a user has more then one role, he gets the maximum of all "
                 "permissions of his roles. "
                 "Users without any role have no permissions to use Multisite at all "
                 "but still can be monitoring contacts and receive notifications.</i>"))
    html.write("</td><td class=content>")
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))
    for role_id, role in entries:
        html.checkbox("role_" + role_id, role_id in user.get("roles", []))
        url = make_link([("mode", "edit_role"), ("edit", role_id)])
        html.write("%s - <a href='%s'>%s</a><br>" % (role_id, url, role["alias"]))
    html.write("</td></tr>")

    # Contact groups
    html.write("<tr><td class=legend>")
    url1 = make_link([("mode", "contact_groups")])
    url2 = make_link([("mode", "rulesets")])
    html.write(_("Contact groups<br><i>Contact groups are used to assign monitoring "
                 "objects to users. If you haven't defined any contact groups yet, "
                 "then first <a href='%s'>do so</a>. Hosts and services can be "
                 "assigned to contact groups using <a href='%s'>rules</a>.") %
                 (url1, url2))
    html.write("<br><br>" + _("If you do not put the user into any contact group "
               "then no monitoring contact will be created for the user.")
               + "</i>")
    html.write("</td><td class=content>")
    if len(contact_groups) == 0:
        html.write(_("Please first create some <a href='%s'>contact groups</a>") %
                url1)
    else:
        entries = [ (contact_groups[c], c) for c in contact_groups ]
        entries.sort()
        for alias, gid in entries:
            if not alias:
                alias = gid
            html.checkbox("cg_" + gid, gid in user.get("contactgroups", []))
            url = make_link([("mode", "edit_contact_group"), ("edit", gid)])
            html.write(" %s - <a href=\"%s\">%s</a><br>" % (gid, url, alias))

    html.write("</td></tr>")

    # Notifications enabled
    html.write("<tr><td class=legend>")
    html.write(_("Notifications enabled<br><i>Notifications are sent out "
                "when the status of a host or service changes.</i>"))
    html.write("</td><td class=content>")
    html.checkbox("notifications_enabled", user.get("notifications_enabled", True))
    html.write(" " + _("enable notifications"))
    html.write("</td></tr>")

    # Notification period
    html.write("<tr><td class=legend>")
    html.write(_("Notification time period<br><i>Only during this time period the "
                 "user will get notifications about host or service alerts."))
    html.write("</td><td class=content>")
    choices = [ ( "24X7", _("24X7 - Always")) ] + \
              [ ( id, "%s - %s" % (id, tp["alias"])) for (id, tp) in timeperiods.items() ]
    html.sorted_select("notification_period", choices, user.get("notification_period"))
    html.write("</td></tr>")

    # Notification options
    notification_option_names = { # defined here: _() must be executed always!
        "host" : {
            "d" : _("Host goes down"),
            "u" : _("Host gets unreachble"),
            "r" : _("Host goes up again"),
        },
        "service" : {
            "w" : _("Service goes into warning state"),
            "u" : _("Service goes into unknown state"),
            "c" : _("Service goes into critical state"),
            "r" : _("Service recovers to OK"),
        },
        "both" : {
            "f" : _("Start or end of flapping state"),
            "s" : _("Start or end of a scheduled downtime"),
        }
    }

    html.write("<tr><td class=legend>")
    html.write(_("Notification options<br><i>Here you specify which types of alerts "
               "will be notified to this contact.</i>"))
    html.write("</td><td class=content>")
    for title, what, opts in [ ( _("Host events"), "host", "durfs"), 
                  (_("Service events"), "service", "wucrfs") ]:
        html.write("%s:<ul>" % title)
        user_opts = user.get(what + "_notification_options", opts)
        for opt in opts:
            html.checkbox(what + "_" + opt, opt in user_opts)
            opt_name = notification_option_names[what].get(opt, 
                   notification_option_names["both"].get(opt))
            html.write(" %s<br>" % opt_name)
        html.write("</ul>")
    html.write("</td></tr>")

    # TODO: Later we could add custom macros here, which
    # then could be used for notifications. On the other hand,
    # if we implement some check_mk --notify, we could directly
    # access the data in the account with the need to store
    # values in the monitoring core. We'll see what future brings.
    html.write("<tr><td class=buttons colspan=2>")
    html.button("save", _("Save"))
    html.write("</tr>")

    html.write("</table>")
    html.hidden_fields()
    html.end_form()




def encrypt_password(password):
    import md5crypt, time
    salt = "%06d" % (1000000 * (time.time() % 1.0))
    return md5crypt.md5crypt(password, salt, '$1$')

def load_users(): 
    # First load monitoring contacts from Check_MK's world
    filename = root_dir + "contacts.mk"
    if os.path.exists(filename):
        try:
            vars = { "contacts" : {} }
            execfile(filename, vars, vars)
            contacts = vars["contacts"]
        except Exception, e:
            if config.debug:
                raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                              (filename, e)))
            contacts = {}
    else:
        contacts = {}

    # Now add information about users from the Web world
    filename = multisite_dir + "users.mk"
    if os.path.exists(filename):
        try:
            vars = { "multisite_users" : {} }
            execfile(filename, vars, vars)
            users = vars["multisite_users"]
        except Exception, e:
            if config.debug:
                raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                              (filename, e)))
            users = {}
    else:
        users = {}

    # Merge them together. Monitoring users not known to Multisite
    # will be added later as normal users.
    result = {}
    for id, user in users.items():
        profile = contacts.get(id, {})
        profile.update(user)
        result[id] = profile

    # This loop is only neccessary if someone has edited
    # contacts.mk manually. But we want to support that as
    # far as possible.
    for id, contact in contacts.items():
        if id not in result:
            result[id] = contact
            result[id]["roles"] = [ "user" ]
            result[id]["locked"] = True
            result[id]["password"] = ""

    # Passwords are read directly from the apache htpasswd-file.
    # That way heroes of the command line will still be able to
    # change passwords with htpasswd.
    filename = defaults.htpasswd_file
    for line in file(filename):
        id, password = line.strip().split(":")[:2]
        if password.startswith("!"):
            locked = True
            password = password[1:]
        else:
            locked = False
        if id in result:
            result[id]["password"] = password
            result[id]["locked"] = locked
        elif id in config.admin_users:
            # Create entry if this is an admin user
            new_user = {
                "roles" : [ "admin" ],
                "password" : password,
                "locked" : False
            }
            result[id] = new_user
        # Other unknown entries will silently be dropped. Sorry...

    return result

def split_dict(d, keylist, positive):
    return dict([(k,v) for (k,v) in d.items() if (k in keylist) == positive])

def save_users(profiles):
    # TODO: delete var/check_mk/web/$USER of non-existing users. Do we
    # need to remove other references as well?
    non_contact_keys = [ "roles", "password", "locked" ]

    # Remove multisite keys in contacts
    contacts = dict([ (id, split_dict(user, non_contact_keys, False)) for (id, user) in profiles.items() ])

    # Remove contact keys and password from users
    users  = dict([ (id, { "roles" : p.get("roles", []) } ) 
                  for (id, p) 
                  in profiles.items() ] )

    # Check_MK's monitoring contacts
    filename = root_dir + "contacts.mk"
    out = file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("contacts.update(\n%s\n)\n" % pprint.pformat(contacts))

    # Users with passwords for Multisite
    make_nagios_directory(multisite_dir)
    filename = multisite_dir + "users.mk"
    out = file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("multisite_users = \\\n%s\n" % pprint.pformat(users))

    # Apache htpasswd. We only store passwords here. During
    # loading we created entries for all admin users we know. Other
    # users from htpasswd are lost. If you start managing users with
    # WATO, you should continue to do so or stop doing to for ever...
    # Locked accounts get a '!' before their password. This disable it.
    filename = defaults.htpasswd_file
    out = file(filename, "w")
    for id, user in profiles.items():
        if user.get("locked", False):
            locksym = '!'
        else:
            locksym = ""
        out.write("%s:%s%s\n" % (id, locksym, user.get("password", "!")))

#   +----------------------------------------------------------------------+
#   |                       ____       _                                   |
#   |                      |  _ \ ___ | | ___  ___                         |
#   |                      | |_) / _ \| |/ _ \/ __|                        |
#   |                      |  _ < (_) | |  __/\__ \                        |
#   |                      |_| \_\___/|_|\___||___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing roles and permissions.                             |
#   | In order to make getting started easier - Check_MK Multisite comes   |
#   | with three builtin-roles: admin, user and guest. These roles have    |
#   | predefined permissions. The builtin roles cannot be deleted. Users   |
#   | listed in admin_users in multisite.mk automatically get the role     |
#   | admin - even if no such user or contact has been configured yet. By  |
#   | that way an initial login - e.g. as omdamin - is possible. The admin |
#   | role cannot be removed from that user as long as he is listed in     |
#   | admin_users. Also the variables guest_users, users and default_user_ |
#   | role still work. That way Multisite is fully operable without WATO   |
#   | and also backwards compatible.                                       |
#   | In WATO you can create further roles and also edit the permissions   |
#   | of the existing roles. Users can be assigned to builtin and custom   |
#   | roles.                                                               |
#   | This modes manages the creation of custom roles and the permissions  |
#   | configuration of all roles.
#   +----------------------------------------------------------------------+

def mode_roles(phase):
    if phase == "title":
        return _("Manage Roles & Permissions")

    elif phase == "buttons":
        global_buttons()
        return

    roles = load_roles()
    users = load_users()
        
    if phase == "action":
        if html.var("_delete"):
            delid = html.var("_delete")
            if html.transaction_valid() and roles[delid].get('builtin'):
                raise MKUserError(None, _("You cannot delete the builtin roles!"))

            c = wato_confirm(_("Confirm deletion of role %s" % delid),
                             _("Do you really want to delete the role %s?" % delid))
            if c: 
                rename_user_role(delid, None) # Remove from existing users
                del roles[delid]
                save_roles(roles)
                log_audit(None, "edit-roles", _("Deleted role '%s'" % delid))
                return None
            elif c == False:
                return ""
            else:
                return
        elif html.var("_clone"):
            if html.check_transaction():
                cloneid = html.var("_clone")
                cloned_role = roles[cloneid]
                newid = cloneid
                while newid in roles:
                    newid += "x"
                new_role = {}
                new_role.update(cloned_role)
                if cloned_role.get("builtin"):
                    new_role["builtin"] =  False
                    new_role["basedon"] = cloneid
                roles[newid] = new_role
                save_roles(roles)
                log_audit(None, "edit-roles", _("Created new role '%s'" % newid))
                return None
            else:
                return None


    html.write("<h3>" + _("User Roles") + "</h3>")
    html.write("<table class=data>")
    html.write("<tr>"
             + "<th>" + _("Actions")       + "</th>"  
             + "<th>" + _("ID")            + "</th>"  
             + "<th>" + _("Description")   + "</th>"  
             + "<th>" + _("Type")          + "</th>"
             + "<th>" + _("Modifications") + "</th>"
             + "<th>" + _("Users")         + "</th>"
             + "</tr>\n")


    # Show table of builtin and user defined roles
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))

    odd = "even"
    for id, role in entries:
        odd = odd == "odd" and "even" or "odd" 
        html.write('<tr class="data %s0">' % odd)

        # Actions 
        html.write("<td>")
        edit_url = make_link([("mode", "edit_role"), ("edit", id)])
        clone_url = html.makeactionuri([("_clone", id)])
        delete_url = html.makeactionuri([("_delete", id)])
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(clone_url, _("Clone"))
        if not role.get("builtin"):
            html.buttonlink(delete_url, _("Delete"))
        html.write("</td>")

        # ID
        html.write("<td>%s</td>" % id)

        # Description
        html.write("<td>%s</td>" % role["alias"])

        # Type
        html.write("<td>%s</td>" % (role.get("builtin") and _("builtin") or _("custom")))

        # Modifications
        html.write("<td><span title='%s'>%s</span></td>" % (
            _("That many permissions do not use the factory defaults."), len(role["permissions"])))

        # Users
        html.write("<td>%s</td>" %
          ", ".join([ '<a href="%s">%s</a>' % (make_link([("mode", "edit_user"), ("edit", user_id)]), 
             user.get("alias", user_id))  
            for (user_id, user) in users.items() if (id in user["roles"])]))

        html.write("</tr>\n") 

    # Possibly we could also display the following information
    # - number of set permissions (needs loading users)
    # - number of users with this role
    html.write("</table>")


def mode_edit_role(phase):
    id = html.var("edit")

    if phase == "title":
        return _("Edit user role %s" % id)

    elif phase == "buttons":
        html.context_button(_("All Roles"), make_link([("mode", "roles")]), "back")
        return

    roles = load_roles()
    role = roles[id]

    if phase == "action":
        alias = html.var_utf8("alias")
        new_id = html.var("id")
        if len(new_id) == 0:
            raise MKUserError("id", _("Please specify an ID for the new role.")) 
        if not re.match("^[-a-z0-9A-Z_]*$", new_id):
            raise MKUserError("id", _("Invalid role ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
        if new_id != id:
            if new_id in roles:
                raise MKUserError("id", _("The ID is already used by another role"))

        role["alias"] = alias 

        # based on 
        if not role.get("builtin"):
            basedon = html.var("basedon")
            if basedon not in config.builtin_role_ids:
                raise MKUserError("basedon", _("Invalid valid for based on. Must be id of builtin rule."))
            role["basedon"] = basedon

        # Permissions
        permissions = {}
        for perm in config.permissions_by_order:
            pname = perm["name"]
            value = html.var("perm_" + pname)
            if value == "yes":
                permissions[pname] = True
            elif value == "no":
                permissions[pname] = False
        role["permissions"] = permissions

        if id != new_id:
            roles[new_id] = role
            del roles[id]
            rename_user_role(id, new_id)

        save_roles(roles)
        log_audit(None, "edit-roles", _("Modified user role '%s'" % new_id)) 
        return "roles"

    html.begin_form("role", method="POST")
    html.write("<table class=form>")

    # ID
    html.write("<tr><td class=legend>")
    html.write(_("Internal ID"))
    html.write("</td><td class=content>")
    if role.get("builtin"):
        html.write("%s (%s)" % (id, _("builtin role"))) 
        html.hidden_field("id", id)
    else:
        html.text_input("id", id)
        html.set_focus("id")
    html.write("</td></tr>")

    # Alias
    html.write("<tr><td class=legend>")
    html.write(_("Alias") + "<br><i>" + _("An optional description of the timeperiod</i>"))
    html.write("</td><td class=content>")
    html.text_input("alias", role.get("alias", ""), size = 50)
    html.write("</td></tr>")

    # Based on
    if not role.get("builtin"):
        html.write("<tr><td class=legend>")
        html.write(_("Based on<br><i>Each user defined role is based on one of the builtin roles. "
                     "When created it will start with all permissions of that role. When due to a software "
                     "update or installation of an addons new permissions appear, the user role will get or "
                     "not get those new permissions based on the default settings of the builtin role it's "
                     "based on.</i>"))
        html.write("</td><td class=content>")
        choices = [ (i, r["alias"]) for i, r in roles.items() if r.get("builtin") ]
        html.sorted_select("basedon", choices, role.get("basedon", "user"))
        html.write("</td></tr>")

    
    # Permissions
    base_role_id = role.get("basedon", id)
    def perm_header(section_id, title, is_open, help=None):
        html.write("<tr><td class=legend>")
        html.write(title)
        if help:
            html.write("<br><i>%s</i>" % help)
        html.write("</td><td class=content>")
        html.begin_foldable_container('permissions', section_id, is_open, title, indent=False) 
        html.write("<table class=permissions>")

    def perm_footer():
        html.write("</table>")
        html.end_foldable_container()
        html.write("</td></tr>")

    perm_header("general", _("General permissions"), True, 
       _("When you leave the permissions at <i>default</i> then they get their "
         "settings from the factory defaults (for builtin roles) or from the " 
         "factory default of their base role (for user define roles). Factory defaults "
         "may change due to software updates. When choosing another base role, all "
         "permissions that are on default will reflect the new base role."))
    current_section = None
    for perm in config.permissions_by_order:
        pname = perm["name"]
        if "." in pname:
            section = pname.split(".")[0]
            section_title = config.permission_sections[section]
            if section != current_section:
                perm_footer()
                perm_header(section, section_title, False)
                current_section = section
        
        pvalue = role["permissions"].get(pname)
        def_value = base_role_id in perm["defaults"]
        html.write("<tr><td class=left>%s<br><i>%s</i></td>" % (perm["title"], perm["description"]))
        html.write("<td class=right>")
        choices = [ ( "yes", _("yes")),
                    ( "no", _("no")),
                    ( "default", _("default (%s)") % (def_value and _("yes") or _("no") )) ] 
        html.select("perm_" + pname, choices, { True: "yes", False: "no" }.get(pvalue, "default") )
        html.write("</td></tr>")
    perm_footer()

    # Save button
    html.write("<tr><td colspan=2 class=buttons>")
    html.button("save", _("Save"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


def load_roles():
    # Fake builtin roles into user roles.
    builtin_role_names = {  # Default names for builtin roles
        "admin" : _("Administrator"),
        "user"  : _("Normal monitoring user"),
        "guest" : _("Guest user"),
    }
    roles = dict([(id, { 
         "alias" : builtin_role_names.get(id, id),
         "permissions" : {}, # use default everywhere
         "builtin": True}) 
                  for id in config.builtin_role_ids ])
    
    filename = multisite_dir + "roles.mk"
    if not os.path.exists(filename):
        return roles

    try:
        vars = { "roles" : roles }
        execfile(filename, vars, vars)
        return vars["roles"]
    
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return roles


def save_roles(roles):
    make_nagios_directory(multisite_dir)
    filename = multisite_dir + "roles.mk"
    out = file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("roles.update(\n%s)\n" % pprint.pformat(roles))


# Adapt references in users. Builtin rules cannot
# be renamed and are not handled here. If new_id is None,
# the role is being deleted
def rename_user_role(id, new_id):
    users = load_users()
    for user in users.values():
        if id in user["roles"]:
            user["roles"].remove(id)
            if new_id:
                user["roles"].append(new_id)
    save_users(users)


#   +----------------------------------------------------------------------+
#   |              _   _           _     _____                             |
#   |             | | | | ___  ___| |_  |_   _|_ _  __ _ ___               |
#   |             | |_| |/ _ \/ __| __|   | |/ _` |/ _` / __|              |
#   |             |  _  | (_) \__ \ |_    | | (_| | (_| \__ \              |
#   |             |_| |_|\___/|___/\__|   |_|\__,_|\__, |___/              |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   | Manage the variable config.wato_host_tags -> The set of tags to be   |
#   | assigned to hosts and that is the basis of the rules.                |
#   +----------------------------------------------------------------------+
def mode_hosttags(phase):
    if phase == "title":
        return _("Manage host tag groups")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Tag group"), make_link([("mode", "edit_hosttag")]), "new")
        return

    hosttags = load_hosttags()

    if phase == "action":
        del_id = html.var("_delete")
        if del_id:
            for e in hosttags:
                if e[0] == del_id:
                    # In case of tag group deletion, the operations is a pair of tag_id
                    # and list of choice-ids.
                    operations = [ x[0] for x in e[2] ]

            message = rename_host_tags_after_confirmation(del_id, operations)
            if message:
                hosttags = [ e for e in hosttags if e[0] != del_id ]
                save_hosttags(hosttags)
                rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts                
                log_pending(None, "edit-hosttags", _("Removed host tag group %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        move_nr = html.var("_move")
        if move_nr != None:
            if html.check_transaction():
                move_nr = int(move_nr)
                if move_nr > 0:
                    dir = 1
                else:
                    move_nr = -move_nr
                    dir = -1
                moved = hosttags[move_nr]
                del hosttags[move_nr]
                hosttags[move_nr+dir:move_nr+dir] = [moved]
                save_hosttags(hosttags)
                config.wato_host_tags = hosttags
                log_pending(None, "edit-hosttags", _("Changed order of host tag groups"))
        return

    if len(hosttags) == 0:
        render_main_menu([
            ("edit_hosttag", _("Create new tag group"), "new", "hosttags",
            _("Click here to create a first host tag group. For each tag group a dropdown choice or "
              "checkbox will be added to the folder and host properties. When defining rules, host tags "
              "are the fundament of the rules' conditions.")),])

    else:
        html.write("<h3>" + _("Host tag groups") + "</h3>")
        html.write("<table class=data>")
        html.write("<tr>" + 
                   "<th>" + _("Actions") + "</th>"
                   "<th>" + _("ID") + "</th>"
                   "<th>" + _("Title") + "</th>"
                   "<th>" + _("Type") + "</th>"
                   "<th>" + _("Choices") + "</th>"
                   "<th>" + _("Demonstration") + "</th>"
                   "<th></th>"
                   "</tr>")
        odd = "even"
        for nr, (tag_id, title, choices) in enumerate(hosttags):
            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)
            edit_url     = make_link([("mode", "edit_hosttag"), ("edit", tag_id)])
            delete_url   = html.makeactionuri([("_delete", tag_id)])
            html.write("<td>")
            if nr == 0:
                empty_icon_button()
            else:
                icon_button(html.makeactionuri([("_move", str(-nr))]), 
                            _("Move this tag group one position up"), "up")
            if nr == len(hosttags) - 1:
                empty_icon_button()
            else:
                icon_button(html.makeactionuri([("_move", str(nr))]),
                            _("Move this tag group one position down"), "down")
            icon_button(delete_url, _("Delete this tag group"), "delete")
            html.write("</td>")
            html.write("<td>%s</td>" % tag_id)
            html.write("<td>%s</td>" % title)
            html.write("<td>%s</td>" % (len(choices) == 1 and _("Checkbox") or _("Dropdown")))
            html.write("<td class=number>%d</td>" % len(choices))
            html.write("<td>")
            html.begin_form("tag_%s" % tag_id)
            host_attribute["tag_%s" % tag_id].render_input(None)
            html.end_form()
            html.write("</td>")
            html.write("<td class=buttons>")
            html.buttonlink(edit_url, _("Edit"))
            html.write("</td>")

            html.write("</tr>")
        html.write("</table>")


def mode_edit_hosttag(phase):
    tag_id = html.var("edit")
    new = tag_id == None

    if phase == "title":
        if new:
            return _("Create new tag group")
        else:
            return _("Edit tag group")

    elif phase == "buttons":
        html.context_button(_("All Hosttags"), make_link([("mode", "hosttags")]), "back")
        return

    hosttags = load_hosttags()
    if new:
        tag_id = None
        title = ""
        choices = []
    else:
        for id, tit, ch in hosttags:
            if id == tag_id:
                title = tit
                choices = ch
                break

    if phase == "action":
        if html.transaction_valid():
            if new:
                html.check_transaction() # use up transaction id
                tag_id = html.var("tag_id").strip()
                if len(tag_id) == 0:
                    raise MKUserError("tag_id", _("Please specify an ID for your tag group."))
                if not re.match("^[-a-z0-9A-Z_]*$", tag_id):
                    raise MKUserError("tag_id", _("Invalid tag group ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                for tgid, tit, ch in config.wato_host_tags:
                    if tgid == tag_id:
                        raise MKUserError("tag_id", _("The tag group ID %s is already used by the tag group '%s'.") % (tag_id, tit))

            title = html.var_utf8("title").strip()
            if not title:
                raise MKUserError("title", _("Please specify a title for your host tag group."))

            nr = 0
            new_choices = []
            have_none_tag = False
            while html.has_var("id_%d" % nr):
                id = html.var("id_%d" % nr).strip()
                descr = html.var_utf8("descr_%d" % nr).strip()
                if id or descr:
                    if not re.match("^[-a-z0-9A-Z_]*$", id):
                        raise MKUserError("id_%d" % nr, _("Invalid tag ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                    if not descr:
                        raise MKUserError("descr_%d" % nr, _("Please supply a description for the tag with the ID %s.") % id)
                    if not id:
                        id = None
                        if have_none_tag:
                            raise MKUserError("id_%d" % nr, _("Only on tag may be empty."))
                        have_none_tag = True
                    new_choices.append((id, descr))
                if id:
                    # Make sure this ID is not used elsewhere
                    for tgid, tit, ch in config.wato_host_tags:
                        if tgid != tag_id:
                            for e in ch:
                                # Check primary and secondary tags
                                if id == e[0] or len(e) > 2 and id in e[2]:
                                    raise MKUserError("id_%d" % nr, 
                                      _("The tag ID '%s' is already being used by the choice "
                                        "'%s' in the tag group '%s'.") % 
                                        ( id, e[1], tit ))

                nr += 1
            if len(new_choices) == 0:
                raise MKUserError("id_0", _("Please specify at least on tag."))
            if len(new_choices) == 1 and new_choices[0][0] == None:
                raise MKUserError("id_0", _("Tags with only one choice must have an ID."))

            if new:
                taggroup = tag_id, title, new_choices
                hosttags.append(taggroup)
                save_hosttags(hosttags)
                config.wato_host_tags = hosttags
                declare_host_tag_attributes()
                rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts                
                log_pending(None, "edit-hosttags", _("Created new host tag group '%s'") % tag_id)
                return "hosttags", _("Created new host tag group '%s'") % title
            else:
                new_hosttags = []
                for entry in hosttags:
                    if entry[0] == tag_id:
                        new_hosttags.append((tag_id, title, new_choices))
                    else:
                        new_hosttags.append(entry)

                # This is the major effort of WATO when it comes to 
                # host tags: renaming and deleting of tags that might be
                # in use by folders, hosts and rules. First we create a
                # kind auf "patch" from the old to the new tags. The renaming
                # of a tag is detected by comparing the titles. Addition
                # of new tags is not a problem and need not be handled.
                operations = {}

                # Detect renaming
                new_by_title = dict([(tit, tag) for (tag, tit) in new_choices])
                for tag, tit in choices:
                    if tit in new_by_title:
                        new_tag = new_by_title[tit]
                        if new_tag != tag:
                            operations[tag] = new_tag # might be None

                # Detect removal
                for tag, tit in choices:
                   if tag != None \
                       and tag not in [ e[0] for e in new_choices ] \
                       and tag not in operations:
                       # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
                       operations[tag] = False

                # Now check, if any folders, hosts or rules are affected
                message = rename_host_tags_after_confirmation(tag_id, operations)
                if message:
                    save_hosttags(new_hosttags)
                    config.wato_host_tags = new_hosttags
                    declare_host_tag_attributes()
                    rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts                
                    log_pending(None, "edit-hosttags", _("Edited host tag group %s (%s)") % (message, tag_id))
                    return "hosttags", message != True and message or None

        return "hosttags"



    html.begin_form("hosttaggroup")
    html.write("<table class=form>")

    # Tag ID
    html.write("<tr><td class=legend>")
    html.write(_("Internal ID") + "<br><i>")
    html.write(_("The internal ID of the tag group is used to store the tag's "
                 "value in the host properties. It cannot be changed later.</i>"))
    html.write("</td><td class=content>")
    if new:
        html.text_input("tag_id")
        html.set_focus("tag_id")
    else:
        html.write(tag_id) 
    html.write("</td></tr>")

    # Title
    html.write("<tr><td class=legend>")
    html.write(_("Title") + "<br><i>" + _("A description of this tag group</i>"))
    html.write("</td><td class=content>")
    html.text_input("title", title, size = 30)
    html.write("</td></tr>")

    # Choices
    num_choices = 16
    html.write("<tr><td class=legend>")
    html.write(_("Choices") + "<br><i>" +
               _("The first choice of a tag group will be its default value. "
                 "If a tag group has only one choice, it will be displayed "
                 "as a checkbox and set or not set the only tag. If it has "
                 "more choices you may leave at most one tag id empty. A host "
                 "with that choice will not get any tag of this group.<br><br>"
                 "The tag ID must contain only of letters, digits and "
                 "underscores.<br><br><b>Renaming tags ID:</b> if you want "
                 "to rename the ID of a tag, then please make sure that you do not "
                 "change its title at the same time! Otherwise WATO will not "
                 "be able to detect the renaming and cannot exchange the tags "
                 "in all folders, hosts and rules accordingly.</i>"))
    html.write("</td><td class=content>")
    html.write("<table>")
    html.write("<tr><th>%s</th><th>%s</th></tr>" % 
        (_("Tag ID"), _("Description")))
    for nr in range(max(num_choices, len(choices))):
        if nr < len(choices):
            tag_id, descr = choices[nr]
        else:
            tag_id, descr = "", ""
        if tag_id == None:
            tag_id = "" # for empty tag
        html.write("<tr><td>")
        html.text_input("id_%d" % nr, tag_id, size=10)
        html.write("</td><td>")
        html.text_input("descr_%d" % nr, descr, size=30)
        html.write("</td></tr>")
    html.write("</table>")
    html.write("</td></tr>")


    # Button and end
    html.write("<tr><td colspan=2 class=buttons>")
    html.button("save", _("Save"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()




def load_hosttags():
    filename = multisite_dir + "hosttags.mk"
    if not os.path.exists(filename):
        return []
    try:
        vars = { "wato_host_tags" : [] }
        execfile(filename, vars, vars)
        return vars["wato_host_tags"]
    
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %  
                          (filename, e)))
        return []

def save_hosttags(hosttags):
    make_nagios_directory(multisite_dir)
    out = file(multisite_dir + "hosttags.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("wato_host_tags += \\\n%s\n" % pprint.pformat(hosttags))

def rename_host_tags_after_confirmation(tag_id, operations):
    mode = html.var("_repair")
    if mode == "abort":
        raise MKUserError("id_0", "Please refine your changes or go back to the list of tag groups.")
    elif mode:
        if type(operations) == list: # make attribute unknown to system, important for save() operations
            undeclare_host_tag_attribute(tag_id)
        affected_folders, affected_hosts, affected_rulespecs = \
        change_host_tags_in_folders(tag_id, operations, mode, g_root_folder)
        return _("Modified folders: %d, modified hosts: %d, modified rulesets: %d" %
            (len(affected_folders), len(affected_hosts), len(affected_rulespecs)))

    message = ""
    affected_folders, affected_hosts, affected_rulespecs = \
        change_host_tags_in_folders(tag_id, operations, "check", g_root_folder)

    if affected_folders:
        message += _("Affected folders with an explicit reference to this tag group and that are affected by the change") + ":<ul>"
        for folder in affected_folders:
            message += '<li><a href="%s">%s</a></li>' % (
                make_link_to([("mode", "editfolder")], folder),
                folder["title"])
            message += "</ul>"

    if affected_hosts:
        message += _("Hosts where this tag group is explicitely set and that are effected by the change") + ":<ul><li>"
        for nr, host in enumerate(affected_hosts):
            if nr > 20:
                message += "... (%d more)" % len(affected_hosts - 20)
                break
            elif nr > 0:
                message += ", "

            message += '<a href="%s">%s</a>' % (
                make_link([("mode", "edithost"), ("host", host[".name"])]),
                host[".name"])
        message += "</li></ul>"

    if affected_rulespecs:
        message += _("Rulesets that contain rules with references to the changed tags") + ":<ul>"
        for rulespec in affected_rulespecs:
            message += '<li><a href="%s">%s</a></li>' % (
                make_link([("mode", "edit_ruleset"), ("varname", rulespec["varname"])]),
                rulespec["title"])
        message += "</ul>"

    if not message and type(operations) == tuple: # deletion of unused tag group
        html.write("<div class=really>")
        html.begin_form("confirm")
        html.write(_("Please confirm the deletion of the tag group."))
        html.button("_abort", _("Abort"))
        html.button("_do_confirm", _("Proceed"))
        html.hidden_fields(add_action_vars = True)
        html.end_form()
        html.write("</div>")

    elif message:
        if type(operations) == list:
            wato_html_head(_("Confirm tag deletion"))
        else:
            wato_html_head(_("Confirm tag modifications"))
        html.write("<div class=really>")
        html.write("<h3>" + _("Your modifications affects some objects") + "</h3>")
        html.write(message)
        html.write("<br>" + _("WATO can repair things for you. It can rename tags in folders, host and rules. "
                              "Removed tag groups will be removed from hosts and folders, removed tags will be "
                              "replaced with the default value for the tag group (for hosts and folders). What "
                              "rules concern, you have to decide how to proceed."))
        html.begin_form("confirm")

        # Check if operations contains removal
        if type(operations) == list:
            have_removal = True
        else:
            have_removal = False
            for new_val in operations.values():
                if not new_val:
                    have_removal = True
                    break

        if len(affected_rulespecs) > 0 and have_removal:
            html.write("<br><b>" + _("Some tags that are used in rules have been removed by you. What "
                       "shall we do with that rules?") + "</b><ul>")
            html.radiobutton("_repair", "remove", True, _("Just remove the affected tags from the rules."))
            html.write("<br>")
            html.radiobutton("_repair", "delete", False, _("Delete rules containing tags that have been removed, if tag is used in a positive sense. Just remove that tag if it's used negated."))
        else:
            html.write("<ul>")
            html.radiobutton("_repair", "repair", True, _("Fix affected folders, hosts and rules."))

        html.write("<br>")
        html.radiobutton("_repair", "abort", False, _("Abort your modifications."))
        html.write("</ul>")

        html.button("_do_confirm", _("Proceed"), "")
        html.hidden_fields(add_action_vars = True)
        html.end_form()
        html.write("</div>")
        return False

    return True

# operation == None -> tag group is deleted completely
def change_host_tags_in_folders(tag_id, operations, mode, folder):
    need_save = False
    affected_folders = []
    affected_hosts = []
    affected_rulespecs = []
    attrname = "tag_" + tag_id
    attributes = folder["attributes"]
    if attrname in attributes: # this folder has set the tag group in question
        if type(operations) == list: # deletion of tag group
            if attrname in attributes:
                affected_folders.append(folder)
                if mode != "check":
                    del attributes[attrname]
                    need_save = True
        else:
            current = attributes[attrname]
            if current in operations:
                affected_folders.append(folder)
                if mode != "check":
                    new_tag = operations[current]
                    if new_tag == False: # tag choice has been removed -> fall back to default
                        del attributes[attrname]
                    else:
                        attributes[attrname] = new_tag
                    need_save = True
    if need_save:
        save_folder(folder)

    for subfolder in folder[".folders"].values():
        aff_folders, aff_hosts, aff_rulespecs = change_host_tags_in_folders(tag_id, operations, mode, subfolder)
        affected_folders += aff_folders
        affected_hosts += aff_hosts
        affected_rulespecs += aff_rulespecs
    
    load_hosts(folder)
    affected_hosts += change_host_tags_in_hosts(folder, tag_id, operations, mode, folder[".hosts"])
    affected_rulespecs += change_host_tags_in_rules(folder, tag_id, operations, mode) 
    return affected_folders, affected_hosts, affected_rulespecs

def change_host_tags_in_hosts(folder, tag_id, operations, mode, hostlist):
    need_save = False
    affected_hosts = []
    for hostname, host in hostlist.items():
        attrname = "tag_" + tag_id
        if attrname in host:
            if type(operations) == list: # delete complete tag group 
                affected_hosts.append(host)
                if mode != "check":
                    del host[attrname]
                    need_save = True
            else:
                if host[attrname] in operations:
                    affected_hosts.append(host)
                    if mode != "check":
                        new_tag = operations[host[attrname]]
                        if new_tag == False: # tag choice has been removed -> fall back to default
                            del host[attrname]
                        else:
                            host[attrname] = new_tag
                        need_save = True
    if need_save:
        save_hosts(folder)
    return affected_hosts


# The function parses all rules in all rulesets and looks
# for host tags that have been removed or renamed. If tags
# are removed then the depending on the mode affected rules
# are either deleted ("delete") or the vanished tags are
# removed from the rule ("remove").
def change_host_tags_in_rules(folder, tag_id, operations, mode):
    need_save = False
    affected_rulespecs = []
    all_rulesets = load_rulesets(folder)
    for varname, ruleset in all_rulesets.items():
        rulespec = g_rulespecs[varname]
        rules_to_delete = set([])
        for nr, rule in enumerate(ruleset):
            modified = False
            value, tag_specs, host_list, item_list = parse_rule(rulespec, rule)
            
            # Handle deletion of complete tag group
            if type(operations) == list: # this list of tags to remove
                for tag in operations:
                    if tag != None and (tag in tag_specs or "!"+tag in tag_specs):
                        modified = True
                        if rulespec not in affected_rulespecs:
                            affected_rulespecs.append(rulespec)
                        if tag in tag_specs and mode == "delete":
                            rules_to_delete.add(nr)
                        elif tag in tag_specs:
                            tag_specs.remove(tag)
                        elif "+"+tag in tag_specs:
                            tag_specs.remove("!"+tag)
        
            # Removal or renamal of single tag choices
            else:
                for old_tag, new_tag in operations.items():
                    # The case that old_tag is None (an empty tag has got a name)
                    # cannot be handled when it comes to rules. Rules do not support
                    # such None-values.
                    if not old_tag:
                        continue

                    if old_tag in tag_specs or ("!" + old_tag) in tag_specs:
                        modified = True
                        if rulespec not in affected_rulespecs:
                            affected_rulespecs.append(rulespec)
                        if mode != "check":
                            if old_tag in tag_specs:
                                tag_specs.remove(old_tag)
                                if new_tag:
                                    tag_specs.append(new_tag)
                                elif mode == "delete":
                                    rules_to_delete.add(nr)
                            # negated tag has been renamed or removed 
                            if "!"+old_tag in tag_specs:
                                tag_specs.remove("!"+old_tag)
                                if new_tag:
                                    tag_specs.append("!"+new_tag)
                                # the case "delete" need not be handled here. Negated
                                # tags can always be removed without changing the rule's
                                # behaviour.
            if modified:
                ruleset[nr] = construct_rule(rulespec, value, tag_specs, host_list, item_list)
                need_save = True

        rules_to_delete = list(rules_to_delete)
        rules_to_delete.sort()
        for nr in rules_to_delete[::-1]:
            del ruleset[nr]

    if need_save:
        save_rulesets(folder, all_rulesets)
    affected_rulespecs.sort(cmp = lambda a, b: cmp(a["title"], b["title"]))
    return affected_rulespecs



#   +----------------------------------------------------------------------+
#   |           ____        _        _____    _ _ _                        |
#   |          |  _ \ _   _| | ___  | ____|__| (_) |_ ___  _ __            |
#   |          | |_) | | | | |/ _ \ |  _| / _` | | __/ _ \| '__|           |
#   |          |  _ <| |_| | |  __/ | |__| (_| | | || (_) | |              |
#   |          |_| \_\\__,_|_|\___| |_____\__,_|_|\__\___/|_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | WATO's awesome rule editor: Let's user edit rule based parameters    |
#   | from main.mk.                                                        |
#   +----------------------------------------------------------------------+
def mode_rulesets(phase):
    only_host = html.var("host", "")
    only_local = html.var("local")

    if phase == "title":
        if only_host:
            return _("Rule sets for for hosts %s") % only_host
        else:
            return _("Rule sets for hosts and services")

    elif phase == "buttons":
        if only_host:
            html.context_button(only_host,
                 make_link([("mode", "edithost"), ("host", only_host)]), "back")
        else:
            global_buttons()
            if config.may("wato.hosts") or config.may("wato.seeall"):
                html.context_button(_("Folder"), make_link([("mode", "folder")]), "folder")
        return
    
    elif phase == "action":
        return

    if not only_host:
        render_folder_path(keepvarnames = ["mode", "local"])
    
    html.begin_form("local")
    html.checkbox("local", False, onclick="form.submit();")
    if only_host:
        html.write(" " + _("show only rulesets that contain rules explicitely listing the host <b>%s</b>." %
            only_host))
    else:
        html.write(" " + _("Show only rulesets that contain rules in the current folder."))
    html.write(' <img align=absbottom class=icon src="images/icon_localrule.png"> ')
    html.hidden_fields()
    html.end_form()
    html.write("<br>")

    # Load all rules from all folders. Hope this doesn't take too much time.
    # We need this information only for displaying the number of rules in 
    # each set.

    if only_local and not only_host:
        all_rulesets = {}
        rs = load_rulesets(g_folder)
        for varname, rules in rs.items():
            all_rulesets.setdefault(varname, [])
            all_rulesets[varname] += [ (g_folder, rule) for rule in rules ]
    else:
        all_rulesets = load_all_rulesets()

    groupnames = g_rulespec_groups.keys()
    groupnames.sort()

    something_shown = False
    # Loop over all ruleset groups
    for groupname in groupnames:
        # Show information about a ruleset
        title_shown = False
        for rulespec in g_rulespec_groups[groupname]: 
            
            varname = rulespec["varname"]
            valuespec = rulespec["valuespec"]
            rules = all_rulesets.get(varname, [])
            num_rules = len(rules)
            if num_rules == 0 and only_local:
                continue

            # Handle case where a host is specified
            rulespec = g_rulespecs[varname]
            this_host = False
            if only_host:
                num_local_rules = 0
                for f, rule in rules:
                    value, tag_specs, host_list, item_list = parse_rule(rulespec, rule)
                    if only_host and only_host in host_list:
                        num_local_rules += 1
            else:
                num_local_rules = len([ f for (f,r) in rules if f == g_folder ])

            if only_local and num_local_rules == 0:
                continue

            if not title_shown:
                if something_shown:
                    html.write("</table>")
                    html.end_foldable_container()
                    html.write("<br>")
                html.begin_foldable_container("rulesets", groupname, False, groupname, indent=False)
                html.write('<table class="data rulesets">')
                html.write("<tr><th>" + _("Rule set") + "</th>"
                           "<th>" + _("Check_MK Variable") + "</th><th>" + _("Rules") + "</th></tr>\n")
                odd = "even"
                title_shown = True

            something_shown = True
            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)

            url_vars = [("mode", "edit_ruleset"), ("varname", varname)]
            if only_host:
                url_vars.append(("host", only_host))
            view_url = make_link(url_vars)

            html.write('<td class=title><a href="%s">%s</a></td>' % (view_url, rulespec["title"]))
            display_varname = ':' in varname and '%s["%s"]' % tuple(varname.split(":")) or varname
            html.write('<td class=varname><tt>%s</tt></td>' % display_varname)
            html.write('<td class=number>')
            if num_local_rules:
                if only_host:
                    title = _("There are %d rules explicitely listing this host." % num_local_rules)
                else:
                    title = _("There are %d rules defined in the current folder." % num_local_rules) 
                html.write('<img title="%s" align=absmiddle class=icon src="images/icon_localrule.png"> ' %
                    title)
            html.write("%d</td>" % num_rules)
            html.write('</tr>')

    if something_shown:
        html.write("</table>")
        html.end_foldable_container()

    else:
        if only_host:
            html.write("<div class=info>" + _("There are no rules with an exception for the host <b>%s</b>.") % only_host + "</div>")
        else:
            html.write("<div class=info>" + _("There are no rules defined in this folder.") + "</div>")

    
def mode_edit_ruleset(phase):
    varname = html.var("varname")
    rulespec = g_rulespecs[varname]
    hostname = html.var("host", "")
    item = eval(html.var("item", "None"))

    if hostname:
        hosts = load_hosts(g_folder)
        host = hosts.get(hostname)
        if not host: 
            hostname = None # host not found. Should not happen

    if phase == "title":
        title = rulespec["title"]
        if hostname:
            title += _(" for host %s") % hostname
        if html.has_var("item") and rulespec["itemtype"]:
            title += _(" and %s '%s'") % (rulespec["itemname"], item)
        return title

    elif phase == "buttons":
        html.context_button(_("All rulesets"), 
              make_link([("mode", "rulesets"), ("host", hostname)]), "back")
        if hostname:
            html.context_button(_("Services"), 
                 make_link([("mode", "inventory"), ("host", hostname)]), "back")
        return

    elif phase == "action":
        # Folder for the rule actions is defined by _folder
        rule_folder = g_folders[html.var("_folder", html.var("folder"))]
        rulesets = load_rulesets(rule_folder) 
        rules = rulesets.get(varname, [])

        if html.var("_new_rule") or html.var("_new_host_rule"):
            if html.check_transaction():
                if html.var("_new_rule"):
                    hostname = None
                    item = None
                new_rule = create_rule(rulespec, hostname, item)
                if hostname:
                    rules[0:0] = [new_rule]
                else:
                    rules.append(new_rule)
                save_rulesets(rule_folder, rulesets)
                log_pending(None, "edit-ruleset", 
                      _("Created new rule in ruleset %s in folder %s") % (rulespec["title"], rule_folder["title"]))
            return

        rulenr = int(html.var("_rulenr")) # rule number relativ to folder
        action = html.var("_action")

        if action == "delete":
            c = wato_confirm(_("Confirm"), _("Delete rule number %d of folder '%s'?") 
                % (rulenr + 1, rule_folder["title"]))
            if c:
                del rules[rulenr]
                save_rulesets(rule_folder, rulesets)
                log_pending(None, "edit-ruleset", 
                      _("Deleted rule in ruleset '%s'") % rulespec["title"])
                return
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload 

        elif action == "insert":
            if not html.check_transaction():
                return None # browser reload
            if g_folder == rule_folder:
                rules[rulenr:rulenr] = [rules[rulenr]]
                save_rulesets(rule_folder, rulesets)
            else:
                folder_rulesets = load_rulesets(g_folder)
                folder_rules = folder_rulesets.setdefault(varname, [])
                folder_rules.append(rules[rulenr])
                save_rulesets(g_folder, folder_rulesets)

            log_pending(None, "edit-ruleset", 
                  _("Inserted new rule in ruleset %s") % rulespec["title"])
            return

        else:
            if not html.check_transaction():
                return None # browser reload
            rule = rules[rulenr]
            del rules[rulenr]
            if action == "up":
                rules[rulenr-1:rulenr-1] = [ rule ]
            else:
                rules[rulenr+1:rulenr+1] = [ rule ]
            save_rulesets(rule_folder, rulesets)
            log_pending(None, "edit-ruleset", 
                     _("Changed order of rules in ruleset %s") % rulespec["title"])
            return

    if not hostname:
        render_folder_path(keepvarnames = ["mode", "varname"])

    html.write("<h3>" + rulespec["title"] + "</h3>")
    if rulespec["help"]:
        html.write("<div class=info>%s</div>" % rulespec["help"])

    # Collect all rulesets
    all_rulesets = load_all_rulesets()
    ruleset = all_rulesets.get(varname)
    if not ruleset:
        html.write("<div class=info>" + _("There are no rules defined in this set.") + "</div>")

    else:
        html.write('<table class="data ruleset">')
        html.write("<tr>"
                   "<th>" + _("#") + "</th>" 
                   "<th>" + _("Actions") + "</th>"
                   "<th>" + _("Folder") + "</th>"
                   "<th>" + _("Value") + "</th>"
                   "<th>" + _("Conditions") + "</th>"
                   "<th></th>" # Edit
                   "<th></th>" # Several icons
                   "</tr>\n")

        odd = "odd"
        alread_matched = False
        match_keys = set([]) # in case if match = "dict"
        last_folder = None
        for rulenr in range(0, len(ruleset)):
            folder, rule = ruleset[rulenr]
            if folder != last_folder:
                first_in_group = True
                rel_rulenr = 0
                # Count how many of the following rules are located in the same
                # folder
                row_span = 1
                while rulenr + row_span < len(ruleset) and ruleset[rulenr + row_span][0] == folder:
                    row_span += 1
                last_folder = folder
            else:
                first_in_group = False
            last_in_group = rulenr == len(ruleset) - 1 or ruleset[rulenr+1][0] != folder
                
            odd = odd == "odd" and "even" or "odd"
            value, tag_specs, host_list, item_list = parse_rule(rulespec, rule)
            html.write('<tr class="data %s0">' % odd)

            # Rule number
            html.write("<td class=number>%d</td>" % (rulenr + 1))

            # Actions
            html.write("<td class=\"buttons rulebuttons\">")
            if not first_in_group:
                rule_button("up", _("Move this rule one position up"), folder, rel_rulenr)
            else:
                rule_button(None)
            if not last_in_group:
                rule_button("down", _("Move this rule one position down"), folder, rel_rulenr)
            else:
                rule_button(None)
            rule_button("insert", _("Insert a copy of this rule into the folder '%s'") 
                        % g_folder["title"], folder, rel_rulenr)
            rule_button("delete", _("Delete this rule"), folder, rel_rulenr)
            html.write("</td>")


            # Folder
            if first_in_group:
                alias_path = get_folder_aliaspath(folder, show_main = False)
                html.write('<td rowspan=%d>%s</td>' % (row_span, alias_path))

            # Value
            html.write('<td class=value>\n')
            if hostname:
                reason = rule_matches_host_and_item(
                    rulespec, tag_specs, host_list, item_list, folder, g_folder, hostname, item)
                # Handle case where dict is constructed from rules
                if reason == True and rulespec["match"] == "dict": 
                    if len(value) == 0:
                        title = _("This rule matches, but does not define any parameters.")
                        img = 'imatch'
                    else:
                        new_keys = set(value.keys())
                        if match_keys.isdisjoint(new_keys):
                            title = _("This rule matches and defines new parameters.")
                            img = 'match'
                        elif new_keys.issubset(match_keys):
                            title = _("This rule matches, but all of its parameters are overridden by previous rules.")
                            img = 'imatch'
                        else:
                            title = _("This rule matches, but some of its parameters are overridden by previous rules.")
                            img = 'pmatch'
                        match_keys.update(new_keys)

                elif reason == True and (not alread_matched or rulespec["match"] == "all"):
                    title = _("This rule matches for the host '%s'") % hostname
                    if rulespec["itemtype"]:
                        title += _(" and the %s '%s'.") % (rulespec["itemname"], item)
                    else:
                        title += "."
                    img = 'match'
                    alread_matched = True
                elif reason == True:
                    title = _("This rule matches, but is overridden by a previous rule.")
                    img = 'imatch'
                    alread_matched = True
                else:
                    title = _("This rule does not match: %s") % reason
                    img = 'nmatch'
                html.write('<img align=absmiddle title="%s" class=icon src="images/icon_rule%s.png"> ' % (title, img))
            if rulespec["valuespec"]:
                value_html = rulespec["valuespec"].value_to_text(value)
            else:
                img = value and "yes" or "no"
                title = value and _("This rule results in a positive outcome.") \
                              or  _("this rule results in a negative outcome.")
                value_html = '<img align=absmiddle title="%s" src="images/rule_%s.png">' % (title, img)
            html.write('%s</td>\n' % value_html)

            # Conditions
            html.write("<td>")
            render_conditions(rulespec, tag_specs, host_list, item_list, varname, folder)
            html.write("</td>")
            
            # Edit
            html.write("<td class=buttons>")
            url = make_link([
                ("mode", "edit_rule"), 
                ("varname", varname), 
                ("rulenr", rel_rulenr), 
                ("host", hostname),
                ("item", repr(item)),
                ("rule_folder", folder[".path"])])
            html.buttonlink(url, _("Edit"))
            html.write("</td>")

            # Icons
            html.write("<td>")
            # "this folder"
            if not hostname and folder == g_folder:
                title = _("This rule is defined in the current folder.")
                html.write('<img title="%s" class=icon src="images/icon_localrule.png">' % title)
            elif hostname and hostname in host_list:
                title = _("This rule contains an exception for the host %s." % hostname)
                html.write('<img title="%s" class=icon src="images/icon_localrule.png">' % title)
            else:
                html.write('<img src="images/icon_trans.png" class=icon>')

            html.write("</td>")
            rel_rulenr += 1

        html.write('</table>')

    html.write("<p>" + _("Create a new rule: "))
    html.begin_form("new_rule")
    if hostname:
        title = _("Exception rule for host %s" % hostname)
        if rulespec["itemtype"]:
            title += _(" and %s '%s'") % (rulespec["itemname"], item)
        html.button("_new_host_rule", title)
        html.write(" " + _("or") + " ")
    html.button("_new_rule", _("General rule in folder: "))
    html.select("folder", folder_selection(g_root_folder))
    html.write("</p>\n")
    html.hidden_fields()
    html.end_form()


def folder_selection(folder, depth=0):
    if depth:
        title_prefix = "&nbsp;&nbsp;&nbsp;" * depth + "` " + "- " * depth
    else:
        title_prefix = ""
    sel = [ (folder[".path"], title_prefix + folder["title"]) ]

    for subfolder in folder[".folders"].values():
        sel += folder_selection(subfolder, depth + 1)
    return sel



def create_rule(rulespec, hostname=None, item=None):
    new_rule = []
    valuespec = rulespec["valuespec"]
    if valuespec:
        new_rule.append(valuespec.canonical_value())
    if hostname:
        new_rule.append([hostname])
    else:
        new_rule.append(ALL_HOSTS) # bottom: default to catch-all rule
    if rulespec["itemtype"]:
        if item != None:
            new_rule.append(["%s$" % item])
        else:
            new_rule.append([""])
    return tuple(new_rule)



def rule_button(action, help=None, folder=None, rulenr=0):
    if action == None:
        empty_icon_button()
    else:
        vars = [("_folder", folder[".path"]), 
          ("_rulenr", str(rulenr)), 
          ("_action", action)]
        if html.var("host"):
            vars.append(("host", html.var("host")))
        url = html.makeactionuri(vars)
        icon_button(url, help, action)

def empty_icon_button():
    html.write('<img class=trans src="images/trans.png">')

def icon_button(url, help, icon):
    html.write('<a href="%s">'
               '<img class=iconbutton title="%s" src="images/button_%s_lo.png" ' 
               'onmouseover=\"hilite_icon(this, 1)\" '
               'onmouseout=\"hilite_icon(this, 0)\">'
               '</a>\n' % (url, help, icon))


def parse_rule(ruleset, orig_rule):
    rule = orig_rule
    try:
        # Extract value from front, if rule has a value
        if ruleset["valuespec"]:
            value = rule[0]
            rule = rule[1:]
        else:
            if rule[0] == NEGATE:
                value = False
                rule = rule[1:]
            else:
                value = True

        # Extract liste of items from back, if rule has items
        if ruleset["itemtype"]:
            item_list = rule[-1]
            rule = rule[:-1]
        else:
            item_list = None

        # Rest is host list or tag list + host list
        if len(rule) == 1:
            tag_specs = []
            host_list = rule[0]
        else:
            tag_specs = rule[0]
            host_list = rule[1]

        # Remove folder tag from tag list
        tag_specs = filter(lambda t: not t.startswith("/"), tag_specs)

        return value, tag_specs, host_list, item_list # (item_list currently not supported)

    except Exception, e:
        raise MKGeneralException(_("Invalid rule <tt>%s</tt>") % (orig_rule,))



def rule_matches_host_and_item(rulespec, tag_specs, host_list, item_list, 
                               rule_folder, host_folder, hostname, item):
    reasons = []
    host = host_folder[".hosts"][hostname]
    if not (
        (hostname in host_list) 
        or 
        (("!"+hostname) not in host_list 
         and len(host_list) > 0 
         and host_list[-1] == ALL_HOSTS[0])):
         reasons.append(_("The host name does not match."))

    tags_match = True
    for tag in tag_specs:
        if tag[0] != '/' and tag[0] != '!' and tag not in host[".tags"]:
            reasons.append(_("The host is missing the tag %s" % tag))
        elif tag[0] == '!' and tag[1:] in host[".tags"]:
            reasons.append(_("The host has the tag %s" % tag))

    if not is_indirect_parent_of(host_folder, rule_folder):
        reasons.append(_("The rule does not apply to the folder of the host."))

    # Check items
    if rulespec["itemtype"]:
        item_matches = False
        for i in item_list:
            if re.match(i, str(item)):
                item_matches = True
                break
        if not item_matches:
            reasons.append(_("The %s %s does not match this rule.") % 
                   (rulespec["itemname"], item))

    if len(reasons) == 0:
        return True
    else:
        return " ".join(reasons)

def is_indirect_parent_of(pfolder, sfolder):
    return pfolder == sfolder or \
      ('.parent' in pfolder and 
      is_indirect_parent_of(pfolder[".parent"], sfolder))


def construct_rule(ruleset, value, tag_specs, host_list, item_list):
    if ruleset["valuespec"]:
        rule = [ value ]
    elif not value:
        rule = [ NEGATE ]
    else:
        rule = []
    if tag_specs != []:
        rule.append(tag_specs)
    rule.append(host_list)
    if item_list != None:
        rule.append(item_list)
    return tuple(rule)


def tag_alias(tag):
    for id, title, tags in config.wato_host_tags:
        for t in tags:
            if t[0] == tag:
                return t[1]

def render_conditions(ruleset, tagspecs, host_list, item_list, varname, folder):
    html.write("<ul class=conditions>")

    # Host tags
    for tagspec in tagspecs:
        if tagspec[0] == '!':
            negate = True
            tag = tagspec[1:]
        else:
            negate = False
            tag = tagspec


        html.write('<li class="condition">')
        alias = tag_alias(tag)
        if alias:
            if negate:
                html.write(_("Host is <b>" + _("not") + "</b> of type "))
            else:
                html.write(_("Host is of type "))
            html.write("<b>" + alias + "</b>")
        else:
            if negate:
                html.write(_("Host has <b>not</b> the tag ") + "<tt>" + tag + "</tt>")
            else:
                html.write(_("Host has the tag ") + "<tt>" + tag + "</tt>")
        html.write('</li>')

    # Explicit list of hosts
    if host_list != ALL_HOSTS:
        condition = None
        if host_list == []:
            condition = _("This rule does <b>never</b> apply!")
        elif host_list[-1] != ALL_HOSTS[0]:
            tt_list = [ "<tt><b>%s</b></tt>" % t for t in host_list ]
            if len(host_list) == 1:
                condition = _("Host name is %s") % tt_list[0]
            else:
                condition = _("Host name is ") + ", ".join(tt_list[:-1])
                condition += _(" or ") + tt_list[-1]
        elif host_list[0][0] == '!':
            hosts = [ h[1:] for h in host_list[:-1] ]
            condition = _("Host is <b>not</b> one of ") + ", ".join(hosts)
        # other cases should not occur, e.g. list of explicit hosts
        # plus ALL_HOSTS.
        if condition:
            html.write('<li class="condition">%s</li>' % condition)

    # Item list
    if ruleset["itemtype"] and item_list != ALL_SERVICES:
        tt_list = []
        for t in item_list:
            if t.endswith("$"):
                tt_list.append("%s <tt><b>%s</b></tt>" % (_("is"), t[:-1]))
            else:
                tt_list.append("%s <tt><b>%s</b></tt>" % (_("begins with"), t))
        
        if ruleset["itemtype"] == "service":
            condition = _("Service name ") + " or ".join(tt_list)
        elif ruleset["itemtype"] == "item":
            condition = ruleset["itemname"] + " " + " or ".join(tt_list)
        html.write('<li class="condition">%s</li>' % condition)

    html.write("</ul>")


def ruleeditor_hover_code(varname, rulenr, mode, boolval, folder=None):
    if boolval in [ True, False ]:
        url = html.makeactionuri([("_rulenr", rulenr), ("_action", "toggle")])
    else:
        url = make_link_to([("mode", mode), ("varname", varname), ("rulenr", rulenr)], folder or g_folder)
    return \
       ' onmouseover="this.style.cursor=\'pointer\'; this.style.backgroundColor=\'#b7ced3\';" ' \
       ' onmouseout="this.style.cursor=\'auto\'; this.style.backgroundColor=\'#a7bec3\';" ' \
       ' onclick="location.href=\'%s\'"' % url



def get_rule_conditions(ruleset):
    # Tag list
    tag_list = []
    for id, title, tags in config.wato_host_tags:
        mode = html.var("tag_" + id)
        tagvalue = html.var("tagvalue_" + id)
        if mode == "is":
            tag_list.append(tagvalue)
        elif mode == "isnot":
            tag_list.append("!" + tagvalue)

    # Host list
    if not html.get_checkbox("explicit_hosts"):
        host_list = ALL_HOSTS
    else:
        negate = html.get_checkbox("negate_hosts")
        nr = 0
        host_list = []
        while True:
            var = "host_%d" % nr
            host = html.var(var)
            if nr > config.wato_num_itemspecs and not host:
                break
            if host:
                if negate:
                    host = "!" + host
                host_list.append(host)
            nr += 1
        # append ALL_HOSTS to negated host lists
        if len(host_list) > 0 and host_list[0][0] == '!':
            host_list += ALL_HOSTS
        elif len(host_list) == 0 and negate:
            host_list = ALL_HOSTS # equivalent

    # Item list
    itemtype = ruleset["itemtype"]
    if itemtype:
        explicit = html.get_checkbox("explicit_services")
        if not explicit:
            item_list = [ "" ]
        else:
            nr = 0
            item_list = []
            while True:
                var = "item_%d" % nr
                item = html.var(var)
                if nr > config.wato_num_itemspecs and not item:
                    break
                if item:
                    item_list.append(item)
                nr += 1
    else:
        item_list = None

    return tag_list, host_list, item_list


def mode_edit_rule(phase):
    rulenr = int(html.var("rulenr"))
    varname = html.var("varname")
    rulespec = g_rulespecs[varname]

    if phase == "title":
        return _("Edit rule %s") % rulespec["title"]

    elif phase == "buttons":
        html.context_button(_("All rules"), 
             make_link([("mode", "edit_ruleset"), 
                        ("varname", varname), 
                        ("host", html.var("host", "")),
                        ("item", html.var("item", "None"))]), "back")
        return

    folder = g_folders[html.var("rule_folder")]
    rulesets = load_rulesets(folder)
    rules = rulesets[varname]
    rule = rules[rulenr]
    valuespec = rulespec.get("valuespec")
    value, tag_specs, host_list, item_list = parse_rule(rulespec, rule)

    if phase == "action":
        if html.check_transaction():
            # CONDITION
            tag_specs, host_list, item_list = get_rule_conditions(rulespec)
            new_rule_folder = g_folders[html.var("new_rule_folder")]
            # VALUE
            if valuespec:
                value = get_edited_value(valuespec)
            else:
                value = html.var("value") == "yes"
            rule = construct_rule(rulespec, value, tag_specs, host_list, item_list)
            if new_rule_folder == folder:
                rules[rulenr] = rule
                save_rulesets(folder, rulesets)
                log_pending(None, "edit-rule", _("Changed properties of rule %s in folder %s") % 
                        (rulespec["title"], folder["title"]))
            else: # Move rule to new folder
                del rules[rulenr]
                save_rulesets(folder, rulesets)
                rulesets = load_rulesets(new_rule_folder)
                rules = rulesets.setdefault(varname, [])
                rules.append(rule)
                save_rulesets(new_rule_folder, rulesets)
                log_pending(None, "edit-rule", _("Changed properties of rule %s, moved rule from "
                            "folder %s to %s") % (rulespec["title"], folder["title"], 
                            new_rule_folder["title"]))

        return "edit_ruleset"

    html.begin_form("rule_editor")
    html.write('<table class="form ruleeditor">\n')

    # Value
    html.write("<tr><td class=title colspan=2><h3>%s</h3></td></tr>\n" % 
                _("Value"))
    if valuespec:
        value = rule[0]
        edit_value(valuespec, value)
        valuespec.set_focus("ve")
    else:
        html.write("<tr><td class=legend></td>\n")
        html.write("<td class=content>")
        for posneg, img in [ ("positive", "yes"), ("negative", "no")]:
            val = img == "yes"
            html.write('<img align=top src="images/rule_%s.png"> ' % img)
            html.radiobutton("value", img, value == val, _("Make the outcome of the ruleset <b>%s</b><br>") % posneg)
        html.write("</td></tr>\n")

    # Conditions
    html.write("<tr><td class=title colspan=2><h3>%s</h3></td></tr>" % 
                _("Conditions"))

    # Rule folder
    html.write("<tr><td class=legend>%s<br><i>%s</i></td>" % 
               (_("Folder"), _("The rule is only applied to hosts directly in or below this folder.")))
    html.write("<td class=content>")
    html.select("new_rule_folder", folder_selection(g_root_folder), folder[".path"])
    html.write("</td></tr>")

    # Host tags
    html.write("<tr><td class=legend>" + _("Host tags") + "<br><i>")
    html.write(_("The rule will only be applied to hosts fullfulling all of "
                 "of the host tag conditions listed here, even if they appear "
                 "in the list of explicit host names."))
    
    html.write("</i></td>")
    html.write("<td class=content>")
    if len(config.wato_host_tags) == 0:
        html.write(_("You have not configured any host tags. If you work with rules "
                     "you should better do so and add a <tt>wato_host_tags = ..</tt> "
                     "to your <tt>multisite.mk</tt>. You will find an example there."))
    else:
        html.write("<table>")
        for id, title, tags in config.wato_host_tags:
            html.write("<tr><td>%s: &nbsp;</td>" % title)
            default_tag = None
            ignore = True
            for t in tag_specs:
                if t[0] == '!':
                    n = True
                    t = t[1:]
                else:
                    n = False
                if t in [ x[0] for x in tags]:
                    ignore = False
                    negate = n
            if ignore:
                deflt = "ignore"
            elif negate:
                deflt = "isnot"
            else: 
                deflt = "is"

            html.write("<td>")
            html.select("tag_" + id, [
                ("ignore", _("ignore")), 
                ("is", _("is")), 
                ("isnot", _("isnot"))], deflt,
                onchange="wato_toggle_dropdownn(this, 'tag_sel_%s');" % id)
            html.write("</td><td>")
            if html.form_submitted():
                div_is_open = html.var("tag_" + id) != "ignore"
            else:
                div_is_open = deflt != "ignore"
            html.write('<div id="tag_sel_%s" style="white-space: nowrap; %s">' % (
                id, not div_is_open and "display: none;" or ""))
            html.select("tagvalue_" + id, [t[0:2] for t in tags if t[0] != None], deflt=default_tag)
            html.write("</div>")
            html.write("</td></tr>")
        html.write("</table>")
    html.write("</td></tr>")


    # Explicit hosts / ALL_HOSTS
    html.write("<tr><td class=legend>")
    html.write(_("Explicit hosts"))
    html.write("<br><i>")
    html.write(_("You can enter a number of explicit host names that rule should or should "
                 "not apply to here. Leave this option disabled if you want the rule to "
                 "apply for all hosts specified by the given tags."))
    html.write("</i></td><td class=content>")
    div_id = "div_all_hosts"

    checked = host_list != ALL_HOSTS
    html.checkbox("explicit_hosts", checked, onclick="wato_toggle_option(this, %r)" % div_id)
    html.write(" " + _("Specify explicit host names"))
    html.write('<div id="%s" style="display: %s">' % (
            div_id, not checked and "none" or ""))
    negate_hosts = len(host_list) > 0 and host_list[0].startswith("!")

    html.write("<table class=itemlist>")
    num_cols = 3
    for nr in range(config.wato_num_itemspecs):
        x = nr % num_cols
        if x == 0:
            html.write("<tr>")
        if nr < len(host_list) and host_list[nr] != ALL_HOSTS[0]:
            host_name = host_list[nr].strip("!")
        else:
            host_name = ""
        html.write("<td>")
        html.text_input("host_%d" % nr, host_name)
        html.write("</td>")
        if x == num_cols - 1:
            html.write("</tr>")
    while x < num_cols - 1:
        html.write("<td></td>")
        if x == num_cols - 1:
            html.write("</tr>")
        x += 1
    html.write("</table>")
    html.checkbox("negate_hosts", negate_hosts)
    html.write(" " + _("<b>Negate:</b> make Rule apply for <b>all but</b> the above hosts") + "\n")
    html.write("</div></td></tr>")

    # Itemlist
    itemtype = rulespec["itemtype"]
    if itemtype:
        html.write("<tr><td class=legend>")
        if itemtype == "service":
            html.write(_("Services") + "<br><i>" + 
                       _("Specify a list of service patterns this rule shall apply to. " 
                         "The patterns must match the <b>beginning</b> of the service "
                         "in question. Adding a <tt>$</tt> to the end forces an excact "
                         "match. Pattern use <b>regular expressions</b>. A <tt>.*</tt> will "
                         "match an arbitrary text.") + "</i>")
        elif itemtype == "checktype":
            html.write(_("Check types"))
        elif itemtype == "item":
            html.write(rulespec["itemname"].title())
            html.write("<br><i>")
            if rulespec["itemhelp"]:
                html.write(rulespec["itemhelp"])
            else:
                html.write(_("You can make the rule apply only on certain services of the "
                             "specified hosts. Do this by specifying explicit items to mach "
                             "here. <b>Note:</b> the match is done on the <u>beginning</u> "
                             "of the item in question. Regular expressions are interpreted, "
                             "so appending a <tt>$</tt> will force an exact match."))
        else:
            raise MKGeneralException("Invalid item type '%s'" % itemtype)

        html.write("</td><td class=content>")
        if itemtype:
            checked = len(item_list) > 0 and item_list[0] != ""
            div_id = "itemlist"
            html.checkbox("explicit_services", checked, onclick="wato_toggle_option(this, %r)" % div_id)
            html.write(" " + _("Specify explicit values"))
            html.write('<div id="%s" style="display: %s">' % (
                div_id, not checked and "none" or ""))
            html.write("<table class=itemlist>")
            num_cols = 3
            for nr in range(config.wato_num_itemspecs):
                x = nr % num_cols
                if x == 0:
                    html.write("<tr>")
                html.write("<td>")
                item = nr < len(item_list) and item_list[nr] or ""
                html.text_input("item_%d" % nr, item)
                html.write("</td>")
                if x == num_cols - 1:
                    html.write("</tr>")
            while x < num_cols - 1:
                html.write("<td></td>")
                if x == num_cols - 1:
                    html.write("</tr>")
                x += 1
            html.write("</table>")
            html.write(_("The entries here are regular expressions to match the beginning. "
                         "Add a <tt>$</tt> for an exact match. An arbitrary substring is matched "
                         "with <tt>.*</tt>"))
            html.write("</div>")
                
    html.write("<tr><td class=buttons colspan=2>")
    html.button("save", _("Save"))
    html.write("</td></tr>")
    html.write("</table>")
    html.hidden_fields()
    html.end_form()


def save_rulesets(folder, rulesets):
    make_nagios_directory(root_dir)
    path = root_dir + '/' + folder['.path'] + '/' + "rules.mk" 
    out = file(path, "w") 
    out.write("# Written by WATO\n# encoding: utf-8\n\n")

    for varname, rulespec in g_rulespecs.items():
        ruleset = rulesets.get(varname)
        if not ruleset:
            continue # don't save empty rule sets

        if ':' in varname:
            dictname, subkey = varname.split(':')
            out.write("\n%s.setdefault(%r, [])\n" % (dictname, subkey))
            out.write("%s[%r] += [\n" % (dictname, subkey))
        else:
            if rulespec["optional"]:
                out.write("\nif %s == None:\n    %s = []\n" % (varname, varname))
            out.write("\n%s += [\n" % varname)
        for rule in ruleset:
            save_rule(out, folder, rulespec, rule)
        out.write("]\n\n")

def save_rule(out, folder, rulespec, rule):
    out.write("  ( ")
    value, tag_specs, host_list, item_list = parse_rule(rulespec, rule)
    if rulespec["valuespec"]:
        out.write(repr(value) + ", ")
    elif not value:
        out.write("NEGATE, ")

    out.write("[")
    for tag in tag_specs:
        out.write(repr(tag))
        out.write(", ")
    if folder != g_root_folder:
        out.write("'/' + FOLDER_PATH + '/+'")
    out.write("], ")
    if len(host_list) > 0 and host_list[-1] == ALL_HOSTS[0]:
        if len(host_list) > 1:
            out.write(repr(host_list[:-1]))
            out.write(" + ALL_HOSTS")
        else:
            out.write("ALL_HOSTS")
    else:
        out.write(repr(host_list))

    if rulespec["itemtype"]:
        out.write(", ")
        if item_list == ALL_SERVICES:
            out.write("ALL_SERVICES")
        else:
            out.write(repr(item_list))

    out.write(" ),\n")




def load_rulesets(folder):
    # TODO: folder berücksichtigen
    path = root_dir + "/" + folder[".path"] + "/" + "rules.mk"
    vars = {
        "ALL_HOSTS"      : ALL_HOSTS,
        "ALL_SERVICES"   : [ "" ],
        "NEGATE"         : NEGATE,
        "FOLDER_PATH"    : folder[".path"],
        "FILE_PATH"      : folder[".path"] + "/hosts.mk",
    }
    # Prepare empty rulesets so that rules.mk has something to 
    # append to

    for varname, ruleset in g_rulespecs.items():
        if ':' in varname:
            dictname, subkey = varname.split(":")
            vars[dictname] = {}
        else:
            vars[varname] = []

    try:
        execfile(path, vars, vars)
    except:
        pass

    # Extract only specified rule variables
    rulevars = {} 
    for ruleset in g_rulespecs.values():
        varname = ruleset["varname"]
        # handle extra_host_conf:max_check_attempts
        if ':' in varname:
            dictname, subkey = varname.split(":")
            if dictname in vars:
                dictionary = vars[dictname]
                if subkey in dictionary:
                    rulevars[varname] = dictionary[subkey]
            # If this ruleset is not defined in rules.mk use empty list.
            if varname not in rulevars:
                rulevars[varname] = []

        else:
            if varname in vars:
                rulevars[varname] = vars[varname]
    return rulevars

# Load all rules of all folders into a dictionary that
# has the rules' varnames as keys and a list of (folder, rule)
# as values.
def load_rulesets_recursively(folder, all_rulesets):
    for subfolder in folder[".folders"].values():
        load_rulesets_recursively(subfolder, all_rulesets)

    rs = load_rulesets(folder)
    for varname, rules in rs.items():
        all_rulesets.setdefault(varname, [])
        all_rulesets[varname] += [ (folder, rule) for rule in rules ]

def load_all_rulesets():
    all_rulesets = {}
    load_rulesets_recursively(g_root_folder, all_rulesets)
    return all_rulesets


g_rulespecs = {}
g_rulespec_groups = {}
def register_rule(group, varname, valuespec = None, title = None, 
                  help = None, itemtype = None, itemname = None, 
                  itemhelp = None,
                  match = "first", optional = False):
    ruleset = {
        "group"     : group, 
        "varname"   : varname, 
        "valuespec" : valuespec, 
        "itemtype"  : itemtype, # None, "service", "checktype" or "checkitem"
        "itemname"  : itemname, # e.g. "mount point"
        "itemhelp"  : itemhelp, # a description of the item, only rarely used
        "match"     : match,
        "title"     : title or valuespec.title(),
        "help"      : help or valuespec.help(),
        "optional"  : optional, # rule may be None (like only_hosts)
        }

    g_rulespec_groups.setdefault(group, []).append(ruleset)
    g_rulespecs[varname] = ruleset
 
#   +----------------------------------------------------------------------+
#   |       _   _             _           ___        _    ____ ___         |
#   |      | | | | ___   ___ | | _____   ( _ )      / \  |  _ \_ _|        |
#   |      | |_| |/ _ \ / _ \| |/ / __|  / _ \/\   / _ \ | |_) | |         |
#   |      |  _  | (_) | (_) |   <\__ \ | (_>  <  / ___ \|  __/| |         |
#   |      |_| |_|\___/ \___/|_|\_\___/  \___/\/ /_/   \_\_|  |___|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The API allows addons to query information about configured hosts.   |
#   |                                                                      |
#   | Hooks are a way how addons can add own activities at certain points  |
#   | of time, e.g. when a host as been edited of the changes have been    | 
#   | activated.                                                           |
#   +----------------------------------------------------------------------+ 

# Inform plugins about changes of hosts. the_thing can be:
# a folder, a file or a host

g_hooks = {}

class API:
    def register_hook(self, name, func):
        g_hooks.setdefault(name, []).append(func)

    # Get a (flat) dictionary containing all hosts with their *effective*
    # attributes (containing all inherited and default values where appropriate).
    def get_all_hosts(self):
        load_all_folders()
        return collect_hosts(g_root_folder)

    # Find a folder by its path. Raise an exception if it does
    # not exist.
    def get_folder(self, path):
        load_all_folders()
        folder = g_folders.get(path)
        if folder:
            load_hosts(folder)
            return folder
        else:
            raise MKGeneralException("No WATO folder %s." % path)

    # Get the number of hosts recursive from the given folder
    def num_hosts_in_folder(self, folder):
        return num_hosts_in(folder, True)

    # Get all effective data of a host. Folder must be returned by get_folder()
    def get_host(self, folder, hostname):
        declare_host_tag_attributes()
        host = folder[".hosts"][hostname]
        eff = effective_attributes(host, folder)
        eff["name"] = hostname
        return eff

    # Update the attributes of the given host and returns the resulting host attributes
    # which have been persisted
    def update_host_attributes(self, host, attr):
        folder = g_folders.get(host["path"])
        load_hosts(folder)
        folder[".hosts"][host["name"]].update(attr)
        save_folder_and_hosts(folder)
        return folder[".hosts"][host["name"]]

    # Return displayable information about host (call with with result vom get_host())
    def get_host_painted(self, host): 
        declare_host_tag_attributes()
        result = []
        for attr, topic in host_attributes:   
            attrname = attr.name()
            if attrname in host:
                tdclass, content = attr.paint(host[attrname], host["name"])
                result.append((attr.title(), content))
        return result

    # Get information about the folder and directory tree. 
    # This is useful for components that display hosts in 
    # the tree (e.g. the status GUI).
    def get_folder_tree(self):
        load_all_folders()
        num_hosts_in(g_root_folder) # sets ".total_hosts"
        return g_root_folder

    # sort list of folders or files by their title
    def sort_by_title(self, folders):
        def folder_cmp(f1, f2):
            return cmp(f1["title"].lower(), f2["title"].lower())
        folders.sort(cmp = folder_cmp)
        return folders

    # Create an URL to a certain WATO folder.
    def link_to_path(self, path):
        return "wato.py?mode=folder&folder=" + htmllib.urlencode(path)

    # Create an URL to the edit-properties of a host.
    def link_to_host(self, hostname):
        return "wato.py?" + htmllib.urlencode_vars(
        [("mode", "edithost"), ("host", hostname)])

    # Same, but links to services of that host
    def link_to_host_inventory(self, hostname):
        return "wato.py?" + htmllib.urlencode_vars(
        [("mode", "inventory"), ("host", hostname)])

    # Return the title of a folder - which is given as a string path
    def get_folder_title(self, path):
        load_all_folders() # TODO: use in-memory-cache
        folder = g_folders.get(path)
        if folder:
            return folder["title"]
        else:
            return path

    # Returns the number of not activated changes.
    def num_pending_changes(self):
        return len(parse_audit_log("pending"))

    # BELOW ARE PRIVATE HELPER FUNCTIONS

    def _cleanup_directory(self, thing):
        # drop 'parent' entry, recursively
        def drop_internal(folder):
            new_folder = {}
            new_folder.update(folder)
            if ".parent" in new_folder:
                del new_folder[".parent"]
            if ".folders" in new_folder:
                new_folder[".folders"] = drop_internal_dict(new_folder[".folders"])
            return new_folder

        def drop_internal_dict(self, folderdict): 
            new_dict = {}
            for name, thing in folderdict.items():
                new_dict[name] = drop_internal(thing)
            return new_dict

        return drop_internal(thing)

api = API()



# internal helper functions for API
def collect_hosts(folder):
    load_hosts(folder)
    hosts = {}

    # Collect hosts in this folder
    for hostname, host in folder[".hosts"].items():
        hosts[hostname] = effective_attributes(host, folder)
        hosts[hostname]["path"] = folder[".path"]

    # Collect hosts from subfolders
    for subfolder in folder[".folders"].values():
        hosts.update(collect_hosts(subfolder))

    return hosts

def hook_registered(name):
    """ Returns True if at least one function is registered for the given hook """
    return g_hooks.get(name, []) != []

def call_hooks(name, *args):
    n = 0
    for hk in g_hooks.get(name, []):
        n += 1
        try:
            hk(*args)
        except Exception, e:
            import traceback, StringIO
            txt = StringIO.StringIO()
            t, v, tb = sys.exc_info()
            traceback.print_exception(t, v, tb, None, txt)
            html.show_error("<h3>" + _("Error executing hook") + " %s #%d: %s</h3><pre>%s</pre>" % (name, n, e, txt.getvalue()))

def call_hook_hosts_changed(folder):
    if "hosts-changed" in g_hooks:
        hosts = collect_hosts(folder)
        call_hooks("hosts-changed", hosts)

    # The same with all hosts!
    if "all-hosts-changed" in g_hooks:
        hosts = collect_hosts(g_root_folder)
        call_hooks("all-hosts-changed", hosts)

def call_hook_folder_created(folder):
    if 'folder-created' in g_hooks:
        call_hooks("folder-created", folder)

def call_hook_folder_deleted(folder):
    if 'folder-deleted' in g_hooks:
        call_hooks("folder-deleted", folder)

def call_hook_activate_changes():
    """
    This hook is executed when one applies the pending configuration changes
    from wato.

    But it is only excecuted when there is at least one function
    registered for this host.

    The registered hooks are called with a dictionary as parameter which
    holds all available with the hostnames as keys and the attributes of
    the hosts as values.
    """
    if hook_registered('activate-changes'):
        call_hooks("activate-changes", collect_hosts(g_root_folder))


#   +----------------------------------------------------------------------+
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Functions needed at various places                                   |
#   +----------------------------------------------------------------------+

def host_status_button(hostname, viewname):
    html.context_button(_("Status"), 
       "view.py?" + htmllib.urlencode_vars([
           ("view_name", viewname), 
           ("filename", g_folder[".path"] + "/hosts.mk"),
           ("host",     hostname),
           ("site",     "")]), 
           "status")  # TODO: support for distributed WATO

def folder_status_button(viewname = "allhosts"):
    html.context_button(_("Status"), 
       "view.py?" + htmllib.urlencode_vars([
           ("view_name", viewname), 
           ("wato_folder", g_folder[".path"])]), 
           "status")  # TODO: support for distributed WATO

def global_buttons():
    changelog_button()
    home_button()

def home_button():
    html.context_button(_("Home"), make_link([("mode", "main")]), "home")

def snapshots_button():
    if config.may("wato.snapshots"):
        html.context_button(_("Backup / Restore"),  make_link([("mode", "snapshot")]), "backup")

def search_button():
    html.context_button(_("Search"), make_link([("mode", "search")]), "search")

def changelog_button():
    pending = parse_audit_log("pending")
    if len(pending) > 0:
        buttontext = "<b>%d " % len(pending) + _("Changes")  + "</b>"
        hot = True
    else:
        buttontext = _("No Changes")
        hot = False
    html.context_button(buttontext, make_link([("mode", "changelog")]), "wato_changes", hot)

def find_host(host):
    return find_host_in(host, g_root_folder)

def find_host_in(host, folder):
    hosts = load_hosts(folder)
    if host in hosts:
        return folder

    for f in folder.get(".folders").values():
        p = find_host_in(host, f)
        if p != None:
            return p

def num_hosts_in(folder, recurse=True):
    if not "num_hosts" in folder:
        load_hosts(folder)
        save_folder(folder)

    if not recurse:
        return folder["num_hosts"]

    num = 0
    for subfolder in folder[".folders"].values():
        num += num_hosts_in(subfolder, True)
    num += folder["num_hosts"]
    folder[".total_hosts"] = num # store for later usage
    return num

# This is a dummy implementation which works without tags
# and implements only a special case of Check_MK's real logic.
def host_extra_conf(hostname, conflist):
    for value, hostlist in conflist:
        if hostname in hostlist:
            return [value]
    return []

# Create link keeping the context to the current folder / file
def make_link(vars):
    vars = vars + [ ("folder", g_folder[".path"]) ]
    return html.makeuri_contextless(vars)

# Small helper for creating a link with a context to a given folder
def make_link_to(vars, folder):
    vars = vars + [ ("folder", folder[".path"]) ]
    return html.makeuri_contextless(vars)

def make_action_link(vars):
    return make_link(vars + [("_transid", html.current_transid())])


# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    wato_html_head(html_title)
    return html.confirm(message)

def wato_html_head(title):
    global g_html_head_open
    if not g_html_head_open:
        g_html_head_open = True
        html.header(title)
        html.write("<div class=wato>\n")

def render_folder_path(the_folder = 0, link_to_last = False, keepvarnames = ["mode"]):
    if the_folder == 0:
        the_folder = g_folder

    keepvars = [ (name, html.var(name)) for name in keepvarnames ]
    def render_component(folder):
        return '<a href="%s">%s</a>' % (
               html.makeuri_contextless([
                  ("folder", folder[".path"])] + keepvars), folder["title"])

    folders = []
    folder = the_folder.get(".parent")
    while folder:
        folders.append(folder)
        folder = folder.get(".parent")

    parts = []
    for folder in folders[::-1]:
        parts.append(render_component(folder))
    if link_to_last:
        parts.append(render_component(the_folder))
    else:
        parts.append("<b>" + the_folder["title"] + "</b>")

    html.write("<div class=folderpath>%s\n" % "<i> / </i>".join(parts))

    subfolders = the_folder[".folders"]
    if len(subfolders) > 0 and not link_to_last:
        html.write("<i> / </i>")
        html.write("<form method=GET name=folderpath>")
        options = [ (sf[".path"], sf["title"]) for sf in subfolders.values() ]
        html.sorted_select("folder", [ ("", "") ] + options, onchange="folderpath.submit();", attrs={"class" : "folderpath"})
        for var in keepvarnames:
            html.hidden_field(var, html.var(var))
        html.write("</form>")
    html.write("</div>")

def may_see_hosts():
    return config.may("wato.use") and \
       (config.may("wato.seeall") or config.may("wato.hosts"))

#   +----------------------------------------------------------------------+
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Prepare plugin-datastructures and load WATO plugins                  |
#   +----------------------------------------------------------------------+

modes = {
   "main"               : ([], mode_main),
   "folder"             : (["hosts"], mode_folder),
   "newfolder"          : (["hosts", "manage_folders"], lambda phase: mode_editfolder(phase, True)),
   "editfolder"         : (["hosts" ], lambda phase: mode_editfolder(phase, False)),
   "newhost"            : (["hosts", "manage_hosts"], lambda phase: mode_edithost(phase, True)),
   "edithost"           : (["hosts"], lambda phase: mode_edithost(phase, False)),
   "firstinventory"     : (["hosts", "services"], lambda phase: mode_inventory(phase, True)),
   "inventory"          : (["hosts"], lambda phase: mode_inventory(phase, False)),
   "search"             : (["hosts"], mode_search),
   "bulkinventory"      : (["hosts", "services"], mode_bulk_inventory),
   "bulkedit"           : (["hosts", "edit_hosts"], mode_bulk_edit),
   "bulkcleanup"        : (["hosts", "edit_hosts"], mode_bulk_cleanup),
   "changelog"          : ([], mode_changelog),
   "snapshot"           : (["snapshots"], mode_snapshot),
   "globalvars"         : (["global"], mode_globalvars),
   "edit_configvar"     : (["global"], mode_edit_configvar),
   "rulesets"           : (["rulesets"], mode_rulesets),
   "edit_ruleset"       : (["rulesets"], mode_edit_ruleset),
   "edit_rule"          : (["rulesets"], mode_edit_rule),
   "host_groups"        : (["groups"], lambda phase: mode_groups(phase, "host")),
   "service_groups"     : (["groups"], lambda phase: mode_groups(phase, "service")),
   "contact_groups"     : (["users"], lambda phase: mode_groups(phase, "contact")),
   "edit_host_group"    : (["groups"], lambda phase: mode_edit_group(phase, "host")),
   "edit_service_group" : (["groups"], lambda phase: mode_edit_group(phase, "service")),
   "edit_contact_group" : (["users"], lambda phase: mode_edit_group(phase, "contact")),
   "timeperiods"        : (["timeperiods"], mode_timeperiods),
   "edit_timeperiod"    : (["timeperiods"], mode_edit_timeperiod),
   "sites"              : (["sites"], mode_sites),
   "edit_site"          : (["sites"], mode_edit_site),
   "users"              : (["users"], mode_users),
   "edit_user"          : (["users"], mode_edit_user),
   "roles"              : (["users"], mode_roles),
   "edit_role"          : (["users"], mode_edit_role),
   "hosttags"           : (["hosttags"], mode_hosttags),
   "edit_hosttag"       : (["hosttags"], mode_edit_hosttag),
}

extra_buttons = [
]

load_web_plugins("wato", globals())
