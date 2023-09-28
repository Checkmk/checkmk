#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author Bastian Kuhn <bk@mathias-kettner.de>
# Converts a File with host- and/or service groups definitions
# into a dict. The output can be used to paste it into the wato/rules.mk
# The input format must be :
# define hostgroup{
#    ....
#    hostgroup_name  hostgroup_name
#    alias   alias
#    ....
# }
# Means alias has to follow the name

import sys

path = sys.argv[1]

alias = False
next_ = ""

servicegroups = {}
hostgroups = {}
for line in open(path).readlines():
    line = line.strip()
    if line != "" and line[0] != "#" and line != "}" and not line.startswith("define"):
        try:
            attr, value = line.split(" ", 1)
            attr = attr.strip()
            value = value.strip()
            if attr == "hostgroup_name":
                next_ = "hostgroup"
                name = value
            elif attr == "servicegroup_name":
                next_ = "servicegroup"
                name = value

            if alias:
                if next_ == "hostgroup":
                    hostgroups[name] = value
                elif next_ == "servicegroup":
                    servicegroups[name] = value
                alias = False
            alias = True
        except Exception:
            pass

print("Hostgroups:")
print(hostgroups)
print("")
print("Service groups")
print(servicegroups)
