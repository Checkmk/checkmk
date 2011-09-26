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
#   ".parent"         -> parent folder (not name, but Python reference!)
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

import sys, pprint, socket, re, subprocess, time, datetime, shutil, tarfile, StringIO
import config, htmllib
from lib import *

config.declare_permission("use_wato",
     _("Use WATO"),
     _("This permissions allows users to use WATO - Check_MK's Web Administration Tool."),
     [ "admin", "user" ])

root_dir     = defaults.check_mk_configdir + "/wato/"
var_dir      = defaults.var_dir + "/wato/"
log_dir      = var_dir + "log/"
snapshot_dir = var_dir + "/snapshots/"

ALL_HOSTS    = [ '@all' ]
ALL_SERVICES = [ "" ]
NEGATE       = '@negate'


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
    if not config.wato_enabled:
        raise MKGeneralException(_("WATO is disabled. Please set <tt>wato_enabled = True</tt> in your <tt>multisite.mk</tt> if you want to use WATO."))
    if not config.may("use_wato"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    declare_host_tag_attributes() # create attributes out of tag definitions
    load_all_folders()            # load information about all folders
    set_current_folder()          # set g_folder from HTML variable
    load_hosts(g_folder)          # load information about hosts
    title = g_folder["title"]     # title might be changed by actions

    current_mode = html.var("mode", "folder")
    modefunc = mode_functions.get(current_mode)

    # Do actions (might switch mode)
    action_message = None
    if html.has_var("_transid"):
        try:
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
                modefunc = mode_functions.get(newmode, mode_folder)
                current_mode = newmode
                html.set_var("mode", newmode) # will be used by makeuri

        except MKUserError, e:
            action_message = e.message
            html.add_user_error(e.varname, e.message)

    # Title
    mode_title = modefunc("title")
    if mode_title:
        title += " - " + mode_title
    html.header(title)
    html.write("<script type='text/javascript' src='js/wato.js'></script>")
    html.write("<div class=wato>\n")

    try:
        # Show contexts buttons
        html.begin_context_buttons()
        modefunc("buttons")
        for inmode, buttontext, target in extra_buttons:
            if inmode == current_mode:
                if '/' == target[0] or target.startswith('../') or '://' in target:
                    html.context_button(buttontext, target)
                else:
                    html.context_button(buttontext, make_link([("mode", target)]))
        html.end_context_buttons()

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

    except Exception, e:
        import traceback
        html.show_error(traceback.format_exc().replace('\n', '<br />'))

    html.write("</div>\n")
    html.footer()


def set_current_folder():
    global g_folder

    if html.has_var("folder"):
        path = html.var("folder")
    else:
        host = html.var("host")
        if host: # find host with full scan. Expensive operation
            path = find_host(host)
            if not path:
                raise MKGeneralException(_("The host <b>%s</b> is not managed by WATO.") % host)
        else: # fall back to root folder
            path = ""

    g_folder = g_folders.get(path)
    html.set_var("folder", path) # in case of implizit folder selection
    if not g_folder:
        raise MKGeneralException(_('You called this page with a non-existing folder! '
                                 'Go back to the <a href="wato.py">main index</a>.'))

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
            "roles"     : [ "admin" ], 
            "title"     : name and name or _("Main directory"),
            "num_hosts" : 0,
        }

    folder[".name"]    = name
    folder[".path"]    = path
    folder[".folders"] = {}

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
    for f in base_folder[".files"].values():
        hosts.update(load_hosts_file(base_folder, f))
    for f in base_folder[".folders"].values():
        hosts.update(load_all_hosts(f))
    return hosts

def load_hosts(folder):
    if ".hosts" not in folder:
        folder[".hosts"] = load_hosts_file(folder)
        folder["num_hosts"] = len(folder[".hosts"])
    return folder[".hosts"]


def load_hosts_file(folder):
    hosts = {}

    filename = root_dir + folder[".path"] + "/hosts.mk"
    if os.path.exists(filename):
        variables = {
            "ALL_HOSTS"          : ALL_HOSTS,
            "all_hosts"          : [],
            "ipaddresses"        : {},
            "extra_host_conf"    : { "alias" : [] },
            "extra_service_conf" : { "_WATO" : [] },
            "host_attributes"    : {},
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
            hosts[hostname]   = host


    # html.write("<pre>%s</pre>" % pprint.pformat(hosts))
    return hosts

def save_hosts(folder):
    folder_path = folder[".path"]
    dirname = root_dir + folder_path
    filename = dirname + "/hosts.mk"
    hosts = folder.get(".hosts", [])
    if len(hosts) == 0:
        if os.path.exists(filename):
            os.remove(filename)
        return

    all_hosts = []
    ipaddresses = {}
    hostnames = hosts.keys()
    hostnames.sort()
    for hostname in hostnames:
        host = hosts[hostname]
        effective = effective_attributes(host, folder)

        ipaddress = effective.get("ipaddress")

        # Compute tags from settings of each individual tag. We've got
        # the current value for each individual tag.
        tags = set([])
        for attr, topic in host_attributes:
            if isinstance(attr, HostTagAttribute):
                value = effective.get(attr.name())
                tags.update(attr.get_tag_list(value))

        all_hosts.append("|".join([hostname] + list(tags) + [ folder_path, 'wato' ]))
        if ipaddress:
            ipaddresses[hostname] = ipaddress

    if not os.path.isdir(dirname):
        os.makedirs(dirname)

    out = file(filename, "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    if len(all_hosts) > 0:
        out.write("all_hosts += ")
        out.write(pprint.pformat(all_hosts))
        if len(ipaddresses) > 0:
            out.write("\n\nipaddresses.update(")
            out.write(pprint.pformat(ipaddresses))
            out.write(")")
        out.write("\n")

    # Add custom macros for attributes that are to be present in Nagios
    custom_macros = {}
    for hostname, host in hosts.items():
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attrname in effective:
                nag_varname = attr.nagios_name()
                if nag_varname:
                    value = effective.get(attrname)
                    nagstring = attr.to_nagios(value)
                    if nag_varname not in custom_macros:
                        custom_macros[nag_varname] = {}
                    custom_macros.setdefault(nag_varname, {})[hostname] = nagstring
    for nag_varname, entries in custom_macros.items():
        macrolist = []
        for hostname, nagstring in entries.items():
            macrolist.append((nagstring, [hostname]))
        if len(macrolist) > 0:
            out.write("\n# %s\n" % host_attribute[attrname].title())
            out.write("extra_host_conf.setdefault(%r, []).extend(\n" % nag_varname)
            out.write("  %s)\n" % pprint.pformat(macrolist))

    # Write information about all host attributes into special variable - even
    # values stored for check_mk as well.
    out.write("\n# Host attributes (needed for WATO)\n")
    out.write("host_attributes.update(%s)\n" % pprint.pformat(hosts))


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
        return None

    elif phase == "buttons":
        folder_status_button()
        html.context_button(_("Configuration"),    make_link([("mode", "configuration")]), "configuration")
        html.context_button(_("Rulesets"),         make_link_to([("mode", "rulesets")], g_folder), "rulesets")
        html.context_button(_("Properties"),       make_link_to([("mode", "editfolder")], g_folder), "properties")
        html.context_button(_("New folder"),       make_link([("mode", "newfolder")]), "newfolder")
        html.context_button(_("New host"),         make_link([("mode", "newhost")]), "new")
        html.context_button(_("Backup / Restore"), make_link([("mode", "snapshot")]), "backup")
        changelog_button()
        search_button()
    
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
                return delete_folder_after_confirm(del_folder)
            else:
                raise MKGeneralException(_("You called this page with a non-existing folder/file %s") % delname)

        ### Operations on HOSTS

        # Deletion of single hosts
        delname = html.var("_delete_host")
        if delname and delname in g_folder[".hosts"]:
            return delete_host_after_confirm(delname)

        # Move single hosts to other files
        if html.has_var("_move_host_to"):
            hostname = html.var("host")
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
            return delete_hosts_after_confirm(selected_hosts)

        # Move
        elif html.var("_bulk_move"):
            target_file = html.var("bulk_moveto")
            if not target_file:
                raise MKUserError("bulk_moveto", _("Please select the destination file"))
            num_moved = move_hosts_to(selected_hosts, target_file)
            return None, _("Successfully moved %d hosts to %s") % (num_moved, target_file)

        # Move to target folder (from import)
        elif html.var("_bulk_movetotarget"):
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
            html.write("<div class=info>" + 
            _("There are no sub folders and no hosts in this folder. ") +
            "</div>")


def show_subfolders(folder):
    if len(folder[".folders"]) == 0:
        return False

    html.write("<h3>" + _("Subfolders") + "</h3>")
    html.write("<table class=data>\n")
    html.write("<tr><th class=left>" + _("Actions") + "</th><th>" + _("Title") + "</th>")

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

        edit_url     = make_link_to([("mode", "editfolder")], entry)
        delete_url   = make_action_link([("mode", "folder"), 
                       ("_delete_folder", entry[".name"])])
        enter_url    = make_link_to([], entry)

        html.write("<td class=buttons>")
        html.buttonlink(edit_url, _("Properties"))
        html.buttonlink(delete_url, _("Delete"))
        html.write("</td>")


        # Title and filename
        html.write('<td class=takeall><a href="%s">%s</a></td>' % 
                    (enter_url, entry["title"]))

        # Attributes for Hosts
        for attr, topic in host_attributes:
            if attr.show_in_table() and attr.show_in_folder():
                attrname = attr.name()
                if attrname in entry.get("attributes", {}):
                    tdclass, content = attr.paint(entry["attributes"][attrname], "")
                else:
                    tdclass, content = "", ""
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
    # We assume that the hosts of the folder already have been loaded
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

    hostnames = g_folder[".hosts"].keys()
    hostnames.sort()

    # Show table of hosts in this folder
    colspan = 6
    html.begin_form("hosts", None, "POST", onsubmit = 'add_row_selections(this);')
    html.write("<table class=data>\n")
    html.write("<tr><th class=left></th><th></th><th>" + _("Hostname") + "</th>")

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
        html.button("_bulk_delete", _("Delete"))
        html.button("_bulk_edit", _("Edit"))
        html.button("_bulk_cleanup", _("Cleanup"))
        html.button("_bulk_inventory", _("Inventory"))
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
    if more_than_ten_items:
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
        html.buttonlink(edit_url,     _("Edit"))
        html.buttonlink(services_url, _("Services"))
        html.buttonlink(clone_url,    _("Clone"))
        html.buttonlink(delete_url,   _("Delete"))
        html.write("</td>\n")

        # Hostname with link to details page (edit host)
        html.write('<td><a href="%s">%s</a></td>\n' % (edit_url, hostname))

        # Show attributes
        for attr, topic in host_attributes:
            attrname = attr.name()
            if attr.show_in_table():
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
        host_move_combo(hostname)
        html.write("</td>\n")
        html.write("</tr>\n")

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
        if config.role in afolder["roles"] and afolder != g_folder:
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
            html.select(field_name, selections, "",
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
    if target_folder == g_folder:
        return # target and source are the same

    if config.role not in target_folder["roles"]:
        raise MKAuthException(_("You have no change permissions on the target folder"))

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
        log_pending(target_file, "move-host", _("Moved %d hosts from %s to %s") %
            (num_moved, g_folder[".path"], target_folder[".path"]))
    return num_moved 
        

def move_host_to(hostname, target_filename):
    move_hosts_to([hostname], target_filename)
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
            os.remove(folder_path + "/.wato")
            os.rmdir(folder_path)
        except:
            pass
        if os.path.exists(folder_path):
            raise MKGeneralException(_("Cannot remove the folder '%s': probably there are "
                                       "still non-WATO files contained in this directory.") % folder_path)

        log_audit(folder_dir(del_folder), "delete-folder", _("Deleted empty folder %s")% folder_dir(del_folder))
        call_hook_folder_deleted(del_folder)
        html.reload_sidebar() # refresh WATO snapin
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
        name, title, roles = None, None, []
        mode = "new"
    else:
        page_title = _("Edit Properties")
        name  = g_folder[".name"]
        title = g_folder["title"]
        roles = g_folder["roles"]
        mode = "edit"

    if phase == "title":
        return page_title

    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "folder")]), "abort")
            
    elif phase == "action":
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

        # Roles and Permissions
        roles = [ role for role in config.roles if html.var("role_" + role) ]

        attributes = collect_attributes()
        attributes_changed = not new and attributes != g_folder.get("attributes", {})

        if new:
            newpath = g_folder[".path"] + "/" + name
            new_folder = { 
                ".name"       : name,
                ".path"       : newpath,
                "title"      : title, 
                "roles"      : roles,
                "attributes" : attributes,
                ".folders"   : {},
                ".hosts"     : {},
                "num_hosts"  : 0,
            }
            g_folders[newpath] = new_folder
            g_folder[".folders"][name] = new_folder
            save_folder(new_folder)
            call_hook_folder_created(new_folder)

            log_audit(new_folder, "new-folder", _("Created new folder %s") % title)

        else:
            log_pending(g_folder, "edit-folder", "Edited properties of folder %s" % title)

            g_folder["title"]      = title
            g_folder["roles"]      = roles
            g_folder["attributes"] = attributes

        
        html.reload_sidebar() # refresh WATO snapin. FIXME: Geht das nicht besser?
        save_folder_and_hosts(g_folder) # save folder metainformation

        # Due to changes in folder/file attributes, host files
        # might need to be rewritten in order to reflect Changes
        # in Nagios-relevant attributes.
        if attributes_changed:
            rewrite_config_files_below(g_folder) # due to inherited attributes
            log_pending(g_folder, "edit-folder", _("Changed attributes of folder %s") % title)
            call_hook_hosts_changed(g_folder)

        return "folder"


    else:
        html.begin_form("editfolder")
        html.write('<table class="form">\n')
        
        # title
        html.write("<tr><td class=legend colspan=2>Title</td><td class=content>")
        html.text_input("title", title)
        html.set_focus("title")
        html.write("</td></tr>\n")

        # folder name (omit this for root folder)
        if not (not new and g_folder == g_root_folder):
            if not config.wato_hide_filenames:
                html.write("<tr><td class=legend colspan=2>" 
                    + _("Internal directory name") + "<br><i>"
                    + _("This is the name of subdirectory where the files and<br> "
                    "other folders will be created. You cannot change this later") +
                    "</i></td><td class=content>")

                if new:
                    html.text_input("name")
                else:
                    html.write(name)

                html.write("</td></tr>\n")

        # permissions
        html.write("<tr><td class=legend colspan=2>" 
                   + _("Grant access to") + "</td><td class=content>")
        for role in config.roles:
            html.checkbox("role_" + role, role in g_folder["roles"])
            html.write(" " + role + "<br>")
        html.write("</td></tr>")

        # Attributes inherited to hosts
        if have_folder_attributes():
            html.write("<tr><td class=title colspan=3>")
            html.write(_("The following attributes will be inherited to all hosts "
                         "in this folder"))
            html.write("</td></tr>")
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
        title = _("Edit host ") + hostname
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
        html.context_button(_("Abort"), make_link([("mode", "folder")]), "abort")
        if not new:
            html.context_button(_("Services"), 
                  make_link([("mode", "inventory"), ("host", hostname)]))

    elif phase == "action":
        if not new and html.var("delete"): # Delete this host
            if not html.transaction_valid():
                return "folder"
            else:
                return delete_host_after_confirm(hostname)

        host = collect_attributes()

        # handle clone & new
        if new:
            if not hostname:
                raise MKUserError("host", _("Please specify a host name"))
            elif hostname in g_folder[".hosts"]:
                raise MKUserError("host", _("A host with this name already exists."))
            elif not re.match("^[a-zA-Z0-9-_.]+$", hostname):
                raise MKUserError("host", _("Invalid host name: must contain only characters, digits, dash, underscore and dot."))

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
        html.begin_form("edithost")
        html.write('<table class="form">\n')

        # host name
        html.write("<tr><td class=legend colspan=2>" + _("Hostname") + "</td><td class=content>")
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
        html.context_button(_("Folder"), make_link([("mode", "folder")]))
        html.context_button(_("Edit host"), 
                            make_link([("mode", "edithost"), ("host", hostname)]))
        html.context_button(_("Full Scan"), html.makeuri([("_scan", "yes")]))

    elif phase == "action":
        if html.check_transaction():
            cache_options = not html.var("_scan") and [ '--cache' ] or []
            table = check_mk_automation("try-inventory", cache_options + [hostname])
            table.sort()
            active_checks = {}
            new_target = "folder"
            for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
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
            message = _("Saved check configuration of host [%s] with %d services") % (hostname, len(active_checks)) 
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
        for st, ct, item, paramstring, params, descr, state, output, perfdata in table:
            if state_type != st:
                continue
            if first:
                html.write('<tr class=groupheader><td colspan=7><br>%s</td></tr>\n' % state_name)
                html.write("<tr><th>" + _("Status") + "</th><th>" + _("Checktype") + "</th><th>" + _("Item") + "</th>"
                           "<th>" + _("Service Description") + "</th><th>" + _("Current check") + "</th><th></th></tr>\n")
                first = False
            trclass = trclass == "even" and "odd" or "even"
            statename = nagios_short_state_names.get(state, "PEND")
            if statename == "PEND":
                stateclass = "state svcstate statep"
                state = 0 # for tr class
            else:
                stateclass = "state svcstate state%s" % state
            html.write("<tr class=\"data %s%d\"><td class=\"%s\">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>" %
                    (trclass, state, stateclass, statename, ct, item, descr, output))
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
        html.context_button(_("Back"), make_link_to([("mode", "folder")], g_folder), "back")

    elif phase == "action":
        pass

    else:
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
        target_file = create_target_file_from_aliaspath(imported_folder)
        num_moved += move_hosts_to(hosts, target_file) 

    save_folder_config()
    html.reload_sidebar() # refresh WATO snapin
    return None, _("Successfully moved %d hosts to their original folder destinations.") % num_moved


def create_target_file_from_aliaspath(aliaspath):
    # The alias path is a '/' separated path of folder titles.
    # An empty path is interpreted as root path. The actual file
    # name is the host list with the name "Hosts". 
    if aliaspath == "":
        folder = g_root_folder
    else:
        parts = aliaspath.split("/")
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
                new_folder = {
                    ".name" : name,
                    ".path" : folder[".path"] + (name,),
                    "title" : parts[0],
                    "roles" : folder["roles"],
                    "attributes" : {}, 
                    ".folders" : {},
                    ".files" : {},
                }
                folder[".folders"][name] = new_folder
                folder = new_folder
                parts = parts[1:]

    # Now folder points to the folder the host needs to be created
    # in. In that folder we put the host into the host list "hosts.mk". 
    if "hosts.mk" not in folder[".files"]:
        new_file = {
            ".name" : "hosts.mk",
            ".path" : folder[".path"] + ("hosts.mk",),
            "title" : _("Hosts"),
            "roles" : folder["roles"],
            "attributes" : {},
            "num_hosts" : 0, 
        }
        folder[".files"]["hosts.mk"] = new_file 
        g_files[new_file[".path"]] = new_file

    the_file = folder[".files"]["hosts.mk"]
    return "/" + "/".join(the_file[".path"])



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
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
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
        html.button("_start", _("Start!"))
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
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
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
            call_hook_hosts_changed(g_file)
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
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
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
        return _("Change log")

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        if log_exists("pending"):
            html.context_button(_("Activate Changes!"), 
                html.makeuri([("_action", "activate"), ("_transid", html.current_transid())]), "apply", True)
        if log_exists("audit"):
            html.context_button(_("Clear Audit Log"),
                html.makeuri([("_action", "clear"), ("_transid", html.current_transid())]), "trash")
            html.context_button(_("Download Audit Log"),
                html.makeuri([("_action", "csv"), ("_transid", html.current_transid())]), "csv")

    elif phase == "action":
        if html.var("_action") == "clear":
            return clear_audit_log_after_confirm()

        elif html.var("_action") == "csv":
            return export_audit_log()

        elif html.check_transaction():
                create_snapshot()
                try:
                    check_mk_automation("restart")
                    call_hook_activate_changes()
                except Exception, e:
                    raise MKUserError(None, str(e))
                log_commit_pending() # flush logfile with pending actions
                log_audit(None, "activate-config", _("Configuration activated, monitoring server restarted"))
                return None, _("The new configuration has been successfully activated.")


    else:
        pending = parse_audit_log("pending")
        render_audit_log(pending, "pending")

        audit = parse_audit_log("audit")
        render_audit_log(audit, "audit")


def log_entry(linkinfo, action, message, logfilename):
    if type(message) == unicode:
        message = message.encode("utf-8")

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
    f.write("%d %s %s %s " % (int(time.time()), link, html.req.user, action))
    f.write(message)
    f.write("\n")


def log_audit(linkinfo, what, message):
    log_entry(linkinfo, what, message, "audit.log")


def log_pending(linkinfo, what, message):
    log_entry(linkinfo, what, message, "pending.log")
    log_entry(linkinfo, what, message, "audit.log")

def log_commit_pending():
    pending = log_dir + "pending.log"
    if os.path.exists(pending):
        os.remove(pending)

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
            entries.append(line.split(None, 4))
        entries.reverse()
        return entries
    return []

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
        t = int(t)
        if t >= end_time:
            # This log is too new
            continue
        elif first_log_index is None and t < end_time and t >= start_time:
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
        htmlcode += "<b>" + _("All Changes") + "</b>"
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
        htmlcode += '<td>%s</td><td>%s</td><td>%s</td><td width="100%%">%s</td></tr>\n' % (
                                          fmt_date(float(t)), fmt_time(float(t)), user, text)
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
        raise MKGeneralException("Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>%s" %
              (" ".join(cmd), exitcode, outdata, sudo_msg))
    try:
        return eval(outdata)
    except Exception, e:
        raise MKGeneralException("Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
                      (" ".join(cmd), e, outdata))



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
           ("folder", g_folder[".path"])]), 
           "status")  # TODO: support for distributed WATO

def search_button():
    html.context_button(_("Search"), make_link([("mode", "search")]), "search")

def changelog_button():
    pending = parse_audit_log("pending")
    buttontext = _("ChangeLog")
    if len(pending) > 0:
        buttontext = "<b>%s (%d)</b>" % (buttontext, len(pending))
        hot = True
    else:
        hot = False
    html.context_button(buttontext, make_link([("mode", "changelog")]), "wato_changes", hot)

def find_host(host):
    return find_host_in(host, g_root_folder)

def find_host_in(host, folder):
    for f in folder.get(".files", {}).values():
        hosts = load_hosts_file(folder, f)
        if host in hosts:
            return f[".path"]

    for f in folder.get(".folders", {}).values():
        p = find_host_in(host, f)
        if p != None:
            return p

def num_hosts_in(folder, recurse):
    if not "num_hosts" in folder:
        load_hosts(folder)
        save_folder(folder)

    if not recurse:
        return folder["num_hosts"]

    num = 0
    for subfolder in folder[".folders"].values():
        num += num_hosts_in(subfolder, True)
    num += folder["num_hosts"]
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
    if not html.var("filled_in") == "confirm":
        wato_html_head(html_title)
    return html.confirm(message)

g_html_head_open = False

def wato_html_head(title):
    global g_html_head_open
    g_html_head_open = True
    html.header(title)
    html.write("<div class=wato>\n")

def render_folder_path(the_folder = 0, link_to_last = False):
    if the_folder == 0:
        the_folder = g_folder

    def render_component(folder):
        return '<a href="%s">%s</a>' % (
               html.makeuri_contextless([("folder", folder[".path"])]), folder["title"])

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

    html.write("<div class=folderpath>%s</div>\n" % " / ".join(parts))

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
        return value.encode("utf-8")

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
    def __init__(self, nr, tag_definition):
        # In newer days, the tag defitions contain a third
        # element: the id of the tag group - written at the
        # beginning of the tuple. If that is present, we use
        # it as id, otherwise we use the number.
        if len(tag_definition) >= 3:
            name = "tag_" + tag_definition[0]
            tag_definition = tag_definition[1:]
        else:
            name = "tag_%d" % nr

        title, self._taglist = tag_definition 
        Attribute.__init__(self, name, title, "", self._taglist[0][0])

    def paint(self, value, hostname):
        for entry in self._taglist:
            if value == entry[0]:
                return "", entry[1]
        return "", "" # Should never happen, at least one entry should match
                      # But case could occur if tags definitions have been changed.

    def render_input(self, value):
        choices = [e[:2] for e in self._taglist]
        html.select("attr_" + self.name(), choices, value)

    def from_html_vars(self):
        value = html.var("attr_" + self.name())
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

        for num, entry in enumerate(config.wato_host_tags):
            declare_host_attribute(HostTagAttribute(num + 1, entry), show_in_table = False, show_in_folder = True, topic = _("Host tags"))

        configured_host_tags = config.wato_host_tags


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
            # html.write("<tr><td colspan=3 class=buttons>")
            html.begin_foldable_container("wato_attributes", title, 
                                          topic == None, title, indent = False)
            html.write("<table class=form>")

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
                html.write("<table class=form>")


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
    chain = [ host ]
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
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        html.context_button(_("Create Snapshot"), make_action_link([("mode", "snapshot"),("_create_snapshot","Yes")]))
        return
    elif phase == "action":
        if html.has_var("_download_file"):
            # FIXME: HTML Variable pruefen, kein join verwenden
            download_file = os.path.join(snapshot_dir, html.var("_download_file"))
            if os.path.exists(download_file):
                html.req.headers_out['Content-Disposition'] = 'Attachment; filename=' + html.var("_download_file")
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
        self._title = kwargs.get("title")
        self._help  = kwargs.get("help")

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

    # Create a canonical, minimal, default value that 
    # matches the datatype of the value specification and
    # fullfills also data validation.
    def default_value(self):
        return None

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


# Editor for a single integer
class Integer(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size     = kwargs.get("size", 5)
        self._minvalue = kwargs.get("minvalue") 
        self._maxvalue = kwargs.get("maxvalue")
        self._label    = kwargs.get("label")

    def default_value(self):
        if self._minvalue:
            return self._minvalue
        else:
            return 0

    def render_input(self, varprefix, value):
        html.number_input(varprefix, str(value), self._size)
        if self._label:
            html.write(" ")
            html.write(self._label)

    def from_html_vars(self, varprefix):
        try:
            return int(html.var(varprefix))
        except:
            raise MKUserError(varprefix, 
                  _("The text <b><tt>%s</tt></b> is not a valid integer number." % html.var(varprefix)))

    def validate_datatype(self, value, varprefix): 
        if type(value) != int:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type int") % (type(value)))
 
    def validate_value(self, value, varprefix):
        if self._minvalue != None and value < self._minvalue:
            raise MKUserError(varprefix, _("The minimum allowed value is %d." % self._minvalue))
        if self._maxvalue != None and value > self._maxvalue:
            raise MKUserError(varprefix, _("The maximum allowed value is %d." % self._maxvalue))

# Editor for a line of text
class TextAscii(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size     = kwargs.get("size", 30)

    def default_value(self):
        return ""

    def render_input(self, varprefix, value):
        html.text_input(varprefix, str(value), self._size)

    def value_to_text(self, value):
        return value

    def from_html_vars(self, varprefix):
        return html.var(varprefix, "")

    def validate_datatype(self, value, varprefix): 
        if type(value) != str:
            raise MKUserError(varprefix, _("The value must be of type str, but it has type %s") % type(value)) 

    #def validate_value(self, value, varprefix):
    #    pass

# A variant of TextAscii() that validates a path to a filename that 
# lies in an existing directory.
class Filename(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        if "default" in kwargs:
            self._default_path = kwargs["default"]
        else:
            self._default_path = "/tmp/foo"

    def default_value(self):
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
    
    def default_value(self):
        return float(Integer.default_value(self))

    def from_html_vars(self, varprefix):
        try:
            return float(html.var(varprefix))
        except:
            raise MKUserError(varprefix, 
            _("The text <b><tt>%s</tt></b> is not a valid floating point number." % html.var(varprefix)))

    def validate_datatype(self, value, varprefix): 
        if type(value) != float:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type float") % (type(value)))


class Checkbox(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs) 
        self._label = kwargs.get("label")

    def default_value(self):
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

class DropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs["choices"]

    def default_value(self):
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


# Make a configuration value optional, i.e. it may be None.
# The user has a checkbox for activating the option. Example:
# debug_log: it is either None or set to a filename.
class Optional(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = valuespec
        self._label = kwargs.get("label")

    def default_value(self):
        return None

    def render_input(self, varprefix, value): 
        div_id = "option_" + varprefix
        if html.has_var(varprefix + "_use"):
            checked = html.get_checkbox(varprefix + "_use")
        else:
            checked = value != None
        html.checkbox(varprefix + "_use" , checked,
                      onclick="wato_toggle_option(this, %r)" % div_id)
        if self._label:
            html.write(self._label)
        else:
            html.write(_(" Activate this option"))
        html.write("<br><br>")
        html.write('<div id="%s" style="display: %s">' % (
                div_id, not checked and "none" or ""))
        if value == None:
            value = ""
        self._valuespec.render_input(varprefix + "_value", value)
        html.write('</div>')

    def value_to_text(self, value):
        if value == None:
            return _("(unset)")
        else:
            return value

    def from_html_vars(self, varprefix): 
        if html.get_checkbox(varprefix + "_use"):
            return self._valuespec.from_html_vars(varprefix + "_value")
        else:
            return None

    def validate_datatype(self, value, varprefix): 
        if value != None:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def validate_value(self, value, varprefix):
        if value != None:
            self._valuespec.validate_value(value, varprefix + "_value")

# Edit a n-tuple (with fixed size) of values
class Tuple(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]

    def default_value(self):
        return tuple([x.default_value() for x in self._elements])

    def render_input(self, varprefix, value):
        html.write("<table>")
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            html.write("<tr><td>%s<br>%s</td>" % (element.title(), element.help()))
            html.write("<td>")
            element.render_input(vp, val)
            html.write("</td></tr>")
        html.write("</table>")

    def value_to_text(self, value): 
        return "(" + ",".join([ element.value_to_text(val) 
                         for (element, val)
                         in zip(self._elements, value)]) + ")"

    def from_html_vars(self, varprefix):
        value = []
        for no, element in enumerate(self._elements):
            vp = varprefix + "_" + str(no)
            value.append(element.from_html_vars(vp))
        return tuple(value)

    def validate_value(self, value, varprefix):
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_value(vp, val)

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
            

def edit_value(valuespec, value):
    html.begin_form("value_editor")
    html.write("<h3>%s</h3>" % valuespec.title())
    html.write("<table class=form><tr>")
    if valuespec.help() != None:
        html.write('<td class=legend>%s</td>' % valuespec.help()) 
    html.write("<td class=content>")
    valuespec.render_input("ve", value) 
    html.write("</td></tr>")
    html.write("<tr><td class=buttons colspan=2>")
    html.button("save", _("Save"))
    html.write("</td></tr></table>")
    html.hidden_fields()
    html.set_focus("ve")
    html.end_form()

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
#   | WATO's new editor for configuration variables in main.mk (except     |
#   | rule based parameters. Those are handled separately).                |
#   +----------------------------------------------------------------------+
def mode_configuration(phase):
    valuespec = Integer(title="TCP Port used by Check_MK Agent", size=5, minvalue=1, maxvalue=65535)

    valuespec = Tuple(
       title="Default filesystem levels",
       elements = [
           Integer(title = "Warning (MB)"),
           Integer(title = "Critical (MB)")]
    )

    if phase == "title":
        return "Global configuration settings for Check_MK"

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        return
    
    # Get default settings of all configuration variables of interest (this
    # also reflects the settings done in main.mk)
    default_values = check_mk_automation("get-configuration", [], g_configvars.keys())
    current_settings = load_configuration_settings()

    if phase == "action":
        varname = html.var("_reset")
        if varname:
            valuespec = g_configvars[varname]
            def_value = default_values[varname]

            c = wato_confirm(
                _("Resetting configuration variable"),
                _("Do you really want to reset the configuration variable <b>%s</b> "
                  "from its current value of <b><tt>%s</tt></b> back to the default value "
                  "of <b><tt>%s</tt></b>") % (varname, "4711", valuespec.value_to_text(def_value)))
            if c:
                del current_settings[varname]
                save_configuration_settings(current_settings)
                msg = _("Resetted configuration variable %s to its default.") % varname
                log_pending(None, "edit-configvar", msg)
                return "configuration", msg 
            elif c == False:
                return ""
            else:
                return None

    groupnames = g_configvar_groups.keys()
    groupnames.sort()
    html.write("<table class=data>")
    for groupname in groupnames:
        html.write("<tr><td colspan=4><h3>%s</h3></td></tr>\n" % groupname) 
        html.write("<tr><th></th><th>" + _("Configuration variable") + 
                   "</th><th>" + _("Default") + "</th><th>" + _("Your setting") + "</th></tr>\n")
        odd = "even"
            
        for varname, valuespec in g_configvar_groups[groupname]: 
            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)
            if varname not in default_values:
                if config.debug:
                    raise MKGeneralException("The configuration variable <tt>%s</tt> is unknown to "
                                          "your local Check_MK installation" % varname)
                else:
                    continue
                
            defaultvalue = default_values[varname]
            edit_url = make_link([("mode", "edit_configvar"), ("varname", varname)])

            html.write("<td class=buttons>")
            html.buttonlink(edit_url, _("Edit"))
            if varname in current_settings: 
                reset_url = make_action_link([("mode", "configuration"), ("_reset", varname)])
                html.buttonlink(reset_url, _("Reset"))
            html.write("</td>")

            html.write('<td>%s</td>' % valuespec.title())
            if varname in current_settings: 
                html.write('<td class=inherited>%s</td>' % valuespec.value_to_text(defaultvalue))
                html.write('<td><b>%s</b></td>'          % valuespec.value_to_text(current_settings[varname]))
            else:
                html.write('<td><b>%s</b></td>'                 % valuespec.value_to_text(defaultvalue))
                html.write('<td></td>')
            html.write('</tr>')
    html.write("</table>")


def mode_edit_configvar(phase):
    if phase == "title":
        return "Global configuration settings for Check_MK"

    elif phase == "buttons":
        html.context_button(_("Abort"), make_link([("mode", "configuration")]), "abort")
        return

    varname = html.var("varname")
    valuespec = g_configvars[varname]
    current_settings = load_configuration_settings() 

    if phase == "action":
        new_value = get_edited_value(valuespec)
        current_settings[varname] = new_value
        save_configuration_settings(current_settings)
        msg = _("Changed global configuration variable %s to %s.") \
              % (varname, valuespec.value_to_text(new_value)) 
        log_pending(None, "edit-configvar", msg)
        return "configuration"
    
    if varname in current_settings:
        value = current_settings[varname]
    else:
        value = check_mk_automation("get-configuration", [], [varname])[varname]

    edit_value(valuespec, value)

g_configvars = {}
g_configvar_groups = {}
def register_configvar(group, name, valuespec):
    g_configvar_groups.setdefault(group, []).append((name, valuespec))
    g_configvars[name] = valuespec
 

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
    try:
        settings = {}
        execfile(root_dir + "global.mk", settings, settings)
        for varname in settings.keys():
            if varname not in g_configvars:
                del settings[varname]
        return settings
    except:
        return {}

def save_configuration_settings(vars):
    make_nagios_directory(root_dir)
    out = file(root_dir + "global.mk", "w")
    out.write("# Written by WATO\n# encoding: utf-8\n\n")
    for varname, value in vars.items():
        out.write("%s = %r\n" % (varname, value))
    

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
    if phase == "title":
        return "Rule sets for hosts and services"

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "folder")]), "back")
        return
    
    elif phase == "action":
        return

    rulesets = load_rulesets(g_folder)
    groupnames = g_ruleset_groups.keys()
    groupnames.sort()
    html.write("<table class=data>")
    for groupname in groupnames:
        html.write("<tr><td colspan=4><h3>%s</h3></td></tr>\n" % groupname) 
        html.write("<tr><th></th><th>" + _("Rule set") + "</th>"
                   "<th>" + _("Check_MK Variable") + "</th><th>" + _("Rules") + "</th></tr>\n")
        odd = "even"
            
        for ruleset in g_ruleset_groups[groupname]: 
            varname = ruleset["varname"]
            valuespec = ruleset["valuespec"]
            num_rules = len(rulesets.get(varname, []))

            odd = odd == "odd" and "even" or "odd" 
            html.write('<tr class="data %s0">' % odd)
            edit_url = make_link([("mode", "edit_ruleset"), ("varname", varname)])

            html.write("<td class=buttons>")
            html.buttonlink(edit_url, _("Edit"))
            html.write("</td>")
            html.write('<td>%s</td>' % ruleset["title"])
            varname = ruleset["varname"]
            if ':' in varname:
                varname = '%s["%s"]' % tuple(varname.split(":"))
            html.write('<td><tt>%s</tt></td>' % varname)
            html.write('<td class=number>%d</td>' % num_rules)
            html.write('</tr>')
    html.write("</table>")
    

def mode_edit_ruleset(phase): 
    varname = html.var("varname")
    ruleset = g_rulesets[varname]

    if phase == "title":
        return _("Rule set") + " " + ruleset["title"]

    elif phase == "buttons":
        html.context_button(_("Back"), make_link([("mode", "rulesets")]), "back")
        html.context_button(_("New rule (top)"),    html.makeactionuri([("_new", "top")]), "new")
        html.context_button(_("New rule (bottom)"), html.makeactionuri([("_new", "bottom")]), "new")
        return

    elif phase == "action":
        if html.var("_new"):
            if not html.check_transaction():
                return

            configured_rulesets = load_rulesets(g_folder) 
            rules = configured_rulesets.get(varname, [])
            new_rule = []
            valuespec = ruleset["valuespec"]
            if valuespec:
                new_rule.append(valuespec.default_value())
            if html.var("_new") == "top":
                new_rule.append([]) # better not match if new rule has precedence
            else:
                new_rule.append(ALL_HOSTS) # bottom: default to catch-all rule
            if ruleset["itemtype"]:
                new_rule.append([])
            new_rule = tuple(new_rule)
            if html.var("_new") == "top":
                rules[0:0] = [new_rule]
            else:
                rules.append(new_rule)
            save_rulesets(g_folder, configured_rulesets)
            log_pending(None, "edit-ruleset", 
                        _("Created new rule in ruleset %s") % ruleset["title"])
            return


        rulenr = int(html.var("_rulenr"))
        action = html.var("_action")
        configured_rulesets = load_rulesets(g_folder) 
        rules = configured_rulesets.get(varname, [])

        if action == "delete":
            c = wato_confirm(_("Confirm"), _("Delete rule number %d?") % rulenr)
            if c:
                del rules[rulenr - 1]
                save_rulesets(g_folder, configured_rulesets)
                log_pending(None, "edit-ruleset", 
                      _("Changed order of rules in ruleset %s") % ruleset["title"])
                return
            elif c == False: # not yet confirmed
                return ""
            else:
                return None # browser reload 
        elif action == "toggle":
            if html.check_transaction():
                rule = list(rules[rulenr - 1])
                if rule[0] == NEGATE:
                    del rule[0]
                else:
                    rule[0:0] = [NEGATE]
                rules[rulenr - 1] = tuple(rule)
                save_rulesets(g_folder, configured_rulesets)
                log_pending(None, "edit-ruleset", 
                      _("Negated result of rule %d in ruleset %s") % (rulenr, ruleset["title"]))

            return


        else:
            rule = rules[rulenr - 1]
            del rules[rulenr - 1]
            if action == "up":
                rules[rulenr-2:rulenr-2] = [ rule ]
            else:
                rules[rulenr:rulenr] = [ rule ]
            save_rulesets(g_folder, configured_rulesets)
            log_pending(None, "edit-ruleset", 
                     _("Changed order of rules in ruleset %s") % ruleset["title"])
            return


    html.write("<h3>%s</h3>\n" % ruleset["title"])
    html.write("<p>%s</p>\n" % ruleset["help"])
    all_configured_rulesets = load_rulesets(g_folder) 
    
    rules = all_configured_rulesets.get(varname, [])
    for n, rule in enumerate(rules):
        render_rule(ruleset, rule, n + 1, n == len(rules) - 1)

def rule_button(action, rulenr):
    url = html.makeactionuri([("_rulenr", str(rulenr)), ("_action", action)])
    html.write('<div class="button %s">'
               '<a href="%s">'
               '<img src="images/button_%s_lo.png" ' 
               'onmouseover=\"hilite_icon(this, 1)\" '
               'onmouseout=\"hilite_icon(this, 0)\">'
               '</a></div>\n' % (action, url, action))


def parse_rule(ruleset, rule):
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

    return value, tag_specs, host_list, item_list # (item_list currently not supported)

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


def render_rule(ruleset, rule, rulenr, islast):
    varname = ruleset["varname"]
    html.write('<div class="rule">')
    html.write('<div class="nr"><b>%d</b></div>' % rulenr)
    rule_button("delete", rulenr)
    if rulenr != 1:
        rule_button("up", rulenr)
    if not islast:
        rule_button("down", rulenr)

    value, tag_specs, host_list, item_list = parse_rule(ruleset, rule)

    html.write('<div class="conditions title">%s</div>'  % _("Preconditions"))
    html.write('<div class="value title">%s</div>' % _("Value"))

    render_conditions(ruleset, tag_specs, host_list, item_list, varname, rulenr)
    if ruleset["valuespec"]:
        value_html = ruleset["valuespec"].value_to_text(value)
        boolval = None # no boolean ruleset
    else:
        boolval = value # boolean ruleset
        img = value and "yes" or "no"
        title = value and _("This rule results in a positive outcome.") \
                      or  _("this rule results in a negative outcome.")
        title += " " + _("Click to toggle outcome of this rule.")
        value_html = '<img title="%s" src="images/rule_%s.png">' % (title, img)
        
    html.write('<div class="value box" %s>%s</div>' % 
          (ruleeditor_hover_code(varname, rulenr, "edit_rulevalue", boolval), value_html))
           

    html.write('</div>')

def tag_alias(tag):
    for id, title, tags in config.wato_host_tags:
        for t in tags:
            if t[0] == tag:
                return t[1]

def render_conditions(ruleset, tagspecs, host_list, item_list, varname, rulenr):
    html.write('<div class="conditions box" %s><ul>' % 
      ruleeditor_hover_code(varname, rulenr, "edit_ruleconds", None))

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
            html.write(_("Host is of type "))
            if negate:
                html.write("<b>" + _("not") + "</b> ")
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
    if ruleset["itemtype"] == "service":
        if item_list != ALL_SERVICES:
            tt_list = [ "<tt><b>%s</b></tt>" % t for t in item_list ]
            condition = _("Service name begins with ") + " or with ".join(tt_list)
            html.write('<li class="condition">%s</li>' % condition)


    html.write('</ul></div>')

def ruleeditor_hover_code(varname, rulenr, mode, boolval):
    if boolval in [ True, False ]:
        url = html.makeactionuri([("_rulenr", rulenr), ("_action", "toggle")])
    else:
        url = make_link([("mode", mode), ("varname", varname), ("rulenr", rulenr) ])
    return \
       ' onmouseover="this.style.cursor=\'pointer\'; this.style.backgroundColor=\'#b7ced3\';" ' \
       ' onmouseout="this.style.cursor=\'auto\'; this.style.backgroundColor=\'#a7bec3\';" ' \
       ' onclick="location.href=\'%s\'"' % url


def mode_edit_ruleconds(phase):
    rulenr = int(html.var("rulenr"))
    varname = html.var("varname")
    
    if phase == "title":
        return _("Edit condition of rule %d") % rulenr

    elif phase == "buttons":
        html.context_button(_("Back"), 
                         make_link([("mode", "edit_ruleset"), ("varname", varname)]), "back")
        return

    ruleset = g_rulesets[varname]
    configured_rulesets = load_rulesets(g_folder)
    configured_ruleset = configured_rulesets[varname]
    rule = configured_ruleset[rulenr - 1]
    value, tag_specs, host_list, item_list = parse_rule(ruleset, rule)

    if phase == "action":
        if html.check_transaction():
            # re-construct rule from HTML variables
            value, tag_specs, host_list, item_list = parse_rule(ruleset, rule)
            tag_specs, host_list, item_list = get_rule_conditions(ruleset)
            rule = construct_rule(ruleset, value, tag_specs, host_list, item_list)
            configured_ruleset[rulenr - 1] = rule
            save_rulesets(g_folder, configured_rulesets)
            log_pending(None, "edit-rule", "Changed conditions of rule %d of %s" % 
                    (rulenr, varname))
        return "edit_ruleset"

    # There are several types of conditions:
    # - List of host tags. That list can be missing.
    # - List of host names. That list can also be ALL_HOSTS.
    # - List of items (service descriptions, etc.). This list
    #   is not present for all rules.

    html.begin_form("condition")
    html.write("<table class=form>")

    # Host tags
    html.write("<tr><td class=legend>" + _("Host tags") + "<br><i>")
    html.write(_("The rule will only be applied to hosts fullfulling all of "
                 "of the host tag conditions listed here, even if they appear "
                 "in the list of explicit host names."))
    
    html.write("</i></td>")
    html.write("<td class=content>")
    for id, title, tags in config.wato_host_tags:
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

        html.radiobutton("tag_" + id, "ignore", ignore, _("ignore"))
        html.write("&nbsp;")
        html.radiobutton("tag_" + id, "is",     not ignore and not negate, _("is"))
        html.write("&nbsp;")
        html.radiobutton("tag_" + id, "isnot",  not ignore and negate, _("is not"))
        html.write("&nbsp;")
        html.select("tagvalue_" + id, [t[0:2] for t in tags if t[0] != None], deflt=default_tag)
        html.write("<br>")
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
    for nr in range(config.wato_num_hostspecs):
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
    itemtype = ruleset["itemtype"]
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
        elif itemtype == "checkitem":
            html.write(_("Check items"))
        else:
            raise MKGeneralException("Invalid item type '%s'" % itemtype)
        html.write("</td><td class=content>")
        if itemtype == "service":
            checked = len(item_list) > 0 and item_list[0] != '""'
            div_id = "itemlist"
            html.checkbox("explicit_services", checked, onclick="wato_toggle_option(this, %r)" % div_id)
            html.write(" " + _("Specify explicit services"))
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
            html.write("</table></div>")
                
    # SAVE
    html.write("<tr><td class=buttons colspan=2>")
    html.button("_save", _("Save"))
    html.write("</td></tr>")

    html.write("</table>")
    html.hidden_fields()
    html.end_form()

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
            if nr > config.wato_num_hostspecs and not host:
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
    if itemtype == "service":
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

def mode_edit_rulevalue(phase):
    rulenr = int(html.var("rulenr"))
    varname = html.var("varname")

    if phase == "title":
        return _("Edit value of rule %d") % rulenr

    elif phase == "buttons":
        html.context_button(_("Back"), 
                         make_link([("mode", "edit_ruleset"), ("varname", varname)]), "back")
        return

    ruleset = g_rulesets[varname]
    configured_rulesets = load_rulesets(g_folder)
    configured_ruleset = configured_rulesets[varname]
    rule = configured_ruleset[rulenr - 1]

    if phase == "action":
        if html.check_transaction():
            value = get_edited_value(ruleset["valuespec"])
            configured_ruleset[rulenr - 1] = (value,) + rule[1:]
            save_rulesets(g_folder, configured_rulesets)
            log_pending(None, "edit-rule", "Changed value of rule %d of %s to %s" % 
                    (rulenr, varname, ruleset["valuespec"].value_to_text(value)))
            return "edit_ruleset"
        else:
            return

    value = rule[0]
    edit_value(ruleset["valuespec"], value)


def save_rulesets(folder, configured_rulesets):
    # TODO: folder berücksichtigen
    path = root_dir + "rules.mk" 
    out = file(path, "w") 
    out.write("# Written by WATO\n# encoding: utf-8\n\n")

    for varname, ruleset in g_rulesets.items():
        if ':' in varname:
            dictname, subkey = varname.split(':')
            out.write("\n%s.setdefault(%r, [])\n" % (dictname, subkey))
            out.write("%s[%r] += " % (dictname, subkey))
        else:
            out.write("\n%s += " % varname)
        out.write("%s\n" % pprint.pformat(configured_rulesets[varname]))


def load_rulesets(folder):
    # TODO: folder berücksichtigen
    path = root_dir + "rules.mk" 
    vars = {
        "ALL_HOSTS"      : ALL_HOSTS,
        "ALL_SERVICES"   : [ "" ],
        "NEGATE"         : NEGATE,
    }
    # Prepare empty rulesets so that rules.mk has something to 
    # append to

    for varname, ruleset in g_rulesets.items():
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
    for ruleset in g_rulesets.values():
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


g_rulesets = {}
g_ruleset_groups = {}
def register_rule(group, varname, valuespec = None, title = None, 
                  help = None, itemtype = None, match = "first"):
    ruleset = {
        "group"     : group, 
        "varname"   : varname, 
        "valuespec" : valuespec, 
        "itemtype"  : itemtype, # None, "service", "checktype" or "checkitem"
        "match"     : match,
        "title"     : title or valuespec.title(),
        "help"      : help or valuespec.help(),
        }
    g_ruleset_groups.setdefault(group, []).append(ruleset)
    g_rulesets[varname] = ruleset
 
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


    # Get all effective data of a host. Folder must be returned by get_folder()
    def get_host(self, folder, hostname):
        declare_host_tag_attributes()
        host = folder[".hosts"][hostname]
        eff = effective_attributes(host, folder)
        eff["name"] = hostname
        return eff

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
        return g_root_folder

    # sort list of folders or files by their title
    def sort_by_title(self, folders):
        def folder_cmp(f1, f2):
            return cmp(f1["title"].lower(), f2["title"].lower())
        folders.sort(cmp = folder_cmp)
        return folders

    # Create an URL to a certain WATO folder.
    def link_to_path(self, path):
        return "wato.py?folder=" + htmllib.urlencode(path)

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
    for hostname, host in folder[".hosts"]:
        hosts[hostname] = effective_attributes(host, folder)
        host["file"] = folder[".path"]

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
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Prepare plugin-datastructures and load WATO plugins                  |
#   +----------------------------------------------------------------------+


mode_functions = {
   "folder"         : mode_folder,
   "newfolder"      : lambda phase: mode_editfolder(phase, True),
   "editfolder"     : lambda phase: mode_editfolder(phase, False),
   "newhost"        : lambda phase: mode_edithost(phase, True),
   "edithost"       : lambda phase: mode_edithost(phase, False),
   "firstinventory" : lambda phase: mode_inventory(phase, True),
   "inventory"      : lambda phase: mode_inventory(phase, False),
   "search"         : mode_search,
   "bulkinventory"  : mode_bulk_inventory,
   "bulkedit"       : mode_bulk_edit,
   "bulkcleanup"    : mode_bulk_cleanup,
   "changelog"      : mode_changelog,
   "snapshot"       : mode_snapshot,
   "configuration"  : mode_configuration,
   "edit_configvar" : mode_edit_configvar,
   "rulesets"       : mode_rulesets,
   "edit_ruleset"   : mode_edit_ruleset,
   "edit_rulevalue" : mode_edit_rulevalue,
   "edit_ruleconds" : mode_edit_ruleconds,
}

extra_buttons = [
]

load_web_plugins("wato", globals())
