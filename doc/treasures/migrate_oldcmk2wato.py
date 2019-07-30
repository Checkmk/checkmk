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

from __future__ import print_function
import os, pprint, sys, operator


def usage():
    print("Usage: ./migrate_oldcmk2wato start\n")
    print("  This script tries to convert a WATO-less Check_MK configuration into WATO.")
    print("  It scans for *.mk files in the current folder and creates a respective WATO folder")
    print("  for each file found. The content of the file is splitted into a hosts.mk and rules.mk")
    print(
        "  As an alternative, you can configure where to put the content of the source *.mk files")
    print("  (have a look at the config section within the script)")
    print(
        "  After the conversion is finished, you can see the unconverted data in the file unconverted.info"
    )
    print("  \nNote: This script is still under development an not close to completion")


if len(sys.argv) != 2 or sys.argv[1] != "start":
    usage()
    sys.exit(0)

if not os.environ.get("OMD_SITE"):
    print("Please run this script as site user")
    sys.exit(0)

confd_folder = os.path.expanduser("~/etc/check_mk/conf.d")

#   .--config--------------------------------------------------------------.
#   |                     ____             __ _                            |
#   |                    / ___|___  _ __  / _(_) __ _                      |
#   |                   | |   / _ \| '_ \| |_| |/ _` |                     |
#   |                   | |__| (_) | | | |  _| | (_| |                     |
#   |                    \____\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+

# Target directory, created in ~/etc/check_mk/conf.d
wato_folder = "wato"

hosttags_file = os.path.expanduser("~/etc/check_mk/multisite.d/wato/hosttags.mk")
host_tags_info = {"wato_aux_tags": [], "wato_host_tags": []}

# For each unknown host tag a tag group with a single value is created (checkbox)
# Here you can configure its prefix. Example:
# Unknown tag  : mytag
# New tag group: autogen_mytag
taggroup_prefix = "autogen"

# Here you can configure the destination folder for specific files
# Per default each file is converted into a folder, with their respective hosts.mk and rules.mk
# In the following dictionary, you can rewrite the destination of
file_section_to_folder = {
    # Example: sourcefile: { "section": "destination_folder" }
    # "accesspoints.mk": { "logwatch_patterns": "/",  # logwatch patterns in accesspoints.mk are stored in the main folder
    #                      "hosts.mk":          "AP", # hosts.mk is stored in the folder AP
    #"*": {"ALL": "MIGRATION"} # Put everything (hosts/rules) into MIGRATION folder
}

#   .--Globals-------------------------------------------------------------.
#   |                    ____ _       _           _                        |
#   |                   / ___| | ___ | |__   __ _| |___                    |
#   |                  | |  _| |/ _ \| '_ \ / _` | / __|                   |
#   |                  | |_| | | (_) | |_) | (_| | \__ \                   |
#   |                   \____|_|\___/|_.__/ \__,_|_|___/                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# tag usage statistics
available_tags = {}

# configuration of all parsed files
all_file_vars = {}

# unknown host tags -> will be converted to tag group with checkbox
new_host_tags = set([])

# combined information of all config files
all_ipaddresses = {}
all_alias = []
all_parents = []
all_host_parents = {}

# result folders
result_files = {}

# unconverted settings sorted by file
partial_unconverted_data = ""  # partially unconverted sections
unconverted_data = ""  # complete  unconverted sections

# host tags stuff
if os.path.exists(hosttags_file):
    execfile(hosttags_file, globals(), host_tags_info)

map_tag_to_taggroup = {}
map_tag_to_auxtags = {}
known_aux_tags = set()
for tag_group, tag_descr, tag_choices in host_tags_info["wato_host_tags"]:
    for choice in tag_choices:
        map_tag_to_taggroup[choice[0]] = tag_group  # tag name
        map_tag_to_auxtags[choice[0]] = choice[2]  # aux tags
        known_aux_tags |= set(choice[2])  # list of known aux tags

# template for hosts.mk files
hosts_mk_template = """# Created by converter script
# encoding: utf-8

all_hosts += [
%(all_hosts_info)s
]

# Explicit IPv4 addresses
ipaddresses.update(
%(ip_address_info)s
)

# Settings for alias
extra_host_conf.setdefault('alias', []).extend(
%(alias_info)s
)

# Settings for parents
extra_host_conf.setdefault('parents', []).extend(
%(parent_info)s
)

# Host attributes (needed for WATO)
host_attributes.update(
%(host_attributes_info)s
)

"""

#   .--Functions-----------------------------------------------------------.
#   |             _____                 _   _                              |
#   |            |  ___|   _ _ __   ___| |_(_) ___  _ __  ___              |
#   |            | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|             |
#   |            |  _|| |_| | | | | (__| |_| | (_) | | | \__ \             |
#   |            |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def reinstate_orig_vars(content):
    for what in ["ALL_HOSTS", "ANY_USER", "ALL_SERVICES"]:
        content = content.replace("'$%s$'" % what, what)
        content = content.replace("$%s$" % what, what)
    return content


def get_target_folder(filename, what):
    filename = filename[:-3]  # strip .mk

    settings = file_section_to_folder.get(filename, file_section_to_folder.get("*"))
    if not settings:
        return filename

    return settings.get(what, settings.get("ALL", filename))


def add_to_folder(content, what, foldername):
    content = reinstate_orig_vars(content)
    result_files.setdefault(foldername, {"hosts.mk": "", "rules.mk": ""})
    result_files[foldername][what] += content + "\n\n\n"


def get_hosts_mk(file_vars):
    wato_config = {}
    tags_of_hosts = {}

    def add_wato_parameter(host, what, value):
        wato_config.setdefault(host, {})
        wato_config[host][what] = value

    # ALL HOSTS
    # Add wato tag and folder path to all_host
    def analyze_tags(line):
        hostname = line.split("|")[0]
        tags = line.split("|")[1:]
        tags_of_hosts[hostname] = tags
        for tag in tags:
            available_tags.setdefault(tag, 0)
            available_tags[tag] += 1

    all_hosts_info = []
    host_dict = {}
    for entry in file_vars["all_hosts"]:
        analyze_tags(entry)
        host_dict[entry.split("|")[0]] = None
        all_hosts_info.append("\"%s\"," % (entry + "|wato|/\" + FOLDER_PATH + \"/"))

    # Parents
    parent_list = []
    for hostname in host_dict.keys():
        if hostname in all_host_parents:
            add_wato_parameter(hostname, "parents", list(all_host_parents[hostname]))
            parent_list.append((",".join(all_host_parents[hostname]), [hostname]))

    # IP Addresses
    ip_dict = {}
    for hostname in host_dict.keys():
        if hostname in all_ipaddresses:
            ip_dict[hostname] = all_ipaddresses[hostname]
            add_wato_parameter(hostname, "ipaddress", all_ipaddresses[hostname])

    # Alias
    alias_info = []
    for entry in file_vars["extra_host_conf"].get("alias", []):
        for hostname in entry[1]:
            add_wato_parameter(hostname, "alias", entry[0])

    # Add wato config host tags (tricky...)
    for hostname, tags in tags_of_hosts.items():
        for tag in tags:
            if tag in known_aux_tags:
                # ignore, these are not shown in WATO
                continue


#   Here you can add some special cases, create extra tags for found tags, etc.
#            found_match = False
#            for entry in [ "snmp" ]:
#                if tag == entry:
#                    add_wato_parameter(hostname, "tag_agent", "snmp-tcp")
#                    add_wato_parameter(hostname, "tag_%s_snmp" % taggroup_prefix, entry)
#                    new_host_tags.add(entry)
#                    found_match = True
#
#            if found_match:
#                continue

            if tag in map_tag_to_taggroup:
                add_wato_parameter(hostname, map_tag_to_taggroup[tag], tag)
            else:
                add_wato_parameter(hostname, "tag_%s_%s" % (taggroup_prefix, tag), tag)
                new_host_tags.add(tag)

    content = hosts_mk_template % {
        "all_hosts_info": "    " + "\n    ".join(all_hosts_info),
        "ip_address_info": pprint.pformat(ip_dict),
        "alias_info": pprint.pformat(file_vars["extra_host_conf"].get("alias", [])),
        "parent_info": pprint.pformat(parent_list),
        "host_attributes_info": pprint.pformat(wato_config).replace("\"", "\\\"")
    }

    for what in ["all_hosts", "extra_host_conf"]:
        if what in file_vars:
            del file_vars[what]

    return content


def create_wato_folder(filename, file_vars):
    global unconverted_data

    # each of the following section removes the relevant data from file_vars
    # in the end we see the leftover, unconverted data

    # hosts.mk
    ###########
    add_to_folder(get_hosts_mk(file_vars), "hosts.mk", get_target_folder(filename, "hosts.mk"))

    # rules.mk
    ###########
    # Inventory services
    content = ""
    if file_vars.get("inventory_services", []):
        content += "inventory_services_rules = [\n"
        for entry in file_vars["inventory_services"]:
            if len(entry) == 2:
                hosts, values = entry
                tags = []
            elif len(entry) == 3:
                tags, hosts, values = entry
            content += "  ( {'services': %r}, %r, %s),\n" % (values, tags, hosts)
        content += "] + inventory_services_rules"

        add_to_folder(content, "rules.mk", get_target_folder(filename, "inventory_services"))

        del file_vars["inventory_services"]

    # Ignored services
    content = ""
    if file_vars.get("ignored_services", []):
        content += "ignored_services = "
        content += pprint.pformat(file_vars.get("ignored_services"))
        content += " + ignored_services"

        add_to_folder(content, "rules.mk", get_target_folder(filename, "ignored_services"))

        del file_vars["ignored_services"]

    # Fileinfo Groups
    content = ""
    if file_vars.get("fileinfo_groups", []):
        content += "fileinfo_groups = [\n"
        for entry in file_vars["fileinfo_groups"]:
            if len(entry) == 2:
                values, hosts = entry
                tags = []
            elif len(entry) == 3:
                values, tags, hosts = entry
            content += "  ( %r, %r, %r),\n" % (values, tags, hosts)
        content += "] + fileinfo_groups"

        add_to_folder(content, "rules.mk", get_target_folder(filename, "fileinfo_groups"))

        del file_vars["fileinfo_groups"]

    # Inventory processes
    content = ""
    if file_vars.get("inventory_processes"):
        content += "inventory_processes_rules = [\n"
        for entry in file_vars["inventory_processes"]:
            levels = entry[-4:]
            rest = entry[:-4]
            if len(rest) == 5:
                tags, hosts, name, match, user = rest
            elif len(rest) == 4:
                tags = []
                hosts, name, match, user = rest
            else:
                partial_unconverted_data += "%s: Unable to convert process rule %r" % (filename,
                                                                                       entry)

            content += "( {'default_params': {'levels': %r}, 'descr': %r, 'match': %r, 'user': %r}, %r, %r),\n" % \
                    (levels, name, match, user != "$ANY_USER$" and user or None, tags, hosts)

        content += "] + inventory_processes_rules"
        add_to_folder(content, "rules.mk", get_target_folder(filename, "inventory_processes"))

        del file_vars["inventory_processes"]

    # Logwatch Patterns (these values are getting re-sorted)
    if file_vars.get("logwatch_patterns"):
        content += "\nlogwatch_rules = [\n"
        for logfile, rules in file_vars["logwatch_patterns"].items():
            groups = {}
            # First run - determine groups
            for entry in rules:
                if len(entry) == 3:
                    hosts, state, pattern = entry
                    tags = []
                elif len(entry) == 4:
                    tags, hosts, state, pattern = entry
                group_name = (tuple(tags), tuple(hosts), state)
                groups.setdefault(group_name, [])
                groups[group_name].append((tags, hosts, state, pattern))
            # Second run - create useful rules
            for group_name, values in groups.items():
                tags, hosts, state, patterns = values[0]

                pattern_info = []
                for value in values:
                    pattern_info.append("(%r, %r, \"(auto generated)\")" % (state, value[3]))

                content += "( [%s], %s, %s, [\"%s\"]),\n" % (", ".join(pattern_info), tags, hosts,
                                                             logfile)

        content += "] + logwatch_rules"

        del file_vars["logwatch_patterns"]

        add_to_folder(content, "rules.mk", get_target_folder(filename, "logwatch_patterns"))

    # Log unconverted
    unconverted_data += "##########################\n"\
                   "## Unconverted data of file %s\n" % filename
    for key, value in file_vars.items():
        if value == [] or value == {} or key in ["ALL_HOSTS", "ALL_SERVICES", "ANY_USER"]:
            continue
        unconverted_data += "Parameter: %s\nValue:\n%s\n\n\n" % (key, pprint.pformat(value))


#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

# Parse files
print("Parsing files")
print("#############")
for filename in os.listdir("."):
    try:
        if not os.path.isfile(filename) or not filename.endswith(".mk"):
            continue

        print("Process file: %s" % filename)
        file_vars = {
            "all_hosts": [],  # converted
            "extra_host_conf": {
                "alias": []
            },  # converted
            "parents": [],  # converted
            "ignored_services": [],  # converted
            "fileinfo_groups": [],  # converted
            "ipaddresses": {},  # converted
            "legacy_checks": [],  # not converted - you need to create active checks
            "extra_nagios_conf": "",  # not possible
            "inventory_services": [],  # converted
            "inventory_processes": [],  # converted
            "scanparent_hosts": [],  # not converted
            "inventory_processes_rules": [],  # not converted
            "datasource_programs": [],  # not converted
            "clustered_services_of": {},  # not converted
            "logwatch_patterns": {},  # converted
            "check_parameters": [],  # not converted
            "checks": [],  # not converted
            "ALL_HOSTS": "$ALL_HOSTS$",  # Placeholder
            "ALL_SERVICES": "$ALL_SERVICES$",  # Placeholder
            "ANY_USER": "$ANY_USER$",  # Placeholder
        }
        execfile(filename, globals(), file_vars)
        all_file_vars[filename] = file_vars
    except Exception as e:
        print("Error parsing file %s: %s" % (filename, e))
print("")

# Pre-process files, deterime global IP addresses and parent relationships
for filename, file_vars in all_file_vars.items():
    all_ipaddresses.update(file_vars.get("ipaddresses", {}))
    all_alias.extend(file_vars.get("extra_host_conf", {}).get("alias", []))

    all_parents.extend(file_vars.get("extra_host_conf", {}).get("parents", []))
    for entry in file_vars.get("parents", []):
        if len(entry) == 3:
            parents, tags, hosts = entry
            partial_unconverted_data += "%s: Unable to convert parent configuration: %s" % (
                filename, pprint.pformat(entry))
        elif len(entry) == 2:
            parents, hosts = entry
            parent_tokens = parents.split(",")
            for host in hosts:
                all_host_parents.setdefault(host, set())
                all_host_parents[host] |= set(parent_tokens)
    all_parents.extend(file_vars.get("parents", []))

# Process files
for filename, file_vars in all_file_vars.items():
    create_wato_folder(filename, file_vars)

# Debug, shows overall tag usage
print("Tag usage statistics")
print("####################")
tag_counts = sorted(available_tags.items(), key=operator.itemgetter(1), reverse=True)
for key, value in tag_counts:
    print("%-20s %s" % (key, value))
print("")

# Create hosttags.mk file
print("hosttags.mk")
print("###########")

print("Creating hosttags.mk in %s (inspect and copy this to ~/etc/check_mk/multisite.d/wato)" %
      os.path.expanduser("~"))
tag_template = "('%(taggroup_prefix)s_%(tag)s', u'%(tag)s', [('%(tag)s', u'%(tag)s (auto generated)', [])]),"
extra_host_tags = []
for tag in new_host_tags:
    extra_host_tags.append(tag_template % {"tag": tag, "taggroup_prefix": taggroup_prefix})

hosttags_content = """# Created by converter script
# encoding: utf-8

wato_host_tags += \
%(wato_host_tags)s

wato_aux_tags += \
%(wato_aux_tags)s

wato_host_tags += [\n\
%(extra_host_tags)s
]
""" % {
    "wato_host_tags": pprint.pformat(host_tags_info["wato_host_tags"]),
    "wato_aux_tags": pprint.pformat(host_tags_info["wato_aux_tags"]),
    "extra_host_tags": "\n".join(extra_host_tags)
}
file(os.path.expanduser("~/hosttags.mk"), "w").write(hosttags_content)
print("")

# Write all configuration (hosts.mk/rules.mk) files
print("Writing configuration files")
print("###########################")
for dirname, content in result_files.items():
    filepath = "%s/%s/%s" % (confd_folder, wato_folder, dirname)
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    for filename, text in content.items():
        print("Writing %s... %s" % (filepath, filename))
        file("%s/%s" % (filepath, filename), "w").write(text)
    print("")

if unconverted_data or partial_unconverted_data:
    print("""##################################################
# Unconverted data remains (see unconverted.info)#
##################################################""")

    # Write all unconverted data into the file unconverted.info
    file("unconverted.info", "w").write(unconverted_data + """
    #############################
    #Partially unconverted data:#
    #############################

    %s
    """ % partial_unconverted_data)
