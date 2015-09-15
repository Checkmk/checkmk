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

def paint_wiki_notes(row):
    host = row["host_name"]
    svc = row.get("service_description")
    svc = svc.replace(':','')
    svc = svc.replace('/','')
    svc = svc.replace('\\','')
    svc = svc.replace(' ','_')
    svc = svc.lower()
    host = host.lower()
    filename = defaults.omd_root + '/var/dokuwiki/data/pages/docu/%s/%s.txt' % (host, svc)
    if not os.path.isfile(filename):
        filename = defaults.omd_root + '/var/dokuwiki/data/pages/docu/default/%s.txt' % (svc,)
   
    text = u"<a href='../wiki/doku.php?id=docu:default:%s'>Edit Default Instructions</a> - " %  svc
    text += u"<a href='../wiki/doku.php?id=docu:%s:%s'>Edit Host Instructions</a> <hr> " % (host, svc)

    try:
        import codecs
        text += codecs.open(filename, "r", "utf-8").read()
    except IOError:
        text += "No instructions found in " + filename
    
    return "", text + "<br /><br />"

multisite_painters["svc_wiki_notes"] = {
    "title"   : _("Instructions"),
    "short"   : _("Instr"),
    "columns" : [ "host_name", "service_description" ],
    "paint"   : paint_wiki_notes,
}
