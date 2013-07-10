#!/usr/bin/python
#Send notifications remote to mkeventd
#Including Service Level

mkevent_host = ''
mkevent_port = 514
application  = "notify"

import time, socket, os
host = os.environ['NOTIFY_HOSTNAME'] 
#0       Emergency
#1       Alert
#2       Critical
#3       Error
#4       Warning
#5       Notice
#6       Informational
#7       Debug

def state_to_prio(state):
    state = int(state)
    if state == 0:
        return 5 
    elif state == 1:
        return 4
    elif state == 2:
        return 2
    elif state == 3:
        return 7


if os.environ['NOTIFY_WHAT'] == 'SERVICE':
    sl = os.environ.get('NOTIFY_SVC_SL', 0)
    prio = state_to_prio(os.environ['NOTIFY_SERVICESTATEID'])
    message = "%s|%s|%s" % \
    ( sl, os.environ['NOTIFY_SERVICEDESC'], os.environ['NOTIFY_SERVICEOUTPUT'] )
else:
    sl = os.environ.get('NOTIFY_HOST_SL', 0)
    prio = state_to_prio(os.environ['NOTIFY_HOSTSTATEID'])
    message = "%s|HOSTSTATE|%s" % (sl,  os.environ['NOTIFY_HOSTOUTPUT'] ) 

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((mkevent_host, mkevent_port))

timestamp = time.strftime("%b %d %H:%M:%S", time.localtime(time.time()))
sock.send("<%s>%s %s %s: %s\n" % (prio, timestamp, host, application,  message))
sock.close()
