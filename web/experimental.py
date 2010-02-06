import check_mk, livestatus, htmllib, time
from lib import *

multisite_datasources = {}
multisite_filters     = {}
multisite_layouts     = {}
multisite_painters    = {}

def page(h):
    global html
    html = h

    html.header("Experimental")
    if check_mk.multiadmin_restrict and \
	html.req.user not in check_mk.multiadmin_unrestricted_users:
	    auth_user = html.req.user
    else:
	auth_user = None

    connect_to_livestatus(html, auth_user)

    # show_page("hosts", "ungrouped_list", [ "sitename_plain", "host_with_state" ])
    show_page("services",  # data source
	      [ "host", "service", "svcstate" ], # filters
	      "grouped_list", # layout
	      [ "site", "host_name" ], # grouping columns
	      [ "site_icon", "host_black" ], # group painters
	      [ "service_state", "service_description", "state_age", "plugin_output" ])

    html.footer()

def show_page(datasourcename, filternames, layoutname, group_columns, group_painternames, painternames):
    datasource = multisite_datasources[datasourcename]
    filters = [ multisite_filters[fn] for fn in filternames ]
    filterheaders = "".join(f.filter(datasource["table"]) for f in filters)
    html.write("<pre>%s</pre>" % filterheaders)
    data = query_data(datasource, filterheaders)
    painters = [ multisite_painters[n] for n in painternames ]
    layout = multisite_layouts[layoutname]
    group_painters = [ multisite_painters[n] for n in group_painternames ]
    layout["render"](data, filters, group_columns, group_painters, painters)

def show_filter_form(filters):
    html.begin_form("filter")
    html.write("<table class=form id=filter>\n")
    for f in filters:
	html.write("<tr><td class=legend>%s</td>" % f.title)
	html.write("<td class=content>")
	f.display()
	html.write("</td></tr>\n")
    html.write("<tr><td class=legend></td><td class=content>")
    html.button("search", "Search", "submit")
    html.write("</td></tr>\n")
    html.write("</table>\n")
    html.end_form()

def query_data(datasource, add_headers):
    tablename = datasource["table"]
    query = "GET %s\n" % tablename
    columns = datasource["columns"]
    query += "Columns: %s\n" % " ".join(datasource["columns"])
    query += add_headers
    live.set_prepend_site(True)
    data = live.query(query)
    columns_with_site = ["site"] + columns
    assoc = [ dict(zip(columns_with_site, row)) for row in data ]
    live.set_prepend_site(False)

    # If you understand this code than you are really smart >;-/
    def rowfunction(painter, row):
	paintertable = painter.get("table")
	if paintertable in [None, tablename]:
	    return lambda x: row[x]
	else:
	    return lambda x: row.get(paintertable[:-1] + "_" + x, row.get(x))

    return (["site"] + columns, rowfunction, assoc)
    
     
def connect_to_livestatus(html, auth_user = None):
    global site_status, live
    site_status = {}
    # If there is only one site (non-multisite), than
    # user cannot enable/disable. 
    if check_mk.is_multisite():
	enabled_sites = {}
	for sitename, site in check_mk.sites().items():
	    varname = "siteoff_" + sitename
	    if not html.var(varname) == "on":
		enabled_sites[sitename] = site
	global live
	live = livestatus.MultiSiteConnection(enabled_sites)
	live.set_prepend_site(True)
        for site, v1, v2 in live.query("GET status\nColumns: livestatus_version program_version"):
	    site_status[site] = { "livestatus_version": v1, "program_version" : v2 }
	live.set_prepend_site(False)
    else:
	live = livestatus.SingleSiteConnection(check_mk.livestatus_unix_socket)

    if auth_user:
	live.addHeader("AuthUser: %s" % auth_user)

##################################################################################
# Data sources
##################################################################################

multisite_datasources["hosts"] = {
    "table"   : "hosts",
    "columns" : ["name", "state"],
}

multisite_datasources["services"] = {
    "table"   : "services",
    "columns" : ["description", "plugin_output", "state", "has_been_checked", 
                 "host_name", "host_state", "last_state_change" ],
}

##################################################################################
# Filters
##################################################################################

def declare_filter(f):
    multisite_filters[f.name] = f

class Filter:
    def __init__(self, name, title, table, columns, htmlvars):
	self.name = name
	self.table = table
	self.title = title
	self.columns = columns
	self.htmlvars = htmlvars
	
    def display(self):
	raise MKInternalError("Incomplete implementation of filter %s '%s': missing display()" % \
		(self.name, self.title))
	html.write("FILTER NOT IMPLEMENTED")

    def filter(self):
	raise MKInternalError("Incomplete implementation of filter %s '%s': missing filter()" % \
	    (self.name, self.title))
	html.write("FILTER NOT IMPLEMENTED")

    def tableprefix(self, tablename):
	if self.table == tablename:
	    return ""
	else:
	    return self.table[:-1] + "_"

class FilterText(Filter):
    def __init__(self, name, title, table, column, htmlvar, op):
	Filter.__init__(self, name, title, table, [column], [htmlvar])
	self.op = op
    
    def display(self):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar, "")
	html.text_input(htmlvar, current_value)

    def filter(self, tablename):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar)
	if current_value:
	    return "Filter: %s%s %s %s\n" % (self.tableprefix(tablename), self.columns[0], self.op, current_value)
	else:
	    return ""

class FilterServiceState(Filter):
    def __init__(self):
	Filter.__init__(self, "svcstate", "Service states", 
		"services", [ "state", "has_been_checked" ], [ "st0", "st1", "st2", "st3", "stp" ])
    
    def display(self):
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"
	for var, text in [("st0", "OK"), ("st1", "WARN"), ("st2", "CRIT"), ("st3", "UNKNOWN"), ("stp", "PENDING")]:
	    html.checkbox(var, defval)
	    html.write(" %s " % text)

    def filter(self, tablename):
	headers = []
	if html.var("filled_in"):
	    defval = ""
	else:
	    defval = "on"

	for i in [0,1,2,3]:
	    if html.var("st%d" % i, defval) == "on":
		headers.append("Filter: %sstate = %d\nFilter: has_been_checked = 1\nAnd: 2\n" % (self.tableprefix(tablename), i))
	if html.var("stp", defval) == "on":
	    headers.append("Filter: has_been_checked = 0\n")
	if len(headers) == 0:
	    return "Limit: 0\n" # now allowed state
	else:
	    return "".join(headers) + ("Or: %d\n" % len(headers))

declare_filter(FilterText("host", "Hostname", "hosts", "name", "host", "~~"))
declare_filter(FilterText("service", "Service", "services", "description", "service", "~~"))
declare_filter(FilterServiceState())

##################################################################################
# Layouts
##################################################################################

def render_ungrouped_list(data, filters, group_columns, group_painters, painters):
    show_filter_form(filters)
    columns, rowfunction, rows = data
    html.write("<table class=services>\n")
    trclass = None
    for row in rows:
        if trclass == "odd":
	    trclass = "even"
	else:
	    trclass = "odd"
        # render state, if available through whole tr
	state = row.get("state", 0)
	html.write("<tr class=%s%d>" % (trclass, state))
        for p in painters:
	    html.write(p["paint"](rowfunction(p, row)))
	html.write("</tr>\n")
    html.write("<table>\n")

def render_grouped_list(data, filters, group_columns, group_painters, painters):
    show_filter_form(filters)
    columns, rowfunction, rows = data
    html.write("<table class=services>\n")
    last_group = None
    trclass = None
    for row in rows:
        if trclass == "odd":
	    trclass = "even"
	else:
	    trclass = "odd"

        this_group = [ row[c] for c in group_columns ]
	if this_group != last_group:
	    html.write("<tr class=groupheader>")
	    html.write("<td colspan=%d><table><tr>" % len(painters))
            for p in group_painters:
	        html.write(p["paint"](rowfunction(p, row)))
	    html.write("</tr></table></td></tr>\n")
	    last_group = this_group
	    trclass = "even"
        # render state, if available through whole tr
	state = row.get("state", 0)
	html.write("<tr class=%s%d>" % (trclass, state))
        for p in painters:
	    html.write(p["paint"](rowfunction(p, row)))
	html.write("</tr>\n")
    html.write("<table>\n")

multisite_layouts["ungrouped_list"] = { 
    "render" : render_ungrouped_list,
}

multisite_layouts["grouped_list"] = { 
    "render" : render_grouped_list,
    "group" : True
}

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
    if row("site") and check_mk.multiadmin_use_siteicons:
	return "<td><img class=siteicon src=\"icons/site-%s-24.png\"> " % row("site")
    else:
	return "<td></td>"
	

multisite_painters["sitename_plain"] = {
    "paint" : lambda row: "<td>%s</td>" % row("site"),
}

def paint_host_black(row):
    state = row("state")
    if state == 0:
	style = "up"
    else:
	style = "down"
    return "<td class=host><b class=%s><a href=\"%s\">%s</a></b></td>" % \
	(style, nagios_host_url(row("site"), row("name")), row("name"))

multisite_painters["host_black"] = {
    "table" : "hosts",
    "paint" : paint_host_black,
}

multisite_painters["host_with_state"] = {
    "table" : "hosts",
    "paint" : lambda row: "<td class=hstate%d><a href=\"%s\">%s</a></td>" % \
	(row("state"), nagios_host_url(row("site"), row("name")), row("name")),
}

def paint_service_state_short(row):
    if row("has_been_checked") == 1:
	state = row("state")
	name = nagios_short_state_names[row("state")]
    else:
	state = "p"
	name = "PEND"
    return "<td class=state%s>%s</td>" % (state, name)

multisite_painters["service_state"] = {
    "paint" : paint_service_state_short
}

multisite_painters["site_icon"] = {
    "paint" : paint_site_icon
}

multisite_painters["plugin_output"] = {
    "paint" : lambda row: paint_plain(row("plugin_output"))
}
    
multisite_painters["service_description"] = {
    "paint" : lambda row: "<td><a href=\"%s\">%s</a></td>" % (nagios_service_url(row("site"), row("host_name"), row("description")), row("description"))
}

multisite_painters["state_age"] = {
    "title" : "The age of the current state",
    "paint" : lambda row: paint_age(row("last_state_change"), row("has_been_checked") == "1")
}
