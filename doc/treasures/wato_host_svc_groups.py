#!/usr/bin/python
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
