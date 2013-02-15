#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# Author Bastian Kuhn <bk@mathias-kettner.de>
# Converts a File with host- and/or service groups definitions
# into a dict. The output can be used to paste it into the wato/rules.mk 
# The input format must be :
#define hostgroup{
#    ....
#    hostgroup_name  hostgroup_name
#    alias   alias
#    ....
#}
# Means alias has to follow the name

import sys
path = sys.argv[1]

alias = False
next = False

servicegroups = {}
hostgroups = {}
for line in file(path).readlines():
     line = line.strip()
     if line != "" and line[0] != '#' and line != '}' and not line.startswith('define'):
         try:
             attr, value =  line.split(" ", 1)
             attr = attr.strip()
             value = value.strip()
	     if attr == "hostgroup_name":
	         next = "hostgroup"
	         name = value
	     elif attr == "servicegroup_name":
	         next = "servicegroup"
	         name = value

             if alias == True:
	        if next == "hostgroup":
	            hostgroups[name] = value
	        elif next == "servicegroup":
	            servicegroups[name] = value
	        alias = False
	     alias = True
         except:
            pass

print "Hostgroups:"
print hostgroups
print ""
print "Service groups"
print servicegroups
