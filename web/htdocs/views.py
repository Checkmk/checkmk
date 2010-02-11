import check_mk, livestatus, htmllib, time, os, re, pprint, time
from lib import *
from pagefunctions import *

multisite_datasources = {}
multisite_filters     = {}
multisite_layouts     = {}
multisite_painters    = {}
multisite_sorters     = {}
multisite_views       = {}

plugins_path = check_mk.web_dir + "/plugins/views"
for fn in os.listdir(plugins_path):
    if fn.endswith(".py"):
	execfile(plugins_path + "/" + fn)

max_display_columns   = 10
max_group_columns     = 3
max_sort_columns      = 4

def load_views():
    global multisite_views
    multisite_views = {}
    subdirs = os.listdir(check_mk.multisite_config_dir)

    for user in subdirs:
	try:
	    dirpath = check_mk.multisite_config_dir + "/" + user
	    if os.path.isdir(dirpath):
	        f = file(dirpath + "/views.mk", "r", 0)
		sourcecode = f.read()
		t = 0
		while sourcecode == "": # This should never happen. But it happened. Don't know why.
		    # It's just a plain file. No fsync or stuff helped. Hack around a bit.
		    time.sleep(0.2)
		    sourcecode = f.read()
		    t += 1
		    if t > 10:
			raise MKGeneralException("Cannot load views from %s/view.mk: file empty or not flushed" % dirpath)
		views = eval(sourcecode)
		for name, view in views.items():
		    multisite_views[(user, name)] = view
	except IOError:
	     pass
	except SyntaxError, e:
	     raise MKGeneralException("Cannot load views from %s/views.mk: %s" % (dirpath, e))

def save_views(us):
    userviews = {}
    for (user, name), view in multisite_views.items():
	if us == user:
	    userviews[name] = view
    userdir = check_mk.multisite_config_dir + "/" + us
    if not os.path.exists(userdir):
	os.mkdir(userdir)
    f = file(userdir + "/views.mk", "w", 0)
    f.write(pprint.pformat(userviews) + "\n")
	    

# Show one view filled with data
def page_view(h):
    global html
    html = h
    load_views()
    try:
        user, view_name = html.var("view_name").split("/")
	view = multisite_views[(user, view_name)]
    except:
	raise MKGeneralException("This view does not exist (user: %s, name: %s)." % (user, view_name))

    html.header(view["title"])
    show_site_header(html)
    show_view(view)

    html.footer()

# Show list of all views with buttons for editing
def page_edit_views(h, msg=None):
    global html
    html = h
    html.header("Edit views")
    html.write("<p>Here you can create and edit customizable <b>views</b>. A view "
	    "displays monitoring status or log data by combining filters, sortings, "
	    "groupings and other aspects.</p>")

    if msg: # called from page_edit_view() after saving
	html.message(msg)

    load_views()

    # Deletion of views
    delname = html.var("delete")
    if delname and html.confirm("Please confirm the deletion of the view <tt>%s</tt>" % delname):
	del multisite_views[(html.req.user, delname)]
	save_views(html.req.user)

    # Cloning of views
    try:
	cloneuser, clonename = html.var("clone").split("/")
    except:
	clonename = ""

    if clonename:
	newname = clonename + "_clone"
	n = 1
	while (html.req.user, newname) in multisite_views:
	    n += 1
	    newname = clonename + "_clone%d" % n
	import copy
	orig = multisite_views[(cloneuser, clonename)]
	clone = copy.copy(orig)
	clone["name"] = newname
	clone["title"] = orig["title"] + " (Copy)" 
	if cloneuser != html.req.user: 
	    clone["public"] = False
	multisite_views[(html.req.user, newname)] = clone
	save_views(html.req.user)
	load_views()
		
    html.write("<table class=views>\n")

    keys_sorted = multisite_views.keys()
    keys_sorted.sort()
    first = True
    for (owner, viewname) in keys_sorted:
	view = multisite_views[(owner, viewname)]
	if owner == html.req.user or view["public"]:
	    if first:
		html.write("<tr><th>Name</th><th>Title</th><th>Owner</th><th>Public</th><th>Datasource</th><th></th></tr>\n")
		first = False
	    html.write("<tr><td class=legend>%s</td>" % viewname)
	    html.write("<td class=content><a href=\"view.py?view_name=%s/%s\">%s</a>" % (owner, viewname, view["title"]))
	    html.write("<td class=content>%s</td>" % owner)
	    html.write("<td class=content>%s</td>" % (view["public"] and "yes" or "no"))
	    html.write("</td><td class=content>%s</td><td class=buttons>\n" % view["datasource"])
	    html.buttonlink("edit_views.py?clone=%s/%s" % (owner, viewname), "Clone")
	    if owner == html.req.user:
		html.buttonlink("edit_view.py?load_view=%s" % viewname, "Edit")
		html.buttonlink("edit_views.py?delete=%s" % viewname, "Delete!")
	    html.write("</td></tr>")

    html.write("<tr><td class=legend colspan=6>")
    html.begin_form("create_view", "edit_view.py") 
    html.button("create", "Create new view")
    html.write(" for datasource: ")
    html.sorted_select("datasource", [ (k, v["title"]) for k, v in multisite_datasources.items() ])
    html.write("</table>\n")
    html.end_form()
    html.footer()


# Edit one view
def page_edit_view(h):
    global html
    html = h

    view = None

    # Load existing view from disk
    viewname = html.var("load_view")
    if viewname:
	load_views()
	view = multisite_views.get((html.req.user, viewname), None)
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
		load_views()
		multisite_views[(html.req.user, view["name"])] = view
		save_views(html.req.user)
		return page_edit_views(h, "Your view has been saved.")

	except MKUserError, e:
	    html.write("<div class=error>%s</div>\n" % e.message)
	    html.add_user_error(e.varname, e.message)

    html.header("Edit view")
    html.write("<p>Edit the properties of the view or go <a href=\"edit_views.py\">back to this list of all views</a>.</p>")
    html.begin_form("view")
    html.write("<table class=view>\n")

    html.write("<tr><td class=legend>Shortname for linking</td><td class=content>")
    html.text_input("view_name")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Title</td><td class=content>")
    html.text_input("view_title")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Configuration</td><td class=content>")
    html.checkbox("public")
    html.write(" make this view available for all users")
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
	html.write("<td class=title>%s</td>" % filt.title)
	html.write("<td class=usage>")
	html.sorted_select("filter_%s" % fname, [("off", "Don't use"), ("show", "Show to user"), ("hard", "Hardcode")], "", "filter_activation")
	html.write("</td><td class=widget>")
	filt.display()
	html.write("</td></tr>\n")
    html.write("</table></td></tr>\n")
    html.write("<script language=\"javascript\">\n")
    for fname, filt in allowed_filters.items():
	html.write("filter_activation(\"filter_%s\");\n" % fname)
    html.write("</script>\n")	
   
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
    
    if html.has_var("try") or html.has_var("search"):
        html.set_var("search", "on")
	if view: 
	    show_view(view)

    html.footer()

def load_view_into_html_vars(view):
    # view is well formed, not checks neccessary
    html.set_var("view_title", view["title"])
    html.set_var("view_name",  view["name"])
    html.set_var("datasource", view["datasource"])
    html.set_var("layout",     view["layout"])
    html.set_var("public",     view["public"] and "on" or "")

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
    public = html.var("public", "") != ""
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
	"public"          : public,
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
    columns, rows = query_data(datasource, query)

    # [4] Sorting
    sorters = [ (multisite_sorters[sn], reverse) for sn, reverse in view["sorters"] ]
    sort_data(rows, sorters)

    # [5] Grouping
    group_painters = [ multisite_painters[n] for n in view["group_painters"] ]
    group_columns = needed_group_columns(group_painters)

    # [6] Columns
    painters = [ multisite_painters[n] for n in view["painters"] ]
    layout["render"]((columns, rows), show_filters, group_columns, group_painters, painters)

def needed_group_columns(painters):
    columns = []
    for p in painters:
	columns += p["columns"] 
    return columns


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
def query_data(datasource, add_headers):
    tablename = datasource["table"]
    query = "GET %s\n" % tablename
    columns = datasource["columns"]
    query += "Columns: %s\n" % " ".join(datasource["columns"])
    query += add_headers
    html.live.set_prepend_site(True)
    html.write("<div class=message><pre>%s</pre></div>\n" % query)
    data = html.live.query(query)
    # convert lists-rows into dictionaries. Thas costs a bit of
    # performance, but makes live much easier later. What also
    # makes live easier is, that we prefix all columns with
    # the table name, if that prefix is not already present
    # for example "name" -> "host_name" in table "hosts"
    prefixed_columns = ["site"]
    for col in columns:
	parts = col.split("_", 1)
	if len(parts) < 2 or parts[0] not in [ "host", "service", "contact", "contactgroup" ]:
		col = tablename[:-1] + "_" + col
	elif tablename == "log" and col.startswith("current_"):
	    col = col[8:]
	prefixed_columns.append(col)

    assoc = [ dict(zip(prefixed_columns, row)) for row in data ]
    html.live.set_prepend_site(False)

    return (prefixed_columns, assoc)

# Sort data according to list of sorters. The tablename
# is needed in order to handle different column names
# for same objects (e.g. host_name in table services and
# simply name in table hosts)
def sort_data(data, sorters):
    if len(sorters) == 0:
	return
    elif len(sorters) == 1:
        data.sort(sorters[0][0]["cmp"], None, sorters[0][1])
	return
    
    sort_cmps = [(s["cmp"], (reverse and -1 or 1)) for s, reverse in sorters]

    def multisort(e1, e2):
	for func, neg in sort_cmps:
	    c = neg * func(e1, e2)
	    if c != 0: return c
	return 0 # equal

    data.sort(multisort)


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
