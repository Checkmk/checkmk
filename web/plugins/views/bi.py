import bi

multisite_datasources["bi_aggregations"] = {
    "title"       : "BI Aggregations",
    "table"       : bi.host_table, 
    "infos"       : [ "host", "aggr" ],
    "keys"        : [],
}

def paint_aggr_state_short(row):
    if True: # row["service_has_been_checked"] == 1:
        state = row["aggr_state"]
        name = nagios_short_state_names[state]
    else:
        state = "p"
        name = "PEND"
    return "state svcstate state%s" % state, name

multisite_painters["aggr_state"] = {
    "title"   : "Aggregated state",
    "short"   : "State",
    "columns" : [ "aggr_state" ],
    "paint"   : paint_aggr_state_short
}

multisite_painters["aggr_name"] = {
    "title"   : "Aggregation name",
    "short"   : "Aggregate",
    "columns" : [ "aggr_name" ],
    "paint"   : lambda row: ("", row["aggr_name"])
}

multisite_painters["aggr_output"] = {
    "title"   : "Aggregation status output",
    "short"   : "Output",
    "columns" : [ "aggr_output" ],
    "paint"   : lambda row: ("", row["aggr_output"])
}

def paint_aggregated_services(row):
    h = "<table>"
    for de, st, pd, out in row["aggr_atoms"]:
        svclink = '<a href="view.py?view_name=service&site=%s&host=%s&service=%s">%s</a>' % \
                  (row['site'], row['host_name'], htmllib.urlencode(de), de)
        h += '<tr><td class="state svcstate state%s">%s</td><td>%s</td><td>%s</td></tr>' %  \
             (st, nagios_short_state_names[st], svclink, out)
    h += '</table>'
    return "aggr svcdetail", h 

multisite_painters["aggr_services"] = {
    "title"   : "Aggregated services in detail",
    "short"   : "Services",
    "columns" : [ "aggr_atoms" ],
    "paint"   : paint_aggregated_services,
}

