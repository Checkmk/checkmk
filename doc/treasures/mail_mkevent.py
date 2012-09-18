#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#This script sends all mails from given mailbox
#to the mkeventd pipe of given OMD Installation
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
    out.write("<5>%s %s mail: %s" % (timestamp, host, msg))
    out.close()
    M.dele(i+1)
M.quit()     


