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

# This script sends all mails from given mailbox
# to the mkeventd pipe of given OMD Installation
#
# Bastian Kuhn, bk@mathias-kettner.de
import poplib
import time

pop3_server = "localhost"
mail_user = "USER"
mail_pass = "mail"
site_name = "SITE"
deamon_path = "/omd/sites/%s/tmp/run/mkeventd/events" % site_name


M = poplib.POP3(pop3_server)
M.user(mail_user)
M.pass_(mail_pass)
numMessages = len(M.list()[1])
for i in range(numMessages):
    host = "not_found"
    msg = ""
    found_host = False
    for line in M.retr(i+1)[1]:
        if found_host == False and line.split()[0] == "From:":
            host = line.split()[1].split('@')[1]
            host = host.replace('>','')
            found_host = True
        msg += line
    out = open(deamon_path, "w")
    timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
    out.write("<5>%s %s mail: %s\n" % (timestamp, host, msg))
    out.close()
    M.dele(i+1)
M.quit()     

