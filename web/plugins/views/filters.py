
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

    def allowed_for_table(self, tablename):
	return True

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

    def allowed_for_table(self, tablename):
	if tablename == self.table:
	    return True
	if self.table == "hosts" and tablename == "services":
	    return True
	return False

class FilterLimit(Filter):
    def __init__(self):
	Filter.__init__(self, "limit", "Limit number of data sets", None, [], [ "limit" ])

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

declare_filter(FilterLimit())
	

# Helper that retrieves the list of host/service/contactgroups via Livestatus
def all_groups(what):
    groups = dict(html.live.query("GET %sgroups\nColumns: name alias\n" % what))
    names = groups.keys()
    names.sort()
    return [ (name, groups[name]) for name in names ]

class FilterHostgroupCombo(Filter):
    def __init__(self):
	Filter.__init__(self, "hostgroup", "Hostgroup-Combobox, obligatory",
		"hosts", [ "host_groups" ], [ "hostgroup" ])

    def display(self):
	html.select("hostgroup", all_groups("host"))

    def filter(self, tablename):
	htmlvar = self.htmlvars[0]
	current_value = html.var(htmlvar)
	if not current_value: # Take first hostgroup
	    current_value = html.live.query_value("GET hostgroups\nColumns: name\nLimit: 1\n")
	return "Filter: %sgroups >= %s\n" % (self.tableprefix(tablename), current_value)
    
    def allowed_for_table(self, tablename):
	return tablename in [ "hosts", "services", "hostgroups" ]


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
	
    def allowed_for_table(self, tablename):
	return tablename in [ "services" ]

declare_filter(FilterText("host", "Hostname", "hosts", "name", "host", "~~"))
declare_filter(FilterText("service", "Service", "services", "description", "service", "~~"))
declare_filter(FilterServiceState())
declare_filter(FilterHostgroupCombo())
