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
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

#Author: Bastian Kuhn bk@mathias-kettner.de

import os
import sys
try:
    path = os.environ.pop('OMD_ROOT')
    pathlokal = "~/etc/check_mk/conf.d/wato/"
    pathlokal = os.path.expanduser(pathlokal)
    datei = open(sys.argv[1],'r')
except:
    print """Run this script inside a OMD site
    Usage: ./wato_import.py csvfile.csv
    CSV Example:
    wato_foldername,hostname|tags,host_alias,(ipaddress|None)"""
    sys.exit()

folders = {}
for line in datei:
    if line.startswith('#') or len(line.split(',')) < 4:
        continue
    ordner, name, alias, ipaddress = line.split(',')[:4]
    if ordner:
        try:
            os.makedirs(pathlokal+ordner)
        except os.error:
            pass
        folders.setdefault(ordner,[])
        ipaddress = ipaddress.strip()
        if ipaddress == "None":
            ipaddress = False
        folders[ordner].append((name,alias,ipaddress))
datei.close()

for folder in folders:
    all_hosts = ""
    host_attributes = ""
    ips = ""
    for name, alias, ipaddress in folders[folder]:
	realname = name.split("|")[0]
        all_hosts += "'%s',\n" % (name)
        if ipaddress:
            host_attributes += "'%s' : {'alias' : u'%s', 'ipaddress' : '%s' },\n" % (realname, alias, ipaddress)
            ips += "'%s' : '%s'," % ( realname, ipaddress )
        else:
            host_attributes += "'%s' : {'alias' : u'%s' },\n" % (realname, alias)


    ziel = open(pathlokal + folder + '/hosts.mk','w')
    ziel.write('all_hosts += [')
    ziel.write(all_hosts)
    ziel.write(']\n\n')
    ziel.write('host_attributes.update({')
    ziel.write(host_attributes)
    ziel.write('})\n\n')
    if len(ips) > 0:
        ziel.write('ipaddresses.update({')
        ziel.write(ips)
        ziel.write('})\n\n')
    ziel.close()
