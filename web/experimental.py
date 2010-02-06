import check_mk, livestatus, htmllib, time
from lib import *

multisite_datasources = {}
multisite_filters     = {}
multisite_layouts     = {}
multisite_painters    = {}
max_display_columns  = 10


def setup(h):
    global html
    html = h

    if check_mk.multiadmin_restrict and \
	html.req.user not in check_mk.multiadmin_unrestricted_users:
	    auth_user = html.req.user
    else:
	auth_user = None

    connect_to_livestatus(html, auth_user)

def page(h):
    setup(h)
    html.header("Experimental")
    # show_page("hosts", "ungrouped_list", [ "sitename_plain", "host_with_state" ])
    show_page("services",  # data source
	      [ "host", "service", "svcstate" ], # filters
	      "grouped_list", # layout
	      [ "site", "host_name" ], # grouping columns
	      [ "site_icon", "host_black" ], # group painters
	      [ "service_state", "service_description", "state_age", "plugin_output" ])

    html.footer()

def page_designer(h):
    setup(h)
    html.header("Experimental: View designer")
    html.begin_form("view")
    html.write("<table class=view>\n")
    def show_list(name, title, data):
	html.write("<tr><td class=legend>%s</td>" % title)
	html.write("<td class=content>")
	html.select(name, [ (k, v["title"]) for k,v in data.items() ])
	html.write("</td></tr>\n")

    # [1] Datasource
    show_list("datasource", "Datasource", multisite_datasources)
    
    # [2] Layout
    show_list("layout", "Layout", multisite_layouts)
  
    # [3] Filters 
    html.write("<tr><td class=legend>Filters</td><td>")
    html.write("<table class=filters>")
    html.write("<tr><th>Filter</th><th>usage</th><th>hardcoded settings</th></tr>\n")
    for fname, filt in multisite_filters.items():
	html.write("<tr>")
	html.write("<td>%s</td>" % filt.title)
	html.write("<td>")
	html.select("filter_%s" % fname, [("off", "Don't use"), ("show", "Show to user"), ("hard", "Hardcode")])
	html.write("</td><td>")
	filt.display()
	html.write("</td></tr>\n")
    html.write("</table></td></tr>\n")
   
    # [4] Sorting

    # [5] Grouping

    # [6] Columns (painters)	
    html.write("<tr><td class=legend>Columns</td><td class=content>")
    for n in range(1, max_display_columns+1):
	collist = [ ("", "") ] + [ (name, p["title"]) for name, p in multisite_painters.items() ]
	html.write("%02d " % n)
	html.select("col_%d" % n, collist)
	html.write("<br />")
    html.write("</td></tr>\n")
    html.write("<tr><td colspan=2>")
    html.button("show", "Try out")
    html.write("</table>\n")
    html.heading("Sorting &amp; Grouping")

    html.heading("Display columns")

    if html.var("show"):
	html.write("Zeige")
	preview_view()

def preview_view():
    datasourcename = html.var("datasource")
    datasource = multisite_datasources[datasourcename]
    tablename = datasource["table"]
    layoutname = html.var("layout")
    filternames = []
    add_headers = ""
    for fname, filt in multisite_filters.items():
	usage = html.var("filter_%s" % fname)
	if usage == "show":
	    filternames.append(fname)
	elif usage == "hard":
	    add_headers += filt.filter(tablename)
    
    painternames = []
    for n in range(1, max_display_columns+1):
	pname = html.var("col_%d" % n)
	if pname:
	    painternames.append(pname)
   
    html.set_var("filled_in", "on") 
    show_page(datasourcename, add_headers, filternames, layoutname, [], [], painternames) 


def show_page(datasourcename, add_headers, filternames, layoutname, group_columns, group_painternames, painternames):
    datasource = multisite_datasources[datasourcename]
    filters = [ multisite_filters[fn] for fn in filternames ]
    filterheaders = "".join(f.filter(datasource["table"]) for f in filters)
    query = filterheaders + add_headers
    data = query_data(datasource, query)
    painters = [ multisite_painters[n] for n in painternames ]
    layout = multisite_layouts[layoutname]
    group_painters = [ multisite_painters[n] for n in group_painternames ]
    layout["render"](data, filters, group_columns, group_painters, painters)

def show_filter_form(filters):
    if len(filters) > 0:
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
    "title"   : "All hosts",
    "table"   : "hosts",
    "columns" : ["name", "state"],
}

multisite_datasources["services"] = {
    "title"   : "All services",
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
    "title"  : "Ungrouped list",
    "render" : render_ungrouped_list,
}

multisite_layouts["grouped_list"] = { 
    "title"  : "Grouped list",
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
    "title" : "The id of the site",
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
    "title" : "Hostname, red background if down or unreachable",
    "table" : "hosts",
    "paint" : paint_host_black,
}

multisite_painters["host_with_state"] = {
    "title" : "Hostname colored with state",
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
    "title" : "The service state, colored and short (4 letters)",
    "paint" : paint_service_state_short
}

multisite_painters["site_icon"] = {
    "title" : "Icon showing the site",
    "paint" : paint_site_icon
}

multisite_painters["plugin_output"] = {
    "title" : "Output of check plugin",
    "paint" : lambda row: paint_plain(row("plugin_output"))
}
    
multisite_painters["service_description"] = {
    "title" : "Service description",
    "paint" : lambda row: "<td><a href=\"%s\">%s</a></td>" % (nagios_service_url(row("site"), row("host_name"), row("description")), row("description"))
}

multisite_painters["state_age"] = {
    "title" : "The age of the current state",
    "paint" : lambda row: paint_age(row("last_state_change"), row("has_been_checked") == "1")
}
