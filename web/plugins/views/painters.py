
##################################################################################
# Painters
##################################################################################
def nagios_host_url(sitename, host):
    nagurl = check_mk.site(sitename)["nagios_cgi_url"]
    return nagurl + "/status.cgi?host=" + htmllib.urlencode(host)

def nagios_service_url(sitename, host, svc):
    nagurl = check_mk.site(sitename)["nagios_cgi_url"]
    return nagurl + ( "/extinfo.cgi?type=2&host=%s&service=%s" % (htmllib.urlencode(host), htmllib.urlencode(svc)))

def paint_age(timestamp, has_been_checked):
    if not has_been_checked:
	return "age", "-"
	   
    age = time.time() - timestamp
    if age < 60 * 10:
	age_class = "agerecent"
    else:
	age_class = "age"
    return age_class, html.age_text(age)

def paint_site_icon(row):
    if row["site"] and check_mk.multiadmin_use_siteicons:
	return None, "<img class=siteicon src=\"icons/site-%s-24.png\">" % row["site"]
    else:
	return None, ""
	

multisite_painters["sitename_plain"] = {
    "title" : "Site id",
    "short" : "Site",
    "table" : None,
    "columns" : ["site"],
    "paint" : lambda row: (None, row["site"])
}

multisite_painters["sitealias"] = {
    "title" : "Site alias",
    "table" : None,
    "columns" : ["site"],
    "paint" : lambda row: (None, check_mk.site(row["site"])["alias"])
}

def paint_host_black(row):
    state = row["host_state"]
    if state == 0:
	style = "up"
    else:
	style = "down"
    return "host", "<b class=%s><a href=\"%s\">%s</a></b>" % \
	(style, nagios_host_url(row["site"], row["host_name"]), row["host_name"])

multisite_painters["host_black"] = {
    "title" : "Hostname, red background if down or unreachable",
    "short" : "Host",
    "columns" : ["site","host_name"],
    "table" : "hosts",
    "paint" : paint_host_black,
}

multisite_painters["host_with_state"] = {
    "title" : "Hostname colored with state",
    "short" : "Host",
    "columns" : ["site","host_name"],
    "table" : "hosts",
    "paint" : lambda row: ("hstate%d" % row["host_state"], row["host_name"])
}

multisite_painters["host"] = {
    "title" : "Hostname",
    "short" : "Host",
    "table" : "hosts",
    "columns" : ["host_name"],
    "paint" : lambda row: (None, row["host_name"])
}

multisite_painters["alias"] = {
    "title" : "Host alias",
    "short" : "Alias",
    "table" : "hosts",
    "columns" : ["host_alias"],
    "paint" : lambda row: (None, row["host_alias"])
}

def paint_service_state_short(row):
    if row["service_has_been_checked"] == 1:
	state = row["service_state"]
	name = nagios_short_state_names[row["service_state"]]
    else:
	state = "p"
	name = "PEND"
    return "state%s" % state, name

def paint_host_state_short(row):
# return None, str(row)
    if row["host_has_been_checked"] == 1:
	state = row["host_state"]
	name = nagios_short_host_state_names[row["host_state"]]
    else:
	state = "p"
	name = "PEND"
    return "hstate%s" % state, name

multisite_painters["service_state"] = {
    "title" : "Service state",
    "short" : "state",
    "table" : "services",
    "columns" : ["service_has_been_checked","service_state"],
    "paint" : paint_service_state_short
}

multisite_painters["host_state"] = {
    "title" : "Host state",
    "short" : "state",
    "table" : "hosts",
    "columns" : ["host_has_been_checked","host_state"],
    "paint" : paint_host_state_short
}

multisite_painters["site_icon"] = {
    "title" : "Icon showing the site",
    "short" : "",
    "table" : None,
    "columns" : ["site"],
    "paint" : paint_site_icon
}

multisite_painters["svc_plugin_output"] = {
    "title" : "Output of check plugin",
    "short" : "Plugin output",
    "table" : "services",
    "columns" : ["service_plugin_output"],
    "paint" : lambda row: (None, row["service_plugin_output"])
}
    
multisite_painters["service_description"] = {
    "title" : "Service description",
    "short" : "Service",
    "table" : "services",
    "columns" : ["service_description"],
    "paint" : lambda row: (None, row["service_description"])
}

multisite_painters["svc_state_age"] = {
    "title" : "The age of the current service state",
    "short" : "age",
    "table" : "services",
    "columns" : [ "service_has_been_checked", "service_last_state_change" ],
    "paint" : lambda row: paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1)
}

def paint_svc_count(id, count):
    if count > 0:
	return "state%s" % id, str(count)
    else:
	return "statex", "0"

multisite_painters["num_services"] = {
    "title"   : "Number of services",
    "short"   : "",
    "table"   : "hosts",
    "columns" : [ "host_num_services" ],
    "paint"   : lambda row: (None, str(row["host_num_services"])),
}

multisite_painters["num_services_ok"] = {
    "title"   : "Number of services in state OK",
    "short"   : "O",
    "table"   : "hosts",
    "columns" : [ "host_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["host_num_services_ok"])
}

multisite_painters["num_services_warn"] = {
    "title"   : "Number of services in state WARN",
    "short"   : "W",
    "table"   : "hosts",
    "columns" : [ "host_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["host_num_services_warn"])
}

multisite_painters["num_services_crit"] = {
    "title"   : "Number of services in state CRIT",
    "short"   : "C",
    "table"   : "hosts",
    "columns" : [ "host_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["host_num_services_crit"])
}

multisite_painters["num_services_unknown"] = {
    "title"   : "Number of services in state UNKNOWN",
    "short"   : "U",
    "table"   : "hosts",
    "columns" : [ "host_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["host_num_services_unknown"])
}

multisite_painters["num_services_pending"] = {
    "title"   : "Number of pending services",
    "short"   : "P",
    "table"   : "hosts",
    "columns" : [ "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["host_num_services_pending"])
}

# Intelligent Links to PNP4Nagios 0.6.X

def paint_pnp_service_link(row):
    # On our local site, we look for an existing XML file or PNP.
    sitename = row["site"]
    site = html.site_status[sitename]["site"]
    host = row["host_name"]
    svc = row["service_description"]
    url = site["pnp_prefix"] + ("?host=%s&srv=%s" % (htmllib.urlencode(host), htmllib.urlencode(svc)))
    a = "<a href=\"%s\">PNP</a>" % url

    if check_mk.site_is_local(sitename):
	# Where is our RRD?
	basedir = check_mk.rrd_path + "/" + host
	xmlpath = basedir + "/" + svc.replace("/", "_").replace(" ", "_") + ".xml"
	if os.path.exists(xmlpath):
	    return "", a
	else:
	    return "", ""
    
    # Darn. Remote site. We cannot check for a file but rather use
    # (Lars' idea) the perfdata field
    elif row["service_perf_data"]:
	return "", a
    else:
	return "", ""
        

multisite_painters["link_to_pnp_service"] = {
    "title"   : "Link to PNP4Nagios",
    "short"   : "PNP",
    "table"   : "services",
    "columns" : [ "site", "host_name", "service_description", "service_perf_data"],
    "paint"   : paint_pnp_service_link,
}


