
##################################################################################
# Painters
##################################################################################
def nagios_host_url(sitename, host):
    nagurl = check_mk.site(sitename)["nagios_cgi_url"]
    return nagurl + "/status.cgi?host=" + htmllib.urlencode(host)

def nagios_service_url(sitename, host, svc):
    nagurl = check_mk.site(sitename)["nagios_cgi_url"]
    return nagurl + ( "/extinfo.cgi?type=2&host=%s&service=%s" % (htmllib.urlencode(host), htmllib.urlencode(svc)))

def paint_plain(text):
    return "<td>%s</td>" % text

def paint_age(timestamp, has_been_checked):
    if not has_been_checked:
	return "<td class=age>-</td>"
	   
    age = time.time() - timestamp
    if age < 60 * 10:
	age_class = "agerecent"
    else:
	age_class = "age"
    return "<td class=%s>%s</td>\n" % (age_class, html.age_text(age))

def paint_site_icon(row):
    if row["site"] and check_mk.multiadmin_use_siteicons:
	return "<td><img class=siteicon src=\"icons/site-%s-24.png\"> " % row["site"]
    else:
	return "<td></td>"
	

multisite_painters["sitename_plain"] = {
    "title" : "The id of the site",
    "table" : None,
    "columns" : ["site"],
    "paint" : lambda row: "<td>%s</td>" % row["site"],
}

def paint_host_black(row):
    state = row["host_state"]
    if state == 0:
	style = "up"
    else:
	style = "down"
    return "<td class=host><b class=%s><a href=\"%s\">%s</a></b></td>" % \
	(style, nagios_host_url(row["site"], row["host_name"]), row["host_name"])

multisite_painters["host_black"] = {
    "title" : "Hostname, red background if down or unreachable",
    "columns" : ["site","host_name"],
    "table" : "hosts",
    "paint" : paint_host_black,
}

multisite_painters["host_with_state"] = {
    "title" : "Hostname colored with state",
    "columns" : ["site","host_name"],
    "table" : "hosts",
    "paint" : lambda row: "<td class=hstate%d><a href=\"%s\">%s</a></td>" % \
	(row["state"], nagios_host_url(row["site"], row["host_name"]), row["host_name"]),
}

multisite_painters["host"] = {
    "title" : "Hostname with link to Nagios",
    "table" : "hosts",
    "columns" : ["host_name"],
    "paint" : lambda row: "<td><a href=\"%s\">%s</a></td>" % (nagios_host_url(row["site"], row["host_name"]), row["host_name"])
}


def paint_service_state_short(row):
    if row["service_has_been_checked"] == 1:
	state = row["service_state"]
	name = nagios_short_state_names[row["service_state"]]
    else:
	state = "p"
	name = "PEND"
    return "<td style=\"width: 4ex;\" class=state%s>%s</td>" % (state, name)

multisite_painters["service_state"] = {
    "title" : "The service state, colored and short (4 letters)",
    "table" : "services",
    "columns" : ["service_has_been_checked","service_state"],
    "paint" : paint_service_state_short
}

multisite_painters["site_icon"] = {
    "title" : "Icon showing the site",
    "table" : None,
    "columns" : ["site"],
    "paint" : paint_site_icon
}

multisite_painters["svc_plugin_output"] = {
    "title" : "Output of check plugin",
    "table" : "services",
    "columns" : ["service_plugin_output"],
    "paint" : lambda row: paint_plain(row["service_plugin_output"])
}
    
multisite_painters["service_description"] = {
    "title" : "Service description",
    "table" : "services",
    "columns" : ["service_description"],
    "paint" : lambda row: "<td><a href=\"%s\">%s</a></td>" % \
	(nagios_service_url(row["site"], row["host_name"], row["service_description"]), row["service_description"])
}

multisite_painters["svc_state_age"] = {
    "title" : "The age of the current service state",
    "table" : "services",
    "columns" : [ "service_has_been_checked", "service_last_state_change" ],
    "paint" : lambda row: paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1)
}
