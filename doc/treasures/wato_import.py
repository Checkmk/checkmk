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

# Author :  Bastian Kuhn bk@mathias-kettner.de

# Author : Andreas Boesl ab@mathias-kettner.de
# Updated: Set correct host_tag group for given tags

import os, pprint, sys, subprocess
try:
    path = os.environ.pop('OMD_ROOT')
    pathlokal = "~/etc/check_mk/conf.d/wato/"
    pathlokal = os.path.expanduser(pathlokal)
    csv_file = open(sys.argv[1], 'r')
except:
    print """Run this script inside a OMD site
    Usage: ./wato_import.py csvfile.csv
    CSV Example:
    wato_foldername;hostname|tag1 tag2;host_alias;ipaddress|None"""
    sys.exit()

folders = {}
for line in csv_file:
    if line.startswith('#'):
        continue
    target_folder, name, alias, ipaddress = line.split(';')[:5]
    if target_folder:
        try:
            os.makedirs(pathlokal + target_folder)
        except os.error:
            pass
        folders.setdefault(target_folder, [])
        ipaddress = ipaddress.strip()
        if ipaddress == "None":
            ipaddress = False
        folders[target_folder].append((name, alias, ipaddress))
csv_file.close()

host_tags_info = {"wato_aux_tags": [], "wato_host_tags": []}
execfile("%s/../../multisite.d/wato/hosttags.mk" % pathlokal, globals(), host_tags_info)

host_tag_mapping = {}
aux_tag_mapping = {}
for tag_group, tag_descr, tag_choices in host_tags_info["wato_host_tags"]:
    for choice in tag_choices:
        host_tag_mapping[choice[0]] = tag_group  # tag name
        aux_tag_mapping[choice[0]] = choice[2]  # aux tags

for folder in folders:
    all_hosts = ""
    host_attributes = ""
    ips = ""
    for name, alias, ipaddress in folders[folder]:
        name_tokens = name.split("|")
        real_name = name_tokens[0]

        extra_infos = []
        # WATO Tag extra info
        host_aux_tags = set()
        if len(name_tokens) > 1:
            for tag in name_tokens[1].split():
                host_aux_tags |= set(aux_tag_mapping.get(tag, []))
                if tag not in host_tag_mapping:
                    print "Unknown host tag: %s" % tag
                else:
                    extra_infos.append("'tag_%s': '%s'" % (host_tag_mapping[tag], tag))

        extra_aux_tags = ""
        if host_aux_tags:
            extra_aux_tags = "|".join(host_aux_tags) + "|"
        all_hosts += "'%s|%swato|/' + FOLDER_PATH + '/',\n" % (name.replace(" ",
                                                                            "|"), extra_aux_tags)

        # WATO Alias extra info
        if alias:
            extra_infos.append("'alias' : u'%s'" % alias)

        if ipaddress:
            host_attributes += "'%s' : {'ipaddress' : '%s', %s},\n" % (real_name, ipaddress,
                                                                       ", ".join(extra_infos))
            ips += "'%s' : '%s',\n" % (real_name, ipaddress)
        else:
            host_attributes += "'%s' : {%s},\n" % (real_name, ", ".join(extra_infos))

    hosts_mk_file = open(pathlokal + folder + '/hosts.mk', 'w')
    hosts_mk_file.write('all_hosts += [\n')
    hosts_mk_file.write(all_hosts)
    hosts_mk_file.write(']\n\n')

    if len(ips) > 0:
        hosts_mk_file.write('ipaddresses.update({\n')
        hosts_mk_file.write(ips)
        hosts_mk_file.write('})\n\n')

    hosts_mk_file.write('host_attributes.update({\n')
    hosts_mk_file.write(host_attributes)
    hosts_mk_file.write('})\n\n')
    hosts_mk_file.close()

    wato_file = open(pathlokal + folder + '/.wato', 'w')
    wato_file.write("{'attributes': {}, 'num_hosts': %d, 'title': '%s'}\n" %
                    (len(folders[folder]), folder))
    wato_file.close()
