#!/usr/bin/python

import sys, time, urllib
from xml.dom import minidom
now = int(time.time())
start = now - 24 * 60 * 60 
end =  now
dpu =  1

url = "http://localhost/recoveryconsole/bpl/syncstatus.php?type=replicate&arguments=start:%s,end:%s&sid=%s&auth=1:" % ( start, end, dpu )
xml = urllib.urlopen(url)

print "<<<unitrends_replication:sep(124)>>>"
dom = minidom.parse(xml)
for item in dom.getElementsByTagName('SecureSyncStatus'):
    application = item.getElementsByTagName('Application')
    if application:
        application = application[0].attributes['Name'].value
    else:
        application = "N/A"
    result = item.getElementsByTagName('Result')[0].firstChild.data
    completed = item.getElementsByTagName('Complete')[0].firstChild.data
    targetname = item.getElementsByTagName('TargetName')[0].firstChild.data
    instancename = item.getElementsByTagName('InstanceName')[0].firstChild.data
    print "%s|%s|%s|%s|%s" % (application, result, completed, targetname, instancename)
