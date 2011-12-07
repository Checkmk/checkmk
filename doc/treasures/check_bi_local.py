#!/usr/bin/python

# Example for creating real Nagios checks from BI
# aggregations. You need to create a view with
# the name aggr_service with the two columns
# Aggr State and Aggr Name.

import os

url = 'http://omdadmin:omd@localhost/bi/check_mk/view.py?view_name=aggr_webservice&output_format=python'

data = eval(os.popen("curl --silent '%s'" % url).read())

states = {
  "OK"      : 0,
  "WARN"    : 1,
  "CRIT"    : 2,
  "UNKNOWN" : 3,
}

for state, name in data[1:]:
    state_nr = states.get(state, -1)
    descr = "BI_Aggr_" + name.replace(" ", "_")
    if state_nr != -1:
        print "%d %s - %s" % (state_nr, descr, state)

