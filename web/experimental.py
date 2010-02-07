import check_mk, livestatus, htmllib, time, os, re, pprint
from lib import *

multisite_datasources = {}
multisite_filters     = {}
multisite_layouts     = {}
multisite_painters    = {}
multisite_sorters     = {}
multisite_views       = {}

include_path = "/usr/share/check_mk/web"
execfile(include_path + "/datasources.py")
execfile(include_path + "/layouts.py")
execfile(include_path + "/filters.py")
execfile(include_path + "/sortings.py")
execfile(include_path + "/painters.py")

max_display_columns   = 10
max_group_columns     = 3
max_sort_columns      = 4


def setup(h):
    global html, authuser
    html = h
    authuser = html.req.user

    if check_mk.multiadmin_restrict and \
	authuser not in check_mk.multiadmin_unrestricted_users:
	    auth_user = authuser
    else:
	auth_user = None

    connect_to_livestatus(html, auth_user)

multisite_config_dir = "/tmp"

def load_views(user = None): # None => load all views
    if user:
	subdirs = [user]
    else:
	subdirs = os.listdir(multisite_config_dir)

    for user in subdirs:
	try:
	    dirpath = multisite_config_dir + "/" + user
	    if os.path.isdir(dirpath):
	        f = file(dirpath + "/views.mk")
		views = eval(f.read())
		for name, view in views.items():
		    multisite_views[(user, name)] = view
	except:
	     pass

def save_views(us):
    userviews = {}
    for (user, name), view in multisite_views.items():
	if us == user:
	    userviews[name] = view
    userdir = multisite_config_dir + "/" + user
    if not os.path.exists(userdir):
	os.mkdir(userdir)
    file(userdir + "/views.mk", "w").write(pprint.pformat(userviews) + "\n")
	    

# Show one view filled with data
def page_view(h):
    setup(h)
    load_views()
    try:
        user, view_name = html.var("view_name").split("/")
	view = multisite_views[(user, view_name)]
    except:
	raise MKGeneralException("This view does not exist.")

    html.header(view["title"])
    show_view(view)

    html.footer()

# Show list of all views with buttons for editing
def page_edit_views(h, msg=None):
    setup(h)
    html.header("Experimental: User defined views")

    if msg: # called from page_edit_view() after saving
	html.message(msg)

    load_views(authuser)

    # Deletion of views
    delname = html.var("delete")
    if delname and html.confirm("Please confirm the deletion of the view <tt>%s</tt>" % delname):
	del multisite_views[(authuser, delname)]
	save_views(authuser)

    # Cloning of views
    clonename = html.var("clone")
    if clonename:
	newname = clonename + "_clone"
	n = 1
	while (authuser, newname) in multisite_views:
	    n += 1
	    newname = clonename + "_clone%d" % n
	import copy
	orig = multisite_views[(authuser, clonename)]
	clone = copy.copy(orig)
	clone["name"] = newname
	clone["title"] = orig["title"] + " (Copy)" 
	multisite_views[(authuser, newname)] = clone
	save_views(authuser)
		
    html.write("<table class=views>\n")
    html.write("<tr><th>Name</th><th>Title</th><th>Datasource</th><th></th></tr>\n")
    keys_sorted = multisite_views.keys()
    keys_sorted.sort()
    for (user, viewname) in keys_sorted:
	view = multisite_views[(user, viewname)]
	if user == authuser:
	    html.write("<tr><td class=legend>%s</td>" % viewname)
	    html.write("<td class=content><a href=\"view.py?view_name=%s/%s\">%s</a>" % (user, viewname, view["title"]))
	    html.write("</td><td class=content>%s</td><td class=edit>\n" % view["datasource"])
	    html.buttonlink("edit_view.py?load_view=%s" % viewname, "Edit")
	    html.buttonlink("edit_views.py?clone=%s" % viewname, "Clone")
	    html.buttonlink("edit_views.py?delete=%s" % viewname, "Delete!")
	    html.write("</td></tr>")
    html.write("</table>\n")

    html.begin_form("create_view", "edit_view.py") 
    html.button("create", "Create new view for datasource -> ")
    html.sorted_select("datasource", [ (k, v["title"]) for k, v in multisite_datasources.items() ])
    html.end_form()
    html.footer()


# Edit one view
def page_edit_view(h):
    setup(h)

    view = None

    # Load existing view from disk
    viewname = html.var("load_view")
    if viewname:
	load_views(authuser)
	view = multisite_views.get((authuser, viewname), None)
	datasourcename = view["datasource"]
	if view:
	    load_view_into_html_vars(view)

    # set datasource name if a new view is being created
    elif html.var("datasource"):
	datasourcename = html.var("datasource")

    # handle case of save or try or press on search button
    if html.var("save") or html.var("try") or html.var("search"):
	try:
	    view = create_view()
	    if html.var("save"):
		load_views(authuser)
		multisite_views[(authuser, view["name"])] = view
		save_views(authuser)
		return page_edit_views(h, "Your view has been saved.")

	except MKUserError, e:
	    html.write("<div class=error>%s</div>\n" % e.message)
	    html.add_user_error(e.varname, e.message)

    html.header("Experimental: View designer")
    html.buttonlink("edit_views.py", "Back to list of views")
    html.begin_form("view")
    html.write("<table class=view>\n")

    html.write("<tr><td class=legend>Shortname for linking</td><td class=content>")
    html.text_input("view_name")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Title</td><td class=content>")
    html.text_input("view_title")
    html.write("</td></tr>\n")

    def show_list(name, title, data):
	html.write("<tr><td class=legend>%s</td>" % title)
	html.write("<td class=content>")
	html.sorted_select(name, [ (k, v["title"]) for k,v in data.items() ])
	html.write("</td></tr>\n")

    # [1] Datasource (not changeable here!)
    html.write("<tr><td class=legend>1. Datasource</td><td>%s</td></tr>" % datasourcename)
    html.hidden_field("datasource", datasourcename)
    
    # [2] Layout
    show_list("layout", "2. Layout", multisite_layouts)
  
    # [3] Filters 
    html.write("<tr><td class=legend>3. Filters</td><td>")
    html.write("<table class=filters>")
    html.write("<tr><th>Filter</th><th>usage</th><th>hardcoded settings</th></tr>\n")
    allowed_filters = filters_allowed_for_datasource(datasourcename)
    for fname, filt in allowed_filters.items():
	html.write("<tr>")
	html.write("<td>%s</td>" % filt.title)
	html.write("<td>")
	html.sorted_select("filter_%s" % fname, [("off", "Don't use"), ("show", "Show to user"), ("hard", "Hardcode")])
	html.write("</td><td>")
	filt.display()
	html.write("</td></tr>\n")
    html.write("</table></td></tr>\n")
   
    # [4] Sorting
    def column_selection(title, var_prefix, maxnum, data, order=False):
	allowed = allowed_for_datasource(data, datasourcename)
	html.write("<tr><td class=legend>%s</td><td class=content>" % title)
	for n in range(1, maxnum+1):
	    collist = [ ("", "") ] + [ (name, p["title"]) for name, p in allowed.items() ]
	    html.write("%02d " % n)
	    html.select("%s%d" % (var_prefix, n), collist)
	    if order:
		html.write(" ")
		html.select("%sorder_%d" % (var_prefix, n), [("asc", "Ascending"), ("dsc", "Descending")])
	    html.write("<br />")
	html.write("</td></tr>\n")
    column_selection("4. Sorting", "sort_", max_sort_columns, multisite_sorters, True)

    # [5] Grouping
    column_selection("5. Group by", "group_", max_group_columns, multisite_painters)

    # [6] Columns (painters)	
    column_selection("6. Display columns", "col_", max_display_columns, multisite_painters)

    html.write("<tr><td colspan=2>")
    html.button("try", "Try out")
    html.write(" ")
    html.button("save", "Save")
    html.write("</table>\n")
    html.end_form()
    
    if html.has_var("try") or html.has_var("filled_in"):
        html.set_var("filled_in", "on")
	if view: 
	    show_view(view)

    html.footer()

def load_view_into_html_vars(view):
    # view is well formed, not checks neccessary
    html.set_var("view_title", view["title"])
    html.set_var("view_name",  view["name"])
    html.set_var("datasource", view["datasource"])
    html.set_var("layout",     view["layout"])

    # [3] Filters
    for name, filt in multisite_filters.items():
	if name in view["show_filters"]:
	    html.set_var("filter_%s" % name, "show")
	elif name in view["hard_filters"]:
	    html.set_var("filter_%s" % name, "hard")
    for varname, value in view["hard_filtervars"]:
	html.set_var(varname, value)

    # [4] Sorting
    n = 1
    for name, desc in view["sorters"]:
	html.set_var("sort_%d" % n, name)
	if desc:
	    value = "dsc"
	else:
	    value = "asc"
	html.set_var("sort_order_%d" % n, value)
	n +=1

    # [5] Grouping
    n = 1
    for name in view["group_painters"]:
	html.set_var("group_%d" % n, name)
	n += 1

    # [6] Columns
    n = 1
    for name in view["painters"]:
	html.set_var("col_%d" % n, name)
	n += 1

    # Make sure, checkboxes with default "on" do no set "on". Otherwise they
    # would always be on
    html.set_var("filled_in", "on")

# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
def create_view():
    name = html.var("view_name").strip()
    if name == "":
	raise MKUserError("view_name", "Please supply a unique name for the view, this will be used to specify that view in HTTP links.")
    if not re.match("^[a-zA-Z0-9_]+$", name):
	raise MKUserError("view_name", "The name of the view may only contain letters, digits and underscores.")
    title = html.var("view_title").strip()
    if title == "":
	raise MKUserError("view_title", "Please specify a title for your view")

    datasourcename = html.var("datasource")
    datasource = multisite_datasources[datasourcename]
    tablename = datasource["table"]
    layoutname = html.var("layout")
    show_filternames = []
    hard_filternames = []
    hard_filtervars = []

    for fname, filt in multisite_filters.items():
	usage = html.var("filter_%s" % fname)
	if usage == "show":
	    show_filternames.append(fname)
	elif usage == "hard":
	    hard_filternames.append(fname)
	    for varname in filt.htmlvars:
		hard_filtervars.append((varname, html.var(varname, "")))

    sorternames = []
    for n in range(1, max_sort_columns+1):
	sname = html.var("sort_%d" % n)
	if sname:
	    reverse = html.var("sort_order_%d" % n) == "dsc"
	    sorternames.append((sname, reverse))

    group_painternames = [] 
    for n in range(1, max_group_columns+1):
	pname = html.var("group_%d" % n)
	if pname:
	    group_painternames.append(pname)

    painternames = []
    for n in range(1, max_display_columns+1):
	pname = html.var("col_%d" % n)
	if pname:
	    painternames.append(pname)
  
    return { 
	"name"            : name,
	"title"           : title,
	"datasource"      : datasourcename,
	"layout"          : layoutname,
	"show_filters"    : show_filternames,
	"hard_filters"    : hard_filternames,
	"hard_filtervars" : hard_filtervars,
	"sorters"         : sorternames,
	"group_painters"  : group_painternames,
	"painters"        : painternames
    }


# Display view with real data. This is *the* function everying
# is about.
def show_view(view):
    # [1] Datasource
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]

    # [2] Layout
    layout = multisite_layouts[view["layout"]]
    
    # [3] Filters
    show_filters = [ multisite_filters[fn] for fn in view["show_filters"] ]
    hard_filter = [ multisite_filters[fn] for fn in view["hard_filters"] ]
    for varname, value in view["hard_filtervars"]:
	html.set_var(varname, value)
    filterheaders = "".join(f.filter(tablename) for f in show_filters)
    filterheaders += "".join(f.filter(tablename) for f in hard_filter)
    query = filterheaders + view.get("add_headers", "")
    
    # Fetch data
    data = query_data(datasource, query)

    # [4] Sorting
    sorters = [ (multisite_sorters[sn], reverse) for sn, reverse in view["sorters"] ]
    sort_data(data[2], sorters, tablename)

    # [5] Grouping
    group_painters = [ multisite_painters[n] for n in view["group_painters"] ]
    group_columns = needed_group_columns(group_painters, tablename)

    # [6] Columns
    painters = [ multisite_painters[n] for n in view["painters"] ]
    layout["render"](data, show_filters, group_columns, group_painters, painters)

def needed_group_columns(painters, tablename):
    columns = []
    for p in painters:
	t = p.get("table", tablename)
	if tablename != t:
	    prefix = p["table"][:-1] + "_"
	else:
	    prefix = ""
	for c in p["columns"]:
	    if c != "site":
		c = prefix + c
	    if c not in columns:
		columns.append(c)
    return columns


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
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

# Sort data according to list of sorters. The tablename
# is needed in order to handle different column names
# for same objects (e.g. host_name in table services and
# simply name in table hosts)
def sort_data(data, sorters, tablename):
    if len(sorters) == 0:
	return
    
    # Construct sort function. It must return -1, 0 or +1 when
    # comparing to elements of data. The sorter functions do
    # not expect a row array but a rowfunction for each of the
    # the elements
    sort_cmps = []

    # convert compare function that gets to functions row() into
    # compare function that gets to row-dictionaries. Also take
    # reverse sorting into account
    def make_compfunc(rowfunc, compfunc, reverse):
        if reverse:	
	    return lambda dict2, dict1: compfunc(lambda k: rowfunc(dict1, k), lambda k: rowfunc(dict2, k))
	else:
	    return lambda dict1, dict2: compfunc(lambda k: rowfunc(dict1, k), lambda k: rowfunc(dict2, k))

    for s, reverse in sorters:
        tn = s.get("table", tablename)
	if tn == tablename:
	    rowfunc = lambda a, b: a[b]
	else:
	    prefix = tn[:-1] + "_"
	    rowfunc = lambda a, b: a[prefix + b]

	compfunc = s["cmp"]
	cmp = make_compfunc(rowfunc, compfunc, reverse)
	sort_cmps.append(cmp)

    compfunc = None

    def multisort(e1, e2):
	for cmp in sort_cmps:
	    c = cmp(e1, e2)
	    if c != 0: return c
	return 0 # equal

    if len(sort_cmps) > 1:
	data.sort(multisort)
    else:
	data.sort(sort_cmps[0])


def filters_allowed_for_datasource(datasourcename):
    datasource = multisite_datasources[datasourcename]
    tablename = datasource["table"]
    allowed = {}
    for fname, filt in multisite_filters.items():
	if filt.allowed_for_table(tablename):
	    allowed[fname] = filt
    return allowed

def painters_allowed_for_datasource(datasourcename):
    return allowed_for_datasource(multisite_painters, datasourcename)

def sorters_allowed_for_datasource(datasourcename):
    return allowed_for_datasource(multisite_sorters, datasourcename)

def allowed_for_datasource(collection, datasourcename):
    datasource = multisite_datasources[datasourcename]
    tablename = datasource["table"]
    allowed = {}
    for name, item in collection.items():
	if item["table"] == tablename or \
	    item["table"] == None or \
	    (item["table"] == "hosts" and tablename == "services"):
	    allowed[name] = item
    return allowed

     
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


