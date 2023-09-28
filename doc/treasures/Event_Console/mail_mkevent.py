#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
    for line_ in M.retr(i + 1)[1]:
        line = line_.decode("utf-8")
        if not found_host and line.split()[0] == "From:":
            host = line.split()[1].split("@")[1]
            host = host.replace(">", "")
            found_host = True
        msg += line
    out = open(deamon_path, "w")
    timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
    out.write("<5>{} {} mail: {}\n".format(timestamp, host, msg))
    out.close()
    M.dele(i + 1)
M.quit()
