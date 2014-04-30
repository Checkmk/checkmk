#!/usr/bin/python
# Send SMS via MultiTech SMS-Gateway # encoding: utf-8
#
# This notification script can be put below share/check_mk/notifications. It sends
# SMS via a MultiTech SMS-Gateway. Please add your personal configuration directly in this
# script. The target phone number is take from the contact's pager address.
# You can override this by specifying it as a parameter
import sys, os, urllib

# This does not need to be changed
to       = os.environ.get("NOTIFY_CONTACTPAGER")
fromname = "Check_MK"
user     = "nagios"
passwd   = "test123"
url      = "http://isms.example.com/sendmsg?"


if len(sys.argv) > 1:
    to = sys.argv[1]

if not to:
    sys.stderr.write("NOTIFY_CONTACTPAGER is not set.\n")
    sys.exit(1)


max_len = 160
message = os.environ['NOTIFY_HOSTNAME'] + " "

if os.environ['NOTIFY_WHAT'] == 'SERVICE':
    message += os.environ['NOTIFY_SERVICESTATE'][:2] + " "
    avail_len = max_len - len(message)
    message += os.environ['NOTIFY_SERVICEDESC'][:avail_len] + " "
    avail_len = max_len - len(message)
    message += os.environ['NOTIFY_SERVICEOUTPUT'][:avail_len]

else:
    message += "is " + os.environ['NOTIFY_HOSTSTATE']

# constructing a url like
# http://isms.example.com/sendmsg?user=nagios&passwd=test123&cat=1&to=017012345678&text=sample' 
url += urllib.urlencode([ 
   ( "user", user ),
   ( "passwd", passwd ),
   ( "cat", "1" ),
   ( "to", to ),
   ( "text", message )
])


try:
    handle = urllib.urlopen(url)
    response = handle.read().strip()
    print response
    if response.startswith("ID:"):
        sys.stdout.write("Successfully sent SMS to %s\n" % to)
    else:
        sys.stderr.write("Error sending SMS to %s: %s\n" % (to, response))
        sys.stderr.write("URL was %s\n" % url)
except Exception, e:
    sys.stderr.write("Error sending SMS to %s. Exception: %s%s\n" % e)

