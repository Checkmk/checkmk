
##################################################################################
# Filters
##################################################################################

def declare_filter(f, comment = None):
    multisite_filters[f.name] = f
    f.comment = comment
    
    
class Filter:
    def __init__(self, name, title, table, htmlvars):
	self.name = name
	self.table = table
	self.title = title
	self.htmlvars = htmlvars
	
    def display(self):
	raise MKInternalError("Incomplete implementation of filter %s '%s': missing display()" % \
		(self.name, self.title))
	html.write("FILTER NOT IMPLEMENTED")

    def filter(self):
	raise MKInternalError("Incomplete implementation of filter %s '%s': missing filter()" % \
	    (self.name, self.title))
	html.write("FILTER NOT IMPLEMENTED")
    
    def variable_settings(self, row):
       return [] # return pairs of htmlvar and name according to dataset in row	

    def tableprefix(self, tablename):
	if self.table == tablename:
	    return ""
	else:
	    return self.table[:-1] + "_"

    def allowed_for_table(self, tablename):
	return True

    # Hidden filters may contribute to the pages headers of the views
    def heading_info(self, tablename):
	return None

# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, name, title, table, column, htmlvar, op):
	Filter.__init__(self, name, title, table, [htmlvar])
	self.op = op
	self.column = column
    
    def display(self):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar, "")
	html.text_input(htmlvar, current_value)

    def filter(self, tablename):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar)
	if current_value:
	    return "Filter: %s%s %s %s\n" % (self.tableprefix(tablename), self.column, self.op, current_value)
	else:
	    return ""

    def variable_settings(self, row):
       return [ (self.htmlvars[0], row[self.table[:-1] + "_" + self.column]) ]
    
    def allowed_for_table(self, tablename):
	if tablename == self.table:
	    return True
	if self.table == "hosts" and tablename == "services":
	    return True
	return False

    def heading_info(self, tablename):
	htmlvar = self.htmlvars[0]
	return html.var(self.htmlvars[0])

declare_filter(FilterText("hostregex",    "Hostname",             "hosts",    "name",          "hostregex",    "~~"),
			  "Search field with regular expressions, also allows partial matches")
declare_filter(FilterText("host",    "Hostname",             "hosts",    "name",          "host",    "="),
			  "Exact match. Use this for linking from other views.")
declare_filter(FilterText("service", "Service",              "services", "description",   "service", "~~"))
declare_filter(FilterText("output",  "Service check output", "services", "plugin_output", "service", "~~"))


class FilterLimit(Filter):
    def __init__(self):
	Filter.__init__(self, "limit", "Limit number of data sets", None, [ "limit" ])

    def current_value(self):
	try:
	    return int(html.var("limit"))
	except:
	    return 0

    def display(self):
	html.number_input("limit", self.current_value())
    
    def filter(self, tablename):
	v = self.current_value()
	if v > 0:
	    return "Limit: %d\n" % v
	return ""

declare_filter(FilterLimit(), "Limits the number of items queried via livestatus. The limitation is "
	"done <b>before</b> any sorting is done.")
	

# Helper that retrieves the list of host/service/contactgroups via Livestatus
def all_groups(what):
    groups = dict(html.live.query("GET %sgroups\nColumns: name alias\n" % what))
    names = groups.keys()
    names.sort()
    return [ (name, groups[name]) for name in names ]

class FilterGroupCombo(Filter):
    def __init__(self, what):
	Filter.__init__(self, what + "group", what[0].upper() + what[1:] + "group",
		what + "s", [ what + "group" ])
        self.what = what

    def display(self):
	html.select(self.what + "group", all_groups(self.what))

    def current_value(self, tablename):
	htmlvar = self.htmlvars[0]
	return html.var(htmlvar)

    def filter(self, tablename):
	current_value = self.current_value(tablename)
	if not current_value: # Take first group with the name we search
	    current_value = html.live.query_value("GET %sgroups\nColumns: name\nLimit: 1\n" % self.what, None)
	if current_value == None:
	    return "" # no {what}group exists!

	if self.what + "s" == tablename:
	    col = "groups"
	else:
	    col = self.what + "_groups"
	return "Filter: %s >= %s\n" % (col, current_value)
    
    def allowed_for_table(self, tablename):
	if tablename == "services": return True # Service table allows all groups
	elif tablename == "hosts" : return self.what in [ "host", "contact" ]
	elif tablename == "contacts" : return self.what == "contact"
	else:
	    return False

    def heading_info(self, tablename):
	current_value = self.current_value(tablename)
	if current_value:
	    alias = html.live.query_value("GET %sgroups\nColumns: alias\nFilter: name = %s\n" % 
		(self.what, current_value))
	    return alias


declare_filter(FilterGroupCombo("host"), "Dropdown list, selection of host group is enforced")
declare_filter(FilterGroupCombo("service"), "Dropdown list, selection of service group is enforced")
# Livestatus still misses "contact_groups" column. 
# declare_filter(FilterGroupCombo("contact"))

class FilterQueryDropdown(Filter):
    def __init__(self, name, title, table, query, filterline):
	Filter.__init__(self, name, title, table, [ name ])
	self.query = query
	self.filterline = filterline

    def display(self):
	selection = html.live.query_column_unique(self.query)
	html.sorted_select(self.name, [("", "")] + [(x,x) for x in selection])

    def filter(self, tablename):
	current = html.var(self.name)
	if current:
	    return self.filterline % current
	else:
	    return ""

    def allowed_for_table(self, tablename):
	return self.table == tablename

declare_filter(FilterQueryDropdown("check_command", "Check command", "services", \
	"GET commands\nColumns: name\n", "Filter: check_command = %s\n"))

class FilterServiceState(Filter):
    def __init__(self):
	Filter.__init__(self, "svcstate", "Service states", 
		"services", [ "st0", "st1", "st2", "st3", "stp" ])
    
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
	
    def allowed_for_table(self, tablename):
	return tablename == "services"

class FilterTristate(Filter):
    def __init__(self, name, title, table, column, deflt = -1):
	self.column = column
	self.varname = "is_" + name
	Filter.__init__(self, name, title, table, [ self.varname ])
	self.deflt = deflt
   
    def display(self):
        current = html.var(self.varname)
        for value, text in [("1", "yes"), ("0", "no"), ("-1", "(ignore)")]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text)

    def tristate_value(self):
        current = html.var(self.varname)
	if current in [ None, "" ]:
	    return self.deflt
	return int(current)
	
    def allowed_for_table(self, tablename):
	if self.table == "hosts":
	    return tablename in [ "hosts", "services" ]
	else:
	    return tablename == self.table
    
    def filter(self, tablename):
	current = self.tristate_value()
	if current == -1: # ignore
	    return ""
	elif current == 1:
	    return self.filter_code(tablename, True)
	else:
	    return self.filter_code(tablename, False)

class FilterNagiosFlag(FilterTristate):
    def __init__(self, table, column, title, deflt = -1):
	FilterTristate.__init__(self, table[:-1] + "_" + column, title, table, column, deflt)

    def filter_code(self, tablename, positive):
	if tablename == "services" and self.table == "hosts":
	    column = "host_" + self.column
	else:
	    column = self.column
	if positive:
	    return "Filter: %s != 0\n" % column
	else:
	    return "Filter: %s = 0\n" % column

class FilterNagiosExpression(FilterTristate):
    def __init__(self, table, name, title, pos, neg, deflt = -1):
	FilterTristate.__init__(self, name, title, table, None, deflt)
	self.pos = pos
	self.neg = neg

    def allowed_for_table(self, tablename):
	return self.table == tablename

    def filter_code(self, tablename, positive):
	return positive and self.pos or self.neg

declare_filter(FilterNagiosExpression("services", "show_summary_hosts", "Show summary hosts", 
	    "Filter: host_custom_variable_names >= _REALNAME\n",
	    "Filter: host_custom_variable_names < _REALNAME\n"))


declare_filter(FilterNagiosFlag("hosts",    "in_notification_period",   "Host is in notification period"))
declare_filter(FilterNagiosFlag("services", "acknowledged",             "Problem has been acknowledged"))
declare_filter(FilterNagiosFlag("services", "in_notification_period",   "Service is in notification period"))
declare_filter(FilterNagiosFlag("services", "active_checks_enabled",    "Active checks enabled"))
declare_filter(FilterNagiosFlag("services", "notifications_enabled",    "Notifications enabled"))
declare_filter(FilterNagiosFlag("services", "is_flapping",              "Flapping"))
declare_filter(FilterNagiosFlag("services", "in_notification_period",   "Service is in notification period"))
declare_filter(FilterNagiosFlag("hosts",    "in_notification_period",   "Host is in notification period"))
declare_filter(FilterNagiosFlag("services", "scheduled_downtime_depth", "Service in downtime"))
declare_filter(FilterNagiosFlag("hosts",    "scheduled_downtime_depth", "Host in downtime"))
declare_filter(FilterNagiosExpression("services", "in_downtime", "Host or Service in downtime",
	    "Filter: scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n",
	    "Filter: scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"))
	
declare_filter(FilterServiceState())

class FilterSite(Filter):
    def __init__(self):
	Filter.__init__(self, "site", "Site", None, ["site"])

    def display(self):
	site_selector(html, "site")

    def filter(self, tablename):
	if check_mk.is_multisite():
	    return "Sites: %s\n" % html.var("site", "")
	else:
	    return ""

    def heading_info(self, tablename):
	current_value = html.var("site")
	if current_value:
	    alias = check_mk.site(current_value)["alias"]
	    return alias
    
    def variable_settings(self, row):
	return [("site", row["site"])]
	

declare_filter(FilterSite())
