#!/usr/bin/python
# Send SMS via Mobilant # encoding: utf-8
#
# This notification script can be put below share/check_mk/notifications. It sends
# SMS via mobilant.com. Please add your personal configuration directly in this
# script. The target phone number is take from the contact's pager address.
# You can override this by specifying it as a parameter

import sys, os, urllib

key      = "8F37ksjf8kJ8k37f729Btlllsw8" # Enter your mobilant web key here!

# This does not need to be changed
to       = os.environ.get("NOTIFY_CONTACTPAGER")
fromname = "Check_MK"


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


url = "http://gw.mobilant.com/?" + urllib.urlencode([ 
   ( "key", key ),
   ( "to", to ),
   ( "message", message ),
   ( "route", "gold" ),
   ( "from", fromname )
])

exitcodes = {
    "10" : u"Empfängernummer nicht korrekt, Parameter: to",
    "20" : u"Absenderkennung nicht korrekt, Parameter: from",
    "30" : u"Nachrichtentext nicht korrekt, Parameter: message",
    "31" : u"Messagetyp nicht korrekt, Parameter: messagetype",
    "40" : u"SMS Route nicht korrekt, Parameter: route",
    "50" : u"Identifikation fehlgeschlagen, Parameter: key",
    "60" : u"nicht genügend Guthaben",
    "70" : u"Netz wird nicht abgedeckt, Parameter: route",
    "71" : u"Feature nicht möglich, Parameter: route",
    "80" : u"Übergabe an SMS-C, fehlgeschlagen",
    "100" : u"SMS wurde angenommen und, versendet",
}

try:
    handle = urllib.urlopen(url)
    response = handle.read().strip()
    if response == "100":
        sys.stdout.write("Successfully sent SMS to %s\n" % to)
    else:
        sys.stderr.write("Error sending SMS to %s: %s\n" % (to, exitcodes.get(response, "Invalid exit code %s" % response)))
        sys.stderr.write("URL was %s\n" % url)
except 1: # Exception, e:
    sys.stderr.write("Error sending SMS to %s. Exception: %s%s\n" % e)

