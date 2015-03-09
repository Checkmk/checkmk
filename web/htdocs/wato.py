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

#   .--README--------------------------------------------------------------.
#   |               ____                _                                  |
#   |              |  _ \ ___  __ _  __| |  _ __ ___   ___                 |
#   |              | |_) / _ \/ _` |/ _` | | '_ ` _ \ / _ \                |
#   |              |  _ <  __/ (_| | (_| | | | | | | |  __/                |
#   |              |_| \_\___|\__,_|\__,_| |_| |_| |_|\___|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A few words about the implementation details of WATO.                |
#   `----------------------------------------------------------------------'

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
#   ".siteid"         -> This attribute is mandatory for host objects and optional for folder
#                        objects. In case of hosts and single WATO setup it is always None.
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
# g_configvars -> dictionary of variables in main.mk that can be configured
#           via WATO.
#
# g_html_head_open -> True, if the HTML head has already been rendered.


#.
#   .--Init----------------------------------------------------------------.
#   |                           ___       _ _                              |
#   |                          |_ _|_ __ (_) |_                            |
#   |                           | || '_ \| | __|                           |
#   |                           | || | | | | |_                            |
#   |                          |___|_| |_|_|\__|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Importing, Permissions, global variables                             |
#   `----------------------------------------------------------------------'

import sys, pprint, socket, re, subprocess, time, datetime,  \
       shutil, tarfile, cStringIO, math, fcntl, pickle, random
import config, table, multitar, userdb, hooks, weblib, login
from hashlib import sha256
from lib import *
from valuespec import *
import forms


class MKAutomationException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

# Some paths and directories
root_dir           = defaults.check_mk_configdir + "/wato/"
multisite_dir      = defaults.default_config_dir + "/multisite.d/wato/"
sites_mk           = defaults.default_config_dir + "/multisite.d/sites.mk"
var_dir            = defaults.var_dir + "/wato/"
log_dir            = var_dir + "log/"
snapshot_dir       = var_dir + "snapshots/"
php_api_dir        = var_dir + "php-api/"
repstatus_file     = var_dir + "replication_status.mk"


ALL_HOSTS    = [ '@all' ]
ALL_SERVICES = [ "" ]
NEGATE       = '@negate'
NO_ITEM      = {} # Just an arbitrary unique thing

# Actions for log_pending
RESTART      = 1
SYNC         = 2
SYNCRESTART  = 3
AFFECTED     = 4
LOCALRESTART = 5

g_folder = None
g_root_folder = None
g_folders = {}
g_html_head_open = False

#.
#   .--Main----------------------------------------------------------------.
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
#   `----------------------------------------------------------------------'

wato_styles = [ "pages", "wato", "status" ]

def page_handler():
    global g_html_head_open
    g_html_head_open = False

    if not config.wato_enabled:
        raise MKGeneralException(_("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
                                   " in your <tt>multisite.mk</tt> if you want to use WATO."))
    current_mode = html.var("mode") or "main"
    modeperms, modefunc = modes.get(current_mode, ([], None))

    if modeperms != None and not config.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))


    # If we do an action, we aquire an exclusive lock on the complete
    # WATO.
    if html.is_transaction():
        lock_exclusive()

    try:
        # Make information about current folder and hosts available
        # To be able to perform a "factory reset" or a snapshot restore
        # even with a broken config ignore exceptions in this function
        # when running in "snapshot" mode
        prepare_folder_info()
    except:
        if current_mode == 'snapshot':
            pass
        else:
            raise

    if modefunc == None:
        html.header(_("Sorry"), stylesheets=wato_styles)
        html.begin_context_buttons()
        html.context_button(_("Main Menu"), make_link([("mode", "main")]), "home")
        html.end_context_buttons()
        html.message(_("This module has not yet been implemented."))
        html.footer()
        return

    # Check general permission for this mode
    if modeperms != None and not config.may("wato.seeall"):
        for pname in modeperms:
            if '.' not in pname:
                pname = "wato." + pname
            config.need_permission(pname)

    # Do actions (might switch mode)
    action_message = None
    if html.is_transaction():
        try:
            config.need_permission("wato.edit")

            # Even if the user has seen this mode because auf "seeall",
            # he needs an explicit access permission for doing changes:
            if config.may("wato.seeall"):
                if modeperms:
                    for pname in modeperms:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.need_permission(pname)

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
                if modeperms != None and not config.may("wato.seeall"):
                    for pname in modeperms:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.need_permission(pname)

        except MKUserError, e:
            action_message = e.message
            html.add_user_error(e.varname, e.message)

        except MKAuthException, e:
            action_message = e.reason
            html.add_user_error(None, e.reason)

    # Title
    html.header(modefunc("title"), stylesheets = wato_styles)
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

        # Show outcome of action
        if html.has_user_errors():
            html.show_error(action_message)
        elif action_message:
            html.message(action_message)

        # Show content
        modefunc("content")

    except MKGeneralException:
        raise

    except MKInternalError:
        html.unplug()
        raise

    except MKAuthException:
        raise

    except Exception, e:
        html.unplug()
        import traceback
        html.show_error(traceback.format_exc().replace('\n', '<br />'))

    html.write("</div>\n")
    if g_need_sidebar_reload == id(html):
        html.reload_sidebar()

    if config.wato_use_git and html.is_transaction():
        do_git_commit()

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

def lock_exclusive():
    aquire_lock(defaults.default_config_dir + "/multisite.mk")


def git_command(args):
    encoded_args = " ".join([ a.encode("utf-8") for a in args ])
    command = "cd '%s' && git %s 2>&1" % (defaults.default_config_dir, encoded_args)
    p = os.popen(command)
    output = p.read()
    status = p.close()
    if status != None:
        raise MKGeneralException(_("Error executing GIT command %s: %s") %
                (command.decode('utf-8'), output))

def shell_quote(s):
    return "'" + s.replace("'", "'\"'\"'") + "'"

def do_git_commit():
    author = shell_quote("%s <%s>" % (config.user_id, config.user_alias))
    git_dir = defaults.default_config_dir + "/.git"
    if not os.path.exists(git_dir):
        git_command(["init"])

        # Make sure that .gitignore-files are present and uptodate
        file(defaults.default_config_dir + "/.gitignore", "w").write("*\n!*.d\n!.gitignore\n*swp\n")
        for subdir in os.listdir(defaults.default_config_dir):
            if subdir.endswith(".d"):
                file(defaults.default_config_dir + "/" + subdir + "/.gitignore", "w").write("*\n!wato\n!wato/*\n")

        git_command(["add", ".gitignore", "*.d/wato"])
        git_command(["commit", "--untracked-files=no", "--author", author, "-m", shell_quote(_("Initialized GIT for Check_MK"))])

    # Only commit, if something is changed
    if os.popen("cd '%s' && git status --untracked-files=no --porcelain" % defaults.default_config_dir).read().strip():
        git_command(["add", "*.d/wato"])
        message = ", ".join(g_git_messages)
        if not message:
            message = _("Unknown configuration change")
        git_command(["commit", "--author", author, "-m", shell_quote(message)])



#.
#   .--Load/Save-----------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

def folder_dir(the_folder):
    return root_dir + the_folder[".path"]

# Save one folder (i.e. make sure the directory exist and write its .wato file)
def save_folder(folder):
    if folder.get(".lock"):
        raise MKAuthException(_("Sorry, you cannot edit this folder. It is locked."))

    # Remove temporary entries from the dictionary
    cleaned = dict([(k, v) for (k, v) in folder.iteritems() if not k.startswith('.') ])

    # Create the directory with the correct permissions (in case it doesn't exist)
    dir = folder_dir(folder)
    make_nagios_directory(dir)

    wato_filename = dir + "/.wato"
    config.write_settings_file(wato_filename, cleaned)

def save_folder_and_hosts(folder):
    if not folder.get(".lock"):
        save_folder(folder)
    if not folder.get(".lock_hosts"):
        save_hosts(folder)

def folder_config_exists(dir):
    return os.path.exists(dir + "/.wato")

# Load the meta-data of a folder (it's .wato file), register
# it in g_folders, load recursively all subfolders and then
# return the folder object. The case the .wato file is missing
# it will be assume to contain default values.
def load_folder(dir, name="", path="", parent=None, childs = True):
    fn = dir + "/.wato"
    try:
        folder = eval(file(fn).read())
    except:
        # .wato missing or invalid
        folder = {
            "title"      : name and name or _("Main directory"),
            "num_hosts"  : 0,
        }

    folder[".name"]        = name
    folder[".path"]        = path
    folder[".folders"]     = {}
    folder[".lock"]        = folder.get("lock", False)
    folder[".lock_subfolders"] = folder.get("lock_subfolders", False)
    folder[".lock_hosts"]  = False
    if parent:
        # Update reference to parent folder
        folder[".parent"] = parent

        # Update reference in parent folder
        parent[".folders"][name] = folder

    if "attributes" not in folder: # Make sure, attributes are always present
        folder["attributes"] = {}

    # Add information about the effective site of this folder
    if is_distributed():
        if "site" in folder["attributes"]:
            folder[".siteid"] = folder["attributes"]["site"]
        elif parent:
            folder[".siteid"] = parent[".siteid"]
        else:
            folder[".siteid"] = default_site()

    # Now look subdirectories
    if childs and os.path.exists(dir):
        for entry in os.listdir(dir):
            if entry[0] == '.': # entries '.' and '..'
                continue

            p = dir + "/" + entry

            if os.path.isdir(p):
                if path == "":
                    subpath = entry
                else:
                    subpath = path + "/" + entry
                f = load_folder(p, entry, subpath, folder)
                folder[".folders"][entry] = f

    g_folders[path] = folder
    return folder

# Reload a folder. This is called after the folder is modified,
# so that subsequent code has access to the correct folder
# meta data (such as .siteid)
def reload_folder(folder):
    have_hosts = ".hosts" in folder
    new_folder = load_folder(folder_dir(folder), folder[".name"], folder[".path"], folder.get(".parent"))
    if have_hosts: # hosts were loaded in old folder -> do this again
        load_hosts(new_folder)
    return new_folder

# Load the information about all folders - except the hosts
def load_all_folders():
    if not os.path.exists(root_dir):
        make_nagios_directories(root_dir)

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

def load_hosts(folder = None, force = False):
    if folder == None:
        folder = g_folder
    if ".hosts" not in folder or force:
        folder[".hosts"] = load_hosts_file(folder)
    folder["num_hosts"] = len(folder[".hosts"])
    return folder[".hosts"]

def reload_hosts(folder = None):
    load_hosts(folder, force = True)


def load_hosts_file(folder):
    hosts = {}

    filename = root_dir + folder[".path"] + "/hosts.mk"
    if os.path.exists(filename):
        variables = {
            "FOLDER_PATH"               : "",
            "ALL_HOSTS"                 : ALL_HOSTS,
            "all_hosts"                 : [],
            "clusters"                  : {},
            "ipaddresses"               : {},
            "explicit_snmp_communities" : {},
            "extra_host_conf"           : { "alias" : [] },
            "extra_service_conf"        : { "_WATO" : [] },
            "host_attributes"           : {},
            "host_contactgroups"        : [],
            "_lock"                     : False,
        }
        execfile(filename, variables, variables)
        nodes_of = {}
        # Add entries in clusters{} to all_hosts
        for cluster_with_tags, nodes in variables["clusters"].items():
            variables["all_hosts"].append(cluster_with_tags)
            nodes_of[cluster_with_tags.split('|')[0]] = nodes

        folder[".lock_hosts"] = variables["_lock"]

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
                host["alias"]           = alias
                host["ipaddress"]       = ipaddress
                host["snmp_community"]  = variables["explicit_snmp_communities"].get(hostname)

                # Retrieve setting for each individual host tag
                tags = set([ tag for tag in parts[1:] if tag != 'wato' and not tag.endswith('.mk') ])
                for attr, topic in host_attributes:
                    if isinstance(attr, HostTagAttribute):
                        tagvalue = attr.get_tag_value(tags)
                        host[attr.name()] = tagvalue

            # Add cluster nodes if this is a cluster
            if hostname in nodes_of:
                host[".nodes"] = nodes_of[hostname]

            # access to "raw" tags, needed for rule engine, remove implicit tags
            host[".tags"] = [ p for p in parts[1:] if p not in [ "wato", "//" ] ]

            # access to name of host, if key is not present
            host[".name"] = hostname

            # access to the folder object
            host['.folder'] = folder

            # Compute site attribute, because it is needed at various
            # places.
            if is_distributed():
                if "site" in host:
                    host[".siteid"] = host["site"]
                else:
                    host[".siteid"] = folder[".siteid"]
            else:
                host[".siteid"] = None

            hosts[hostname] = host


    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))
    return hosts

def save_hosts(folder = None):
    if folder == None:
        folder = g_folder

    if folder.get(".lock_hosts"):
        raise MKAuthException(_("Sorry, you cannot edit hosts in this folder. They are locked."))

    folder_path = folder[".path"]
    dirname = root_dir + folder_path
    filename = dirname + "/hosts.mk"

    if not os.path.isdir(dirname):
        make_nagios_directories(dirname)

    out = create_user_file(filename, 'w')
    out.write("# Written by WATO\n# encoding: utf-8\n\n")

    hosts = folder.get(".hosts", [])
    if len(hosts) == 0:
        if os.path.exists(filename):
            os.remove(filename)
        return

    all_hosts = [] # list of [Python string for all_hosts]
    clusters = [] # tuple list of (Python string, nodes)
    ipaddresses = {}
    explicit_snmp_communities = {}
    hostnames = hosts.keys()
    hostnames.sort()
    custom_macros = {} # collect value for attributes that are to be present in Nagios
    cleaned_hosts = {}
    for hostname in hostnames:
        nodes = hosts[hostname].get(".nodes")
        # Remove temporary entries from the dictionary
        cleaned_hosts[hostname] = dict([(k, v) for (k, v) in hosts[hostname].iteritems() if not k.startswith('.') ])

        host = cleaned_hosts[hostname]
        effective = effective_attributes(host, folder)
        ipaddress      = effective.get("ipaddress")
        snmp_community = effective.get("snmp_community")

        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag. Also other attributes
        # can set tags (e.g. the SiteAttribute)
        tags = set([])
        for attr, topic in host_attributes:
            value = effective.get(attr.name())
            tags.update(attr.get_tag_list(value))

        # Slave sites preserve any SiteAttribute tag
        if not is_distributed() and "site" in effective:
            tags.update(SiteAttribute().get_tag_list(effective["site"]))

        tagstext = "|".join(list(tags))
        if tagstext:
            tagstext += "|"
        hostentry = '"%s|%swato|/" + FOLDER_PATH + "/"' % (hostname, tagstext)

        if nodes:
            clusters.append((hostentry, nodes))
        else:
            all_hosts.append(hostentry)

        if ipaddress:
            ipaddresses[hostname] = ipaddress
        if snmp_community:
            explicit_snmp_communities[hostname] = snmp_community

        # Create contact group rule entries for hosts with explicitely set values
        # Note: since the type if this entry is a list, not a single contact group, all other list
        # entries coming after this one will be ignored. That way the host-entries have
        # precedence over the folder entries.

        if "contactgroups" in host:
            cgconfig = convert_cgroups_from_tuple(host["contactgroups"])
            cgs = cgconfig["groups"]
            use = cgconfig["use"]
            if use and cgs:
                out.write("\nhost_contactgroups += [\n")
                for cg in cgs:
                    out.write('    ( %r, [%r] ),\n' % (cg, hostname))
                out.write(']\n\n')

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

    if len(all_hosts) > 0:
        out.write("all_hosts += [\n")
        for entry in all_hosts:
            out.write('  %s,\n' % entry)
        out.write("]\n")

    if len(clusters) > 0:
        out.write("\nclusters.update({")
        for entry, nodes in clusters:
            out.write('\n  %s : %s,\n' % (entry, repr(nodes)))
        out.write("})\n")

    if len(ipaddresses) > 0:
        out.write("\n# Explicit IP addresses\n")
        out.write("ipaddresses.update(")
        out.write(pprint.pformat(ipaddresses))
        out.write(")\n")

    if len(explicit_snmp_communities) > 0:
        out.write("\n# Explicit SNMP communities\n")
        out.write("explicit_snmp_communities.update(")
        out.write(pprint.pformat(explicit_snmp_communities))
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
    perm_groups, contact_groups = collect_folder_groups(folder)
    if contact_groups:
        out.write("\nhost_contactgroups.append(\n"
                  "  ( %r, [ '/' + FOLDER_PATH + '/' ], ALL_HOSTS ))\n" % list(contact_groups))


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
    try:
        save_hosts(folder)
    except MKAuthException, e:
        # Ignore MKAuthExceptions of locked host.mk files
        pass

# returns the aliaspath of the given folder
def get_folder_aliaspath(folder, show_main = True):
    aliaspath = [folder['title']]
    while '.parent' in folder:
        folder = folder['.parent']
        if folder != g_root_folder or show_main:
            aliaspath.insert(0,folder['title'])
    return ' / '.join(aliaspath)

#.
#   .--Folders-------------------------------------------------------------.
#   |                   _____     _     _                                  |
#   |                  |  ___|__ | | __| | ___ _ __ ___                    |
#   |                  | |_ / _ \| |/ _` |/ _ \ '__/ __|                   |
#   |                  |  _| (_) | | (_| |  __/ |  \__ \                   |
#   |                  |_|  \___/|_|\__,_|\___|_|  |___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for showing a folder, bulk actions on hosts.                    |
#   '----------------------------------------------------------------------'

def mode_folder(phase):
    global g_folder

    auth_message = check_folder_permissions(g_folder, "read", False)
    auth_read = auth_message == True
    auth_write = check_folder_permissions(g_folder, "write", False) == True

    if phase == "title":
        return g_folder["title"]

    elif phase == "buttons":
        global_buttons()
        if config.may("wato.rulesets") or config.may("wato.seeall"):
            html.context_button(_("Rulesets"),        make_link([("mode", "ruleeditor")]), "rulesets")
            html.context_button(_("Manual Checks"),   make_link([("mode", "static_checks")]), "static_checks")
        if auth_read:
            html.context_button(_("Folder Properties"), make_link_to([("mode", "editfolder")], g_folder), "edit")
        if not g_folder.get(".lock_subfolders") and config.may("wato.manage_folders") and auth_write:
            html.context_button(_("New folder"),        make_link([("mode", "newfolder")]), "newfolder")
        if not g_folder.get(".lock_hosts") and config.may("wato.manage_hosts") and auth_write:
            html.context_button(_("New host"),    make_link([("mode", "newhost")]), "new")
            html.context_button(_("New cluster"), make_link([("mode", "newcluster")]), "new_cluster")
            html.context_button(_("Bulk Import"), make_link_to([("mode", "bulk_import")], g_folder), "bulk_import")
        if config.may("wato.services"):
            html.context_button(_("Bulk Discovery"), make_link([("mode", "bulkinventory"), ("all", "1")]),
                        "inventory")
        if not g_folder.get(".lock_hosts") and config.may("wato.parentscan") and auth_write:
            html.context_button(_("Parent scan"), make_link([("mode", "parentscan"), ("all", "1")]),
                        "parentscan")
        search_button()
        folder_status_button()
        if config.may("wato.random_hosts"):
            html.context_button(_("Random Hosts"), make_link([("mode", "random_hosts")]), "random")

    elif phase == "action":
        if html.var("_search"): # just commit to search form
            return

        ### Operations on SUBFOLDERS

        if html.var("_delete_folder"):
            if html.transaction_valid():
                delname = html.var("_delete_folder")
                del_folder = g_folder[".folders"][delname]
                config.need_permission("wato.manage_folders")
                if True != check_folder_permissions(g_folder, "write", False):
                    raise MKAuthException(_("Sorry. In order to delete a folder you need write permissions to its "
                                            "parent folder."))
                return delete_folder_after_confirm(del_folder)
            return

        elif html.has_var("_move_folder_to"):
            if html.check_transaction():
                if config.may("wato.manage_folders") and \
                    check_folder_permissions(g_folder, "write", False):
                    what_folder = g_folders[html.var("what_folder")]
                    path = html.var("_move_folder_to")
                    target_folder = g_folders[path]
                    mark_affected_sites_dirty(what_folder)
                    move_folder(what_folder, target_folder)
                    load_all_folders()
                    g_folder = g_folders[html.var("folder")]
                    # Folder hav been reloaded, so our object is invalid
                    target_folder = g_folders[path]
                    what_folder = target_folder[".folders"][what_folder[".name"]]
                    mark_affected_sites_dirty(what_folder)
                    log_pending(AFFECTED, what_folder, "move-folder",
                        _("Moved folder %s to %s") % (html.var("what_folder"), target_folder[".path"]))
            return


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
            config.need_permission("wato.move_hosts")
            hostname = html.var("host")
            check_folder_permissions(g_folder, "write")
            if hostname:
                move_host_to(hostname, html.var("_move_host_to"))
                return

        # bulk operation on hosts
        if not html.transaction_valid():
            return

        # Host table: No error message on search filter reset
        if html.var("_hosts_reset_sorting") or html.var("_hosts_sort"):
            return

        selected_hosts = get_hostnames_from_checkboxes()
        if len(selected_hosts) == 0:
            raise MKUserError(None,
            _("Please select some hosts before doing bulk operations on hosts."))

        if html.var("_bulk_inventory"):
            return "bulkinventory"

        elif html.var("_parentscan"):
            return "parentscan"

        # Deletion
        if html.var("_bulk_delete"):
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(g_folder, "write")
            return delete_hosts_after_confirm(selected_hosts)

        # Move
        elif html.var("_bulk_move"):
            config.need_permission("wato.edit_hosts")
            config.need_permission("wato.move_hosts")
            target_folder_name = html.var("bulk_moveto")
            if target_folder_name == "@":
                raise MKUserError("bulk_moveto", _("Please select the destination folder"))
            target_folder = g_folders[target_folder_name]
            num_moved = move_hosts_to(selected_hosts, target_folder_name)
            return None, _("Successfully moved %d hosts to %s") % (num_moved, target_folder["title"])

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
            config.need_permission("wato.edit_hosts")
            config.need_permission("wato.move_hosts")
            return move_to_imported_folders(selected_hosts)

        elif html.var("_bulk_edit"):
            return "bulkedit"

        elif html.var("_bulk_cleanup"):
            return "bulkcleanup"

    else:
        render_folder_path()

        if not auth_read:
            html.message(HTML('<img class=authicon src="images/icon_autherr.png"> %s' % html.attrencode(auth_message)))

        lock_messages = []
        if g_folder.get(".lock_hosts"):
            if g_folder[".lock_hosts"] == True:
                lock_messages.append(_("Hosts attributes locked (You cannot create, edit or delete hosts in this folder)"))
            else:
                lock_messages.append(g_folder[".lock_hosts"])
        if g_folder.get(".lock"):
            if g_folder[".lock"] == True:
                lock_messages.append(_("Folder attributes locked (You cannot edit the attributes of this folder)"))
            else:
                lock_messages.append(g_folder[".lock"])
        if g_folder.get(".lock_subfolders"):
            if g_folder[".lock_subfolders"] == True:
                lock_messages.append(_("Folder is locked (You cannot create or remove folders in this folder)"))
            else:
                lock_messages.append(g_folder[".lock_subfolders"])

        if len(lock_messages) > 0:
            lock_message = ", ".join(lock_messages)
            html.write("<div class=info>" + lock_message + "</div>")

        have_something = show_subfolders(g_folder)
        # Show hosts only if we have permission to this folder

        if True == check_folder_permissions(g_folder, "read", False):
            have_something = show_hosts(g_folder) or have_something

        if not have_something and auth_write:
            menu_items = []
            if not g_folder.get(".lock_hosts"):
                menu_items.extend([
                ("newhost", _("Create new host"), "new", "hosts",
                  _("Add a new host to the monitoring (agent must be installed)")),
                ("newcluster", _("Create new cluster"), "new_cluster", "hosts",
                  _("Use Check_MK clusters if an item can move from one host "
                    "to another at runtime"))])
            if not g_folder.get(".lock_subfolders"):
                menu_items.extend([
                ("newfolder", _("Create new folder"), "newfolder", "hosts",
                  _("Folders group your hosts, can inherit attributes and can have permissions."))
                ])
            render_main_menu(menu_items)

def prepare_folder_info():
    load_all_folders()            # load information about all folders
    create_sample_config()        # if called for the very first time!
    declare_host_tag_attributes() # create attributes out of tag definitions
    declare_site_attribute()      # create attribute for distributed WATO
    set_current_folder()          # set g_folder from HTML variable


def folder_title_path(path, withlinks = False):
    folder = g_folders.get(path)
    titles = []
    while (folder):
        title = folder["title"]
        if withlinks:
            title = "<a href='wato.py?mode=folder&folder=%s'>%s</a>" % (folder[".path"], title)
        titles.append(title)
        folder = folder.get(".parent")
    return titles[::-1]


def check_host_permissions(hostname, exception=True, folder=None):
    if folder == None:
        folder = g_folder

    if config.may("wato.all_folders"):
        return True
    host = folder[".hosts"][hostname]
    perm_groups, contact_groups = collect_host_groups(host, folder)

    # Get contact groups of user
    users = userdb.load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id].get("contactgroups",[])

    for c in user_cgs:
        if c in perm_groups:
            return True

    reason = _("Sorry, you have no permission on the host '<b>%s</b>'. The host's contact "
               "groups are <b>%s</b>, your contact groups are <b>%s</b>.") % \
               (hostname, ", ".join(perm_groups), ", ".join(user_cgs))
    if exception:
        raise MKAuthException(reason)
    return reason

def get_folder_permissions_of_users(users):
    folders = {}

    def get_flat_folders(folder):
        folders[folder['.path']] = folder
        for child in folder.get('.folders', {}).itervalues():
            get_flat_folders(child)

    get_flat_folders(get_folder_tree())

    permissions = {}

    users = userdb.load_users()
    for username in users.iterkeys():
        perms = {}
        for folder_path, folder in folders.iteritems():
            readable = check_folder_permissions(folder, 'read', False, username, users) == True
            writable = check_folder_permissions(folder, 'write', False, username, users) == True

            if readable or writable:
                perms[folder_path] = {}
                if readable:
                    perms[folder_path]['read'] = True
                if writable:
                    perms[folder_path]['write'] = True

        if perms:
            permissions[username] = perms
    return permissions

def check_folder_permissions(folder, how, exception=True, user = None, users = None):
    if not user:
        if config.may("wato.all_folders"):
            return True
        if how == "read" and config.may("wato.see_all_folders"):
            return True
    else:
        if config.user_may(user, "wato.all_folders"):
            return True
        if how == "read" and config.user_may(user, "wato.see_all_folders"):
            return True

    # Get contact groups of that folder
    perm_groups, cgs = collect_folder_groups(folder)

    if not user:
        user = config.user_id

    # Get contact groups of user
    if users == None:
        users = userdb.load_users()
    if user not in users:
        user_cgs = []
    else:
        user_cgs = users[user].get("contactgroups", [])

    for c in user_cgs:
        if c in perm_groups:
            return True

    reason = _("Sorry, you have no permissions to the folder <b>%s</b>. ") % folder["title"]
    if not perm_groups:
        reason += _("The folder is not permitted for any contact group.")
    else:
        reason += _("The folder's permitted contact groups are <b>%s</b>. ") % ", ".join(perm_groups)
        if user_cgs:
            reason += _("Your contact groups are <b>%s</b>.") %  ", ".join(user_cgs)
        else:
            reason += _("But you are not a member of any contact group.")
    reason += _("You may enter the folder as you might have permission on a subfolders, though.")

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

    cgconf = convert_cgroups_from_tuple(cgspec)
    cgs = cgconf["groups"]
    users = userdb.load_users()
    if config.user_id not in users:
        user_cgs = []
    else:
        user_cgs = users[config.user_id]["contactgroups"]
    for c in cgs:
        if c not in user_cgs:
            raise MKAuthException(_("Sorry, you cannot assign the contact group '<b>%s</b>' "
              "because you are not member in that group. Your groups are: <b>%s</b>") %
                 ( c, ", ".join(user_cgs)))


def get_folder_cgconf_from_attributes(attributes):
    v = attributes.get("contactgroups", ( False, [] ))
    cgconf = convert_cgroups_from_tuple(v)
    return cgconf

# Get all contact groups of a folder, while honoring recursive
# groups and permissions. Returns a pair of
# 1. The folders permitted groups (for WATO permissions)
# 2. The folders contact groups (for hosts)
def collect_folder_groups(folder, host=None):
    perm_groups = set([])
    host_groups = set([])
    effective_folder_attributes = effective_attributes(host, folder)
    cgconf = get_folder_cgconf_from_attributes(effective_folder_attributes)

    # First set explicit groups
    perm_groups.update(cgconf["groups"])
    if cgconf["use"]:
        host_groups.update(cgconf["groups"])

    # Now consider recursion
    if host:
        parent = folder
    elif ".parent" in folder:
        parent = folder['.parent']
    else:
        parent = None

    while parent:
        effective_folder_attributes = effective_attributes(None, parent)
        parconf = get_folder_cgconf_from_attributes(effective_folder_attributes)
        parent_perm_groups, parent_host_groups = collect_folder_groups(parent)

        if parconf["recurse_perms"]: # Parent gives us its permissions
            perm_groups.update(parent_perm_groups)

        if parconf["recurse_use"]:   # Parent give us its contact groups
            host_groups.update(parent_host_groups)

        parent = parent.get(".parent")

    return perm_groups, host_groups


def collect_host_groups(host, folder):
    return collect_folder_groups(folder, host)


def show_subfolders(folder):
    if len(folder[".folders"]) == 0:
        return False

    html.write('<div class=folders>')

    for entry in sort_by_title(folder[".folders"].values()):
        enter_url  = make_link_to([("mode", "folder")], entry)
        edit_url   = make_link_to([("mode", "editfolder"), ("backfolder", g_folder[".path"])], entry)
        delete_url = make_action_link([("mode", "folder"), ("_delete_folder", entry[".name"])])

        # Am I authorized at least for read access?
        auth_message = check_folder_permissions(entry, "read", False)
        auth_read = auth_message == True
        auth_write = check_folder_permissions(entry, "write", False) == True

        html.write('<div class="floatfolder%s" id="folder_%s"' % (
            auth_read and " unlocked" or " locked", entry['.name']))
        html.write(' onclick="wato_open_folder(event, \'%s\');"' % enter_url)
        html.write('>')

        # Only make folder openable when permitted to edit
        if not auth_read:
            html.write('<img class="icon autherr" src="images/icon_autherr.png" title="%s">' % \
                       (html.strip_tags(auth_message)))

        if True: # auth_read:
            if not auth_read:
                html.write('<div class=hoverarea>')

            else:
                html.write(
                    '<div class=hoverarea onmouseover="wato_toggle_folder(event, this, true);" '
                    'onmouseout="wato_toggle_folder(event, this, false)">'
                )

                html.icon_button(
                    edit_url,
                    _("Edit the properties of this folder"),
                    "edit",
                    id = 'edit_' + entry['.name'],
                    cssclass = 'edit',
                    style = 'display:none',
                )

            if not folder.get(".lock_subfolders") and not entry.get(".lock"):
                if config.may("wato.manage_folders") and auth_write:
                    html.icon_button(
                        '', # url is replaced by onclick code
                        _("Move this folder to another place"),
                        "move",
                        id = 'move_' + entry['.name'],
                        cssclass = 'move',
                        style = 'display:none',
                        onclick = 'wato_toggle_move_folder(event, this);'
                    )
                    html.write('<div id="move_dialog_%s" class="popup move_dialog" style="display:none">' % entry['.name'])
                    html.write('<span>%s</span>' % _('Move this folder to:'))
                    move_to_folder_combo("folder", entry, False, multiple = True)
                    html.write('</div>')

                if auth_write and config.may("wato.manage_folders"):
                    html.icon_button(
                        delete_url,
                        _("Delete this folder"),
                        "delete",
                        id = 'delete_' + entry['.name'],
                        cssclass = 'delete',
                        style = 'display:none',
                    )
            html.write('</div>')

        html.write('<div class=infos>')
        groups = userdb.load_group_information().get("contact", {})
        perm_groups, contact_groups = collect_folder_groups(entry)
        for num, pg in enumerate(perm_groups):
            cgalias = groups.get(pg, {'alias': pg})['alias']
            html.icon(_("Contactgroups that have permission on this folder"), "contactgroups")
            html.write(' %s<br>' % cgalias)
            if num > 1 and len(perm_groups) > 4:
                html.write(_('<i>%d more contact groups</i><br>') % (len(perm_groups) - num - 1))
                break


        num_hosts = num_hosts_in(entry, recurse=True)
        if num_hosts == 1:
            html.write(_("1 Host"))
        elif num_hosts > 0:
            html.write("%d %s" % (num_hosts, _("Hosts")))
        else:
            html.write("<i>%s</i>" % _("(no hosts)"))
        html.write('</div>')

        title = entry['title']
        # Internal foldername
        if not config.wato_hide_filenames:
            title += ' (%s)' % entry['.name']

        html.write('<div class=title title="%s">' % title)
        if auth_read:
            html.write('<a href="%s">' % enter_url)
        html.write(entry['title'])
        if auth_read:
            html.write("</a>")
        html.write('</div>')
        html.write('</div>')

    html.write("</div><div class=folder_foot></div>")
    return True

def show_hosts(folder):
    load_hosts(folder)
    if len(folder[".hosts"]) == 0:
        return False

    show_checkboxes = html.var('show_checkboxes', '0') == '1'

    html.write("<h3>" + _("Hosts") + "</h3>")
    hostnames = folder[".hosts"].keys()
    hostnames.sort(cmp = lambda a, b: cmp(num_split(a), num_split(b)))
    search_text = html.var("search")

    # Helper function for showing bulk actions. This is needed at the bottom
    # of the table of hosts and - if there are more than just a few - also
    # at the top of the table.
    search_shown = False
    def bulk_actions(at_least_one_imported, top, withsearch, colspan, show_checkboxes):
        table.row(collect_headers=False, fixed=True)
        table.cell(css="bulksearch", colspan=3)
        if not show_checkboxes:
            html.write('<div id="%s_on" title="%s" class="togglebutton %s up" '
                       'onclick="location.href=\'%s\'"></div>' % (
                        'checkbox', _('Show Checkboxes and bulk actions'), 'checkbox',
                        html.makeuri([('show_checkboxes', '1'), ('selection', weblib.selection_id())])))

        else:
            html.write('<div id="%s_on" title="%s" class="togglebutton %s down" '
                       'onclick="location.href=\'%s\'"></div>' % (
                        'checkbox', _('Hide Checkboxes and bulk actions'), 'checkbox',
                        html.makeuri([('show_checkboxes', '0')])))
        if withsearch:
            html.text_input(top and "search" or "search")
            html.button("_search", _("Search"))
            html.set_focus("search")
        table.cell(css="bulkactions", colspan=colspan-3)
        html.write(' ' + _("Selected hosts:\n"))

        if not g_folder.get(".lock_hosts"):
            if config.may("wato.manage_hosts"):
                html.button("_bulk_delete", _("Delete"))
            if config.may("wato.edit_hosts"):
                html.button("_bulk_edit", _("Edit"))
                html.button("_bulk_cleanup", _("Cleanup"))
        if config.may("wato.services"):
            html.button("_bulk_inventory", _("Discovery"))
        if not g_folder.get(".lock_hosts"):
            if config.may("wato.parentscan"):
                html.button("_parentscan", _("Parentscan"))
            if config.may("wato.edit_hosts") and config.may("wato.move_hosts"):
                move_to_folder_combo("host", None, top)
                if at_least_one_imported:
                    html.button("_bulk_movetotarget", _("Move to Target Folders"))

    # Show table of hosts in this folder
    html.begin_form("hosts", method = "POST")
    table.begin("hosts", searchable=False)

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

    # Compute colspan for bulk actions
    colspan = 6
    for attr, topic in host_attributes:
        if attr.show_in_table():
            colspan += 1
    if not g_folder.get(".lock_hosts") and config.may("wato.edit_hosts") and config.may("wato.move_hosts"):
        colspan += 1
    if show_checkboxes:
        colspan += 1

    # Add the bulk action buttons also to the top of the table when this
    # list shows more than 10 rows
    if more_than_ten_items and \
        (config.may("wato.edit_hosts") or config.may("wato.manage_hosts")):
        bulk_actions(at_least_one_imported, True, True, colspan, show_checkboxes)
        search_shown = True

    contact_group_names = userdb.load_group_information().get("contact", {})
    def render_contact_group(c):
        display_name = contact_group_names.get(c, {'alias': c})['alias']
        return '<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' % (c, display_name)

    host_errors = validate_all_hosts(hostnames)
    rendered_hosts = []
    # Now loop again over all hosts and display them
    for hostname in hostnames:
        if search_text and (search_text.lower() not in hostname.lower()):
            continue

        rendered_hosts.append(hostname)
        host = g_folder[".hosts"][hostname]
        effective = effective_attributes(host, g_folder)

        table.row()

        # Column with actions (buttons)
        edit_url     = make_link([("mode", "edithost"), ("host", hostname)])
        params_url   = make_link([("mode", "object_parameters"), ("host", hostname)])
        services_url = make_link([("mode", "inventory"), ("host", hostname)])
        clone_url    = make_link([("mode", host.get(".nodes") and "newcluster" or "newhost"),
                                 ("clone", hostname)])
        delete_url   = make_action_link([("mode", "folder"), ("_delete_host", hostname)])

        if show_checkboxes:
            table.cell("<input type=button class=checkgroup name=_toggle_group"
                       " onclick=\"toggle_all_rows();\" value=\"%s\" />" % _('X'), sortable=False)
            # Use CSS class "failed" in order to provide information about
            # selective toggling inventory-failed hosts for Javascript
            if host.get("inventory_failed"):
                css_class = "class=failed"
            else:
                css_class = ""
            html.write("<input type=checkbox %s name=\"_c_%s\" value=%d />" % (css_class, hostname, colspan))

        table.cell(_("Actions"), css="buttons", sortable=False)
        html.icon_button(edit_url, _("Edit the properties of this host"), "edit")
        html.icon_button(params_url, _("View the rule based parameters of this host"), "rulesets")
        if check_host_permissions(hostname, False) == True:
            msg = _("Edit the services of this host, do a service discovery")
            image =  "services"
            if host.get("inventory_failed"):
                image = "inventory_failed"
                msg += ". " + _("The service discovery of this host failed during a previous bulk service discovery.")
            html.icon_button(services_url, msg, image)
        if not g_folder.get(".lock_hosts") and config.may("wato.manage_hosts"):
            if config.may("wato.clone_hosts"):
                html.icon_button(clone_url, _("Create a clone of this host"), "insert")
            html.icon_button(delete_url, _("Delete this host"), "delete")

        # Hostname with link to details page (edit host)
        table.cell(_("Hostname"))
        errors = host_errors.get(hostname,[]) + validate_host(host, g_folder)
        if errors:
            msg = _("Warning: This host has an invalid configuration: ")
            msg += ", ".join(errors)
            html.icon(msg, "validation_error")
            html.write("&nbsp;")

        html.write('<a href="%s">%s</a>\n' % (edit_url, hostname))

        if ".nodes" in host:
            html.write("&nbsp;")
            html.icon(_("This host is a cluster of %s") % ", ".join(host[".nodes"]), "cluster")

        # Show attributes
        for attr, topic in host_attributes:
            if attr.show_in_table():
                attrname = attr.name()
                if attrname in host:
                    tdclass, tdcontent = attr.paint(host.get(attrname), hostname)
                else:
                    tdclass, tdcontent = attr.paint(effective.get(attrname), hostname)
                    tdclass += " inherited"
                table.cell(attr.title(), tdcontent, css=tdclass)

        # Am I authorized?
        auth = check_host_permissions(hostname, False)
        if auth == True:
            icon = "authok"
            title = _("You have permission to this host.")
        else:
            icon = "autherr"
            title = html.strip_tags(auth)

        table.cell(_('Auth'), '<img class=icon src="images/icon_%s.png" title="%s">' % (icon, title), sortable=False)

        # Permissions and Contact groups - through complete recursion and inhertance
        perm_groups, contact_groups = collect_host_groups(host, folder)
        table.cell(_("Permissions"), ", ".join(map(render_contact_group, perm_groups)))
        table.cell(_("Contact Groups"), ", ".join(map(render_contact_group, contact_groups)))

        if not config.wato_hide_hosttags:
            # Raw tags
            #
            # Optimize wraps:
            # 1. add <nobr> round the single tags to prevent wrap within tags
            # 2. add "zero width space" (&#8203;)
            tag_title = "|".join([ '%s' % t for t in host[".tags"] ])
            table.cell(_("Tags"), help=tag_title, css="tag-ellipsis")
            html.write("<b style='color: #888;'>|</b>&#8203;".join([ '<nobr>%s</nobr>' % t for t in host[".tags"] ]))

        # Move to
        if not g_folder.get(".lock_hosts") and config.may("wato.edit_hosts") and config.may("wato.move_hosts"):
            table.cell(_("Move To"), css="right", sortable=False)
            move_to_folder_combo("host", hostname)

    if config.may("wato.edit_hosts") or config.may("wato.manage_hosts"):
        bulk_actions(at_least_one_imported, False, not search_shown, colspan, show_checkboxes)

    table.end()
    html.hidden_fields()
    html.end_form()

    selected = weblib.get_rowselection('wato-folder-/'+g_folder['.path'])

    row_count = len(rendered_hosts)
    headinfo = "%d %s" % (row_count, row_count == 1 and _("host") or _("hosts"))
    html.javascript("update_headinfo('%s');" % headinfo)

    if show_checkboxes:
        html.javascript(
            'g_page_id = "wato-folder-%s";\n'
            'g_selection = "%s";\n'
            'g_selected_rows = %r;\n'
            'init_rowselect();' % ('/' + g_folder['.path'], weblib.selection_id(), selected)
        )
    return True

move_to_folder_combo_cache_id = None
# In case of what == "host", thing is either None or the name of the host
# In case of what == "folder", thing is the folder dict
def move_to_folder_combo(what, thing = None, top = False, multiple = False):
    global move_to_folder_combo_cache, move_to_folder_combo_cache_id
    if move_to_folder_combo_cache_id != id(html):
        move_to_folder_combo_cache = {}
        move_to_folder_combo_cache_id = id(html)

    select_attrs = {}
    if multiple:
        select_attrs = {'multiple': '10'}

    # In case of a folder move combo, thing is the folder object
    # we want to move
    if what == "folder" or id(g_folder) not in move_to_folder_combo_cache:
        selections = [("@", _("(select folder)"))]
        for path, afolder in g_folders.items():
            # TODO: Check permisssions
            if afolder != g_folder and \
                 (what != "folder" or not (
                    # no move to itselfs or child folders of "thing"
                    folder_is_parent_of(thing, afolder)
                    # avoid naming conflict!
                    or thing[".name"] in afolder[".folders"])):
                os_path = afolder[".path"]
                title_path = folder_title_path(os_path)
                if len(title_path) > 1:
                    del title_path[0] # remove name of main folder
                msg = " / ".join(title_path)
                # msg = afolder["title"]
                if os_path and not config.wato_hide_filenames:
                    msg += " (%s)" % os_path
                selections.append((os_path, msg))
        selections.sort(cmp=lambda a,b: cmp(a[1].lower(), b[1].lower()))
        move_to_folder_combo_cache[g_folder['.path']] = selections
    else:
        selections = move_to_folder_combo_cache[g_folder['.path']]

    if len(selections) > 1:
        if thing == None:
            html.button("_bulk_move", _("Move:"))
            field_name = 'bulk_moveto'
            if top:
                field_name = '_top_bulk_moveto'
                if html.has_var('bulk_moveto'):
                    html.javascript('update_bulk_moveto("%s")' % html.var('bulk_moveto', ''))
            html.select(field_name, selections, "@",
                        onchange = "update_bulk_moveto(this.value)",
                        attrs = {'class': 'bulk_moveto'})
        elif what == "host":
            html.hidden_field("host", thing)
            uri = html.makeactionuri([("host", thing)])
            html.select("_host_move_%s" % thing, selections, "@",
                "location.href='%s' + '&_move_host_to=' + this.value;" % uri, attrs = select_attrs);
        else: # what == "folder"
            # html.hidden_field("what_folder", thing)
            uri = html.makeactionuri([("what_folder", thing[".path"])])
            html.select("_folder_move_%s" % thing[".path"], selections, "@",
                "location.href='%s' + '&_move_folder_to=' + this.value;" % uri, attrs = select_attrs);




def move_hosts_to(hostnames, path):
    if path not in g_folders: # non-existing folder
        return

    target_folder = g_folders[path]
    check_folder_permissions(g_folder, "write")
    check_folder_permissions(target_folder, "write")

    if target_folder == g_folder:
        return 0 # target and source are the same

    # read hosts currently in target file
    load_hosts(target_folder)
    target_hosts = target_folder[".hosts"]

    if g_folder.get(".lock_hosts"):
        raise MKUserError(None, _("Cannot move selected hosts: Hosts in this folder are locked."))
    if target_folder.get(".lock_hosts"):
        raise MKUserError(None, _("Cannot move selected hosts: Hosts in target folder are locked."))

    num_moved = 0
    for hostname in hostnames:
        if hostname not in g_folder[".hosts"]: # non-existant host
            continue

        mark_affected_sites_dirty(g_folder, hostname)

        # Add to new folder
        target_hosts[hostname] = g_folder[".hosts"][hostname]
        target_hosts[hostname]['.folder'] = target_folder
        target_folder["num_hosts"] += 1

        # Remove from old folder
        g_folder["num_hosts"] -= 1
        del g_folder[".hosts"][hostname]

        mark_affected_sites_dirty(target_folder, hostname)

        if len(hostnames) == 1:
            log_pending(AFFECTED, hostname, "move-host", _("Moved host from %s to %s") %
                (g_folder[".path"], target_folder[".path"]))
        num_moved += 1

    save_folder_and_hosts(target_folder)
    save_folder_and_hosts(g_folder)
    call_hook_hosts_changed(g_root_folder)
    if len(hostnames) > 1:
        log_pending(AFFECTED, target_folder, "move-host", _("Moved %d hosts from %s to %s") %
            (num_moved, g_folder[".path"], target_folder[".path"]))
    return num_moved


def move_host_to(hostname, target_filename):
    return move_hosts_to([hostname], target_filename)

def delete_hosts_after_confirm(hosts):
    c = wato_confirm(_("Confirm deletion of %d hosts") % len(hosts),
                     _("Do you really want to delete the %d selected hosts?") % len(hosts))
    if c:
        if g_folder.get(".lock_hosts"):
            raise MKUserError(None, _("Cannot delete hosts. Hosts in this folder are locked"))

        for delname in hosts:
            mark_affected_sites_dirty(g_folder, delname)
            host = g_folder[".hosts"][delname]
            # check_mk_automation(host[".siteid"], "delete-host", [delname])
            del g_folder[".hosts"][delname]
            g_folder["num_hosts"] -= 1
            log_pending(AFFECTED, delname, "delete-host", _("Deleted host %s") % delname)

        save_folder_and_hosts(g_folder)
        call_hook_hosts_changed(g_folder)
        return "folder", _("Successfully deleted %d hosts") % len(hosts)
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload

def move_folder(what_folder, target_folder):
    if what_folder.get(".lock_subfolders"):
        raise MKUserError(None, _("Cannot move folder: This folder is locked."))
    elif target_folder.get(".lock_subfolders"):
        raise MKUserError(None, _("Cannot move folder: Target folder is locked."))

    old_parent = what_folder[".parent"]
    old_dir = folder_dir(what_folder)
    del old_parent[".folders"][what_folder[".name"]]
    target_folder[".folders"][what_folder[".name"]] = what_folder
    what_folder[".parent"] = target_folder
    new_dir = folder_dir(target_folder)
    shutil.move(old_dir, new_dir)

def delete_folder_after_confirm(del_folder):
    msg = _("Do you really want to delete the folder %s?") % del_folder["title"]
    if not config.wato_hide_filenames:
        msg += _(" Its directory is <tt>%s</tt>.") % folder_dir(del_folder)
    num_hosts = num_hosts_in(del_folder)
    if num_hosts:
        msg += _(" The folder contains <b>%d</b> hosts, which will also be deleted!") % num_hosts
    c = wato_confirm(_("Confirm folder deletion"), msg)

    if c:
        mark_affected_sites_dirty(g_folder)
        del g_folder[".folders"][del_folder[".name"]]
        folder_path = folder_dir(del_folder)
        shutil.rmtree(folder_path)
        log_pending(AFFECTED, del_folder, "delete-folder",
                _("Deleted empty folder %s")% folder_dir(del_folder))
        call_hook_folder_deleted(del_folder)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload

# Create list of all hosts that are select with checkboxes in the current file.
# This is needed for bulk operations.
def get_hostnames_from_checkboxes(filterfunc = None):
    show_checkboxes = html.var("show_checkboxes") == "1"

    entries = g_folder[".hosts"].items()
    entries.sort()

    if show_checkboxes:
        selected = weblib.get_rowselection('wato-folder-/'+g_folder['.path'])

    selected_hosts = []
    search_text = html.var("search")
    for hostname, host in entries:
        if (not search_text or (search_text.lower() in hostname.lower())) \
            and (not show_checkboxes or ('_c_' + hostname) in selected):
                if filterfunc == None or \
                   filterfunc(host):
                    selected_hosts.append(hostname)
    return selected_hosts

#.
#   .--Edit Folder---------------------------------------------------------.
#   |           _____    _ _ _     _____     _     _                       |
#   |          | ____|__| (_) |_  |  ___|__ | | __| | ___ _ __             |
#   |          |  _| / _` | | __| | |_ / _ \| |/ _` |/ _ \ '__|            |
#   |          | |__| (_| | | |_  |  _| (_) | | (_| |  __/ |               |
#   |          |_____\__,_|_|\__| |_|  \___/|_|\__,_|\___|_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for editing the properties of a folder. This includes the       |
#   | creation of new folders.                                             |
#   '----------------------------------------------------------------------'

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
            if g_folder.get(".lock_subfolders"):
                raise MKUserError("title", _("Folder is locked. You cannot create or remove a folders "
                                             "in this folder."))
            config.need_permission("wato.manage_folders")
        else:
            if g_folder.get(".lock"):
                raise MKUserError("title", _("Folder attributes locked. You cannot change the attributes of this folder."))
            config.need_permission("wato.edit_folders")

        if not html.check_transaction():
            return "folder"

        # Title
        title = html.var_utf8("title")
        if not title:
            raise MKUserError("title", _("Please supply a title."))
        title_changed = not new and title != g_folder.get('title', '')

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
            create_wato_folder(g_folder, name, title, attributes)

        else:
            # TODO: migrate this block into own function edit_wato_folder(..)
            cgs_changed = get_folder_cgconf_from_attributes(attributes) != \
                          get_folder_cgconf_from_attributes(g_folder["attributes"])
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
            log_pending(AFFECTED, g_folder, "edit-folder", _("Edited properties of folder %s") % title)

            g_folder["title"]      = title

            if attributes_changed or title_changed:
                mark_affected_sites_dirty(g_folder)
                g_folder["attributes"] = attributes

                # Due to changes in folder/file attributes, host files
                # might need to be rewritten in order to reflect Changes
                # in Nagios-relevant attributes.
                rewrite_config_files_below(g_folder) # due to inherited attributes
                save_folder(g_folder)
                # This updates g_folder and g_folders[...]
                g_folder = reload_folder(g_folder)

                mark_affected_sites_dirty(g_folder)

                log_pending(AFFECTED, g_folder, "edit-folder",
                       _("Changed attributes of folder %s") % title)
                call_hook_hosts_changed(g_folder)

        need_sidebar_reload()

        if html.has_var("backfolder"):
            set_current_folder(g_folders[html.var("backfolder")])
        return "folder"


    else:
        render_folder_path()
        check_folder_permissions(g_folder, "read")

        lock_message = ""
        if g_folder.get(".lock"):
            if g_folder[".lock"] == True:
                lock_message = _("Folder attributes locked (You cannot edit the attributes of this folder)")
            else:
                lock_message = g_folder[".lock"]
        if len(lock_message) > 0:
            html.write("<div class=info>" + lock_message + "</div>")

        html.begin_form("edithost", method = "POST")

        # title
        forms.header(_("Title"))
        forms.section()
        html.text_input("title", title)
        html.set_focus("title")

        # folder name (omit this for root folder)
        if not (not new and g_folder == g_root_folder):
            if not config.wato_hide_filenames:
                forms.section(_("Internal directory name"))
                if new:
                    html.text_input("name")
                else:
                    html.write(name)
                html.help(_("This is the name of subdirectory where the files and "
                    "other folders will be created. You cannot change this later."))

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

            configure_attributes(new, {"folder": attributes}, "folder", parent, myself)

        forms.end()
        if new or not g_folder.get(".lock"):
            html.button("save", _("Save &amp; Finish"), "submit")
        html.hidden_fields()
        html.end_form()


def check_wato_foldername(htmlvarname, name, just_name = False):
    if not just_name and name in g_folder:
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

def ajax_set_foldertree():
    config.save_user_file("foldertree", (html.var('topic'), html.var('target')))


#.
#   .--Edit-Host-----------------------------------------------------------.
#   |               _____    _ _ _     _   _           _                   |
#   |              | ____|__| (_) |_  | | | | ___  ___| |_                 |
#   |              |  _| / _` | | __| | |_| |/ _ \/ __| __|                |
#   |              | |__| (_| | | |_  |  _  | (_) \__ \ |_                 |
#   |              |_____\__,_|_|\__| |_| |_|\___/|___/\__|                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for host details (new, clone, edit)                             |
#   '----------------------------------------------------------------------'

def mode_edithost(phase, new, cluster):
    hostname = html.var("host") # may be empty in new/clone mode

    clonename = html.var("clone")
    if clonename and clonename not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page with an invalid host name."))

    if clonename and not config.may("wato.clone_hosts"):
        raise MKAuthException(_("Sorry, you are not allowed to clone hosts."))

    if clonename:
        title = _("Create clone of %s") % clonename
        host = g_folder[".hosts"][clonename]
        cluster = ".nodes" in host
        mode = "clone"
    elif not new and hostname in g_folder[".hosts"]:
        title = _("Properties of host") + " " + hostname
        host = g_folder[".hosts"][hostname]
        cluster = ".nodes" in host
        mode = "edit"
    else:
        if cluster:
            title = _("Create new cluster")
            host = { ".nodes" : [] }
        else:
            title = _("Create new host")
            host = {}
        mode = "new"
        new = True

    if phase == "title":
        return title

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        if not new:
            host_status_button(hostname, "hoststatus")

            html.context_button(_("Services"),
                  make_link([("mode", "inventory"), ("host", hostname)]), "services")
            html.context_button(_("Parameters"),
                  make_link([("mode", "object_parameters"), ("host", hostname)]), "rulesets")
            if not g_folder.get(".lock_hosts"):
                html.context_button(_("Rename %s") % (cluster and _("Cluster") or _("Host")),
                  make_link([("mode", "rename_host"), ("host", hostname)]), "rename_host")
            if not cluster:
                html.context_button(_("Diagnostic"),
                      make_link([("mode", "diag_host"), ("host", hostname)]), "diagnose")
            html.context_button(_("Update DNS Cache"),
                      html.makeactionuri([("_update_dns_cache", "1")]), "update")

    elif phase == "action":
        if html.var("_update_dns_cache"):
            if html.check_transaction():
                config.need_permission("wato.update_dns_cache")
                num_updated, failed_hosts = check_mk_automation(host[".siteid"], "update-dns-cache", [])
                infotext = _("Successfully updated IP addresses of %d hosts.") % num_updated
                if failed_hosts:
                    infotext += "<br><br><b>Hostnames failed to lookup:</b> " + ", ".join(["<tt>%s</tt>" % h for h in failed_hosts])
                return None, infotext
            else:
                return None


        if not new and html.var("delete"): # Delete this host
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(g_folder, "write")
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_host_after_confirm(hostname)

        host = collect_attributes()
        if cluster:
            nodes = ListOfStrings().from_html_vars("nodes")
            if len(nodes) < 1:
                raise MKUserError("nodes_0", _("The cluster must have at least one node"))
            for nr, node in enumerate(nodes):
                if not find_host(node):
                    raise MKUserError("nodes_%d" % nr, _("The node <b>%s</b> is not a WATO host.") % node)
            host[".nodes"] = nodes

        # handle clone & new
        if new:
            if not html.transaction_valid():
                return "folder"
            check_new_host_permissions(g_folder, host, hostname)
        else:
            check_edit_host_permissions(g_folder, host, hostname)

        if hostname:
            go_to_services = html.var("services")
            go_to_diag     = html.var("diag_host")
            if html.check_transaction():
                if new:
                    add_hosts_to_folder(g_folder, {hostname: host})
                else:
                    update_hosts_in_folder(g_folder, {hostname: {"set": host}})

            errors = validate_all_hosts([hostname]).get(hostname, []) + validate_host(g_folder[".hosts"][hostname], g_folder)
            if errors: # keep on this page if host does not validate
                return
            elif new:
                if host.get('tag_agent') != 'ping':
                    create_msg = _('Successfully created the host. Now you should do a '
                                   '<a href="%s">service discovery</a> in order to auto-configure '
                                   'all services to be checked on this host.') % \
                                    make_link([("mode", "inventory"), ("host", hostname)])
                else:
                    create_msg = None

                if go_to_services:
                    return "firstinventory"
                elif go_to_diag:
                    html.set_var("_try", "1")
                    return "diag_host", create_msg
                else:
                    return "folder", create_msg
            else:
                if go_to_services:
                    return "inventory"
                elif go_to_diag:
                    html.set_var("_try", "1")
                    return "diag_host"
                else:
                    return "folder"

    else:
        # Show outcome of host validation. Do not validate new hosts
        errors = None
        if new:
            render_folder_path()
        else:
            errors = validate_all_hosts([hostname]).get(hostname, []) + validate_host(host, g_folder)

        if errors:
            html.write("<div class=info>")
            html.write('<table class=validationerror border=0 cellspacing=0 cellpadding=0><tr><td class=img>')
            html.write('<img src="images/icon_validation_error.png"></td><td>')
            html.write('<p><h3>%s</h3><ul>%s</ul></p>' %
                (_("Warning: This host has an invalid configuration!"),
                 "".join(["<li>%s</li>" % error for error in errors])))

            if html.form_submitted():
                html.write("<br><b>%s</b>" % _("Your changes have been saved nevertheless."))

            html.write("</td></tr></table></div>")

        lock_message = ""
        if g_folder.get(".lock_hosts"):
            if g_folder[".lock_hosts"] == True:
                lock_message = _("Host attributes locked (You cannot edit this host)")
            else:
                lock_message = g_folder[".lock_hosts"]
        if len(lock_message) > 0:
            html.write("<div class=info>" + lock_message + "</div>")

        html.begin_form("edithost", method="POST")

        # host name
        forms.header(_("General Properties"))
        if hostname and mode == "edit":
            forms.section(_("Hostname"), simple=True)
            html.write(hostname)
        else:
            forms.section(_("Hostname"))
            html.text_input("host")
            html.set_focus("host")

        # Cluster: nodes
        if cluster:
            vs = ListOfStrings(valuespec = TextAscii(size = 19), orientation="horizontal")
            forms.section(_("Nodes"))
            vs.render_input("nodes", host[".nodes"])
            html.help(_('Enter the host names of the cluster nodes. These '
                       'hosts must be present in WATO. '))

        configure_attributes(new, {hostname: host}, "host", parent = g_folder)

        forms.end()
        if not g_folder.get(".lock_hosts"):
            html.image_button("services", _("Save &amp; go to Services"), "submit")
            html.image_button("save", _("Save &amp; Finish"), "submit")
            if not cluster:
                html.image_button("diag_host", _("Save &amp; Test"), "submit")
            if not new:
                html.image_button("delete", _("Delete host!"), "submit")
        html.hidden_fields()
        html.end_form()


def delete_host_after_confirm(delname):
    c = wato_confirm(_("Confirm host deletion"),
                     _("Do you really want to delete the host <tt>%s</tt>?") % delname)
    if c:
        if g_folder.get(".lock_hosts"):
            raise MKUserError(None, _("Cannot delete host. Hosts in this folder are locked"))

        mark_affected_sites_dirty(g_folder, delname)
        log_pending(AFFECTED, delname, "delete-host", _("Deleted host %s") % delname)
        host = g_folder[".hosts"][delname]
        del g_folder[".hosts"][delname]
        g_folder["num_hosts"] -= 1
        save_folder_and_hosts(g_folder)
        check_mk_automation(host[".siteid"], "delete-host", [delname])
        call_hook_hosts_changed(g_folder)
        return "folder"
    elif c == False: # not yet confirmed
        return ""
    else:
        return None # browser reload

def check_new_hostname(varname, hostname):
    if not hostname:
        raise MKUserError(varname, _("Please specify a host name."))
    elif hostname in g_folder[".hosts"]:
        raise MKUserError(varname, _("A host with this name already exists."))
    elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
        raise MKUserError(varname, _("Invalid host name: must contain only characters, digits, dash, underscore and dot."))

def check_new_host_permissions(folder, host, hostname):
    config.need_permission("wato.manage_hosts")
    check_folder_permissions(folder, "write")
    check_user_contactgroups(host.get("contactgroups", (False, [])))
    check_new_hostname("host", hostname)

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

#.
#   .--Rename Host---------------------------------------------------------.
#   |     ____                                   _   _           _         |
#   |    |  _ \ ___ _ __   __ _ _ __ ___   ___  | | | | ___  ___| |_       |
#   |    | |_) / _ \ '_ \ / _` | '_ ` _ \ / _ \ | |_| |/ _ \/ __| __|      |
#   |    |  _ <  __/ | | | (_| | | | | | |  __/ |  _  | (_) \__ \ |_       |
#   |    |_| \_\___|_| |_|\__,_|_| |_| |_|\___| |_| |_|\___/|___/\__|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for renaming an existing host.                                  |
#   '----------------------------------------------------------------------'

def mode_rename_host(phase):
    hostname = html.var("host")

    if hostname not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page with an invalid host name."))

    host = g_folder[".hosts"][hostname]
    is_cluster = ".nodes" in host

    if phase == "title":
        return _("Rename %s %s") % (is_cluster and _("Cluster") or _("Host"), hostname)

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Host Properties"), make_link([("mode", "edithost"), ("host", hostname)]), "back")
        return

    elif phase == "action":
        if g_folder.get(".lock_hosts"):
            raise MKGeneralException(_("This folder is locked. You cannot rename a host here."))

        if parse_audit_log("pending"):
            raise MKGeneralException(_("You cannot rename a host while you have pending changes."))

        newname = html.var("newname")
        check_new_hostname("newname", newname)
        c = wato_confirm(_("Confirm renaming of host"),
                         _("Are you sure you want to rename the host <b>%s</b> into <b>%s</b>? "
                           "This involves a restart of the monitoring core!") %
                         (hostname, newname))
        if c:
            # Creating pending entry. That makes the site dirty and that will force a sync of
            # the config to that site before the automation is being done.
            log_pending(AFFECTED, newname, "rename-host", _("Renamed host %s into %s") % (hostname, newname))
            actions = rename_host(host, newname) # Already activates the changes!
            log_commit_pending() # All activated by the underlying rename automation
            html.set_var("host", newname)
            action_txt =  "".join([ "<li>%s</li>" % a for a in actions ])
            return "edithost", HTML(_("Renamed host <b>%s</b> into <b>%s</b> at the following places:<br><ul>%s</ul>") % (
                                 hostname, newname, action_txt))
        elif c == False: # not yet confirmed
            return ""
        return

    html.help(_("The renaming of hosts is a complex operation since a host's name is being "
               "used as a unique key in various places. It also involves stopping and starting "
               "of the monitoring core. You cannot rename a host while you have pending changes."))

    html.begin_form("rename_host", method="POST")
    forms.header(_("Rename to host %s") % hostname)
    forms.section(_("Current name"))
    html.write(hostname)
    forms.section(_("New name"))
    html.text_input("newname", "")
    forms.end()
    html.set_focus("newname")
    html.image_button("rename", _("Rename host!"), "submit")
    html.hidden_fields()
    html.end_form()

def rename_host_in_list(thelist, oldname, newname):
    did_rename = False
    for nr, element in enumerate(thelist):
        if element == oldname:
            thelist[nr] = newname
            did_rename = True
        elif element == '!'+oldname:
            thelist[nr] = '!'+newname
            did_rename = True
    return did_rename

def rename_host(host, newname):

    actions = []

    # 1. Fix WATO configuration itself ----------------

    # Hostname itself in the current folder
    oldname = host[".name"]
    g_folder[".hosts"][newname] = host
    host[".name"] = newname
    del g_folder[".hosts"][oldname]
    save_folder_and_hosts(g_folder)
    mark_affected_sites_dirty(g_folder)
    actions.append(_("The WATO folder"))

    # Is this host node of a cluster?
    all_hosts = load_all_hosts()
    clusters = []
    parents = []
    for somehost in all_hosts.values():
        if ".nodes" in somehost:
            nodes = somehost[".nodes"]
            if rename_host_in_list(somehost[".nodes"], oldname, newname):
                clusters.append(somehost[".name"])
                folder = somehost['.folder']
                save_folder_and_hosts(folder)
                mark_affected_sites_dirty(folder)

        if somehost.get("parents"):
            if rename_host_in_list(somehost["parents"], oldname, newname):
                parents.append(somehost[".name"])
                folder = somehost['.folder']
                save_folder_and_hosts(folder)
                mark_affected_sites_dirty(folder)

    if clusters:
        actions.append(_("The following cluster definitions: %s") % (", ".join(clusters)))

    if parents:
        actions.append(_("The parents of the following hosts: %s") % (", ".join(parents)))

    # Rules that explicitely name that host (no regexes)
    changed_rulesets = []
    def rename_host_in_folder_rules(folder):
        rulesets = load_rulesets(folder)
        changed = False
        for varname, rules in rulesets.items():
            rulespec = g_rulespecs[varname]
            for nr, rule in enumerate(rules):
                value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
                if rename_host_in_list(host_list, oldname, newname):
                    newrule = construct_rule(rulespec, value, tag_specs, host_list, item_list, rule_options)
                    rules[nr] = newrule
                    changed_rulesets.append(varname)
                    changed = True
        if changed:
            save_rulesets(folder, rulesets)
            mark_affected_sites_dirty(folder)

        for subfolder in folder['.folders'].values():
            rename_host_in_folder_rules(subfolder)

    rename_host_in_folder_rules(g_root_folder)
    if changed_rulesets:
        unique = set(changed_rulesets)
        for varname in unique:
            actions.append(_("%d WATO rules in ruleset <i>%s</i>") % (
              changed_rulesets.count(varname), g_rulespecs[varname]["title"]))

    # Business Intelligence rules
    num_bi = rename_host_in_bi(oldname, newname)
    if num_bi:
        actions.append(_("%d BI rules and aggregations") % num_bi)

    # Now make sure that the remote site that contains that host is being
    # synced.

    # 3. Check_MK stuff ------------------------------------------------
    # Things like autochecks, counters, etc. This has to be done via an
    # automation, since it might have to happen on a remote site. During
    # this automation the core will be stopped, after the renaming has
    # taken place a new configuration will be created and the core started
    # again.
    ip_lookup_failed = True
    for what in check_mk_automation(host[".siteid"], "rename-host", [oldname, newname]):
        if what == "cache":
            actions.append(_("Cached output of monitoring agents"))
        elif what == "counters":
            actions.append(_("Files with performance counters"))
        elif what == "piggyback-load":
            actions.append(_("Piggyback information from other host"))
        elif what == "piggyback-pig":
            actions.append(_("Piggyback information for other hosts"))
        elif what == "autochecks":
            actions.append(_("Auto-disovered services of the host"))
        elif what == "logwatch":
            actions.append(_("Logfile information of logwatch plugin"))
        elif what == "snmpwalk":
            actions.append(_("A stored SNMP walk"))
        elif what == "rrd":
            actions.append(_("RRD databases with performance data"))
        elif what == "rrdcached":
            actions.append(_("RRD updates in journal of RRD Cache"))
        elif what == "pnpspool":
            actions.append(_("Spool files of PNP4Nagios"))
        elif what == "nagvis":
            actions.append(_("NagVis maps"))
        elif what == "history":
            actions.append(_("Monitoring history entries (events and availability)"))
        elif what == "retention":
            actions.append(_("The current monitoring state (including acknowledgements and downtimes)"))
        elif what == "ipfail":
            actions.append("<div class=error>%s</div>" % (_("<b>WARNING:</b> the IP address lookup of "
                   "<tt>%s</tt> has failed. The core has been started by using the address <tt>0.0.0.0</tt> for the while. "
                   "You will not be able to activate any changes until you have either updated your "
                   "DNS or configured an explicit address for <tt>%s</tt>.") % (newname, newname)))

    # Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    def rename_in_notification_rules(rules):
        num_changed = 0
        for rule in rules:
            for key in [ "match_hosts", "match_exclude_hosts" ]:
                if rule.get(key):
                    if rename_host_in_list(rule[key], oldname, newname):
                        num_changed += 1
        return num_changed

    users = userdb.load_users(lock = True)
    some_user_changed = False
    for userid, user in users.items():
        if user.get("notification_rules"):
            rules = user["notification_rules"]
            num_changed = rename_in_notification_rules(rules)
            if num_changed:
                actions.append("%d notification rules of user %s" % (num_changed, userid))
                some_changed = True

    rules = load_notification_rules()
    num_changed = rename_in_notification_rules(rules)
    if num_changed:
        actions.append(_("%d global notification rules") % num_changed)
        save_notification_rules(rules)

    # Notification channels of flexible notifcations also can have host conditions
    for userid, user in users.items():
        method = user.get("notification_method")
        if method and type(method) == tuple and method[0] == "flexible":
            channels_changed = 0
            for channel in method[1]:
                if channel.get("only_hosts"):
                    num_changed = rename_host_in_list(channel["only_hosts"], oldname, newname)
                    if num_changed:
                        channels_changed += 1
                        some_user_changed = True
            if channels_changed:
                actions.append("%d flexible notification configurations of user %s" % (channels_changed, userid))

    if some_user_changed:
        userdb.save_users(users)

    # State of Multisite ---------------------------------------
    # Favorites of users and maybe other settings. We simply walk through
    # all directories rather then through the user database. That way we
    # are sure that also currently non-existant users are being found and
    # also only users that really have a profile.
    users_changed = 0
    total_changed = 0
    for userid in os.listdir(config.config_dir):
        if userid[0] != '.':
            favpath = config.config_dir + "/" + userid + "/favorites.mk"
            if os.path.exists(favpath):
                try:
                    num_changed = 0
                    favorites = eval(file(favpath).read())
                    for nr, entry in enumerate(favorites):
                        if entry == oldname:
                            favorites[nr] = newname
                            num_changed += 1
                        elif entry.startswith(oldname + ";"):
                            favorites[nr] = newname + ";" + entry.split(";")[1]
                            num_changed += 1
                    if num_changed:
                        file(favpath, "w").write(repr(favorites) + "\n")
                        users_changed += 1
                        total_changed += num_changed
                except:
                    if config.debug:
                        raise
    if users_changed:
        actions.append(_("%d favorite entries of %d users") % (total_changed, users_changed))

    call_hook_hosts_changed(g_root_folder)
    return actions



#.
#   .--Host & Services Parameters Overview pages---------------------------.
#   |        ____                                _                         |
#   |       |  _ \ __ _ _ __ __ _ _ __ ___   ___| |_ ___ _ __ ___          |
#   |       | |_) / _` | '__/ _` | '_ ` _ \ / _ \ __/ _ \ '__/ __|         |
#   |       |  __/ (_| | | | (_| | | | | | |  __/ ||  __/ |  \__ \         |
#   |       |_|   \__,_|_|  \__,_|_| |_| |_|\___|\__\___|_|  |___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for displaying and modifying the rule based host and service    |
#   | parameters. This is a host/service overview page over all things     |
#   | that can be modified via rules.                                      |
#   '----------------------------------------------------------------------'

def mode_object_parameters(phase):
    hostname = html.var("host") # may be empty in new/clone mode
    host = g_folder[".hosts"][hostname]
    is_cluster = ".nodes" in host
    service = html.var("service")

    if phase == "title":
        title = _("Parameters of") + " " + hostname
        if service:
            title += " / " + service
        return title

    elif phase == "buttons":
        if service:
            prefix = _("Host-")
        else:
            prefix = ""
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        if service:
            service_status_button(hostname, service)
        else:
            host_status_button(hostname, "hoststatus")
        html.context_button(prefix + _("Properties"), make_link([("mode", "edithost"), ("host", hostname)]), "edit")
        html.context_button(_("Services"), make_link([("mode", "inventory"), ("host", hostname)]), "services")
        if not is_cluster:
            html.context_button(prefix + _("Diagnostic"),
              make_link([("mode", "diag_host"), ("host", hostname)]), "diagnose")
        return

    elif phase == "action":
        return


    # Now we collect all rulesets that apply to hosts, except those specifying
    # new active or static checks
    all_rulesets = load_all_rulesets()
    groupnames = [ gn for gn, rulesets in g_rulespec_groups
                   if not gn.startswith("static/") and
                      not gn.startswith("checkparams/") and
                      gn != "activechecks" ]
    groupnames.sort()


    def render_rule_reason(title, title_url, reason, reason_url, is_default, setting):
        if title_url:
            title = '<a href="%s">%s</a>' % (title_url, title)
        forms.section(title)

        if reason:
            title = '<a href="%s">%s</a>' % (reason_url, reason)
        if is_default:
            reason = '<i>' + reason + '</i>'
        html.write("<table class=setting><tr><td class=reason>%s</td>" % reason)
        html.write('<td class="settingvalue %s">%s</td></tr></table>' % (is_default and "unused" or "used", setting))


    # For services we make a special handling the for origin and parameters
    # of that service!
    if service:
        serviceinfo = check_mk_automation(host[".siteid"], "analyse-service", [hostname, service])
        if serviceinfo:
            forms.header(_("Check Origin and Parameters"), isopen = True, narrow=True, css="rulesettings")
            origin = serviceinfo["origin"]
            origin_txt = {
                "active"  : _("Active check"),
                "static"  : _("Manual check"),
                "auto"    : _("Inventorized check"),
                "classic" : _("Classical check"),
            }[origin]
            render_rule_reason(_("Type of check"), None, "", "", False, origin_txt)

            # First case: discovered checks. They come from var/check_mk/autochecks/HOST.
            if origin ==  "auto":
                checkgroup = serviceinfo["checkgroup"]
                checktype = serviceinfo["checktype"]
                if not checkgroup:
                    render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

                # Logwatch needs a special handling, since it is not configured
                # via checkgroup_parameters but via "logwatch_rules" in a special
                # WATO module.
                elif checkgroup == "logwatch":
                    rulespec = g_rulespecs["logwatch_rules"]
                    output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                            serviceinfo["item"], serviceinfo["parameters"])

                else:
                    # Note: some discovered checks have a check group but
                    # *no* ruleset for discovered checks. One example is "ps".
                    # That can be configured as a manual check or created by
                    # inventory. But in the later case all parameters are set
                    # by the inventory. This will be changed in a later version,
                    # but we need to address it anyway.
                    grouprule = "checkgroup_parameters:" + checkgroup
                    if grouprule not in g_rulespecs:
                        rulespec = g_rulespecs.get("static_checks:" + checkgroup)
                        if rulespec:
                            url = make_link([('mode', 'edit_ruleset'), ('varname', "static_checks:" + checkgroup), ('host', hostname)])
                            render_rule_reason(_("Parameters"), url, _("Determined by discovery"), None, False,
                                       rulespec["valuespec"]._elements[2].value_to_text(serviceinfo["parameters"]))
                        else:
                            render_rule_reason(_("Parameters"), None, "", "", True, _("This check is not configurable via WATO"))

                    else:
                        rulespec = g_rulespecs[grouprule]
                        output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                                serviceinfo["item"], serviceinfo["parameters"])

            elif origin == "static":
                checkgroup = serviceinfo["checkgroup"]
                checktype = serviceinfo["checktype"]
                if not group:
                    htmlwrite(_("This check is not configurable via WATO"))
                else:
                    rulespec = g_rulespecs["static_checks:" + checkgroup]
                    itemspec = rulespec["itemspec"]
                    if itemspec:
                        item_text = itemspec.value_to_text(serviceinfo["item"])
                        title = rulespec["itemspec"].title()
                    else:
                        item_text = serviceinfo["item"]
                        title = _("Item")
                    render_rule_reason(title, None, "", "", False, item_text)
                    output_analysed_ruleset(all_rulesets, rulespec, hostname,
                                            serviceinfo["item"], PARAMETERS_OMIT)
                    html.write(rulespec["valuespec"]._elements[2].value_to_text(serviceinfo["parameters"]))
                    html.write("</td></tr></table>")


            elif origin == "active":
                checktype = serviceinfo["checktype"]
                rulespec = g_rulespecs["active_checks:" + checktype]
                output_analysed_ruleset(all_rulesets, rulespec, hostname, None, serviceinfo["parameters"])

            elif origin == "classic":
                rule = all_rulesets["custom_checks"][serviceinfo["rule_nr"]]
                # Find relative rule number in folder
                old_folder = None
                rel_nr = -1
                for r in all_rulesets["custom_checks"]:
                    if old_folder != r[0]:
                        rel_nr = -1
                    rel_nr += 1
                    if r is rule:
                        break
                url = make_link([('mode', 'edit_ruleset'), ('varname', "custom_checks"), ('host', hostname)])
                forms.section('<a href="%s">%s</a>' % (url, _("Command Line")))
                url = make_link([
                    ('mode', 'edit_rule'),
                    ('varname', "custom_checks"),
                    ('rule_folder', rule[0][".path"]),
                    ('rulenr', rel_nr),
                    ('host', hostname)])

                html.write('<table class=setting><tr><td class=reason><a href="%s">%s %d %s %s</a></td>' % (
                    url, _("Rule"), rel_nr + 1, _("in"), rule[0]["title"]))
                html.write("<td class=settingvalue used>")
                if "command_line" in serviceinfo:
                    html.write("<tt>%s</tt>" % serviceinfo["command_line"])
                else:
                    html.write(_("(no command line, passive check)"))
                html.write("</td></tr></table>")

    last_maingroup = None
    for groupname in groupnames:
        maingroup = groupname.split("/")[0]
        # Show information about a ruleset
        # Sort rulesets according to their title
        g_rulespec_group[groupname].sort(
            cmp = lambda a, b: cmp(a["title"], b["title"]))

        for rulespec in g_rulespec_group[groupname]:
            if (rulespec["itemtype"] == 'service') == (not service):
                continue # This rule is not for hosts/services

            # Open form for that group here, if we know that we have at least one rule
            if last_maingroup != maingroup:
                last_maingroup = maingroup
                grouptitle, grouphelp = g_rulegroups.get(maingroup, (maingroup, ""))
                forms.header(grouptitle, isopen = maingroup == "monconf", narrow=True, css="rulesettings")
                html.help(grouphelp)

            output_analysed_ruleset(all_rulesets, rulespec, hostname, service)


    forms.end()

PARAMETERS_UNKNOWN = []
PARAMETERS_OMIT = []
def output_analysed_ruleset(all_rulesets, rulespec, hostname, service, known_settings=PARAMETERS_UNKNOWN):
    def rule_url(rule):
        rule_folder, rule_nr = rule
        return make_link([
            ('mode', 'edit_rule'),
            ('varname', varname),
            ('rule_folder', rule_folder[".path"]),
            ('rulenr', rule_nr),
            ('host', hostname),
            ('item', service and mk_repr(service) or '')])


    varname = rulespec["varname"]
    valuespec = rulespec["valuespec"]
    url = make_link([('mode', 'edit_ruleset'), ('varname', varname), ('host', hostname), ('item', mk_repr(service))])
    forms.section('<a href="%s">%s</a>' % (url, rulespec["title"]))
    setting, rules = analyse_ruleset(rulespec, all_rulesets[varname], hostname, service)
    html.write("<table class='setting'><tr>")
    html.write("<td class=reason>")

    # Show reason for the determined value
    if len(rules) == 1:
        rule_folder, rule_nr = rules[0]
        url = rule_url(rules[0])
        html.write('<a href="%s">%s</a>' % (rule_url(rules[0]), _("Rule %d in %s") % (rule_nr + 1, rule_folder["title"])))
    elif len(rules) > 1:
        html.write('<a href="%s">%d %s</a>' % (url, len(rules), _("Rules")))
    else:
        html.write("<i>" + _("Default Value") + "</i>")
    html.write('</td>')

    # Show the resulting value or factory setting
    html.write("<td class='settingvalue %s'>" % (len(rules) > 0 and "used" or "unused"))

    # In some cases we now the settings from a check_mk automation
    if known_settings is PARAMETERS_OMIT:
        return

    # Special handling for logwatch: The check parameter is always None. The actual
    # patterns are configured in logwatch_rules. We do not have access to the actual
    # patterns here but just to the useless "None". In order not to complicate things
    # we simply display nothing here.
    elif varname == "logwatch_rules":
        pass

    elif known_settings is not PARAMETERS_UNKNOWN:
        try:
            html.write(valuespec.value_to_text(known_settings))
        except Exception, e:
            if config.debug:
                raise
            html.write(_("Invalid parameter %r: %s") % (known_settings, e))

    else:
        # For match type "dict" it can be the case the rule define some of the keys
        # while other keys are taken from the factory defaults. We need to show the
        # complete outcoming value here.
        if rules and rulespec["match"] == "dict":
            if rulespec["factory_default"] is not NO_FACTORY_DEFAULT \
                and rulespec["factory_default"] is not FACTORY_DEFAULT_UNUSED:
                fd = rulespec["factory_default"].copy()
                fd.update(setting)
                setting = fd

        if valuespec and not rules: # show the default value
            # Some rulesets are ineffective if they are empty
            if rulespec["factory_default"] is FACTORY_DEFAULT_UNUSED:
                html.write(_("(unused)"))

            # If there is a factory default then show that one
            elif rulespec["factory_default"] is not NO_FACTORY_DEFAULT:
                setting = rulespec["factory_default"]
                html.write(valuespec.value_to_text(setting))

            # Rulesets that build lists are empty if no rule matches
            elif rulespec["match"] in ("all", "list"):
                html.write(_("(no entry)"))

            # Else we use the default value of the valuespec
            else:
                html.write(valuespec.value_to_text(valuespec.default_value()))

        # We have a setting
        elif valuespec:
            if rulespec["match"] in ( "all", "list" ):
                html.write(", ".join([valuespec.value_to_text(e) for e in setting]))
            else:
                html.write(valuespec.value_to_text(setting))

        # Binary rule, no valuespec, outcome is True or False
        else:
            html.write('<img align=absmiddle class=icon title="%s" src="images/rule_%s%s.png">' % (
                setting and _("yes") or _("no"), setting and "yes" or "no", not rules and "_off" or ""))

    html.write("</td></tr></table>")

# Returns the outcoming value or None and
# a list of matching rules. These are pairs
# of rule_folder and rule_number
def analyse_ruleset(rulespec, ruleset, hostname, service):
    resultlist = []
    resultdict = {}
    effectiverules = []
    old_folder = None
    nr = -1
    for ruledef in ruleset:
        folder, rule = ruledef
        if folder != old_folder:
            old_folder = folder
            nr = -1 # Starting couting again in new folder
        nr += 1
        value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
        if rule_options.get("disabled"):
            continue

        if True != rule_matches_host_and_item(rulespec, tag_specs, host_list, item_list, folder, g_folder, hostname, service):
            continue

        if rulespec["match"] == "all":
            resultlist.append(value)
            effectiverules.append((folder, nr))

        elif rulespec["match"] == "list":
            resultlist += value
            effectiverules.append((folder, nr))

        elif rulespec["match"] == "dict":
            new_result = value.copy()
            new_result.update(resultdict)
            resultdict = new_result
            effectiverules.append((folder, nr))

        else:
            return value, [(folder, nr)]

    if rulespec["match"] in ("list", "all"):
        return resultlist, effectiverules

    elif rulespec["match"] == "dict":
        return resultdict, effectiverules

    else:
        return None, [] # No match





#.
#   .--Host Diag-----------------------------------------------------------.
#   |              _   _           _     ____  _                           |
#   |             | | | | ___  ___| |_  |  _ \(_) __ _  __ _               |
#   |             | |_| |/ _ \/ __| __| | | | | |/ _` |/ _` |              |
#   |             |  _  | (_) \__ \ |_  | |_| | | (_| | (_| |              |
#   |             |_| |_|\___/|___/\__| |____/|_|\__,_|\__, |              |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   | Verify or find out a hosts agent related configuration.              |
#   '----------------------------------------------------------------------'

def diag_host_tests():
    return [
        ('ping',          _('Ping')),
        ('agent',         _('Agent')),
        ('snmpv1',        _('SNMPv1')),
        ('snmpv2',        _('SNMPv2c')),
        ('snmpv2_nobulk', _('SNMPv2c (without Bulkwalk)')),
        ('traceroute',    _('Traceroute')),
    ]

def mode_diag_host(phase):
    hostname = html.var("host")
    if not hostname:
        raise MKGeneralException(_('The hostname is missing.'))

    if phase == 'title':
        return _('Diagnostic of host') + " " + hostname

    elif phase == 'buttons':
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        host_status_button(hostname, "hoststatus")
        html.context_button(_("Properties"),
                            make_link([("mode", "edithost"), ("host", hostname)]), "edit")
        html.context_button(_("Parameters"),
              make_link([("mode", "object_parameters"), ("host", hostname)]), "rulesets")
        html.context_button(_("Services"),
                            make_link([("mode", "inventory"), ("host", hostname)]), "services")
        return

    vs_host = Dictionary(
        required_keys = ['hostname'],
        elements = [
            ('hostname', FixedValue(hostname,
                title = _('Hostname'),
                allow_empty = False
            )),
            ('ipaddress', IPv4Address(
                title = _('IP address'),
                allow_empty = False
            )),
            ('snmp_community', TextAscii(
                title = _("SNMP Community"),
                allow_empty = False
            )),
        ]
    )

    vs_rules = Dictionary(
        optional_keys = False,
        elements = [
            ('agent_port', Integer(
                minvalue = 1,
                maxvalue = 65535,
                default_value = 6556,
                title = _("Check_MK Agent Port (<a href=\"%s\">Rules</a>)") % \
                    make_link([('mode', 'edit_ruleset'), ('varname', 'agent_ports')]),
                help = _("This variable allows to specify the TCP port to "
                         "be used to connect to the agent on a per-host-basis.")
            )),
            ('snmp_timeout', Integer(
                title = _("SNMP-Timeout (<a href=\"%s\">Rules</a>)") % \
                    make_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                help = _("After a request is sent to the remote SNMP agent we will wait up to this "
                         "number of seconds until assuming the answer get lost and retrying."),
                default_value = 1,
                minvalue = 1,
                maxvalue = 60,
                unit = _("sec"),
            )),
            ('snmp_retries', Integer(
                title = _("SNMP-Retries (<a href=\"%s\">Rules</a>)") % \
                    make_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                default_value = 5,
                minvalue = 0,
                maxvalue = 50,
            )),
            ('datasource_program', TextAscii(
                title = _("Datasource Program (<a href=\"%s\">Rules</a>)") % \
                    make_link([('mode', 'edit_ruleset'), ('varname', 'datasource_programs')]),
                help = _("For agent based checks Check_MK allows you to specify an alternative "
                         "program that should be called by Check_MK instead of connecting the agent "
                         "via TCP. That program must output the agent's data on standard output in "
                         "the same format the agent would do. This is for example useful for monitoring "
                         "via SSH. The command line may contain the placeholders <tt>&lt;IP&gt;</tt> and "
                         "<tt>&lt;HOST&gt;</tt>.")
            ))
        ]
    )

    host = g_folder[".hosts"].get(hostname)

    if not host:
        raise MKGeneralException(_('The given host does not exist.'))
    if ".nodes" in host:
        raise MKGeneralException(_('This view does not support cluster hosts.'))

    if phase == 'action':
        if not html.check_transaction():
            return

        if html.var('_save'):
            # Save the ipaddress and/or community
            mark_affected_sites_dirty(g_folder, hostname)

            new = vs_host.from_html_vars('vs_host')
            vs_host.validate_value(new, 'vs_host')
            if 'ipaddress' in new:
                host['ipaddress'] = new['ipaddress']
            if 'snmp_community' in new:
                host['snmp_community'] = new['snmp_community']
            log_pending(AFFECTED, hostname, "edit-host", _("Edited properties of host via diagnose [%s]") % hostname)
            save_folder_and_hosts(g_folder)
            reload_hosts(g_folder)
            call_hook_hosts_changed(g_folder)

            html.del_all_vars()
            html.set_var("host", hostname)
            html.set_var("folder", g_folder[".path"])

            return "edithost"
        return

    html.write('<div class="diag_host">')
    html.write('<table><tr><td>')
    html.begin_form('diag_host', method = "POST")
    forms.header(_('Host Properties'))

    forms.section(legend = False)
    vs_host.render_input("vs_host", host)
    html.help(vs_host.help())

    forms.end()

    html.write('<div style="margin-bottom:10px">')
    html.button("_save", _("Save & Exit"))
    html.write('</div>')

    forms.header(_('Options'))

    value = {}
    forms.section(legend = False)
    vs_rules.render_input("vs_rules", value)
    html.help(vs_rules.help())
    forms.end()

    html.button("_try",  _("Test"))

    html.hidden_fields()
    html.end_form()

    html.write('</td><td style="padding-left:10px;">')

    if not html.var('_try'):
        html.message(_('You can diagnose the connection to a specific host using this dialog. '
                       'You can either test wether your current configuration is still working '
                       'or investigate in which ways a host can be reached. Simply configure the '
                       'connection options you like to try on the right side of the screen and '
                       'press the "Test" button. The results will be displayed here.'))
    else:
        for ident, title in diag_host_tests():
            html.write('<h3>%s</h3>' % title)
            html.write('<table class="data test"><tr class="data odd0">')
            html.write('<td class="icons"><div>')
            html.write('<img class="icon" id="%s_img" src="">' % ident)
            html.write('<a href="javascript:start_host_diag_test(\'%s\', \'%s\');">'
                       '<img class="icon retry" id="%s_retry" src="images/icon_retry_disabled.gif" title="%s"></a>' %
                        (ident, hostname, ident, _('Retry this test')))
            html.write('</div></td>')
            html.write('<td><div class="log" id="%s_log"></div>' % ident)
            html.write('</tr></table>')
            html.javascript('start_host_diag_test("%s", "%s")' % (ident, hostname))

    html.write('</td></tr></table>')
    html.write('</div>')

def ajax_diag_host():
    try:
        prepare_folder_info()

        if not config.may('wato.diag_host'):
            raise MKAuthException(_('You are not permitted to perform this action.'))

        hostname = html.var("host")
        if not hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        host = g_folder[".hosts"].get(hostname)

        if not host:
            raise MKGeneralException(_('The given host does not exist.'))
        if ".nodes" in host:
            raise MKGeneralException(_('This view does not support cluster hosts.'))

        _test = html.var('_test')
        if not _test:
            raise MKGeneralException(_('The test is missing.'))

        # Execute a specific test
        if _test not in dict(diag_host_tests()).keys():
            raise MKGeneralException(_('Invalid test.'))
        args = [
            html.var('ipaddress'),
            html.var('snmp_community'),
            html.var('agent_port'),
            html.var('snmp_timeout'),
            html.var('snmp_retries'),
            html.var('datasource_program'),
        ]
        result = check_mk_automation(host[".siteid"], "diag-host", [hostname, _test] + args)
        # API is defined as follows: Two data fields, separated by space.
        # First is the state: 0 or 1, 0 means success, 1 means failed.
        # Second is treated as text output
        html.write("%s %s" % (result[0], html.attrencode(result[1])))
    except Exception, e:
        import traceback
        html.write("1 %s" % _("Exception: %s") % html.attrencode(traceback.format_exc()))

#.
#   .--Inventory & Services------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for doing the inventory on a single host and/or showing and     |
#   | editing the current services of a host.                              |
#   '----------------------------------------------------------------------'

def mode_inventory(phase, firsttime):
    hostname = html.var("host")
    if hostname not in g_folder[".hosts"]:
        raise MKGeneralException(_("You called this page for a non-existing host."))
    host = g_folder[".hosts"][hostname]

    if phase == "title":
        title = _("Services of host %s") % hostname
        if html.var("_scan"):
            title += _(" (live scan)")
        else:
            title += _(" (might be cached data)")
        return title

    elif phase == "buttons":
        html.context_button(_("Folder"),
                            make_link([("mode", "folder")]), "back")
        host_status_button(hostname, "host")
        html.context_button(_("Properties"), make_link([("mode", "edithost"), ("host", hostname)]), "edit")
        html.context_button(_("Parameters"),
              make_link([("mode", "object_parameters"), ("host", hostname)]), "rulesets")
        if ".nodes" not in host:
            # only display for non cluster hosts
            html.context_button(_("Diagnostic"),
                  make_link([("mode", "diag_host"), ("host", hostname)]), "diagnose")
        html.context_button(_("Full Scan"), html.makeuri([("_scan", "yes")]))

    elif phase == "action":
        config.need_permission("wato.services")
        check_host_permissions(hostname)
        if html.check_transaction():

            # Settings for showing parameters
            if html.var("_show_parameters"):
                parameter_column = True
                config.save_user_file("parameter_column", True)
                return
            elif html.var("_hide_parameters"):
                parameter_column = False
                config.save_user_file("parameter_column", False)
                return

            cache_options = html.var("_scan") and [ '@scan' ] or [ '@noscan' ]
            new_target = "folder"

            if html.var("_refresh"):
                counts, failed_hosts = check_mk_automation(host[".siteid"], "inventory", [ "@scan", "refresh", hostname ])
                count_added, count_removed, count_kept, count_new = counts[hostname]
                message = _("Refreshed check configuration of host [%s] with %d services") % \
                            (hostname, count_added)
                log_pending(LOCALRESTART, hostname, "refresh-autochecks", message)

            else:
                table = check_mk_automation(host[".siteid"], "try-inventory", cache_options + [hostname])
                table.sort()
                active_checks = {}
                for st, ct, checkgroup, item, paramstring, params, descr, state, output, perfdata in table:
                    if (html.has_var("_cleanup") or html.has_var("_fixall")) \
                        and st in [ "vanished", "obsolete" ]:
                        pass
                    elif (html.has_var("_activate_all") or html.has_var("_fixall")) \
                        and st == "new":
                        active_checks[(ct, item)] = paramstring
                    else:
                        varname = "_%s_%s" % (ct, html.varencode(item))
                        if html.var(varname, "") != "":
                            active_checks[(ct, item)] = paramstring
                    if st.startswith("clustered"):
                        active_checks[(ct, item)] = paramstring

                check_mk_automation(host[".siteid"], "set-autochecks", [hostname], active_checks)
                if host.get("inventory_failed"):
                    del host["inventory_failed"]
                    save_hosts()
                message = _("Saved check configuration of host [%s] with %d services") % \
                            (hostname, len(active_checks))
                log_pending(LOCALRESTART, hostname, "set-autochecks", message)

            mark_affected_sites_dirty(g_folder, hostname, sync=False, restart=True)
            return new_target, message
        return "folder"

    else:
        show_service_table(host, firsttime)


def show_service_table(host, firsttime):
    hostname = host[".name"]

    # Read current check configuration
    cache_options = html.var("_scan") and [ '@scan' ] or [ '@noscan' ]
    parameter_column = config.load_user_file("parameter_column", False)

    # We first try using the Cache (if the user has not pressed Full Scan).
    # If we do not find any data, we omit the cache and immediately try
    # again without using the cache.
    try:
        checktable = check_mk_automation(host[".siteid"], "try-inventory", cache_options + [hostname])
        if len(checktable) == 0 and cache_options != []:
            checktable = check_mk_automation(host[".siteid"], "try-inventory", [ '@scan', hostname ])
            html.set_var("_scan", "on")
    except Exception, e:
        if config.debug:
            raise
        html.show_error(_("Service discovery failed for this host: %s") % e)
        return

    checktable.sort()

    html.begin_form("checks", method = "POST")
    fixall = 0
    if config.may("wato.services"):
        for entry in checktable:
            if entry[0] == 'new' and not html.has_var("_activate_all") and not firsttime:
                html.button("_activate_all", _("Activate missing"))
                fixall += 1
                break
        for entry in checktable:
            if entry[0] in [ 'obsolete', 'vanished', ]:
                html.button("_cleanup", _("Remove exceeding"))
                fixall += 1
                break

        if fixall == 2:
            html.button("_fixall", _("Fix all missing/exceeding"))

        if len(checktable) > 0:
            html.button("_save", _("Save manual check configuration"))
            html.button("_refresh", _("Automatic Refresh (Tabula Rasa)"))

        html.write(" &nbsp; ")
        if parameter_column:
            html.button("_hide_parameters", _("Hide Check Parameters"))
        else:
            html.button("_show_parameters", _("Show Check Parameters"))

    html.hidden_fields()
    if html.var("_scan"):
        html.hidden_field("_scan", "on")

    table.begin(css ="data", searchable = False, limit = None, sortable = False)

    # This option will later be switchable somehow

    divid = 0
    for state_name, check_source, checkbox in [
        ( _("Available (missing) services"), "new", firsttime ),
        ( _("Already configured services"), "old", True, ),
        ( _("Obsolete services (being checked, but should be ignored)"), "obsolete", True ),
        ( _("Disabled services (configured away by admin)"), "ignored", None),
        ( _("Vanished services (checked, but no longer exist)"), "vanished", True ),
        ( _("Active checks"), "active", None ),
        ( _("Manual services (defined in main.mk)"), "manual", None ),
        ( _("Legacy services (defined in main.mk)"), "legacy", None ),
        ( _("Custom checks (defined via rule)"), "custom", None ),
        ( _("Already configured clustered services (located on cluster host)"), "clustered_old", None ),
        ( _("Available clustered services"), "clustered_new", None ),
        ]:
        first = True
        for st, ct, checkgroup, item, paramstring, params, descr, state, output, perfdata in checktable:
            item = html.attrencode(item or 'None')
            if check_source != st:
                continue
            if first:
                table.groupheader(state_name)
                first = False
            statename = nagios_short_state_names.get(state, _("PEND"))
            if statename == _("PEND"):
                stateclass = "state svcstate statep"
                state = 0 # for tr class
            else:
                stateclass = "state svcstate state%s" % state
            # html.write("<tr class=\"data %s%d\">" % (trclass, state))

            table.row(css="data", state=state)

            # Status, Checktype, Item, Description, Check Output
            table.cell(_("Status"),              statename, css=stateclass)
            table.cell(_("Checkplugin"),         ct)
            table.cell(_("Item"),                item)
            table.cell(_("Service Description"), html.attrencode(descr))
            table.cell(_("Plugin output"))

            if defaults.omd_root and check_source in ( "custom", "active" ):
                divid += 1
                html.write("<div id='activecheck%d'><img class=icon title='%s' src='images/icon_reloading.gif'></div>" % (divid, hostname))
                html.final_javascript("execute_active_check('%s', '%s', '%s', '%s', 'activecheck%d');" % (
                     host[".siteid"] or '', hostname, ct, item.replace("'", "\'"), divid))
            else:
                html.write(html.attrencode(output))

            # Icon for Rule editor, Check parameters
            varname = None
            if checkgroup:
                varname = "checkgroup_parameters:" + checkgroup
            elif check_source == "active":
                varname = "active_checks:" + ct

            if parameter_column:
                table.cell(_("Check Parameters"))
                if varname and varname in g_rulespecs:
                    rulespec = g_rulespecs[varname]
                    try:
                        rulespec["valuespec"].validate_datatype(params, "")
                        rulespec["valuespec"].validate_value(params, "")
                        paramtext = rulespec["valuespec"].value_to_text(params)
                    except Exception, e:
                        paramtext = _("Invalid check parameter: %s!") % e
                        paramtext += _(" The parameter is: %r") % (params,)

                    html.write(paramtext)

            # Icon for Service parameters. Not for missing services!
            table.cell(css='buttons')
            if check_source not in [ "new", "ignored" ]:
                # Link to list of all rulesets affecting this service
                params_url = make_link([("mode", "object_parameters"),
                                        ("host", hostname),
                                        ("service", descr)])
                html.icon_button(params_url, _("View and edit the parameters for this service"), "rulesets")

                url = make_link([("mode", "edit_ruleset"),
                                 ("varname", varname),
                                 ("host", hostname),
                                 ("item", mk_repr(item))])
                html.icon_button(url, _("Edit and analyze the check parameters of this service"), "check_parameters")

            if check_source == "ignored":
                url = make_link([("mode", "edit_ruleset"),
                                 ("varname", "ignored_services"),
                                 ("host", hostname),
                                 ("item", mk_repr(descr))])
                html.icon_button(url, _("Edit and analyze the disabled services rules"), "ignore")

            # Permanently disable icon
            if check_source in ['new', 'old']:
                url = make_link([
                    ('mode', 'edit_ruleset'),
                    ('varname', 'ignored_services'),
                    ('host', hostname),
                    ('item', mk_repr(descr)),
                    ('mode', 'new_rule'),
                    ('_new_host_rule', '1'),
                    ('filled_in', 'new_rule'),
                    ('rule_folder', ''),
                    ('back_mode', 'inventory'),
                ])
                html.icon_button(url, _("Create rule to permanently disable this service"), "ignore")

            # Temporary ignore checkbox
            table.cell()
            if checkbox != None:
                varname = "_%s_%s" % (ct, html.varencode(item))
                html.checkbox(varname, checkbox, add_attr = ['title="%s"' % _('Temporarily ignore this service')])

    table.end()
    html.end_form()


def ajax_execute_check():
    site      = html.var("site")
    hostname  = html.var("host")
    checktype = html.var("checktype")
    item      = html.var("item")
    try:
        status, output = check_mk_automation(site, "active-check", [ hostname, checktype, item ])
    except Exception, e:
        status = 1
        output = str(e)
    statename = nagios_short_state_names.get(status, "UNKN")
    html.write("%d\n%s\n%s" % (status, statename, output))


#.
#   .--Search--------------------------------------------------------------.
#   |                   ____                      _                        |
#   |                  / ___|  ___  __ _ _ __ ___| |__                     |
#   |                  \___ \ / _ \/ _` | '__/ __| '_ \                    |
#   |                   ___) |  __/ (_| | | | (__| | | |                   |
#   |                  |____/ \___|\__,_|_|  \___|_| |_|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Dialog for searching for hosts - globally in all files               |
#   '----------------------------------------------------------------------'

def mode_search(phase):
    if phase == "title":
        return _("Search for hosts")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        return "search_results"

    render_folder_path()

    ## # Show search form
    html.begin_form("edithost", method = "POST")
    forms.header(_("General Properties"))
    forms.section(_("Hostname"))
    html.text_input("host")
    html.set_focus("host")

    # Attributes
    configure_attributes(False, {}, "search", parent = None)

    # Button
    forms.end()
    html.button("_global", _("Search globally"), "submit")
    html.button("_local", _("Search in %s") % g_folder["title"], "submit")
    html.hidden_fields()
    html.end_form()


def mode_search_results(phase):
    if phase == "title":
        return _("Search results")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Search"), html.makeuri([("mode", "search")]), "back")
        return

    elif phase == "action":
        return

    crit = { ".name" : html.var("host") }
    crit.update(collect_attributes(do_validate = False))

    if html.has_var("_local"):
        folder = g_folder
    else:
        folder = g_root_folder

    if not search_hosts_in_folders(folder, crit):
        html.message(_("No matching hosts found."))




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
        found.sort(cmp = lambda a,b: cmp(num_split(a[0]), num_split(b[0])))

        table.begin("search_hosts", "");
        for hostname, host, effective in found:
            host_url =  make_link_to([("mode", "edithost"), ("host", hostname)], folder)
            table.row()
            table.cell(_("Hostname"), '<a href="%s">%s</a>' % (host_url, hostname))
            for attr, topic in host_attributes:
                attrname = attr.name()
                if attr.show_in_table():
                    if attrname in host:
                        tdclass, content = attr.paint(host[attrname], hostname)
                    else:
                        tdclass, content = attr.paint(effective[attrname], hostname)
                        tdclass += " inherited"
                    table.cell(attr.title(), content, css=tdclass)
        table.end()

    return len(found)

#.
#   .--CSV-Import----------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

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
    log_pending(AFFECTED, g_folder, "move-hosts", _("Moved %d imported hosts to their original destination.") % num_moved)
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
                    ".parent"    : folder,
                }

                if '.siteid' in folder:
                    new_folder['.siteid'] = folder[".siteid"]

                folder[".folders"][name] = new_folder
                g_folders[new_path] = new_folder
                folder = new_folder
                parts = parts[1:]
                save_folder(folder) # make sure, directory is created
                reload_folder(folder)

    return folder

#.
#   .--Bulk Import---------------------------------------------------------.
#   |       ____        _ _      ___                            _          |
#   |      | __ ) _   _| | | __ |_ _|_ __ ___  _ __   ___  _ __| |_        |
#   |      |  _ \| | | | | |/ /  | || '_ ` _ \| '_ \ / _ \| '__| __|       |
#   |      | |_) | |_| | |   <   | || | | | | | |_) | (_) | |  | |_        |
#   |      |____/ \__,_|_|_|\_\ |___|_| |_| |_| .__/ \___/|_|   \__|       |
#   |                                         |_|                          |
#   +----------------------------------------------------------------------+
#   | Realizes a simple page with a single textbox which one can insert    |
#   | several hostnames, separated by different chars and submit it to     |
#   | create these hosts in the current folder.                            |
#   '----------------------------------------------------------------------'

def mode_bulk_import(phase):
    if phase == "title":
        return _('Bulk Host Import')

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")

    elif phase == "action":
        if not html.check_transaction():
            return "folder"

        attributes = collect_attributes()

        config.need_permission("wato.manage_hosts")
        check_folder_permissions(g_folder, "write")
        check_user_contactgroups(attributes.get("contactgroups", (False, [])))

        hosts = html.var('_hosts')
        if not hosts:
            raise MKUserError('_hosts', _('Please specify at least one hostname.'))

        created  = 0
        skipped  = 0
        selected = []

        # Split by all possible separators
        hosts = hosts.replace(' ', ';').replace(',', ';').replace('\n', ';').replace('\r', '')
        for hostname in hosts.split(';'):
            if hostname in g_folder['.hosts']:
                skipped += 1
                continue
            elif not re.match('^[a-zA-Z0-9-_.]+$', hostname):
                skipped += 1
                continue

            new_host = {
                '.name'   : hostname,
                '.folder' : g_folder,
            }
            g_folder[".hosts"][hostname] = new_host
            mark_affected_sites_dirty(g_folder, hostname)

            message = _("Created new host %s.") % hostname
            log_pending(AFFECTED, hostname, "create-host", message)
            g_folder["num_hosts"] += 1
            created += 1
            selected.append('_c_%s' % hostname)

        if not created:
            return 'folder', _('No host has been imported.')

        else:
            save_folder_and_hosts(g_folder)
            reload_hosts(g_folder)
            call_hook_hosts_changed(g_folder)

            if html.get_checkbox('_do_service_detection'):
                # Create a new selection
                weblib.set_rowselection('wato-folder-/'+g_folder['.path'], selected, 'set')
                html.set_var('mode', 'bulkinventory')
                html.set_var('show_checkboxes', '1')
                return 'bulkinventory'

            result_txt = ''
            if skipped > 0:
                result_txt = _('Imported %d hosts, but skipped %d hosts. Hosts might '
                    'be skipped when they already exist or contain illegal chars.') % (created, skipped)
            else:
                result_txt = _('Imported %d hosts.') % created

            return 'folder', result_txt

    else:
        html.begin_form("bulkimport", method = "POST")

        html.write('<p>')
        html.write(_('Using this page you can import several hosts at once into '
            'the choosen folder. You can paste a list of hostnames, separated '
            'by comma, semicolon, space or newlines. These hosts will then be '
            'added to the folder using the default attributes. If some of the '
            'host names cannot be resolved via DNS, you must manually edit '
            'those hosts later and add explicit IP addresses.'))
        html.write('</p>')
        forms.header(_('Bulk Host Import'))
        forms.section(_('Hosts'))
        html.text_area('_hosts', cols = 70, rows = 10)

        forms.section(_('Options'))
        html.checkbox('_do_service_detection', False, label = _('Perform automatic service discovery'))
        forms.end()

        html.button('_import', _('Import'))

        html.hidden_fields()
        html.end_form()

#.
#   .--Bulk-Inventory------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

def mode_bulk_inventory(phase):
    if phase == "title":
        return _("Bulk Service Discovery")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.var("_item"):
            if not html.check_transaction():
                html.write(repr([ 'failed', 0, 0, 0, 0, 0, 0, ]) + "\n")
                html.write(_("Error during discovery: Maximum number of retries reached. "
                             "You need to restart the bulk service discovery"))
                return ""

            how = html.var("how")
            try:
                site_id, folderpath, hostnamesstring = html.var("_item").split("|")
                hostnames = hostnamesstring.split(";")
                num_hosts = len(hostnames)
                folder = g_folders[folderpath]
                load_hosts(folder)
                arguments = [how,] + hostnames
                if html.var("use_cache"):
                    arguments = [ "@cache" ] + arguments
                if html.var("do_scan"):
                    arguments = [ "@scan" ] + arguments
                counts, failed_hosts = check_mk_automation(site_id, "inventory", arguments)
                # sum up host individual counts to have a total count
                sum_counts = [ 0, 0, 0, 0 ] # added, removed, kept, new
                result_txt = ''
                for hostname in hostnames:
                    sum_counts[0] += counts[hostname][0]
                    sum_counts[1] += counts[hostname][1]
                    sum_counts[2] += counts[hostname][2]
                    sum_counts[3] += counts[hostname][3]
                    host = folder[".hosts"][hostname]
                    if hostname in failed_hosts:
                        result_txt += _("Failed to inventorize %s: %s<br>") % (hostname, failed_hosts[hostname])
                        if not host.get("inventory_failed"):
                            host["inventory_failed"] = True
                            save_hosts(folder)
                    else:
                        result_txt += _("Inventorized %s<br>\n") % hostname
                        mark_affected_sites_dirty(folder, hostname, sync=False, restart=True)
                        log_pending(AFFECTED, hostname, "bulk-inventory",
                            _("Inventorized host: %d added, %d removed, %d kept, %d total services") %
                                                                                tuple(counts[hostname]))
                        if "inventory_failed" in host:
                            del host["inventory_failed"]
                            save_hosts(folder) # Could be optimized, but difficult here

                result = repr([ 'continue', num_hosts, len(failed_hosts) ] + sum_counts) + "\n" + result_txt

            except Exception, e:
                result = repr([ 'failed', num_hosts, num_hosts, 0, 0, 0, 0, ]) + "\n"
                if site_id:
                    msg = _("Error during inventory of %s on site %s<div class=exc>%s</div") % \
                                     (", ".join(hostnames), site_id, e)
                else:
                    msg = _("Error during inventory of %s<div class=exc>%s</div>") % (", ".join(hostnames), e)
                if config.debug:
                    msg += "<br><pre>%s</pre><br>" % format_exception().replace("\n", "<br>")
                result += msg
            html.write(result)
            return ""
        return


    # interactive progress is *not* done in action phase. It
    # renders the page content itself.

    def recurse_hosts(folder, recurse, only_failed):
        entries = []
        hosts = load_hosts(folder)
        for hostname, host in hosts.items():
            if not only_failed or host.get("inventory_failed"):
                entries.append((hostname, folder))
        if recurse:
            for f in folder[".folders"].values():
                entries += recurse_hosts(f, recurse, only_failed)
        return entries

    config.need_permission("wato.services")

    if html.get_checkbox("only_failed_invcheck"):
        restrict_to_hosts = find_hosts_with_failed_inventory_check()
    else:
        restrict_to_hosts = None

    if html.get_checkbox("only_ok_agent"):
        skip_hosts = find_hosts_with_failed_agent()
    else:
        skip_hosts = []

    # 'all' not set -> only inventorize checked hosts
    hosts_to_inventorize = []

    if not html.var("all"):
        complete_folder = False
        if html.get_checkbox("only_failed"):
            filterfunc = lambda host: host.get("inventory_failed")
        else:
            filterfunc = None

        hostnames = get_hostnames_from_checkboxes(filterfunc)
        for hostname in hostnames:
            if restrict_to_hosts and hostname not in restrict_to_hosts:
                continue
            if hostname in skip_hosts:
                continue
            check_host_permissions(hostname)
            host = g_folder[".hosts"][hostname]
            eff = effective_attributes(host, g_folder)
            site_id = eff.get("site")
            hosts_to_inventorize.append( (site_id, g_folder[".path"], hostname) )

    # all host in this folder, maybe recursively. New: we always group
    # a bunch of subsequent hosts of the same folder into one item.
    # That saves automation calls and speeds up mass inventories.
    else:
        complete_folder = True
        entries = recurse_hosts(g_folder, html.get_checkbox("recurse"), html.get_checkbox("only_failed"))
        items = []
        hostnames = []
        current_folder = None
        num_hosts_in_current_chunk = 0
        for hostname, folder in entries:
            if restrict_to_hosts != None and hostname not in restrict_to_hosts:
                continue
            if hostname in skip_hosts:
                continue
            check_host_permissions(hostname, folder=folder)
            host = folder[".hosts"][hostname]
            eff = effective_attributes(host, folder)
            site_id = eff.get("site")
            hosts_to_inventorize.append( (site_id, folder[".path"], hostname) )

    # Create a list of items for the progress bar, where we group
    # subsequent hosts that are in the same folder and site
    hosts_to_inventorize.sort()

    current_site_and_folder = None
    items = []
    hosts_in_this_item = 0
    bulk_size = int(html.var("bulk_size", 10))
    for site_id, folder_path, hostname in hosts_to_inventorize:
        if not items or (site_id, folder_path) != current_site_and_folder or hosts_in_this_item >= bulk_size:
            items.append("%s|%s|%s" % (site_id, folder_path, hostname))
            hosts_in_this_item = 1
        else:
            items[-1] += ";" + hostname
            hosts_in_this_item += 1
        current_site_and_folder = site_id, folder_path


    if html.var("_start"):
        # Start interactive progress
        interactive_progress(
            items,
            _("Bulk Service Discovery"),  # title
            [ (_("Total hosts"),      0),
              (_("Failed hosts"),     0),
              (_("Services added"),   0),
              (_("Services removed"), 0),
              (_("Services kept"),    0),
              (_("Total services"),   0) ], # stats table
            [ ("mode", "folder") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
            fail_stats = [ 1 ],
        )

    else:
        html.begin_form("bulkinventory", method = "POST")
        html.hidden_fields()

        # Mode of action
        html.write("<p>")
        if not complete_folder:
            html.write(_("You have selected <b>%d</b> hosts for bulk discovery. ") % len(hostnames))
        html.write(_("Check_MK service discovery will automatically find and configure "
                     "services to be checked on your hosts."))
        forms.header(_("Bulk Discovery"))
        forms.section(_("Mode"))
        html.radiobutton("how", "new",     True,  _("Find only new services") + "<br>")
        html.radiobutton("how", "remove",  False, _("Remove obsolete services") + "<br>")
        html.radiobutton("how", "fixall",  False, _("Find new &amp; remove obsolete") + "<br>")
        html.radiobutton("how", "refresh", False, _("Refresh all services (tabula rasa)") + "<br>")

        forms.section(_("Selection"))
        if complete_folder:
            html.checkbox("recurse", True, label=_("Include all subfolders"))
            html.write("<br>")
        html.checkbox("only_failed", False, label=_("Only include hosts that failed on previous discovery"))
        html.write("<br>")
        html.checkbox("only_failed_invcheck", False, label=_("Only include hosts with a failed discovery check"))
        html.write("<br>")
        html.checkbox("only_ok_agent", False, label=_("Exclude hosts where the agent is unreachable"))

        forms.section(_("Performance options"))
        html.checkbox("use_cache", True, label=_("Use cached data if present"))
        html.write("<br>")
        html.checkbox("do_scan", True, label=_("Do full SNMP scan for SNMP devices"))
        html.write("<br>")
        html.write(_("Number of hosts to handle at once:") + " ")
        html.number_input("bulk_size", 10, size=3)

        # Start button
        forms.end()
        html.button("_start", _("Start"))

def find_hosts_with_failed_inventory_check():
    return html.live.query_column(
        "GET services\n"
        "Filter: description = Check_MK inventory\n" # FIXME: Remove this one day
        "Filter: description = Check_MK Discovery\n"
        "Or: 2\n"
        "Filter: state > 0\n"
        "Columns: host_name")

def find_hosts_with_failed_agent():
    return html.live.query_column(
        "GET services\n"
        "Filter: description = Check_MK\n"
        "Filter: state >= 2\n"
        "Columns: host_name")

#.
#   .--Bulk-Edit-----------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

def mode_bulk_edit(phase):
    if phase == "title":
        return _("Bulk edit hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            config.need_permission("wato.edit_hosts")

            changed_attributes = collect_attributes()
            if "contactgroups" in changed_attributes:
                 if True != check_folder_permissions(g_folder, "write", False):
                     raise MKAuthException(_("Sorry. In order to change the permissions of a host you need write "
                                             "access to the folder it is contained in."))

            hostnames = get_hostnames_from_checkboxes()
            # Check all permissions for doing any edit
            for hostname in hostnames:
                check_host_permissions(hostname)

            for hostname in hostnames:
                host = g_folder[".hosts"][hostname]
                mark_affected_sites_dirty(g_folder, hostname)
                host.update(changed_attributes)
                mark_affected_sites_dirty(g_folder, hostname)
                log_pending(AFFECTED, hostname, "bulk-edit", _("Changed attributes of host %s in bulk mode") % hostname)
            save_folder_and_hosts(g_folder)
            reload_hosts() # indirect host tag changes
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

    html.begin_form("edithost", method = "POST")
    configure_attributes(False, hosts, "bulk", parent = g_folder)
    forms.end()
    html.button("_save", _("Save &amp; Finish"))
    html.hidden_fields()
    html.end_form()


#.
#   .--Bulk-Cleanup--------------------------------------------------------.
#   |      ____        _ _       ____ _                                    |
#   |     | __ ) _   _| | | __  / ___| | ___  __ _ _ __  _   _ _ __        |
#   |     |  _ \| | | | | |/ / | |   | |/ _ \/ _` | '_ \| | | | '_ \       |
#   |     | |_) | |_| | |   <  | |___| |  __/ (_| | | | | |_| | |_) |      |
#   |     |____/ \__,_|_|_|\_\  \____|_|\___|\__,_|_| |_|\__,_| .__/       |
#   |                                                         |_|          |
#   +----------------------------------------------------------------------+
#   | Mode for removing attributes from host in bulk mode.                 |
#   '----------------------------------------------------------------------'

def mode_bulk_cleanup(phase):
    if phase == "title":
        return _("Bulk removal of explicit attributes")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            config.need_permission("wato.edit_hosts")
            to_clean = bulk_collect_cleaned_attributes()
            if "contactgroups" in to_clean:
                 if True != check_folder_permissions(g_folder, "write", False):
                     raise MKAuthException(_("Sorry. In order to change the permissions of a host you need write "
                                             "access to the folder it is contained in."))
            hostnames = get_hostnames_from_checkboxes()

            # Check all permissions for doing any edit
            for hostname in hostnames:
                check_host_permissions(hostname)

            for hostname in hostnames:
                mark_affected_sites_dirty(g_folder, hostname)
                host = g_folder[".hosts"][hostname]
                num_cleaned = 0
                for attrname in to_clean:
                    num_cleaned += 1
                    if attrname in host:
                        del host[attrname]
                if num_cleaned > 0:
                    log_pending(AFFECTED, hostname, "bulk-cleanup", _("Cleaned %d attributes of host %s in bulk mode") % (
                    num_cleaned, hostname))
                    mark_affected_sites_dirty(g_folder, hostname)
            save_hosts(g_folder)
            reload_hosts() # indirect host tag changes
            return "folder"
        return

    hostnames = get_hostnames_from_checkboxes()
    hosts = dict([(hn, g_folder[".hosts"][hn]) for hn in hostnames])

    html.write("<p>" + _("You have selected <b>%d</b> hosts for bulk cleanup. This means removing "
    "explicit attribute values from hosts. The hosts will then inherit attributes "
    "configured at the host list or folders or simply fall back to the builtin "
    "default values.") % len(hostnames))
    html.write("</p>")

    html.begin_form("bulkcleanup", method = "POST")
    forms.header(_("Attributes to remove from hosts"))
    if not bulk_cleanup_attributes(g_folder, hosts):
        forms.end()
        html.write(_("The selected hosts have no explicit attributes"))
    else:
        forms.end()
        html.button("_save", _("Save &amp; Finish"))
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
        forms.section(attr.title())

        if attr.is_mandatory() and not is_inherited:
            html.write(_("This attribute is mandatory and there is no value "
                         "defined in the host list or any parent folder."))
        else:
            label = "clean this attribute on <b>%s</b> hosts" % \
                (num_haveit == len(hosts) and "all selected" or str(num_haveit))
            html.checkbox("_clean_%s" % attrname, False, label=label)
        html.help(attr.help())

    return num_shown > 0



#.
#   .--Parentscan----------------------------------------------------------.
#   |          ____                      _                                 |
#   |         |  _ \ __ _ _ __ ___ _ __ | |_ ___  ___ __ _ _ __            |
#   |         | |_) / _` | '__/ _ \ '_ \| __/ __|/ __/ _` | '_ \           |
#   |         |  __/ (_| | | |  __/ | | | |_\__ \ (_| (_| | | | |          |
#   |         |_|   \__,_|_|  \___|_| |_|\__|___/\___\__,_|_| |_|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Automatic scan for parents (similar to cmk --scan-parents)           |
#   '----------------------------------------------------------------------'
def mode_parentscan(phase):
    if phase == "title":
        return _("Parent scan")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    # Ignored during initial form display
    settings = {
        "where"          : html.var("where"),
        "alias"          : html.var_utf8("alias", "").strip() or None,
        "recurse"        : html.get_checkbox("recurse"),
        "select"         : html.var("select"),
        "timeout"        : saveint(html.var("timeout")) or 8,
        "probes"         : saveint(html.var("probes")) or 2,
        "max_ttl"        : saveint(html.var("max_ttl")) or 10,
        "force_explicit" : html.get_checkbox("force_explicit"),
        "ping_probes"    : saveint(html.var("ping_probes")) or 0,
    }

    if phase == "action":
        if html.var("_item"):
            try:
                # TODO: We could improve the performance by scanning
                # in parallel. The automation already can do this.
                # We would need to cluster hosts into bulks here.
                folderpath, hostname = html.var("_item").split("|")
                folder = g_folders[folderpath]
                load_hosts(folder)
                host = folder[".hosts"][hostname]
                eff = effective_attributes(host, folder)
                site_id = eff.get("site")
                params = map(str, [ settings["timeout"], settings["probes"], settings["max_ttl"], settings["ping_probes"] ])
                gateways = check_mk_automation(site_id, "scan-parents", params + [hostname])
                gateway, state, skipped_gateways, error = gateways[0]

                if state in [ "direct", "root", "gateway" ]:
                    message, pconf, gwcreat = \
                        configure_gateway(state, site_id, folder, host, eff, gateway)
                else:
                    message = error
                    pconf = False
                    gwcreat = False

                # Possible values for state are:
                # failed, dnserror, garbled, root, direct, notfound, gateway
                counts = [ 'continue',
                    1,                                           # Total hosts
                    gateway and 1 or 0,                          # Gateways found
                    state in [ "direct", "root" ] and 1 or 0,    # Directly reachable hosts
                    skipped_gateways,                            # number of failed PING probes
                    state == "notfound" and 1 or 0,              # No gateway found
                    pconf and 1 or 0,                            # New parents configured
                    gwcreat and 1 or 0,                          # Gateway hosts created
                    state in [ "failed", "dnserror", "garbled" ] and 1 or 0, # Errors
                ]
                result = "%r\n%s: %s<br>\n" % (counts, hostname, message)

            except Exception, e:
                result = repr([ 'failed', 1, 0, 0, 0, 0, 0, 1 ]) + "\n"
                if site_id:
                    msg = _("Error during parent scan of %s on site %s: %s") % (hostname, site_id, e)
                else:
                    msg = _("Error during parent scan of %s: %s") % (hostname, e)
                if config.debug:
                    msg += "<br><pre>%s</pre>" % format_exception().replace("\n", "<br>")
                result += msg + "\n<br>"
            html.write(result)
            return ""
        return


    config.need_permission("wato.parentscan")

    # interactive progress is *not* done in action phase. It
    # renders the page content itself.

    # select: 'noexplicit' -> no explicit parents
    #         'no'         -> no implicit parents
    #         'ignore'     -> not important
    def include_host(folder, host, select):
        if select == 'noexplicit' and "parents" in host:
            return False
        elif select == 'no':
            effective = effective_attributes(host, folder)
            if effective.get("parents"):
                return False
        return True

    def recurse_hosts(folder, recurse, select):
        entries = []
        hosts = load_hosts(folder)
        for hostname, host in hosts.items():
            if include_host(folder, host, select):
                entries.append((hostname, folder))

        if recurse:
            for f in folder[".folders"].values():
                entries += recurse_hosts(f, recurse, select)
        return entries

    # 'all' not set -> only scan checked hosts in current folder, no recursion
    if not html.var("all"):
        complete_folder = False
        items = []
        for hostname in get_hostnames_from_checkboxes():
            host = g_folder[".hosts"][hostname]
            if include_host(g_folder, host, settings["select"]):
                items.append("%s|%s" % (g_folder[".path"], hostname))

    # all host in this folder, maybe recursively
    else:
        complete_folder = True
        entries = recurse_hosts(g_folder, settings["recurse"], settings["select"])
        items = []
        for hostname, folder in entries:
            items.append("%s|%s" % (folder[".path"], hostname))


    if html.var("_start"):
        # Persist settings
        config.save_user_file("parentscan", settings)


        # Start interactive progress
        interactive_progress(
            items,
            _("Parent scan"),  # title
            [ (_("Total hosts"),               0),
              (_("Gateways found"),            0),
              (_("Directly reachable hosts"),  0),
              (_("Unreachable gateways"),      0),
              (_("No gateway found"),          0),
              (_("New parents configured"),    0),
              (_("Gateway hosts created"),     0),
              (_("Errors"),                    0),
            ],
            [ ("mode", "folder") ], # URL for "Stop/Finish" button
            50, # ms to sleep between two steps
            fail_stats = [ 1 ],
        )

    else:
        html.begin_form("parentscan", method = "POST")
        html.hidden_fields()

        # Mode of action
        html.write("<p>")
        if not complete_folder:
            html.write(_("You have selected <b>%d</b> hosts for parent scan. ") % len(items))
        html.write("<p>" +
                   _("The parent scan will try to detect the last gateway "
                   "on layer 3 (IP) before a host. This will be done by "
                   "calling <tt>traceroute</tt>. If a gateway is found by "
                   "that way and its IP address belongs to one of your "
                   "monitored hosts, that host will be used as the hosts "
                   "parent. If no such host exists, an artifical ping-only "
                   "gateway host will be created if you have not disabled "
                   "this feature.") + "</p>")

        forms.header(_("Settings for Parent Scan"))

        settings = config.load_user_file("parentscan", {
            "where"          : "subfolder",
            "alias"          : _("Created by parent scan"),
            "recurse"        : True,
            "select"         : "noexplicit",
            "timeout"        : 8,
            "probes"         : 2,
            "ping_probes"    : 5,
            "max_ttl"        : 10,
            "force_explicit" : False,
        })

        # Selection
        forms.section(_("Selection"))
        if complete_folder:
            html.checkbox("recurse", settings["recurse"], label=_("Include all subfolders"))
            html.write("<br>")
        html.radiobutton("select", "noexplicit", settings["select"] == "noexplicit",
                _("Skip hosts with explicit parent definitions (even if empty)") + "<br>")
        html.radiobutton("select", "no",  settings["select"] == "no",
                _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>")
        html.radiobutton("select", "ignore",  settings["select"] == "ignore",
                _("Scan all hosts") + "<br>")

        # Performance
        forms.section(_("Performance"))
        html.write("<table><tr><td>")
        html.write(_("Timeout for responses") + ":</td><td>")
        html.number_input("timeout", settings["timeout"], size=2)
        html.write(" %s</td></tr>" % _("sec"))
        html.write("<tr><td>")
        html.write(_("Number of probes per hop") + ":</td><td>")
        html.number_input("probes", settings["probes"], size=2)
        html.write('</td></tr>')
        html.write("<tr><td>")
        html.write(_("Maximum distance (TTL) to gateway") + ":</td><td>")
        html.number_input("max_ttl", settings["max_ttl"], size=2)
        html.write('</td></tr>')
        html.write('<tr><td>')
        html.write(_("Number of PING probes") + ":")
        html.help(_("After a gateway has been found, Check_MK checks if it is reachable "
                    "via PING. If not, it is skipped and the next gateway nearer to the "
                    "monitoring core is being tried. You can disable this check by setting "
                    "the number of PING probes to 0."))
        html.write("</td><td>")
        html.number_input("ping_probes", settings.get("ping_probes", 5), size=2)
        html.write('</td></tr>')
        html.write('</table>')

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox("force_explicit",
            settings["force_explicit"], label=_("Force explicit setting for parents even if setting matches that of the folder"))

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write(_("Create gateway hosts in<ul>"))
        html.radiobutton("where", "subfolder", settings["where"] == "subfolder",
                _("in the subfolder <b>%s/Parents</b>") % g_folder["title"])
        html.write("<br>")
        html.radiobutton("where", "here", settings["where"] == "here",
                _("directly in the folder <b>%s</b>") % g_folder["title"])
        html.write("<br>")
        html.radiobutton("where", "there", settings["where"] == "there",
                _("in the same folder as the host"))
        html.write("<br>")
        html.radiobutton("where", "nowhere", settings["where"] == "nowhere",
                _("do not create gateway hosts"))
        html.write("</ul>")
        html.write(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", settings["alias"])

        # Start button
        forms.end()
        html.button("_start", _("Start"))


def configure_gateway(state, site_id, folder, host, effective, gateway):
    # Settings for configuration and gateway creation
    force_explicit = html.get_checkbox("force_explicit")
    where          = html.var("where")
    alias          = html.var("alias")

    # If we have found a gateway, we need to know a matching
    # host name from our configuration. If there is none,
    # we can create one, if the users wants this. The automation
    # for the parent scan already tries to find such a host
    # within the site.
    gwcreat = False

    if gateway:
        gw_host, gw_ip, dns_name = gateway
        if not gw_host:
            if where == "nowhere":
                return _("No host %s configured, parents not set") % gw_ip, \
                    False, False

            # Determine folder where to create the host.
            elif where == "here": # directly in current folder
                gw_folder = g_folder
            elif where == "subfolder":
                # Put new gateways in subfolder "Parents" of current
                # folder. Does this folder already exist?
                if "parents" in g_folder[".folders"]:
                    gw_folder = g_folder[".folders"]["parents"]
                    load_hosts(gw_folder)
                else:
                    # Create new gateway folder
                    config.need_permission("wato.manage_folders")
                    check_folder_permissions(g_folder, "write")
                    gw_folder = {
                        ".name"      : "parents",
                        ".parent"    : g_folder,
                        ".path"      : g_folder[".path"] + "/parents",
                        "title"      : _("Parents"),
                        "attributes" : {},
                        ".folders"   : {},
                        ".hosts"     : {},
                        "num_hosts"  : 0,
                    }
                    g_folders[gw_folder[".path"]] = gw_folder
                    g_folder[".folders"]["parent"] = gw_folder
                    save_folder(gw_folder)
                    call_hook_folder_created(gw_folder)
                    log_pending(AFFECTED, gw_folder, "new-folder",
                               _("Created new folder %s during parent scant")
                                 % gw_folder[".path"])
            elif where == "there": # In same folder as host
                gw_folder = folder
                load_hosts(gw_folder)

            # Create gateway host
            config.need_permission("wato.manage_hosts")
            check_folder_permissions(gw_folder, "write")
            if dns_name:
                gw_host = dns_name
            elif site_id:
                gw_host = "gw-%s-%s" % (site_id, gw_ip.replace(".", "-"))
            else:
                gw_host = "gw-%s" % (gw_ip.replace(".", "-"))

            new_host = {
                ".name" :     gw_host,
                "ipaddress" : gw_ip,
                ".folder" :   gw_folder,
            }
            if alias:
                new_host["alias"] = alias

            # Important: set the "site" attribute for the new host, but
            # only set it explicitely if it differs from the id of the
            # folder.
            e = effective_attributes(new_host, gw_folder)
            if "site" in e and e["site"] != site_id:
                new_host["site"] = site_id

            gw_folder[".hosts"][new_host[".name"]] = new_host
            save_hosts(gw_folder)
            reload_hosts(gw_folder)
            save_folder(gw_folder)
            mark_affected_sites_dirty(gw_folder, gw_host)
            log_pending(AFFECTED, gw_host, "new-host",
                        _("Created new host %s during parent scan") % gw_host)

            reload_folder(gw_folder)
            gwcreat = True

        parents = [ gw_host ]

    else:
        parents = []

    if effective["parents"] == parents:
        return _("Parents unchanged at %s") %  \
                (parents and ",".join(parents) or _("none")), False, gwcreat


    config.need_permission("wato.edit_hosts")
    check_host_permissions(host[".name"], folder=folder)

    if force_explicit:
        host["parents"] = parents
    else:
        # Check which parents the host would have inherited
        if "parents" in host:
            del host["parents"]
            effective = effective_attributes(host, folder)
        if effective["parents"] != parents:
            host["parents"] = parents

    if parents:
        message = _("Set parents to %s") % ",".join(parents)
    else:
        message = _("Removed parents")

    mark_affected_sites_dirty(folder, host[".name"])
    save_hosts(folder)
    log_pending(AFFECTED, host[".name"], "set-gateway", message)
    return message, True, gwcreat


#.
#   .--Random Hosts--------------------------------------------------------.
#   |  ____                 _                   _   _           _          |
#   | |  _ \ __ _ _ __   __| | ___  _ __ ___   | | | | ___  ___| |_ ___    |
#   | | |_) / _` | '_ \ / _` |/ _ \| '_ ` _ \  | |_| |/ _ \/ __| __/ __|   |
#   | |  _ < (_| | | | | (_| | (_) | | | | | | |  _  | (_) \__ \ |_\__ \   |
#   | |_| \_\__,_|_| |_|\__,_|\___/|_| |_| |_| |_| |_|\___/|___/\__|___/   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | This module allows the creation of large numbers of random hosts,    |
#   | for test and development.                                            |
#   '----------------------------------------------------------------------'
def mode_random_hosts(phase):
    if phase == "title":
        return _("Random Hosts")

    elif phase == "buttons":
        html.context_button(_("Folder"), make_link([("mode", "folder")]), "back")
        return

    elif phase == "action":
        if html.check_transaction():
            count = int(html.var("count"))
            folders = int(html.var("folders"))
            levels = int(html.var("levels"))
            created = create_random_hosts(g_folder, count, folders, levels)
            log_pending(AFFECTED, g_folder, "create-random-hosts",
                _("Created %d random hosts in %d folders") % (created, folders))
            return "folder", _("Created %d random hosts.") % created
        else:
            return "folder"

    html.begin_form("random")
    forms.header(_("Create Random Hosts"))
    forms.section(_("Number to create"))
    html.write("%s: " % _("Hosts to create in each folder"))
    html.number_input("count", 10)
    html.set_focus("count")
    html.write("<br>%s: " % _("Number of folders to create in each level"))
    html.number_input("folders", 10)
    html.write("<br>%s: " % _("Levels of folders to create"))
    html.number_input("levels", 1)

    forms.end()
    html.button("start", _("Start!"), "submit")
    html.hidden_fields()
    html.end_form()

def create_random_hosts(folder, count, folders, levels):
    if levels == 0:
        created = 0
        while created < count:
            name = "random_%010d" % int(random.random() * 10000000000)
            host = {"ipaddress" : "127.0.0.1"}
            folder[".hosts"][name] = host
            created += 1
        folder["num_hosts"] += count
        save_folder_and_hosts(folder)
        mark_affected_sites_dirty(folder)
        reload_hosts()
        return count
    else:
        total_created = 0
        if folder[".path"]:
            prefixpath = folder[".path"] + "/"
        else:
            prefixpath = ""
        created = 0
        while created < folders:
            created += 1
            i = 1
            while True:
                name = "folder_%02d" % i
                if name not in folder[".folders"]:
                    break
                i += 1
            title = "Subfolder %02d" % i
            path = prefixpath + name
            subfolder = {
                ".parent" : folder,
                ".name" : name,
                ".folders" : {},
                ".hosts" : {},
                ".path" : path,
                ".siteid" : None,
                "attributes" : {},
                "num_hosts" : 0,
                "title" : title,
            }
            g_folders[path] = subfolder
            folder[".folders"][name] = subfolder
            save_folder(subfolder)
            total_created += create_random_hosts(subfolder, count, folders, levels - 1)
        save_folder(folder)
        return total_created

#.
#   .--Auditlog------------------------------------------------------------.
#   |                    _                 __ _ _                          |
#   |                   | |    ___   __ _ / _(_) | ___                     |
#   |                   | |   / _ \ / _` | |_| | |/ _ \                    |
#   |                   | |__| (_) | (_| |  _| | |  __/                    |
#   |                   |_____\___/ \__, |_| |_|_|\___|                    |
#   |                               |___/                                  |
#   +----------------------------------------------------------------------+
#   | Handling of the audit logfiles                                       |
#   '----------------------------------------------------------------------'
def mode_auditlog(phase):
    if phase == "title":
        return _("Audit Log")

    elif phase == "buttons":
        home_button()
        changelog_button()
        if log_exists("audit") and config.may("wato.auditlog") and config.may("wato.edit"):
            html.context_button(_("Download"),
                html.makeactionuri([("_action", "csv")]), "download")
            if config.may("wato.edit"):
                html.context_button(_("Clear Log"),
                    html.makeactionuri([("_action", "clear")]), "trash")
        return

    elif phase == "action":
        if html.var("_action") == "clear":
            config.need_permission("wato.auditlog")
            config.need_permission("wato.edit")
            return clear_audit_log_after_confirm()

        elif html.var("_action") == "csv":
            config.need_permission("wato.auditlog")
            return export_audit_log()

    audit = parse_audit_log("audit")
    if len(audit) == 0:
        html.write("<div class=info>" + _("The audit log is empty.") + "</div>")
    else:
        render_audit_log(audit, "audit")

#.
#   .--Pending & Replication-----------------------------------------------.
#   |                 ____                _ _                              |
#   |                |  _ \ ___ _ __   __| (_)_ __   __ _                  |
#   |                | |_) / _ \ '_ \ / _` | | '_ \ / _` |                 |
#   |                |  __/  __/ | | | (_| | | | | | (_| |                 |
#   |                |_|   \___|_| |_|\__,_|_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Mode for activating pending changes. Does also replication with      |
#   | remote sites in distributed WATO.                                    |
#   '----------------------------------------------------------------------'

def mode_changelog(phase):
    # See below for the usage of this weird variable...
    global sitestatus_do_async_replication
    try:
        sitestatus_do_async_replication
    except:
        sitestatus_do_async_replication = False

    if phase == "title":
        return _("Pending changes to activate")

    elif phase == "buttons":
        home_button()
        # Commit pending log right here, if all sites are up-to-date
        if is_distributed() and global_replication_state() == "clean":
            log_commit_pending()

        if config.may("wato.activate") and (
                (not is_distributed() and log_exists("pending"))
            or (is_distributed() and global_replication_state() == "dirty")):
            html.context_button(_("Activate Changes!"),
                html.makeactionuri([("_action", "activate")]),
                             "apply", True, id="act_changes_button")
            if get_last_wato_snapshot_file():
                html.context_button(_("Discard Changes!"),
                    html.makeactionuri([("_action", "discard")]),
                                 "discard", id="discard_changes_button")

        if is_distributed():
            html.context_button(_("Site Configuration"), make_link([("mode", "sites")]), "sites")

        if config.may("wato.auditlog"):
            html.context_button(_("Audit Log"), make_link([("mode", "auditlog")]), "auditlog")

    elif phase == "action":
        action = html.var("_action")
        if action == "activate":
            # Let host validators do their work
            defective_hosts = validate_all_hosts([], force_all = True)
            if defective_hosts:
                raise MKUserError(None, _("You cannot activate changes while some hosts have "
                  "an invalid configuration: ") + ", ".join(
                    [ '<a href="%s">%s</a>' % (make_link([("mode", "edithost"), ("host", hn)]), hn)
                      for hn in defective_hosts.keys() ]))

        # If there are changes by other users, we need a confirmation
        transaction_already_checked = False
        changes = foreign_changes()
        if changes:
            table = "<table class=foreignchanges>"
            for user_id, count in changes.items():
                table += '<tr><td>%s: </td><td>%d %s</td></tr>' % \
                   (config.alias_of_user(user_id), count, _("changes"))
            table += '</table>'

            if action == "activate":
                title = _("Confirm activating foreign changes")
                text  = _("There are some changes made by your colleagues that you will "
                          "activate if you proceed:")
            else:
                title = _("Confirm discarding foreign changes")
                text  = _("There are some changes made by your colleagues that you will "
                          "discard if you proceed:")

            c = wato_confirm(title,
              '<img class=foreignchanges src="images/icon_foreign_changes.png">' + text + table +
              _("Do you really want to proceed?"))
            if c == False:
                return ""
            elif not c:
                return None
            transaction_already_checked = True

        if changes and not config.may("wato.activateforeign"):
            raise MKAuthException(_("Sorry, you are not allowed to activate "
                                    "changes of other users."))

        if action == "discard":
            # Now remove all currently pending changes by simply restoring the last automatically
            # taken snapshot. Then activate the configuration. This should revert all pending changes.
            file_to_restore = get_last_wato_snapshot_file()
            if not file_to_restore:
                raise MKUserError(None, _('There is no WATO snapshot to be restored.'))
            log_pending(LOCALRESTART, None, "changes-discarded",
                 _("Discarded pending changes (Restored %s)") % html.attrencode(file_to_restore))
            extract_snapshot(file_to_restore)
            activate_changes()
            log_commit_pending()
            return None, _("Successfully discarded all pending changes.")

        # Give hooks chance to do some pre-activation things (and maybe stop
        # the activation)
        try:
            call_hook_pre_distribute_changes()
        except Exception, e:
            if config.debug:
                raise
            else:
                raise MKUserError(None, "<h1>%s</h1>%s" % (_("Cannot activate changes"), e))

        sitestatus_do_async_replication = False # see below
        if html.has_var("_siteaction"):
            config.need_permission("wato.activate")
            site_id = html.var("_site")
            action = html.var("_siteaction")
            if transaction_already_checked or html.check_transaction():
                try:
                    # If the site has no pending changes but just needs restart,
                    # the button text is just "Restart". We do a sync anyway. This
                    # can be optimized in future but is the save way for now.
                    site = config.site(site_id)
                    if action in [ "sync", "sync_restart" ]:
                        response = synchronize_site(site, restart = action == "sync_restart")
                    else:
                        try:
                            restart_site(site)
                            response = True
                        except Exception, e:
                            response = str(e)

                    if response == True:
                        return
                    else:
                        raise MKUserError(None, _("Error on remote access to site: %s") % response)

                except MKAutomationException, e:
                    raise MKUserError(None, _("Remote command on site %s failed: <pre>%s</pre>") % (site_id, e))
                except Exception, e:
                    if config.debug:
                        raise
                    raise MKUserError(None, _("Remote command on site %s failed: <pre>%s</pre>") % (site_id, e))

        elif transaction_already_checked or html.check_transaction():
            config.need_permission("wato.activate")
            create_snapshot({"comment": "Activated changes by %s" % config.user_id})

            # Do nothing here, but let site status table be shown in a mode
            # were in each site that is not up-to-date an asynchronus AJAX
            # job is being startet that updates that site
            sitestatus_do_async_replication = True

    else: # phase: regular page rendering
        changes_activated = False

        if is_distributed():
            # Distributed WATO: Show replication state of each site

            html.write("<h3>%s</h3>" % _("Distributed WATO - Replication Status"))
            repstatus = load_replication_status()
            sites = [(name, config.site(name)) for name in config.sitenames() ]
            sort_sites(sites)
            html.write("<table class=data>")
            html.write("<tr class=dualheader>")
            html.write("<th rowspan=2>%s</th>" % _("ID") +
                       "<th rowspan=2>%s</th>" % _("Alias"))
            html.write("<th colspan=6>%s</th>" % _("Livestatus"))
            html.write("<th colspan=%d>%s</th>" %
                         (sitestatus_do_async_replication and 3 or 6, _("Replication")))
            html.write("<tr>" +
                       "<th>%s</th>" % _("Status") +
                       "<th>%s</th>" % _("Version") +
                       "<th>%s</th>" % _("Core") +
                       "<th>%s</th>" % _("Ho.") +
                       "<th>%s</th>" % _("Sv.") +
                       "<th>%s</th>" % _("Uptime") +
                       "<th>%s</th>" % _("Multisite URL") +
                       "<th>%s</th>" % _("Type"))
            if sitestatus_do_async_replication:
                html.write("<th>%s</th>" % _("Replication result"))
            else:
                html.write("<th>%s</th>" % _("State") +
                           "<th>%s</th>" % _("Actions") +
                           "<th>%s</th>" % _("Last result"))
            html.write("</tr>")

            odd = "odd"
            num_replsites = 0 # for detecting end of bulk replication
            for site_id, site in sites:
                is_local = site_is_local(site_id)

                if not is_local and not site.get("replication"):
                    continue

                if site.get("disabled"):
                    ss = {}
                    status = "disabled"
                else:
                    ss = html.site_status.get(site_id, {})
                    status = ss.get("state", "unknown")

                srs = repstatus.get(site_id, {})

                # Make row red, if site status is not online
                html.write('<tr class="data %s0">' % odd)
                odd = odd == "odd" and "even" or "odd"

                # ID & Alias
                html.write("<td><a href='%s'>%s</a></td>" %
                   (make_link([("mode", "edit_site"), ("edit", site_id)]), site_id))
                html.write("<td>%s</td>" % site.get("alias", ""))

                # Livestatus
                html.write('<td><img src="images/button_sitestatus_%s_lo.png"></td>' % (status))

                # Livestatus-Version
                html.write('<td>%s</td>' % ss.get("livestatus_version", ""))

                # Core-Version
                html.write('<td>%s</td>' % ss.get("program_version", ""))

                # Hosts/services
                html.write('<td class=number><a href="view.py?view_name=sitehosts&site=%s">%s</a></td>' %
                  (site_id, ss.get("num_hosts", "")))
                html.write('<td class=number><a href="view.py?view_name=sitesvcs&site=%s">%s</a></td>' %
                  (site_id, ss.get("num_services", "")))

                # Uptime / Last restart
                if "program_start" in ss:
                    age_text = html.age_text(time.time() - ss["program_start"])
                else:
                    age_text = ""
                html.write('<td class=number>%s</td>' % age_text)

                # Multisite-URL
                html.write("<td>%s</td>" % (not is_local
                   and "<a target=\"_blank\" href='%s'>%s</a>" % tuple([site.get("multisiteurl")]*2) or ""))

                # Type
                sitetype = ''
                if is_local:
                    sitetype = _("local")
                elif site["replication"] == "slave":
                    sitetype = _("Slave")
                html.write("<td>%s</td>" % sitetype)

                need_restart = srs.get("need_restart")
                need_sync    = srs.get("need_sync") and not site_is_local(site_id)
                uptodate = not (need_restart or need_sync)

                # Start asynchronous replication
                if sitestatus_do_async_replication:
                    html.write("<td class=repprogress>")
                    # Do only include sites that are known to be up
                    if not site_is_local(site_id) and not "secret" in site:
                        html.write("<b>%s</b>" % _("Not logged in."))
                    else:
                        html.write('<div id="repstate_%s">%s</div>' %
                                (site_id, uptodate and _("nothing to do") or ""))
                        if not uptodate:
                            if need_restart and need_sync:
                                what = "sync+restart"
                            elif need_restart:
                                what = "restart"
                            else:
                                what = "sync"
                            estimated_duration = srs.get("times", {}).get(what, 2.0)
                            html.javascript("wato_do_replication('%s', %d);" %
                              (site_id, int(estimated_duration * 1000.0)))
                            num_replsites += 1
                    html.write("</td>")
                else:
                    # State
                    html.write("<td class=buttons>")
                    if srs.get("need_sync") and not site_is_local(site_id):
                        html.write('<img class=icon title="%s" src="images/icon_need_replicate.png">' %
                            _("This site is not update and needs a replication."))
                    if srs.get("need_restart"):
                        html.write('<img class=icon title="%s" src="images/icon_need_restart.png">' %
                            _("This site needs a restart for activating the changes."))
                    if uptodate:
                        html.write('<img class=icon title="%s" src="images/icon_siteuptodate.png">' %
                            _("This site is up-to-date."))
                    html.write("</td>")

                    # Actions
                    html.write("<td class=buttons>")
                    sync_url = make_action_link([("mode", "changelog"),
                            ("_site", site_id), ("_siteaction", "sync")])
                    restart_url = make_action_link([("mode", "changelog"),
                            ("_site", site_id), ("_siteaction", "restart")])
                    sync_restart_url = make_action_link([("mode", "changelog"),
                            ("_site", site_id), ("_siteaction", "sync_restart")])
                    if not site_is_local(site_id) and "secret" not in site:
                        html.write("<b>%s</b>" % _("Not logged in."))
                    elif not uptodate:
                        if not site_is_local(site_id):
                            if srs.get("need_sync"):
                                html.buttonlink(sync_url, _("Sync"))
                                if srs.get("need_restart"):
                                    html.buttonlink(sync_restart_url, _("Sync & Restart"))
                            else:
                                html.buttonlink(restart_url, _("Restart"))
                        else:
                            html.buttonlink(restart_url, _("Restart"))
                    html.write("</td>")

                    # Last result
                    result = srs.get("result", "")
                    if len(result) > 20:
                        result = html.strip_tags(result)
                        result = '<span title="%s">%s...</span>' % \
                            (html.attrencode(result), result[:20])
                    html.write("<td>%s</td>" % result)

                html.write("</tr>")
            html.write("</table>")
            # The Javascript world needs to know, how many asynchronous
            # replication jobs it should wait to be finished.
            if sitestatus_do_async_replication and num_replsites > 0:
                html.javascript("var num_replsites = %d;\n" % num_replsites)

        elif sitestatus_do_async_replication:
            # Single site setup
            if cmc_rush_ahead_activation():
                html.message(_("All changes have been activated."))
                changes_activated = True
            else:
                # Is rendered on the page after hitting the "activate" button
                # Renders the html to show the progress and starts the sync via javascript
                html.write("<table class=data>")
                html.write("<tr><th class=left>%s</th><th>%s</th></tr>" % (_('Progress'), _('Status')))
                html.write('<tr class="data odd0"><td class=repprogress><div id="repstate_local"></div></td>')
                html.write('<td id="repmsg_local"><i>%s</i></td></tr></table>' % _('activating...'))

                srs = load_replication_status().get(None, {})
                estimated_duration = srs.get("times", {}).get('act', 2.0)
                html.javascript("wato_do_activation(%d);" %
                  (int(estimated_duration * 1000.0)))

        sitestatus_do_async_replication = None # could survive in global context!

        pending = parse_audit_log("pending")
        if len(pending) == 0:
            if not changes_activated:
                html.write("<div class=info>" + _("There are no pending changes.") + "</div>")
        else:
            html.write('<div id=pending_changes>')
            render_audit_log(pending, "pending", hilite_others=True)
            html.write('</div>')

def get_last_wato_snapshot_file():
    for snapshot_file in get_snapshots():
        status = get_snapshot_status(snapshot_file)
        if status['type'] == 'automatic' and not status['broken']:
            return snapshot_file

# Determine if other users have made pending changes
def foreign_changes():
    changes = {}
    for t, linkinfo, user, action, text in parse_audit_log("pending"):
        if user != '-' and user != config.user_id:
            changes.setdefault(user, 0)
            changes[user] += 1
    return changes


def log_entry(linkinfo, action, message, logfilename, user_id = None):
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

    if user_id == None:
        user_id = config.user_id
    elif user_id == '':
        user_id = '-'

    log_file = log_dir + logfilename
    make_nagios_directory(log_dir)
    f = create_user_file(log_file, "ab")
    f.write("%d %s %s %s %s\n" % (int(time.time()), link, user_id, action, message))


def log_audit(linkinfo, what, message, user_id = None):
    if config.wato_use_git:
        g_git_messages.append(message)
    log_entry(linkinfo, what, message, "audit.log", user_id)

# status is one of:
# SYNC        -> Only sync neccessary
# RESTART     -> Restart and sync neccessary
# SYNCRESTART -> Do sync and restart
# AFFECTED    -> affected sites are already marked for sync+restart
#                by mark_affected_sites_dirty().
# LOCALRESTART-> Called after inventory. In distributed mode, affected
#                sites have already been marked for restart. Do nothing here.
#                In non-distributed mode mark for restart
def log_pending(status, linkinfo, what, message, user_id = None):
    log_audit(linkinfo, what, message, user_id)
    need_sidebar_reload()

    # On each change to the Check_MK configuration mark the agents to be rebuild
    if 'need_to_bake_agents' in globals():
        need_to_bake_agents()

    if not is_distributed():
        if status != SYNC:
            log_entry(linkinfo, what, message, "pending.log", user_id)
        cmc_rush_ahead()


    # Currently we add the pending to each site, regardless if
    # the site is really affected. This needs to be optimized
    # in future.
    else:
        log_entry(linkinfo, what, message, "pending.log", user_id)
        for siteid, site in config.sites.items():

            changes = {}

            # Local site can never have pending changes to be synced
            if site_is_local(siteid):
                if status in [ RESTART, SYNCRESTART ]:
                    changes["need_restart"] = True
            else:
                if status in [ SYNC, SYNCRESTART ]:
                    changes["need_sync"] = True
                if status in [ RESTART, SYNCRESTART ]:
                    changes["need_restart"] = True
            update_replication_status(siteid, changes)

            # Make sure that a new snapshot for syncing will be created
            # when times comes to syncing
            remove_sync_snapshot(siteid)

def cmc_rush_ahead():
    if defaults.omd_root:
        socket_path = defaults.omd_root + "/tmp/run/cmcrush"
        if os.path.exists(socket_path):
            try:
                changeid = str(random.randint(1, 100000000000000000))
                file(log_dir + "changeid", "w").write(changeid + "\n")
                socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) \
                          .sendto(changeid, socket_path)
            except:
                if config.debug:
                    raise


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
    c = wato_confirm(_("Confirm deletion of audit log"),
                     _("Do you really want to clear the audit log?"))
    if c:
        clear_audit_log()
        return None, _("Cleared audit log.")
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

def fmt_bytes(num):
    for x in ['Bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            if x == "Bytes":
                return "%d %s" % (num, x)
            else:
                return "%3.1f %s" % (num, x)
        num /= 1024.0

def paged_log(log):
    start = int(html.var('start', 0))
    if not start:
        start = int(time.time())

    while True:
        log_today, times = paged_log_from(log, start)
        if len(log) == 0 or len(log_today) > 0:
            return log_today, times
        else: # No entries today, but log not empty -> go back in time
            start -= 24 * 3600


def paged_log_from(log, start):
    start_time, end_time = get_timerange(start)
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

    if next_log_time is not None:
        html.icon_button(html.makeuri([('start', get_timerange(int(time.time()))[0])]),
                        _("Most recent events"), "start")
        html.icon_button(html.makeuri([('start', next_log_time)]),
                        '%s: %s' % (_("Newer events"), fmt_date(next_log_time)),
                        "back")
    else:
        html.empty_icon_button()
        html.empty_icon_button()

    if previous_log_time is not None:
        html.icon_button(html.makeuri([('start', previous_log_time)]),
                        '%s: %s' % (_("Older events"), fmt_date(previous_log_time)),
                        "forth")
    else:
        html.empty_icon_button()
    html.write('</div>')


def render_audit_log(log, what, with_filename = False, hilite_others=False):
    htmlcode = ''
    if what == 'audit':
        log, times = paged_log(log)
        empty_msg = _("The log is empty. No host has been created or changed yet.")
    elif what == 'pending':
        empty_msg = _("No pending changes, monitoring server is up to date.")

    if len(log) == 0:
        html.write("<div class=info>%s</div>" % empty_msg)
        return

    elif what == 'audit':
        htmlcode += "<h3>" + _("Audit log for %s") % fmt_date(times[0]) + "</h3>"

    elif what == 'pending':
        if is_distributed():
            htmlcode += "<h3>" + _("Changes that are not activated on all sites:") + "</h3>"
        else:
            htmlcode += "<h3>" + _("Changes that are not yet activated:") + "</h3>"

    if what == 'audit':
        display_paged(times)

    htmlcode += '<table class="data wato auditlog %s">' % what
    even = "even"
    for t, linkinfo, user, action, text in log:
        even = even == "even" and "odd" or "even"
        hilite = hilite_others and user != '-' and config.user_id != user
        htmlcode += '<tr class="data %s%d">' % (even, hilite and 2 or 0)
        htmlcode += '<td class=nobreak>%s</td>' % render_linkinfo(linkinfo)
        htmlcode += '<td class=nobreak>%s</td>' % fmt_date(float(t))
        htmlcode += '<td class=nobreak>%s</td>' % fmt_time(float(t))
        htmlcode += '<td class=nobreak>'
        user = user == '-' and ('<i>%s</i>' % _('internal')) or user
        if hilite:
            htmlcode += '<img class=icon src="images/icon_foreign_changes.png" title="%s">' \
                     % _("This change has been made by another user")
        htmlcode += user + '</td>'

        htmlcode += '</td><td width="100%%">%s</td></tr>\n' % text
    htmlcode += "</table>"

    if what == 'audit':
        html.write(htmlcode)
        display_paged(times)
    else:
        html.write(htmlcode)

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

#.
#   .--Automation----------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

def check_mk_automation(siteid, command, args=[], indata=""):
    if not siteid or site_is_local(siteid):
        return check_mk_local_automation(command, args, indata)
    else:
        return check_mk_remote_automation(siteid, command, args, indata)


def check_mk_local_automation(command, args=[], indata=""):
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
                    "needed Check_MK/Nagios files.<br>Please ensure you have set-up "
                    "the sudo environment correctly. e.g. proceed as follows:</p>\n"
                    "<ol><li>install sudo package</li>\n"
                    "<li>Append the following to the <tt>/etc/sudoers</tt> file:\n"
                    "<pre># Needed for WATO - the Check_MK Web Administration Tool\n"
                    "Defaults:%s !requiretty\n"
                    "%s\n"
                    "</pre></li>\n"
                    "<li>Retry this operation</li></ol>\n" %
                    (html.apache_user(), sudoline))

    if command in [ 'restart', 'reload' ]:
        try:
            call_hook_pre_activate_changes()
        except Exception, e:
            if config.debug:
                raise
            html.show_error(_("<h1>Cannot activate changes</h1>%s") % e)
            return

    try:
        # This debug output makes problems when doing bulk inventory, because
        # it garbles the non-HTML response output
        # if config.debug:
        #     html.write("<div class=message>Running <tt>%s</tt></div>\n" % " ".join(cmd))
        p = subprocess.Popen(cmd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
    except Exception, e:
        if commandargs[0] == 'sudo':
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s<br><br>%s" % (commandargs[0], e, sudo_msg))
        else:
            raise MKGeneralException("Cannot execute <tt>%s</tt>: %s" % (commandargs[0], e))
    p.stdin.write(repr(indata))
    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    if exitcode != 0:
        if config.debug:
            raise MKGeneralException("Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>%s" %
                  (" ".join(cmd), exitcode, hilite_errors(outdata), outdata.lstrip().startswith('sudo:') and sudo_msg or ''))
        else:
            raise MKGeneralException(hilite_errors(outdata))


    # On successful "restart" command execute the activate changes hook
    if command in [ 'restart', 'reload' ]:
        call_hook_activate_changes()

    try:
        return eval(outdata)
    except Exception, e:
        raise MKGeneralException("Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
                      (" ".join(cmd), e, outdata))


def hilite_errors(outdata):
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


#.
#   .--Progress------------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

# success_stats: Fields from the stats list to use for checking if something has been found
# fail_stats:    Fields from the stats list to used to count failed elements
def interactive_progress(items, title, stats, finishvars, timewait, success_stats = [], termvars = [], fail_stats = []):
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
    json_items    = '[ %s ]' % ',\n'.join([ "'" + h + "'" for h in items ])
    success_stats = '[ %s ]' % ','.join(map(str, success_stats))
    fail_stats    = '[ %s ]' % ','.join(map(str, fail_stats))
    # Remove all sel_* variables. We do not need them for our ajax-calls.
    # They are just needed for the Abort/Finish links. Those must be converted
    # to POST.
    base_url = html.makeuri([], remove_prefix = "sel")
    finish_url = make_link([("mode", "folder")] + finishvars)
    term_url = make_link([("mode", "folder")] + termvars)

    # Reserve a certain amount of transids for the progress scheduler
    # Each json item requires one transid. Additionally, each "Retry failed hosts" eats
    # up another one. We reserve 20 additional transids for the retry function
    # Note: The "retry option" ignores the bulk size
    transids = []
    for i in range(len(items) + 20):
        transids.append(html.fresh_transid())
    json_transids = '[ %s ]' % ',\n'.join([ "'" + h + "'" for h in transids])
    html.javascript(('progress_scheduler("%s", "%s", 50, %s, %s, "%s", %s, %s, "%s", "' + _("FINISHED.") + '");') %
                     (html.var('mode'), base_url, json_items, json_transids, finish_url,
                      success_stats, fail_stats, term_url))


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Attributes of hosts are based on objects and are extendable via      |
#   | WATO plugins.                                                        |
#   '----------------------------------------------------------------------'

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

    # Wether or not this attribute can be edited after creation
    # of the object
    def editable(self):
        return self._editable

    # Wether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Return information about the user roles we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_roles is set by declare_host_attribute().
    def depends_on_roles(self):
        try:
            return self._depends_on_roles
        except:
            return []

    # Return information about the host tags we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_tags is set by declare_host_attribute().
    def depends_on_tags(self):
        try:
            return self._depends_on_tags
        except:
            return []

    # Render HTML input fields displaying the value and
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, value):
        pass

    # Create value from HTML variables.
    def from_html_vars(self):
        return None


    # Check whether this attribute needs to be validated at all
    # Attributes might be permanently hidden (show_in_form = False)
    # or dynamically hidden by the depends_on_tags, editable features
    def needs_validation(self):
        if not self._show_in_form:
            return False
        return html.var('attr_display_%s' % self._name, "1") == "1"

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

    # Host tags to set for this host
    def get_tag_list(self, value):
        return []


# A simple text attribute. It is stored in
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self, name, title, help = None, default_value="", mandatory=False, allow_empty=True, size=25):
        Attribute.__init__(self, name, title, help, default_value)
        self._mandatory = mandatory
        self._allow_empty = allow_empty
        self._size = size

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
        html.text_input("attr_" + self.name(), value, size = self._size)

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
        if not self._allow_empty and value.strip() == "":
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
            return value
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
        # Definition is either triple or 4-tuple (with
        # dependency definition)
        tag_id, title, self._taglist = tag_definition
        name = "tag_" + tag_id
        if len(self._taglist) == 1:
            def_value = None
        else:
            def_value = self._taglist[0][0]
        Attribute.__init__(self, name, title, "", def_value)

    def paint(self, value, hostname):
        # Localize the titles. To make the strings available in the scanned localization
        # files the _() function must also be placed in the configuration files
        # But don't localize empty strings - This empty string is connected to the header
        # of the .mo file
        if len(self._taglist) == 1:
            title = self._taglist[0][1]
            if title:
                title = _(title)
            if value:
                return "", title
            else:
                return "", "%s %s" % (_("not"), title)
        for entry in self._taglist:
            if value == entry[0]:
                return "", entry[1] and _(entry[1]) or ''
        return "", "" # Should never happen, at least one entry should match
                      # But case could occur if tags definitions have been changed.

    def render_input(self, value):
        varname = "attr_" + self.name()
        if value == None:
            value = html.var(varname,"") # "" is important for tag groups with an empty tag entry

        # Tag groups with just one entry are being displayed
        # as checkboxes
        choices = []
        for e in self._taglist:
            tagvalue = e[0]
            if not tagvalue: # convert "None" to ""
                tagvalue = ""
            if len(e) >= 3: # have secondary tags
                secondary_tags = e[2]
            else:
                secondary_tags = []
            choices.append(("|".join([ tagvalue ] + secondary_tags), e[1] and _u(_(e[1])) or ''))
            if value != "" and value == tagvalue and secondary_tags:
                value = value + "|" + "|".join(secondary_tags)

        if len(choices) == 1:
            html.checkbox(varname, value != "", cssclass = '', onclick='wato_fix_visibility();',
                          add_attr = ["tags=%s"%choices[0][0]], label = choices[0][1])
        else:
            html.select(varname, choices, value, onchange='wato_fix_visibility();')

    def from_html_vars(self):
        varname = "attr_" + self.name()
        if len(self._taglist) == 1:
            if html.get_checkbox(varname):
                return self._taglist[0][0]
            else:
                return None
        else:
            # strip of secondary tags
            value = html.var(varname).split("|")[0]
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


# An attribute using the generic ValueSpec mechanism
class ValueSpecAttribute(Attribute):
    def __init__(self, name, vs):
        Attribute.__init__(self, name)
        self._valuespec = vs

    def title(self):
        return self._valuespec.title()

    def help(self):
        return self._valuespec.help()

    def default_value(self):
        return self._valuespec.default_value()

    def paint(self, value, hostname):
        return "", \
            self._valuespec.value_to_text(value)

    def render_input(self, value):
        self._valuespec.render_input(self._name, value)

    def from_html_vars(self):
        return self._valuespec.from_html_vars(self._name)

    def validate_input(self):
        value = self.from_html_vars()
        self._valuespec.validate_value(value, self._name)


# Attribute for selecting the name of an other host
class HostSelectionAttribute(Attribute):
    def __init__(self, name, title, help=None, hostfilter = lambda h: True):
        Attribute.__init__(self, name, title, help)
        self._hostfilter = hostfilter

    def paint(self, value, hostname):
        return "", (value and value or "")

    def render_input(self, value):
        hosts = get_all_hosts().items()
        hosts.sort()
        selections = [("", _("-- not connected --"))]
        for n, h in hosts:
            if self._hostfilter(h):
                selections.append((n, n))
        if len(selections) == 1:
            html.write(_("There are no possible hosts."))
        else:
            html.select(self._name, selections, value)

    def from_html_vars(self):
        hostname = html.var(self._name).strip()
        if not hostname:
            return None
        folder = find_host(hostname)
        if not folder:
            raise MKUserError(self._name, _("This host is not configured."))
        host = get_host(folder, hostname)
        if not self._hostfilter(host):
            raise MKUserError(self._name, _("This host is not possible."))
        return hostname and hostname or None


# Convert old tuple representation to new dict representation of
# folder's group settings
def convert_cgroups_from_tuple(value):
    if type(value) == dict:
        return value
    else:
        return {
            "groups"        : value[1],
            "recurse_perms" : False,
            "use"           : value[0],
            "recurse_use"   : False,
        }

# Attribute needed for folder permissions
class ContactGroupsAttribute(Attribute):
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self):
        url = "wato.py?mode=rulesets&group=grouping"
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
        value = convert_cgroups_from_tuple(value)

        texts = []
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1]['alias'], b[1]['alias']))
        for name, cgroup in items:
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append('<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' % (name, display_name))
        result = ", ".join(texts)
        if texts and value["use"]:
            result += "<span title='%s'><b>*</b></span>" % \
                  _("These contact groups are also used in the monitoring configuration.")
        return "", result

    def render_input(self, value):
        value = convert_cgroups_from_tuple(value)

        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = not not html.var("host")

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp = lambda a,b: cmp(a[1], b[1]))
        for name, group in items:
            html.checkbox(self._name + "_n_" + name, name in value["groups"])
            html.write(' <a href="%s">%s</a><br>' % (make_link([("mode", "edit_contact_group"), ("edit", name)]), group['alias'] and group['alias'] or name))
        html.write("<hr>")
        if is_host:
            html.checkbox(self._name + "_use", value["use"], label = _("Add these contact groups to host"))
        else:
            html.checkbox(self._name + "_recurse_perms", value["recurse_perms"], label = _("Give these groups also <b>permission on all subfolders</b>"))
            html.write("<hr>")
            html.checkbox(self._name + "_use", value["use"], label = _("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.write("<br>")
            html.checkbox(self._name + "_recurse_use", value["recurse_use"], label = _("Add these groups as <b>contacts in all subfolders</b>"))

    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)

        self._contactgroups = userdb.load_group_information().get("contact", {})

    def from_html_vars(self):
        cgs = []
        self.load_data()
        for name in self._contactgroups:
            if html.get_checkbox(self._name + "_n_" + name):
                cgs.append(name)
        return {
            "groups"        : cgs,
            "recurse_perms" : html.get_checkbox(self._name + "_recurse_perms"),
            "use"           : html.get_checkbox(self._name + "_use"),
            "recurse_use"   : html.get_checkbox(self._name + "_recurse_use"),
        }

    def filter_matches(self, crit, value, hostname):
        value = convert_cgroups_from_tuple(value)
        for c in crit[1]:
            if c in value["groups"]:
                return True
        return False


# Declare an attribute for each host tag configured in multisite.mk
# Also make sure that the tags are reconfigured as soon as the
# configuration of the tags has changed.
def declare_host_tag_attributes():
    global configured_host_tags
    global host_attributes

    if configured_host_tags != config.wato_host_tags:
        # Remove host tag attributes from list, if existing
        host_attributes = [ (attr, topic)
               for (attr, topic)
               in host_attributes
               if not attr.name().startswith("tag_") ]

        # Also remove those attributes from the speed-up dictionary host_attribute
        for attr in host_attribute.values():
            if attr.name().startswith("tag_"):
                del host_attribute[attr.name()]

        for topic, grouped_tags in group_hosttags_by_topic(config.wato_host_tags):
            for entry in grouped_tags:
                # if the entry has o fourth component, then its
                # the tag dependency defintion.
                depends_on_tags = []
                depends_on_roles = []
                attr_editable = True
                if len(entry) >= 6:
                    attr_editable = entry[5]
                if len(entry) >= 5:
                    depends_on_roles = entry[4]
                if len(entry) >= 4:
                    depends_on_tags = entry[3]

                if not topic:
                    topic = _('Host tags')

                declare_host_attribute(
                    HostTagAttribute(entry[:3]),
                        show_in_table = False,
                        show_in_folder = True,
                        editable = attr_editable,
                        depends_on_tags = depends_on_tags,
                        depends_on_roles = depends_on_roles,
                        topic = topic)

        configured_host_tags = config.wato_host_tags

def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)



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
def declare_host_attribute(a, show_in_table = True, show_in_folder = True,
       topic = None, show_in_form = True, depends_on_tags = [], depends_on_roles = [], editable = True):
    host_attributes.append((a, topic))
    host_attribute[a.name()] = a
    a._show_in_table    = show_in_table
    a._show_in_folder   = show_in_folder
    a._show_in_form     = show_in_form
    a._depends_on_tags  = depends_on_tags
    a._depends_on_roles = depends_on_roles
    a._editable         = editable


def undeclare_host_attribute(attrname):
    if attrname in host_attribute:
        attr = host_attribute[attrname]
        del host_attribute[attrname]
        global host_attributes
        host_attributes = [ ha for ha in host_attributes if ha[0] != attr ]


# Read attributes from HTML variables
def collect_attributes(do_validate = True):
    host = {}
    for attr, topic in host_attributes:
        attrname = attr.name()
        if not html.var("_change_%s" % attrname, False):
            continue

        if do_validate and attr.needs_validation():
            attr.validate_input()

        host[attrname] = attr.from_html_vars()
    return host

def have_folder_attributes():
    for attr, topic in host_attributes:
        if attr.show_in_folder():
            return True
    return False

# Show HTML form for editing attributes.
#
# new: Boolean flag if this is a creation step or editing
# for_what can be:
#   "host"   -> normal host edit dialog
#   "folder" -> properies of folder or file
#   "search" -> search dialog
#   "bulk"   -> bulk change
# parent: The parent folder of the objects to configure
# myself: For mode "folder" the folder itself or None, if we edit a new folder
#         This is needed for handling mandatory attributes.
def configure_attributes(new, hosts, for_what, parent, myself=None, without_attributes = []):
    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    # Make sure, that the topics "Basic settings" and host tags
    # are always show first.
    topics = [None]
    if len(config.wato_host_tags):
        topics.append(_("Host tags"))

    # The remaining topics are shown in the order of the
    # appearance of the attribute declarations:
    for attr, topic in host_attributes:
        if topic not in topics and attr.show_in_form():
            topics.append(topic)

    # Collect dependency mapping for attributes (attributes that are only
    # visible, if certain host tags are set).
    dependency_mapping_tags = {}
    dependency_mapping_roles = {}
    inherited_tags     = {}

    volatile_topics = []
    hide_attributes = []
    for topic in topics:
        topic_is_volatile = True # assume topic is sometimes hidden due to dependencies
        if len(topics) > 1:
            if topic == None:
                title = _("Basic settings")
            else:
                title = _u(topic)

            if topic == _("Host tags"):
                topic_id = "wato_host_tags"
            else:
                topic_id = None
            forms.header(title, isopen = topic == topics[0], table_id = topic_id)

        for attr, atopic in host_attributes:
            if atopic != topic:
                continue
            attrname = attr.name()
            if attrname in without_attributes:
                continue # e.g. needed to skip ipaddress in CSV-Import

            # Hide invisible attributes
            hide_attribute = False
            if for_what in [ "host", "bulk" ] and not attr.show_in_form():
                hide_attribute = True
            elif (for_what == "folder") and not attr.show_in_folder():
                hide_attribute = True

            # Determine visibility information if this attribute is not always hidden
            if not hide_attribute:
                depends_on_tags = attr.depends_on_tags()
                depends_on_roles = attr.depends_on_roles()
                # Add host tag dependencies, but only in host mode. In other
                # modes we always need to show all attributes.
                if for_what == "host" and depends_on_tags:
                    dependency_mapping_tags[attrname] = depends_on_tags

                if depends_on_roles:
                    dependency_mapping_roles[attrname] = depends_on_roles

                if not depends_on_tags and not depends_on_roles:
                    # One attribute is always shown -> topic is always visible
                    topic_is_volatile = False
            else:
                hide_attributes.append(attr.name())

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
                    if topic == _("Host tags"):
                        inherited_tags["attr_%s" % attrname] = '|'.join(attr.get_tag_list(inherited_value))
                    break

                container = container.get(".parent")
                what = "folder"

            if not container: # We are the root folder - we inherit the default values
                inherited_from = _("Default value")
                inherited_value = attr.default_value()
                # Also add the default values to the inherited values dict
                if topic == _("Host tags"):
                    inherited_tags["attr_%s" % attrname] = '|'.join(attr.get_tag_list(inherited_value))

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
            disabled = False

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

            if not new and not attr.editable():
                if active:
                    force_entry = True
                else:
                    disabled = True

            if (for_what == "host" and g_folder.get(".lock_hosts")) or (for_what == "folder" and g_folder.get(".lock")):
                checkbox_code = None
            elif force_entry:
                checkbox_code = '<input type=checkbox name="ignored_%s" CHECKED DISABLED>' % checkbox_name
                checkbox_code += '<input type=hidden name="%s" value="on">' % checkbox_name
            else:
                onclick = "wato_fix_visibility(); wato_toggle_attribute(this, '%s');" % attrname
                checkbox_code = '<input type=checkbox name="%s" %s %s onclick="%s">' % (
                    checkbox_name, active and "CHECKED" or "", disabled and "DISABLED" or "", onclick)

            forms.section(_u(attr.title()), checkbox=checkbox_code, id="attr_" + attrname)
            html.help(attr.help())

            if len(values) == 1:
                defvalue = values[0]
            else:
                defvalue = attr.default_value()

            if not new and not attr.editable():
                # In edit mode only display non editable values, don't show the
                # input fields
                html.write('<div id="attr_hidden_%s" style="display:none">' % attrname)
                attr.render_input(defvalue)
                html.write('</div>')

                html.write('<div class="inherited" id="attr_visible_%s">' % (attrname))

            else:
                # Now comes the input fields and the inherited / default values
                # as two DIV elements, one of which is visible at one time.

                # DIV with the input elements
                html.write('<div id="attr_entry_%s" style="%s">'
                  % (attrname, (not active) and "display: none" or ""))

                attr.render_input(defvalue)
                html.write("</div>")

                html.write('<div class="inherited" id="attr_default_%s" style="%s">'
                   % (attrname, active and "display: none" or ""))

            #
            # DIV with actual / inherited / default value
            #

            # in bulk mode we show inheritance only if *all* hosts inherit
            explanation = ""
            if for_what == "bulk":
                if num_haveit == 0:
                    explanation = " (" + inherited_from + ")"
                    value = inherited_value
                elif not unique:
                    explanation = _("This value differs between the selected hosts.")
                else:
                    value = values[0]

            elif for_what in [ "host", "folder" ]:
                if not new and not attr.editable() and active:
                    value = values[0]
                else:
                    explanation = " (" + inherited_from + ")"
                    value = inherited_value

            if for_what != "search" and not (for_what == "bulk" and not unique):
                tdclass, content = attr.paint(value, "")
                if not content:
                    content = _("empty")
                html.write("<b>" + _u(content) + "</b>")

            html.write(explanation)
            html.write("</div>")


        if len(topics) > 1:
            if topic_is_volatile:
                volatile_topics.append((topic or _("Basic settings")).encode('utf-8'))

    def dump_json(obj):
        return repr(obj).replace('None', 'null')

    forms.end()
    # Provide Javascript world with the tag dependency information
    # of all attributes.
    html.javascript("var inherited_tags = %s;\n"\
                    "var wato_check_attributes = %s;\n"\
                    "var wato_depends_on_tags = %s;\n"\
                    "var wato_depends_on_roles = %s;\n"\
                    "var volatile_topics = %s;\n"\
                    "var user_roles = %s;\n"\
                    "var hide_attributes = %s;\n"\
                    "wato_fix_visibility();\n" % (
                       dump_json(inherited_tags),
                       dump_json(list(set(dependency_mapping_tags.keys()+dependency_mapping_roles.keys()+hide_attributes))),
                       dump_json(dependency_mapping_tags),
                       dump_json(dependency_mapping_roles),
                       dump_json(volatile_topics),
                       dump_json(config.user_role_ids),
                       dump_json(hide_attributes)))


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


#.
#   .--Snapshots-----------------------------------------------------------.
#   |           ____                        _           _                  |
#   |          / ___| _ __   __ _ _ __  ___| |__   ___ | |_ ___            |
#   |          \___ \| '_ \ / _` | '_ \/ __| '_ \ / _ \| __/ __|           |
#   |           ___) | | | | (_| | |_) \__ \ | | | (_) | |_\__ \           |
#   |          |____/|_| |_|\__,_| .__/|___/_| |_|\___/ \__|___/           |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Mode for backup/restore/creation of snapshots                        |
#   '----------------------------------------------------------------------'

# Returns status information for snapshots or snapshots in progress
def get_snapshot_status(snapshot, validate_checksums = False):
    if type(snapshot) == tuple:
        name, file_stream = snapshot
    else:
        name = snapshot
        file_stream = None

    # Defaults of available keys
    status = {
        "name"            : "",
        "total_size"      : 0,
        "type"            : None,
        "files"           : {},
        "comment"         : "",
        "created_by"      : "",
        "broken"          : False,
        "progress_status" : "",
    }

    def access_snapshot(handler):
        if file_stream:
            file_stream.seek(0)
            return handler(file_stream)
        else:
            return handler(snapshot_dir + name)

    def check_size():
        if file_stream:
            file_stream.seek(0, os.SEEK_END)
            size = file_stream.tell()
        else:
            statinfo = os.stat(snapshot_dir + name)
            size = statinfo.st_size
        if size < 256:
            raise MKGeneralException(_("Invalid snapshot (too small)"))
        else:
            status["total_size"] = size

    def check_extension():
        # Check snapshot extension: tar or tar.gz
        if name.endswith(".tar.gz"):
            status["type"]    = "legacy"
            status["comment"] = _("Snapshot created with old version")
        elif not name.endswith(".tar"):
            raise MKGeneralException(_("Invalid snapshot (incorrect file extension)"))

    def check_content():
        status["files"] = access_snapshot(multitar.list_tar_content)

        if status.get("type") == "legacy":
            allowed_files = map(lambda x: "%s.tar" % x[1], backup_paths)
            for tarname in status["files"].keys():
                if tarname not in allowed_files:
                    raise MKGeneralException(_("Invalid snapshot (contains invalid tarfile %s)") % tarname)
        else: # new snapshots
            for entry in ["comment", "created_by", "type"]:
                if entry in status["files"]:
                    status[entry] = access_snapshot(lambda x: multitar.get_file_content(x, entry))
                else:
                    raise MKGeneralException(_("Invalid snapshot (missing file: %s)") % entry)

    def check_core():
        if not defaults.omd_root:
            return # Do not perform this check in non OMD environments
        cmk_tar = cStringIO.StringIO(access_snapshot(lambda x: multitar.get_file_content(x, 'check_mk.tar.gz')))
        files = multitar.list_tar_content(cmk_tar)
        using_cmc = os.path.exists(defaults.omd_root + '/etc/check_mk/conf.d/microcore.mk')
        snapshot_cmc = 'conf.d/microcore.mk' in files
        if using_cmc and not snapshot_cmc:
            raise MKGeneralException(_('You are currently using the Check_MK Micro Core, but this snapshot does not use the '
                                       'Check_MK Micro Core. If you need to migrate your data, you could consider changing '
                                       'the core, restoring the snapshot and changing the core back again.'))
        elif not using_cmc and snapshot_cmc:
            raise MKGeneralException(_('You are currently not using the Check_MK Micro Core, but this snapshot uses the '
                                       'Check_MK Micro Core. If you need to migrate your data, you could consider changing '
                                       'the core, restoring the snapshot and changing the core back again.'))

    def snapshot_secret():
        path = defaults.default_config_dir + '/snapshot.secret'
        try:
            return file(path).read()
        except IOError:
            return '' # validation will fail in this case

    def check_checksums():
        for f in status["files"].values():
            f['checksum'] = None

        # checksums field might contain three states:
        # a) None  - This is a legacy snapshot, no checksum file available
        # b) False - No or invalid checksums
        # c) True  - Checksums successfully validated
        if status['type'] == 'legacy':
            status['checksums'] = None
            return

        if 'checksums' not in status['files'].keys():
            status['checksums'] = False
            return

        # Extract all available checksums from the snapshot
        checksums_raw = access_snapshot(lambda x: multitar.get_file_content(x, 'checksums'))
        checksums = {}
        for l in checksums_raw.split('\n'):
            line = l.strip()
            if ' ' in line:
                parts = line.split(' ')
                if len(parts) == 3:
                    checksums[parts[0]] = (parts[1], parts[2])

        # now loop all known backup domains and check wheter or not they request
        # checksum validation, there is one available and it is valid
        status['checksums'] = True
        for domain_id, domain in backup_domains.items():
            filename = domain_id + '.tar.gz'
            if not domain.get('checksum', True) or filename not in status['files']:
                continue

            if filename not in checksums:
                continue

            checksum, signed = checksums[filename]

            # Get hashes of file in question
            subtar = access_snapshot(lambda x: multitar.get_file_content(x, filename))
            subtar_hash   = sha256(subtar).hexdigest()
            subtar_signed = sha256(subtar_hash + snapshot_secret()).hexdigest()

            status['files'][filename]['checksum'] = checksum == subtar_hash and signed == subtar_signed
            status['checksums'] &= status['files'][filename]['checksum']

    try:
        if len(name) > 35:
            status["name"] = "%s %s" % (name[14:24], name[25:33].replace("-",":"))
        else:
            status["name"] = name

        if not file_stream:
            # Check if the snapshot build is still in progress...
            path_status = "%s/workdir/%s/%s.status" % (snapshot_dir, name, name)
            path_pid    = "%s/workdir/%s/%s.pid"    % (snapshot_dir, name, name)

            # Check if this process is still running
            if os.path.exists(path_pid):
                if os.path.exists(path_pid) and not os.path.exists("/proc/%s" % open(path_pid).read()):
                    status["progress_status"] = _("ERROR: Snapshot progress no longer running!")
                    raise MKGeneralException(_("Error: The process responsible for creating the snapshot is no longer running!"))
                else:
                    status["progress_status"] = _("Snapshot build currently in progress")

            # Read snapshot status file (regularly updated by snapshot process)
            if os.path.exists(path_status):
                lines = file(path_status, "r").readlines()
                status["comment"] = lines[0].split(":", 1)[1]
                file_info = {}
                for filename in lines[1:]:
                    name, info = filename.split(":", 1)
                    text, size = info[:-1].split(":", 1)
                    file_info[name] = {"size" : saveint(size), "text": text}
                status["files"] = file_info
                return status

        # Snapshot exists and is finished - do some basic checks
        check_size()
        check_extension()
        check_content()
        check_core()

        if validate_checksums:
            check_checksums()

    except Exception, e:
        if config.debug:
            import traceback
            status["broken_text"] = traceback.format_exc()
            status["broken"]      = True
        else:
            status["broken_text"] = '%s' % e
            status["broken"]      = True
    return status

def mode_snapshot_detail(phase):
    snapshot_name = html.var("_snapshot_name")

    if ".." in snapshot_name or "/" in snapshot_name:
        raise MKUserError("_snapshot_name", _("Invalid snapshot requested"))
    if not os.path.exists(snapshot_dir + '/' + snapshot_name):
        raise MKUserError("_snapshot_name", _("The requested snapshot does not exist"))

    if phase not in ["buttons", "action"]:
        status = get_snapshot_status(snapshot_name, validate_checksums = True)

    if phase == "title":
        return _("Snapshot details of %s") % html.attrencode(status["name"])
    elif phase == "buttons":
        home_button()
        html.context_button(_("Back"), make_link([("mode", "snapshot")]), "back")
        return
    elif phase == "action":
        return

    other_content = []

    if status.get("broken"):
        html.add_user_error('broken', _  ('This snapshot is broken!'))
        html.add_user_error('broken_text', status.get("broken_text"))
        html.show_user_errors()

    html.begin_form("snapshot_details", method="POST")
    forms.header(_("Snapshot %s") % html.attrencode(snapshot_name))

    for entry in [ ("comment", _("Comment")), ("created_by", _("Created by")) ]:
        if status.get(entry[0]):
            forms.section(entry[1])
            html.write(status.get(entry[0]))

    forms.section(_("Content"))
    files = status["files"]
    if not files:
        html.write(_("Snapshot is empty!"))
    else:
        html.write("<table>")
        html.write("<tr><th align='left'>%s</th>"
                   "<th align='right'>%s</th>"
                   "<th>%s</th></tr>" % (_("Description"), _("Size"), _("Trusted")))

        domains        = []
        other_content  = []
        for filename, values in files.items():
            if filename in ["comment", "type", "created_by", "checksums"]:
                continue
            domain_key = filename[:-7]
            if domain_key in backup_domains.keys():
                verify_checksum = backup_domains.get('checksum', True) # is checksum check enabled here?
                domains.append((backup_domains[domain_key]["title"], verify_checksum, filename, values))
            else:
                other_content.append((_("Other"), filename, values))
        domains.sort()

        for (title, verify_checksum, filename, values) in domains:
            extra_info = ""
            if values.get("text"):
                extra_info = "%s - " % values["text"]
            html.write("<tr><td>%s%s</td>"  % (extra_info, title))
            html.write("<td align='right'>%s</td>" % fmt_bytes(values["size"]))

            html.write("<td>")
            if verify_checksum:
                if values.get('checksum') == True:
                    checksum_title = _('Checksum valid and signed')
                    checksum_icon  = ''
                elif values.get('checksum') == False:
                    checksum_title = _('Checksum invalid and not signed')
                    checksum_icon  = 'p'
                else:
                    checksum_title = _('Checksum not available')
                    checksum_icon  = 'n'
                html.icon(checksum_title, 'snapshot_%schecksum' % checksum_icon)
            html.write("</td>")

            html.write("</tr>")

        if other_content:
            html.write("<tr><td colspan=\"3\"><i>%s</i></td></tr>" % _("Other content"))
            for (title, filename, values) in other_content:
                html.write("<tr><td>%s</td>"  % html.attrencode(filename))
                html.write("<td align='right'>%s</td>" % fmt_bytes(values["size"]))
                html.write("<td></td>")
                html.write("</tr>")
        html.write("</table>")

    forms.end()

    if snapshot_name != "uploaded_snapshot":
        delete_url = make_action_link([("mode", "snapshot"), ("_delete_file", snapshot_name)])
        html.buttonlink(delete_url, _("Delete Snapshot"))
        download_url = make_action_link([("mode", "snapshot"), ("_download_file", snapshot_name)])
        html.buttonlink(download_url, _("Download Snapshot"))

    if not status.get("progress_status") and not status.get("broken"):
        restore_url = make_action_link([("mode", "snapshot"), ("_restore_snapshot", snapshot_name)])
        html.buttonlink(restore_url, _("Restore Snapshot"))

def get_snapshots():
    snapshots = []
    try:
        for f in os.listdir(snapshot_dir):
            if os.path.isfile(snapshot_dir + f):
                snapshots.append(f)
        snapshots.sort(reverse=True)
    except OSError:
        pass
    return snapshots

def extract_snapshot(snapshot_file):
    multitar.extract_from_file(snapshot_dir + snapshot_file, backup_domains)

def mode_snapshot(phase):
    if phase == "title":
        return _("Backup & Restore")
    elif phase == "buttons":
        home_button()
        changelog_button()
        html.context_button(_("Factory Reset"),
                make_action_link([("mode", "snapshot"),("_factory_reset","Yes")]), "factoryreset")
        return

    # Cleanup incompletely processed snapshot upload
    if os.path.exists(snapshot_dir) and not html.var("_restore_snapshot") \
       and os.path.exists("%s/uploaded_snapshot" % snapshot_dir):
        os.remove("%s/uploaded_snapshot" % snapshot_dir)

    snapshots = get_snapshots()

    # Generate valuespec for snapshot options
    # Sort domains by group
    domains_grouped = {}
    for domainname, data in backup_domains.items():
        if not data.get("deprecated"):
            domains_grouped.setdefault(data.get("group","Other"), {}).update({domainname: data})
    backup_groups = []
    for idx, key in enumerate(sorted(domains_grouped.keys())):
        value = domains_grouped[key]
        choices = []
        default_values = []
        for entry in sorted(value.keys()):
            choices.append( (entry,value[entry]["title"]) )
            if value[entry].get("default"):
                default_values.append(entry)
        choices.sort(key = lambda x: x[1])
        backup_groups.append( ("group_%d" % idx, ListChoice(title = key, choices = choices, default_value = default_values) ) )

    # Optional snapshot comment
    backup_groups.append(("comment", TextUnicode(title = _("Comment"), size=80)))
    snapshot_vs = Dictionary(
        elements =  backup_groups,
        optional_keys = []
    )


    if phase == "action":
        if html.has_var("_download_file"):
            download_file = html.var("_download_file")

            # Find the latest snapshot file
            if download_file == 'latest':
                if not snapshots:
                    return False
                download_file = snapshots[-1]
            elif download_file not in snapshots:
                raise MKUserError(None, _("Invalid download file specified."))

            download_path = os.path.join(snapshot_dir, download_file)
            if os.path.exists(download_path):
                html.req.headers_out['Content-Disposition'] = 'Attachment; filename=' + download_file
                html.req.headers_out['content_type'] = 'application/x-tar'
                html.write(open(download_path).read())
                return False

        # create snapshot
        elif html.has_var("_create_snapshot"):
            if html.check_transaction():
                # create snapshot
                store_domains = {}

                snapshot_options = snapshot_vs.from_html_vars("snapshot_options")
                snapshot_vs.validate_value(snapshot_options, "snapshot_options")

                for key, value in snapshot_options.items():
                    if key.startswith("group_"):
                        for entry in value:
                            store_domains[entry] = backup_domains[entry]

                snapshot_data = {}
                snapshot_name = "wato-snapshot-%s.tar" %  \
                                time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
                snapshot_data["comment"]       = snapshot_options.get("comment") \
                                                 or _("Snapshot created by %s") % config.user_id
                snapshot_data["type"]          = "manual"
                snapshot_data["snapshot_name"] = snapshot_name
                snapshot_data["domains"]       = store_domains

                return None, _("Created snapshot <tt>%s</tt>.") % create_snapshot(snapshot_data)

        # upload snapshot
        elif html.uploads.get("_upload_file"):
            uploaded_file = html.uploaded_file("_upload_file")
            filename      = uploaded_file[0]

            if ".." in filename or "/" in filename:
                raise MKUserError("_upload_file", _("Invalid filename"))
            filename = os.path.basename(filename)

            if uploaded_file[0] == "":
                raise MKUserError(None, _("Please select a file for upload."))

            if html.check_transaction():
                file_stream = cStringIO.StringIO(uploaded_file[2])
                status = get_snapshot_status((filename, file_stream), validate_checksums = True)

                if status.get("broken"):
                    raise MKUserError("_upload_file", _("This is not a Check_MK snapshot!<br>%s") % \
                                                                            status.get("broken_text"))
                elif not status.get("checksums") and not config.wato_upload_insecure_snapshots:
                    if status["type"] == "legacy":
                        raise MKUserError("_upload_file", _('The integrity of this snapshot could not be verified. '
                                          'You are restoring a legacy snapshot which can not be verified. The snapshot contains '
                                          'files which contain code that will be executed during runtime of the monitoring. '
                                          'The upload of insecure snapshots is currently disabled in WATO. If you want to allow '
                                          'the upload of insecure snapshots you can activate it in the Global Settings under '
                                          '<i>Configuration GUI (WATO) -> Allow upload of insecure WATO snapshots</i>'))
                    else:
                       raise MKUserError("_upload_file", _('The integrity of this snapshot could not be verified.<br><br>'
                                          'If you restore a snapshot on the same site as where it was created, the checksum should '
                                          'always be OK. If not, it is likely that something has been modified in the snapshot.<br>'
                                          'When you restore the snapshot on a different site, the checksum check will always fail. '
                                          'The snapshot contains files which contain code that will be executed during runtime '
                                          'of the monitoring.<br><br>'
                                          'The upload of insecure snapshots is currently disabled in WATO. If you want to allow '
                                          'the upload of insecure snapshots you can activate it in the Global Settings under<br>'
                                          '<tt>Configuration GUI (WATO) -> Allow upload of insecure WATO snapshots</tt>'))
                else:
                    file(snapshot_dir + filename, "w").write(uploaded_file[2])
                    html.set_var("_snapshot_name", filename)
                    return "snapshot_detail"

        # delete file
        elif html.has_var("_delete_file"):
            delete_file = html.var("_delete_file")

            if delete_file not in snapshots:
                raise MKUserError(None, _("Invalid file specified."))

            c = wato_confirm(_("Confirm deletion of snapshot"),
                             _("Are you sure you want to delete the snapshot <br><br>%s?") %
                                html.attrencode(delete_file)
                            )
            if c:
                os.remove(os.path.join(snapshot_dir, delete_file))
                # Remove any files in workdir
                for ext in [ ".pid", ".status", ".subtar", ".work" ]:
                    tmp_name = "%s/workdir/%s%s" % (snapshot_dir, os.path.basename(delete_file), ext)
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
                return None, _("Snapshot deleted.")
            elif c == False: # not yet confirmed
                return ""

        # restore snapshot
        elif html.has_var("_restore_snapshot"):
            snapshot_file = html.var("_restore_snapshot")

            if snapshot_file not in snapshots:
                raise MKUserError(None, _("Invalid file specified."))

            status = get_snapshot_status(snapshot_file, validate_checksums = True)

            if status['checksums'] == True:
                q = _("Are you sure you want to restore the snapshot %s?") % \
                                                html.attrencode(snapshot_file)

            elif status["type"] == "legacy" and status['checksums'] == None:
                q = _('The integrity of this snapshot could not be verified.<br><br>'
                      'You are restoring a legacy snapshot which can not be verified. The snapshot contains '
                      'files which contain code that will be executed during runtime of the monitoring. Please '
                      'ensure that the snapshot is a legit, not manipulated file.<br><br>'
                      'Do you want to continue restoring the snapshot?')

            else:
                q = _('The integrity of this snapshot could not be verified.<br><br>'
                      'If you restore a snapshot on the same site as where it was created, the checksum should '
                      'always be OK. If not, it is likely that something has been modified in the snapshot.<br>'
                      'When you restore the snapshot on a different site, the checksum check will always fail.<br><br>'
                      'The snapshot contains files which contain code that will be executed during runtime '
                      'of the monitoring. Please ensure that the snapshot is a legit, not manipulated file.<br><br>'
                      'Do you want to <i>ignore</i> the failed integrity check and restore the snapshot?')

            c = wato_confirm(_("Confirm restore snapshot"), q)
            if c:
                if status["type"] == "legacy":
                    multitar.extract_from_file(snapshot_dir + snapshot_file, backup_paths)
                else:
                    extract_snapshot(snapshot_file)
                log_pending(SYNCRESTART, None, "snapshot-restored",
                     _("Restored snapshot %s") % html.attrencode(snapshot_file))
                return None, _("Successfully restored snapshot.")
            elif c == False: # not yet confirmed
                return ""

        elif html.has_var("_factory_reset"):
            c = wato_confirm(_("Confirm factory reset"),
                _("If you proceed now, all hosts, folders, rules and other configurations "
                  "done with WATO will be deleted! Please consider making a snapshot before "
                  "you do this. Snapshots will not be deleted. Also the password of the currently "
                  "logged in user (%s) will be kept.<br><br>"
                  "Do you really want to delete all or your configuration data?") % config.user_id)
            if c:
                factory_reset()
                return None, _("Resetted WATO, wiped all configuration.")
            elif c == False: # not yet confirmed
                return ""
        return None

    else:
        snapshots = get_snapshots()

        # Render snapshot domain options
        html.begin_form("create_snapshot", method="POST")
        forms.header(_("Create snapshot"))
        forms.section(_("Elements to save"))
        forms.input(snapshot_vs, "snapshot_options", {})
        html.write("<br><br>")
        html.hidden_fields()
        forms.end()
        html.button("_create_snapshot", _("Create snapshot"), "submit")
        html.end_form()
        html.write("<br>")

        html.write("<h3>" + _("Restore from uploaded file") + "</h3>")
        html.write(_("Only supports snapshots up to 100MB. If your snapshot is larger than 100MB please copy it into the sites "
                   "backup directory <tt>%s/wato/snapshots</tt>. It will then show up in the snapshots table.") % defaults.var_dir)
        html.begin_form("upload_form", method = "POST")
        html.upload_file("_upload_file")
        html.button("upload_button", _("Restore from file"), "submit")
        html.hidden_fields()
        html.end_form()

        table.begin("snapshots", _("Snapshots"), empty_text=_("There are no snapshots available."))
        for name in snapshots:
            if name == "uploaded_snapshot":
                continue
            status = get_snapshot_status(name)
            table.row()
            # Snapshot name
            table.cell(_("From"), '<a href="%s">%s</a>' %
                       (make_link([("mode","snapshot_detail"),("_snapshot_name", name)]), status["name"]))

            # Comment
            table.cell(_("Comment"), status.get("comment",""))

            # Age and Size
            st = os.stat(snapshot_dir + name)
            age = time.time() - st.st_mtime
            table.cell(_("Size"), fmt_bytes(st.st_size), css="number"),

            # Status icons
            table.cell(_("Status"))
            if status.get("broken"):
                html.icon(status.get("broken_text",_("This snapshot is broken")), "validation_error")
            elif status.get("progress_status"):
                html.icon( status.get("progress_status"), "timeperiods")
        table.end()

def get_backup_domains(modes, extra_domains = {}):
    domains = {}
    for mode in modes:
        for domain, value in backup_domains.items():
            if mode in value and not value.get("deprecated"):
                domains.update({domain: value})
    domains.update(extra_domains)
    return domains

def do_snapshot_maintenance():
    snapshots = []
    for f in os.listdir(snapshot_dir):
        if f.startswith('wato-snapshot-'):
            status = get_snapshot_status(f)
            # only remove automatic and legacy snapshots
            if status.get("type") in [ "automatic", "legacy" ]:
                snapshots.append(f)

    snapshots.sort(reverse=True)
    while len(snapshots) > config.wato_max_snapshots:
        log_audit(None, "snapshot-removed", _("Removed snapshot %s") % snapshots[-1])
        os.remove(snapshot_dir + snapshots.pop())


def create_snapshot(data = {}):
    import copy
    def remove_functions(snapshot_data):
        snapshot_data_copy = copy.deepcopy(snapshot_data)
        for dom_key, dom_values in snapshot_data.items():
            for key, value in dom_values.items():
                if hasattr(value, '__call__'):
                    del snapshot_data_copy[dom_key][key]
        return snapshot_data_copy

    make_nagios_directory(snapshot_dir)

    snapshot_name = data.get("name") or "wato-snapshot-%s.tar" %  \
                    time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))
    snapshot_data = {}
    snapshot_data["comment"]       = data.get("comment", _("Snapshot created by %s") % config.user_id)
    snapshot_data["created_by"]    = data.get("created_by", config.user_id)
    snapshot_data["type"]          = data.get("type", "automatic")
    snapshot_data["snapshot_name"] = snapshot_name
    snapshot_data["domains"]       = remove_functions(data.get("domains", get_backup_domains(["default"])))

    check_mk_local_automation("create-snapshot", [], snapshot_data)

    log_audit(None, "snapshot-created", _("Created snapshot %s") % snapshot_name)
    do_snapshot_maintenance()

    return snapshot_name


def factory_reset():
    # Darn. What makes things complicated here is that we need to conserve htpasswd,
    # at least the account of the currently logged in user.
    users = userdb.load_users(lock = True)
    for id in users.keys():
        if id != config.user_id:
            del users[id]

    to_delete = [ path for c,n,path
                  in backup_paths
                  if n != "auth.secret" ] + [ log_dir ]
    for path in to_delete:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)

    make_nagios_directory(multisite_dir)
    make_nagios_directory(root_dir)

    userdb.save_users(users) # make sure, omdadmin is present after this
    log_pending(SYNCRESTART, None, "factory-reset", _("Complete reset to factory settings."))


#.
#   .--Value-Editor--------------------------------------------------------.
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
#   '----------------------------------------------------------------------'


class CheckTypeSelection(DualListChoice):
    def __init__(self, **kwargs):
        DualListChoice.__init__(self, **kwargs)

    def get_elements(self):
        checks = check_mk_local_automation("get-check-information")
        elements = [ (cn, (cn + " - " + c["title"])[:60]) for (cn, c) in checks.items()]
        elements.sort()
        return elements


def edit_value(valuespec, value, title=""):
    if title:
        title = title + "<br>"
    help = valuespec.help() or ""
    html.write('<tr>')
    html.write('<td class=legend>%s' % title)
    html.help(help)
    html.write("</td><td class=content>")

    valuespec.render_input("ve", value)
    html.write("</td></tr>")

def get_edited_value(valuespec):
    value = valuespec.from_html_vars("ve")
    valuespec.validate_value(value, "ve")
    return value


#.
#   .--Configuration-------------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+
#   | Main entry page for configuration of global variables, rules, groups,|
#   | timeperiods, users, etc.                                             |
#   '----------------------------------------------------------------------'

def mode_main(phase):
    if phase == "title":
        return _("WATO - Check_MK's Web Administration Tool")

    elif phase == "buttons":
        changelog_button()
        return

    elif phase == "action":
        return

    render_main_menu(modules)

def render_main_menu(some_modules, columns = 2):
    html.write('<div class="mainmenu">')
    for nr, (mode_or_url, title, icon, permission, help) in enumerate(some_modules):
        if "." not in permission:
            permission = "wato." + permission
        if not config.may(permission) and not config.may("wato.seeall"):
            continue

        if '?' in mode_or_url or '/' in mode_or_url:
            url = mode_or_url
        else:
            url = make_link([("mode", mode_or_url)])

        html.write('<a href="%s" onfocus="if (this.blur) this.blur();"' % url)
        # html.write(r''' onmouseover='this.style.backgroundImage="url(\"images/wato_mainmenu_button_hi.png\")"; ''')
        # html.write(r''' onmouseout='this.style.backgroundImage="url(\"images/wato_mainmenu_button_lo.png\")"; ''')
        html.write(">")
        html.write('<img src="images/icon_%s.png">' % icon)
        html.write('<div class=title>%s</div>' % title)
        html.write('<div class=subtitle>%s</div>' % help)
        html.write('</a>')

    html.write("</div>")

#.
#   .--LDAP Config---------------------------------------------------------.
#   |       _     ____    _    ____     ____             __ _              |
#   |      | |   |  _ \  / \  |  _ \   / ___|___  _ __  / _(_) __ _        |
#   |      | |   | | | |/ _ \ | |_) | | |   / _ \| '_ \| |_| |/ _` |       |
#   |      | |___| |_| / ___ \|  __/  | |__| (_) | | | |  _| | (_| |       |
#   |      |_____|____/_/   \_\_|      \____\___/|_| |_|_| |_|\__, |       |
#   |                                                         |___/        |
#   +----------------------------------------------------------------------+
#   | LDAP configuration and diagnose page                                 |
#   '----------------------------------------------------------------------'

def mode_ldap_config(phase):
    if phase == 'title':
        return _('LDAP Configuration')

    elif phase == 'buttons':
        global_buttons()
        html.context_button(_("Users"), make_link([("mode", "users")]), "users")
        return

    config_vars = [
        'ldap_connection',
        'ldap_userspec',
        'ldap_groupspec',
        'ldap_active_plugins',
        'ldap_cache_livetime',
        'ldap_debug_log',
    ]
    vs = [ (v, g_configvars[v][1]) for v in config_vars ]

    current_settings = load_configuration_settings()

    if not userdb.connector_enabled('ldap'):
        html.message(_('The LDAP user connector is disabled. You need to enable it to be able '
                       'to configure the LDAP settings.'))
        return

    if phase == 'action':
        if not html.check_transaction():
            return

        for (varname, valuespec) in vs:
            valuespec = dict(vs)[varname]
            new_value = valuespec.from_html_vars(varname)
            valuespec.validate_value(new_value, varname)
            if current_settings.get(varname) != new_value:
                msg = _("Changed LDAP configuration variable %s to %s.") \
                          % (varname, valuespec.value_to_text(new_value))
                log_pending(SYNC, None, "edit-configvar", msg)
            current_settings[varname] = new_value

        save_configuration_settings(current_settings)
        config.load_config() # make new configuration active
        return

    userdb.ldap_test_module()

    #
    # Regular page rendering
    #

    html.write('<div id=ldap>')
    html.write('<table><tr><td>')
    html.begin_form('ldap_config', method = "POST", action = 'wato.py?mode=ldap_config')
    need_header = True
    for (var, valuespec) in vs:
        value = current_settings.get(var, valuespec.default_value())
        if isinstance(valuespec, Dictionary):
            valuespec._render = "form"
        else:
            if need_header:
                forms.header(_('Other Settings'))
                need_header = False
            forms.section(valuespec.title())
        valuespec.render_input(var, value)
        html.help(valuespec.help())
    forms.end()

    html.button("_save", _("Save"))
    html.button("_test", _("Save & Test"))
    html.hidden_fields()
    html.end_form()
    html.write('</td><td style="padding-left:10px;">')

    html.write('<h2>' + _('Diagnostics') + '</h2>')
    if not html.var('_test'):
        html.message(HTML('<p>%s</p><p>%s</p>' %
                    (_('You can verify the single parts of your ldap configuration using this '
                       'dialog. Simply make your configuration in the form on the left side and '
                       'hit the "Save & Test" button to execute the tests. After '
                       'the page reload, you should see the results of the test here.'),
                     _('If you need help during configuration or experience problems, please refer '
                       'to the Multisite <a target="_blank" '
                       'href="http://mathias-kettner.de/checkmk_multisite_ldap_integration.html">'
                       'LDAP Documentation</a>.'))))
    else:
        def test_connect(address):
            conn, msg = userdb.ldap_connect_server(address)
            if conn:
                return (True, _('Connection established. The connection settings seem to be ok.'))
            else:
                return (False, msg)

        def test_user_base_dn(address):
            if not userdb.ldap_user_base_dn_configured():
                return (False, _('The User Base DN is not configured.'))
            userdb.ldap_connect(enforce_new = True, enforce_server = address)
            if userdb.ldap_user_base_dn_exists():
                return (True, _('The User Base DN could be found.'))
            elif userdb.ldap_bind_credentials_configured():
                return (False, _('The User Base DN could not be found. Maybe the provided '
                                 'user (provided via bind credentials) has no permission to '
                                 'access the Base DN or the credentials are wrong.'))
            else:
                return (False, _('The User Base DN could not be found. Seems you need '
                                 'to configure proper bind credentials.'))

        def test_user_count(address):
            if not userdb.ldap_user_base_dn_configured():
                return (False, _('The User Base DN is not configured.'))
            userdb.ldap_connect(enforce_new = True, enforce_server = address)
            try:
                ldap_users = userdb.ldap_get_users()
                msg = _('Found no user object for synchronization. Please check your filter settings.')
            except Exception, e:
                ldap_users = None
                msg = str(e)
                if 'successful bind must be completed' in msg:
                    if not userdb.ldap_bind_credentials_configured():
                        return (False, _('Please configure proper bind credentials.'))
                    else:
                        return (False, _('Maybe the provided user (provided via bind credentials) has not '
                                         'enough permissions or the credentials are wrong.'))

            if ldap_users and len(ldap_users) > 0:
                return (True, _('Found %d users for synchronization.') % len(ldap_users))
            else:
                return (False, msg)

        def test_group_base_dn(address):
            if not userdb.ldap_group_base_dn_configured():
                return (False, _('The Group Base DN is not configured, not fetching any groups.'))
            userdb.ldap_connect(enforce_new = True, enforce_server = address)
            if userdb.ldap_group_base_dn_exists():
                return (True, _('The Group Base DN could be found.'))
            else:
                return (False, _('The Group Base DN could not be found.'))

        def test_group_count(address):
            if not userdb.ldap_group_base_dn_configured():
                return (False, _('The Group Base DN is not configured, not fetching any groups.'))
            userdb.ldap_connect(enforce_new = True, enforce_server = address)
            try:
                ldap_groups = userdb.ldap_get_groups()
                msg = _('Found no group object for synchronization. Please check your filter settings.')
            except Exception, e:
                ldap_groups = None
                msg = str(e)
                if 'successful bind must be completed' in msg:
                    if not userdb.ldap_bind_credentials_configured():
                        return (False, _('Please configure proper bind credentials.'))
                    else:
                        return (False, _('Maybe the provided user (provided via bind credentials) has not '
                                         'enough permissions or the credentials are wrong.'))
            if ldap_groups and len(ldap_groups) > 0:
                return (True, _('Found %d groups for synchronization.') % len(ldap_groups))
            else:
                return (False, msg)

        def test_groups_to_roles(address):
            if 'groups_to_roles' not in config.ldap_active_plugins:
                return True, _('Skipping this test (Plugin is not enabled)')

            userdb.ldap_connect(enforce_new = True, enforce_server = address)
            num = 0
            for role_id, dn in config.ldap_active_plugins['groups_to_roles'].items():
                if isinstance(dn, str):
                    num += 1
                    try:
                        ldap_groups = userdb.ldap_get_groups(dn)
                        if not ldap_groups:
                            return False, _('Could not find the group specified for role %s') % role_id
                    except Exception, e:
                        return False, _('Error while fetching group for role %s: %s') % (role_id, str(e))
            return True, _('Found all %d groups.') % num

        tests = [
            (_('Connection'),          test_connect),
            (_('User Base-DN'),        test_user_base_dn),
            (_('Count Users'),         test_user_count),
            (_('Group Base-DN'),       test_group_base_dn),
            (_('Count Groups'),        test_group_count),
            (_('Sync-Plugin: Roles'),  test_groups_to_roles),
        ]

        for address in userdb.ldap_servers():
            html.write('<h3>%s: %s</h3>' % (_('Server'), address))
            table.begin('test', searchable = False)

            for title, test in tests:
                table.row()
                try:
                    state, msg = test(address)
                except Exception, e:
                    state = False
                    msg = _('Exception: %s') % html.attrencode(e)

                if state:
                    img = html.render_icon("success", _('Success'))
                else:
                    img = html.render_icon("failed", _("Failed"))

                table.cell(_("Test"),   title)
                table.cell(_("State"),   img)
                table.cell(_("Details"), msg)

            table.end()

        userdb.ldap_disconnect()

    html.write('</td></tr></table>')
    html.write('</div>')

#.
#   .--Global-Settings-----------------------------------------------------.
#   |          ____ _       _           _  __     __                       |
#   |         / ___| | ___ | |__   __ _| | \ \   / /_ _ _ __ ___           |
#   |        | |  _| |/ _ \| '_ \ / _` | |  \ \ / / _` | '__/ __|          |
#   |        | |_| | | (_) | |_) | (_| | |   \ V / (_| | |  \__ \          |
#   |         \____|_|\___/|_.__/ \__,_|_|    \_/ \__,_|_|  |___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Editor for global settings in main.mk                                |
#   '----------------------------------------------------------------------'

def mode_globalvars(phase):
    search = html.var("search")
    if search != None:
        search = search.strip().lower()

    if phase == "title":
        if search:
            return _("Global configuration settings matching %s") % html.attrencode(search)
        else:
            return _("Global configuration settings for Check_MK")

    elif phase == "buttons":
        global_buttons()
        return

    # Get default settings of all configuration variables of interest in the domain
    # "check_mk". (this also reflects the settings done in main.mk)
    check_mk_vars = [ varname for (varname, var) in g_configvars.items() if var[0] == "check_mk" ]
    default_values = check_mk_local_automation("get-configuration", [], check_mk_vars)
    current_settings = load_configuration_settings()

    if phase == "action":
        varname = html.var("_varname")
        action = html.var("_action")
        if varname:
            domain, valuespec, need_restart, allow_reset, in_global_settings = g_configvars[varname]
            def_value = default_values.get(varname, valuespec.default_value())

            if action == "reset" and not is_a_checkbox(valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset the configuration variable <b>%s</b> "
                      "back to the default value of <b><tt>%s</tt></b>?") %
                       (varname, valuespec.value_to_text(def_value)))
            else:
                if not html.check_transaction():
                    return
                c = True # no confirmation for direct toggle

            if c:
                # if action == "reset":
                #     del current_settings[varname]
                #     msg = _("Resetted configuration variable %s to its default.") % varname
                # else:
                if varname in current_settings:
                    current_settings[varname] = not current_settings[varname]
                else:
                    current_settings[varname] = not def_value
                msg = _("Changed Configuration variable %s to %s." % (varname,
                    current_settings[varname] and "on" or "off"))
                save_configuration_settings(current_settings)
                pending_func  = g_configvar_domains[domain].get("pending")
                if pending_func:
                    pending_func(msg)
                else:
                    log_pending(need_restart and SYNCRESTART or SYNC, None, "edit-configvar", msg)
                if action == "_reset":
                    return "globalvars", msg
                else:
                    return "globalvars"
            elif c == False:
                return ""
            else:
                return None
        else:
            return

    render_global_configuration_variables(default_values, current_settings, search=search)

def render_global_configuration_variables(default_values, current_settings, show_all=False, search=None):
    groupnames = g_configvar_groups.keys()
    groupnames.sort()

    search_form(_("Search for settings:"))

    at_least_one_painted = False
    html.write('<div class=globalvars>')
    for groupname in groupnames:
        header_is_painted = False # needed for omitting empty groups

        for domain, varname, valuespec in g_configvar_groups[groupname]:
            if not show_all and (not g_configvars[varname][4]
                                 or not g_configvar_domains[domain].get('in_global_settings', True)):
                continue # do not edit via global settings
            if domain == "check_mk" and varname not in default_values:
                if config.debug:
                    raise MKGeneralException("The configuration variable <tt>%s</tt> is unknown to "
                                          "your local Check_MK installation" % varname)
                else:
                    continue

            help_text  = type(valuespec.help())  == unicode and valuespec.help().encode("utf-8")  or valuespec.help() or ''
            title_text = type(valuespec.title()) == unicode and valuespec.title().encode("utf-8") or valuespec.title()

            if search and search not in groupname \
                           and search not in domain \
                           and search not in varname \
                           and search not in help_text \
                           and search not in title_text:
                continue # skip variable when search is performed and nothing matches
            at_least_one_painted = True

            if not header_is_painted:
                # always open headers when searching
                forms.header(groupname, isopen=search)
                header_is_painted = True

            defaultvalue = default_values.get(varname, valuespec.default_value())

            edit_url = make_link([("mode", "edit_configvar"), ("varname", varname), ("site", html.var("site", ""))])
            title = '<a href="%s" class=%s title="%s">%s</a>' % \
                    (edit_url, varname in current_settings and '"modified"' or '""',
                     html.strip_tags(help_text), title_text)

            if varname in current_settings:
                to_text = valuespec.value_to_text(current_settings[varname])
            else:
                to_text = valuespec.value_to_text(defaultvalue)

            # Is this a simple (single) value or not? change styling in these cases...
            simple = True
            if '\n' in to_text or '<td>' in to_text:
                simple = False
            forms.section(title, simple=simple)

            toggle_url = html.makeactionuri([("_action", "toggle"), ("_varname", varname)])
            if varname in current_settings:
                if is_a_checkbox(valuespec):
                    html.icon_button(toggle_url, _("Immediately toggle this setting"),
                        "snapin_switch_" + (current_settings[varname] and "on" or "off"),
                        cssclass="modified")
                else:
                    html.write('<a class=modified href="%s">%s</a>' % (edit_url, to_text))
            else:
                if is_a_checkbox(valuespec):
                    html.icon_button(toggle_url, _("Immediately toggle this setting"),
                    # "snapin_greyswitch_" + (defaultvalue and "on" or "off"))
                    "snapin_switch_" + (defaultvalue and "on" or "off"))
                else:
                    html.write('<a href="%s">%s</a>' % (edit_url, to_text))

        if header_is_painted:
            forms.end()
    if not at_least_one_painted:
        html.message(_('Did not find any global setting matching your search.'))
    html.write('</div>')


def mode_edit_configvar(phase, what = 'globalvars'):
    siteid = html.var("site")
    if siteid:
        sites = load_sites()
        site = sites[siteid]

    if phase == "title":
        if what == 'mkeventd':
            return _("Event Console Configuration")
        elif siteid:
            return _("Site-specific global configuration for %s" % siteid)
        else:
            return _("Global configuration settings for Check_MK")

    elif phase == "buttons":
        if what == 'mkeventd':
            html.context_button(_("Abort"), make_link([("mode", "mkeventd_config")]), "abort")
        elif siteid:
            html.context_button(_("Abort"), make_link([("mode", "edit_site_globals"), ("site", siteid)]), "abort")
        else:
            html.context_button(_("Abort"), make_link([("mode", "globalvars")]), "abort")
        return

    varname = html.var("varname")
    domain, valuespec, need_restart, allow_reset, in_global_settings = g_configvars[varname]
    if siteid:
        current_settings = site.setdefault("globals", {})
    else:
        current_settings = load_configuration_settings()

    is_on_default = varname not in current_settings

    if phase == "action":
        if html.var("_reset"):
            if not is_a_checkbox(valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset this configuration variable "
                      "back to its default value?"))
                if c == False:
                    return ""
                elif c == None:
                    return None

            del current_settings[varname]
            msg = _("Resetted configuration variable %s to its default.") % varname
        else:
            new_value = get_edited_value(valuespec)
            current_settings[varname] = new_value
            msg = _("Changed global configuration variable %s to %s.") \
                  % (varname, valuespec.value_to_text(new_value))

        if siteid:
            save_sites(sites, activate=False)
            changes = { "need_sync" : True }
            if need_restart:
                changes["need_restart"] = True
            update_replication_status(siteid, changes)
            log_pending(AFFECTED, None, "edit-configvar", msg)
            return "edit_site_globals"
        else:
            save_configuration_settings(current_settings)
            if need_restart:
                status = SYNCRESTART
            else:
                status = SYNC

            pending_func  = g_configvar_domains[domain].get("pending")
            if pending_func:
                pending_func(msg)
            else:
                log_pending(status, None, "edit-configvar", msg)
            if what == 'mkeventd':
                return 'mkeventd_config'
            else:
                return "globalvars"

    check_mk_vars = check_mk_local_automation("get-configuration", [], [varname])

    if varname in current_settings:
        value = current_settings[varname]
    else:
        if siteid:
            globalsettings = load_configuration_settings()
            check_mk_vars.update(globalsettings)
        value = check_mk_vars.get(varname, valuespec.default_value())

    if siteid:
        defvalue = check_mk_vars.get(varname, valuespec.default_value())
    else:
        defvalue = valuespec.default_value()


    html.begin_form("value_editor", method="POST")
    forms.header(valuespec.title())
    if not config.wato_hide_varnames:
        forms.section(_("Variable for <tt>%s.mk</tt>" %
            { "check_mk" : "main" }.get(domain, domain)))
        html.write("<tt>%s</tt>" % varname)

    forms.section(_("Current setting"))
    valuespec.render_input("ve", value)
    valuespec.set_focus("ve")
    html.help(valuespec.help())

    forms.section(_("Default setting"))
    if is_on_default:
        html.write(_("This variable is at factory settings."))
    else:
        curvalue = current_settings[varname]
        if curvalue == defvalue:
            html.write(_("Your setting and factory settings are identical."))
        else:
            html.write(valuespec.value_to_text(defvalue))

    forms.end()
    html.button("save", _("Save"))
    if allow_reset and not is_on_default:
        curvalue = current_settings[varname]
        html.button("_reset", curvalue == defvalue and _("Remove explicit setting") or _("Reset to default"))
    html.hidden_fields()
    html.end_form()

# domain is one of "check_mk", "multisite" or "nagios"
def register_configvar(group, varname, valuespec, domain="check_mk",
                       need_restart=False, allow_reset=True, in_global_settings=True):
    g_configvar_groups.setdefault(group, []).append((domain, varname, valuespec))
    g_configvars[varname] = domain, valuespec, need_restart, allow_reset, in_global_settings

g_configvar_domains = {
    "check_mk" : {
        "configdir" : root_dir,
    },
    "multisite" : {
        "configdir" : multisite_dir,
    },
}

# The following keys are available:
# configdir: Directory to store the global.mk in (applies to check_mk, multisite, mkeventd)
# pending:   Handler function to create the pending log entry
# load:      Optional handler to load/parse the file
# save:      Optional handler to save the filea
# in_global_settings: Set to False to hide whole section from global settings dialog
def register_configvar_domain(domain, configdir = None, pending = None, save = None, load = None, in_global_settings = True):
    g_configvar_domains[domain] = {
        'in_global_settings': in_global_settings,
    }
    for k in [ 'configdir', 'pending', 'save', 'load' ]:
        if locals()[k] is not None:
            g_configvar_domains[domain][k] = locals()[k]

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
    for domain, domain_info in g_configvar_domains.items():
        if 'load' in domain_info:
            domain_info['load'](settings)
        else:
            load_configuration_vars(domain_info["configdir"] + "global.mk", settings)
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
    for varname, (domain, valuespec, need_restart, allow_reset, in_global_settings) in g_configvars.items():
        if varname not in vars:
            continue
        per_domain.setdefault(domain, {})[varname] = vars[varname]

    # The global setting wato_enabled is not registered in the configuration domains
    # since the user must not change it directly. It is set by D-WATO on slave sites.
    if "wato_enabled" in vars:
        per_domain.setdefault("multisite", {})["wato_enabled"] = vars["wato_enabled"]

    for domain, domain_info in g_configvar_domains.items():
        if 'save' in domain_info:
            domain_info['save'](per_domain.get(domain, {}))
        else:
            dir = domain_info["configdir"]
            make_nagios_directory(dir)
            save_configuration_vars(per_domain.get(domain, {}), dir + "global.mk")

def save_configuration_vars(vars, filename):
    out = create_user_file(filename, 'w')
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for varname, value in vars.items():
        out.write("%s = %s\n" % (varname, pprint.pformat(value)))

#.
#   .--Groups--------------------------------------------------------------.
#   |                    ____                                              |
#   |                   / ___|_ __ ___  _   _ _ __  ___                    |
#   |                  | |  _| '__/ _ \| | | | '_ \/ __|                   |
#   |                  | |_| | | | (_) | |_| | |_) \__ \                   |
#   |                   \____|_|  \___/ \__,_| .__/|___/                   |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   | Mode for editing host-, service- and contact groups                  |
#   '----------------------------------------------------------------------'

def find_usages_of_group_in_rules(name, varnames):
    used_in = []
    rulesets = load_all_rulesets()
    for varname in varnames:
        ruleset  = rulesets[varname]
        rulespec = g_rulespecs[varname]
        for folder, rule in ruleset:
            value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
            if value == name:
                used_in.append(("%s: %s" % (_("Ruleset"), g_rulespecs[varname]["title"]),
                               make_link([("mode", "edit_ruleset"), ("varname", varname)])))
    return used_in

# Check if a group is currently in use and cannot be deleted
# Returns a list of occurrances.
# Possible usages:
# - 1. rules: host to contactgroups, services to contactgroups
# - 2. user memberships
def find_usages_of_contact_group(name):
    # Part 1: Rules
    used_in = find_usages_of_group_in_rules(name, [ 'host_contactgroups', 'service_contactgroups' ])

    # Is the contactgroup assigned to a user?
    users = filter_hidden_users(userdb.load_users())
    entries = users.items()
    entries.sort(cmp = lambda a, b: cmp(a[1].get("alias"), b[1].get("alias")))
    for userid, user in entries:
        cgs = user.get("contactgroups", [])
        if name in cgs:
            used_in.append(('%s: %s' % (_('User'), user.get('alias')),
                make_link([('mode', 'edit_user'), ('edit', userid)])))

    global_config = load_configuration_settings()

    # Used in default_user_profile?
    domain, valuespec, need_restart, allow_reset, in_global_settings = g_configvars['default_user_profile']
    configured = global_config.get('default_user_profile', {})
    default_value = valuespec.default_value()
    if (configured and name in configured['contactgroups']) \
       or name in  default_value['contactgroups']:
        used_in.append(('%s' % (_('Default User Profile')),
            make_link([('mode', 'edit_configvar'), ('varname', 'default_user_profile')])))

    # Is the contactgroup used in mkeventd notify (if available)?
    if 'mkeventd_notify_contactgroup' in g_configvars:
        domain, valuespec, need_restart, allow_reset, in_global_settings = g_configvars['mkeventd_notify_contactgroup']
        configured = global_config.get('mkeventd_notify_contactgroup')
        default_value = valuespec.default_value()
        if (configured and name == configured) \
           or name == default_value:
            used_in.append(('%s' % (valuespec.title()),
                make_link([('mode', 'edit_configvar'), ('varname', 'mkeventd_notify_contactgroup')])))

    return used_in

def find_usages_of_host_group(name):
    return find_usages_of_group_in_rules(name, [ 'host_groups' ])

def find_usages_of_service_group(name):
    return find_usages_of_group_in_rules(name, [ 'service_groups' ])

def get_nagvis_maps():
    # Find all NagVis maps in the local installation to register permissions
    # for each map. When no maps can be found skip this problem silently.
    # This only works in OMD environments.
    maps = []
    if defaults.omd_root:
        nagvis_maps_path = defaults.omd_root + '/etc/nagvis/maps'
        for f in os.listdir(nagvis_maps_path):
            if f[0] != '.' and f.endswith('.cfg'):
                maps.append((f[:-4], f[:-4]))
    return maps

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
        if what == "host":
            html.context_button(_("Service groups"), make_link([("mode", "service_groups")]), "hostgroups")
            html.context_button(_("New host group"), make_link([("mode", "edit_host_group")]), "new")
        elif what == "service":
            html.context_button(_("Host groups"), make_link([("mode", "host_groups")]), "servicegroups")
            html.context_button(_("New service group"), make_link([("mode", "edit_service_group")]), "new")
        else:
            html.context_button(_("New contact group"), make_link([("mode", "edit_contact_group")]), "new")
        if what == "contact":
            html.context_button(_("Rules"), make_link([("mode", "rulesets"),
                ("filled_in", "search"), ("search", _("contact group"))]), "rulesets")
        else:
            varname = what + "_groups"
            html.context_button(_("Rules"), make_link([("mode", "edit_ruleset"), ("varname", varname)]), "rulesets")
        return

    all_groups = userdb.load_group_information()
    groups = all_groups.get(what, {})

    if phase == "action":
        if html.var('_delete'):
            delname = html.var("_delete")

            if what == 'contact':
                usages = find_usages_of_contact_group(delname)
            elif what == 'host':
                usages = find_usages_of_host_group(delname)
            elif what == 'service':
                usages = find_usages_of_service_group(delname)

            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this %s group.") % what,
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            confirm_txt = _('Do you really want to delete the %s group "%s"?') % (what, delname)

            c = wato_confirm(_("Confirm deletion of group \"%s\"" % delname), confirm_txt)
            if c:
                del groups[delname]
                save_group_information(all_groups)
                if what == 'contact':
                    hooks.call('contactgroups-saved', all_groups)
                log_pending(SYNCRESTART, None, "edit-%sgroups", _("Deleted %s group %s" % (what, delname)))
            elif c == False:
                return ""

        return None

    sorted = groups.items()
    sorted.sort(cmp = lambda a,b: cmp(a[1]['alias'], b[1]['alias']))
    if len(sorted) == 0:
        if what == "contact":
            render_main_menu([
              ( "edit_contact_group", _("Create new contact group"), "new",
              what == "contact" and "users" or "groups",
              _("Contact groups are needed for assigning hosts and services to people (contacts)"))])
        else:
            html.write("<div class=info>" + _("No groups are defined yet.") + "</div>")
        return

    # Show member of contact groups
    if what == "contact":
        users = filter_hidden_users(userdb.load_users())
        members = {}
        for userid, user in users.items():
            cgs = user.get("contactgroups", [])
            for cg in cgs:
                members.setdefault(cg, []).append((userid, user.get('alias', userid)))

    table.begin(what + "groups")
    for name, group in sorted:
        table.row()

        table.cell(_("Actions"), css="buttons")
        edit_url = make_link([("mode", "edit_%s_group" % what), ("edit", name)])
        delete_url = html.makeactionuri([("_delete", name)])
        clone_url    =  make_link([("mode", "edit_%s_group" % what), ("clone", name)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy of this group"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), group['alias'])

        if what == "contact":
            table.cell(_("Members"))
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_user"), ("edit", userid)]), alias)
                 for userid, alias in members.get(name, [])]))

    table.end()


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

    all_groups = userdb.load_group_information()
    groups = all_groups.setdefault(what, {})

    edit_nagvis_map_permissions = what == 'contact' and defaults.omd_root
    if edit_nagvis_map_permissions:
        vs_nagvis_maps = ListChoice(
            title = _('NagVis Maps'),
            choices = get_nagvis_maps,
            toggle_all = True,
        )

        if not new:
            permitted_maps = groups[name].get('nagvis_maps', [])
        else:
            permitted_maps = []

    if phase == "action":
        if html.check_transaction():
            alias = html.var_utf8("alias").strip()
            if not alias:
                raise MKUserError("alias", _("Please specify an alias name."))

            unique, info = is_alias_used(what, name, alias)
            if not unique:
                raise MKUserError("alias", info)

            if new:
                name = html.var("name").strip()
                if len(name) == 0:
                    raise MKUserError("name", _("Please specify a name of the new group."))
                if ' ' in name:
                    raise MKUserError("name", _("Sorry, spaces are not allowed in group names."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid group name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if name in groups:
                    raise MKUserError("name", _("Sorry, there is already a group with that name"))
                groups[name] = {
                    'alias': alias,
                }
                log_pending(SYNCRESTART, None, "edit-%sgroups" % what, _("Create new %s group %s") % (what, name))
            else:
                groups[name] = {
                    'alias': alias,
                }
                log_pending(SYNCRESTART, None, "edit-%sgroups" % what, _("Updated properties of %s group %s") % (what, name))

            if edit_nagvis_map_permissions:
                permitted_maps = vs_nagvis_maps.from_html_vars('nagvis_maps')
                vs_nagvis_maps.validate_value(permitted_maps, 'nagvis_maps')
                if permitted_maps:
                    groups[name]['nagvis_maps'] = permitted_maps

            save_group_information(all_groups)
            if what == 'contact':
                hooks.call('contactgroups-saved', all_groups)

        return what + "_groups"


    html.begin_form("group")
    forms.header(_("Properties"))
    forms.section(_("Name"), simple = not new)
    html.help(_("The name of the group is used as an internal key. It cannot be "
                 "changed later. It is also visible in the status GUI."))
    if new:
        clone_group = html.var("clone")
        html.text_input("name", clone_group or "")
        html.set_focus("name")
    else:
        clone_group = None
        html.write(name)
        html.set_focus("alias")

    forms.section(_("Alias"))
    html.help(_("An Alias or description of this group."))
    alias = groups.get(name, {}).get('alias', '')
    if not alias:
        if clone_group:
            alias = groups.get(clone_group, {}).get('alias', '')
        else:
            alias = name
    html.text_input("alias", alias)

    # Show permissions for NagVis maps if any of those exist
    if edit_nagvis_map_permissions and get_nagvis_maps():
        forms.header(_("Permissions"))
        forms.section(_("Access to NagVis Maps"))
        html.help(_("Configure access permissions to NagVis maps."))
        vs_nagvis_maps.render_input('nagvis_maps', permitted_maps)

    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def save_group_information(all_groups):
    # Split groups data into Check_MK/Multisite parts
    check_mk_groups  = {}
    multisite_groups = {}

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
    make_nagios_directory(root_dir)
    out = create_user_file(root_dir + "groups.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for what in [ "host", "service", "contact" ]:
        if what in check_mk_groups and len(check_mk_groups[what]) > 0:
            out.write("if type(define_%sgroups) != dict:\n    define_%sgroups = {}\n" % (what, what))
            out.write("define_%sgroups.update(%s)\n\n" % (what, pprint.pformat(check_mk_groups[what])))

    # Users with passwords for Multisite
    filename = multisite_dir + "groups.mk.new"
    make_nagios_directory(multisite_dir)
    out = create_user_file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for what in [ "host", "service", "contact" ]:
        if what in multisite_groups and len(multisite_groups[what]) > 0:
            out.write("multisite_%sgroups = \\\n%s\n\n" % (what, pprint.pformat(multisite_groups[what])))
    out.close()
    os.rename(filename, filename[:-4])

class GroupSelection(ElementSelection):
    def __init__(self, what, **kwargs):
        kwargs.setdefault('empty_text', _('You have not defined any %s group yet. Please '
                                          '<a href="wato.py?mode=edit_%s_group">create</a> at least one first.') %
                                                                                                    (what, what))
        ElementSelection.__init__(self, **kwargs)
        self._what = what
        # Allow to have "none" entry with the following title
        self._no_selection = kwargs.get("no_selection")

    def get_elements(self):
        all_groups = userdb.load_group_information()
        this_group = all_groups.get(self._what, {})
        # replace the title with the key if the title is empty
        elements = [ (k, t['alias'] and t['alias'] or k) for (k, t) in this_group.items() ]
        if self._no_selection:
            # Beware: ElementSelection currently can only handle string
            # keys, so we cannot take 'None' as a value.
            elements.append(('', self._no_selection))
        return dict(elements)


class CheckTypeGroupSelection(ElementSelection):
    def __init__(self, checkgroup, **kwargs):
        ElementSelection.__init__(self, **kwargs)
        self._checkgroup = checkgroup

    def get_elements(self):
        checks = check_mk_local_automation("get-check-information")
        elements = dict([ (cn, "%s - %s" % (cn, c["title"])) for (cn, c) in checks.items()
                     if c.get("group") == self._checkgroup ])
        return elements

    def value_to_text(self, value):
        return "<tt>%s</tt>" % value


#.
#   .--Notifications-(Rule Based)------------------------------------------.
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Module for managing the new rule based notifications.               |
#   '----------------------------------------------------------------------'

def load_notification_rules():
    filename = root_dir + "notifications.mk"
    if not os.path.exists(filename):
        return []
    try:
        vars = { "notification_rules" : [] }
        execfile(filename, vars, vars)
        notification_rules = vars["notification_rules"]
        # Convert to new plugin configuration format
        for rule in notification_rules:
            if "notify_method" in rule:
                method = rule["notify_method"]
                plugin = rule["notify_plugin"]
                del rule["notify_method"]
                rule["notify_plugin"] = ( plugin, method )
        return notification_rules
    except:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        return []

def save_notification_rules(rules):
    make_nagios_directory(root_dir)
    file(root_dir + "notifications.mk", "w").write("notification_rules += %s\n" % pprint.pformat(rules))


def FolderChoice(**kwargs):
    kwargs["choices"] = folder_selection(g_root_folder)
    kwargs.setdefault("title", _("Folder"))
    return DropdownChoice(**kwargs)


class GroupChoice(DualListChoice):
    def __init__(self, what, **kwargs):
        DualListChoice.__init__(self, **kwargs)
        self.what = what
        self._choices = lambda: self.load_groups()

    def load_groups(self):
        all_groups = userdb.load_group_information()
        this_group = all_groups.get(self.what, {})
        return [ (k, t['alias'] and t['alias'] or k) for (k, t) in this_group.items() ]

def vs_notification_bulkby():
    return ListChoice(
      title = _("Create separate notification bulks based on"),
      choices = [
        ( "folder",     _("Folder") ),
        ( "host",       _("Host") ),
        ( "service",    _("Service description") ),
        ( "sl",         _("Service level") ),
        ( "check_type", _("Check type") ),
        ( "state",      _("Host/Service state") ),
      ],
      default_value = [ "host" ],
    )

def vs_notification_scripts():
    return DropdownChoice(
       title = _("Notification Script"),
       choices = notification_script_choices,
       default_value = "mail"
    )

def vs_notification_methods():
    return CascadingDropdown(
        title = _("Notification Method"),
        choices = notification_script_choices_with_parameters,
        default_value = ( "mail", {} )
    )

def vs_notification_rule(userid = None):
    if userid:
        contact_headers = []
        section_contacts = []
        section_override = []
    else:
        contact_headers = [
            ( _("Contact Selection"), [ "contact_all", "contact_all_with_email", "contact_object",
                                        "contact_users", "contact_groups", "contact_emails" ] ),
        ]
        section_contacts = [
            # Contact selection
            ( "contact_object",
              Checkbox(
                  title = _("All contacts of the notified object"),
                  label = _("Notify all contacts of the notified host or service."),
                  default_value = True,
              )
            ),
            ( "contact_all",
              Checkbox(
                  title = _("All users"),
                  label = _("Notify all users"),
              )
            ),
            ( "contact_all_with_email",
              Checkbox(
                  title = _("All users with an email address"),
                  label = _("Notify all users that have configured an email address in their profile"),
              )
            ),
            ( "contact_users",
              ListOf(
                  UserSelection(only_contacts = False),
                  title = _("The following users"),
                  help = _("Enter a list of user IDs to be notified here. These users need to be members "
                           "of at least one contact group in order to be notified."),
                  movable = False,
              )
            ),
            ( "contact_groups",
              ListOf(
                  GroupSelection("contact"),
                  title = _("The members of certain contact groups"),
                  movable = False,
              )
            ),
            ( "contact_emails",
              ListOfStrings(
                  valuespec = EmailAddress(size = 44),
                  title = _("The following explicit email addresses"),
                  orientation = "vertical",
              )
            ),
        ]
        section_override = [
            ( "allow_disable",
              Checkbox(
                title = _("Overriding by users"),
                help = _("If you uncheck this option then users are not allowed to deactive notifications "
                         "that are created by this rule."),
                label = _("allow users to deactivate this notification"),
                default_value = True,
              )
            ),
        ]

    return Dictionary(
        title = _("Rule Properties"),
        elements = [
            # General Properties
            ( "description",
              TextUnicode(
                title = _("Description"),
                help = _("You can use this description for commenting your rules. It has no influence on the notification."),
                size = 64,
                attrencode = True,
                allow_empty = False,
            )),
            ( "comment",
              TextAreaUnicode(
                title = _("Comment"),
                help = _("An optional comment that explains the purpose of this rule."),
                rows = 5,
              )
            ),
            ( "disabled",
              Checkbox(
                title = _("Rule activation"),
                help = _("Disabled rules are kept in the configuration but are not applied."),
                label = _("do not apply this rule"),
              )
            ),
        ] + section_override +
        [

            # Matching
            ( "match_folder",
              FolderChoice(
                  help = _("This condition makes the rule match only hosts that are managed "
                           "via WATO and that are contained in this folder - either directly "
                           "or in one of its subfolders."),
              ),
            ),
            ( "match_hosttags",
              HostTagCondition(
                  title = _("Match Host Tags"))
            ),
            ( "match_hostgroups",
              GroupChoice("host",
                  title = _("Match Host Groups"),
                  help = _("The host must be in one of the selected host groups"),
                  allow_empty = False,
              )
            ),
            ( "match_hosts",
              ListOfStrings(
                  title = _("Match only the following hosts"),
                  size = 24,
                  orientation = "horizontal",
                  allow_empty = False,
                  empty_text = _("Please specify at least one host. Disable the option if you want to allow all hosts."),
              )
            ),
            ( "match_exclude_hosts",
              ListOfStrings(
                  title = _("Exclude the following hosts"),
                  size = 24,
                  orientation = "horizontal",
              )
            ),
            ( "match_services",
              ListOfStrings(
                  title = _("Match only the following services"),
                  help = _("Specify a list of regular expressions that must match the <b>beginning</b> of the "
                           "service name in order for the rule to match. Note: Host notifications never match this "
                           "rule if this option is being used."),
                  valuespec = TextUnicode(size = 32),
                  orientation = "horizontal",
                  allow_empty = False,
                  empty_text = _("Please specify at least one service regex. Disable the option if you want to allow all services."),
              )
            ),
            ( "match_servicegroups",
              GroupChoice("service",
                  title = _("Match Service Groups"),
                  help = _("The service must be in one of the selected service groups"),
                  allow_empty = False,
              )
            ),
            ( "match_contactgroups",
              GroupChoice("contact",
                  title = _("Match Contact Groups (CMC only)"),
                  help = _("The host/service must be in one of the selected contact groups. This only works with Check_MK Micro Core. " \
                           "If you don't use the CMC that filter will not apply"),
                  allow_empty = False,
              )
            ),
            ( "match_exclude_services",
              ListOfStrings(
                  title = _("Do <b>not</b> match the following services"),
                  valuespec = TextUnicode(size = 32),
                  orientation = "horizontal",
              )
            ),
            ( "match_plugin_output",
              RegExp(
                 title = _("Match the output of the check plugin"),
                 help = _("This text is a regular expression that is being searched in the output "
                          "of the check plugins that produced the alert. It is not a prefix but an infix match."),
              ),
            ),
            ( "match_checktype",
              CheckTypeSelection(
                  title = _("Match the following check types"),
                  help = _("Only apply the rule if the notification originates from certain types of check plugins. "
                           "Note: Host notifications never match this rule if this option is being used."),
              )
            ),
            ( "match_timeperiod",
              TimeperiodSelection(
                  title = _("Match only during timeperiod"),
                  help = _("Match this rule only during times where the selected timeperiod from the monitoring "
                           "system is active."),
              ),
            ),
            ( "match_escalation",
              Tuple(
                  title = _("Restrict to n<sup>th</sup> to m<sup>th</sup> notification"),
                  orientation = "float",
                  elements = [
                      Integer(
                          label = _("from"),
                          help = _("Let through notifications counting from this number. "
                                   "For normal alerts The first notification has the number 1. "
                                   "For custom notifications the number is 0."),
                          default_value = 0,
                          minvalue = 0,
                          maxvalue = 999999,
                      ),
                      Integer(
                          label = _("to"),
                          help = _("Let through notifications counting upto this number"),
                          default_value = 999999,
                          minvalue = 1,
                          maxvalue = 999999,
                      ),
                ],
              ),
            ),
            ( "match_escalation_throttle",
              Tuple(
                  title = _("Throttle periodic notifications"),
                  help = _("This match option allows you to throttle periodic notifications after "
                           "a certain number of notifications have been created by the monitoring "
                           "core. If you for example select 10 as the beginning and 5 as the rate "
                           "then you will receive the notification 1 through 10 and then 15, 20, "
                           "25.. and so on."),
                  orientation = "float",
                  elements = [
                     Integer(
                         label = _("beginning from notifcation number"),
                         default_value = 10,
                         minvalue = 1,
                     ),
                     Integer(
                         label = _("send only every"),
                         default_value = 5,
                         unit = _("th notification"),
                         minvalue = 1,
                    )
                  ],
              )
            ),
            ( "match_sl",
              Tuple(
                title = _("Match service level"),
                help = _("Host or service must be in the following service level to get notification"),
                orientation = "horizontal",
                show_titles = False,
                elements = [
                  DropdownChoice(label = _("from:"),  choices = service_levels, prefix_values = True),
                  DropdownChoice(label = _(" to:"),  choices = service_levels, prefix_values = True),
                ],
              ),
            ),
            ( "match_host_event",
               ListChoice(
                    title = _("Match host event type"),
                    help = _("Select the host event types and transitions this rule should handle. Note: "
                             "If you activate this option and do <b>not</b> also specify service event "
                             "types then this rule will never hold for service notifications!"),
                    choices = [
                        ( 'rd', _("UP")          + u" ➤ " + _("DOWN")),
                        ( 'dr', _("DOWN")        + u" ➤ " + _("UP")),
                        ( 'ru', _("UP")          + u" ➤ " + _("UNREACHABLE")),
                        ( 'du', _("DOWN")        + u" ➤ " + _("UNREACHABLE")),
                        ( 'ud', _("UNREACHABLE") + u" ➤ " + _("DOWN")),
                        ( 'ur', _("UNREACHABLE") + u" ➤ " + _("UP")),
                        ( 'f', _("Start or end of flapping state")),
                        ( 's', _("Start or end of a scheduled downtime ")),
                        ( 'x', _("Acknowledgement of host problem")),
                    ],
                    default_value = [ 'rd', 'dr', 'f', 's', 'x' ],
              )
            ),
            ( "match_service_event",
                ListChoice(
                    title = _("Match service event type"),
                     help  = _("Select the service event types and transitions this rule should handle. Note: "
                               "If you activate this option and do <b>not</b> also specify host event "
                               "types then this rule will never hold for host notifications!"),
                    choices = [
                        ( 'rw', _("OK")      + u" ➤ " + _("WARN")),
                        ( 'rc', _("OK")      + u" ➤ " + _("CRIT")),
                        ( 'ru', _("OK")      + u" ➤ " + _("UNKNOWN")),

                        ( 'wr', _("WARN")    + u" ➤ " + _("OK")),
                        ( 'wc', _("WARN")    + u" ➤ " + _("CRIT")),
                        ( 'wu', _("WARN")    + u" ➤ " + _("UNKNOWN")),

                        ( 'cr', _("CRIT")    + u" ➤ " + _("OK")),
                        ( 'cw', _("CRIT")    + u" ➤ " + _("WARN")),
                        ( 'cu', _("CRIT")    + u" ➤ " + _("UNKNOWN")),

                        ( 'ur', _("UNKNOWN") + u" ➤ " + _("OK")),
                        ( 'uw', _("UNKNOWN") + u" ➤ " + _("WARN")),
                        ( 'uc', _("UNKNOWN") + u" ➤ " + _("CRIT")),

                        ( 'f', _("Start or end of flapping state")),
                        ( 's', _("Start or end of a scheduled downtime")),
                        ( 'x', _("Acknowledgement of service problem")),
                    ],
                    default_value = [ 'rw', 'rc', 'ru', 'wc', 'wu', 'uc', 'f', 's', 'x' ],
               )
             ),
             ( "match_ec",
               Alternative(
                   title = _("Event Console alerts"),
                   help = _("The Event Console can have events create notifications in Check_MK. "
                            "These notifications will be processed by the rule based notification "
                            "system of Check_MK. This matching option helps you distinguishing "
                            "and also gives you access to special event fields."),
                   style = "dropdown",
                   elements = [
                        FixedValue(False, title = _("Do not match Event Console alerts"), totext=""),
                        Dictionary(
                            title = _("Match only Event Console alerts"),
                            elements = [
                                ( "match_rule_id",
                                  ID(title = _("Match event rule"), label = _("Rule ID:"), size=12, allow_empty=False),
                                ),
                                ( "match_priority",
                                  Tuple(
                                      title = _("Match syslog priority"),
                                      help = _("Define a range of syslog priorities this rule matches"),
                                      orientation = "horizontal",
                                      show_titles = False,
                                      elements = [
                                         DropdownChoice(label = _("from:"), choices = mkeventd.syslog_priorities, default_value = 4),
                                         DropdownChoice(label = _(" to:"),   choices = mkeventd.syslog_priorities, default_value = 0),
                                      ],
                                  ),
                                ),
                                ( "match_facility",
                                  DropdownChoice(
                                      title = _("Match syslog facility"),
                                      help = _("Make the rule match only if the event has a certain syslog facility. "
                                               "Messages not having a facility are classified as <tt>user</tt>."),
                                      choices = mkeventd.syslog_facilities,
                                  )
                                ),
                                ( "match_comment",
                                  RegExpUnicode(
                                      title = _("Match event comment"),
                                      help = _("This is a regular expression for matching the event's comment."),
                                  )
                                ),
                            ]
                        )
                   ]
               )
             )
        ] +
        section_contacts +
        [
            # Notification
            ( "notify_plugin",
              vs_notification_methods(),
            ),

            # ( "notify_method",
            #   Alternative(
            #       title = _("Parameters / Cancelling"),
            #       style = "dropdown",
            #       elements = [
            #           ListOfStrings(
            #               title = _("Call the script with the following parameters"),
            #               valuespec = TextUnicode(size = 24),
            #               orientation = "horizontal",
            #           ),
            #           FixedValue(
            #               value = None,
            #               title = _("Cancel all previous notifications with this method"),
            #               totext = "",
            #           ),
            #       ]
            #   )
            # ),

            ( "bulk",
              Dictionary(
                  title = _("Notification Bulking"),
                  help = _("Enabling the bulk notifications will collect several subsequent notifications "
                           "for the same contact into one single notification, which lists of all the "
                           "actual problems, e.g. in a single emails. This cuts down the number of notifications "
                           "in cases where many (related) problems occur within a short time."),
                  elements = [
                    ( "interval",
                      Age(
                          title = _("Time horizon"),
                          label = _("Bulk up to"),
                          help = _("Notifications are kept back for bulking at most for this time."),
                          default_value = 60,
                      )
                    ),
                    ( "count",
                      Integer(
                          title = _("Maximum bulk size"),
                          label = _("Bulk up to"),
                          unit  = _("Notifications"),
                          help = _("At most that many Notifications are kept back for bulking. A value of "
                                   "1 essentially turns of notification bulking."),
                          default_value = 1000,
                          minvalue = 1,
                      ),
                    ),
                    ( "groupby",
                      vs_notification_bulkby(),
                    ),
                    ( "groupby_custom",
                      ListOfStrings(
                          valuespec = ID(),
                          orientation = "horizontal",
                          title = _("Create separate notification bulks for different values of the following custom macros"),
                          help = _("If you enter the names of host/service-custom macros here then for each different "
                                   "combination of values of those macros a separate bulk will be created. This can be used "
                                   "in combination with the grouping by folder, host etc. Omit any leading underscore. "
                                   "<b>Note</b>: If you are using "
                                   "Nagios as a core you need to make sure that the values of the required macros are "
                                   "present in the notification context. This is done in <tt>check_mk_templates.cfg</tt>. If you "
                                   "macro is <tt>_FOO</tt> then you need to add the variables <tt>NOTIFY_HOST_FOO</tt> and "
                                   "<tt>NOTIFY_SERVICE_FOO</tt>."),
                    )),
                  ],
                  columns = 1,
                  optional_keys = False,
            ),
          ),

        ],
        optional_keys = [ "match_folder", "match_hosttags", "match_hostgroups", "match_hosts", "match_exclude_hosts",
                          "match_services", "match_servicegroups", "match_contactgroups", "match_exclude_services", "match_plugin_output",
                          "match_timeperiod", "match_escalation", "match_escalation_throttle",
                          "match_sl", "match_host_event", "match_service_event", "match_ec",
                          "match_checktype", "bulk", "contact_users", "contact_groups", "contact_emails" ],
        headers = [
            ( _("General Properties"), [ "description", "comment", "disabled", "allow_disable" ] ),
            ( _("Notification Method"), [ "notify_plugin", "notify_method", "bulk" ] ),]
            + contact_headers
            + [
            ( _("Conditions"),         [ "match_folder", "match_hosttags", "match_hostgroups", "match_hosts", "match_exclude_hosts",
                                         "match_services", "match_servicegroups", "match_contactgroups", "match_exclude_services", "match_plugin_output",
                                         "match_checktype", "match_timeperiod",
                                         "match_escalation", "match_escalation_throttle",
                                         "match_sl", "match_host_event", "match_service_event", "match_ec" ] ),
        ],
        render = "form",
        form_narrow = True,
        validate = validate_notification_rule,
    )

def validate_notification_rule(rule, varprefix):
    if "bulk" in rule and rule["notify_plugin"][1] == None:
        raise MKUserError(varprefix + "_p_bulk_USE",
             _("It does not make sense to add a bulk configuration for cancelling rules."))

    if "bulk" in rule:
        if rule["notify_plugin"][0]:
            info = load_notification_scripts()[rule["notify_plugin"][0]]
            if not info["bulk"]:
                raise MKUserError(varprefix + "_p_notify_plugin",
                      _("The notification script %s does not allow bulking.") % info["title"])
        else:
            raise MKUserError(varprefix + "_p_notify_plugin",
                  _("Legacy ASCII Emails do not support bulking. You can either disable notification "
                    "bulking or choose another notification plugin which allows bulking."))


def render_notification_rules(rules, userid="", show_title=False, show_buttons=True,
                              analyse=False, start_nr=0, profilemode=False):
    if not rules:
        html.message(_("You have not created any rules yet."))

    if rules:
        if not show_title:
            title = ""
        elif profilemode:
            title = _("Notification rules")
        elif userid:
            url = html.makeuri([("mode", "user_notifications"), ("user", userid)])
            html.plug()
            html.icon_button(url, _("Edit this user's notifications"), "edit")
            code = html.drain()
            html.unplug()
            title = code + _("Notification rules of user %s") % userid
        else:
            title = _("Global notification rules")
        table.begin(title = title, limit = None)

        if analyse:
            analyse_rules, analyse_plugins = analyse

        # have_match = False
        for nr, rule in enumerate(rules):
            table.row()

            # Analyse
            if analyse:
                table.cell(css="buttons")
                what, anarule, reason = analyse_rules[nr + start_nr]
                if what == "match":
                    html.icon(_("This rule matches"), "rulematch")
                elif what == "miss":
                    html.icon(_("This rule does not match: %s") % reason, "rulenmatch")

            if profilemode:
                listmode = "user_notifications_p"
            elif userid:
                listmode = "user_notifications"
            else:
                listmode = "notifications"

            if show_buttons:
                anavar = html.var("analyse", "")
                delete_url = make_action_link([("mode", listmode), ("user", userid), ("_delete", nr)])
                top_url    = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr), ("_where", 0)])
                bottom_url = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr), ("_where", len(rules)-1)])
                up_url     = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr), ("_where", nr-1)])
                down_url   = make_action_link([("mode", listmode), ("analyse", anavar), ("user", userid), ("_move", nr), ("_where", nr+1)])
                suffix = profilemode and "_p" or ""
                edit_url   = make_link([("mode", "notification_rule" + suffix), ("edit", nr), ("user", userid)])
                clone_url  = make_link([("mode", "notification_rule" + suffix), ("clone", nr), ("user", userid)])

                table.cell(_("Actions"), css="buttons")
                html.icon_button(edit_url, _("Edit this notification rule"), "edit")
                html.icon_button(clone_url, _("Create a copy of this notification rule"), "clone")
                html.icon_button(delete_url, _("Delete this notification rule"), "delete")
                if not rule is rules[0]:
                    html.icon_button(top_url, _("Move this notification rule to the top"), "top")
                    html.icon_button(up_url, _("Move this notification rule one position up"), "up")
                else:
                    html.empty_icon_button()
                    html.empty_icon_button()

                if not rule is rules[-1]:
                    html.icon_button(down_url, _("Move this notification rule one position down"), "down")
                    html.icon_button(bottom_url, _("Move this notification rule to the bottom"), "bottom")
                else:
                    html.empty_icon_button()
                    html.empty_icon_button()
            else:
                table.cell("", css="buttons")
                for x in range(7):
                    html.empty_icon_button()

            table.cell("", css="narrow")
            if rule.get("disabled"):
                html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
            else:
                html.empty_icon_button()

            notify_method = rule["notify_plugin"]
            # catch rules with empty notify_plugin key
            # TODO Mayby this should be avoided somewhere else ( e.g. rule editor)
            if not notify_method:
                notify_method = ( None, [] )
            notify_plugin = notify_method[0]

            table.cell(_("Type"), css="narrow")
            if notify_method[1] == None:
                html.icon(_("Cancel notifications for this plugin type"), "notify_cancel")
            else:
                html.icon(_("Create a notification"), "notify_create")

            table.cell(_("Plugin"), notify_plugin or _("Plain Email"), css="narrow nowrap")

            table.cell(_("Bulk"), css="narrow")
            if "bulk" in rule:
                html.icon(_("This rule configures bulk notifications."), "bulk")

            table.cell(_("Description"), rule["description"])

            table.cell(_("Contacts"))
            infos = []
            if rule.get("contact_object"):
                infos.append(_("all contacts of the notified object"))
            if rule.get("contact_all"):
                infos.append(_("all users"))
            if rule.get("contact_all_with_email"):
                infos.append(_("all users with and email address"))
            if rule.get("contact_users"):
                infos.append(_("users: ") + (", ".join(rule["contact_users"])))
            if rule.get("contact_groups"):
                infos.append(_("contact groups: ") + (", ".join(rule["contact_groups"])))
            if rule.get("contact_emails"):
                infos.append(_("email addresses: ") + (", ".join(rule["contact_emails"])))
            if not infos:
                html.write("<i>%s</i>" % _("(no one)"))
            else:
                for line in infos:
                    html.write("&bullet; %s<br>" % line)

            table.cell(_("Conditions"))
            num_conditions = len([key for key in rule if key.startswith("match_")])
            if num_conditions:
                html.write(_("%d conditions") % num_conditions)
            else:
                html.write("<i>%s</i>" % _("(no conditions)"))

        table.end()



def mode_notifications(phase):
    options         = config.load_user_file("notification_display_options", {})
    show_user_rules = options.get("show_user_rules", False)
    show_backlog    = options.get("show_backlog", False)
    show_bulks      = options.get("show_bulks", False)

    if phase == "title":
        return _("Notification configuration")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Rule"), make_link([("mode", "notification_rule")]), "new")
        if show_user_rules:
            html.context_button(_("Hide user rules"), html.makeactionuri([("_show_user", "")]), "users")
        else:
            html.context_button(_("Show user rules"), html.makeactionuri([("_show_user", "1")]), "users")

        if show_backlog:
            html.context_button(_("Hide Analysis"), html.makeactionuri([("_show_backlog", "")]), "analyze")
        else:
            html.context_button(_("Analyse"), html.makeactionuri([("_show_backlog", "1")]), "analyze")

        if show_bulks:
            html.context_button(_("Hide Bulks"), html.makeactionuri([("_show_bulks", "")]), "bulk")
        else:
            html.context_button(_("Show Bulks"), html.makeactionuri([("_show_bulks", "1")]), "bulk")

        return

    rules = load_notification_rules()

    if phase == "action":
        if html.has_var("_show_user"):
            if html.check_transaction():
                options["show_user_rules"] = not not html.var("_show_user")
                config.save_user_file("notification_display_options", options)

        elif html.has_var("_show_backlog"):
            if html.check_transaction():
                options["show_backlog"] = not not html.var("_show_backlog")
                config.save_user_file("notification_display_options", options)

        elif html.has_var("_show_bulks"):
            if html.check_transaction():
                options["show_bulks"] = not not html.var("_show_bulks")
                config.save_user_file("notification_display_options", options)

        elif html.has_var("_replay"):
            if html.check_transaction():
                nr = int(html.var("_replay"))
                result = check_mk_local_automation("notification-replay", [str(nr)], None)
                return None, _("Replayed notifiation number %d") % (nr + 1)

        elif html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = rules[nr]
            c = wato_confirm(_("Confirm notification rule deletion"),
                             _("Do you really want to delete the notification rule <b>%d</b> <i>%s</i>?" %
                               (nr, rule.get("description",""))))
            if c:
                log_pending(SYNC, None, "notification-delete-rule", _("Deleted notification rule %d") % nr)
                del rules[nr]
                save_notification_rules(rules)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = int(html.var("_move"))
                to_pos = int(html.var("_where"))
                rule = rules[from_pos]
                del rules[from_pos] # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                save_notification_rules(rules)
                log_pending(SYNC, None, "notification-move-rule", _("Changed position of notification rule %d") % from_pos)
        return

    # Check setting of global notifications. Are they enabled? If not, display
    # a warning here. Note: this is a main.mk setting, so we cannot access this
    # directly.
    current_settings = load_configuration_settings()
    if not current_settings.get("enable_rulebased_notifications"):
        url = 'wato.py?mode=edit_configvar&varname=enable_rulebased_notifications'
        html.show_warning(
           _("<b>Warning</b><br><br>Rule based notifications are disabled in your global settings. "
             "The rules that you edit here will have affect only on notifications that are "
             "created by the Event Console. Normal monitoring alerts will <b>not</b> use the "
             "rule based notifications now."
             "<br><br>"
             "You can change this setting <a href=\"%s\">here</a>.") % url)

    # Do not warn for missing fallback email address anymore. It might be a
    # useful feature to not have one - after all.
    ## elif not current_settings.get("notification_fallback_email"):
    ##     url = 'wato.py?mode=edit_configvar&varname=notification_fallback_email'
    ##     html.show_warning(
    ##       _("<b>Warning</b><br><br>You haven't configured a fallback email address "
    ##         "in case of a problem in your notification rules. Please configure "
    ##         "one <a href=\"%s\">here</a>.") % url)

    if show_bulks:
        if not render_bulks(only_ripe = False): # Warn if there are unsent bulk notificatios
            html.message(_("Currently there are no unsent notification bulks pending."))
    else:
        render_bulks(only_ripe = True) # Warn if there are unsent bulk notificatios

    # Show recent notifications. We can use them for rule analysis
    if show_backlog:
        try:
            backlog = eval(file(defaults.var_dir + "/notify/backlog.mk").read())
        except:
            backlog = []

        if backlog:
            table.begin(table_id = "backlog", title = _("Recent notifications (for analysis)"), sortable=False)
            for nr, entry in enumerate(backlog):
                table.row()
                table.cell(css="buttons")

                analyse_url = html.makeuri([("analyse", str(nr))])
                context = entry.items()
                context.sort()
                tooltip = "".join(("%s: %s\n" % e).decode('utf-8') for e in context)
                html.icon_button(analyse_url, _("Analyze ruleset with this notification:\n%s" % tooltip), "analyze")
                replay_url = html.makeactionuri([("_replay", str(nr))])
                html.icon_button(replay_url, _("Replay this notification, send it again!"), "replay")
                if html.var("analyse") and nr == int(html.var("analyse")):
                    html.icon(_("You are analysing this notification"), "rulematch")

                table.cell(_("Nr."), nr+1, css="number")
                if "MICROTIME" in entry:
                    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(entry["MICROTIME"]) / 1000000.0))
                else:
                    date = entry.get("SHORTDATETIME") or \
                           entry.get("LONGDATETIME") or \
                           entry.get("DATE") or \
                           _("Unknown date")

                table.cell(_("Date/Time"), date, css="nobr")
                nottype = entry.get("NOTIFICATIONTYPE", "")
                table.cell(_("Type"), nottype)

                if nottype in [ "PROBLEM", "RECOVERY" ]:
                    if entry.get("SERVICESTATE"):
                        statename = _(entry["SERVICESTATE"][:4])
                        state = entry["SERVICESTATEID"]
                        css = "state svcstate state%s" % state
                    else:
                        statename = _(entry.get("HOSTSTATE")[:4])
                        state = entry["HOSTSTATEID"]
                        css = "state hstate state%s" % state
                    table.cell(_("State"), statename, css=css)
                elif nottype.startswith("DOWNTIME"):
                    table.cell(_("State"))
                    html.icon(_("Downtime"), "downtime")
                elif nottype.startswith("ACK"):
                    table.cell(_("State"))
                    html.icon(_("Acknowledgement"), "ack")
                elif nottype.startswith("FLAP"):
                    table.cell(_("State"))
                    html.icon(_("Flapping"), "flapping")
                else:
                    table.cell(_("State"), "")

                table.cell(_("Host"), entry.get("HOSTNAME", ""))
                table.cell(_("Service"), entry.get("SERVICEDESC", ""))
                output = entry.get("SERVICEOUTPUT", entry.get("HOSTOUTPUT"))
                table.cell(_("Plugin output"), output)
            table.end()

    # Do analysis
    if html.var("analyse"):
        nr = int(html.var("analyse"))
        analyse = check_mk_local_automation("notification-analyse", [str(nr)], None)
    else:
        analyse = False

    start_nr = 0
    render_notification_rules(rules, show_title = True, analyse=analyse, start_nr = start_nr)
    start_nr += len(rules)

    if options.get("show_user_rules"):
        users = userdb.load_users()
        userids = users.keys()
        userids.sort() # Create same order as modules/notification.py
        for userid in userids:
            user = users[userid]
            rules = user.get("notification_rules", [])
            if rules:
                render_notification_rules(rules, userid, show_title = True, show_buttons = False, analyse=analyse, start_nr = start_nr)
                start_nr += len(rules)

    if analyse:
        table.begin(table_id = "plugins", title = _("Resulting notifications"))
        for contact, plugin, parameters, bulk in analyse[1]:
            table.row()
            if contact.startswith('mailto:'):
                contact = contact[7:] # strip of fake-contact mailto:-prefix
            table.cell(_("Recipient"), contact)
            table.cell(_("Plugin"), vs_notification_scripts().value_to_text(plugin))
            table.cell(_("Plugin parameters"), ", ".join(parameters))
            table.cell(_("Bulking"))
            if bulk:
                html.write(_("Time horizon") + ": " + Age().value_to_text(bulk["interval"]))
                html.write(", %s: %d" % (_("Maximum count"), bulk["count"]))
                html.write(", %s %s" % (_("group by"), vs_notification_bulkby().value_to_text(bulk["groupby"])))

        table.end()


def render_bulks(only_ripe):
    bulks = check_mk_local_automation("notification-get-bulks", [ only_ripe and "1" or "0" ], None)
    if bulks:
        if only_ripe:
            table.begin(title = _("Overdue bulk notifications!"))
        else:
            table.begin(title = _("Open bulk notifications"))

        for dir, age, interval, maxcount, uuids in bulks:
            dirparts = dir.split("/")
            contact = dirparts[-3]
            method = dirparts[-2]
            bulk_id = dirparts[-1].split(",", 2)[-1]
            table.row()
            table.cell(_("Contact"), contact)
            table.cell(_("Method"), method)
            table.cell(_("Bulk ID"), bulk_id)
            table.cell(_("Max. Age"), "%d %s" % (interval, _("sec")), css="number")
            table.cell(_("Age"), "%d %s" % (age, _("sec")), css="number")
            if age >= interval:
                html.icon(_("Age of oldest notification is over maximum age"), "warning")
            table.cell(_("Max. Count"), str(maxcount), css="number")
            table.cell(_("Count"), str(len(uuids)), css="number")
            if len(uuids) >= maxcount:
                html.icon(_("Number of notifications exceeds maximum allowed number"), "warning")
        table.end()
        return True
    else:
        return False



# Similar like mode_notifications, but just for the user specific notification table
def mode_user_notifications(phase, profilemode):
    if profilemode:
        userid = config.user_id
        title = _("Your personal notification rules")
        config.need_permission("general.edit_notifications")
    else:
        userid = html.var("user")
        title = _("Custom notification table for user ") + userid

    if phase == "title":
        return title

    users = userdb.load_users(lock = phase == 'action')
    user = users[userid]
    rules = user.setdefault("notification_rules", [])

    if phase == "buttons":
        if profilemode:
            html.context_button(_("Profile"), "user_profile.py", "back")
            html.context_button(_("New Rule"), make_link([("mode", "notification_rule_p")]), "new")
        else:
            html.context_button(_("All Users"), make_link([("mode", "users")]), "back")
            html.context_button(_("User Properties"), make_link([("mode", "edit_user"), ("edit", userid)]), "edit")
            html.context_button(_("New Rule"), make_link([("mode", "notification_rule"), ("user", userid)]), "new")
        return

    elif phase == "action":
        if html.has_var("_delete"):
            nr = int(html.var("_delete"))
            rule = rules[nr]
            c = wato_confirm(_("Confirm notification rule deletion"),
                             _("Do you really want to delete the notification rule <b>%d</b> <i>%s</i>?" %
                               (nr, rule.get("description",""))))
            if c:
                log_pending(SYNC, None, "notification-delete-user-rule", _("Deleted notification rule %d of user %s") %
                            (nr, userid))
                del rules[nr]
                userdb.save_users(users)
            elif c == False:
                return ""
            else:
                return

        elif html.has_var("_move"):
            if html.check_transaction():
                from_pos = int(html.var("_move"))
                to_pos = int(html.var("_where"))
                rule = rules[from_pos]
                del rules[from_pos] # make to_pos now match!
                rules[to_pos:to_pos] = [rule]
                userdb.save_users(users)
                log_pending(SYNC, None, "notification-move-user-rule", _("Changed position of notification rule %d of user %s") %
                       (from_pos, userid))
        return

    rules = user.get("notification_rules", [])
    render_notification_rules(rules, userid, profilemode = profilemode)


def mode_notification_rule(phase, profilemode):
    edit_nr = int(html.var("edit", "-1"))
    clone_nr = int(html.var("clone", "-1"))
    if profilemode:
        userid = config.user_id
        config.need_permission("general.edit_notifications")
    else:
        userid = html.var("user", "")

    if userid and not profilemode:
        suffix = _(" for user ") + html.attrencode(userid)
    else:
        suffix = ""

    new = edit_nr < 0

    if phase == "title":
        if new:
            return _("Create new notification rule") + suffix
        else:
            return _("Edit notification rule %d") % edit_nr + suffix

    elif phase == "buttons":
        if profilemode:
            html.context_button(_("All Rules"), make_link([("mode", "user_notifications_p")]), "back")
        else:
            html.context_button(_("All Rules"), make_link([("mode", "notifications"), ("userid", userid)]), "back")
        return

    if userid:
        users = userdb.load_users(lock = phase == 'action')
        user = users[userid]
        rules = user.setdefault("notification_rules", [])
    else:
        rules = load_notification_rules()

    if new:
        if clone_nr >= 0 and not html.var("_clear"):
            rule = {}
            rule.update(rules[clone_nr])
        else:
            rule = {}
    else:
        rule = rules[edit_nr]

    vs = vs_notification_rule(userid)

    if phase == "action":
        if not html.check_transaction():
            return "notifications"

        rule = vs.from_html_vars("rule")
        if userid:
            rule["contact_users"] = [ userid ] # Force selection of our user

        vs.validate_value(rule, "rule")

        if new and clone_nr >= 0:
            rules[clone_nr:clone_nr] = [ rule ]
        elif new:
            rules[0:0] = [ rule ]
        else:
            rules[edit_nr] = rule

        if userid:
            userdb.save_users(users)
        else:
            save_notification_rules(rules)

        if new:
            log_pending(SYNC, None, "new-notification-rule", _("Created new notification rule") + suffix)
        else:
            log_pending(SYNC, None, "edit-notification-rule", _("Changed notification rule %d") % edit_nr + suffix)
        if profilemode:
            return "user_notifications_p"
        elif userid:
            return "user_notifications"
        else:
            return "notifications"


    html.begin_form("rule", method = "POST")
    vs.render_input("rule", rule)
    vs.set_focus("rule")
    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()





#.
#   .--Timeperiods---------------------------------------------------------.
#   |      _____ _                                _           _            |
#   |     |_   _(_)_ __ ___   ___ _ __   ___ _ __(_) ___   __| |___        |
#   |       | | | | '_ ` _ \ / _ \ '_ \ / _ \ '__| |/ _ \ / _` / __|       |
#   |       | | | | | | | | |  __/ |_) |  __/ |  | | (_) | (_| \__ \       |
#   |       |_| |_|_| |_| |_|\___| .__/ \___|_|  |_|\___/ \__,_|___/       |
#   |                            |_|                                       |
#   +----------------------------------------------------------------------+
#   | Modes for managing Nagios' timeperiod definitions.                   |
#   '----------------------------------------------------------------------'

def mode_timeperiods(phase):
    if phase == "title":
        return _("Time Periods")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Timeperiod"), make_link([("mode", "edit_timeperiod")]), "new")
        html.context_button(_("Import iCalendar"), make_link([("mode", "import_ical")]), "ical")
        return

    timeperiods = load_timeperiods()

    if phase == "action":
        delname = html.var("_delete")
        if delname and html.transaction_valid():
            usages = find_usages_of_timeperiod(delname)
            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this timeperiod."),
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            c = wato_confirm(_("Confirm deletion of time period %s") % delname,
                  _("Do you really want to delete the time period '%s'? I've checked it: "
                    "it is not being used by any rule or user profile right now.") % delname)
            if c:
                del timeperiods[delname]
                save_timeperiods(timeperiods)
                log_pending(SYNCRESTART, None, "edit-timeperiods", _("Deleted timeperiod %s") % delname)
            elif c == False:
                return ""
        return None


    table.begin("timeperiods", empty_text = _("There are no timeperiods defined yet."))
    names = timeperiods.keys()
    names.sort()
    for name in names:
        table.row()

        timeperiod = timeperiods[name]
        edit_url     = make_link([("mode", "edit_timeperiod"), ("edit", name)])
        delete_url   = make_action_link([("mode", "timeperiods"), ("_delete", name)])

        table.cell(_("Actions"), css="buttons")
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), timeperiod.get("alias", ""))
    table.end()



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
    out = create_user_file(root_dir + "timeperiods.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("timeperiods.update(%s)\n" % pprint.pformat(timeperiods))

class ExceptionName(TextAscii):
    def __init__(self, **kwargs):
        kwargs["regex"] = "^[-a-z0-9A-Z /]*$"
        kwargs["regex_error"] = _("This is not a valid Nagios timeperiod day specification.")
        kwargs["allow_empty"] = False
        TextAscii.__init__(self, **kwargs)

    def validate_value(self, value, varprefix):
        if value in [ "monday", "tuesday", "wednesday", "thursday",
                       "friday", "saturday", "sunday" ]:
            raise MKUserError(varprefix, _("You cannot use weekday names (%s) in exceptions" % value))
        if value in [ "name", "alias", "timeperiod_name", "register", "use", "exclude" ]:
            raise MKUserError(varprefix, _("<tt>%s</tt> is a reserved keyword."))
        TextAscii.validate_value(self, value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)

class MultipleTimeRanges(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._num_columns = kwargs.get("num_columns", 3)
        self._rangevs = TimeofdayRange()

    def canonical_value(self):
        return [ ((0,0), (24,0)), None, None ]

    def render_input(self, varprefix, value):
        for c in range(0, self._num_columns):
            if c:
                html.write(" &nbsp; ")
            if c < len(value):
                v = value[c]
            else:
                v = self._rangevs.canonical_value()
            self._rangevs.render_input(varprefix + "_%d" % c, v)

    def value_to_text(self, value):
        parts = []
        for v in value:
            parts.append(self._rangevs.value_to_text(v))
        return ", ".join(parts)

    def from_html_vars(self, varprefix):
        value = []
        for c in range(0, self._num_columns):
            v = self._rangevs.from_html_vars(varprefix + "_%d" % c)
            if v != None:
                value.append(v)
        return value

    def validate_value(self, value, varprefix):
        for c, v in enumerate(value):
            self._rangevs.validate_value(v, varprefix + "_%d" % c)
        ValueSpec.custom_validate(self, value, varprefix)

# Check, if timeperiod tpa excludes or is tpb
def timeperiod_excludes(timeperiods, tpa_name, tpb_name):
    if tpa_name == tpb_name:
        return True

    tpa = timeperiods[tpa_name]
    for ex in tpa.get("exclude", []):
        if ex == tpb_name:
            return True
        if timeperiod_excludes(timeperiods, ex, tpb_name):
            return True
    return False

def validate_ical_file(value, varprefix):
    filename, ty, content = value
    if not filename.endswith('.ics'):
        raise MKUserError(varprefix, _('The given file does not seem to be a valid iCalendar file. '
                                       'It needs to have the file extension <tt>.ics</tt>.'))

    if not content.startswith('BEGIN:VCALENDAR'):
        raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))

    if not content.startswith('END:VCALENDAR'):
        raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))

# Returns a dictionary in the format:
# {
#   'name'   : '...',
#   'descr'  : '...',
#   'events' : [
#       {
#           'name': '...',
#           'date': '...',
#       },
#   ],
# }
#
# Relevant format specifications:
#   http://tools.ietf.org/html/rfc2445
#   http://tools.ietf.org/html/rfc5545
def parse_ical(ical_blob, horizon=10, times=(None, None, None)):
    ical = {'raw_events': []}

    def get_params(key):
        if ';' in key:
            return dict([ p.split('=', 1) for p in key.split(';')[1:] ])
        return {}

    def parse_date(params, val):
        # First noprmalize the date value to make it easier parsable later
        if 'T' not in val and params.get('VALUE') == 'DATE':
            val += 'T000000' # add 00:00:00 to date specification

        return list(time.strptime(val, '%Y%m%dT%H%M%S'))

    # First extract the relevant information from the file
    in_event = False
    event    = {}
    for l in ical_blob.split('\n'):
        line = l.strip()
        if not line:
            continue
        try:
            key, val = line.split(':', 1)
        except ValueError:
            raise Exception('Failed to parse line: "%s"' % line)

        if key == 'X-WR-CALNAME':
            ical['name'] = val
        elif key == 'X-WR-CALDESC':
            ical['descr'] = val

        elif line == 'BEGIN:VEVENT':
            in_event = True
            event = {} # create new event

        elif line == 'END:VEVENT':
            # Finish the current event
            ical['raw_events'].append(event)
            in_event = False

        elif in_event:
            if key.startswith('DTSTART'):
                params = get_params(key)
                event['start'] = parse_date(params, val)

            elif key.startswith('DTEND'):
                params = get_params(key)
                event['end'] = parse_date(params, val)

            elif key == 'RRULE':
                event['recurrence'] = dict([ p.split('=', 1) for p in val.split(';') ])

            elif key == 'SUMMARY':
                event['name'] = val

    def next_occurrence(start, now, freq):
        # convert struct_time to list to be able to modify it,
        # then set it to the next occurence
        t = start[:]

        if freq == 'YEARLY':
            t[0] = now[0]+1 # add 1 year
        elif freq == 'MONTHLY':
            if now[1] + 1 > 12:
                t[0] = now[0]+1
                t[1] = now[1] + 1 - 12
            else:
                t[0] = now[0]
                t[1] = now[1] + 1
        else:
            raise Exception('The frequency "%s" is currently not supported' % freq)
        return t

    # Now resolve recurring events starting from 01.01 of current year
    # Non-recurring events are simply copied
    resolved = []
    now  = list(time.strptime(str(time.localtime().tm_year-1), "%Y"))
    last = now[:]
    last[0] += horizon+1 # update year to horizon
    for event in ical['raw_events']:
        if 'recurrence' in event and event['start'] < now:
            rule     = event['recurrence']
            freq     = rule['FREQ']
            interval = int(rule.get('INTERVAL', 1))
            cur      = now
            while cur < last:
                cur = next_occurrence(event['start'], cur, freq)
                resolved.append({
                    'name'  : event['name'],
                    'date'  : time.strftime('%Y-%m-%d', cur),
                })
        else:
            resolved.append({
                'name' : event['name'],
                'date' : time.strftime('%Y-%m-%d', event['start'])
            })

    ical['events'] = sorted(resolved)

    return ical

# Displays a dialog for uploading an ical file which will then
# be used to generate timeperiod exceptions etc. and then finally
# open the edit_timeperiod page to create a new timeperiod using
# these information
def mode_timeperiod_import_ical(phase):
    if phase == "title":
        return _("Import iCalendar File to create a Timeperiod")

    elif phase == "buttons":
        html.context_button(_("All Timeperiods"), make_link([("mode", "timeperiods")]), "back")
        return

    vs_ical = Dictionary(
        title = _('Import iCalendar File'),
        render = "form",
        optional_keys = None,
        elements = [
            ('file', FileUpload(
                title = _('iCalendar File'),
                help = _("Select an iCalendar file (<tt>*.ics</tt>) from your PC"),
                allow_empty = False,
                custom_validate = validate_ical_file,
            )),
            ('horizon', Integer(
                title = _('Time horizon for repeated events'),
                help = _("When the iCalendar file contains definitions of repeating events, these repeating "
                         "events will be resolved to single events for the number of years you specify here."),
                minvalue = 0,
                maxvalue = 50,
                default_value = 10,
                unit = _('years'),
                allow_empty = False,
            )),
            ('times', Optional(
                MultipleTimeRanges(
                    default_value = [None, None, None],
                ),
                title = _('Use specific times'),
                label = _('Use specific times instead of whole day'),
                help = _("When you specify explicit time definitions here, these will be added to each "
                         "date which is added to the resulting time period. By default the whole day is "
                         "used."),
            )),
        ]
    )

    ical = {}

    if phase == "action":
        if html.check_transaction():
            ical = vs_ical.from_html_vars("ical")
            vs_ical.validate_value(ical, "ical")

            filename, ty, content = ical['file']

            try:
                data = parse_ical(content, ical['horizon'], ical['times'])
            except Exception, e:
                if config.debug:
                    raise
                raise MKUserError('ical_file', _('Failed to parse file: %s') % e)

            html.set_var('alias', data.get('descr', data.get('name', filename)))

            for day in [ "monday", "tuesday", "wednesday", "thursday",
                         "friday", "saturday", "sunday" ]:
                html.set_var('%s_0_from' % day, '')
                html.set_var('%s_0_until' % day, '')

            html.set_var('except_count', len(data['events']))
            for index, event in enumerate(data['events']):
                index += 1
                html.set_var('except_%d_0' % index, event['date'])
                html.set_var('except_indexof_%d' % index, index)
                if ical['times']:
                    for n in range(3):
                        if ical['times'][n]:
                            html.set_var('except_%d_1_%d_from' % (index, n+1), ical['times'][n][0])
                            html.set_var('except_%d_1_%d_until' % (index, n+1), ical['times'][n][1])
            return "edit_timeperiod"
        return

    html.write('<p>%s</p>' %
        _('This page can be used to generate a new timeperiod definition based '
          'on the appointments of an iCalendar (<tt>*.ics</tt>) file. This import is normally used '
          'to import events like holidays, therefore only single whole day appointments are '
          'handled by this import.'))

    html.begin_form("import_ical", method="POST")
    vs_ical.render_input("ical", ical)
    forms.end()
    html.button("upload", _("Import"))
    html.hidden_fields()
    html.end_form()

def mode_edit_timeperiod(phase):
    num_columns = 3
    timeperiods = load_timeperiods()
    name = html.var("edit") # missing -> new group
    new = name == None

    # ValueSpec for the list of Exceptions
    vs_ex = ListOf(
        Tuple(
            orientation = "horizontal",
            show_titles = False,
            elements = [
                ExceptionName(),
                MultipleTimeRanges()]
        ),
        movable = False,
        add_label = _("Add Exception"))

    # ValueSpec for excluded Timeperiods. We offer the list of
    # all other timeperiods - but only those that do not
    # exclude the current timeperiod (in order to avoid cycles)
    other_tps = []
    for tpname, tp in timeperiods.items():
        if not timeperiod_excludes(timeperiods, tpname, name):
            other_tps.append((tpname, tp.get("alias") or name))

    vs_excl = ListChoice(choices=other_tps)

    # convert Check_MK representation of range to ValueSpec-representation
    def convert_from_tod(tod):
        # "00:30" -> (0, 30)
        return tuple(map(int, tod.split(":")))

    def convert_from_range(range):
        # ("00:30", "10:17") -> ((0,30),(10,17))
        return tuple(map(convert_from_tod, range))

    def convert_to_tod(value):
        return "%02d:%02d" % value

    def convert_to_range(value):
        return tuple(map(convert_to_tod, value))

    def timeperiod_ranges(vp, keyname, new):
        ranges = timeperiod.get(keyname, [])
        value = []
        for range in ranges:
            value.append(convert_from_range(range))
        if len(value) == 0 and new:
            value.append(((0,0),(24,0)))

        html.write("<td>")
        MultipleTimeRanges().render_input(vp, value)
        html.write("</td>")

    def get_ranges(varprefix):
        value = MultipleTimeRanges().from_html_vars(varprefix)
        MultipleTimeRanges().validate_value(value, varprefix)
        return map(convert_to_range, value)

    if phase == "title":
        if new:
            return _("Create new time period")
        else:
            return _("Edit time period")

    elif phase == "buttons":
        html.context_button(_("All Timeperiods"), make_link([("mode", "timeperiods")]), "back")
        return

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

            unique, info = is_alias_used("timeperiods", name, alias)
            if not unique:
                raise MKUserError("alias", info)

            timeperiod.clear()

            # extract time ranges of weekdays
            for weekday, weekday_name in weekdays:
                ranges = get_ranges(weekday)
                if ranges:
                    timeperiod[weekday] = ranges
                elif weekday in timeperiod:
                    del timeperiod[weekday]

            # extract ranges for custom days
            exceptions = vs_ex.from_html_vars("except")
            vs_ex.validate_value(exceptions, "except")
            for exname, ranges in exceptions:
                timeperiod[exname] = map(convert_to_range, ranges)

            # extract excludes
            excludes = vs_excl.from_html_vars("exclude")
            vs_excl.validate_value(excludes, "exclude")
            if excludes:
                timeperiod["exclude"] = excludes

            if new:
                name = html.var("name")
                if len(name) == 0:
                    raise MKUserError("name", _("Please specify a name of the new timeperiod."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid timeperiod name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if name in timeperiods:
                    raise MKUserError("name", _("This name is already being used by another timeperiod."))
                if name == "24X7":
                    raise MKUserError("name", _("The time period name 24X7 cannot be used. It is always autmatically defined."))
                timeperiods[name] = timeperiod
                log_pending(SYNCRESTART, None, "edit-timeperiods", _("Created new time period %s" % name))
            else:
                log_pending(SYNCRESTART, None, "edit-timeperiods", _("Modified time period %s" % name))
            timeperiod["alias"] = alias
            save_timeperiods(timeperiods)
            return "timeperiods"
        return

    html.begin_form("timeperiod", method="POST")
    forms.header(_("Timeperiod"))

    # Name
    forms.section(_("Internal name"), simple = not new)
    if new:
        html.text_input("name")
        html.set_focus("name")
    else:
        html.write(name)

    # Alias
    if not new:
        alias = timeperiods[name].get("alias", "")
    else:
        alias = ""

    forms.section(_("Alias"))
    html.help(_("An alias or description of the timeperiod"))
    html.text_input("alias", alias, size = 81)
    if not new:
        html.set_focus("alias")

    # Week days
    forms.section(_("Weekdays"))
    html.help("For each weekday you can setup no, one or several "
               "time ranges in the format <tt>23:39</tt>, in which the time period "
               "should be active.")
    html.write("<table class=timeperiod>")

    for weekday, weekday_alias in weekdays:
        ranges = timeperiod.get(weekday)
        html.write("<tr><td class=name>%s</td>" % weekday_alias)
        timeperiod_ranges(weekday, weekday, new)
        html.write("</tr>")
    html.write("</table>")

    # Exceptions
    forms.section(_("Exceptions (from weekdays)"))
    html.help(_("Here you can specify exceptional time ranges for certain "
                "dates in the form YYYY-MM-DD which are used to define more "
                "specific definitions to override the times configured for the matching "
                "weekday."))

    exceptions = []
    for k in timeperiod:
        if k not in [ w[0] for w in weekdays ] and k not in [ "alias", "exclude" ]:
            exceptions.append((k, map(convert_from_range, timeperiod[k])))
    exceptions.sort()
    vs_ex.render_input("except", exceptions)

    # Excludes
    if other_tps:
        forms.section(_("Exclude"))
        html.help(_('You can use other timeperiod definitions to exclude the times '
                    'defined in the other timeperiods from this current timeperiod.'))
        vs_excl.render_input("exclude", timeperiod.get("exclude", []))


    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()


class TimeperiodSelection(ElementSelection):
    def __init__(self, **kwargs):
        ElementSelection.__init__(self, **kwargs)

    def get_elements(self):
        timeperiods = load_timeperiods()
        elements = dict([ ("24X7", _("Always")) ] + \
           [ (name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items() ])
        return elements

    def default_value(self):
        return "24x7"

# Check if a timeperiod is currently in use and cannot be deleted
# Returns a list of occurrances.
# Possible usages:
# - 1. rules: service/host-notification/check-period
# - 2. user accounts (notification period)
# - 3. excluded by other timeperiods
def find_usages_of_timeperiod(tpname):

    # Part 1: Rules
    used_in = []
    for varname, ruleset in load_all_rulesets().items():
        rulespec = g_rulespecs[varname]
        if isinstance(rulespec.get("valuespec"), TimeperiodSelection):
            for folder, rule in ruleset:
                value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
                if value == tpname:
                    used_in.append(("%s: %s" % (_("Ruleset"), g_rulespecs[varname]["title"]),
                                   make_link([("mode", "edit_ruleset"), ("varname", varname)])))
                    break

    # Part 2: Users
    for userid, user in userdb.load_users().items():
        tp = user.get("notification_period")
        if tp == tpname:
            used_in.append(("%s: %s" % (_("User"), userid),
                make_link([("mode", "edit_user"), ("edit", userid)])))

    # Part 3: Other Timeperiods
    for tpn, tp in load_timeperiods().items():
        if tpname in tp.get("exclude", []):
            used_in.append(("%s: %s (%s)" % (_("Timeperiod"), tp.get("alias", tpn),
                    _("excluded")),
                    make_link([("mode", "edit_timeperiod"), ("edit", tpn)])))

    return used_in


#.
#   .--Multisite Connections-----------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing sites.                                             |
#   '----------------------------------------------------------------------'

# Sort given sites argument by local, followed by slaves
def sort_sites(sites):
    def custom_sort(a,b):
        return cmp(a[1].get("replication","peer"), b[1].get("replication","peer")) or \
               cmp(a[1].get("alias"), b[1].get("alias"))
    sites.sort(cmp = custom_sort)

def mode_sites(phase):
    if phase == "title":
        return _("Distributed Monitoring")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New connection"), make_link([("mode", "edit_site")]), "new")
        return

    sites = load_sites()

    if phase == "action":
        delid = html.var("_delete")
        if delid and html.transaction_valid():
            # The last connection can always be deleted. In that case we
            # fallb back to non-distributed-WATO and the site attribute
            # will be removed.
            test_sites = dict(sites.items())
            del test_sites[delid]
            if is_distributed(test_sites):
                # Make sure that site is not being used by hosts and folders
                site_ids = set([])
                find_folder_sites(site_ids, g_root_folder, True)
                if delid in site_ids:
                    raise MKUserError(None,
                        _("You cannot delete this connection. "
                          "It has folders/hosts assigned to it."))

            c = wato_confirm(_("Confirm deletion of site %s" % delid),
                             _("Do you really want to delete the connection to the site %s?" % delid))
            if c:
                del sites[delid]
                save_sites(sites)
                update_replication_status(delid, None)

                # Due to the deletion the replication state can get clean.
                if is_distributed() and global_replication_state() == "clean":
                    log_commit_pending()

                log_pending(SYNCRESTART, None, "edit-sites", _("Deleted site %s" % (delid)))
                return None
            elif c == False:
                return ""
            else:
                return None

        logout_id = html.var("_logout")
        if logout_id:
            site = sites[logout_id]
            c = wato_confirm(_("Confirm logout"),
                       _("Do you really want to log out of '%s'?") % site["alias"])
            if c:
                if "secret" in site:
                    del site["secret"]
                save_sites(sites)
                log_audit(None, "edit-site", _("Logged out of remote site '%s'") % site["alias"])
                return None, _("Logged out.")
            elif c == False:
                return ""
            else:
                return None

        login_id = html.var("_login")
        if login_id:
            if html.var("_abort"):
                return "sites"
            if not html.check_transaction():
                return
            site = sites[login_id]
            error = None
            # Fetch name/password of admin account
            if html.has_var("_name"):
                name = html.var("_name", "").strip()
                passwd = html.var("_passwd", "").strip()
                try:
                    secret = do_site_login(login_id, name, passwd)
                    site["secret"] = secret
                    save_sites(sites)
                    log_audit(None, "edit-site", _("Successfully logged into remote site '%s'") % site["alias"])
                    return None, _("Successfully logged into remote site '%s'!" % site["alias"])
                except MKAutomationException, e:
                    error = _("Cannot connect to remote site: %s") % e
                except MKUserError, e:
                    html.add_user_error(e.varname, e.message)
                    error = e.message
                except Exception, e:
                    if config.debug:
                        raise
                    html.add_user_error("_name", error)
                    error = str(e)


            wato_html_head(_("Login into site '%s'") % site["alias"])
            if error:
                html.show_error(error)

            html.write('<p>%s</p>' % (_("For the initial login into the slave site %s "
                         "we need once your administration login for the Multsite "
                         "GUI on that site. Your credentials will only be used for "
                         "the initial handshake and not be stored. If the login is "
                         "successful then both side will exchange a login secret "
                         "which is used for the further remote calls.") % site["alias"]))
            html.begin_form("login", method="POST")
            forms.header(_('Login credentials'))
            forms.section(_('Adminstrator name:'))
            html.text_input("_name")
            html.set_focus("_name")
            forms.section(_('Adminstrator password:'))
            html.password_input("_passwd")
            forms.end()
            html.button("_do_login", _("Login"))
            html.button("_abort", _("Abort"))
            html.hidden_field("_login", login_id)
            html.hidden_fields()
            html.end_form()
            return ""
        return


    table.begin("sites", _("Connections to local and remote sites"),
                empty_text = _("You have not configured any local or remotes sites. Multisite will "
                               "implicitely add the data of the local monitoring site. If you add remotes "
                               "sites, please do not forget to add your local monitoring site also, if "
                               "you want to display its data."))

    entries = sites.items()
    sort_sites(entries)
    for id, site in entries:
        table.row()
        # Buttons
        edit_url = make_link([("mode", "edit_site"), ("edit", id)])
        clone_url = make_link([("mode", "edit_site"), ("clone", id)])
        delete_url = html.makeactionuri([("_delete", id)])
        table.cell(_("Actions"), css="buttons")
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Clone this connection in order to create a new one"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")
        if site.get("replication"):
            globals_url = make_link([("mode", "edit_site_globals"), ("site", id)])
            html.icon_button(globals_url, _("Site-specific global configuration"), "configuration")

        # Site-ID
        table.cell(_("Site-ID"), id)

        # Alias
        table.cell(_("Alias"), site.get("alias", ""))

        # Socket
        socket = site.get("socket", _("local site"))
        if socket == "disabled:":
            socket = _("don't query status")
        table.cell(_("Socket"))
        if type(socket) == tuple and socket[0] == "proxy":
            html.write(_("Use livestatus Proxy-Daemon"))
        else:
            html.write(socket)

        # Status host
        if "status_host" in site:
            sh_site, sh_host = site["status_host"]
            table.cell(_("Status host"), "%s/%s" % (sh_site, sh_host))
        else:
            table.cell(_("Status host"))

        # Disabled
        if site.get("disabled", False) == True:
            table.cell(_("Disabled"), "<b>%s</b>" % _("yes"))
        else:
            table.cell(_("Disabled"), _("no"))

        # Timeout
        if "timeout" in site:
            table.cell(_("Timeout"), _("%d sec") % site["timeout"], css="number")
        else:
            table.cell(_("Timeout"), "")

        # Persist
        if site.get("persist", False):
            table.cell(_("Pers."), "<b>%s</b>" % _("yes"))
        else:
            table.cell(_("Pers."), _("no"))

        # Replication
        if site.get("replication") == "slave":
            repl = _("Slave")
        else:
            repl = ""
        table.cell(_("Replication"), repl)

        # Login-Button for Replication
        table.cell(_("Login"))
        if repl:
            if site.get("secret"):
                logout_url = make_action_link([("mode", "sites"), ("_logout", id)])
                html.buttonlink(logout_url, _("Logout"))
            else:
                login_url = make_action_link([("mode", "sites"), ("_login", id)])
                html.buttonlink(login_url, _("Login"))

    table.end()

def mode_edit_site_globals(phase):
    sites = load_sites()
    siteid = html.var("site")
    site = sites[siteid]

    if phase == "title":
        return _("Edit site-specific global settings of %s" % siteid)

    elif phase == "buttons":
        html.context_button(_("All Sites"), make_link([("mode", "sites")]), "back")
        html.context_button(_("Connection"), make_link([("mode", "edit_site"), ("edit", siteid)]), "sites")
        return

    # The site's default values are the current global settings
    check_mk_vars = [ varname for (varname, var) in g_configvars.items() if var[0] == "check_mk" ]
    default_values = check_mk_local_automation("get-configuration", [], check_mk_vars)
    default_values.update(load_configuration_settings())
    current_settings = site.get("globals", {})

    if phase == "action":
        varname = html.var("_varname")
        action = html.var("_action")
        if varname:
            domain, valuespec, need_restart, allow_reset, in_global_settings = g_configvars[varname]
            def_value = default_values.get(varname, valuespec.default_value())

            if action == "reset" and not is_a_checkbox(valuespec):
                c = wato_confirm(
                    _("Removing site-specific configuration variable"),
                    _("Do you really want to remove the configuration variable <b>%s</b> "
                      "of the specific configuration of this site and that way use the global value "
                      "of <b><tt>%s</tt></b>?") %
                       (varname, valuespec.value_to_text(def_value)))
            else:
                if not html.check_transaction():
                    return
                c = True # no confirmation for direct toggle

            if c:
                if varname in current_settings:
                    current_settings[varname] = not current_settings[varname]
                else:
                    current_settings[varname] = not def_value
                msg = _("Changed site-specific configuration variable %s to %s." % (varname,
                    current_settings[varname] and "on" or "off"))
                site.setdefault("globals", {})[varname] = current_settings[varname]
                save_sites(sites, activate=False)

                changes = { "need_sync" : True }
                if need_restart:
                    changes["need_restart"] = True
                update_replication_status(siteid, changes)
                log_pending(AFFECTED, None, "edit-configvar", msg)
                if action == "_reset":
                    return "edit_site_globals", msg
                else:
                    return "edit_site_globals"
            elif c == False:
                return ""
            else:
                return None
        else:
            return
        return

    html.help(_("Here you can configure global settings, that should just be applied "
                "on that remote site. <b>Note</b>: this only makes sense if the site "
                "is a configuration slave."))

    if site.get("replication") != "slave":
        html.show_error(_("This site is not a replication slave. You cannot configure specific settings for it."))
        return

    render_global_configuration_variables(default_values, current_settings, show_all=True)

def create_site_globals_file(siteid, tmp_dir):
    if not os.path.exists(tmp_dir):
        make_nagios_directory(tmp_dir)
    sites = load_sites()
    site = sites[siteid]
    config = site.get("globals", {})

    # Add global setting for disabling WATO right here. It is not
    # available as a normal global option. That would be too dangerous.
    # You could disable WATO on the master very easily that way...
    # The default value is True - even for sites configured with an
    # older version of Check_MK.
    config["wato_enabled"] = not site.get("disable_wato", True)
    file(tmp_dir + "/sitespecific.mk", "w").write("%r\n" % config)


def mode_edit_site(phase):
    sites = load_sites()
    siteid = html.var("edit") # missing -> new site
    cloneid = html.var("clone")
    new = siteid == None
    if cloneid:
        site = sites[cloneid]
    elif new:
        site = {}
    else:
        site = sites.get(siteid, {})

    if phase == "title":
        if new:
            return _("Create new site connection")
        else:
            return _("Edit site connection %s" % siteid)

    elif phase == "buttons":
        html.context_button(_("All Sites"), make_link([("mode", "sites")]), "back")
        if not new and site.get("replication"):
            html.context_button(_("Site-Globals"), make_link([("mode", "edit_site_globals"), ("site", siteid)]), "configuration")
        return

    vs_tcp_port = Tuple(
            title = _("TCP Port to connect to"),
            orientation = "float",
            elements = [
                TextAscii(label = _("Host:"), allow_empty = False, size=15),
                Integer(label = _("Port:"), minvalue=1, maxvalue=65535, default_value=6557),
    ])
    conn_choices = [
        ( None, _("Connect to the local site") ),
        ( "tcp",   _("Connect via TCP"), vs_tcp_port),
        ( "unix",  _("Connect via UNIX socket"), TextAscii(
            label = _("Path:"),
            size = 40,
            allow_empty = False)),
    ]
    if config.liveproxyd_enabled:
        conn_choices[2:2] = [
        ( "proxy", _("Use Livestatus Proxy-Daemon"),
          Dictionary(
              optional_keys = False,
              columns = 1,
              elements = [
                  ( "socket", vs_tcp_port ),
                  ( "channels",
                    Integer(
                        title = _("Number of channels to keep open"),
                        minvalue = 2,
                        maxvalue = 50,
                        default_value = 5)),
                  ( "heartbeat",
                    Tuple(
                        title = _("Regular heartbeat"),
                        orientation = "float",
                        elements = [
                            Integer(label = _("Rate:"), unit=_("/sec"), minvalue=1, default_value = 5),
                            Float(label = _("Timeout:"), unit=_("sec"), minvalue=0.1, default_value = 2.0),
                   ])),
                   ( "channel_timeout",
                     Float(
                         title = _("Timeout waiting for a free channel"),
                         minvalue = 0.1,
                         default_value = 3,
                         unit = _("sec"),
                     )
                   ),
                   ( "query_timeout",
                     Float(
                         title = _("Total query timeout"),
                         minvalue = 0.1,
                         unit = _("sec"),
                         default_value = 120,
                     )
                   ),
                   ( "connect_retry",
                     Float(
                        title = _("Cooling period after failed connect/heartbeat"),
                        minvalue = 0.1,
                        unit = _("sec"),
                        default_value = 4.0,
                   )),
                   ( "cache",
                      Checkbox(title = _("Enable Caching"),
                         label = _("Cache several non-status queries"),
                          help = _("This option will enable the caching of several queries that "
                                   "need no current data. This reduces the number of Livestatus "
                                   "queries to sites and cuts down the response time of remote "
                                   "sites with large latencies."),
                          default_value = True,
                   )),
                ]
             )
          )
        ]

    # ValueSpecs for the more complex input fields
    vs_conn_method = CascadingDropdown(
        html_separator = " ",
        choices = conn_choices,
    )


    if phase == "action":
        if not html.check_transaction():
            return "sites"

        if new:
            id = html.var("id").strip()
        else:
            id = siteid

        if new and id in sites:
            raise MKUserError("id", _("This id is already being used by another connection."))
        if not re.match("^[-a-z0-9A-Z_]+$", id):
            raise MKUserError("id", _("The site id must consist only of letters, digit and the underscore."))

        # Save copy of old site for later
        if not new:
            old_site = sites[siteid]

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
        disabled = html.get_checkbox("disabled")
        new_site["disabled"] = disabled

        # Connection
        method = vs_conn_method.from_html_vars("method")
        vs_conn_method.validate_value(method, "method")
        if type(method) == tuple and method[0] in [ "unix", "tcp"]:
            if method[0] == "unix":
                new_site["socket"] = "unix:" + method[1]
            else:
                new_site["socket"] = "tcp:%s:%d" % method[1]
        elif method:
            new_site["socket"] = method
        elif "socket" in new_site:
            del new_site["socket"]

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

        # Replication
        repl = html.var("replication")
        if repl == "none":
            repl = None
        if repl:
            new_site["replication"] = repl

        multisiteurl = html.var("multisiteurl", "").strip()
        if repl:
            if not multisiteurl:
                raise MKUserError("multisiteurl",
                    _("Please enter the Multisite URL of the slave site."))
            if not multisiteurl.endswith("/check_mk/"):
                raise MKUserError("multisiteurl",
                    _("The Multisite URL must end with /check_mk/"))
            if not multisiteurl.startswith("http://") and not multisiteurl.startswith("https://"):
                raise MKUserError("multisiteurl",
                    _("The Multisites URL must begin with <tt>http://</tt> or <tt>https://</tt>."))
            if "socket" not in new_site:
                raise MKUserError("replication",
                    _("You cannot do replication with the local site."))

        # Save Multisite-URL even if replication is turned off. That way that
        # setting is not lost if replication is turned off for a while.
        new_site["multisiteurl"] = multisiteurl

        # Disabling of WATO
        new_site["disable_wato"] = html.get_checkbox("disable_wato")

        # Handle the insecure replication flag
        new_site["insecure"] = html.get_checkbox("insecure")

        # Allow direct user login
        new_site["user_login"] = html.get_checkbox("user_login")

        # Secret is not checked here, just kept
        if not new and "secret" in old_site:
            new_site["secret"] = old_site["secret"]

        # Do not forget to add those settings (e.g. "globals") that
        # are not edited with this dialog
        if not new:
            for key in old_site.keys():
                if key not in new_site:
                    new_site[key] = old_site[key]

        save_sites(sites)

        # Own site needs RESTART in any case
        update_replication_status(our_site_id(), { "need_restart" : True })
        if new:
            if not site_is_local(id):
                update_replication_status(id, { "need_sync" : True, "need_restart" : True })
            log_pending(AFFECTED, None, "edit-sites", _("Created new connection to site %s" % id))
        else:
            log_pending(AFFECTED, None, "edit-sites", _("Modified site connection %s" % id))
            # Replication mode has switched on/off => handle replication state
            repstatus = load_replication_status()
            if repl:              # Repl is on
                update_replication_status(id, { "need_sync" : True, "need_restart" : True })
            elif id in repstatus: # Repl switched off
                update_replication_status(id, None) # Replication switched off
                if is_distributed() and global_replication_state() == "clean":
                    log_commit_pending()
        return "sites"

    html.begin_form("site")


    # ID
    forms.header(_("Basic settings"))
    forms.section(_("Site ID"), simple = not new)
    if new:
        html.text_input("id", siteid or cloneid)
        html.set_focus("id")
    else:
        html.write(siteid)

    # Alias
    forms.section(_("Alias"))
    html.text_input("alias", site.get("alias", ""), size = 60)
    if not new:
        html.set_focus("alias")
    html.help(_("An alias or description of the site"))


    forms.header(_("Livestatus settings"))
    forms.section(_("Connection"))
    method = site.get("socket", None)
    if type(method) == str and method.startswith("unix:"):
        method = ('unix', method[5:])
    elif type(method) == str and method.startswith("tcp:"):
        parts = method.split(":")[1:]
        method = ('tcp', (parts[0], int(parts[1])))
    vs_conn_method.render_input("method", method)

    html.help( _("When connecting to remote site please make sure "
               "that Livestatus over TCP is activated there. You can use UNIX sockets "
               "to connect to foreign sites on localhost. Please make sure that this "
               "site has proper read and write permissions to the UNIX socket of the "
               "foreign site."))

    # Timeout
    forms.section(_("Connect Timeout"))
    timeout = site.get("timeout", 10)
    html.number_input("timeout", timeout, size=2)
    html.write(_(" seconds"))
    html.help(_("This sets the time that Multisite waits for a connection "
                 "to the site to be established before the site is considered to be unreachable. "
                 "If not set, the operating system defaults are begin used and just one login attempt is being. "
                 "performed."))

    # Persistent connections
    forms.section(_("Persistent Connection"), simple=True)
    html.checkbox("persist", site.get("persist", False), label=_("Use persistent connections"))
    html.help(_("If you enable persistent connections then Multisite will try to keep open "
              "the connection to the remote sites. This brings a great speed up in high-latency "
              "situations but locks a number of threads in the Livestatus module of the target site."))

    # URL-Prefix
    docu_url = "http://mathias-kettner.de/checkmk_multisite_modproxy.html"
    forms.section(_("URL prefix"))
    html.text_input("url_prefix", site.get("url_prefix", ""), size = 60)
    html.help(_("The URL prefix will be prepended to links of addons like PNP4Nagios "
                 "or the classical Nagios GUI when a link to such applications points to a host or "
                 "service on that site. You can either use an absolute URL prefix like <tt>http://some.host/mysite/</tt> "
                 "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you needed a mod_proxy "
                 "configuration in your local system apache that proxies such URLs to the according remote site. "
                 "Please refer to the <a target=_blank href='%s'>online documentation</a> for details. "
                 "The prefix should end with a slash. Omit the <tt>/pnp4nagios/</tt> from the prefix.") % docu_url)

    # Status-Host
    docu_url = "http://mathias-kettner.de/checkmk_multisite_statushost.html"
    forms.section(_("Status host"))

    sh = site.get("status_host")
    if sh:
        sh_site, sh_host = sh
    else:
        sh_site = ""
        sh_host = ""
    html.write(_("host: "))
    html.text_input("sh_host", sh_host, size=10)
    html.write(_(" on monitoring site: "))
    html.sorted_select("sh_site",
       [ ("", _("(no status host)")) ] + [ (sk, si.get("alias", sk)) for (sk, si) in sites.items() ], sh_site)
    html.help( _("By specifying a status host for each non-local connection "
                 "you prevent Multisite from running into timeouts when remote sites do not respond. "
                 "You need to add the remote monitoring servers as hosts into your local monitoring "
                 "site and use their host state as a reachability state of the remote site. Please "
                 "refer to the <a target=_blank href='%s'>online documentation</a> for details.") % docu_url)

    # Disabled
    forms.section(_("Disable"), simple=True)
    html.checkbox("disabled", site.get("disabled", False), label = _("Temporarily disable this connection"))
    html.help( _("If you disable a connection, then no data of this site will be shown in the status GUI. "
                 "The replication is not affected by this, however."))

    # Replication
    forms.header(_("Configuration Replication (Distributed WATO)"))
    forms.section(_("Replication method"))
    html.select("replication",
        [ ("none",  _("No replication with this site")),
          ("slave", _("Slave: push configuration to this site"))
        ], site.get("replication", "none"))
    html.help( _("WATO replication allows you to manage several monitoring sites with a "
                "logically centralized WATO. Slave sites receive their configuration "
                "from master sites. <br><br>Note: Slave sites "
                "do not need any replication configuration. They will be remote-controlled "
                "by the master sites."))

    forms.section(_("Multisite-URL of remote site"))
    html.text_input("multisiteurl", site.get("multisiteurl", ""), size=60)
    html.help( _("URL of the remote Check_MK including <tt>/check_mk/</tt>. "
                   "This URL is in many cases the same as the URL-Prefix but with <tt>check_mk/</tt> "
                   "appended, but it must always be an absolute URL. Please note, that "
                   "that URL will be fetched by the Apache server of the local "
                   "site itself, whilst the URL-Prefix is used by your local Browser."))

    forms.section(_("WATO"), simple=True)
    html.checkbox("disable_wato", site.get("disable_wato", True), label = _('Disable configuration via WATO on this site'))
    html.help( _('It is a good idea to disable access to WATO completely on the slave site. '
                 'Otherwise a user who does not now about the replication could make local '
                 'changes that are overridden at the next configuration activation.'))

    forms.section(_("SSL"), simple=True)
    html.checkbox("insecure", site.get("insecure", False), label = _('Ignore SSL certificate errors'))
    html.help( _('This might be needed to make the synchronization accept problems with '
                 'SSL certificates when using an SSL secured connection.'))

    forms.section(_('Direct login to Web GUI allowed'), simple=True)
    html.checkbox('user_login', site.get('user_login', True),
                  label = _('Users are allowed to directly login into the Web GUI of this site'))
    html.help(_('When enabled, this site is marked for synchronisation every time a Web GUI '
                'related option is changed in the master site.'))

    forms.end()
    html.button("save", _("Save"))

    html.hidden_fields()
    html.end_form()


def load_sites():
    try:
        if not os.path.exists(sites_mk):
            return {}

        vars = { "sites" : {} }
        execfile(sites_mk, vars, vars)

        # Be compatible to old "disabled" value in socket attribute.
        # Can be removed one day.
        for site in vars['sites'].values():
            if site.get('socket') == 'disabled':
                site['disabled'] = True
                del site['socket']

        return vars["sites"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (sites_mk, e)))
        return {}


def save_sites(sites, activate=True):
    make_nagios_directory(multisite_dir)

    # Important: even write out sites if it's empty. The global 'sites'
    # variable will otherwise survive in the Python interpreter of the
    # Apache processes.
    out = create_user_file(sites_mk, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("sites = \\\n%s\n" % pprint.pformat(sites))

    # Do not activate when just the site's global settings have
    # been edited
    if activate:
        config.load_config() # make new site configuration active
        update_distributed_wato_file(sites)
        declare_site_attribute()
        load_all_folders() # make sure that .siteid is present
        rewrite_config_files_below(g_root_folder) # fix site attributes
        need_sidebar_reload()

        if config.liveproxyd_enabled:
            save_liveproxyd_config(sites)

        create_nagvis_backends(sites)

        # Call the sites saved hook
        call_hook_sites_saved(sites)

def save_liveproxyd_config(sites):
    path = defaults.default_config_dir + "/liveproxyd.mk"
    out = create_user_file(path, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")

    conf = {}
    for siteid, siteconf in sites.items():
        s = siteconf.get("socket")
        if type(s) == tuple and s[0] == "proxy":
            conf[siteid] = s[1]

    out.write("sites = \\\n%s\n" % pprint.pformat(conf))
    try:
        pidfile = defaults.livestatus_unix_socket + "proxyd.pid"
        pid = int(file(pidfile).read().strip())
        os.kill(pid, 10)
    except Exception, e:
        html.show_error(_("Warning: cannot reload Livestatus Proxy-Daemon: %s" % e))

def create_nagvis_backends(sites):
    if not defaults.omd_root:
        return # skip when not in OMD environment
    cfg = [
        '; MANAGED BY CHECK_MK WATO - Last Update: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
    ]
    for site_id, site in sites.items():
        if site == defaults.omd_site:
            continue # skip local site, backend already added by omd
        if 'socket' not in site:
            continue # skip sites without configured sockets

        # Handle special data format of livestatus proxy config
        if type(site['socket']) == tuple:
            socket = 'tcp:%s:%d' % site['socket'][1]['socket']
        else:
            socket = site['socket']

        cfg += [
            '',
            '[backend_%s]' % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if 'status_host' in site:
            cfg.append('statushost="%s"' % ':'.join(site['status_host']))

    file('%s/etc/nagvis/conf.d/cmk_backends.ini.php' % defaults.omd_root, 'w').write('\n'.join(cfg))

# Makes sure, that in distributed mode we monitor only
# the hosts that are directly assigned to our (the local)
# site.
def update_distributed_wato_file(sites):
    # Note: we cannot access config.sites here, since we
    # are currently in the process of saving the new
    # site configuration.
    distributed = False
    found_local = False
    for siteid, site in sites.items():
        if site.get("replication"):
            distributed = True
        if site_is_local(siteid):
            found_local = True
            create_distributed_wato_file(siteid, site.get("replication"))

    # Remove the distributed wato file
    # a) If there is no distributed WATO setup
    # b) If the local site could not be gathered
    if not distributed: # or not found_local:
        delete_distributed_wato_file()

#.
#   .--Replication---------------------------------------------------------.
#   |           ____            _ _           _   _                        |
#   |          |  _ \ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __             |
#   |          | |_) / _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \            |
#   |          |  _ <  __/ |_) | | | (_| (_| | |_| | (_) | | | |           |
#   |          |_| \_\___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|           |
#   |                    |_|                                               |
#   +----------------------------------------------------------------------+
#   | Functions dealing with the WATO replication feature.                 |
#   | Let's call this "Distributed WATO". More buzz-word like :-)          |
#   '----------------------------------------------------------------------'

def do_site_login(site_id, name, password):
    sites = load_sites()
    site = sites[site_id]
    if not name:
        raise MKUserError("_name",
            _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd",
            _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + 'login.py'
    post_data = html.urlencode_vars([
        ('_login', '1'),
        ('_username', name),
        ('_password', password),
        ('_origtarget', 'automation_login.py'),
        ('_plain_error', '1'),
    ])
    response = get_url(url, site.get('insecure', False), name, password, post_data=post_data).strip()
    if '<html>' in response.lower():
        message = _("Authentication to web service failed.<br>Message:<br>%s") % \
            html.strip_tags(html.strip_scripts(response))
        if config.debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    elif not response:
        raise MKAutomationException(_("Empty response from web service"))
    else:
        try:
            return eval(response)
        except:
            raise MKAutomationException(response)

def upload_file(url, file_path, insecure):
    return get_url(url, insecure, params = ' -F snapshot=@%s' % file_path)

def get_url(url, insecure, user=None, password=None, params = '', post_data = None):
    cred = ''
    if user:
        cred = ' -u "%s:%s"' % (user, password)

    insecure = insecure and ' --insecure' or ''

    # -s: silent
    # -S: show errors
    # -w '%{http_code}': add the http status code to the end of the output
    # -L: follow redirects
    # -b /dev/null: handle cookies, but do not persist them
    command = 'curl -b /dev/null -L -w "\n%%{http_code}" -s -S%s%s%s "%s" 2>&1' % (
              insecure, cred, params, url)
    tmp_file = None
    if post_data != None:
        # Put POST data on command line as long as it is not
        # longer than 50 KB (remember: Linux has an upper limit
        # of 132 KB for command line plus environment
        if len(post_data) < 50000:
            command += ' --data-binary "%s"' % post_data
        else:
            import tempfile
            tmp_file = tempfile.NamedTemporaryFile(dir = defaults.tmp_dir)
            tmp_file.write(post_data)
            tmp_file.flush()
            command += ' --data-binary "@%s"' % tmp_file.name

    response = os.popen(command).read().strip()
    try:
        status_code = int(response[-3:])
        response_body = response[:-3]
    except:
        status_code = None
        response_body = response

    if status_code == 401:
        raise MKUserError("_passwd", _("Authentication failed. Invalid login/password."))
    elif status_code != 200:
        raise MKUserError("_passwd", _("HTTP Error - %s: %s") % (status_code, response_body))

    return response_body

def check_mk_remote_automation(siteid, command, args, indata):
    site = config.site(siteid)
    if "secret" not in site:
        raise MKGeneralException(_("Cannot access site %s - you are not logged in.")
           % site.get("alias", siteid))
    # If the site is not up-to-date, synchronize it first.
    repstatus = load_replication_status()
    if repstatus.get(siteid, {}).get("need_sync"):
        synchronize_site(config.site(siteid), False)

    # Now do the actual remote command
    response = do_remote_automation(
        config.site(siteid), "checkmk-automation",
        [
            ("automation", command),   # The Check_MK automation command
            ("arguments", mk_repr(args)),  # The arguments for the command
            ("indata", mk_repr(indata)), # The input data
        ])
    return response

def do_remote_automation(site, command, vars):
    base_url = site["multisiteurl"]
    secret = site.get("secret")
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = base_url + "automation.py?" + \
        html.urlencode_vars([
               ("command", command),
               ("secret",  secret),
               ("debug",   config.debug and '1' or '')
        ])
    vars_encoded = html.urlencode_vars(vars)
    response = get_url(url, site.get('insecure', False),
                       post_data=vars_encoded)
    if not response:
        raise MKAutomationException("Empty output from remote site.")
    try:
        response = eval(response)
    except:
        # The remote site will send non-Python data in case of an
        # error.
        raise MKAutomationException("<pre>%s</pre>" % response)
    return response


# Determine, if we have any slaves to distribute
# configuration to.
def is_distributed(sites = None):
    if sites == None:
        sites = config.sites
    for site in sites.values():
        if site.get("replication"):
            return True
    return False

def declare_site_attribute():
    undeclare_host_attribute("site")
    if is_distributed():
        declare_host_attribute(SiteAttribute(), show_in_table = True, show_in_folder = True)

def default_site():
    for id, site in config.sites.items():
        if not "socket" in site \
            or site["socket"] == "unix:" + defaults.livestatus_unix_socket:
            return id
    try:
        return config.sites.keys()[0]
    except:
        return None

class SiteAttribute(Attribute):
    def __init__(self):
        # Default is is the local one, if one exists or
        # no one if there is no local site
        self._choices = []
        for id, site in config.sites.items():
            title = id
            if site.get("alias"):
                title += " - " + site["alias"]
            self._choices.append((id, title))

        self._choices.sort(cmp=lambda a,b: cmp(a[1], b[1]))
        self._choices_dict = dict(self._choices)
        Attribute.__init__(self, "site", _("Monitored on site"),
                    _("Specify the site that should monitor this host."),
                    default_value = default_site())

    def paint(self, value, hostname):
        return "", self._choices_dict.get(value, value)

    def render_input(self, value):
        html.select("site", self._choices, value)

    def from_html_vars(self):
        return html.var("site")

    def get_tag_list(self, value):
        return [ "site:" + value ]

# The replication status contains information about each
# site. It is a dictionary from the site id to a dict with
# the following keys:
# "need_sync" : 17,  # number of non-synchronized changes
# "need_restart" : True, # True, if remote site needs a restart (cmk -R)
def load_replication_status():
    try:
        return eval(file(repstatus_file).read())
    except:
        return {}

def save_replication_status(repstatus):
    config.write_settings_file(repstatus_file, repstatus)

# Updates one or more dict elements of a site in an
# atomic way. If vars is None, the sites status will
# be removed
def update_replication_status(site_id, vars, times = {}):
    make_nagios_directory(var_dir)
    fd = os.open(repstatus_file, os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    repstatus = load_replication_status()
    if vars == None:
        if site_id in repstatus:
            del repstatus[site_id]
    else:
        repstatus.setdefault(site_id, {})
        repstatus[site_id].update(vars)
        old_times = repstatus[site_id].setdefault("times", {})
        for what, duration in times.items():
            if what not in old_times:
                old_times[what] = duration
            else:
                old_times[what] = 0.8 * old_times[what] + 0.2 * duration
    save_replication_status(repstatus)
    os.close(fd)

def update_login_sites_replication_status():
    for siteid, site in config.sites.items():
        if site.get('user_login', True) and not site_is_local(siteid):
            update_replication_status(siteid, {'need_sync': True})

def global_replication_state():
    repstatus = load_replication_status()
    some_dirty = False

    for site_id in config.sitenames():
        site = config.site(site_id)
        if not site_is_local(site_id) and not site.get("replication"):
            continue

        srs = repstatus.get(site_id, {})
        if srs.get("need_sync") or srs.get("need_restart"):
            some_dirty = True

    if some_dirty:
        return "dirty"
    else:
        return "clean"

def find_host_sites(site_ids, folder, hostname):
    if hostname in folder[".hosts"]:
        host = folder[".hosts"][hostname]
        if "site" in host and host["site"]:
            site_ids.add(host["site"])
        elif folder[".siteid"]:
            site_ids.add(folder[".siteid"])

# Scan recursively for references to sites
# in folders and hosts
def find_folder_sites(site_ids, folder, include_folder = False):
    if include_folder and folder[".siteid"]:
        site_ids.add(folder[".siteid"])
    load_hosts(folder)
    for hostname in folder[".hosts"]:
        find_host_sites(site_ids, folder, hostname)
    for subfolder in folder[".folders"].values():
        find_folder_sites(site_ids, subfolder, include_folder)

# This method is called when:
# a) moving a host from one folder to another (2 times)
# b) deleting a host
# c) deleting a folder
# d) changing a folder's attributes (2 times)
# e) changing the attributes of a host (2 times)
# f) saving check configuration of a single host
# g) doing bulk inventory for a host
# h) doing bulk edit on a host (2 times)
# i) doing bulk cleanup on a host (2 time)
# It scans for the sites affected by the hosts in a folder and its subfolders.
# Please note: The "site" attribute of the folder itself is not relevant
# at all. It's just there to be inherited to the hosts. What counts is
# only the attributes of the hosts.
def mark_affected_sites_dirty(folder, hostname=None, sync = True, restart = True):
    if is_distributed():
        site_ids = set([])
        if hostname:
            find_host_sites(site_ids, folder, hostname)
        else:
            find_folder_sites(site_ids, folder)
        for site_id in site_ids:
            changes = {}
            if sync and not site_is_local(site_id):
                changes["need_sync"] = True
            if restart:
                changes["need_restart"] = True
            update_replication_status(site_id, changes)

# def mark_all_sites_dirty(sites):
#     changes = {
#         "need_sync" : True,
#         "need_restart" : True,
#     }
#     for site_id, site in sites.items():
#         update_replication_status(site_id, changes)

def remove_sync_snapshot(siteid):
    path = sync_snapshot_file(siteid)
    if os.path.exists(path):
        os.remove(path)

def sync_snapshot_file(siteid):
    return defaults.tmp_dir + "/sync-%s.tar.gz" % siteid

def create_sync_snapshot(siteid):
    path = sync_snapshot_file(siteid)
    if not os.path.exists(path):
        tmp_path = "%s-%s" % (path, id(html))

        # Add site-specific global settings.
        site_tmp_dir = defaults.tmp_dir + "/sync-%s-specific-%s" % (siteid, id(html))
        create_site_globals_file(siteid, site_tmp_dir)

        paths = replication_paths + [("dir", "sitespecific", site_tmp_dir)]
        multitar.create(tmp_path, paths)
        shutil.rmtree(site_tmp_dir)
        os.rename(tmp_path, path)

def synchronize_site(site, restart):
    if site_is_local(site["id"]):
        if restart:
            start = time.time()
            restart_site(site)
            update_replication_status(site["id"],
            { "need_restart" : False },
            { "restart" : time.time() - start})

        return True

    create_sync_snapshot(site["id"])
    try:
        start = time.time()
        result = push_snapshot_to_site(site, restart)
        duration = time.time() - start
        update_replication_status(site["id"], {},
           { restart and "sync+restart" or "restart" : duration })
        if result == True:
            update_replication_status(site["id"], {
                "need_sync": False,
                "result" : _("Success"),
                })
            if restart:
                update_replication_status(site["id"], { "need_restart": False })
        else:
            update_replication_status(site["id"], { "result" : result })
        return result
    except Exception, e:
        update_replication_status(site["id"], { "result" : str(e) })
        raise

# Isolated restart without prior synchronization. Currently this
# is only being called for the local site.
def restart_site(site):
    start = time.time()
    check_mk_automation(site["id"], config.wato_activation_method)
    duration = time.time() - start
    update_replication_status(site["id"],
        { "need_restart" : False }, { "restart" : duration })

def push_snapshot_to_site(site, do_restart):
    mode = site.get("replication", "slave")
    url_base = site["multisiteurl"] + "automation.py?"
    var_string = html.urlencode_vars([
        ("command",    "push-snapshot"),
        ("secret",     site["secret"]),
        ("siteid",     site["id"]),         # This site must know it's ID
        ("mode",       mode),
        ("restart",    do_restart and "yes" or "on"),
        ("debug",      config.debug and "1" or ""),
    ])
    url = url_base + var_string
    response_text = upload_file(url, sync_snapshot_file(site["id"]), site.get('insecure', False))
    try:
        return eval(response_text)
    except:
        raise MKAutomationException(_("Garbled automation response from site %s: '%s'") %
            (site["id"], response_text))

def push_user_profile_to_site(site, user_id, profile):
    url = site["multisiteurl"] + "automation.py?" + html.urlencode_vars([
        ("command",    "push-profile"),
        ("secret",     site["secret"]),
        ("siteid",     site['id']),
        ("debug",      config.debug and "1" or ""),
    ])
    content = html.urlencode_vars([
        ('user_id', user_id),
        ('profile', mk_repr(profile)),
    ])

    response = get_url(url, site.get('insecure', False), post_data = content)
    if not response:
        raise MKAutomationException("Empty output from remote site.")

    try:
        response = mk_eval(response)
    except:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException('Invalid response: %s' % response)
    return response

def synchronize_profile(site, user_id):
    users = userdb.load_users(lock = False)
    if not user_id in users:
        raise MKUserError(None, _('The requested user does not exist'))

    start = time.time()
    result = push_user_profile_to_site(site, user_id, users[user_id])
    duration = time.time() - start
    update_replication_status(site["id"], {}, {"profile-sync": duration})
    return result


# AJAX handler for javascript triggered wato activation
def ajax_activation():
    try:
        if is_distributed():
            raise MKUserError(None, _('Call not supported in distributed setups.'))

        config.need_permission("wato.activate")

        # Initialise g_root_folder, load all folder information
        prepare_folder_info()

        # Activate changes for single site
        activate_changes()

        log_commit_pending() # flush logfile with pending actions
        log_audit(None, "activate-config", _("Configuration activated, monitoring server restarted"))

        html.write('OK: ')
        html.write('<div class=act_success><img src="images/icon_apply.png" /> %s</div>' %
                  _("Configuration successfully activated."))
    except Exception, e:
        html.show_error(str(e))

# Try to do a rush-ahead-activation
def cmc_rush_ahead_activation():
    return

def cmc_reload():
    log_audit(None, "activate-config", "Reloading Check_MK Micro Core on the fly")
    html.live.command("[%d] RELOAD_CONFIG" % time.time())

# AJAX handler for asynchronous replication of user profiles (changed passwords)
def ajax_profile_repl():
    site_id = html.var("site")

    status = html.site_status.get(site_id, {}).get("state", "unknown")
    if status == "dead":
        result = _('The site is marked as dead. Not trying to replicate.')

    else:
        site = config.site(site_id)
        try:
            result = synchronize_profile(site, config.user_id)
        except Exception, e:
            result = str(e)

    if result == True:
        answer = "0 %s" % _("Replication completed successfully.");
    else:
        answer = "1 %s" % (_("Error: %s") % result)
        # Add pending entry to make sync possible later for admins
        update_replication_status(site_id, {"need_sync": True})
        log_pending(AFFECTED, None, "edit-users", _('Password changed (sync failed: %s)') % result)

    html.write(answer)

# AJAX handler for asynchronous site replication
def ajax_replication():
    site_id = html.var("site")
    repstatus = load_replication_status()
    srs = repstatus.get(site_id, {})
    need_sync = srs.get("need_sync", False)
    need_restart = srs.get("need_restart", False)

    # Initialise g_root_folder, load all folder information
    prepare_folder_info()

    site = config.site(site_id)
    try:
        if need_sync:
            result = synchronize_site(site, need_restart)
        else:
            restart_site(site)
            result = True
    except Exception, e:
        result = str(e)
    if result == True:
        answer = "OK:" + _("Success");
        # Make sure that the pending changes are clean as soon as the
        # last site has successfully been updated.
        if is_distributed() and global_replication_state() == "clean":
            log_commit_pending()
    else:
        answer = "<div class=error>%s: %s</div>" % (_("Error"), hilite_errors(result))

    html.write(answer)

#.
#   .--Automation-Webservice-----------------------------------------------.
#   |          _         _                        _   _                    |
#   |         / \  _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __         |
#   |        / _ \| | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \        |
#   |       / ___ \ |_| | || (_) | | | | | | (_| | |_| | (_) | | | |       |
#   |      /_/   \_\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | These function implement a web service with that a master can call   |
#   | automation functions on slaves.                                      |
#   '----------------------------------------------------------------------'

def page_automation_login():
    if not config.may("wato.automation"):
        raise MKAuthException(_("This account has no permission for automation."))
    # When we are here, a remote (master) site has successfully logged in
    # using the credentials of the administrator. The login is done be exchanging
    # a login secret. If such a secret is not yet present it is created on
    # the fly.
    html.write(repr(get_login_secret(True)))

def get_login_secret(create_on_demand = False):
    path = var_dir + "automation_secret.mk"
    try:
        return eval(file(path).read())
    except:
        if not create_on_demand:
            return None
        secret = get_random_string(32)
        write_settings_file(path, secret)
        return secret

def site_is_local(siteid):
    return config.site_is_local(siteid)

# Returns the ID of our site. This function only works in replication
# mode and looks for an entry connecting to the local socket.
def our_site_id():
    if not is_distributed():
        return None
    for site_id in config.allsites():
        if site_is_local(site_id):
            return site_id
    return None

automation_commands = {}

def page_automation():
    secret = html.var("secret")
    if not secret:
        raise MKAuthException(_("Missing secret for automation command."))
    if secret != get_login_secret():
        raise MKAuthException(_("Invalid automation secret."))

    # To prevent mixups in written files we use the same lock here as for
    # the normal WATO page processing. This might not be needed for some
    # special automation requests, like inventory e.g., but to keep it simple,
    # we request the lock in all cases.
    lock_exclusive()

    # Initialise g_root_folder, load all folder information
    prepare_folder_info()

    command = html.var("command")
    if command == "checkmk-automation":
        cmk_command = html.var("automation")
        args   = mk_eval(html.var("arguments"))
        indata = mk_eval(html.var("indata"))
        result = check_mk_local_automation(cmk_command, args, indata)
        html.write(repr(result))

    elif command == "push-snapshot":
        html.write(repr(automation_push_snapshot()))

    elif command == "push-profile":
        html.write(mk_repr(automation_push_profile()))

    elif command in automation_commands:
        html.write(repr(automation_commands[command]()))

    else:
        raise MKGeneralException(_("Invalid automation command: %s.") % command)

def automation_push_profile():
    try:
        site_id = html.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        user_id = html.var("user_id")
        if not user_id:
            raise MKGeneralException(_("Missing variable user_id"))

        our_id = our_site_id()

        # In peer mode, we have a replication configuration ourselves and
        # we have a site ID our selves. Let's make sure that ID matches
        # the ID our peer thinks we have.
        if our_id != None and our_id != site_id:
            raise MKGeneralException(
              _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        profile = html.var("profile")
        if not profile:
            raise MKGeneralException(_('Invalid call: The profile is missing.'))

        users = userdb.load_users(lock = True)
        profile = mk_eval(profile)
        users[user_id] = profile
        userdb.save_users(users)

        return True
    except Exception, e:
        if config.debug:
            return _("Internal automation error: %s\n%s") % (str(e), format_exception())
        else:
            return _("Internal automation error: %s") % e

def automation_push_snapshot():
    try:
        site_id = html.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))
        mode = html.var("mode", "slave")

        our_id = our_site_id()

        if mode == "slave" and is_distributed():
            raise MKGeneralException(_("Configuration error. You treat us as "
               "a <b>slave</b>, but we have an own distributed WATO configuration!"))

        # In peer mode, we have a replication configuration ourselves and
        # we have a site ID our selves. Let's make sure that ID matches
        # the ID our peer thinks we have.
        if our_id != None and our_id != site_id:
            raise MKGeneralException(
              _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        # Make sure there are no local changes we would loose! But only if we are
        # distributed ourselves (meaning we are a peer).
        if is_distributed():
            pending = parse_audit_log("pending")
            if len(pending) > 0:
                message = _("There are %d pending changes that would get lost. The most recent are: ") % len(pending)
                message += ", ".join([e[-1] for e in pending[:10]])
                raise MKGeneralException(message)

        tarcontent = html.uploaded_file("snapshot")
        if not tarcontent:
            raise MKGeneralException(_('Invalid call: The snapshot is missing.'))
        tarcontent = tarcontent[2]

        multitar.extract_from_buffer(tarcontent, replication_paths)

        # We expect one file containing sitespecific global settings.
        # That is contained in the sub-tarball "sitespecific.tar" and
        # just contains one file: "sitespecific.mk". The contains a repr()
        # of all global settings, that should override the ones in global.mk
        # in various directories.
        try:
            tmp_dir = defaults.tmp_dir + "/sitespecific-%s" % id(html)
            if not os.path.exists(tmp_dir):
                make_nagios_directory(tmp_dir)
            multitar.extract_from_buffer(tarcontent, [ ("dir", "sitespecific", tmp_dir) ])
            site_globals = eval(file(tmp_dir + "/sitespecific.mk").read())
            current_settings = load_configuration_settings()
            current_settings.update(site_globals)
            save_configuration_settings(current_settings)
            shutil.rmtree(tmp_dir)
        except Exception, e:
            html.log("Warning: cannot extract site-specific global settings: %s" % e)

        log_commit_pending() # pending changes are lost

        call_hook_snapshot_pushed()

        # Create rule making this site only monitor our hosts
        create_distributed_wato_file(site_id, mode)
        log_audit(None, "replication", _("Synchronized with master (my site id is %s.)") % site_id)
        if html.var("restart", "no") == "yes":
            check_mk_local_automation(config.wato_activation_method)
        return True
    except Exception, e:
        if config.debug:
            return _("Internal automation error: %s\n%s") % (str(e), format_exception())
        else:
            return _("Internal automation error: %s") % e

def create_distributed_wato_file(siteid, mode):
    out = create_user_file(defaults.check_mk_configdir + "/distributed_wato.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("# This file has been created by the master site\n"
              "# push the configuration to us. It makes sure that\n"
              "# we only monitor hosts that are assigned to our site.\n\n")
    out.write("distributed_wato_site = '%s'\n" % siteid)

def delete_distributed_wato_file():
    p = defaults.check_mk_configdir + "/distributed_wato.mk"
    # We do not delete the file but empty it. That way
    # we do not need write permissions to the conf.d
    # directory!
    if os.path.exists(p):
        create_user_file(p, "w").write("")

#.
#   .--Users/Contacts------------------------------------------------------.
#   | _   _                      ______            _             _         |
#   || | | |___  ___ _ __ ___   / / ___|___  _ __ | |_ __ _  ___| |_ ___   |
#   || | | / __|/ _ \ '__/ __| / / |   / _ \| '_ \| __/ _` |/ __| __/ __|  |
#   || |_| \__ \  __/ |  \__ \/ /| |__| (_) | | | | || (_| | (__| |_\__ \  |
#   | \___/|___/\___|_|  |___/_/  \____\___/|_| |_|\__\__,_|\___|\__|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mode for managing users and contacts.                                |
#   '----------------------------------------------------------------------'

def service_levels():
    try:
        return config.mkeventd_service_levels
    except:
        return [(0, "(no service level)")]

# Example header of a notification script:
#!/usr/bin/python
# HTML Emails with included graphs
# Bulk: yes
# Argument 1: Full system path to the pnp4nagios index.php for fetching the graphs. Usually auto configured in OMD.
# Argument 2: HTTP-URL-Prefix to open Multisite. When provided, several links are added to the mail.
#
# This script creates a nifty HTML email in multipart format with
# attached graphs and such neat stuff. Sweet!

def load_notification_scripts_from(adir):
    scripts = {}
    if os.path.exists(adir):
        for entry in os.listdir(adir):
            path = adir + "/" + entry
            if os.path.isfile(path) and os.access(path, os.X_OK):
                info = { "title" : entry, "bulk" : False }
                try:
                    lines = file(path)
                    lines.next()
                    line = lines.next().strip()
                    if line.startswith("#") and "encoding:" in line:
                        line = lines.next().strip()
                    if line.startswith("#"):
                        info["title"] = line.lstrip("#").strip().split("#", 1)[0]
                    while True:
                        line = lines.next().strip()
                        if not line.startswith("#") or ":" not in line:
                            break
                        key, value = line[1:].strip().split(":", 1)
                        value = value.strip()
                        if key.lower() == "bulk":
                            info["bulk"] = (value == "yes")

                except:
                    pass
                scripts[entry] = info
    return scripts


def load_notification_scripts():
    scripts = {}
    try:
        not_dir = defaults.notifications_dir
    except:
        not_dir = defaults.share_dir + "/notifications" # for those with not up-to-date defaults

    scripts = load_notification_scripts_from(not_dir)
    try:
        local_dir = defaults.omd_root + "/local/share/check_mk/notifications"
        scripts.update(load_notification_scripts_from(local_dir))
    except:
        pass

    return scripts

def notification_script_choices():
    scripts = load_notification_scripts()

    choices = [ (name, info["title"].decode('utf-8')) for (name, info) in scripts.items() ]
    choices.append((None, _("ASCII Email (legacy)")))
    choices.sort(cmp = lambda a,b: cmp(a[1], b[1]))
    # Make choices localizable
    choices = [ (k, _(v)) for k, v in choices ]
    return choices


def notification_script_choices_with_parameters():
    choices = []
    for script_name, title in notification_script_choices():
        if script_name in g_notification_parameters:
            vs = g_notification_parameters[script_name]
        else:
            vs = ListOfStrings(
                 title = _("Call with the following parameters:"),
                 valuespec = TextUnicode(size = 24),
                 orientation = "horizontal",
            )
        choices.append((script_name, title,
            Alternative(
                style = "dropdown",
                elements = [
                    vs,
                    FixedValue(None, totext = _("previous notifications of this type are cancelled"),
                               title = _("Cancel previous notifications")),
                ]
            )
        ))
    return choices



def notification_script_title(name):
    return dict(notification_script_choices()).get(name, name)


def load_notification_table():
    # Make sure, that list is not trivially false
    def validate_only_services(value, varprefix):
        for s in value:
            if s and s[0] != '!':
                return
        raise MKUserError(varprefix + "_0", _("The list of services will never match"))

    global vs_notification_method
    vs_notification_method = \
        CascadingDropdown(
            title = _("Notification Method"),
            choices = [
                ( "email", _("Plain Text Email (using configured templates)") ),
                ( "flexible",
                  _("Flexible Custom Notifications"),
                    ListOf(
                        Foldable(
                            Dictionary(
                                optional_keys = [ "service_blacklist", "only_hosts", "only_services", "escalation" , "match_sl"],
                                columns = 1,
                                headers = True,
                                elements = [
                                    (  "plugin",
                                       DropdownChoice(
                                            title = _("Notification Plugin"),
                                            choices = notification_script_choices,
                                            default_value = "mail",
                                        ),
                                    ),
                                    ( "parameters",
                                       ListOfStrings(
                                        title = _("Plugin Arguments"),
                                        help = _("You can specify arguments to the notification plugin here. "
                                                 "Please refer to the documentation about the plugin for what "
                                                 "parameters are allowed or required here."),
                                       )
                                    ),
                                    (  "disabled",
                                       Checkbox(
                                            title = _("Disabled"),
                                            label = _("Currently disable this notification"),
                                            default_value = False,
                                        )
                                    ),
                                    ( "timeperiod",
                                      TimeperiodSelection(
                                          title = _("Timeperiod"),
                                          help = _("Do only notifiy alerts within this time period"),
                                      )
                                    ),
                                    ( "escalation",
                                      Tuple(
                                          title = _("Restrict to n<sup>th</sup> to m<sup>th</sup> notification (escalation)"),
                                          orientation = "float",
                                          elements = [
                                              Integer(
                                                  label = _("from"),
                                                  help = _("Let through notifications counting from this number"),
                                                  default_value = 1,
                                                  minvalue = 1,
                                                  maxvalue = 999999,
                                              ),
                                              Integer(
                                                  label = _("to"),
                                                  help = _("Let through notifications counting upto this number"),
                                                  default_value = 999999,
                                                  minvalue = 1,
                                                  maxvalue = 999999,
                                              ),
                                        ],
                                      ),
                                    ),
                                    ( "match_sl",
                                      Tuple(
                                        title = _("Match service level"),
                                        help = _("Host or Service must be in the following service level to get notification"),
                                        orientation = "horizontal",
                                        show_titles = False,
                                        elements = [
                                          DropdownChoice(label = _("from:"),  choices = service_levels, prefix_values = True),
                                          DropdownChoice(label = _(" to:"),  choices = service_levels, prefix_values = True),
                                        ],
                                      ),
                                    ),
                                  ( "host_events",
                                     ListChoice(
                                          title = _("Host Events"),
                                          choices = [
                                          ( 'd', _("Host goes down")),
                                          ( 'u', _("Host gets unreachble")),
                                          ( 'r', _("Host goes up again")),
                                          ( 'f', _("Start or end of flapping state")),
                                          ( 's', _("Start or end of a scheduled downtime ")),
                                          ( 'x', _("Acknowledgement of host problem")),
                                        ],
                                        default_value = [ 'd', 'u', 'r', 'f', 's', 'x' ],
                                    )
                                  ),
                                    ( "service_events",
                                      ListChoice(
                                          title = _("Service Events"),
                                          choices = [
                                            ( 'w', _("Service goes into warning state")),
                                            ( 'u', _("Service goes into unknown state")),
                                            ( 'c', _("Service goes into critical state")),
                                            ( 'r', _("Service recovers to OK")),
                                            ( 'f', _("Start or end of flapping state")),
                                            ( 's', _("Start or end of a scheduled downtime")),
                                            ( 'x', _("Acknowledgement of service problem")),
                                        ],
                                        default_value = [ 'w', 'c', 'u', 'r', 'f', 's', 'x' ],
                                    )
                                  ),
                                  ( "only_hosts",
                                    ListOfStrings(
                                        title = _("Limit to the following hosts"),
                                        help = _("Configure the hosts for this notification. Without prefix, only exact, case sensitive matches, "
                                                 "<tt>!</tt> for negation and <tt>~</tt> for regex matches."),
                                        orientation = "horizontal",
                                        valuespec = RegExp(size = 20),
                                    ),
                                  ),
                                  ( "only_services",
                                    ListOfStrings(
                                        title = _("Limit to the following services"),
                                        help = _("Configure regular expressions that match the beginning of the service names here. Prefix an "
                                                 "entry with <tt>!</tt> in order to <i>exclude</i> that service."),
                                        orientation = "horizontal",
                                        valuespec = RegExp(size = 20),
                                        validate = validate_only_services,
                                    ),
                                  ),
                                  ( "service_blacklist",
                                    ListOfStrings(
                                        title = _("Blacklist the following services"),
                                        help = _("Configure regular expressions that match the beginning of the service names here."),
                                        orientation = "horizontal",
                                        valuespec = RegExp(size = 20),
                                        validate = validate_only_services,
                                    ),
                                  ),
                                ]
                            ),
                            title_function = lambda v: _("Notify by: ") + notification_script_title(v["plugin"]),
                        ),
                        title = _("Flexible Custom Notifications"),
                        add_label = _("Add notification"),
                    ),
                ),
            ]
        )


def mode_users(phase):
    if phase == "title":
        return _("Users")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New User"), make_link([("mode", "edit_user")]), "new")
        html.context_button(_("Custom Attributes"), make_link([("mode", "user_attrs")]), "custom_attr")
        if 'wato_users' not in config.userdb_automatic_sync:
            html.context_button(_("Sync Users"), html.makeactionuri([("_sync", 1)]), "replicate")
        if config.may("general.notify"):
            html.context_button(_("Notify Users"), 'notify.py', "notification")
        if userdb.connector_enabled('ldap'):
            html.context_button(_("LDAP Settings"), make_link([("mode", "ldap_config")]), "ldap")
        return

    # Execute all connectors synchronisations of users. This must be done before
    # loading the users, because it might modify the users list. But don't execute
    # it during actions, this should save some time.
    if phase != "action" and 'wato_users' in config.userdb_automatic_sync:
        userdb.hook_sync(add_to_changelog = True)

    roles = userdb.load_roles()
    users = filter_hidden_users(userdb.load_users(lock = phase == 'action' and html.var('_delete')))
    timeperiods = load_timeperiods()
    contact_groups = userdb.load_group_information().get("contact", {})

    if phase == "action":
        if html.var('_delete'):
            delid = html.var("_delete")
            if delid == config.user_id:
                raise MKUserError(None, _("You cannot delete your own account!"))

            if delid not in users:
                return None # The account does not exist (anymore), no deletion needed

            c = wato_confirm(_("Confirm deletion of user %s" % delid),
                             _("Do you really want to delete the user %s?" % delid))
            if c:
                del users[delid]
                userdb.save_users(users)
                log_pending(SYNCRESTART, None, "edit-users", _("Deleted user %s" % (delid)))
            elif c == False:
                return ""
        elif html.var('_sync'):
            try:
                if userdb.hook_sync(add_to_changelog = True, raise_exc = True):
                    return None, _('The user synchronization completed successfully.')
            except Exception, e:
                if config.debug:
                    import traceback
                    raise MKUserError(None, traceback.format_exc().replace('\n', '<br>\n'))
                else:
                    raise MKUserError(None, str(e))

        return None

    visible_custom_attrs = [
        (name, attr)
        for name, attr
        in userdb.get_user_attributes()
        if attr.get('show_in_table', False)
    ]

    entries = users.items()
    entries.sort(cmp = lambda a, b: cmp(a[1].get("alias", a[0]).lower(), b[1].get("alias", b[0]).lower()))

    table.begin("users", None, empty_text = _("No users are defined yet."))
    online_threshold = time.time() - config.user_online_maxage
    for id, user in entries:
        table.row()

        connector = userdb.get_connector(user.get('connector'))

        # Buttons
        table.cell(_("Actions"), css="buttons")
        if connector: # only show edit buttons when the connector is available and enabled
            edit_url = make_link([("mode", "edit_user"), ("edit", id)])
            html.icon_button(edit_url, _("Properties"), "edit")

            clone_url = make_link([("mode", "edit_user"), ("clone", id)])
            html.icon_button(clone_url, _("Create a copy of this user"), "clone")

        delete_url = html.makeactionuri([("_delete", id)])
        html.icon_button(delete_url, _("Delete"), "delete")

        notifications_url = make_link([("mode", "user_notifications"), ("user", id)])
        if load_configuration_settings().get("enable_rulebased_notifications"):
            html.icon_button(notifications_url, _("Custom notification table of this user"), "notifications")

        # ID
        table.cell(_("ID"), id)

        # Online/Offline
        if config.save_user_access_times:
            last_seen = user.get('last_seen', 0)
            if last_seen >= online_threshold:
                title = _('Online')
                img_txt = 'on'
            else:
                title = _('Offline')
                img_txt = 'off'
            title += ' (%s %s)' % (fmt_date(last_seen), fmt_time(last_seen))
            table.cell(_("Act."), '<img class=icon title="%s" src="images/icon_%sline.png" />' % (title, img_txt))

        # Connector
        if connector:
            table.cell(_("Connector"), connector['short_title'])
            locked_attributes = userdb.locked_attributes(user.get('connector'))
        else:
            table.cell(_("Connector"), "%s (disabled)" % userdb.get_connector_id(user.get('connector')), css="error")
            locked_attributes = []

        # Authentication
        if "automation_secret" in user:
            auth_method = _("Automation")
        elif user.get("password") or 'password' in locked_attributes:
            auth_method = _("Password")
        else:
            auth_method = "<i>%s</i>" % _("none")
        table.cell(_("Authentication"), auth_method)

        table.cell(_("State"))
        locked = user.get("locked", False)
        if user.get("locked", False):
            html.icon(_('The login is currently locked'), 'user_locked')
        if user.get("disable_notifications", False):
            html.icon(_('Notifications are disabled'), 'notif_disabled')

        # Full name / Alias
        table.cell(_("Alias"), user.get("alias", ""))

        # Email
        table.cell(_("Email"), user.get("email", ""))

        # Roles
        table.cell(_("Roles"))
        if user.get("roles", []):
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_role"), ("edit", r)]), roles[r].get('alias')) for r in user["roles"]]))

        # contact groups
        table.cell(_("Contact groups"))
        cgs = user.get("contactgroups", [])
        if cgs:
            html.write(", ".join(
               [ '<a href="%s">%s</a>' % (make_link([("mode", "edit_contact_group"), ("edit", c)]),
                                          c in contact_groups and contact_groups[c]['alias'] or c) for c in cgs]))
        else:
            html.write("<i>" + _("none") + "</i>")

        # notifications
        if not load_configuration_settings().get("enable_rulebased_notifications"):
            table.cell(_("Notifications"))
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
                else:
                    tp = _("Always")
                html.write(tp)

        # the visible custom attributes
        for name, attr in visible_custom_attrs:
            vs = attr['valuespec']
            table.cell(_u(vs.title()))
            html.write(vs.value_to_text(user.get(name, vs.default_value())))

    table.end()

    if not userdb.load_group_information().get("contact", {}):
        url = "wato.py?mode=contact_groups"
        html.write("<div class=info>" +
            _("Note: you haven't defined any contact groups yet. If you <a href='%s'>"
              "create some contact groups</a> you can assign users to them und thus "
              "make them monitoring contacts. Only monitoring contacts can receive "
              "notifications.") % url + "</div>")



def mode_edit_user(phase):
    # Check if rule based notifications are enabled (via WATO)
    rulebased_notifications = load_configuration_settings().get("enable_rulebased_notifications")

    users = userdb.load_users(lock = phase == 'action')
    userid = html.var("edit") # missing -> new user
    cloneid = html.var("clone") # Only needed in 'new' mode
    new = userid == None
    if phase == "title":
        if new:
            return _("Create new user")
        else:
            return _("Edit user %s" % userid)

    elif phase == "buttons":
        html.context_button(_("All Users"), make_link([("mode", "users")]), "back")
        if rulebased_notifications and not new:
            html.context_button(_("Notifications"), make_link([("mode", "user_notifications"),
                    ("user", userid)]), "notifications")
        return

    if new:
        if cloneid:
            user = users.get(cloneid, userdb.new_user_template('htpasswd'))
        else:
            user = userdb.new_user_template('htpasswd')
        pw_suffix = 'new'
    else:
        user = users.get(userid, userdb.new_user_template('htpasswd'))
        pw_suffix = userid

    # Returns true if an attribute is locked and should be read only. Is only
    # checked when modifying an existing user
    locked_attributes = userdb.locked_attributes(user.get('connector'))
    def is_locked(attr):
        return not new and attr in locked_attributes

    def custom_user_attributes(topic = None):
        for name, attr in userdb.get_user_attributes():
            if topic is not None and topic != attr['topic']:
                continue # skip attrs of other topics

            vs = attr['valuespec']
            forms.section(_u(vs.title()))
            if attr['user_editable'] and not is_locked(name):
                vs.render_input("ua_" + name, user.get(name, vs.default_value()))
            else:
                html.write(vs.value_to_text(user.get(name, vs.default_value())))
                # Render hidden to have the values kept after saving
                html.write('<div style="display:none">')
                vs.render_input("ua_" + name, user.get(name, vs.default_value()))
                html.write('</div>')
            html.help(_u(vs.help()))

    # Load data that is referenced - in order to display dropdown
    # boxes and to check for validity.
    contact_groups = userdb.load_group_information().get("contact", {})
    timeperiods = load_timeperiods()
    roles = userdb.load_roles()

    if phase == "action":
        if not html.check_transaction():
            return "users"

        id = html.var("userid").strip()
        if new and id in users:
            raise MKUserError("userid", _("This username is already being used by another user."))
        if not re.match("^[-a-z0-9A-Z_\.@]+$", id):
            raise MKUserError("userid", _("The username must consist only of letters, digits, <tt>@</tt>, <tt>_</tt> or colon."))

        if new:
            new_user = {}
            users[id] = new_user
        else:
            new_user = users[id]

        # Full name
        alias = html.var_utf8("alias").strip()
        if not alias:
            raise MKUserError("alias",
            _("Please specify a full name or descriptive alias for the user."))
        new_user["alias"] = alias

        # Locking
        if id == config.user_id and html.get_checkbox("locked"):
            raise MKUserError("locked", _("You cannot lock your own account!"))
        new_user["locked"] = html.get_checkbox("locked")

        increase_serial = False
        if users[id] != new_user["locked"] and new_user["locked"]:
            increase_serial = True # when user is being locked now, increase the auth serial

        # Authentication: Password or Secret
        auth_method = html.var("authmethod")
        if auth_method == "secret":
            secret = html.var("secret", "").strip()
            if not secret or len(secret) < 10:
                raise MKUserError('secret', _("Please specify a secret of at least 10 characters length."))
            new_user["automation_secret"] = secret
            new_user["password"] = userdb.encrypt_password(secret)
            increase_serial = True # password changed, reflect in auth serial

        else:
            password = html.var("password_" + pw_suffix, '').strip()
            password2 = html.var("password2_" + pw_suffix, '').strip()

            # Detect switch back from automation to password
            if "automation_secret" in new_user:
                del new_user["automation_secret"]
                if "password" in new_user:
                    del new_user["password"] # which was the encrypted automation password!

            # We compare both passwords only, if the user has supplied
            # the repeation! We are so nice to our power users...
            if password2 and password != password2:
                raise MKUserError("password2", _("The both passwords do not match."))

            if password:
                verify_password_policy(password)
                new_user["password"] = userdb.encrypt_password(password)
                new_user['last_pw_change'] = int(time.time())
                increase_serial = True # password changed, reflect in auth serial

            # PW change enforcement
            new_user["enforce_pw_change"] = html.get_checkbox("enforce_pw_change")
            if new_user["enforce_pw_change"]:
                increase_serial = True # invalidate all existing user sessions, enforce relogon


        # Increase serial (if needed)
        if increase_serial:
            new_user['serial'] = new_user.get('serial', 0) + 1

        # Email address
        email = html.var("email", '').strip()
        regex_email = '^[-a-zäöüÄÖÜA-Z0-9_.+%]+@[-a-zäöüÄÖÜA-Z0-9]+(\.[-a-zäöüÄÖÜA-Z0-9]+)*$'
        if email and not re.match(regex_email, email):
            raise MKUserError("email", _("'%s' is not a valid email address." % email))
        new_user["email"] = email

        # Pager
        pager = html.var("pager", '').strip()
        new_user["pager"] = pager

        # Roles
        new_user["roles"] = filter(lambda role: html.get_checkbox("role_" + role),
                                   roles.keys())

        # Language configuration
        set_lang = html.get_checkbox('_set_lang')
        language = html.var('language')
        if set_lang:
            if language == '':
                language = None
            new_user['language'] = language
        elif not set_lang and 'language' in new_user:
            del new_user['language']

        # Contact groups
        cgs = []
        for c in contact_groups:
            if html.get_checkbox("cg_" + c):
                cgs.append(c)
        new_user["contactgroups"] = cgs

        # Notification settings are only active if we do *not* have
        # rule based notifications!
        if not rulebased_notifications:
            # Notifications
            new_user["notifications_enabled"] = html.get_checkbox("notifications_enabled")

            # Check if user can receive notifications
            if new_user["notifications_enabled"]:
                if not new_user["email"]:
                    raise MKUserError("email",
                         _('You have enabled the notifications but missed to configure a '
                           'Email address. You need to configure your mail address in order '
                           'to be able to receive emails.'))

                if not new_user["contactgroups"]:
                    raise MKUserError("notifications_enabled",
                         _('You have enabled the notifications but missed to make the '
                           'user member of at least one contact group. You need to make '
                           'the user member of a contact group which has hosts assigned '
                           'in order to be able to receive emails.'))

                if not new_user["roles"]:
                    raise MKUserError("role_user",
                        _("Your user has no roles. Please assign at least one role."))

            ntp = html.var("notification_period")
            if ntp not in timeperiods:
                ntp = "24X7"
            new_user["notification_period"] = ntp

            for what, opts in [ ( "host", "durfs"), ("service", "wucrfs") ]:
                new_user[what + "_notification_options"] = "".join(
                  [ opt for opt in opts if html.get_checkbox(what + "_" + opt) ])

            value = vs_notification_method.from_html_vars("notification_method")
            vs_notification_method.validate_value(value, "notification_method")
            new_user["notification_method"] = value

        # Custom user attributes
        for name, attr in userdb.get_user_attributes():
            value = attr['valuespec'].from_html_vars('ua_' + name)
            attr['valuespec'].validate_value(value, "ua_" + name)
            new_user[name] = value

        # Saving
        userdb.save_users(users)
        if new:
            log_pending(SYNCRESTART, None, "edit-users", _("Create new user %s" % id))
        else:
            log_pending(SYNCRESTART, None, "edit-users", _("Modified user %s" % id))
        return "users"

    # Let exceptions from loading notification scripts happen now
    load_notification_scripts()

    html.begin_form("user")
    forms.header(_("Identity"))

    # ID
    forms.section(_("Username"), simple = not new)
    if new:
        html.text_input("userid", userid)
        html.set_focus("userid")
    else:
        html.write(userid)
        html.hidden_field("userid", userid)

    def lockable_input(name, dflt):
        if not is_locked(name):
            html.text_input(name, user.get(name, dflt), size = 50)
        else:
            html.write(user.get(name, dflt))
            html.hidden_field(name, user.get(name, dflt))

    # Full name
    forms.section(_("Full name"))
    lockable_input('alias', userid)
    html.help(_("Full name or alias of the user"))

    # Email address
    forms.section(_("Email address"))
    lockable_input('email', '')
    html.help(_("The email address is optional and is needed "
                "if the user is a monitoring contact and receives notifications "
                "via Email."))

    forms.section(_("Pager address"))
    lockable_input('pager', '')
    html.help(_("The pager address is optional "))
    custom_user_attributes('ident')

    forms.header(_("Security"))
    forms.section(_("Authentication"))
    is_automation = user.get("automation_secret", None) != None
    html.radiobutton("authmethod", "password", not is_automation,
                     _("Normal user login with password"))
    html.write("<ul><table><tr><td>%s</td><td>" % _("password:"))
    if not is_locked('password'):
        html.password_input("password_" + pw_suffix, autocomplete="off")
        html.write("</td></tr><tr><td>%s</td><td>" % _("repeat:"))
        html.password_input("password2_" + pw_suffix, autocomplete="off")
        html.write(" (%s)" % _("optional"))
        html.write("</td></tr><tr><td>%s:</td><td>" % _("Enforce change"))
        # Only make password enforcement selection possible when user is allowed to change the PW
        if new or config.user_may(userid, 'general.edit_profile') and config.user_may(userid, 'general.change_password'):
            html.checkbox("enforce_pw_change", user.get("enforce_pw_change", False),
                          label=_("Change password at next login or access"))
        else:
            html.write(_("Not permitted to change the password. Change can not be enforced."))
    else:
        html.write('<i>%s</i>' % _('The password can not be changed (It is locked by the user connector).'))
        html.hidden_field('password', '')
        html.hidden_field('password2', '')
    html.write("</td></tr></table></ul>")
    html.radiobutton("authmethod", "secret", is_automation,
                     _("Automation secret for machine accounts"))
    html.write("<ul>")
    html.text_input("secret", user.get("automation_secret", ""), size=30,
                    id="automation_secret")
    html.write(" ")
    html.write("<b style='position: relative; top: 4px;'> &nbsp;")
    html.icon_button("javascript:wato_randomize_secret('automation_secret', 20);",
                _("Create random secret"), "random")
    html.write("</b>")
    html.write("</ul>")

    html.help(_("If you want the user to be able to login "
                "then specify a password here. Users without a login make sense "
                "if they are monitoring contacts that are just used for "
                "notifications. The repetition of the password is optional. "
                "<br>For accounts used by automation processes (such as fetching "
                "data from views for further procession), set the method to "
                "<u>secret</u>. The secret will be stored in a local file. Processes "
                "with read access to that file will be able to use Multisite as "
                "a webservice without any further configuration."))

    # Locking
    forms.section(_("Disable password"), simple=True)
    if not is_locked('locked'):
        html.checkbox("locked", user.get("locked", False), label = _("disable the login to this account"))
    else:
        html.write(user.get("locked", False) and _('Login disabled') or _('Login possible'))
        html.hidden_field('locked', user.get("locked", False) and '1' or '')
    html.help(_("Disabling the password will prevent a user from logging in while "
                 "retaining the original password. Notifications are not affected "
                 "by this setting."))

    # Roles
    forms.section(_("Roles"))
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))
    is_member_of_at_least_one = False
    for role_id, role in entries:
        if not is_locked('roles'):
            html.checkbox("role_" + role_id, role_id in user.get("roles", []))
            url = make_link([("mode", "edit_role"), ("edit", role_id)])
            html.write("<a href='%s'>%s</a><br>" % (url, role["alias"]))
        else:
            is_member = role_id in user.get("roles", [])
            if is_member:
                is_member_of_at_least_one = True

                url = make_link([("mode", "edit_role"), ("edit", role_id)])
                html.write("<a href='%s'>%s</a><br>" % (url, role["alias"]))

            html.hidden_field("role_" + role_id, is_member and '1' or '')
    if is_locked('roles') and not is_member_of_at_least_one:
        html.write('<i>%s</i>' % _('No roles assigned.'))
    custom_user_attributes('security')

    # Contact groups
    forms.header(_("Contact Groups"), isopen=False)
    forms.section()
    url1 = make_link([("mode", "contact_groups")])
    url2 = make_link([("mode", "rulesets"), ("group", "grouping")])
    if len(contact_groups) == 0:
        html.write(_("Please first create some <a href='%s'>contact groups</a>") %
                url1)
    else:
        entries = [ (group['alias'], c) for c, group in contact_groups.items() ]
        entries.sort()
        is_member_of_at_least_one = False
        for alias, gid in entries:
            if not alias:
                alias = gid
            if not is_locked('contactgroups'):
                html.checkbox("cg_" + gid, gid in user.get("contactgroups", []))
                url = make_link([("mode", "edit_contact_group"), ("edit", gid)])
                html.write(" <a href=\"%s\">%s</a><br>" % (url, alias))
            else:
                is_member = gid in user.get("contactgroups", [])
                if is_member:
                    is_member_of_at_least_one = True

                    url = make_link([("mode", "edit_contact_group"), ("edit", gid)])
                    html.write("<a href='%s'>%s</a><br>" % (url, alias))

                html.hidden_field("cg_" + gid, is_member and '1' or '')

        if is_locked('contactgroups') and not is_member_of_at_least_one:
            html.write('<i>%s</i>' % _('No contact groups assigned.'))

    html.help(_("Contact groups are used to assign monitoring "
                "objects to users. If you haven't defined any contact groups yet, "
                "then first <a href='%s'>do so</a>. Hosts and services can be "
                "assigned to contact groups using <a href='%s'>rules</a>.<br><br>"
                "If you do not put the user into any contact group "
                "then no monitoring contact will be created for the user.") % (url1, url2))

    if not rulebased_notifications:
        forms.header(_("Notifications"), isopen=False)

        forms.section(_("Enabling"), simple=True)
        html.checkbox("notifications_enabled", user.get("notifications_enabled", False),
             label = _("enable notifications"))
        html.help(_("Notifications are sent out "
                    "when the status of a host or service changes."))

        # Notification period
        forms.section(_("Notification time period"))
        choices = [ ( "24X7", _("Always")) ] + \
                  [ ( id, "%s" % (tp["alias"])) for (id, tp) in timeperiods.items() ]
        html.sorted_select("notification_period", choices, user.get("notification_period"))
        html.help(_("Only during this time period the "
                     "user will get notifications about host or service alerts."))

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

        forms.section(_("Notification Options"))
        for title, what, opts in [ ( _("Host events"), "host", "durfs"),
                      (_("Service events"), "service", "wucrfs") ]:
            html.write("%s:<ul>" % title)
            user_opts = user.get(what + "_notification_options", opts)
            for opt in opts:
                opt_name = notification_option_names[what].get(opt,
                       notification_option_names["both"].get(opt))
                html.checkbox(what + "_" + opt, opt in user_opts, label = opt_name)
                html.write("<br>")
            html.write("</ul>")
        html.help(_("Here you specify which types of alerts "
                   "will be notified to this contact. Note: these settings will only be saved "
                   "and used if the user is member of a contact group."))

        forms.section(_("Notification Method"))
        vs_notification_method.render_input("notification_method", user.get("notification_method"))
        custom_user_attributes('notify')

    forms.header(_("Personal Settings"), isopen = False)
    select_language(user)
    custom_user_attributes('personal')

    # TODO: Later we could add custom macros here, which
    # then could be used for notifications. On the other hand,
    # if we implement some check_mk --notify, we could directly
    # access the data in the account with the need to store
    # values in the monitoring core. We'll see what future brings.
    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def filter_hidden_users(users):
    if config.wato_hidden_users:
        return dict([ (id, user) for id, user in users.items() if id not in config.wato_hidden_users ])
    else:
        return users


def generate_wato_users_elements_function(none_value, only_contacts = False):
    def get_wato_users(nv):
        users = filter_hidden_users(userdb.load_users())
        elements = [ (name, "%s - %s" % (name, us.get("alias", name)))
                     for (name, us)
                     in users.items()
                     if (not only_contacts or us.get("contactgroups")) ]
        elements.sort()
        if nv != None:
            elements = [ (None, none_value) ] + elements
        return elements
    return lambda: get_wato_users(none_value)


# Dropdown for choosing a multisite user
class UserSelection(DropdownChoice):
    def __init__(self, **kwargs):
        only_contacts = kwargs.get("only_contacts", False)
        kwargs["choices"] = generate_wato_users_elements_function(kwargs.get("none"), only_contacts = only_contacts)
        DropdownChoice.__init__(self, **kwargs)

    def value_to_text(self, value):
        text = DropdownChoice.value_to_text(self, value)
        return text.split(" - ")[-1]


#.
#   .--Roles---------------------------------------------------------------.
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
#   | configuration of all roles.                                          |
#   '----------------------------------------------------------------------'

def mode_roles(phase):
    if phase == "title":
        return _("Roles & Permissions")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Matrix"), make_link([("mode", "role_matrix")]), "matrix")
        return

    roles = userdb.load_roles()
    users = filter_hidden_users(userdb.load_users())

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
                update_login_sites_replication_status()
                log_pending(AFFECTED, None, "edit-roles", _("Deleted role '%s'" % delid))
            elif c == False:
                return ""
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
                update_login_sites_replication_status()
                log_pending(AFFECTED, None, "edit-roles", _("Created new role '%s'" % newid))
        return

    table.begin("roles")

    # Show table of builtin and user defined roles
    entries = roles.items()
    entries.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))

    for id, role in entries:
        table.row()

        # Actions
        table.cell(_("Actions"), css="buttons")
        edit_url = make_link([("mode", "edit_role"), ("edit", id)])
        clone_url = html.makeactionuri([("_clone", id)])
        delete_url = html.makeactionuri([("_delete", id)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Clone"), "clone")
        if not role.get("builtin"):
            html.icon_button(delete_url, _("Delete this role"), "delete")

        # ID
        table.cell(_("Name"), id)

        # Alias
        table.cell(_("Alias"), role["alias"])

        # Type
        table.cell(_("Type"), role.get("builtin") and _("builtin") or _("custom"))

        # Modifications
        table.cell(_("Modifications"), "<span title='%s'>%s</span>" % (
            _("That many permissions do not use the factory defaults."), len(role["permissions"])))

        # Users
        table.cell(_("Users"),
          ", ".join([ '<a href="%s">%s</a>' % (make_link([("mode", "edit_user"), ("edit", user_id)]),
             user.get("alias", user_id))
            for (user_id, user) in users.items() if (id in user["roles"])]))


    # Possibly we could also display the following information
    # - number of set permissions (needs loading users)
    # - number of users with this role
    table.end()





def mode_edit_role(phase):
    id = html.var("edit")

    if phase == "title":
        return _("Edit user role %s") % id

    elif phase == "buttons":
        html.context_button(_("All Roles"), make_link([("mode", "roles")]), "back")
        return

    # Make sure that all dynamic permissions are available (e.g. those for custom
    # views)
    config.load_dynamic_permissions()

    roles = userdb.load_roles()
    role = roles[id]

    if phase == "action":
        alias = html.var_utf8("alias")

        unique, info = is_alias_used("roles", id, alias)
        if not unique:
            raise MKUserError("alias", info)

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
        update_login_sites_replication_status()
        log_pending(AFFECTED, None, "edit-roles", _("Modified user role '%s'" % new_id))
        return "roles"

    html.begin_form("role", method="POST")

    # ID
    forms.header(_("Basic Properties"))
    forms.section(_("Internal ID"), simple = "builtin" in role)
    if role.get("builtin"):
        html.write("%s (%s)" % (id, _("builtin role")))
        html.hidden_field("id", id)
    else:
        html.text_input("id", id)
        html.set_focus("id")

    # Alias
    forms.section(_("Alias"))
    html.help(_("An alias or description of the role"))
    html.text_input("alias", role.get("alias", ""), size = 50)

    # Based on
    if not role.get("builtin"):
        forms.section(_("Based on role"))
        html.help(_("Each user defined role is based on one of the builtin roles. "
                    "When created it will start with all permissions of that role. When due to a software "
                    "update or installation of an addons new permissions appear, the user role will get or "
                    "not get those new permissions based on the default settings of the builtin role it's "
                    "based on."))
        choices = [ (i, r["alias"]) for i, r in roles.items() if r.get("builtin") ]
        html.sorted_select("basedon", choices, role.get("basedon", "user"))


    # Permissions
    base_role_id = role.get("basedon", id)

    html.help(
       _("When you leave the permissions at &quot;default&quot; then they get their "
         "settings from the factory defaults (for builtin roles) or from the "
         "factory default of their base role (for user define roles). Factory defaults "
         "may change due to software updates. When choosing another base role, all "
         "permissions that are on default will reflect the new base role."))

    # Loop all permission sections, but sorted plz
    for section, (prio, section_title, do_sort) in sorted(config.permission_sections.iteritems(),
                                                 key = lambda x: x[1][0], reverse = True):
        forms.header(section_title, False)

        # Loop all permissions
        permlist = config.permissions_by_order[:]
        if do_sort:
            permlist.sort(cmp = lambda a,b: cmp(a["title"], b["title"]))

        for perm in permlist:
            pname = perm["name"]
            this_section = pname.split(".")[0]
            if section != this_section:
                continue # Skip permissions of other sections

            forms.section(perm["title"])

            pvalue = role["permissions"].get(pname)
            def_value = base_role_id in perm["defaults"]

            choices = [ ( "yes", _("yes")),
                        ( "no", _("no")),
                        ( "default", _("default (%s)") % (def_value and _("yes") or _("no") )) ]
            html.select("perm_" + pname, choices, { True: "yes", False: "no" }.get(pvalue, "default"), attrs={"style": "width: 130px;"} )

            html.help(perm["description"])

    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def make_unicode(s):
    if type(s) != unicode: # assume utf-8 encoded bytestring
        return s.decode("utf-8")
    else:
	return s

def save_roles(roles):
    # Reflect the data in the roles dict kept in the config module Needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    config.roles.update(roles)

    make_nagios_directory(multisite_dir)
    filename = multisite_dir + "roles.mk"
    out = create_user_file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("roles.update(\n%s)\n" % pprint.pformat(roles))

    call_hook_roles_saved(roles)


# Adapt references in users. Builtin rules cannot
# be renamed and are not handled here. If new_id is None,
# the role is being deleted
def rename_user_role(id, new_id):
    users = userdb.load_users(lock = True)
    for user in users.values():
        if id in user["roles"]:
            user["roles"].remove(id)
            if new_id:
                user["roles"].append(new_id)
    userdb.save_users(users)

def mode_role_matrix(phase):
    if phase == "title":
        return _("Role & Permission Matrix")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Back"), make_link([("mode", "roles")]), "back")
        return

    elif phase == "action":
        return

    # Show table of builtin and user defined roles, sorted by alias
    roles = userdb.load_roles()
    role_list = roles.items()
    role_list.sort(cmp = lambda a,b: cmp((a[1]["alias"],a[0]), (b[1]["alias"],b[0])))

    html.write("<table class=data>")
    html.write("<tr class=dualheader><th></th>")
    num_roles = 1
    for id, role in role_list:
        html.write('<th>%s</th>' % role['alias'])
        num_roles += 1
    html.write("</tr>\n")

    # Loop all permission sections, but sorted plz
    odd = "even"
    for section, (prio, section_title, do_sort) in sorted(config.permission_sections.iteritems(),
                                                 key = lambda x: x[1][0], reverse = True):

        html.write('<tr>')
        html.write('<th colspan=%d>%s</th>' % (num_roles, section_title))
        html.write('</tr>')

        # Loop all permissions
        permlist = config.permissions_by_order[:]
        if do_sort:
            permlist.sort(cmp = lambda a,b: cmp(a["title"], b["title"]))

        for perm in permlist:
            pname = perm["name"]
            this_section = pname.split(".")[0]
            if section != this_section:
                continue # Skip permissions of other sections

            odd = odd == "odd" and "even" or "odd"

            html.write('<tr class="data %s0">' % odd)
            html.write('<td class=title>%s</td>' % perm["title"])

            for id, role in role_list:
                base_on_id = role.get('basedon', id)
                pvalue = role["permissions"].get(pname)
                if pvalue is None:
                    pvalue = base_on_id in perm["defaults"]

                html.write('<td>%s</td>' % (pvalue and 'X' or ''))

            html.write('</tr>')

    html.write("</table>")

#.
#   .--Host-Tags-----------------------------------------------------------.
#   |              _   _           _     _____                             |
#   |             | | | | ___  ___| |_  |_   _|_ _  __ _ ___               |
#   |             | |_| |/ _ \/ __| __|   | |/ _` |/ _` / __|              |
#   |             |  _  | (_) \__ \ |_    | | (_| | (_| \__ \              |
#   |             |_| |_|\___/|___/\__|   |_|\__,_|\__, |___/              |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   | Manage the variable config.wato_host_tags -> The set of tags to be   |
#   | assigned to hosts and that is the basis of the rules.                |
#   '----------------------------------------------------------------------'

def parse_hosttag_title(title):
    if '/' in title:
        return title.split('/', 1)
    else:
        return None, title

def hosttag_topics(hosttags, auxtags):
    names = set([])
    for entry in hosttags + auxtags:
        topic, title = parse_hosttag_title(entry[1])
        if topic:
            names.add((topic, topic))
    return list(names)

def group_hosttags_by_topic(hosttags):
    tags = {}
    for entry in hosttags:
        topic, title = parse_hosttag_title(entry[1])
        if not topic:
            topic = _('Host tags')
        tags.setdefault(topic, [])
        tags[topic].append((entry[0], title) + entry[2:])
    return sorted(tags.items(), key = lambda x: x[0])


def mode_hosttags(phase):
    if phase == "title":
        return _("Host tag groups")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("New Tag group"), make_link([("mode", "edit_hosttag")]), "new")
        html.context_button(_("New Aux tag"), make_link([("mode", "edit_auxtag")]), "new")
        return

    hosttags, auxtags = load_hosttags()

    if phase == "action":
        # Deletion of tag groups
        del_id = html.var("_delete")
        if del_id:
            for e in hosttags:
                if e[0] == del_id:
                    # In case of tag group deletion, the operations is a pair of tag_id
                    # and list of choice-ids.
                    operations = [ x[0] for x in e[2] ]

            message = rename_host_tags_after_confirmation(del_id, operations)
            if message == True: # no confirmation yet
                c = wato_confirm(_("Confirm deletion of the host "
                                   "tag group '%s'") % del_id,
                                _("Do you really want to delete the "
                                  "host tag group '%s'?") % del_id)
                if c == False:
                    return ""
                elif c == None:
                    return None

            if message:
                hosttags = [ e for e in hosttags if e[0] != del_id ]
                save_hosttags(hosttags, auxtags)
                rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts
                log_pending(SYNCRESTART, None, "edit-hosttags", _("Removed host tag group %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        # Deletion of auxiliary tags
        del_nr = html.var("_delaux")
        if del_nr:
            nr = int(del_nr)
            del_id = auxtags[nr][0]

            # Make sure that this aux tag is not begin used by any tag group
            for entry in hosttags:
                choices = entry[2]
                for e in choices:
                    if len(e) > 2:
                        if del_id in e[2]:
                            raise MKUserError(None, _("You cannot delete this auxiliary tag. "
                               "It is being used in the tag group <b>%s</b>.") % entry[1])

            operations = { del_id : False }
            message = rename_host_tags_after_confirmation(None, operations)
            if message == True: # no confirmation yet
                c = wato_confirm(_("Confirm deletion of the auxiliary "
                                   "tag '%s'") % del_id,
                                _("Do you really want to delete the "
                                  "auxiliary tag '%s'?") % del_id)
                if c == False:
                    return ""
                elif c == None:
                    return None

            if message:
                del auxtags[nr]
                # Remove auxiliary tag from all host tags
                for e in hosttags:
                    choices = e[2]
                    for choice in choices:
                        if len(choice) > 2:
                            if del_id in choice[2]:
                                choice[2].remove(del_id)

                save_hosttags(hosttags, auxtags)
                rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts
                log_pending(SYNCRESTART, None, "edit-hosttags", _("Removed auxiliary tag %s (%s)") % (message, del_id))
                return "hosttags", message != True and message or None

        move_nr = html.var("_move")
        if move_nr != None:
            if html.check_transaction():
                move_nr = int(move_nr)
                if move_nr >= 0:
                    dir = 1
                else:
                    move_nr = -move_nr
                    dir = -1
                moved = hosttags[move_nr]
                del hosttags[move_nr]
                hosttags[move_nr+dir:move_nr+dir] = [moved]
                save_hosttags(hosttags, auxtags)
                config.wato_host_tags = hosttags
                log_pending(SYNCRESTART, None, "edit-hosttags", _("Changed order of host tag groups"))
        return

    if len(hosttags) + len(auxtags) == 0:
        render_main_menu([
            ("edit_hosttag", _("Create new tag group"), "new", "hosttags",
                _("Each host tag group will create one dropdown choice in the host configuration.")),
            ("edit_auxtag", _("Create new auxiliary tag"), "new", "hosttags",
                _("You can have these tags automatically added if certain primary tags are set.")),
            ])

    else:
        table.begin("hosttags", _("Host tag groups"),
                    help = (_("Host tags are the basis of Check_MK's rule based configuration. "
                             "If the first step you define arbitrary tag groups. A host "
                             "has assigned exactly one tag out of each group. These tags can "
                             "later be used for defining parameters for hosts and services, "
                             "such as <i>disable notifications for all hosts with the tags "
                             "<b>Network device</b> and <b>Test</b></i>.")),
                    empty_text = _("You haven't defined any tag groups yet."),
                    searchable = False, sortable = False)

        if hosttags:
            for nr, entry in enumerate(hosttags):
                tag_id, title, choices = entry[:3] # fourth: tag dependency information
                topic, title = map(_u, parse_hosttag_title(title))
                table.row()
                edit_url     = make_link([("mode", "edit_hosttag"), ("edit", tag_id)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delete", tag_id)])
                table.cell(_("Actions"), css="buttons")
                if nr == 0:
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(-nr))]),
                                _("Move this tag group one position up"), "up")
                if nr == len(hosttags) - 1:
                    html.empty_icon_button()
                else:
                    html.icon_button(make_action_link([("mode", "hosttags"), ("_move", str(nr))]),
                                _("Move this tag group one position down"), "down")
                html.icon_button(edit_url,   _("Edit this tag group"), "edit")
                html.icon_button(delete_url, _("Delete this tag group"), "delete")

                table.cell(_("ID"), tag_id)
                table.cell(_("Title"), title)
                table.cell(_("Topic"), topic or '')
                table.cell(_("Type"), (len(choices) == 1 and _("Checkbox") or _("Dropdown")))
                table.cell(_("Choices"), str(len(choices)))
                table.cell(_("Demonstration"), sortable=False)
                html.begin_form("tag_%s" % tag_id)
                host_attribute["tag_%s" % tag_id].render_input(None)
                html.end_form()
        table.end()

        table.begin("auxtags", _("Auxiliary tags"),
                    help = _("Auxiliary tags can be attached to other tags. That way "
                             "you can for example have all hosts with the tag <tt>cmk-agent</tt> "
                             "get also the tag <tt>tcp</tt>. This makes the configuration of "
                             "your hosts easier."),
                    empty_text = _("You haven't defined any auxiliary tags."),
                    searchable = False)

        if auxtags:
            for nr, (tag_id, title) in enumerate(auxtags):
                table.row()
                topic, title = parse_hosttag_title(title)
                edit_url     = make_link([("mode", "edit_auxtag"), ("edit", nr)])
                delete_url   = make_action_link([("mode", "hosttags"), ("_delaux", nr)])
                table.cell(_("Actions"), css="buttons")
                html.icon_button(edit_url, _("Edit this auxiliary tag"), "edit")
                html.icon_button(delete_url, _("Delete this auxiliary tag"), "delete")
                table.cell(_("ID"), tag_id)
                table.cell(_("Title"), _u(title))
                table.cell(_("Topic"), _u(topic) or '')
        table.end()


def mode_edit_auxtag(phase):
    tag_nr = html.var("edit")
    new = tag_nr == None
    if not new:
        tag_nr = int(tag_nr)

    if phase == "title":
        if new:
            return _("Create new auxiliary tag")
        else:
            return _("Edit auxiliary tag")

    elif phase == "buttons":
        html.context_button(_("All Hosttags"), make_link([("mode", "hosttags")]), "back")
        return

    hosttags, auxtags = load_hosttags()

    vs_topic = OptionalDropdownChoice(
        title = _("Topic") + "<sup>*</sup>",
        choices = hosttag_topics(hosttags, auxtags),
        explicit = TextUnicode(),
        otherlabel = _("Create New Topic"),
        default_value = None,
    )

    if phase == "action":
        if html.transaction_valid():
            html.check_transaction() # use up transaction id
            if new:
                tag_id = html.var("tag_id").strip()
                if not tag_id:
                    raise MKUserError("tag_id", _("Please enter a tag ID"))
                validate_tag_id(tag_id, "tag_id")
            else:
                tag_id = auxtags[tag_nr][0]

            title = html.var_utf8("title").strip()
            if not title:
                raise MKUserError("title", _("Please supply a title "
                "for you auxiliary tag."))

            topic = forms.get_input(vs_topic, "topic")
            if topic != '':
                title = '%s/%s' % (topic, title)

            # Make sure that this ID is not used elsewhere
            for entry in config.wato_host_tags:
                tgid = entry[0]
                tit  = entry[1]
                ch   = entry[2]
                for e in ch:
                    if e[0] == tag_id:
                        raise MKUserError("tag_id",
                        _("This tag id is already being used "
                          "in the host tag group %s") % tit)

            for nr, (id, name) in enumerate(auxtags):
                if nr != tag_nr and id == tag_id:
                    raise MKUserError("tag_id",
                    _("This tag id does already exist in the list "
                      "of auxiliary tags."))

            if new:
                auxtags.append((tag_id, title))
            else:
                auxtags[tag_nr] = (tag_id, title)
            save_hosttags(hosttags, auxtags)
        return "hosttags"


    if new:
        title = ""
        tag_id = ""
        topic = ""
    else:
        tag_id, title = auxtags[tag_nr]
        topic, title = parse_hosttag_title(title)

    html.begin_form("auxtag")
    forms.header(_("Auxiliary Tag"))

    # Tag ID
    forms.section(_("Tag ID"))
    if new:
        html.text_input("tag_id", "")
        html.set_focus("tag_id")
    else:
        html.write(tag_id)
    html.help(_("The internal name of the tag. The special tags "
                "<tt>snmp</tt>, <tt>tcp</tt> and <tt>ping</tt> can "
                "be used here in order to specify the agent type."))

    # Title
    forms.section(_("Title") + "<sup>*</sup>")
    html.text_input("title", title, size = 30)
    html.help(_("An alias or description of this auxiliary tag"))

    # The (optional) topic
    forms.section(_("Topic") + "<sup>*</sup>")
    html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                "selections in the GUI more comfortable."))
    forms.input(vs_topic, "topic", topic)

    # Button and end
    forms.end()
    html.show_localization_hint()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

# Validate the syntactic form of a tag
def validate_tag_id(id, varname):
    if not re.match("^[-a-z0-9A-Z_]*$", id):
        raise MKUserError(varname,
            _("Invalid tag ID. Only the characters a-z, A-Z, "
              "0-9, _ and - are allowed."))

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

    hosttags, auxtags = load_hosttags()
    title = ""
    choices = []
    topic = None
    if not new:
        for entry in hosttags:
            id, tit, ch = entry[:3]
            if id == tag_id:
                topic, title = parse_hosttag_title(tit)
                choices = ch
                break

    vs_topic = OptionalDropdownChoice(
        title = _("Topic"),
        choices = hosttag_topics(hosttags, auxtags),
        explicit = TextUnicode(),
        otherlabel = _("Create New Topic"),
        default_value = None,
    )

    vs_choices = ListOf(
        Tuple(
            elements = [
                TextAscii(
                    title = _("Tag ID"),
                    size = 16,
                    regex="^[-a-z0-9A-Z_]*$",
                    none_is_empty = True,
                    regex_error = _("Invalid tag ID. Only the characters a-z, A-Z, "
                                  "0-9, _ and - are allowed.")),
                TextUnicode(
                    title = _("Description") + "*",
                    allow_empty = False,
                    size = 40),

                Foldable(
                    ListChoice(
                        title = _("Auxiliary tags"),
                        # help = _("These tags will implicitely added to a host if the "
                        #          "user selects this entry in the tag group. Select multiple "
                        #          "entries with the <b>Ctrl</b> key."),
                        choices = auxtags)),

            ],
            show_titles = True,
            orientation = "horizontal"),

        add_label = _("Add tag choice"),
        row_label = "@. Choice")

    if phase == "action":
        if html.transaction_valid():
            if new:
                html.check_transaction() # use up transaction id
                tag_id = html.var("tag_id").strip()
                validate_tag_id(tag_id, "tag_id")
                if len(tag_id) == 0:
                    raise MKUserError("tag_id", _("Please specify an ID for your tag group."))
                if not re.match("^[-a-z0-9A-Z_]*$", tag_id):
                    raise MKUserError("tag_id", _("Invalid tag group ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                for entry in config.wato_host_tags:
                    tgid = entry[0]
                    tit  = entry[1]
                    if tgid == tag_id:
                        raise MKUserError("tag_id", _("The tag group ID %s is already used by the tag group '%s'.") % (tag_id, tit))

            title = html.var_utf8("title").strip()
            if not title:
                raise MKUserError("title", _("Please specify a title for your host tag group."))

            topic = forms.get_input(vs_topic, "topic")
            # always put at least "/" as prefix to the title, the title
            # will then be split by the first "/' in future
            title = '%s/%s' % (topic, title)

            new_choices = forms.get_input(vs_choices, "choices")
            have_none_tag = False
            for nr, (id, descr, aux) in enumerate(new_choices):
                if id or descr:
                    if not id:
                        id = None
                        if have_none_tag:
                            raise MKUserError("choices_%d_id" % (nr+1), _("Only on tag may be empty."))
                        have_none_tag = True
                    # Make sure tag ID is unique within this group
                    for (n, x) in enumerate(new_choices):
                        if n != nr and x[0] == id:
                            raise MKUserError("choices_id_%d" % (nr+1), _("Tags IDs must be unique. You've used <b>%s</b> twice.") % id)

                if id:
                    # Make sure this ID is not used elsewhere
                    for entry in config.wato_host_tags:
                        tgid = entry[0]
                        tit  = entry[1]
                        ch   = entry[2]
                        # Do not compare the taggroup with itselfs
                        if tgid != tag_id:
                            for e in ch:
                                # Check primary and secondary tags
                                if id == e[0] or len(e) > 2 and id in e[2]:
                                    raise MKUserError("choices_id_%d" % (nr+1),
                                      _("The tag ID '%s' is already being used by the choice "
                                        "'%s' in the tag group '%s'.") %
                                        ( id, e[1], tit ))

                    # Also check all defined aux tags even if they are not used anywhere
                    for tag, descr in auxtags:
                        if id == tag:
                            raise MKUserError("choices_id_%d" % (nr+1),
                              _("The tag ID '%s' is already being used as auxiliary tag.") % id)

            if len(new_choices) == 0:
                raise MKUserError("id_0", _("Please specify at least one tag."))
            if len(new_choices) == 1 and new_choices[0][0] == None:
                raise MKUserError("id_0", _("Tags with only one choice must have an ID."))

            if new:
                taggroup = tag_id, title, new_choices
                hosttags.append(taggroup)
                save_hosttags(hosttags, auxtags)
                # Make sure, that all tags are active (also manual ones from main.mk)
                config.load_config()
                declare_host_tag_attributes()
                rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts
                log_pending(SYNCRESTART, None, "edit-hosttags", _("Created new host tag group '%s'") % tag_id)
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
                # kind of "patch" from the old to the new tags. The renaming
                # of a tag is detected by comparing the titles. Addition
                # of new tags is not a problem and need not be handled.
                # Result of this is the dict 'operations': it's keys are
                # current tag names, its values the corresponding new names
                # or False in case of tag removals.
                operations = {}

                # Detect renaming
                new_by_title = dict([e[:2] for e in new_choices])
                for entry in choices:
                    tag, tit = entry[:2] # optional third element: aux tags
                    if tit in new_by_title:
                        new_tag = new_by_title[tit]
                        if new_tag != tag:
                            operations[tag] = new_tag # might be None

                # Detect removal
                for entry in choices:
                    tag, tit = entry[:2] # optional third element: aux tags
                    if tag != None \
                        and tag not in [ e[0] for e in new_choices ] \
                        and tag not in operations:
                        # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
                        operations[tag] = False

                # Now check, if any folders, hosts or rules are affected
                message = rename_host_tags_after_confirmation(tag_id, operations)
                if message:
                    save_hosttags(new_hosttags, auxtags)
                    config.load_config()
                    declare_host_tag_attributes()
                    rewrite_config_files_below(g_root_folder) # explicit host tags in all_hosts
                    log_pending(SYNCRESTART, None, "edit-hosttags", _("Edited host tag group %s (%s)") % (message, tag_id))
                    return "hosttags", message != True and message or None

        return "hosttags"



    html.begin_form("hosttaggroup", method = 'POST')
    forms.header(_("Edit group") + (tag_id and " %s" % tag_id or ""))

    # Tag ID
    forms.section(_("Internal ID"))
    html.help(_("The internal ID of the tag group is used to store the tag's "
                "value in the host properties. It cannot be changed later."))
    if new:
        html.text_input("tag_id")
        html.set_focus("tag_id")
    else:
        html.write(tag_id)

    # Title
    forms.section(_("Title") + "<sup>*</sup>")
    html.help(_("An alias or description of this tag group"))
    html.text_input("title", title, size = 30)

    # The (optional) topic
    forms.section(_("Topic") + "<sup>*</sup>")
    html.help(_("Different taggroups can be grouped in topics to make the visualization and "
                "selections in the GUI more comfortable."))
    forms.input(vs_topic, "topic", topic)

    # Choices
    forms.section(_("Choices"))
    html.help(_("The first choice of a tag group will be its default value. "
                 "If a tag group has only one choice, it will be displayed "
                 "as a checkbox and set or not set the only tag. If it has "
                 "more choices you may leave at most one tag id empty. A host "
                 "with that choice will not get any tag of this group.<br><br>"
                 "The tag ID must contain only of letters, digits and "
                 "underscores.<br><br><b>Renaming tags ID:</b> if you want "
                 "to rename the ID of a tag, then please make sure that you do not "
                 "change its title at the same time! Otherwise WATO will not "
                 "be able to detect the renaming and cannot exchange the tags "
                 "in all folders, hosts and rules accordingly."))
    forms.input(vs_choices, "choices", choices)

    # Button and end
    forms.end()
    html.show_localization_hint()

    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

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

# Creates a includable PHP file which provides some functions which
# can be used by the calling program, for example NagVis. It declares
# the following API:
#
# taggroup_title(group_id)
# Returns the title of a WATO tag group
#
# taggroup_choice(group_id, list_of_object_tags)
# Returns either
#   false: When taggroup does not exist in current config
#   null:  When no choice can be found for the given taggroup
#   array(tag, title): When a tag of the taggroup
#
# all_taggroup_choices(object_tags):
# Returns an array of elements which use the tag group id as key
# and have an assiciative array as value, where 'title' contains
# the tag group title and the value contains the value returned by
# taggroup_choice() for this tag group.
#
def export_hosttags(hosttags, auxtags):
    path = php_api_dir + '/hosttags.php'
    make_nagios_directory(php_api_dir)

    # need an extra lock file, since we move the auth.php.tmp file later
    # to auth.php. This move is needed for not having loaded incomplete
    # files into php.
    tempfile = path + '.tmp'
    lockfile = path + '.state'
    file(lockfile, 'a')
    aquire_lock(lockfile)

    # Transform WATO internal data structures into easier usable ones
    hosttags_dict =  {}
    for id, title, choices in hosttags:
        tags = {}
        for tag_id, tag_title, tag_auxtags in choices:
            tags[tag_id] = tag_title, tag_auxtags
        topic, title = parse_hosttag_title(title)
        hosttags_dict[id] = topic, title, tags
    auxtags_dict = dict(auxtags)

    # First write a temp file and then do a move to prevent syntax errors
    # when reading half written files during creating that new file
    file(tempfile, 'w').write('''<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = %s;
$mk_auxtags = %s;

function taggroup_title($group_id) {
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}

function taggroup_choice($group_id, $object_tags) {
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {
        if (isset($mk_hosttags[$group_id][2][$tag])) {
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }
    }
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}

function all_taggroup_choices($object_tags) {
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }
    return $choices;
}

?>
''' % (format_php(hosttags_dict), format_php(auxtags_dict)))
    # Now really replace the destination file
    os.rename(tempfile, path)
    release_lock(lockfile)
    os.unlink(lockfile)

# Current specification for hosttag entries: One tag definition is stored
# as tuple of at least three elements. The elements are used as follows:
# taggroup_id, group_title, list_of_choices, depends_on_tags, depends_on_roles, editable
def load_hosttags():
    filename = multisite_dir + "hosttags.mk"
    if not os.path.exists(filename):
        return [], []
    try:
        vars = {
            "wato_host_tags" : [],
            "wato_aux_tags" : []}
        execfile(filename, vars, vars)
        # Convert manually crafted host tags tags WATO-style. This
        # makes the migration easier
        for taggroup in vars["wato_host_tags"]:
            for nr, entry in enumerate(taggroup[2]):
                if len(entry) <= 2:
                    taggroup[2][nr] = entry + ([],)
        return vars["wato_host_tags"], vars["wato_aux_tags"]

    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))
        return [], []

def save_hosttags(hosttags, auxtags):
    make_nagios_directory(multisite_dir)
    out = create_user_file(multisite_dir + "hosttags.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    out.write("wato_host_tags += \\\n%s\n\n" % pprint.pformat(hosttags))
    out.write("wato_aux_tags += \\\n%s\n" % pprint.pformat(auxtags))
    export_hosttags(hosttags, auxtags)

# Handle renaming and deletion of host tags: find affected
# hosts, folders and rules. Remove or fix those rules according
# the the users' wishes. In case auf auxiliary tags the tag_id
# is None. In other cases it is the id of the tag group currently
# being edited.
def rename_host_tags_after_confirmation(tag_id, operations):
    mode = html.var("_repair")
    if mode == "abort":
        raise MKUserError("id_0", _("Aborting change."))

    elif mode:
        if tag_id and type(operations) == list: # make attribute unknown to system, important for save() operations
            undeclare_host_tag_attribute(tag_id)
        affected_folders, affected_hosts, affected_rulespecs = \
        change_host_tags_in_folders(tag_id, operations, mode, g_root_folder)
        return _("Modified folders: %d, modified hosts: %d, modified rulesets: %d" %
            (len(affected_folders), len(affected_hosts), len(affected_rulespecs)))

    message = ""
    affected_folders, affected_hosts, affected_rulespecs = \
        change_host_tags_in_folders(tag_id, operations, "check", g_root_folder)

    if affected_folders:
        message += _("Affected folders with an explicit reference to this tag "
                     "group and that are affected by the change") + ":<ul>"
        for folder in affected_folders:
            message += '<li><a href="%s">%s</a></li>' % (
                make_link_to([("mode", "editfolder")], folder),
                folder["title"])
        message += "</ul>"

    if affected_hosts:
        message += _("Hosts where this tag group is explicitely set "
                     "and that are effected by the change") + ":<ul><li>"
        for nr, host in enumerate(affected_hosts):
            if nr > 20:
                message += "... (%d more)" % (len(affected_hosts) - 20)
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
        html.write("<h3>" + _("Your modifications affect some objects") + "</h3>")
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
# tag_id == None -> Auxiliary tag has been deleted, no
# tag group affected
def change_host_tags_in_folders(tag_id, operations, mode, folder):
    need_save = False
    affected_folders = []
    affected_hosts = []
    affected_rulespecs = []
    if tag_id:
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
            try:
                save_folder(folder)
            except MKAuthException, e:
                # Ignore MKAuthExceptions of locked host.mk files
                pass

        for subfolder in folder[".folders"].values():
            aff_folders, aff_hosts, aff_rulespecs = change_host_tags_in_folders(tag_id, operations, mode, subfolder)
            affected_folders += aff_folders
            affected_hosts += aff_hosts
            affected_rulespecs += aff_rulespecs

        load_hosts(folder)
        affected_hosts += change_host_tags_in_hosts(folder, tag_id, operations, mode, folder[".hosts"])

    affected_rulespecs += change_host_tags_in_rules(folder, operations, mode)
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
        try:
            save_hosts(folder)
        except MKAuthException, e:
            # Ignore MKAuthExceptions of locked host.mk files
            pass
    return affected_hosts


# The function parses all rules in all rulesets and looks
# for host tags that have been removed or renamed. If tags
# are removed then the depending on the mode affected rules
# are either deleted ("delete") or the vanished tags are
# removed from the rule ("remove").
def change_host_tags_in_rules(folder, operations, mode):
    need_save = False
    affected_rulespecs = []
    all_rulesets = load_rulesets(folder)
    for varname, ruleset in all_rulesets.items():
        rulespec = g_rulespecs[varname]
        rules_to_delete = set([])
        for nr, rule in enumerate(ruleset):
            modified = False
            value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)

            # Handle deletion of complete tag group
            if type(operations) == list: # this list of tags to remove
                for tag in operations:
                    if tag != None and (tag in tag_specs or "!"+tag in tag_specs):
                        if rulespec not in affected_rulespecs:
                            affected_rulespecs.append(rulespec)
                        if mode != "check":
                            modified = True
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
                        if rulespec not in affected_rulespecs:
                            affected_rulespecs.append(rulespec)
                        if mode != "check":
                            modified = True
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
                ruleset[nr] = construct_rule(rulespec, value, tag_specs, host_list, item_list, rule_options)
                need_save = True

        rules_to_delete = list(rules_to_delete)
        rules_to_delete.sort()
        for nr in rules_to_delete[::-1]:
            del ruleset[nr]

    if need_save:
        save_rulesets(folder, all_rulesets)
    affected_rulespecs.sort(cmp = lambda a, b: cmp(a["title"], b["title"]))
    return affected_rulespecs


#.
#   .--Rule-Editor---------------------------------------------------------.
#   |           ____        _        _____    _ _ _                        |
#   |          |  _ \ _   _| | ___  | ____|__| (_) |_ ___  _ __            |
#   |          | |_) | | | | |/ _ \ |  _| / _` | | __/ _ \| '__|           |
#   |          |  _ <| |_| | |  __/ | |__| (_| | | || (_) | |              |
#   |          |_| \_\\__,_|_|\___| |_____\__,_|_|\__\___/|_|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | WATO's awesome rule editor: Lets the user edit rule based parameters |
#   | from main.mk.                                                        |
#   '----------------------------------------------------------------------'

def mode_ruleeditor(phase):
    only_host = html.var("host", "")
    only_local = "" # html.var("local")

    if phase == "title":
        if only_host:
            return _("Rules effective on host ") + only_host
        else:
            return _("Rule-Based Configuration of Host &amp; Service Parameters")

    elif phase == "buttons":
        global_buttons()
        if only_host:
            html.context_button(only_host,
                make_link([("mode", "edithost"), ("host", only_host)]), "host")

        html.context_button(_("Ineffective rules"), make_link([("mode", "ineffective_rules")]), "usedrulesets")
        return

    elif phase == "action":
        return

    if not only_host:
        render_folder_path(keepvarnames = ["mode", "local"])
    else:
        html.write("<h3>%s: %s</h3>" % (_("Host"), only_host))

    search_form(_("Search for rules: "), "rulesets")

    # Group names are separated with "/" into main group and optional subgroup.
    # Do not loose carefully manually crafted order of groups!
    groupnames = []
    for gn, rulesets in g_rulespec_groups:
        main_group = gn.split('/')[0]
        if main_group not in groupnames:
            groupnames.append(main_group)
    menu = []
    for groupname in groupnames + ["used"]:
        url = make_link([("mode", "rulesets"), ("group", groupname),
                         ("host", only_host), ("local", only_local)])
        if groupname == "used":
            title = _("Used Rulesets")
            help = _("Show only modified rulesets<br>(all rulesets with at least one rule)")
            icon = "usedrulesets"
        elif groupname == "static": # these have moved into their own WATO module
            continue
        else:
            title, help = g_rulegroups.get(groupname, (groupname, ""))
            icon = "rulesets"
        help = help.split('\n')[0] # Take only first line as button text
        menu.append((url, title, icon, "rulesets", help))
    render_main_menu(menu)

def search_form(title, mode=None):
    html.begin_form("search")
    html.write(title+' ')
    html.text_input("search", size=32)
    html.hidden_fields()
    if mode:
        html.hidden_field("mode", mode)
    html.set_focus("search")
    html.write(" ")
    html.button("_do_seach", _("Search"))
    html.end_form()
    html.write('<br>')

def rule_is_ineffective(rule, rule_folder, rulespec, hosts):
    value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
    found_match = False
    for (hostname, hostvalues) in hosts.items():
        reason = rule_matches_host_and_item(rulespec, tag_specs, host_list, item_list, rule_folder, hostvalues[".folder"], hostname, NO_ITEM)
        if reason == True:
            found_match = True
            break
    return not found_match

def mode_ineffective_rules(phase):
    if phase == "title":
        return _("Ineffective rules")

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("All Rulesets"), make_link([("mode", "ruleeditor")]), "back")
        if config.may("wato.hosts") or config.may("wato.seeall"):
            html.context_button(_("Folder"), make_link([("mode", "folder")]), "folder")
        return

    elif phase == "action":
        return

    # Select matching rule groups while keeping their configured order
    all_rulesets = load_all_rulesets()
    groupnames = [ gn for gn, rulesets in g_rulespec_groups ]

    html.write('<div class=rulesets>')

    all_hosts = load_all_hosts()
    html.write("<div class=info>" + _("The following rules do not match to any of the existing hosts.") + "</div>")
    have_ineffective = False

    for groupname in groupnames:
        # Show information about a ruleset
        # Sort rulesets according to their title
        g_rulespec_group[groupname].sort(cmp = lambda a, b: cmp(a["title"], b["title"]))
        for rulespec in g_rulespec_group[groupname]:
            varname = rulespec["varname"]
            valuespec = rulespec["valuespec"]

            # handle only_used
            rules = all_rulesets.get(varname, [])
            num_rules = len(rules)
            if num_rules == 0:
                continue

            ineffective_rules = []
            current_rule_folder = None
            for f, rule in rules:
                if current_rule_folder == None or current_rule_folder != f:
                    current_rule_folder = f
                    rulenr = 0
                else:
                    rulenr = rulenr + 1
                if rule_is_ineffective(rule, f, rulespec, all_hosts):
                    ineffective_rules.append( (rulenr, (f,rule)) )
            if len(ineffective_rules) == 0:
                continue
            have_ineffective = True
            titlename = g_rulegroups[groupname.split("/")[0]][0]
            rulegroup, test = g_rulegroups.get(groupname, (groupname, ""))
            html.write("<div>")
            ruleset_url = make_link([("mode", "edit_ruleset"), ("varname", varname)])
            table.begin("ineffective_rules", title = _("<a href='%s'>%s</a> (%s)") % (ruleset_url, rulespec["title"], titlename), css="ruleset")
            for rel_rulenr, (f, rule) in ineffective_rules:
                value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
                table.row()

                # Actions
                table.cell("Actions", css="buttons")
                edit_url = make_link([
                    ("mode", "edit_rule"),
                    ("varname", varname),
                    ("rulenr", rel_rulenr),
                    ("rule_folder", f[".path"])
                ])
                html.icon_button(edit_url, _("Edit this rule"), "edit")

                delete_url = make_action_link([
                    ("mode", "edit_ruleset"),
                    ("varname", varname),
                    ("_action", "delete"),
                    ("_folder", f[".path"]),
                    ("_rulenr", rel_rulenr),
                    ("rule_folder", f[".path"])
                ])
                html.icon_button(delete_url, _("Delete this rule"), "delete")

                # Rule folder
                table.cell(_("Rule folder"))
                html.write(get_folder_aliaspath(f, show_main = False))

                # Conditions
                # YURKS. This is copy & pase from mode_edit_rule!
                table.cell(_("Conditions"), css="condition")
                render_conditions(rulespec, tag_specs, host_list, item_list, varname, f)

                # Value
                table.cell(_("Value"))
                if rulespec["valuespec"]:
                    try:
                        value_html = rulespec["valuespec"].value_to_text(value)
                    except Exception, e:
                        try:
                            reason = str(e)
                            rulespec["valuespec"].validate_datatype(value, "")
                        except Exception, e:
                            reason = str(e)

                        value_html = '<img src="images/icon_alert.png" class=icon>' \
                                   + _("The value of this rule is not valid. ") \
                                   + reason
                else:
                    img = value and "yes" or "no"
                    title = value and _("This rule results in a positive outcome.") \
                                  or  _("this rule results in a negative outcome.")
                    value_html = '<img align=absmiddle class=icon title="%s" src="images/rule_%s.png">' \
                                    % (title, img)
                html.write(value_html)

                # Comment
                table.cell(_("Comment"))
                url = rule_options.get("docu_url")
                if url:
                    html.icon_button(url, _("Context information about this rule"), "url", target="_blank")
                    html.write("&nbsp;")
                html.write(html.attrencode(rule_options.get("comment", "")))

            table.end()
            html.write("</div>")

    if not have_ineffective:
            html.write("<div class=info>" + _("There are no ineffective rules.") + "</div>")
    html.write('</div>')
    return

def mode_static_checks(phase):
    return mode_rulesets(phase, "static")


def mode_rulesets(phase, group=None):
    if not group:
        group = html.var("group") # obligatory

    search = html.var("search")
    if search != None:
        search = search.strip().lower()

    if group == "used":
        title = _("Used Rulesets")
        help = _("Non-empty rulesets")
        only_used = True
    elif group == "static":
        title = _("Manual Checks")
        help = _("Here you can create explicit checks that are not being created by the automatic service discovery.")
        only_used = False
    elif search != None:
        title = _("Rules matching") + ": " + html.attrencode(search)
        help = _("All rules that contain '%s' in their name") % html.attrencode(search)
        only_used = False
    else:
        title, help = g_rulegroups.get(group, (group, None))
        only_used = False

    only_host = html.var("host", "")
    only_local = "" # html.var("local")

    if phase == "title":
        if only_host:
            return _("%s - %s") % (only_host, title)
        else:
            return title

    elif phase == "buttons":
        if only_host:
            home_button()
            if group != "static":
                html.context_button(_("All Rulesets"), make_link([("mode", "ruleeditor"), ("host", only_host)]), "back")
            html.context_button(only_host,
                 make_link([("mode", "edithost"), ("host", only_host)]), "host")
        else:
            global_buttons()
            if group != "static":
                html.context_button(_("All Rulesets"), make_link([("mode", "ruleeditor")]), "back")
            if config.may("wato.hosts") or config.may("wato.seeall"):
                html.context_button(_("Folder"), make_link([("mode", "folder")]), "folder")
        return

    elif phase == "action":
        return

    if not only_host:
        render_folder_path(keepvarnames = ["mode", "local", "group"])

    if search != None or group == 'static':
        search_form(_("Search for rules: "), group != "static" and "rulesets")

    if help != None:
        help = "".join(help.split("\n", 1)[1:]).strip()
        if help:
            html.help(help)

    if only_local and not only_host:
        all_rulesets = {}
        rs = load_rulesets(g_folder)
        for varname, rules in rs.items():
            all_rulesets.setdefault(varname, [])
            all_rulesets[varname] += [ (g_folder, rule) for rule in rules ]
    else:
        all_rulesets = load_all_rulesets()
        if only_used:
            all_rulesets = dict([ r for r in all_rulesets.items() if len(r[1]) > 0 ])


    # Select matching rule groups while keeping their configured order
    groupnames = [ gn for gn, rulesets in g_rulespec_groups
                   if only_used or search != None or gn == group or (group and gn.startswith(group + "/")) ]

    # In case of search we need to sort the groups since main chapters would
    # appear more than once otherwise.
    if search != None:
        groupnames.sort()

    html.write('<div class=rulesets>')

    # Loop over all ruleset groups
    something_shown = False
    title_shown = False
    for groupname in groupnames:
        # Show information about a ruleset
        # Sort rulesets according to their title
        g_rulespec_group[groupname].sort(
            cmp = lambda a, b: cmp(a["title"], b["title"]))
        for rulespec in g_rulespec_group[groupname]:

            varname = rulespec["varname"]
            valuespec = rulespec["valuespec"]

            # handle only_used
            rules = all_rulesets.get(varname, [])
            num_rules = len(rules)
            if num_rules == 0 and (only_used or only_local):
                continue

            # handle search
            if search != None \
                and not (rulespec["help"] and search in rulespec["help"].lower()) \
                and search not in rulespec["title"].lower() \
                and search not in varname:
                continue

            # Show static checks rules only in on dedicated page and vice versa
            if group != 'static' and groupname.startswith("static/"):
                continue
            elif group == 'static' and not groupname.startswith("static/"):
                continue

            # Handle case where a host is specified
            rulespec = g_rulespecs[varname]
            this_host = False
            if only_host:
                num_local_rules = 0
                for f, rule in rules:
                    value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
                    if only_host and only_host in host_list:
                        num_local_rules += 1
            else:
                num_local_rules = len([ f for (f,r) in rules if f == g_folder ])

            if only_local and num_local_rules == 0:
                continue

            if group != 'static' and (only_used or search != None):
                titlename = g_rulegroups[groupname.split("/")[0]][0]
            else:
                if '/' in groupname:
                    titlename = groupname.split("/", 1)[1]
                else:
                    titlename = title

            if title_shown != titlename:
                forms.header(titlename)
                forms.container()
                title_shown = titlename

            something_shown = True

            float_cls = ''
            if not config.wato_hide_help_in_lists:
                if html.help_visible:
                    float_cls = ' nofloat'
                else:
                    float_cls = ' float'

            url_vars = [("mode", "edit_ruleset"), ("varname", varname)]
            if only_host:
                url_vars.append(("host", only_host))
            view_url = make_link(url_vars)
            html.write('<div class="ruleset%s" title="%s"><div class=text>' %
                                (float_cls, html.strip_tags(rulespec["help"] or '')))
            html.write('<a class="%s" href="%s">%s</a>' %
                      (num_rules and "nonzero" or "zero", view_url, rulespec["title"]))
            html.write('<span class=dots>%s</span></div>' % ("." * 100))
            html.write('<div class="rulecount %s">%d</div>' %
                      (num_rules and "nonzero" or "zero", num_rules))
            if not config.wato_hide_help_in_lists and rulespec["help"]:
                html.help(rulespec["help"])
            html.write('</div>')

    if something_shown:
        forms.end()
    else:
        if only_host:
            html.write("<div class=info>" + _("There are no rules with an exception for the host <b>%s</b>.") % only_host + "</div>")
        else:
            html.write("<div class=info>" + _("There are no rules defined in this folder.") + "</div>")

    html.write('</div>')

def create_new_rule_form(rulespec, hostname = None, item = None, varname = None):
    html.begin_form("new_rule", add_transid = False)

    html.write('<table>')
    if hostname:
        label = _("Host %s" % hostname)
        ty = _('Host')
        if item != NO_ITEM and rulespec["itemtype"]:
            label += _(" and %s '%s'") % (rulespec["itemname"], item)
            ty = rulespec["itemname"]

        html.write('<tr><td>')
        html.button("_new_host_rule", _("Create %s specific rule for: ") % ty)
        html.hidden_field("host", hostname)
        html.hidden_field("item", mk_repr(item))
        html.write('</td><td style="vertical-align:middle">')
        html.write(label)
        html.write('</td></tr>\n')

    html.write('<tr><td>')
    html.button("_new_rule", _("Create rule in folder: "))
    html.write('</td><td>')

    html.select("rule_folder", folder_selection(g_root_folder), html.var('folder'))
    html.write('</td></tr></table>\n')
    html.hidden_field("varname", varname)
    html.hidden_field("mode", "new_rule")
    html.hidden_field('folder', html.var('folder'))
    html.end_form()

def mode_edit_ruleset(phase):
    varname = html.var("varname")

    item = None
    if html.var("check_command"):
        check_command = html.var("check_command")
        checks = check_mk_local_automation("get-check-information")
        if check_command.startswith("check_mk-"):
            check_command = check_command[9:]
            varname = "checkgroup_parameters:" + checks[check_command].get("group","")
            descr_pattern  = checks[check_command]["service_description"].replace("%s", "(.*)")
            matcher = re.search(descr_pattern, html.var("service_description"))
            if matcher:
                try:
                    item = matcher.group(1)
                except:
                    item = None
        elif check_command.startswith("check_mk_active-"):
            check_command = check_command[16:].split(" ")[0][:-1]
            varname = "active_checks:" + check_command

    rulespec = g_rulespecs.get(varname)
    hostname = html.var("host", "")
    if not item:
        if html.has_var("item"):
            try:
                item = mk_eval(html.var("item"))
            except:
                item = NO_ITEM
        else:
            item = NO_ITEM

    if hostname:
        hosts = load_hosts(g_folder)
        host = hosts.get(hostname)
        if not host:
            hostname = None # host not found. Should not happen

    if phase == "title":
        if not rulespec:
            text = html.var("service_description") or varname
            return _("No available rule for service %s at host %s") % (text, hostname)
        title = rulespec["title"]
        if hostname:
            title += _(" for host %s") % hostname
            if html.has_var("item") and rulespec["itemtype"]:
                title += _(" and %s '%s'") % (rulespec["itemname"], item)
        return title

    elif phase == "buttons":
        global_buttons()
        if not rulespec:
            html.context_button(_("All Rulesets"), make_link([("mode", "ruleeditor")]), "back")
        else:
            group = rulespec["group"].split("/")[0]
            groupname = g_rulegroups[group][0]
            html.context_button(groupname,
                  make_link([("mode", "rulesets"), ("group", group), ("host", hostname)]), "back")
        html.context_button(_("Used Rulesets"),
             make_link([("mode", "rulesets"), ("group", "used"), ("host", hostname)]), "usedrulesets")
        if hostname:
            html.context_button(_("Services"),
                 make_link([("mode", "inventory"), ("host", hostname)]), "services")
            html.context_button(_("Parameters"),
                  make_link([("mode", "object_parameters"), ("host", hostname), ("service", item)]), "rulesets")
        return

    elif phase == "action":
        if not rulespec:
            return
        # Folder for the rule actions is defined by _folder
        rule_folder = g_folders[html.var("_folder", html.var("folder"))]
        check_folder_permissions(rule_folder, "write", True)
        rulesets = load_rulesets(rule_folder)
        rules = rulesets.get(varname, [])

        rulenr = int(html.var("_rulenr")) # rule number relativ to folder
        action = html.var("_action")

        if action == "delete":
            c = wato_confirm(_("Confirm"), _("Delete rule number %d of folder '%s'?")
                % (rulenr + 1, rule_folder["title"]))
            if c:
                del rules[rulenr]
                save_rulesets(rule_folder, rulesets)
                mark_affected_sites_dirty(rule_folder)
                log_pending(AFFECTED, None, "edit-ruleset",
                      _("Deleted rule in ruleset '%s'") % rulespec["title"])
                return
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload

        elif action == "insert":
            if not html.check_transaction():
                return None # browser reload
            rules[rulenr:rulenr] = [rules[rulenr]]
            save_rulesets(rule_folder, rulesets)
            mark_affected_sites_dirty(rule_folder)

            log_pending(AFFECTED, None, "edit-ruleset",
                  _("Inserted new rule in ruleset %s") % rulespec["title"])
            return

        else:
            if not html.check_transaction():
                return None # browser reload
            rule = rules[rulenr]
            del rules[rulenr]
            if action == "up":
                rules[rulenr-1:rulenr-1] = [ rule ]
            elif action == "down":
                rules[rulenr+1:rulenr+1] = [ rule ]
            elif action == "top":
                rules.insert(0, rule)
            else:
                rules.append(rule)
            save_rulesets(rule_folder, rulesets)
            mark_affected_sites_dirty(rule_folder)
            log_pending(AFFECTED, None, "edit-ruleset",
                     _("Changed order of rules in ruleset %s") % rulespec["title"])
            return

    if not rulespec:
        text = html.var("service_description") or varname
        html.write("<div class=info>" + _("There are no rules availabe for %s.") % text + "</div>")
        return

    if not hostname:
        render_folder_path(keepvarnames = ["mode", "varname"])

    # Titel ist schon Seitentitel
    # html.write("<h3>" + rulespec["title"] + "</h3>")
    if not config.wato_hide_varnames:
        display_varname = ':' in varname and '%s["%s"]' % tuple(varname.split(":")) or varname
        html.write('<div class=varname>%s</div>' % display_varname)

    html.help(rulespec["help"])

    # Collect all rulesets
    all_rulesets = load_all_rulesets()
    ruleset = all_rulesets.get(varname)
    if not ruleset:
        html.write("<div class=info>" + _("There are no rules defined in this set.") + "</div>")

    else:
        alread_matched = False
        match_keys = set([]) # in case if match = "dict"
        last_folder = None

        skip_this_folder = False
        for rulenr in range(0, len(ruleset)):
            folder, rule = ruleset[rulenr]
            if folder != last_folder:
                skip_this_folder = False
                if last_folder != None:
                    table.end()
                first_in_group = True
                alias_path = get_folder_aliaspath(folder, show_main = False)
                last_folder = folder

                if g_folder != g_root_folder and not folder_is_parent_of(folder, g_folder):
                    skip_this_folder = True
                    continue

                table.begin("rules", title="%s %s" % (_("Rules in folder"), alias_path),
                    css="ruleset", searchable=False, sortable=False)
                rel_rulenr = 0
            else:
                if skip_this_folder:
                    continue

                first_in_group = False
                rel_rulenr += 1

            last_in_group = (rulenr == len(ruleset) - 1 or \
                ruleset[rulenr+1][0] != folder)

            value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
            disabled = rule_options.get("disabled")
            table.row(disabled and "disabled" or None)


            # Rule matching
            if hostname:
                table.cell(_("Ma."))
                if disabled:
                    reason = _("This rule is disabled")
                else:
                    reason = rule_matches_host_and_item(
                        rulespec, tag_specs, host_list, item_list, folder, g_folder, hostname, item)

                # Handle case where dict is constructed from rules
                if reason == True and rulespec["match"] == "dict":
                    if len(value) == 0:
                        title = _("This rule matches, but does not define any parameters.")
                        img = 'imatch'
                    else:
                        new_keys = set(value.keys())
                        if set_is_disjoint(match_keys, new_keys):
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

            # Disabling
            table.cell("", css="buttons")
            if disabled:
                html.icon(_("This rule is currently disabled and will not be applied"), "disabled")
            else:
                html.empty_icon()

            # Actions
            table.cell(_("Order"), css="buttons rulebuttons")
            if not first_in_group:
                rule_button("top", _("Move this rule to the top of the list"), folder, rel_rulenr)
                rule_button("up",  _("Move this rule one position up"), folder, rel_rulenr)
            else:
                rule_button(None)
                rule_button(None)
            if not last_in_group:
                rule_button("down",   _("Move this rule one position down"), folder, rel_rulenr)
                rule_button("bottom", _("Move this rule to the bottom of the list"), folder, rel_rulenr)
            else:
                rule_button(None)
                rule_button(None)

            table.cell(_("Actions"), css="buttons rulebuttons")
            edit_url = make_link([
                ("mode", "edit_rule"),
                ("varname", varname),
                ("rulenr", rel_rulenr),
                ("host", hostname),
                ("item", mk_repr(item)),
                ("rule_folder", folder[".path"])])
            html.icon_button(edit_url, _("Edit this rule"), "edit")
            rule_button("insert", _("Insert a copy of this rule in current folder"),
                        folder, rel_rulenr)
            rule_button("delete", _("Delete this rule"), folder, rel_rulenr)


            # Folder
            # alias_path = get_folder_aliaspath(folder, show_main = False)
            # classes = ""
            # if first_in_group:
            #     classes += "first"
            # if last_in_group:
            #     classes += " last"
            # html.write('<td class="folder %s"><table><tr><td>%s</td></tr></table></td>' % (classes, alias_path))

            # Conditions
            table.cell(_("Conditions"), css="condition")
            render_conditions(rulespec, tag_specs, host_list, item_list, varname, folder)

            # Value
            table.cell(_("Value"))

            if rulespec["valuespec"]:
                try:
                    value_html = rulespec["valuespec"].value_to_text(value)
                except Exception, e:
                    try:
                        reason = str(e)
                        rulespec["valuespec"].validate_datatype(value, "")
                    except Exception, e:
                        reason = str(e)

                    value_html = '<img src="images/icon_alert.png" class=icon>' \
                               + _("The value of this rule is not valid. ") \
                               + reason
            else:
                img = value and "yes" or "no"
                title = value and _("This rule results in a positive outcome.") \
                              or  _("this rule results in a negative outcome.")
                value_html = '<img align=absmiddle class=icon title="%s" src="images/rule_%s.png">' \
                                % (title, img)
            html.write(value_html)

            # Comment
            table.cell(_("Comment"))
            url = rule_options.get("docu_url")
            if url:
                html.icon_button(url, _("Context information about this rule"), "url", target="_blank")
                html.write("&nbsp;")
            html.write(html.attrencode(rule_options.get("comment", "")))

        table.end()

    create_new_rule_form(rulespec, hostname, item, varname)


def folder_selection(folder, depth=0):
    if depth:
        title_prefix = "&nbsp;&nbsp;&nbsp;" * depth + "` " + "- " * depth
    else:
        title_prefix = ""
    sel = [ (folder[".path"], title_prefix + folder["title"]) ]

    subfolders = sorted(folder[".folders"].values(), cmp = lambda x,y : cmp(x.get("title").lower(), y.get("title").lower()))
    for subfolder in subfolders:
        sel += folder_selection(subfolder, depth + 1)
    return sel


def create_rule(rulespec, hostname=None, item=NO_ITEM):
    new_rule = []
    valuespec = rulespec["valuespec"]
    if valuespec:
        new_rule.append(valuespec.default_value())
    if hostname:
        new_rule.append([hostname])
    else:
        new_rule.append(ALL_HOSTS) # bottom: default to catch-all rule
    if rulespec["itemtype"]:
        if item != NO_ITEM:
            new_rule.append(["%s$" % item])
        else:
            new_rule.append([""])
    return tuple(new_rule)

def rule_button(action, help=None, folder=None, rulenr=0):
    if action == None:
        html.empty_icon_button()
    else:
        vars = [
            ("mode",    html.var('mode', 'edit_ruleset')),
            ("varname", html.var('varname')),
            ("_folder", folder[".path"]),
            ("_rulenr", str(rulenr)),
            ("_action", action)
        ]
        if html.var("rule_folder"):
            vars.append(("rule_folder", html.var("rule_folder")))
        if html.var("host"):
            vars.append(("host", html.var("host")))
        if html.var("item"):
            vars.append(("item", html.var("item")))
        url = make_action_link(vars)
        html.icon_button(url, help, action)

def parse_rule(ruleset, orig_rule):
    rule = orig_rule
    try:
        if type(rule[-1]) == dict:
            rule_options = rule[-1]
            rule = rule[:-1]
        else:
            rule_options = {}

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

        return value, tag_specs, host_list, item_list, rule_options # (item_list currently not supported)

    except Exception, e:
        raise MKGeneralException(_("Invalid rule <tt>%s</tt>") % (orig_rule,))


def rule_matches_host_and_item(rulespec, tag_specs, host_list, item_list,
                               rule_folder, host_folder, hostname, item):
    reasons = []
    host = host_folder[".hosts"][hostname]
    hostname_match = False
    negate = False
    regex_match = False

    for check_host in host_list:
        if check_host == "@all" or hostname == check_host:
            hostname_match = True
            break
        else:
            if check_host[0] == '!':
                check_host = check_host[1:]
                negate = True
            if check_host[0] == '~':
                check_host = check_host[1:]
                regex_match = True

            if not regex_match and hostname == check_host:
                if negate:
                    break
                hostname_match = True
                break
            elif regex_match and regex(check_host).match(hostname):
                if negate:
                    break
                hostname_match = True
                break

            # No Match until now, but negate, so thats a match
            if negate:
                hostname_match = True
                break

    if not hostname_match:
        reasons.append(_("The host name does not match."))

    for tag in tag_specs:
        if tag[0] != '/' and tag[0] != '!' and tag not in host[".tags"]:
            reasons.append(_("The host is missing the tag %s" % tag))
        elif tag[0] == '!' and tag[1:] in host[".tags"]:
            reasons.append(_("The host has the tag %s" % tag))

    if not is_indirect_parent_of(host_folder, rule_folder):
        reasons.append(_("The rule does not apply to the folder of the host."))

    # Check items
    if item != NO_ITEM and rulespec["itemtype"]:
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


def construct_rule(ruleset, value, tag_specs, host_list, item_list, rule_options):
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

    # Append rule options, but only if they are not trivial. That way we
    # keep as close as possible to the original Check_MK in rules.mk so that
    # command line users will feel at home...
    ro = {}
    if rule_options.get("disabled"):
        ro["disabled"] = True
    if rule_options.get("comment"):
        ro["comment"] = rule_options["comment"]
    if rule_options.get("docu_url"):
        ro["docu_url"] = rule_options["docu_url"]

    # Preserve other keys that we do not know of
    for k,v in rule_options.items():
        if k not in [ "disabled", "comment", "docu_url"]:
            ro[k] = v
    if ro:
        rule.append(ro)

    return tuple(rule)

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
        alias = config.tag_alias(tag)
        group_alias = config.tag_group_title(tag)
        if alias:
            if group_alias:
                html.write(_("Host") + ": " + group_alias + " " + _("is") + " ")
                if negate:
                    html.write("<b>%s</b> " % _("not"))
            else:
                if negate:
                    html.write(_("Host does not have tag"))
                else:
                    html.write(_("Host has tag"))
            html.write(" <b>" + alias + "</b>")
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
            condition = _("This rule does <b>never</b> apply due to an empty list of explicit hosts!")
        elif host_list[-1] != ALL_HOSTS[0]:
            tt_list = []
            for h in host_list:
                f = find_host(h)
                if f:
                    uri = html.makeuri([("mode", "edithost"), ("folder", f[".path"]), ("host", h)])
                    host_spec = '<a href="%s">%s</a>' % (uri, h)
                else:
                    host_spec = h
                tt_list.append("<tt><b>%s</b></tt>" % host_spec)
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
    tag_list = get_tag_conditions()

    # Host list
    if not html.get_checkbox("explicit_hosts"):
        host_list = ALL_HOSTS
    else:
        negate = html.get_checkbox("negate_hosts")
        nr = 0
        host_list = ListOfStrings().from_html_vars("hostlist")
        if negate:
            host_list = [ "!" + h for h in host_list ]
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
            itemenum = ruleset["itemenum"]
            if itemenum:
                itemspec = ListChoice(choices = itemenum, columns = 3)
                item_list = [ x+"$" for x in itemspec.from_html_vars("item") ]
            else:
                vs = ListOfStrings(valuespec = RegExpUnicode())
                item_list = vs.from_html_vars("itemlist")
                vs.validate_value(item_list, "itemlist")

            if len(item_list) == 0:
                raise MKUserError("item_0", _("Please specify at least one %s or "
                    "this rule will never match.") % ruleset["itemname"])
    else:
        item_list = None

    return tag_list, host_list, item_list


def date_and_user():
    return time.strftime("%F", time.localtime()) + " " + config.user_id + ": "


def mode_edit_rule(phase, new = False):
    # Due to localization this cannot be defined in the global context!
    vs_rule_options = Dictionary(
        title = _("Additional options"),
        optional_keys = False,
        render = "form",
        elements = [
            ( "comment",
              TextUnicode(
                title = _("Comment"),
                help = _("An optional comment that helps you document the purpose of  "
                         "this rule"),
                size = 80,
                attrencode = True,
                prefix_buttons = [ ("insertdate", date_and_user, _("Prefix date and your name to the comment")) ]
              )
            ),
            ( "docu_url",
              TextAscii(
                title = _("Documentation-URL"),
                help = _("An optional URL pointing to documentation or any other page. This will be displayed "
                         "as an icon <img class=icon src='images/button_url_lo.png'> and open a new page when clicked. "
                         "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
                         "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."),
                size = 80,
              ),
            ),
            ( "disabled",
              Checkbox(
                  title = _("Rule activation"),
                  help = _("Disabled rules are kept in the configuration but are not applied."),
                  label = _("do not apply this rule"),
              )
            ),
        ]
    )

    varname = html.var("varname")
    rulespec = g_rulespecs[varname]
    back_mode = html.var('back_mode', 'edit_ruleset')

    if phase == "title":
        return _("%s rule %s") % (new and _("New") or _("Edit"), rulespec["title"])

    elif phase == "buttons":
        if back_mode == 'edit_ruleset':
            var_list = [("mode", "edit_ruleset"), ("varname", varname), ("host", html.var("host",""))]
            if html.var("item"):
                var_list.append( ("item", html.var("item")) )
            backurl = make_link(var_list)
        else:
            backurl = make_link([('mode', back_mode), ("host", html.var("host",""))])
        html.context_button(_("Abort"), backurl, "abort")
        return

    folder   = html.has_var("_new_host_rule") and g_folder or g_folders[html.var("rule_folder")]
    rulesets = load_rulesets(folder)
    rules    = rulesets[varname]

    if new:
        host = None
        item = NO_ITEM
        if html.has_var("_new_host_rule"):
            host = html.var("host")
            item = html.has_var("item") and mk_eval(html.var("item")) or NO_ITEM
        try:
            if item != NO_ITEM:
                item = escape_regex_chars(item)
            rule = create_rule(rulespec, host, item)
        except Exception, e:
            if phase != "action":
                html.message(_("Cannot create rule: %s") % e)
            return
        rulenr   = len(rules)
    else:
        rulenr   = int(html.var("rulenr"))
        rule     = rules[rulenr]

    valuespec = rulespec.get("valuespec")
    value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)

    if phase == "action":
        if html.check_transaction():
            # Additional options
            rule_options = vs_rule_options.from_html_vars("options")
            vs_rule_options.validate_value(rule_options, "options")

            # CONDITION
            tag_specs, host_list, item_list = get_rule_conditions(rulespec)
            new_rule_folder = g_folders[html.var("new_rule_folder")]

            # Check permissions on folders
            if not new:
                check_folder_permissions(folder, "write", True)
            check_folder_permissions(new_rule_folder, "write", True)

            # VALUE
            if valuespec:
                value = get_edited_value(valuespec)
            else:
                value = html.var("value") == "yes"
            rule = construct_rule(rulespec, value, tag_specs, host_list, item_list, rule_options)
            if new_rule_folder == folder:
                if new:
                    rules.append(rule)
                else:
                    rules[rulenr] = rule
                save_rulesets(folder, rulesets)
                mark_affected_sites_dirty(folder)

                if new:
                    log_pending(AFFECTED, None, "edit-rule", _("Created new rule in ruleset %s in folder %s") %
                               (rulespec["title"], new_rule_folder["title"]))
                else:
                    log_pending(AFFECTED, None, "edit-rule", _("Changed properties of rule %s in folder %s") %
                               (rulespec["title"], new_rule_folder["title"]))
            else: # Move rule to new folder
                if not new:
                    del rules[rulenr]
                save_rulesets(folder, rulesets)
                rulesets = load_rulesets(new_rule_folder)
                rules = rulesets.setdefault(varname, [])
                rules.append(rule)
                save_rulesets(new_rule_folder, rulesets)
                mark_affected_sites_dirty(folder)
                mark_affected_sites_dirty(new_rule_folder)
                log_pending(AFFECTED, None, "edit-rule", _("Changed properties of rule %s, moved rule from "
                            "folder %s to %s") % (rulespec["title"], folder["title"],
                            new_rule_folder["title"]))
        else:
            return back_mode

        return (back_mode,
           (new and _("Created new rule in ruleset '%s' in folder %s")
                or _("Edited rule in ruleset '%s' in folder %s")) %
                      (rulespec["title"], new_rule_folder["title"]))

    if rulespec.get("help"):
        html.write("<div class=info>" + rulespec["help"] + "</div>")

    html.begin_form("rule_editor", method="POST")

    # Conditions
    forms.header(_("Conditions"))

    # Rule folder
    forms.section(_("Folder"))
    html.select("new_rule_folder", folder_selection(g_root_folder), folder[".path"])
    html.help(_("The rule is only applied to hosts directly in or below this folder."))

    # Host tags
    forms.section(_("Host tags"))
    render_condition_editor(tag_specs)
    html.help(_("The rule will only be applied to hosts fullfilling all of "
                 "of the host tag conditions listed here, even if they appear "
                 "in the list of explicit host names."))

    # Explicit hosts / ALL_HOSTS
    forms.section(_("Explicit hosts"))
    div_id = "div_all_hosts"

    checked = host_list != ALL_HOSTS
    html.checkbox("explicit_hosts", checked, onclick="valuespec_toggle_option(this, %r)" % div_id,
          label = _("Specify explicit host names"))
    html.write('<div id="%s" style="display: %s">' % (
            div_id, not checked and "none" or ""))
    negate_hosts = len(host_list) > 0 and host_list[0].startswith("!")

    explicit_hosts = [ h.strip("!") for h in host_list if h != ALL_HOSTS[0] ]
    ListOfStrings(
        orientation = "horizontal",
        valuespec = TextAscii(size = 30)).render_input("hostlist", explicit_hosts)

    html.checkbox("negate_hosts", negate_hosts, label =
                 _("<b>Negate:</b> make rule apply for <b>all but</b> the above hosts"))
    html.write("</div>")
    html.help(_("You can enter a number of explicit host names that rule should or should "
                 "not apply to here. Leave this option disabled if you want the rule to "
                 "apply for all hosts specified by the given tags."))

    # Itemlist
    itemtype = rulespec["itemtype"]
    if itemtype:
        if itemtype == "service":
            forms.section(_("Services"))
            html.help(_("Specify a list of service patterns this rule shall apply to. "
                         "The patterns must match the <b>beginning</b> of the service "
                         "in question. Adding a <tt>$</tt> to the end forces an excact "
                         "match. Pattern use <b>regular expressions</b>. A <tt>.*</tt> will "
                         "match an arbitrary text."))
        elif itemtype == "checktype":
            forms.section(_("Check types"))
        elif itemtype == "item":
            forms.section(rulespec["itemname"].title())
            if rulespec["itemhelp"]:
                html.help(rulespec["itemhelp"])
            else:
                html.help(_("You can make the rule apply only to certain services of the "
                             "specified hosts. Do this by specifying explicit <b>items</b> to "
                             "match here. <b>Hint:</b> make sure to enter the item only, "
                             "not the full Service description. "
                             "<b>Note:</b> the match is done on the <u>beginning</u> "
                             "of the item in question. Regular expressions are interpreted, "
                             "so appending a <tt>$</tt> will force an exact match."))
        else:
            raise MKGeneralException("Invalid item type '%s'" % itemtype)

        if itemtype:
            checked = html.get_checkbox("explicit_services")
            if checked == None: # read from rule itself
                checked = len(item_list) == 0 or item_list[0] != ""
            div_id = "item_list"
            html.checkbox("explicit_services", checked, onclick="valuespec_toggle_option(this, %r)" % div_id,
                         label = _("Specify explicit values"))
            html.write('<div id="%s" style="display: %s; padding: 0px;">' % (
                div_id, not checked and "none" or ""))
            itemenum = rulespec["itemenum"]
            if itemenum:
                value = [ x.rstrip("$") for x in item_list ]
                itemspec = ListChoice(choices = itemenum, columns = 3)
                itemspec.render_input("item", value)
            else:
                ListOfStrings(
                    orientation = "horizontal",
                    valuespec = RegExpUnicode(size = 30)).render_input("itemlist", item_list)

                html.write("<br><br>")
                html.help(_("The entries here are regular expressions to match the beginning. "
                             "Add a <tt>$</tt> for an exact match. An arbitrary substring is matched "
                             "with <tt>.*</tt><br>Please note that on windows systems any backslashes need to be escaped."
                             "For example C:\\\\tmp\\\\message.log"))
                html.write("</div>")

    # Value
    if valuespec:
        forms.header(valuespec.title() or _("Value"))
        value = rule[0]
        forms.section()
        try:
            valuespec.validate_datatype(value, "ve")
            valuespec.render_input("ve", value)
        except Exception, e:
            if config.debug:
                raise
            else:
                html.show_warning(_('Unable to read current options of this rule. Falling back to '
                                    'default values. When saving this rule now, your previous settings '
                                    'will be overwritten. Problem was: %s.') % e)

            # In case of validation problems render the input with default values
            valuespec.render_input("ve", valuespec.default_value())

        valuespec.set_focus("ve")
    else:
        forms.header(_("Positive / Negative"))
        forms.section("")
        for posneg, img in [ ("positive", "yes"), ("negative", "no")]:
            val = img == "yes"
            html.write('<img class=ruleyesno align=top src="images/rule_%s.png"> ' % img)
            html.radiobutton("value", img, value == val, _("Make the outcome of the ruleset <b>%s</b><br>") % posneg)

    # Additonal rule options
    vs_rule_options.render_input("options", rule_options)

    forms.end()
    html.button("save", _("Save"))
    html.hidden_fields()
    vs_rule_options.set_focus("options")
    html.end_form()

# Render HTML input fields for editing a tag based condition
def render_condition_editor(tag_specs, varprefix=""):
    if varprefix:
        varprefix += "_"

    if len(config.wato_aux_tags) + len(config.wato_host_tags) == 0:
        html.write(_("You have not configured any <a href=\"wato.py?mode=hosttags\">host tags</a>."))
        return

    # Determine current (default) setting of tag by looking
    # into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )
    def current_tag_setting(choices):
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == '!':
                n = True
                t = t[1:]
            else:
                n = False
            if t in [ x[0] for x in choices ]:
                default_tag = t
                ignore = False
                negate = n
        if ignore:
            deflt = "ignore"
        elif negate:
            deflt = "isnot"
        else:
            deflt = "is"
        return default_tag, deflt

    # Show dropdown with "is/isnot/ignore" and beginning
    # of div that is switched visible by is/isnot
    def tag_condition_dropdown(tagtype, deflt, id):
        html.write("<td>")
        html.select(varprefix + tagtype + "_" + id, [
            ("ignore", _("ignore")),
            ("is",     _("is")),
            ("isnot",  _("isnot"))], deflt,
            onchange="valuespec_toggle_dropdownn(this, '%stag_sel_%s');" % \
                    (varprefix, id)
        )
        html.write("</td><td class=\"tag_sel\">")
        if html.form_submitted():
            div_is_open = html.var(tagtype + "_" + id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.write('<div id="%stag_sel_%s" style="%s">' % (
            varprefix, id, not div_is_open and "display: none;" or ""))


    auxtags = group_hosttags_by_topic(config.wato_aux_tags)
    hosttags = group_hosttags_by_topic(config.wato_host_tags)
    all_topics = set([])
    for topic, taggroups in auxtags + hosttags:
        all_topics.add(topic)
    all_topics = list(all_topics)
    all_topics.sort()
    make_foldable = len(all_topics) > 1
    for topic in all_topics:
        if make_foldable:
            html.begin_foldable_container("topic", topic, True, "<b>%s</b>" % (_u(topic)))
        html.write("<table class=\"hosttags\">")

        # Show main tags
        for t, grouped_tags in hosttags:
            if t == topic:
                for entry in grouped_tags:
                    id, title, choices = entry[:3]
                    html.write("<tr><td class=title>%s: &nbsp;</td>" % _u(title))
                    default_tag, deflt = current_tag_setting(choices)
                    tag_condition_dropdown("tag", deflt, id)
                    if len(choices) == 1:
                        html.write(" " + _("set"))
                    else:
                        html.select(varprefix + "tagvalue_" + id,
                            [(t[0], _u(t[1])) for t in choices if t[0] != None], deflt=default_tag)
                    html.write("</div>")
                    html.write("</td></tr>")

        # And auxiliary tags
        for t, grouped_tags in auxtags:
            if t == topic:
                for id, title in grouped_tags:
                    html.write("<tr><td class=title>%s: &nbsp;</td>" % _u(title))
                    default_tag, deflt = current_tag_setting([(id, _u(title))])
                    tag_condition_dropdown("auxtag", deflt, id)
                    html.write(" " + _("set"))
                    html.write("</div>")
                    html.write("</td></tr>")

        html.write("</table>")
        if make_foldable:
            html.end_foldable_container()


# Retrieve current tag condition settings from HTML variables
def get_tag_conditions(varprefix=""):
    if varprefix:
        varprefix += "_"
    # Main tags
    tag_list = []
    for entry in config.wato_host_tags:
        id, title, tags = entry[:3]
        mode = html.var(varprefix + "tag_" + id)
        if len(tags) == 1:
            tagvalue = tags[0][0]
        else:
            tagvalue = html.var(varprefix + "tagvalue_" + id)

        if mode == "is":
            tag_list.append(tagvalue)
        elif mode == "isnot":
            tag_list.append("!" + tagvalue)

    # Auxiliary tags
    for id, title in config.wato_aux_tags:
        mode = html.var(varprefix + "auxtag_" + id)
        if mode == "is":
            tag_list.append(id)
        elif mode == "isnot":
            tag_list.append("!" + id)

    return tag_list


def save_rulesets(folder, rulesets):
    make_nagios_directory(root_dir)
    path = root_dir + '/' + folder['.path'] + '/' + "rules.mk"
    out = create_user_file(path, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")

    for varname, rulespec in g_rulespecs.items():
        ruleset = rulesets.get(varname)
        if not ruleset:
            continue # don't save empty rule sets

        if ':' in varname:
            dictname, subkey = varname.split(':')
            varname = '%s[%r]' % (dictname, subkey)
            out.write("\n%s.setdefault(%r, [])\n" % (dictname, subkey))
        else:
            if rulespec["optional"]:
                out.write("\nif %s == None:\n    %s = []\n" % (varname, varname))

        out.write("\n%s = [\n" % varname)
        for rule in ruleset:
            save_rule(out, folder, rulespec, rule)
        out.write("] + %s\n\n" % varname)

def save_rule(out, folder, rulespec, rule):
    out.write("  ( ")
    value, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)
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

    if rule_options:
        out.write(", %r" % rule_options)

    out.write(" ),\n")




def load_rulesets(folder):
    # TODO: folder berücksichtigen
    if folder[".path"]:
        path = root_dir + folder[".path"] + "/" + "rules.mk"
    else:
        path = root_dir + "rules.mk"

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
    except IOError:
        pass # Non existant files are ok...
    except Exception, e:
        if config.debug:
            raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                                                                       (path, e)))
        else:
            html.log('load_rulesets: Problem while loading rulesets (%s - %s). '
                     'Continue with partly loaded rules...' % (path, e))

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


g_rulegroups = {}
def register_rulegroup(group, title, help):
    g_rulegroups[group] = (title, help)

g_rulespecs            = {}
g_rulespec_group       = {} # for conveniant lookup
g_rulespec_groups      = [] # for keeping original order
NO_FACTORY_DEFAULT     = [] # needed for unique ID
FACTORY_DEFAULT_UNUSED = [] # means this ruleset is not used if no rule is entered
def register_rule(group, varname, valuespec = None, title = None,
                  help = None, itemspec = None, itemtype = None, itemname = None,
                  itemhelp = None, itemenum = None,
                  match = "first", optional = False, factory_default = NO_FACTORY_DEFAULT):
    if not itemname and itemtype == "service":
        itemname = _("Service")

    ruleset = {
        "group"           : group,
        "varname"         : varname,
        "valuespec"       : valuespec,
        "itemspec"        : itemspec, # original item spec, e.g. if validation is needed
        "itemtype"        : itemtype, # None, "service", "checktype" or "checkitem"
        "itemname"        : itemname, # e.g. "mount point"
        "itemhelp"        : itemhelp, # a description of the item, only rarely used
        "itemenum"        : itemenum, # possible fixed values for items
        "match"           : match,    # used by WATO rule analyzer (green and grey balls)
        "title"           : title or valuespec.title(),
        "help"            : help or valuespec.help(),
        "optional"        : optional, # rule may be None (like only_hosts)
        "factory_default" : factory_default,
    }

    # Register group
    if group not in g_rulespec_group:
        rulesets = [ ruleset ]
        g_rulespec_groups.append((group, rulesets))
        g_rulespec_group[group] = rulesets
    else:
        # If a ruleset for this variable already exist, then we need to replace
        # it. How can this happen? If a user puts his own copy of the definition
        # into some file below local/.
        for nr, rs in enumerate(g_rulespec_group[group]):
            if rs["varname"] == varname:
                del g_rulespec_group[group][nr]
                break # There cannot be two duplicates!
        g_rulespec_group[group].append(ruleset)

    g_rulespecs[varname] = ruleset

# Special version of register_rule, dedicated to checks. This is not really
# modular here, but we cannot put this function into the plugins file because
# the order is not defined there.
def register_check_parameters(subgroup, checkgroup, title, valuespec, itemspec, matchtype, has_inventory=True, register_static_check=True):
    # Register rule for discovered checks
    if valuespec and has_inventory: # would be useless rule if check has no parameters
        itemenum = None
        if itemspec:
            itemtype = "item"
            itemname = itemspec.title()
            itemhelp = itemspec.help()
            if isinstance(itemspec, DropdownChoice) or isinstance(itemspec, OptionalDropdownChoice):
                itemenum = itemspec._choices
        else:
            itemtype = None
            itemname = None
            itemhelp = None

        register_rule(
            "checkparams/" + subgroup,
            varname = "checkgroup_parameters:%s" % checkgroup,
            title = title,
            valuespec = valuespec,
            itemspec = itemspec,
            itemtype = itemtype,
            itemname = itemname,
            itemhelp = itemhelp,
            itemenum = itemenum,
            match = matchtype)

    if register_static_check:
        # Register rule for static checks
        elements = [
            CheckTypeGroupSelection(
                checkgroup,
                title = _("Checktype"),
                help = _("Please choose the check plugin")) ]
        if itemspec:
            elements.append(itemspec)
        else:
            # In case of static checks without check-item, add the fixed
            # valuespec to add "None" as second element in the tuple
            elements.append(FixedValue(
                None,
                totext = '',
            ))
        if not valuespec:
            valuespec =\
                FixedValue(None,
                    help = _("This check has no parameters."),
                    totext = "")
        if not valuespec.title():
            valuespec._title = _("Parameters")
        elements.append(valuespec)

        register_rule(
            "static/" + subgroup,
            "static_checks:%s" % checkgroup,
            title = title,
            valuespec = Tuple(
                title = valuespec.title(),
                elements = elements,
            ),
            itemspec = itemspec,
            match = "all")

# Registers notification parameters for a certain notification script,
# e.g. "mail" or "sms". This will create:
# - A WATO host rule
# - A parametrization of the not-script also in the RBN module
# Notification parameters are always expected to be of type Dictionary.
# The match type will be set to "dict".
g_notification_parameters = {}
def register_notification_parameters(scriptname, valuespec):

    script_title = notification_script_title(scriptname)
    title = _("Parameters for %s") % script_title
    valuespec._title = _("Call with the following parameters:")

    register_rule(
        "monconf/" + _("Notifications"),
        "notification_parameters:" + scriptname,
        valuespec,
        title,
        itemtype = None,
        match = "dict"
    )

    g_notification_parameters[scriptname] = valuespec




# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(**args):
    dif = args.get("default_difference", (2.0, 4.0))
    unitname = args.get("unit", "")
    if unitname:
        unitname += " "

    return Dictionary(
        title = _("Predictive Levels"),
        optional_keys = [ "weight", "levels_upper", "levels_upper_min", "levels_lower", "levels_lower_max" ],
        default_keys = [ "levels_upper" ],
        columns = 1,
        headers = "sup",
        elements = [
             ( "period",
                DropdownChoice(
                    title = _("Base prediction on"),
                    choices = [
                        ( "wday",   _("Day of the week (1-7, 1 is Monday)") ),
                        ( "day",    _("Day of the month (1-31)") ),
                        ( "hour",   _("Hour of the day (0-23)") ),
                        ( "minute", _("Minute of the hour (0-59)") ),
                    ]
             )),
             ( "horizon",
               Integer(
                   title = _("Time horizon"),
                   unit = _("days"),
                   minvalue = 1,
                   default_value = 90,
             )),
             # ( "weight",
             #   Percentage(
             #       title = _("Raise weight of recent time"),
             #       label = _("by"),
             #       default_value = 0,
             # )),
             ( "levels_upper",
               CascadingDropdown(
                   title = _("Dynamic levels - upper bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[0]),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("above predicted value"), default_value = dif[1]),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% above predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% above predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation above the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation above the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
             ( "levels_upper_min",
                Tuple(
                    title = _("Limit for upper bound dynamic levels"),
                    help = _("Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                             "the will never be set below the following limits. This avoids false alarms "
                             "during times where the predicted levels would be very low."),
                    elements = [
                        Float(title = _("Warning level is at least"), unit = unitname),
                        Float(title = _("Critical level is at least"), unit = unitname),
                    ]
              )),
             ( "levels_lower",
               CascadingDropdown(
                   title = _("Dynamic levels - lower bound"),
                   choices = [
                       ( "absolute",
                         _("Absolute difference from prediction"),
                         Tuple(
                             elements = [
                                 Float(title = _("Warning at"),
                                       unit = unitname + _("below predicted value"), default_value = 2.0),
                                 Float(title = _("Critical at"),
                                       unit = unitname + _("below predicted value"), default_value = 4.0),
                             ]
                      )),
                      ( "relative",
                        _("Relative difference from prediction"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("% below predicted value"), default_value = 10),
                                 Percentage(title = _("Critical at"), unit = _("% below predicted value"), default_value = 20),
                             ]
                      )),
                      ( "stdev",
                        _("In relation to standard deviation"),
                         Tuple(
                             elements = [
                                 Percentage(title = _("Warning at"), unit = _("times the standard deviation below the predicted value"), default_value = 2),
                                 Percentage(title = _("Critical at"), unit = _("times the standard deviation below the predicted value"), default_value = 4),
                             ]
                      )),
                   ]
             )),
        ]
    )


# To be used as ValueSpec for levels on numeric values, with
# prediction
def match_levels_alternative(v):
    if type(v) == dict:
        return 2
    elif type(v) == tuple and v != (None, None):
        return 1
    else:
        return 0

def Levels(**kwargs):
    help = kwargs.get("help")
    unit = kwargs.get("unit")
    title = kwargs.get("title")
    default_levels = kwargs.get("default_levels", (0.0, 0.0))
    default_difference = kwargs.get("default_difference", (0,0))
    if "default_value" in kwargs:
        default_value = kwargs["default_value"]
    else:
        default_value = default_levels and default_levels or None

    return Alternative(
          title = title,
          help = help,
          show_titles = False,
          style = "dropdown",
          elements = [
              FixedValue(
                  None,
                  title = _("No Levels"),
                  totext = _("Do not impose levels, always be OK"),
              ),
              Tuple(
                  title = _("Fixed Levels"),
                  elements = [
                      Float(unit = unit, title = _("Warning at"), default_value = default_levels[0], allow_int = True),
                      Float(unit = unit, title = _("Critical at"), default_value = default_levels[1], allow_int = True),
                  ],
              ),
              PredictiveLevels(
                  default_difference = default_difference,
              ),
          ],
          match = match_levels_alternative,
          default_value = default_value,
    )

def HostnameTranslation(**kwargs):
    help = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title = title,
        help = help,
        elements = [
            ( "case",
              DropdownChoice(
                  title = _("Case translation"),
                  choices = [
                       ( None,    _("Do not convert case") ),
                       ( "upper", _("Convert hostnames to upper case") ),
                       ( "lower", _("Convert hostnames to lower case") ),
                  ]
            )),
            ( "drop_domain",
              FixedValue(
                  True,
                  title = _("Convert FQHN"),
                  totext = _("Drop domain part (<tt>host123.foobar.de</tt> &#8594; <tt>host123</tt>)"),
            )),
            ( "regex",
              Tuple(
                  title = _("Regular expression substitution"),
                  help = _("Please specify a regular expression in the first field. This expression should at "
                           "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                           "In the second field you specify the translated host name and can refer to the first matched "
                           "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>"),
                  elements = [
                      RegExpUnicode(
                          title = _("Regular expression"),
                          help = _("Must contain at least one subgroup <tt>(...)</tt>"),
                          mingroups = 0,
                          maxgroups = 9,
                          size = 30,
                          allow_empty = False,
                      ),
                      TextUnicode(
                          title = _("Replacement"),
                          help = _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"),
                          size = 30,
                          allow_empty = False,
                      )
                 ]
            )),
            ( "mapping",
              ListOf(
                  Tuple(
                      orientation = "horizontal",
                      elements =  [
                          TextUnicode(
                               title = _("Original hostname"),
                               size = 30,
                               allow_empty = False,
                               attrencode = True,
                          ),
                          TextUnicode(
                               title = _("Translated hostname"),
                               size = 30,
                               allow_empty = False,
                               attrencode = True,
                          ),
                      ],
                  ),
                  title = _("Explicit host name mapping"),
                  help = _("If case conversion and regular expression do not work for all cases then you can "
                           "specify explicity pairs of origin host name  and translated host name here. This "
                           "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                           "expression conversion (if that matches)."),
                  add_label = _("Add new mapping"),
                  movable = False,
            )),
        ])

#.
#   .--User Profile--------------------------------------------------------.
#   |         _   _                 ____             __ _ _                |
#   |        | | | |___  ___ _ __  |  _ \ _ __ ___  / _(_) | ___           |
#   |        | | | / __|/ _ \ '__| | |_) | '__/ _ \| |_| | |/ _ \          |
#   |        | |_| \__ \  __/ |    |  __/| | | (_) |  _| | |  __/          |
#   |         \___/|___/\___|_|    |_|   |_|  \___/|_| |_|_|\___|          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | A user can change several aspects of it's own profile                |
#   '----------------------------------------------------------------------'

def verify_password_policy(password):
    policy = config.password_policy
    min_len = config.password_policy.get('min_length')
    if min_len and len(password) < min_len:
        raise MKUserError('password', _('The given password is too short. It must have at least %d characters.') % min_len)

    num_groups = config.password_policy.get('num_groups')
    if num_groups:
        groups = {}
        for c in password:
            if c in "abcdefghijklmnopqrstuvwxyz":
                groups['lcase'] = 1
            elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                groups['ucase'] = 1
            elif c in "0123456789":
                groups['numbers'] = 1
            else:
                groups['special'] = 1

        if sum(groups.values()) < num_groups:
            raise MKUserError('password', _('The password does not use enough character groups. You need to '
                'set a password which uses at least %d of them.') % num_groups)


def select_language(user):
    languages = [ l for l in get_languages() if not config.hide_language(l[0]) ]
    if languages:
        active = 'language' in user
        forms.section(_("Language"), checkbox = ('_set_lang', active, 'language'))
        default_label = _('Default: %s') % (get_language_alias(config.default_language) or _('English'))
        html.write('<div class="inherited" id="attr_default_language" style="%s">%s</div>' %
                                            ((active) and "display: none" or "", default_label))
        html.write('<div id="attr_entry_language" style="%s">' % ((not active) and "display: none" or ""))
        html.select("language", languages, user.get('language') or '')
        html.write("</div>")
        html.help(_('Configure the default language '
                    'to be used by the user in the user interface here. If you do not check '
                    'the checkbox, then the system default will be used.<br><br>'
                    'Note: currently Multisite is internationalized '
                    'but comes without any actual localisations (translations). If you want to '
                    'create you own translation, you find <a href="%(url)s">documentation online</a>.') %
                    { "url" : "http://mathias-kettner.de/checkmk_multisite_i18n.html"} )

def user_profile_async_replication_dialog():
    html.header(_('Replicate new Authentication Information'),
                javascripts = ['wato'],
                stylesheets = ['check_mk', 'pages', 'wato', 'status'])

    html.begin_context_buttons()
    html.context_button(_('User Profile'), 'user_profile.py', 'back')
    html.end_context_buttons()

    sites = [(name, config.site(name)) for name in config.sitenames() ]
    sort_sites(sites)
    repstatus = load_replication_status()

    html.message(_('To make a login possible with your new credentials on all remote sites, the '
                   'new login credentials need to be replicated to the remote sites. This is done '
                   'on this page now. Each site is being represented by a single image which is first '
                   'shown gray and then fills to green during synchronisation.'))

    html.write('<h3>%s</h3>' % _('Replication States'))
    html.write('<div id="profile_repl">')
    num_replsites = 0
    for site_id, site in sites:
        is_local = site_is_local(site_id)

        if is_local or (not is_local and not site.get("replication")):
            continue # Skip non replication slaves

        if site.get("disabled"):
            ss = {}
            status = "disabled"
        else:
            ss = html.site_status.get(site_id, {})
            status = ss.get("state", "unknown")

        srs = repstatus.get(site_id, {})

        if not "secret" in site:
            status_txt = _('Not logged in.')
            start_sync = False
            icon       = 'repl_locked'
        else:
            status_txt = _('Waiting for replication to start')
            start_sync = True
            icon       = 'repl_pending'

        html.write('<div id="site-%s" class="site">' % (html.attrencode(site_id)))
        html.icon(status_txt, icon)
        if start_sync:
            estimated_duration = srs.get("times", {}).get("profile-sync", 2.0)
            html.javascript('wato_do_profile_replication(\'%s\', %d, \'%s\');' %
                      (site_id, int(estimated_duration * 1000.0), _('Replication in progress')))
            num_replsites += 1
        html.write('<span>%s</span>' % site.get('alias', site_id))
        html.write('</div>')

    html.javascript('var g_num_replsites = %d;\n' % num_replsites)

    html.write('</div>')
    html.footer()


def page_user_profile(change_pw=False):
    start_async_replication = False

    if not config.user_id:
        raise MKUserError(None, _('Not logged in.'))

    if not config.may('general.edit_profile') and not config.may('general.change_password'):
        raise MKAuthException(_("You are not allowed to edit your user profile."))

    if not config.wato_enabled:
        raise MKAuthException(_('User profiles can not be edited (WATO is disabled).'))

    success = None
    if html.has_var('_save') and html.check_transaction():
        users = userdb.load_users(lock = True)

        try:
            # Profile edit (user options like language etc.)
            if config.may('general.edit_profile'):
                if not change_pw:
                    set_lang = html.get_checkbox('_set_lang')
                    language = html.var('language')
                    # Set the users language if requested
                    if set_lang:
                        if language == '':
                            language = None
                        # Set custom language
                        users[config.user_id]['language'] = language
                        config.user['language'] = language

                    else:
                        # Remove the customized language
                        if 'language' in users[config.user_id]:
                            del users[config.user_id]['language']
                        if 'language' in config.user:
                            del config.user['language']

                    # load the new language
                    load_language(config.get_language())
                    load_all_plugins()

                    user = users.get(config.user_id)
                    if config.may('general.edit_notifications') and user.get("notifications_enabled"):
                        value = forms.get_input(vs_notification_method, "notification_method")
                        users[config.user_id]["notification_method"] = value

                    # Custom attributes
                    if config.may('general.edit_user_attributes'):
                        for name, attr in userdb.get_user_attributes():
                            if attr['user_editable']:
                                if not attr.get("permission") or config.may(attr["permission"]):
                                    vs = attr['valuespec']
                                    value = vs.from_html_vars('ua_' + name)
                                    vs.validate_value(value, "ua_" + name)
                                    users[config.user_id][name] = value

            # Change the password if requested
            if config.may('general.change_password'):
                cur_password = html.var('cur_password')
                password     = html.var('password')
                password2    = html.var('password2', '')

                if change_pw:
                    # Force change pw mode
                    if not cur_password:
                        raise MKUserError("cur_password", _("You need to provide your current password."))
                    if not password:
                        raise MKUserError("password", _("You need to change your password."))
                    if cur_password == password:
                        raise MKUserError("password", _("The new password must differ from your current one."))

                if cur_password and password:
                    if userdb.hook_login(config.user_id, cur_password) in [ None, False ]:
                        raise MKUserError("cur_password", _("Your old password is wrong."))
                    if password2 and password != password2:
                        raise MKUserError("password2", _("The both new passwords do not match."))

                    verify_password_policy(password)
                    users[config.user_id]['password'] = userdb.encrypt_password(password)
                    users[config.user_id]['last_pw_change'] = int(time.time())

                    if change_pw:
                        # Has been changed, remove enforcement flag
                        del users[config.user_id]['enforce_pw_change']

                    # Increase serial to invalidate old cookies
                    if 'serial' not in users[config.user_id]:
                        users[config.user_id]['serial'] = 1
                    else:
                        users[config.user_id]['serial'] += 1

                    # Set the new cookie to prevent logout for the current user
                    login.set_auth_cookie(config.user_id, users[config.user_id]['serial'])

            # Now, if in distributed environment, set the trigger for pushing the new
            # auth information to the slave sites asynchronous
            if is_distributed():
                start_async_replication = True

            userdb.save_users(users)
            success = True
        except MKUserError, e:
            html.add_user_error(e.varname, e.message)
    else:
        users = userdb.load_users()

    # When in distributed setup, display the replication dialog instead of the normal
    # profile edit dialog after changing the password.
    if start_async_replication:
        user_profile_async_replication_dialog()
        return

    if change_pw:
        title = _("Change Password")
    else:
        title = _("Edit User Profile")

    html.header(title, javascripts = ['wato'], stylesheets = ['check_mk', 'pages', 'wato', 'status'])

    # Rule based notifications: The user currently cannot simply call the according
    # WATO module due to WATO permission issues. So we cannot show this button
    # right now.
    if not change_pw:
        rulebased_notifications = load_configuration_settings().get("enable_rulebased_notifications")
        if rulebased_notifications and config.may('general.edit_notifications'):
            html.begin_context_buttons()
            url = "wato.py?mode=user_notifications_p"
            html.context_button(_("Notifications"), url, "notifications")
            html.end_context_buttons()
    else:
        reason = html.var('reason')
        if reason == 'expired':
            html.write('<p>%s</p>' % _('Your password is too old, you need to choose a new password.'))
        else:
            html.write('<p>%s</p>' % _('You are required to change your password before proceeding.'))

    if success:
        html.reload_sidebar()
        if change_pw:
            html.message(_("Your password has been changed."))
            html.http_redirect(html.var('_origtarget', 'index.py'))
        else:
            html.message(_("Successfully updated user profile."))

    if html.has_user_errors():
        html.show_user_errors()

    user = users.get(config.user_id)
    if user == None:
        html.show_warning(_("Sorry, your user account does not exist."))
        html.footer()
        return

    # Returns true if an attribute is locked and should be read only. Is only
    # checked when modifying an existing user
    locked_attributes = userdb.locked_attributes(user.get('connector'))
    def is_locked(attr):
        return attr in locked_attributes

    html.begin_form("profile", method="POST")
    html.write('<div class=wato>')
    forms.header(_("Personal Settings"))

    if not change_pw:
        forms.section(_("Name"), simple=True)
        html.write(user.get("alias", config.user_id))

    if config.may('general.change_password') and not is_locked('password'):
        forms.section(_("Current Password"))
        html.password_input('cur_password', autocomplete = "off")

        forms.section(_("New Password"))
        html.password_input('password', autocomplete = "off")

        forms.section(_("New Password Confirmation"))
        html.password_input('password2', autocomplete = "off")

    if not change_pw and config.may('general.edit_profile'):
        select_language(user)

        # Let the user configure how he wants to be notified
        if not rulebased_notifications \
            and config.may('general.edit_notifications') \
            and user.get("notifications_enabled"):
            forms.section(_("Notifications"))
            html.help(_("Here you can configure how you want to be notified about host and service problems and "
                        "other monitoring events."))
            vs_notification_method.render_input("notification_method", user.get("notification_method"))

        if config.may('general.edit_user_attributes'):
            for name, attr in userdb.get_user_attributes():
                if attr['user_editable']:
                    vs = attr['valuespec']
                    forms.section(_u(vs.title()))
                    value = user.get(name, vs.default_value())
                    if not attr.get("permission") or config.may(attr["permission"]):
                        vs.render_input("ua_" + name, value)
                        html.help(_u(vs.help()))
                    else:
                        html.write(vs.value_to_text(value))

    # Save button
    forms.end()
    html.button("_save", _("Save"))
    html.write('</div>')
    html.hidden_fields()
    html.end_form()
    html.footer()

#.
#   .--Sampleconfig--------------------------------------------------------.
#   |   ____                        _                       __ _           |
#   |  / ___|  __ _ _ __ ___  _ __ | | ___  ___ ___  _ __  / _(_) __ _     |
#   |  \___ \ / _` | '_ ` _ \| '_ \| |/ _ \/ __/ _ \| '_ \| |_| |/ _` |    |
#   |   ___) | (_| | | | | | | |_) | |  __/ (_| (_) | | | |  _| | (_| |    |
#   |  |____/ \__,_|_| |_| |_| .__/|_|\___|\___\___/|_| |_|_| |_|\__, |    |
#   |                        |_|                                 |___/     |
#   +----------------------------------------------------------------------+
#   | Functions for creating an example configuration                      |
#   '----------------------------------------------------------------------'

# Create a very basic sample configuration, but only if none of the
# files that we will create already exists. That is e.g. the case
# after an update from an older version where no sample config had
# been created.
def create_sample_config():
    if os.path.exists(multisite_dir + "hosttags.mk") \
        or os.path.exists(root_dir + "rules.mk") \
        or os.path.exists(root_dir + "groups.mk") \
        or os.path.exists(root_dir + "notifications.mk") \
        or os.path.exists(root_dir + "global.mk"):
        return

    # Global configuration settings
    save_configuration_settings({
        "use_new_descriptions_for": [
            "df",
            "df_netapp",
            "df_netapp32",
            "esx_vsphere_datastores",
            "hr_fs",
            "vms_diskstat.df",
            "zfsget",
            "ps",
            "ps.perf",
            "wmic_process",
            "services",
            "logwatch",
            "cmk-inventory",
            "hyperv_vms",
            "ibm_svc_mdiskgrp",
            "ibm_svc_system",
            "ibm_svc_systemstats.diskio",
            "ibm_svc_systemstats.iops",
            "ibm_svc_systemstats.disk_latency",
            "ibm_svc_systemstats.cache",
        ],
        "inventory_check_interval": 120,
        "enable_rulebased_notifications": True,
    })


    # A contact group where everyone is member of
    groups = {
        "contact" : { 'all' : {'alias': u'Everybody'} },
    }
    save_group_information(groups)

    # Basic setting of host tags
    wato_host_tags = \
    [('agent',
      u'Agent type',
      [('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
       ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
       ('snmp-v1', u'Legacy SNMP device (using V1)', ['snmp']),
       ('snmp-tcp', u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
       ('ping', u'No Agent', [])]),
     ('criticality',
      u'Criticality',
      [('prod', u'Productive system', []),
       ('critical', u'Business critical', []),
       ('test', u'Test system', []),
       ('offline', u'Do not monitor this host', [])]),
     ('networking',
      u'Networking Segment',
      [('lan', u'Local network (low latency)', []),
       ('wan', u'WAN (high latency)', []),
       ('dmz', u'DMZ (low latency, secure access)', [])])]

    wato_aux_tags = \
    [('snmp', u'monitor via SNMP'),
     ('tcp', u'monitor via Check_MK Agent')]

    save_hosttags(wato_host_tags, wato_aux_tags)

    # Rules that match the upper host tag definition
    rulesets = {
        # Make the tag 'offline' remove hosts from the monitoring
        'only_hosts': [
            (['!offline'], ['@all'],
            {'comment': u'Do not monitor hosts with the tag "offline"'})],

        # Rule for WAN hosts with adapted PING levels
        'ping_levels': [
            ({'loss': (80.0, 100.0),
              'packets': 6,
              'rta': (1500.0, 3000.0),
              'timeout': 20}, ['wan'], ['@all'],
              {'comment': u'Allow longer round trip times when pinging WAN hosts'})],

        # All hosts should use SNMP v2c if not specially tagged
        'bulkwalk_hosts': [
            (['snmp', '!snmp-v1'], ['@all'], {'comment': u'Hosts with the tag "snmp-v1" must not use bulkwalk'})],

        # Put all hosts and the contact group 'all'
        'host_contactgroups': [
            ('all', [], ALL_HOSTS, {'comment': u'Put all hosts into the contact group "all"'} ),
        ],

        # Interval for HW/SW-Inventory check
        'extra_service_conf:check_interval': [
          ( 1440, [], ALL_HOSTS, [ "Check_MK HW/SW Inventory$" ], {'comment': u'Restrict HW/SW-Inventory to once a day'} ),
        ],
    }

    save_rulesets(g_root_folder, rulesets)

    notification_rules = [{
        'allow_disable'          : True,
        'contact_all'            : False,
        'contact_all_with_email' : False,
        'contact_object'         : True,
        'description'            : 'Notify all contacts of a host/service via HTML email',
        'disabled'               : False,
        'notify_plugin'          : ('mail', {}),
    }]
    save_notification_rules(notification_rules)


    # Make sure the host tag attributes are immediately declared!
    config.wato_host_tags = wato_host_tags
    config.wato_aux_tags = wato_aux_tags

    # Global settings
    use_new_descriptions_for = [ "df", "ps" ]

    # Initial baking of agents (when bakery is available)
    if 'bake_agents' in globals():
        try:
            bake_agents()
        except:
            pass # silently ignore building errors here

#.
#   .--Pattern Editor------------------------------------------------------.
#   |   ____       _   _                    _____    _ _ _                 |
#   |  |  _ \ __ _| |_| |_ ___ _ __ _ __   | ____|__| (_) |_ ___  _ __     |
#   |  | |_) / _` | __| __/ _ \ '__| '_ \  |  _| / _` | | __/ _ \| '__|    |
#   |  |  __/ (_| | |_| ||  __/ |  | | | | | |__| (_| | | || (_) | |       |
#   |  |_|   \__,_|\__|\__\___|_|  |_| |_| |_____\__,_|_|\__\___/|_|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

def mode_pattern_editor(phase):
    import logwatch

    # 1. Variablen auslesen
    hostname   = html.var('host', '')
    item       = html.var('file', '')
    match_txt  = html.var('match', '')
    master_url = html.var('master_url', '')

    hosts = load_hosts(g_folder)
    host = hosts.get(hostname)

    if phase == "title":
        if not hostname and not item:
            return _("Logfile Pattern Analyzer")
        elif not hostname:
            return _("Logfile Patterns of Logfile %s on all Hosts") % (item)
        elif not item:
            return _("Logfile Patterns of Host %s") % (hostname)
        else:
            return _("Logfile Patterns of Logfile %s on Host %s") % (item, hostname)

    elif phase == "buttons":
        html.context_button(_("Main Menu"), make_link([("mode", "main")]), "home")
        if host:
            if item:
                title = _("Show Logfile")
            else:
                title = _("Host Logfiles")

            master_url = ''
            if config.is_multisite():
                master_url = '&master_url=' + defaults.url_prefix + 'check_mk/'
            html.context_button(title, "logwatch.py?host=%s&amp;file=%s%s" %
                (html.urlencode(hostname), html.urlencode(item), master_url), 'logwatch')

        html.context_button(_('Edit Logfile Rules'), make_link([
                ('mode', 'edit_ruleset'),
                ('varname', 'logwatch_rules')
            ]),
            'edit'
        )

        return

    if phase == "action":
        return

    html.help(_('On this page you can test the defined logfile patterns against a custom text, '
                'for example a line from a logfile. Using this dialog it is possible to analyze '
                'and debug your whole set of logfile patterns.'))

    # Render the tryout form
    html.begin_form('try')
    forms.header(_('Try Pattern Match'))
    forms.section(_('Hostname'))
    html.text_input('host')
    forms.section(_('Logfile'))
    html.text_input('file')
    forms.section(_('Text to match'))
    html.help(_('You can insert some text (e.g. a line of the logfile) to test the patterns defined '
          'for this logfile. All patterns for this logfile are listed below. Matching patterns '
          'will be highlighted after clicking the "Try out" button.')
    )
    html.text_input('match', cssclass = 'match', size=100)
    forms.end()
    html.button('_try', _('Try out'))
    html.del_var('folder') # Never hand over the folder here
    html.hidden_fields()
    html.end_form()

    # Bail out if the given hostname does not exist
    if hostname and not host:
        html.add_user_error('host', _('The given host does not exist.'))
        html.show_user_errors()
        return

    varname = 'logwatch_rules'
    rulespec = g_rulespecs[varname]
    all_rulesets = load_all_rulesets()
    ruleset = all_rulesets.get(varname)

    html.write('<h3>%s</h3>' % _('Logfile Patterns'))
    if not ruleset:
        html.write(
            "<div class=info>"
            + _('There are no logfile patterns defined. You may create '
                'logfile patterns using the <a href="%s">Rule Editor</a>.') % make_link([
                    ('mode', 'edit_ruleset'),
                    ('varname', 'logwatch_rules')
                ])
            + "</div>"
        )

    # Loop all rules for this ruleset
    already_matched = False
    last_folder = None
    for rulenr in range(0, len(ruleset)):
        folder, rule = ruleset[rulenr]
        if folder != last_folder:
            rel_rulenr = 0
            last_folder = folder
        else:
            rel_rulenr += 1
        last_in_group = rulenr == len(ruleset) - 1 or ruleset[rulenr+1][0] != folder
        pattern_list, tag_specs, host_list, item_list, rule_options = parse_rule(rulespec, rule)

        # Check if this rule applies to the given host/service
        if hostname:
            # If hostname (and maybe filename) try match it
            reason = rule_matches_host_and_item(
                          rulespec, tag_specs, host_list, item_list, folder, g_folder, hostname, item)
        elif item:
            # If only a filename is given
            reason = False
            for i in item_list:
                if re.match(i, str(item)):
                    reason = True
                    break
        else:
            # If no host/file given match all rules
            reason = True

        match_img = ''
        if reason == True:
            # Applies to the given host/service
            reason_class = 'reason'
            # match_title/match_img are set below per pattern
        else:
            # not matching
            reason_class = 'noreason'
            match_img   = 'nmatch'
            match_title = reason

        html.begin_foldable_container("rule", str(rulenr), True, "<b>Rule #%d</b>" % (rulenr + 1), indent = False)
        html.write('<table style="width:100%" class="data logwatch"><tr>')
        html.write('<th style="width:30px;">' + _('Match') + '</th>')
        html.write('<th style="width:50px;">' + _('State') + '</th>')
        html.write('<th style="width:300px;">' + _('Pattern') + '</th>')
        html.write('<th>' + _('Comment') + '</th>')
        html.write('<th style="width:300px;">' + _('Matched line') + '</th>')
        html.write('</tr>\n')

        # Each rule can hold no, one or several patterns. Loop them all here
        odd = "odd"
        for state, pattern, comment in pattern_list:
            match_class = ''
            disp_match_txt = ''
            if reason == True:
                matched = re.search(pattern, match_txt)
                if matched:

                    # Prepare highlighted search txt
                    match_start = matched.start()
                    match_end   = matched.end()
                    disp_match_txt = match_txt[:match_start] \
                                     + '<span class=match>' + match_txt[match_start:match_end] + '</span>' \
                                     + match_txt[match_end:]

                    if already_matched == False:
                        # First match
                        match_class  = 'match first'
                        match_img   = 'match'
                        match_title = _('This logfile pattern matches first and will be used for '
                                        'defining the state of the given line.')
                        already_matched = True
                    else:
                        # subsequent match
                        match_class = 'match'
                        match_img  = 'imatch'
                        match_title = _('This logfile pattern matches but another matched first.')
                else:
                    match_img   = 'nmatch'
                    match_title = _('This logfile pattern does not match the given string.')

            html.write('<tr class="data %s0 %s">' % (odd, reason_class))
            html.write('<td><img align=absmiddle title="%s" ' \
                        'class=icon src="images/icon_rule%s.png" />' % \
                        (match_title, match_img))

            cls = ''
            if match_class == 'match first':
                cls = ' class="svcstate state%d"' % logwatch.level_state(state)
            html.write('<td style="text-align:center" %s>%s</td>' % (cls, logwatch.level_name(state)))
            html.write('<td><code>%s</code></td>' % pattern)
            html.write('<td>%s</td>' % comment)
            html.write('<td>%s</td>' % disp_match_txt)
            html.write('</tr>\n')

            odd = odd == "odd" and "even" or "odd"

        html.write('<tr class="data %s0"><td colspan=5>' % odd)
        edit_url = make_link([
            ("mode", "edit_rule"),
            ("varname", varname),
            ("rulenr", rel_rulenr),
            ("host", hostname),
            ("item", mk_repr(item)),
            ("rule_folder", folder[".path"])])
        html.icon_button(edit_url, _("Edit this rule"), "edit")
        html.write('</td></tr>\n')

        html.write('</table>\n')
        html.end_foldable_container()

#.
#   .--BI Rules------------------------------------------------------------.
#   |                 ____ ___   ____        _                             |
#   |                | __ )_ _| |  _ \ _   _| | ___  ___                   |
#   |                |  _ \| |  | |_) | | | | |/ _ \/ __|                  |
#   |                | |_) | |  |  _ <| |_| | |  __/\__ \                  |
#   |                |____/___| |_| \_\\__,_|_|\___||___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Editor for the Rules of BI                                          |
#   '----------------------------------------------------------------------'
def mode_bi_rules(phase):
    if phase == "title":
        return _("BI - Business Intelligence")

    aggregations, aggregation_rules = load_bi_rules()

    if phase == "buttons":
        html.context_button(_("Main Menu"), make_link([("mode", "main")]), "home")
        if aggregation_rules:
            html.context_button(_("New Aggregation"),
                      make_link([("mode", "bi_edit_aggregation")]), "new")
        html.context_button(_("New Rule"),
                  make_link([("mode", "bi_edit_rule")]), "new")
        return

    if phase == "action":
        if html.var("_del_rule"):
            ruleid = html.var("_del_rule")
            c = wato_confirm(_("Confirm rule deletion"),
                _("Do you really want to delete the rule with "
                  "the id <b>%s</b>?") % ruleid)
            if c:
                del aggregation_rules[ruleid]
                log_pending(SYNC, None, "bi-delete-rule", _("Deleted BI rule with id %s") % ruleid)
                save_bi_rules(aggregations, aggregation_rules)
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload
        elif html.var("_del_aggr"):
            nr = int(html.var("_del_aggr"))
            c = wato_confirm(_("Confirm aggregation deletion"),
                _("Do you really want to delete the aggregation number <b>%s</b>?") % (nr+1))
            if c:
                del aggregations[nr]
                log_pending(SYNC, None, "bi-delete-aggregation", _("Deleted BI aggregation number %d") % (nr+1))
                save_bi_rules(aggregations, aggregation_rules)
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload

        return

    if not aggregations and not aggregation_rules:
        menu_items = [
            ("bi_edit_rule", _("Create aggregation rule"), "new", "bi_rules",
              _("Rules are the nodes in BI aggregations. "
                "Each aggregation has one rule as its root."))
        ]
        render_main_menu(menu_items)
        return


    table.begin("bi_aggr", _("Aggregations"))
    for nr, aggregation in enumerate(aggregations):
        table.row()
        table.cell(_("Actions"), css="buttons")
        edit_url = make_link([("mode", "bi_edit_aggregation"), ("id", nr)])
        html.icon_button(edit_url, _("Edit this aggregation"), "edit")
        delete_url = make_action_link([("mode", "bi_rules"), ("_del_aggr", nr)])
        html.icon_button(delete_url, _("Delete this aggregation"), "delete")
        table.cell(_("Nr."), nr+1, css="number")
        table.cell("", css="buttons")
        if aggregation["disabled"]:
            html.icon(_("This aggregation is currently disabled."), "disabled")
        if aggregation["single_host"]:
            html.icon(_("This aggregation covers only data from a single host."), "host")
        table.cell(_("Groups"), ", ".join(aggregation["groups"]))
        ruleid, description = bi_called_rule(aggregation["node"])
        edit_url = make_link([("mode", "bi_edit_rule"), ("id", ruleid)])
        table.cell(_("Rule"), '<a href="%s">%s</a>' % (edit_url, ruleid))
        table.cell(_("Note"), description)

    table.end()

    rules = aggregation_rules.items()
    # Sort rules according to nesting level, and then to id
    rules_refs = [ (ruleid, rule, count_bi_rule_references(aggregations, aggregation_rules, ruleid))
                   for (ruleid, rule) in rules ]
    rules_refs.sort(cmp = lambda a,b: cmp(a[2][2], b[2][2]) or cmp(a[1]["title"], b[1]["title"]))

    table.begin("bi_rules", _("Rules"))
    for ruleid, rule, (aggr_refs, rule_refs, level) in rules_refs:
        table.row()
        table.cell(_("Actions"), css="buttons")
        edit_url = make_link([("mode", "bi_edit_rule"), ("id", ruleid)])
        html.icon_button(edit_url, _("Edit this rule"), "edit")
        if rule_refs == 0:
            tree_url = make_link([("mode", "bi_rule_tree"), ("id", ruleid)])
            html.icon_button(tree_url, _("This is a top-level rule. Show rule tree"), "aggr")
        refs = aggr_refs + rule_refs
        if refs == 0:
            delete_url = make_action_link([("mode", "bi_rules"), ("_del_rule", ruleid)])
            html.icon_button(delete_url, _("Delete this rule"), "delete")
        table.cell(_("Lvl"), level, css="number")
        table.cell(_("ID"), '<a href="%s">%s</a>' % (edit_url, ruleid))
        table.cell(_("Parameters"), " ".join(rule["params"]))
        table.cell(_("Title"), rule["title"])
        table.cell(_("Aggregation"),  "/".join([rule["aggregation"][0]] + map(str, rule["aggregation"][1])))
        table.cell(_("Nodes"), len(rule["nodes"]), css="number")
        table.cell(_("Usages"), refs, css="number")
        table.cell(_("Comment"), rule.get("comment", ""))
    table.end()

def mode_bi_rule_tree(phase):
    ruleid = html.var("id")

    if phase == "title":
        return _("BI - Rule Tree of") + " " + ruleid

    aggregations, aggregation_rules = load_bi_rules()

    if phase == "buttons":
        html.context_button(_("Main Menu"), make_link([("mode", "main")]), "home")
        html.context_button(_("Back"), make_link([("mode", "bi_rules")]), "back")
        return

    if phase == "action":
        return

    aggr_refs, rule_refs, level = count_bi_rule_references(aggregations, aggregation_rules, ruleid)
    if rule_refs == 0:
        render_rule_tree(aggregation_rules, ruleid)

def render_rule_tree(aggregation_rules, ruleid):
    rule = aggregation_rules[ruleid]
    html.write('<div class=biruletree><div class=birule>')
    edit_url = make_link([("mode", "bi_edit_rule"), ("id", ruleid)])
    html.write('<a href="%s">' % edit_url)
    html.icon(rule.get("comment", rule["title"]), "aggr")
    html.write(" " + ruleid + "</a>")
    html.write('</div>')
    for node in rule["nodes"]:
        r = bi_called_rule(node)
        if r:
            subnode_id = r[0]
            html.write('<br><div class=arrow></div>')
            html.write('<div class=node>')
            render_rule_tree(aggregation_rules, subnode_id)
            html.write('</div>')
    html.write('</div>')



def bi_called_rule(node):
    if node[0] == "call":
        if node[1][1]:
            args = _("with arguments: %s") % ", ".join(node[1][1])
        else:
            args = _("without arguments")
        return node[1][0], _("Explicit call ") + args
    elif node[0] == "foreach_host":
        subnode = node[1][-1]
        if subnode[0] == 'call':
            if node[1][0] == 'host':
                info = _("Called for all hosts...")
            elif node[1][0] == 'child':
                info = _("Called for each child of...")
            else:
                info = _("Called for each parent of...")
            return subnode[1][0], info
    elif node[0] == "foreach_service":
        subnode = node[1][-1]
        if subnode[0] == 'call':
            return subnode[1][0], _("Called for each service...")

def count_bi_rule_references(aggregations, aggregation_rules, ruleid):
    aggr_refs = 0
    for aggregation in aggregations:
        called_rule_id, info = bi_called_rule(aggregation["node"])
        if called_rule_id == ruleid:
            aggr_refs += 1

    level = 0
    rule_refs = 0
    for rid, rule in aggregation_rules.items():
        l = bi_rule_uses_rule(aggregation_rules, rule, ruleid)
        level = max(l, level)
        if l == 1:
            rule_refs += 1

    return aggr_refs, rule_refs, level

# Checks if the rule 'rule' uses either directly
# or indirectly the rule with the id 'ruleid'. In
# case of success, returns the nesting level
def bi_rule_uses_rule(aggregation_rules, rule, ruleid, level=0):
    for node in rule["nodes"]:
        r = bi_called_rule(node)
        if r:
            ru_id, info = r
            if ru_id == ruleid: # Rule is directly being used
                return level + 1
            # Check if lower rules use it
            else:
                l = bi_rule_uses_rule(aggregation_rules, aggregation_rules[ru_id], ruleid, level + 1)
                if l:
                    return l
    return False


# ValueSpec for editing a tag-condition
class HostTagCondition(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)

    def render_input(self, varprefix, value):
        render_condition_editor(value, varprefix)

    def from_html_vars(self, varprefix):
        return get_tag_conditions(varprefix=varprefix)

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        return "|".join(value)

    def validate_datatype(self, value, varprefix):
        if type(value) != list:
            raise MKUserError(varprefix, _("The list of host tags must be a list, but "
                                           "is %r") % type(value))
        for x in value:
            if type(x) != str:
                raise MKUserError(varprefix, _("The list of host tags must only contain strings "
                                           "but also contains %r") % x)

    def validate_value(self, value, varprefix):
        pass





# We need to replace the BI constants internally with something
# that we can replace back after writing the BI-Rules out
# with pprint.pformat
bi_constants = {
  'ALL_HOSTS'          : 'ALL_HOSTS-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'HOST_STATE'         : 'HOST_STATE-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'HIDDEN'             : 'HIDDEN-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'FOREACH_HOST'       : 'FOREACH_HOST-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'FOREACH_CHILD'      : 'FOREACH_CHILD-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'FOREACH_CHILD_WITH' : 'FOREACH_CHILD_WITH-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'FOREACH_PARENT'     : 'FOREACH_PARENT-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'FOREACH_SERVICE'    : 'FOREACH_SERVICE-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'REMAINING'          : 'REMAINING-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'DISABLED'           : 'DISABLED-f41e728b-0bce-40dc-82ea-51091d034fc3',
  'HARD_STATES'        : 'HARD_STATES-f41e728b-0bce-40dc-82ea-51091d034fc3',
}

# returns aggregations, aggregation_rules
def load_bi_rules():
    filename = multisite_dir + "bi.mk"
    try:
        vars = { "aggregation_rules" : {},
                 "aggregations"      : [],
                 "host_aggregations" : [],
               }
        vars.update(bi_constants)
        if os.path.exists(filename):
            execfile(filename, vars, vars)
        else:
            exec(bi_example, vars, vars)

        # Convert rules from old-style tuples to new-style dicts
        rules = {}
        for ruleid, rule in vars["aggregation_rules"].items():
            rules[ruleid] = convert_rule_from_bi(rule, ruleid)
        aggregations = []
        for aggregation in vars["aggregations"]:
            aggregations.append(convert_aggregation_from_bi(aggregation, single_host = False))
        for aggregation in vars["host_aggregations"]:
            aggregations.append(convert_aggregation_from_bi(aggregation, single_host = True))
        return aggregations, rules

    except Exception, e:
        if config.debug:
            raise

        raise MKGeneralException(_("Cannot read configuration file %s: %s" %
                          (filename, e)))

def save_bi_rules(aggregations, aggregation_rules):
    def replace_constants(s):
        for name, uuid in bi_constants.items():
            while True:
                n = s.replace("'%s'" % uuid, name)
                if n != s:
                    s = n
                else:
                    break
        return s[0] + '\n ' + s[1:-1] + '\n' + s[-1]

    make_nagios_directory(multisite_dir)
    out = create_user_file(multisite_dir + "bi.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for ruleid, rule in aggregation_rules.items():
        rule = convert_rule_to_bi(rule)
        out.write('aggregation_rules["%s"] = %s\n\n' %
                ( ruleid, replace_constants(pprint.pformat(rule, width=50))))
    out.write('\n')
    for aggregation in aggregations:
        if aggregation["single_host"]:
            out.write("host_aggregations.append(\n")
        else:
            out.write("aggregations.append(\n")
        out.write(replace_constants(pprint.pformat(convert_aggregation_to_bi(aggregation))))
        out.write(")\n")

    # Make sure that BI aggregates are replicated to all other sites that allow
    # direct user login
    update_login_sites_replication_status()

def rename_host_in_bi(oldname, newname):
    renamed = 0
    aggregations, rules = load_bi_rules()
    for aggregation in aggregations:
        renamed += rename_host_in_bi_aggregation(aggregation, oldname, newname)
    for rule in rules.values():
        renamed += rename_host_in_bi_rule(rule, oldname, newname)
    if renamed:
        save_bi_rules(aggregations, rules)
    return renamed

def rename_host_in_bi_aggregation(aggregation, oldname, newname):
    node = aggregation["node"]
    if node[0] == 'call':
        if rename_host_in_list(aggregation["node"][1][1], oldname, newname):
            return 1
    return 0

def rename_host_in_bi_rule(rule, oldname, newname):
    renamed = 0
    nodes = rule["nodes"]
    for nr, node in enumerate(nodes):
        if node[0] in [ "host", "service", "remaining" ]:
            if node[1][0] == oldname:
                nodes[nr] = (node[0], ( newname, ) + node[1][1:])
            renamed = 1
        elif node[0] == "call":
            if rename_host_in_list(node[1][1], oldname, newname):
                renamed = 1
    return renamed


bi_aggregation_functions = {}

# Make some conversions so that the format of the
# valuespecs is matched
def convert_rule_from_bi(rule, ruleid):
    if type(rule) == tuple:
        rule = {
            "title"       : rule[0],
            "params"      : rule[1],
            "aggregation" : rule[2],
            "nodes"       : rule[3],
        }
    crule = {}
    crule.update(rule)
    crule["nodes"] = map(convert_node_from_bi, rule["nodes"])
    parts = rule["aggregation"].split("!")
    crule["aggregation"] = (parts[0], tuple(map(tryint, parts[1:])))
    crule["id"] = ruleid
    return crule

def convert_rule_to_bi(rule):
    brule = {}
    brule.update(rule)
    if "id" in brule:
        del brule["id"]
    brule["nodes"] = map(convert_node_to_bi, rule["nodes"])
    brule["aggregation"] = "!".join(
                [ rule["aggregation"][0] ] + map(str, rule["aggregation"][1]))
    return brule

# Convert node-Tuple into format used by CascadingDropdown
def convert_node_from_bi(node):
    if len(node) == 2:
        if type(node[1]) == list:
            return ("call", node)
        elif node[1] == bi_constants['HOST_STATE']:
            return ("host", (node[0],))
        elif node[1] == bi_constants['REMAINING']:
            return ("remaining", (node[0],))
        else:
            return ("service", node)

    else: # FOREACH_...

        foreach_spec = node[0]
        if foreach_spec == bi_constants['FOREACH_CHILD_WITH']:
            # extract the conditions meant for matching the childs
            child_conditions = list(node[1:3])
            if child_conditions[1] == bi_constants['ALL_HOSTS']:
                child_conditions[1] = None
            node = node[0:1] + node[3:]

        # Extract the list of tags
        if type(node[1]) == list:
            tags = node[1]
            node = node[0:1] + node[2:]
        else:
            tags = []

        hostspec = node[1]
        if hostspec == bi_constants['ALL_HOSTS']:
            hostspec = None

        if foreach_spec == bi_constants['FOREACH_SERVICE']:
            service = node[2]
            subnode = convert_node_from_bi(node[3:])
            return ("foreach_service", (tags, hostspec, service, subnode))
        else:

            subnode = convert_node_from_bi(node[2:])
            if foreach_spec == bi_constants['FOREACH_HOST']:
                what = "host"
            elif foreach_spec == bi_constants['FOREACH_CHILD']:
                what = "child"
            elif foreach_spec == bi_constants['FOREACH_CHILD_WITH']:
                what = ("child_with", child_conditions)
            elif foreach_spec == bi_constants['FOREACH_PARENT']:
                what = "parent"
            return ("foreach_host", (what, tags, hostspec, subnode))


def convert_node_to_bi(node):
    if node[0] == "call":
        return node[1]
    elif node[0] == "host":
        return (node[1][0], bi_constants['HOST_STATE'])
    elif node[0] == "remaining":
        return (node[1][0], bi_constants['REMAINING'])
    elif node[0] == "service":
        return node[1]
    elif node[0] == "foreach_host":
        what = node[1][0]

        tags = node[1][1]
        if node[1][2]:
            hostspec = node[1][2]
        else:
            hostspec = bi_constants['ALL_HOSTS']

        if type(what == tuple) and what[0] == 'child_with':
            child_conditions = what[1]
            what             = what[0]
            child_tags       = child_conditions[0]
            child_hostspec   = child_conditions[1] and child_conditions[1] or bi_constants['ALL_HOSTS']
            return (bi_constants["FOREACH_" + what.upper()], child_tags, child_hostspec, tags, hostspec) \
                   + convert_node_to_bi(node[1][3])
        else:
            return (bi_constants["FOREACH_" + what.upper()], tags, hostspec) + convert_node_to_bi(node[1][3])
    elif node[0] == "foreach_service":
        tags = node[1][0]
        if node[1][1]:
            spec = node[1][1]
        else:
            spec = bi_constants['ALL_HOSTS']
        service = node[1][2]
        return (bi_constants["FOREACH_SERVICE"], tags, spec, service) + convert_node_to_bi(node[1][3])

def convert_aggregation_from_bi(aggr, single_host):
    if aggr[0] == bi_constants["DISABLED"]:
        disabled = True
        aggr = aggr[1:]
    else:
        disabled = False

    if aggr[0] == bi_constants["HARD_STATES"]:
        hard_states = True
        aggr = aggr[1:]
    else:
        hard_states = False

    if type(aggr[0]) != list:
        groups = [aggr[0]]
    else:
        groups = aggr[0]
    node = convert_node_from_bi(aggr[1:])
    return {
        "disabled"    : disabled,
        "hard_states" : hard_states,
        "groups"      : groups,
        "node"        : node,
        "single_host" : single_host,
    }

def convert_aggregation_to_bi(aggr):
    if len(aggr["groups"]) == 1:
        conv = (aggr["groups"][0],)
    else:
        conv = (aggr["groups"],)
    node = convert_node_to_bi(aggr["node"])
    convaggr = conv + node
    if aggr["hard_states"]:
        convaggr = (bi_constants["HARD_STATES"],) + convaggr
    if aggr["disabled"]:
        convaggr = (bi_constants["DISABLED"],) + convaggr
    return convaggr

# Not in global context, so that l10n will happen again
def declare_bi_valuespecs(aggregation_rules):
    global vs_aggregation, aggregation_choices, vs_bi_node

    rule_choices = [
           (key, key + " - " + rule["title"])
           for (key, rule)
           in aggregation_rules.items() ]


    vs_call_rule = Tuple(
        elements = [
            DropdownChoice(
                title = _("Rule:"),
                choices = rule_choices,
                sorted = True,
            ),
            ListOfStrings(
                orientation = "horizontal",
                size = 12,
                title = _("Arguments:"),
            ),
        ]
    )

    host_re_help = _("Either an exact host name or a regular expression exactly matching the host "
                     "name. Example: <tt>srv.*p</tt> will match <tt>srv4711p</tt> but not <tt>xsrv4711p2</tt>. ")
    vs_host_re = TextUnicode(
        title = _("Host:"),
        help = host_re_help,
        allow_empty = False,
    )

    # Configuration of leaf nodes
    vs_bi_node_simplechoices = [
        ( "host", _("State of a host"),
           Tuple(
               help = _("Will create child nodes representing the state of hosts (usually the "
                        "host check is done via ping)."),
               elements = [ vs_host_re, ]
           )
        ),
        ( "service", _("State of a service"),
          Tuple(
              help = _("Will create child nodes representing the state of services."),
              elements = [
                  vs_host_re,
                  TextUnicode(
                      title = _("Service:"),
                      help = _("A regular expression matching the <b>beginning</b> of a service description. You can "
                               "use a trailing <tt>$</tt> in order to define an exact match. For each "
                               "matching service on the specified hosts one child node will be created. "),
                  ),
              ]
          ),
        ),
        ( "remaining", _("State of remaining services"),
          Tuple(
              help = _("Create a child node for each service on the specified hosts that is not "
                       "contained in any other node of the aggregation."),
              elements = [ vs_host_re ],
          )
        ),
    ]

    # Configuration of explicit rule call
    vs_bi_node_call_choices = [
          ( "call", _("Call a Rule"), vs_call_rule ),
    ]

    # Configuration of FOREACH_...-type nodes
    def foreach_choices(subnode_choices):
        return [
          ( "foreach_host", _("Create nodes based on a host search"),
             Tuple(
                 elements = [
                    CascadingDropdown(
                        title = _("Refer to:"),
                        choices = [
                            ( 'host',       _("The found hosts themselves") ),
                            ( 'child',      _("The found hosts' childs") ),
                            ( 'child_with', _("The found hosts' childs (with child filtering)"),
                                Tuple(elements = [
                                    HostTagCondition(
                                        title = _("Child Host Tags:")
                                    ),
                                    OptionalDropdownChoice(
                                        title = _("Child Host Name:"),
                                        choices = [
                                            ( None, _("All Hosts")),
                                        ],
                                        explicit = TextAscii(size = 60),
                                        otherlabel = _("Regex for host name"),
                                        default_value = None,
                                    ),
                                ]),
                            ),
                            ( 'parent',     _("The found hosts' parents") ),
                        ],
                        help = _('When refering to the found hosts childs, this means you '
                          'configure the conditions (tags and host name) below to match '
                          'a host, but you will get one node created for each child host. The'
                          'place holder <tt>$1$</tt> contains the name of the found child.<br><br>'
                          'When refering to the found hosts parents, you use the conditions '
                          'to match a host, but you will get one node created for each of the '
                          'parent hosts of this found host. The conditions are used to match '
                          'the child hosts. The place holder <tt>$1$</tt> contains the name '
                          'of the child host and <tt>$2$</tt> the name of the parent host.'),
                    ),
                    HostTagCondition(
                        title = _("Host Tags:")
                    ),
                    OptionalDropdownChoice(
                        title = _("Host Name:"),
                        choices = [
                            ( None, _("All Hosts")),
                        ],
                        explicit = TextAscii(size = 60),
                        otherlabel = _("Regex for host name"),
                        default_value = None,
                    ),
                    CascadingDropdown(
                        title = _("Nodes to create:"),
                        help = _("When calling a rule you can use the place holder <tt>$1$</tt> "
                                 "in the rule arguments. It will be replaced by the actual host "
                                 "names found by the search - one host name for each rule call."),
                        choices = subnode_choices,
                    ),
                 ]
            )
          ),
          ( "foreach_service", _("Create nodes based on a service search"),
             Tuple(
                 elements = [
                    HostTagCondition(
                        title = _("Host Tags:")
                    ),
                    OptionalDropdownChoice(
                        title = _("Host Name:"),
                        choices = [
                            ( None, _("All Hosts")),
                        ],
                        explicit = TextAscii(size = 60),
                        otherlabel = _("Regex for host name"),
                        default_value = None,
                    ),
                    TextAscii(
                        title = _("Service Regex:"),
                        help = _("Subexpressions enclosed in <tt>(</tt> and <tt>)</tt> will be available "
                                 "as arguments <tt>$2$</tt>, <tt>$3$</tt>, etc."),
                        size = 80,
                    ),
                    CascadingDropdown(
                        title = _("Nodes to create:"),
                        help = _("When calling a rule you can use the place holder <tt>$1$</tt> "
                                 "in the rule arguments. It will be replaced by the actual host "
                                 "names found by the search - one host name for each rule call. If you "
                                 "have regular expression subgroups in the service pattern, then "
                                 "the place holders <tt>$2$</tt> will represent the first group match, "
                                 "<tt>$3</tt> the second, and so on..."),
                        choices = subnode_choices,
                    ),
                 ]
            )
          )
        ]

    vs_bi_node = CascadingDropdown(
       choices = vs_bi_node_simplechoices + vs_bi_node_call_choices \
              + foreach_choices(vs_bi_node_simplechoices + vs_bi_node_call_choices)
    )

    aggregation_choices = []
    for aid, ainfo in bi_aggregation_functions.items():
        aggregation_choices.append((
            aid,
            ainfo["title"],
            ainfo["valuespec"],
        ))

    vs_aggregation = Dictionary(
        title = _("Aggregation Properties"),
        optional_keys = False,
        render = "form",
        elements = [
        ( "groups",
          ListOfStrings(
              title = _("Aggregation Groups"),
              help = _("List of groups in which to show this aggregation. Usually "
                       "each aggregation is only in one group. Group names are arbitrary "
                       "texts. At least one group is mandatory."),
              valuespec = TextUnicode(),
          ),
        ),
        ( "node",
          CascadingDropdown(
              title = _("Rule to call"),
              choices = vs_bi_node_call_choices + foreach_choices(vs_bi_node_call_choices)
          )
        ),
        ( "disabled",
          Checkbox(
              title = _("Disabled"),
              label = _("Currently disable this aggregation"),
          )
        ),
        ( "hard_states",
          Checkbox(
              title = _("Use Hard States"),
              label = _("Base state computation on hard states"),
              help = _("Hard states can only differ from soft states if at least one host or service "
                       "of the BI aggregate has more than 1 maximum check attempt. For example if you "
                       "set the maximum check attempts of a service to 3 and the service is CRIT "
                       "just since one check then it's soft state is CRIT, but its hard state is still OK."),
          )
        ),
        ( "single_host",
          Checkbox(
              title = _("Optimization"),
              label = _("The aggregation covers data from only one host and its parents."),
              help = _("If you have a large number of aggregations that cover only one host and "
                       "maybe its parents (such as Check_MK cluster hosts), "
                       "then please enable this optimization. It reduces the time for the "
                       "computation. Do <b>not</b> enable this for aggregations that contain "
                       "data of more than one host!"),
          ),
        ),
      ]
    )



def mode_bi_edit_aggregation(phase):
    nr = int(html.var("id", "-1")) # In case of Aggregations: index in list
    new = nr == -1

    if phase == "title":
        if new:
            return _("BI - Create New Aggregation")
        else:
            return _("BI - Edit Aggregation")

    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "bi_rules")]), "abort")
        return

    aggregations, aggregation_rules = load_bi_rules()
    declare_bi_valuespecs(aggregation_rules)

    if phase == "action":
        if html.check_transaction():
            new_aggr = vs_aggregation.from_html_vars('aggr')
            vs_aggregation.validate_value(new_aggr, 'aggr')
            if len(new_aggr["groups"]) == 0:
                raise MKUserError('rule_p_groups_0', _("Please define at least one aggregation group"))
            if new:
                aggregations.append(new_aggr)
                log_pending(SYNC, None, "bi-new-aggregation", _("Created new BI aggregation %d") % (len(aggregations)))
            else:
                aggregations[nr] = new_aggr
                log_pending(SYNC, None, "bi-new-aggregation", _("Modified BI aggregation %d") % (nr + 1))
            save_bi_rules(aggregations, aggregation_rules)
        return "bi_rules"

    if new:
        value = { "groups" : [ _("Main") ] }
    else:
        value = aggregations[nr]

    html.begin_form("biaggr", method = "POST")
    vs_aggregation.render_input("aggr", value)
    forms.end()
    html.hidden_fields()
    html.button("_save", new and _("Create") or _("Save"), "submit")
    html.set_focus("rule_p_groups_0")
    html.end_form()

def mode_bi_edit_rule(phase):
    ruleid = html.var("id") # In case of Aggregations: index in list
    new = not ruleid

    if phase == "title":
        if new:
            return _("BI - Create New Rule")
        else:
            return _("BI - Edit Rule") + " " + html.attrencode(ruleid)


    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "bi_rules")]), "abort")
        return

    aggregations, aggregation_rules = load_bi_rules()
    declare_bi_valuespecs(aggregation_rules)

    elements = [
        ( "title",
           TextUnicode(
               title = _("Rule Title"),
               help = _("The title of the BI nodes which are created from this rule. This will be "
                        "displayed as the name of the node in the BI view. For "
                        "top level nodes this title must be unique. You can insert "
                        "rule parameters like <tt>$FOO$</tt> or <tt>$BAR$</tt> here."),
               allow_empty = False,
               size = 64,
           ),
        ),

        ( "comment",
           TextUnicode(
               title = _("Comment"),
               help = _("An arbitrary comment of this rule for you."),
               size = 64,
           ),
        ),
        ( "params",
          ListOfStrings(
              title = _("Parameters"),
              help = _("Parameters are used in order to make rules more flexible. They must "
                       "be named like variables in programming languages. For example you can "
                       "make your rule have the two parameters <tt>HOST</tt> and <tt>INST</tt>. "
                       "When calling the rule - from an aggergation or a higher level rule - "
                       "you can then specify two arbitrary values for these parameters. In the "
                       "title of the rule as well as the host and service names, you can insert the "
                       "actual value of the parameters by <tt>$HOST$</tt> and <tt>$INST$</tt> "
                       "(enclosed in dollar signs)."),
              orientation = "horizontal",
              valuespec = TextAscii(
                size = 12,
                regex = '[A-Za-z_][A-Za-z0-9_]*',
                regex_error = _("Parameters must contain only A-Z, a-z, 0-9 and _ "
                                "and must not begin with a digit."),
              )
          )
        ),
        ( "aggregation",
          CascadingDropdown(
            title = _("Aggregation Function"),
            help = _("The aggregation function decides how the status of a node "
                     "is constructed from the states of the child nodes."),
            html_separator = "",
            choices = aggregation_choices,
          )
        ),
        ( "nodes",
          ListOf(
              vs_bi_node,
              add_label = _("Add child node generator"),
              title = _("Nodes that are aggregated by this rule"),
          ),
        ),
    ]


    if new:
        elements = [
        ( "id",
          TextAscii(
              title = _("Unique Rule ID"),
              help = _("The ID of the rule must be a unique text. It will be used as an internal key "
                       "when rules refer to each other. The rule IDs will not be visible in the status "
                       "GUI. They are just used within the configuration."),
              allow_empty = False,
              size = 12,
          ),
        )] + elements

    vs_rule = Dictionary(
        title = _("Rule Properties"),
        optional_keys = False,
        render = "form",
        elements = elements,
        headers = [
            ( _("General Properties"),     [ "id", "title", "comment", "params" ]),
            ( _("Aggregation Function"),   [ "aggregation" ], ),
            ( _("Child Node Generation"),  [ "nodes" ] ),
        ]
    )


    if phase == "action":
        if html.check_transaction():
            new_rule = vs_rule.from_html_vars('rule')
            vs_rule.validate_value(new_rule, 'rule')
            if new:
                ruleid = new_rule["id"]

            if new and ruleid in aggregation_rules:
                raise MKUserError('rule_p_id',
                    _("There is already a rule with the id <b>%s</b>" % ruleid))
            if not new_rule["nodes"]:
                raise MKUserError(None,
                    _("Please add at least one child node. Empty rules are useless."))

            if new:
                del new_rule["id"]
                aggregation_rules[ruleid] = new_rule
                log_pending(SYNC, None, "bi-new-rule", _("Create new BI rule %s") % ruleid)
            else:
                aggregation_rules[ruleid].update(new_rule)
                new_rule["id"] = ruleid
                if bi_rule_uses_rule(aggregation_rules, new_rule, new_rule["id"]):
                    raise MKUserError(None, _("There is a cycle in your rules. This rule calls itself - "
                                              "either directly or indirectly."))
                log_pending(SYNC, None, "bi-edit-rule", _("Modified BI rule %s") % ruleid)

            save_bi_rules(aggregations, aggregation_rules)
        return "bi_rules"

    if new:
        value = {}
    else:
        value = aggregation_rules[ruleid]

    html.begin_form("birule", method="POST")
    vs_rule.render_input("rule", value)
    forms.end()
    html.hidden_fields()
    html.button("_save", new and _("Create") or _("Save"), "submit")
    if new:
        html.set_focus("rule_p_id")
    else:
        html.set_focus("rule_p_title")
    html.end_form()

#.
#   .--Custom-Attributes---------------------------------------------------.
#   |   ____          _                          _   _   _                 |
#   |  / ___|   _ ___| |_ ___  _ __ ___         / \ | |_| |_ _ __ ___      |
#   | | |  | | | / __| __/ _ \| '_ ` _ \ _____ / _ \| __| __| '__/ __|     |
#   | | |__| |_| \__ \ || (_) | | | | | |_____/ ___ \ |_| |_| |  \__ \_    |
#   |  \____\__,_|___/\__\___/|_| |_| |_|    /_/   \_\__|\__|_|  |___(_)   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Mange custom attributes of users (in future hosts etc.)              |
#   '----------------------------------------------------------------------'

custom_attr_types = [
    ('TextAscii', _('Simple Text')),
]

def save_custom_attrs(attrs):
    make_nagios_directory(multisite_dir)
    out = create_user_file(multisite_dir + "custom_attrs.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for what in [ "user" ]:
        if what in attrs and len(attrs[what]) > 0:
            out.write("if type(wato_%s_attrs) != list:\n    wato_%s_attrs = []\n" % (what, what))
            out.write("wato_%s_attrs += %s\n\n" % (what, pprint.pformat(attrs[what])))

def mode_edit_custom_attr(phase, what):
    name = html.var("edit") # missing -> new group
    new = name == None

    if phase == "title":
        if new:
            if what == "user":
                return _("Create User Attribute")
        else:
            if what == "user":
                return _("Edit User Attribute")

    elif phase == "buttons":
        html.context_button(_("User Attributes"), make_link([("mode", "%s_attrs" % what)]), "back")
        return

    all_attrs = userdb.load_custom_attrs()
    attrs = all_attrs.setdefault(what, [])

    if not new:
        attr = [ a for a in attrs if a['name'] == name ]
        if not attr:
            raise MKUserError(_('The attribute does not exist.'))
        else:
            attr = attr[0]
    else:
        attr = {}

    if phase == "action":
        if html.check_transaction():
            title = html.var_utf8("title").strip()
            if not title:
                raise MKUserError("title", _("Please specify a title."))
            for this_attr in attrs:
                if title == this_attr['title'] and name != this_attr['name']:
                    raise MKUserError("alias", _("This alias is already used by the attribute %s.") % this_attr['name'])

            topic = html.var('topic', '').strip()
            help  = html.var_utf8('help').strip()
            user_editable = html.get_checkbox('user_editable')
            show_in_table = html.get_checkbox('show_in_table')
            add_custom_macro = html.get_checkbox('add_custom_macro')

            if new:
                name = html.var("name", '').strip()
                if not name:
                    raise MKUserError("name", _("Please specify a name for the new attribute."))
                if ' ' in name:
                    raise MKUserError("name", _("Sorry, spaces are not allowed in attribute names."))
                if not re.match("^[-a-z0-9A-Z_]*$", name):
                    raise MKUserError("name", _("Invalid attribute name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."))
                if [ a for a in attrs if a['name'] == name ]:
                    raise MKUserError("name", _("Sorry, there is already an attribute with that name."))

                ty = html.var('type', '').strip()
                if ty not in [ t[0] for t in custom_attr_types ]:
                    raise MKUserError('type', _('The choosen attribute type is invalid.'))

                attr = {
                    'name' : name,
                    'type' : ty,
                }
                attrs.append(attr)

                log_pending(SYNCRESTART, None, "edit-%sattr" % what, _("Create new %s attribute %s") % (what, name))
            else:
                log_pending(SYNCRESTART, None, "edit-%sattr" % what, _("Changed title of %s attribute %s") % (what, name))
            attr.update({
                'title'            : title,
                'topic'            : topic,
                'help'             : help,
                'user_editable'    : user_editable,
                'show_in_table'    : show_in_table,
                'add_custom_macro' : add_custom_macro,
            })

            save_custom_attrs(all_attrs)

        return what + "_attrs"

    html.begin_form("attr")
    forms.header(_("Properties"))
    forms.section(_("Name"), simple = not new)
    html.help(_("The name of the attribute is used as an internal key. It cannot be "
                 "changed later."))
    if new:
        html.text_input("name", attr.get('name'))
        html.set_focus("name")
    else:
        html.write(name)
        html.set_focus("title")

    forms.section(_("Title") + "<sup>*</sup>")
    html.help(_("The title is used to label this attribute."))
    html.text_input("title", attr.get('title'))

    forms.section(_('Topic'))
    html.help(_('The attribute is added to this section in the edit dialog.'))
    html.select('topic', [
        ('ident',    _('Identity')),
        ('security', _('Security')),
        ('notify',   _('Notifications')),
        ('personal', _('Personal Settings')),
    ], attr.get('topic', 'personal'))

    forms.section(_('Help Text') + "<sup>*</sup>")
    html.help(_('You might want to add some helpful description for the attribute.'))
    html.text_area('help', attr.get('help', ''))

    forms.section(_('Data type'))
    html.help(_('The type of information to be stored in this attribute.'))
    if new:
        html.select('type', custom_attr_types, attr.get('type'))
    else:
        html.write(dict(custom_attr_types)[attr.get('type')])

    forms.section(_('Editable by Users'))
    html.help(_('It is possible to let users edit their custom attributes.'))
    html.checkbox('user_editable', attr.get('user_editable', True))

    forms.section(_('Show in Table'))
    html.help(_('This attribute is only visibile on the detail pages by default, but '
                'you can also make it visible in the overview tables.'))
    html.checkbox('show_in_table', attr.get('show_in_table', False))

    forms.section(_('Add as Custom Macro'))
    html.help(_('The attribute can be added to the contact definiton in order  '
                'to use it for notifications.'))
    html.checkbox('add_custom_macro', attr.get('add_custom_macro', False))

    forms.end()
    html.show_localization_hint()
    html.button("save", _("Save"))
    html.hidden_fields()
    html.end_form()

def mode_custom_attrs(phase, what):
    if what == "user":
        title = _("Custom User Attributes")

    if phase == "title":
        return title

    elif phase == "buttons":
        global_buttons()
        html.context_button(_("Users"), make_link([("mode", "users")]), "back")
        html.context_button(_("New Attribute"), make_link([("mode", "edit_%s_attr" % what)]), "new")
        return

    all_attrs = userdb.load_custom_attrs()
    attrs = all_attrs.get(what, {})

    if phase == "action":
        if html.var('_delete'):
            delname = html.var("_delete")

            # FIXME: Find usages and warn
            #if usages:
            #    message = "<b>%s</b><br>%s:<ul>" % \
            #                (_("You cannot delete this %s attribute.") % what,
            #                 _("It is still in use by"))
            #    for title, link in usages:
            #        message += '<li><a href="%s">%s</a></li>\n' % (link, title)
            #    message += "</ul>"
            #    raise MKUserError(None, message)

            confirm_txt = _('Do you really want to delete the custom attribute "%s"?') % (delname)

            c = wato_confirm(_("Confirm deletion of attribute \"%s\"" % delname), confirm_txt)
            if c:
                for index, attr in enumerate(attrs):
                    if attr['name'] == delname:
                        attrs.pop(index)
                save_custom_attrs(all_attrs)
                log_pending(SYNCRESTART, None, "edit-%sattrs" % what, _("Deleted attribute %s" % (delname)))
            elif c == False:
                return ""

        return None

    if not attrs:
        html.write("<div class=info>" + _("No custom attributes are defined yet.") + "</div>")
        return

    table.begin(what + "attrs")
    for attr in sorted(attrs, key = lambda x: x['title']):
        table.row()

        table.cell(_("Actions"), css="buttons")
        edit_url = make_link([("mode", "edit_%s_attr" % what), ("edit", attr['name'])])
        delete_url = html.makeactionuri([("_delete", attr['name'])])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"),  attr['name'])
        table.cell(_("Title"), attr['title'])
        table.cell(_("Type"),  attr['type'])

    table.end()

#.
#   .--Hooks-&-API---------------------------------------------------------.
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
#   '----------------------------------------------------------------------'

# Inform plugins about changes of hosts. the_thing can be:
# a folder, a file or a host
def register_hook(name, func):
    hooks.register(name, func)

def num_pending_changes():
    return len(parse_audit_log("pending"))

def get_folder_tree():
    load_all_folders()
    num_hosts_in(g_root_folder) # sets ".total_hosts"
    return g_root_folder

# Find a folder by its path. Raise an exception if it does
# not exist.
def get_folder(path):
    prepare_folder_info()

    folder = g_folders.get(path)
    if folder:
        load_hosts(folder)
        return folder
    else:
        raise MKGeneralException("No WATO folder %s." % path)

# Return the title of a folder - which is given as a string path
def get_folder_title(path):
    load_all_folders() # TODO: use in-memory-cache
    folder = g_folders.get(path)
    if folder:
        return folder["title"]
    else:
        return path

# Return a list with all the titles of the paths'
# components, e.g. "muc/north" -> [ "Main Directory", "Munich", "North" ]
def get_folder_title_path(path, with_links=False):
    # In order to speed this up, we work with a per HTML-request cache
    cache_name = "wato_folder_titles" + (with_links and "_linked" or "")
    cache = html.get_cached(cache_name)
    if cache == None:
        load_all_folders()
        cache = {}
        html.set_cache(cache_name, cache)
    if path not in cache:
        cache[path] = folder_title_path(path, with_links)
    return cache[path]

def sort_by_title(folders):
    def folder_cmp(f1, f2):
        return cmp(f1["title"].lower(), f2["title"].lower())
    folders.sort(cmp = folder_cmp)
    return folders

def get_all_hosts(folder=None):
    if not folder:
        prepare_folder_info()
    return collect_hosts(folder or g_root_folder)

def get_host(folder, hostname):
    host = folder[".hosts"][hostname]
    eff = effective_attributes(host, folder)
    eff["name"] = hostname
    return eff

# Create an URL to a certain WATO folder.
def link_to_path(path):
    return "wato.py?mode=folder&folder=" + html.urlencode(path)

# Create an URL to the edit-properties of a host.
def link_to_host(hostname):
    return "wato.py?" + html.urlencode_vars(
    [("mode", "edithost"), ("host", hostname)])


#.
#   .--API Helpers---------------------------------------------------------.
#   |       _    ____ ___   _   _ _____ _     ____  _____ ____  ____       |
#   |      / \  |  _ \_ _| | | | | ____| |   |  _ \| ____|  _ \/ ___|      |
#   |     / _ \ | |_) | |  | |_| |  _| | |   | |_) |  _| | |_) \___ \      |
#   |    / ___ \|  __/| |  |  _  | |___| |___|  __/| |___|  _ < ___) |     |
#   |   /_/   \_\_|  |___| |_| |_|_____|_____|_|   |_____|_| \_\____/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |   These functions are used by the Web-API and by WATO as well        |
#   '----------------------------------------------------------------------'

# This is the single site activation mode
def activate_changes():
    try:
        start = time.time()
        check_mk_local_automation(config.wato_activation_method)
        duration = time.time() - start
        update_replication_status(None, {}, { 'act': duration })
    except Exception:
        if config.debug:
            import traceback
            raise MKUserError(None, "Error executing hooks: %s" %
                              traceback.format_exc().replace('\n', '<br />'))
        else:
            raise

# Checks if the given host_tags are all in known host tag groups and have a valid value
def check_host_tags(host_tags):
    for key, value in host_tags.items():
        for group_entry in configured_host_tags:
            if group_entry[0] == key:
                for value_entry in group_entry[2]:
                    if value_entry[0] == value:
                        break
                else:
                    raise MKUserError(None, _("Unknown host tag %s") % html.attrencode(value))
                break
        else:
            raise MKUserError(None, _("Unknown host tag group %s") % html.attrencode(key))

# Create wato folders up to the given path if they don't exists
def create_wato_folders(path):
    path_tokens = path.split("/")
    current_folder = g_root_folder
    for i in range(0, len(path_tokens)):
        check_path = "/".join(path_tokens[:i+1])
        if check_path in g_folders:
            current_folder = g_folders[check_path]
        else:
            check_folder_permissions(current_folder, "write")
            current_folder = create_wato_folder(current_folder, path_tokens[i], path_tokens[i])

# Creates and returns an empty wato folder with the given title
# Write permissions are NOT checked!
def create_wato_folder(parent, name, title, attributes={}):
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


#.
#   .--WEB API-------------------------------------------------------------.
#   |             __        _______ ____       _    ____ ___               |
#   |             \ \      / / ____| __ )     / \  |  _ \_ _|              |
#   |              \ \ /\ / /|  _| |  _ \    / _ \ | |_) | |               |
#   |               \ V  V / | |___| |_) |  / ___ \|  __/| |               |
#   |                \_/\_/  |_____|____/  /_/   \_\_|  |___|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

class API:
    __all_hosts            = None
    __prepared_folder_info = False

    def __prepare_folder_info(self, force = False):
        if not self.__prepared_folder_info or force:
            prepare_folder_info()
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

        host_attribute_names = map(lambda (x, y): x.name(), host_attributes) + ["inventory_failed", ".nodes"]

        for key, value in attributes.items():
            if key in host_attribute_names:
                result[key] = value

        return result

    def lock_wato(self):
        lock_exclusive()

    def validate_host_parameters(self, host_foldername, hostname, host_attr, validate = [], create_folders = True):
        self.__prepare_folder_info()
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
        self.__prepare_folder_info()
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
            create_wato_folders(target_foldername)

            folder = g_folders[target_foldername]
            add_hosts_to_folder(folder, new_hosts)

        # As long as some hooks are able to invalidate the
        # entire g_folders variable we need to enforce a reload
        self.__prepare_folder_info(force = True)
        self.__get_all_hosts(force = True)
#
#        for host_foldername, new_hosts in target_folders.items():
#            for hostname in new_hosts.keys():
#                all_hosts[hostname] = g_folders[host_foldername][".hosts"][hostname]


    # hosts: [ { "attributes": {attr}, "unset_attributes": {attr}, "hostname": "hostA"}, .. ]
    def edit_hosts(self, hosts, validate_hosts = True):
        self.__prepare_folder_info()
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
        self.__prepare_folder_info(force = True)
        self.__get_all_hosts(force = True)
#
#        for host_foldername, update_hosts in target_folders.items():
#            for hostname in update_hosts.keys():
#                all_hosts[hostname] = g_folders[host_foldername][".hosts"][hostname]


    def get_host(self, hostname, effective_attr = False):
        self.__prepare_folder_info()
        all_hosts = self.__get_all_hosts()

        self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing", "permissions_read"])

        the_host = all_hosts[hostname]
        if effective_attr:
            the_host = effective_attributes(the_host, the_host[".folder"])

        cleaned_host = dict([(k, v) for (k, v) in the_host.iteritems() if not k.startswith('.') ])

        return { "attributes": cleaned_host, "path": the_host[".folder"][".path"], "hostname": hostname }

    # hosts: [ "hostA", "hostB", "hostC" ]
    def delete_hosts(self, hosts, validate_hosts = True):
        self.__prepare_folder_info()
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
        self.__prepare_folder_info(force = True)
        self.__get_all_hosts(force = True)

    def discover_services(self, hostname, mode = "new"):
        self.__prepare_folder_info()
        all_hosts = self.__get_all_hosts()

        config.need_permission("wato.services")
        self.__validate_host_parameters(None, hostname, {}, all_hosts, True, ["host_missing"])
        check_host_permissions(hostname, folder = all_hosts[hostname][".folder"])

        ### Start inventory
        host = all_hosts[hostname]
        counts, failed_hosts = check_mk_automation(host[".siteid"], "inventory", [ "@scan", mode ] + [hostname])
        if failed_hosts:
            if not host.get("inventory_failed"):
                host["inventory_failed"] = True
                save_hosts(host[".folder"])
            raise MKUserError(None, _("Failed to inventorize %s: %s") % (hostname, failed_hosts[hostname]))

        if host.get("inventory_failed"):
            del host["inventory_failed"]
            save_hosts(host[".folder"])

        return _("Service discovery successful. Added %d, Removed %d, Kept %d, New Count %d") % tuple(counts[hostname])

    def activate_changes(self, sites, mode = "dirty", allow_foreign_changes = False):
        self.__prepare_folder_info()

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

                    if not site_is_local(site["id"]):
                        remove_sync_snapshot(site["id"])
        else: # Single site
            if mode == "all" or (mode == "dirty" and log_exists("pending")):
                try:
                    activate_changes()
                except Exception, e:
                    errors.append("%s: %s" % (site["id"], e))

        if not errors:
            log_commit_pending()
        else:
            raise MKUserError(None, ", ".join(errors))


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

def call_hook_snapshot_pushed():
    hooks.call("snapshot-pushed")

def call_hook_hosts_changed(folder):
    if hooks.registered("hosts-changed"):
        hosts = collect_hosts(folder)
        hooks.call("hosts-changed", hosts)

    # The same with all hosts!
    if hooks.registered("all-hosts-changed"):
        hosts = collect_hosts(g_root_folder)
        hooks.call("all-hosts-changed", hosts)

def call_hook_folder_created(folder):
    hooks.call("folder-created", folder)

def call_hook_folder_deleted(folder):
    hooks.call("folder-deleted", folder)

# This hook is executed before distributing changes to the remote
# sites (in distributed WATO) or before activating them (in single-site
# WATO). If the hook raises an exception, then the distribution and
# activation is aborted.
def call_hook_pre_distribute_changes():
    if hooks.registered('pre-distribute-changes'):
        hooks.call("pre-distribute-changes", collect_hosts(g_root_folder))

# This hook is executed when one applies the pending configuration changes
# from wato but BEFORE the nagios restart is executed.
#
# It can be used to create custom input files for nagios/Check_MK.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_pre_activate_changes():
    if hooks.registered('pre-activate-changes'):
        hooks.call("pre-activate-changes", collect_hosts(g_root_folder))

# This hook is executed when one applies the pending configuration changes
# from wato.
#
# But it is only excecuted when there is at least one function
# registered for this host.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_activate_changes():
    if hooks.registered('activate-changes'):
        hosts = collect_hosts(g_root_folder)
        hooks.call("activate-changes", hosts)

# This hook is executed when the save_roles() function is called
def call_hook_roles_saved(roles):
    hooks.call("roles-saved", roles)

# This hook is executed when the save_sites() function is called
def call_hook_sites_saved(sites):
    hooks.call("sites-saved", sites)

# This hook is called in order to determine if a host has a 'valid'
# configuration. It used for displaying warning symbols in the
# host list and in the host detail view.
def validate_host(host, folder):
    if hooks.registered('validate-host'):
        errors = []
        eff = effective_attributes(host, folder)
        for hk in hooks.get('validate-host'):
            try:
                hk(eff)
            except MKUserError, e:
                errors.append(e.message)
        return errors
    else:
        return []

# This hook is called in order to determine the errors of the given
# hostnames. These informations are used for displaying warning
# symbols in the host list and the host detail view
# Returns dictionary { hostname: [errors] }
def validate_all_hosts(hostnames, force_all = False):
    if hooks.registered('validate-all-hosts') and (len(hostnames) > 0 or force_all):
        hosts_errors = {}
        all_hosts = collect_hosts(g_root_folder)

        if force_all:
            hostnames = all_hosts.keys()

        for name in hostnames:
            eff = all_hosts[name]
            errors = []
            for hk in hooks.get('validate-all-hosts'):
                try:
                    hk(eff, all_hosts)
                except MKUserError, e:
                    errors.append(e.message)
            hosts_errors[name] = errors
        return hosts_errors
    else:
        return {}

#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Functions needed at various places                                   |
#   '----------------------------------------------------------------------'

import base64

def mk_eval(s):
    try:
        if literal_eval and not config.wato_legacy_eval:
            return literal_eval(base64.b64decode(s))
        else:
            return pickle.loads(base64.b64decode(s))
    except:
        raise MKGeneralException(_('Unable to parse provided data: %s') % html.attrencode(repr(s)))

def mk_repr(s):
    if literal_eval and not config.wato_legacy_eval:
        return base64.b64encode(repr(s))
    else:
        return base64.b64encode(pickle.dumps(s))

# Returns true when at least one folder is defined in WATO
def have_folders():
    root_folder = load_folder(root_dir)
    if len(root_folder[".folders"]) > 0:
        return True
    return False

# Returns true if at least one host or folder exists in the wato root
def using_wato_hosts():
    root_folder = load_folder(root_dir)
    if len(root_folder[".folders"]) > 0:
        return True

    load_hosts(root_folder)
    if len(root_folder[".hosts"]) > 0:
        return True

    return False

def host_status_button(hostname, viewname):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("filename", g_folder[".path"] + "/hosts.mk"),
           ("host",     hostname),
           ("site",     "")]),
           "status")  # TODO: support for distributed WATO

def service_status_button(hostname, servicedesc):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", "service"),
           ("host",     hostname),
           ("service",  servicedesc),
           ]),
           "status")  # TODO: support for distributed WATO

def folder_status_button(viewname = "allhosts"):
    html.context_button(_("Status"),
       "view.py?" + html.urlencode_vars([
           ("view_name", viewname),
           ("wato_folder", g_folder[".path"])]),
           "status")  # TODO: support for distributed WATO

def global_buttons():
    changelog_button()
    home_button()

def home_button():
    html.context_button(_("Main Menu"), make_link([("mode", "main")]), "home")

def search_button():
    html.context_button(_("Search"), make_link([("mode", "search")]), "search")

def changelog_button():
    pending = parse_audit_log("pending")
    if len(pending) > 0:
        buttontext = "%d " % len(pending) + _("Changes")
        hot = True
        icon = "wato_changes"
    else:
        buttontext = _("No Changes")
        hot = False
        icon = "wato_nochanges"
    html.context_button(buttontext, make_link([("mode", "changelog")]), icon, hot)

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

def folder_is_parent_of(folder, child):
    if folder == child:
        return True
    elif ".parent" in child:
        return folder_is_parent_of(folder, child[".parent"])
    else:
        return False

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
    return make_link(vars + [("_transid", html.get_transid())])


# Show confirmation dialog, send HTML-header if dialog is shown.
def wato_confirm(html_title, message):
    if not html.has_var("_do_confirm") and not html.has_var("_do_actions"):
        wato_html_head(html_title)
    return html.confirm(message)

def wato_html_head(title):
    global g_html_head_open
    if not g_html_head_open:
        g_html_head_open = True
        html.header(title, stylesheets = wato_styles)
        html.write("<div class=wato>\n")

def render_folder_path(the_folder = 0, link_to_last = False, keepvarnames = ["mode"]):
    if the_folder == 0:
        the_folder = g_folder

    keepvars = [ (name, html.var(name)) for name in keepvarnames ]

    def render_component(folder):
        return '<a href="%s">%s</a>' % (
               html.makeuri_contextless([
                  ("folder", folder[".path"])] + keepvars), folder["title"])

    def bc_el_start(end = '', z_index = 0):
        html.write('<li style="z-index:%d;"><div class="left %s"></div>' % (z_index, end))

    def bc_el_end(end = ''):
        html.write('<div class="right %s"></div></li>' % end)

    folders = []
    folder = the_folder.get(".parent")
    while folder:
        folders.append(folder)
        folder = folder.get(".parent")
    subfolders = the_folder[".folders"]

    parts = []
    for folder in folders[::-1]:
        parts.append(render_component(folder))

    # The current folder (with link or without link)
    if link_to_last:
        parts.append(render_component(the_folder))
    else:
        parts.append(the_folder["title"])


    # Render the folder path
    html.write("<div class=folderpath><ul>\n")
    num = 0
    for part in parts:
        if num == 0:
            bc_el_start('end', z_index = 100 + num)
        else:
            bc_el_start(z_index = 100 + num)
        html.write('<div class=content>%s</div>\n' % part)

        bc_el_end(num == len(parts)-1
                  and not (
                    len(subfolders) > 0 and not link_to_last)
                  and "end" or "")
        num += 1

    # Render the current folder when having subfolders
    if len(subfolders) > 0 and not link_to_last:
        bc_el_start(z_index = 100 + num)
        html.write("<div class=content><form method=GET name=folderpath>")
        options = [ (sf[".path"], sf["title"]) for sf in subfolders.values() ]
        html.sorted_select(
            "folder", [ ("", "") ] + options,
            onchange = "folderpath.submit();",
            attrs = {
                "class"   : "folderpath",
                # This does not work: it prevents the selection from
                # being unfolded
                # "onfhocus" : "if (this.blur) this.blur();",
            }
        )
        for var in keepvarnames:
            html.hidden_field(var, html.var(var))
        html.write("</form></div>")
        bc_el_end('end')

    html.write("</ul></div>\n")

def may_see_hosts():
    return config.may("wato.use") and \
       (config.may("wato.seeall") or config.may("wato.hosts"))

def is_alias_used(my_what, my_name, my_alias):
    # Host / Service / Contact groups
    all_groups = userdb.load_group_information()
    for what, groups in all_groups.items():
        for gid, group in groups.items():
            if group['alias'] == my_alias and (my_what != what or my_name != gid):
                return False, _("This alias is already used in the %s group %s.") % (what, gid)

    # Timeperiods
    timeperiods = load_timeperiods()
    for key, value in timeperiods.items():
        if value.get("alias") == my_alias and (my_what != "timeperiods" or my_name != key):
            return False, _("This alias is already used in timeperiod %s.") % key

    # Roles
    roles = userdb.load_roles()
    for key, value in roles.items():
        if value.get("alias") == my_alias and (my_what != "roles" or my_name != key):
            return False, _("This alias is already used in the role %s.") % key

    return True, None

# Checks if a valuespec is a Checkbox
def is_a_checkbox(vs):
    if isinstance(vs, Checkbox):
        return True
    elif isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    else:
        return False

def site_neutral_path(path):
    if path.startswith('/omd'):
        parts = path.split('/')
        parts[3] = '&lt;siteid&gt;'
        return '/'.join(parts)
    else:
        return path

syslog_facilities = [
    (0, "kern"),
    (1, "user"),
    (2, "mail"),
    (3, "daemon"),
    (4, "auth"),
    (5, "syslog"),
    (6, "lpr"),
    (7, "news"),
    (8, "uucp"),
    (9, "cron"),
    (10, "authpriv"),
    (11, "ftp"),
    (16, "local0"),
    (17, "local1"),
    (18, "local2"),
    (19, "local3"),
    (20, "local4"),
    (21, "local5"),
    (22, "local6"),
    (23, "local7"),
]


#.
#   .--Plugins-------------------------------------------------------------.
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Prepare plugin-datastructures and load WATO plugins                  |
#   '----------------------------------------------------------------------'

# permissions = None -> every user can use this mode, permissions
# are checked by the mode itself. Otherwise the user needs at
# least wato.use and - if he makes actions - wato.edit. Plus wato.*
# for each permission in the list.
modes = {
   # ident,               permissions, handler function
   "main"               : ([], mode_main),
   "folder"             : (["hosts"], mode_folder),
   "newfolder"          : (["hosts", "manage_folders"], lambda phase: mode_editfolder(phase, True)),
   "editfolder"         : (["hosts" ], lambda phase: mode_editfolder(phase, False)),
   "newhost"            : (["hosts", "manage_hosts"], lambda phase: mode_edithost(phase, True, False)),
   "newcluster"         : (["hosts", "manage_hosts"], lambda phase: mode_edithost(phase, True, True)),
   "rename_host"        : (["hosts", "manage_hosts"], lambda phase: mode_rename_host(phase)),
   "bulk_import"        : (["hosts", "manage_hosts"], lambda phase: mode_bulk_import(phase)),
   "edithost"           : (["hosts"], lambda phase: mode_edithost(phase, False, None)),
   "parentscan"         : (["hosts"], mode_parentscan),
   "firstinventory"     : (["hosts", "services"], lambda phase: mode_inventory(phase, True)),
   "inventory"          : (["hosts"], lambda phase: mode_inventory(phase, False)),
   "diag_host"          : (["hosts", "diag_host"], mode_diag_host),
   "object_parameters"  : (["hosts", "rulesets"], mode_object_parameters),
   "search"             : (["hosts"], mode_search),
   "search_results"     : (["hosts"], mode_search_results),
   "bulkinventory"      : (["hosts", "services"], mode_bulk_inventory),
   "bulkedit"           : (["hosts", "edit_hosts"], mode_bulk_edit),
   "bulkcleanup"        : (["hosts", "edit_hosts"], mode_bulk_cleanup),
   "random_hosts"       : (["hosts", "random_hosts"], mode_random_hosts),
   "changelog"          : ([], mode_changelog),
   "auditlog"           : (["auditlog"], mode_auditlog),
   "snapshot"           : (["snapshots"], mode_snapshot),
   "globalvars"         : (["global"], mode_globalvars),
   "snapshot_detail"    : (["snapshots"], mode_snapshot_detail),
   "edit_configvar"     : (["global"], mode_edit_configvar),
   "ldap_config"        : (["global"], mode_ldap_config),
   "ruleeditor"         : (["rulesets"], mode_ruleeditor),
   "static_checks"      : (["rulesets"], mode_static_checks),
   "rulesets"           : (["rulesets"], mode_rulesets),
   "ineffective_rules"  : (["rulesets"], mode_ineffective_rules),
   "edit_ruleset"       : (["rulesets"], mode_edit_ruleset),
   "new_rule"           : (["rulesets"], lambda phase: mode_edit_rule(phase, True)),
   "edit_rule"          : (["rulesets"], lambda phase: mode_edit_rule(phase, False)),
   "host_groups"        : (["groups"], lambda phase: mode_groups(phase, "host")),
   "service_groups"     : (["groups"], lambda phase: mode_groups(phase, "service")),
   "contact_groups"     : (["users"], lambda phase: mode_groups(phase, "contact")),
   "edit_host_group"    : (["groups"], lambda phase: mode_edit_group(phase, "host")),
   "edit_service_group" : (["groups"], lambda phase: mode_edit_group(phase, "service")),
   "edit_contact_group" : (["users"], lambda phase: mode_edit_group(phase, "contact")),
   "notifications"      : (["notifications"], mode_notifications),
   "notification_rule"  : (["notifications"], lambda phase: mode_notification_rule(phase, False)),
   "user_notifications" : (["users"], lambda phase: mode_user_notifications(phase, False)),
   "notification_rule_p": (None, lambda phase: mode_notification_rule(phase, True)), # for personal settings
   "user_notifications_p":(None, lambda phase: mode_user_notifications(phase, True)), # for personal settings
   "timeperiods"        : (["timeperiods"], mode_timeperiods),
   "edit_timeperiod"    : (["timeperiods"], mode_edit_timeperiod),
   "import_ical"        : (["timeperiods"], mode_timeperiod_import_ical),
   "sites"              : (["sites"], mode_sites),
   "edit_site"          : (["sites"], mode_edit_site),
   "edit_site_globals"  : (["sites"], mode_edit_site_globals),
   "users"              : (["users"], mode_users),
   "edit_user"          : (["users"], mode_edit_user),
   "user_attrs"         : (["users"], lambda phase: mode_custom_attrs(phase, "user")),
   "edit_user_attr"     : (["users"], lambda phase: mode_edit_custom_attr(phase, "user")),
   "roles"              : (["users"], mode_roles),
   "role_matrix"        : (["users"], mode_role_matrix),
   "edit_role"          : (["users"], mode_edit_role),
   "hosttags"           : (["hosttags"], mode_hosttags),
   "edit_hosttag"       : (["hosttags"], mode_edit_hosttag),
   "edit_auxtag"        : (["hosttags"], mode_edit_auxtag),
   "pattern_editor"     : (["pattern_editor"], mode_pattern_editor),
   "bi_rules"           : (["bi_rules"], mode_bi_rules),
   "bi_rule_tree"       : (["bi_rules"], mode_bi_rule_tree),
   "bi_edit_rule"       : (["bi_rules"], mode_bi_edit_rule),
   "bi_edit_aggregation": (["bi_rules"], mode_bi_edit_aggregation),
}

loaded_with_language = False
def load_plugins():
    global g_git_messages
    g_git_messages = []

    global loaded_with_language
    if loaded_with_language == current_language:
        return

    # Reset global vars
    global extra_buttons, configured_host_tags, host_attributes, modules
    extra_buttons = []
    configured_host_tags = None
    host_attributes = []
    modules = []

    load_notification_table()

    global g_configvars, g_configvar_groups
    g_configvars = {}
    g_configvar_groups = {}

    global g_rulegroups, g_rulespecs, g_rulespec_group, g_rulespec_groups
    g_rulegroups = {}
    g_rulespecs = {}
    g_rulespec_group = {}
    g_rulespec_groups = []

    # Directories and files to synchronize during replication
    global replication_paths, backup_paths
    replication_paths = [
        ( "dir",  "check_mk",   root_dir ),
        ( "dir",  "multisite",  multisite_dir ),
        ( "file", "htpasswd",   defaults.htpasswd_file ),
        ( "file", "auth.secret",  '%s/auth.secret' % os.path.dirname(defaults.htpasswd_file) ),
        ( "file", "auth.serials", '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file) ),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ( "dir", "usersettings", defaults.var_dir + "/web" ),
    ]

    # Directories and files for backup & restore
    backup_paths = replication_paths + [
        ( "file", "sites",      sites_mk)
        # autochecks are a site-local ressource. This does only make
        # sense for single-site installations. How should we handle
        # this?
        # ( "dir", "autochecks", defaults.autochecksdir ),
    ]


    # Declare WATO-specific permissions
    config.declare_permission_section("wato", _("WATO - Check_MK's Web Administration Tool"))

    config.declare_permission("wato.use",
         _("Use WATO"),
         _("This permissions allows users to use WATO - Check_MK's "
           "Web Administration Tool. Without this "
           "permission all references to WATO (buttons, links, "
           "snapins) will be invisible."),
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

    config.declare_permission("wato.activateforeign",
         _("Activate Foreign Changes"),
         _("When several users work in parallel with WATO then "
           "several pending changes of different users might pile up "
           "before changes are activate. Only with this permission "
           "a user will be allowed to activate the current configuration "
           "if this situation appears."),
         [ "admin", ])

    config.declare_permission("wato.auditlog",
         _("Audit Log"),
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

    config.declare_permission("wato.parentscan",
         _("Perform network parent scan"),
         _("This permission is neccessary for performing automatic "
           "scans for network parents of hosts (making use of traceroute). "
           "Please note, that for actually modifying the parents via the "
           "scan and for the creation of gateway hosts proper permissions "
           "for host and folders are also neccessary."),
         [ "admin", "user" ])

    config.declare_permission("wato.move_hosts",
         _("Move existing hosts"),
         _("Move existing hosts to other folders. Please also add the permission "
           "<i>Modify existing hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.manage_hosts",
         _("Add & remove hosts"),
         _("Add hosts to the monitoring and remove hosts "
           "from the monitoring. Please also add the permission "
           "<i>Modify existing hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.diag_host",
         _("Host Diagnostic"),
         _("Check whether or not the host is reachable, test the different methods "
           "a host can be accessed, for example via agent, SNMPv1, SNMPv2 to find out "
           "the correct monitoring configuration for that host."),
         [ "admin", "user" ])


    config.declare_permission("wato.clone_hosts",
         _("Clone hosts"),
         _("Clone existing hosts to create new ones from the existing one."
           "Please also add the permission <i>Add & remove hosts</i>."),
         [ "admin", "user" ])

    config.declare_permission("wato.random_hosts",
         _("Create random hosts"),
         _("The creation of random hosts is a facility for test and development "
           "and disabled by default. It allows you to create a number of random "
           "hosts and thus simulate larger environments."),
         [ ])

    config.declare_permission("wato.update_dns_cache",
         _("Update DNS Cache"),
         _("Updating the DNS cache is neccessary in order to reflect IP address "
           "changes in hosts that are configured without an explicit address."),
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

    config.declare_permission("wato.automation",
        _("Site remote automation"),
        _("This permission is needed for a remote administration of the site "
          "as a distributed WATO slave."),
        [ "admin", ])

    config.declare_permission("wato.users",
         _("User management"),
         _("This permission is needed for the modules <b>Users</b>, <b>Roles</b> and <b>Contact Groups</b>"),
         [ "admin", ])

    config.declare_permission("wato.notifications",
         _("Notification configuration"),
         _("This permission is needed for the new rule based notification configuration via the WATO module <i>Notifications</i>."),
         [ "admin", ])

    config.declare_permission("wato.snapshots",
         _("Backup & Restore"),
         _("Access to the module <i>Backup & Restore</i>. Please note: a user with "
           "write access to this module "
           "can make arbitrary changes to the configuration by restoring uploaded snapshots "
           "and even do a complete factory reset!"),
         [ "admin", ])

    config.declare_permission("wato.pattern_editor",
         _("Logfile Pattern Analyzer"),
         _("Access to the module for analyzing and validating logfile patterns."),
         [ "admin", "user" ])

    config.declare_permission("wato.bi_rules",
        _("Business Intelligence Rules"),
        _("Edit the rules for the BI aggregations."),
         [ "admin" ])


    load_web_plugins("wato", globals())

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language
