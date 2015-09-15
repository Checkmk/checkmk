#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
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
