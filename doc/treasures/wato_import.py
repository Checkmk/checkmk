#!/usr/bin/python
#Author: Bastian Kuhn bk@mathias-kettner.de
import os
import sys

try:
    datei = open(sys.argv[1],'r') 
except IndexError:
    print """Place this file in your Wato directory
    Usage: ./wato_import.py csvfile.csv
    CSV Example:
    wato_foldername;hostname;host_alias;oneor|moreHostTags"""
    sys.exit()

folders = {}
for line in datei:
    ordner, name, alias, tag = line.split(';')
    if ordner:
        try:
            os.mkdir(ordner)
        except os.error:
            folder_exsits = True
        folders.setdefault(ordner,[])

        folders[ordner].append((name,alias,tag.strip()))
datei.close()


for folder in folders:
    all_hosts = "" 
    host_attributes = "" 
    for name, alias, tag in folders[folder]:
        all_hosts += "'%s|%s',\n" % (name, tag)
        host_attributes += "'%s' : {'alias' : u'%s' },\n" % (name, alias)

    ziel = open(folder + '/hosts.mk','w') 
    ziel.write('all_hosts += [')
    ziel.write(all_hosts)
    ziel.write(']\n\n')
    ziel.write('host_attributes.update({')
    ziel.write(host_attributes)
    ziel.write('})')
    ziel.close()
