import check_mk, livestatus, htmllib, time, os, re, pprint, time
from lib import *
from pagefunctions import *

multisite_datasources   = {}
multisite_filters       = {}
multisite_layouts       = {}
multisite_painters      = {}
multisite_sorters       = {}
multisite_builtin_views = {}

plugins_path = check_mk.web_dir + "/plugins/views"
for fn in os.listdir(plugins_path):
    if fn.endswith(".py"):
	execfile(plugins_path + "/" + fn)

max_display_columns   = 10
max_group_columns     = 3
max_sort_columns      = 4

# Load all views - users or builtins
def load_views():
    html.multisite_views = {}

    # first load builtins. Set username to ''
    for name, view in multisite_builtin_views.items():
	view["owner"] = '' # might have been forgotten on copy action
	view["public"] = True
	view["name"] = name
	html.multisite_views[('', name)] = view

    # Now scan users subdirs for files "views.mk"
    subdirs = os.listdir(check_mk.multisite_config_dir)
    for user in subdirs:
	try:
	    dirpath = check_mk.multisite_config_dir + "/" + user
	    if os.path.isdir(dirpath):
		path = dirpath + "/views.mk"
		if not os.path.exists(path):
		    continue
	        f = file(path, "r", 65536)
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
		    view["owner"] = user
		    view["name"] = name
		    html.multisite_views[(user, name)] = view
	except SyntaxError, e:
	     raise MKGeneralException("Cannot load views from %s/views.mk: %s" % (dirpath, e))

    html.available_views = available_views()

# Get the list of views which are available to the user
# (which could be retrieved with get_view)
def available_views():
    user = html.req.user
    views = {}
    # 1. user's own views
    for (u, n), view in html.multisite_views.items():
	views[n] = view

    # 2. views of admin users, if public
    for (u, n), view in html.multisite_views.items():
	if n not in views \
	    and u in check_mk.multiadmin_unrestricted_action_users \
	    and view["public"]:
	    views[n] = view
    
    # 3. Builtin views
    for (u, n), view in html.multisite_views.items():
	if u == '' and n not in views:
	    views[n] = view

    # 4. other users views, if public
    for (u, n), view in html.multisite_views.items():
	if n not in views and view["public"]:
	    views[n] = view

    return views


def save_views(us):
    userviews = {}
    for (user, name), view in html.multisite_views.items():
	if us == user:
	    userviews[name] = view
    userdir = check_mk.multisite_config_dir + "/" + us
    if not os.path.exists(userdir):
	os.mkdir(userdir)
    f = file(userdir + "/views.mk", "w", 0)
    f.write(pprint.pformat(userviews) + "\n")
	    

# ----------------------------------------------------------------------
#   _____     _     _               __         _                   
#  |_   _|_ _| |__ | | ___    ___  / _| __   _(_) _____      _____ 
#    | |/ _` | '_ \| |/ _ \  / _ \| |_  \ \ / / |/ _ \ \ /\ / / __|
#    | | (_| | |_) | |  __/ | (_) |  _|  \ V /| |  __/\ V  V /\__ \
#    |_|\__,_|_.__/|_|\___|  \___/|_|     \_/ |_|\___| \_/\_/ |___/
#                                                                  
# ----------------------------------------------------------------------
# Show list of all views with buttons for editing
def page_edit_views(h, msg=None):
    global html
    html = h

    changed = False
    html.header("Edit views")
    html.write("<p>Here you can create and edit customizable <b>views</b>. A view "
	    "displays monitoring status or log data by combining filters, sortings, "
	    "groupings and other aspects.</p>")

    if msg: # called from page_edit_view() after saving
	html.message(msg)
	changed = True

    load_views()

    # Deletion of views
    delname = html.var("delete")
    if delname and html.confirm("Please confirm the deletion of the view <tt>%s</tt>" % delname):
	del html.multisite_views[(html.req.user, delname)]
	save_views(html.req.user)
	changed = True

    # Cloning of views
    try:
	cloneuser, clonename = html.var("clone").split("/")
    except:
	clonename = ""

    if clonename and html.check_transaction():
	newname = clonename + "_clone"
	n = 1
	while (html.req.user, newname) in html.multisite_views:
	    n += 1
	    newname = clonename + "_clone%d" % n
	import copy
	orig = html.multisite_views[(cloneuser, clonename)]
	clone = copy.copy(orig)
	clone["name"] = newname
	clone["title"] = orig["title"] + " (Copy)" 
	if cloneuser != html.req.user: 
	    clone["public"] = False
	html.multisite_views[(html.req.user, newname)] = clone
	save_views(html.req.user)
	load_views()
	changed = True
	
    if changed:
	html.javascript("parent.frames[0].location.reload();");

    html.write("<table class=views>\n")

    keys_sorted = html.multisite_views.keys()
    keys_sorted.sort()
    first = True
    for (owner, viewname) in keys_sorted:
	view = html.multisite_views[(owner, viewname)]
	if owner == html.req.user or view["public"]:
	    if first:
		html.write("<tr><th>Name</th><th>Title / Description</th><th>Owner</th><th>Public</th><th>linked</th><th>Datasource</th><th></th></tr>\n")
		first = False
	    html.write("<tr><td class=legend>%s</td>" % viewname)
	    html.write("<td class=content>")
	    if not view["hidden"]:
		html.write("<a href=\"view.py?view_name=%s\">%s</a>" % (viewname, view["title"]))
	    else:
		html.write(view["title"])
	    description = view.get("description")
	    if description:
		html.write("<br><div class=viewdescription>%s</div>" % description)
	    html.write("</td>")
	    if owner == "":
		ownertxt = "<i>builtin</i>"
	    else:
		ownertxt = owner
	    html.write("<td class=content>%s</td>" % ownertxt)
	    html.write("<td class=content>%s</td>" % (view["public"] and "yes" or "no"))
	    html.write("<td class=content>%s</td>" % (view["hidden"] and "yes" or "no"))
	    html.write("</td><td class=content>%s</td><td class=buttons>\n" % view["datasource"])
	    html.buttonlink("edit_views.py?clone=%s/%s" % (owner, viewname), "Clone", True)
	    if owner == html.req.user:
		html.buttonlink("edit_view.py?load_view=%s" % viewname, "Edit")
		html.buttonlink("edit_views.py?delete=%s" % viewname, "Delete!", True)
	    html.write("</td></tr>")

    html.write("<tr><td class=legend colspan=7>")
    html.begin_form("create_view", "edit_view.py") 
    html.button("create", "Create new view")
    html.write(" for datasource: ")
    html.sorted_select("datasource", [ (k, v["title"]) for k, v in multisite_datasources.items() ])
    html.write("</table>\n")
    html.end_form()
    html.footer()


def select_view(varname, only_with_hidden = False):
    choices = [("", "")]
    for name, view in html.available_views.items():
	if not only_with_hidden or len(view["hide_filters"]) > 0:
	    choices.append(("%s" % name, view["title"]))
    html.sorted_select(varname, choices, "")

# -------------------------------------------------------------------------	
#   _____    _ _ _    __     ___               
#  | ____|__| (_) |_  \ \   / (_) _____      __
#  |  _| / _` | | __|  \ \ / /| |/ _ \ \ /\ / /
#  | |__| (_| | | |_    \ V / | |  __/\ V  V / 
#  |_____\__,_|_|\__|    \_/  |_|\___| \_/\_/  
#  Edit one view
# -------------------------------------------------------------------------	
def page_edit_view(h):
    global html
    html = h
    load_views()

    view = None

    # Load existing view from disk
    viewname = html.var("load_view")
    if viewname:
	view = html.multisite_views.get((html.req.user, viewname), None)
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
	        if html.check_transaction():
		    load_views()
		    html.multisite_views[(html.req.user, view["name"])] = view
		    oldname = html.var("old_name")
		    # Handle renaming of views -> delete old entry
		    if oldname and oldname != view["name"] and (html.req.user, oldname) in html.multisite_views:
			del html.multisite_views[(html.req.user, oldname)]
		    save_views(html.req.user)
		return page_edit_views(h, "Your view has been saved.")

	except MKUserError, e:
	    html.write("<div class=error>%s</div>\n" % e.message)
	    html.add_user_error(e.varname, e.message)

    html.header("Edit view")
    html.write("<p>Edit the properties of the view or go <a href=\"edit_views.py\">back to this list of all views</a>.<br />")
    html.write("<a href=\"view.py?view_name=%s/%s\">Visit view (does not save)</a></p>" % (html.req.user, viewname))
    html.begin_form("view")
    html.hidden_field("old_name", viewname) # safe old name in case user changes it
    html.write("<table class=view>\n")

    html.write("<tr><td class=legend>Shortname for linking</td><td class=content>")
    html.text_input("view_name")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Title</td><td class=content>")
    html.text_input("view_title")
    html.write("</td></tr>\n")
    html.write("<tr><td class=legend>Description</td><td class=content>")
    html.text_area("view_description", 4)
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend>Configuration</td><td class=content>")
    html.checkbox("public")
    html.write(" make this view available for all users")
    html.write("<br />\n")
    html.checkbox("hidden")
    html.write(" hide this view from the sidebar")
    html.write("<br />\n")
    html.checkbox("mustsearch")
    html.write(" show data only on search")
    html.write("</td></tr>\n")

    # [1] Datasource (not changeable here!)
    html.write("<tr><td class=legend>1. Datasource</td><td>%s</td></tr>" % datasourcename)
    html.hidden_field("datasource", datasourcename)
    
    # [2] Layout
    html.write("<tr><td class=legend>2. Layout</td><td class=content>")
    html.sorted_select("layout", [ (k, v["title"]) for k,v in multisite_layouts.items() ])
    html.write("with column headers: \n")
    html.select("column_headers", [ ("off", "off"), ("perpage", "once per page"), ("pergroup", "once per group") ])
    html.write("</td></tr>\n")
  
    # [3] Filters 
    html.write("<tr><td class=legend>3. Filters</td><td>")
    html.write("<table class=filters>")
    html.write("<tr><th>Filter</th><th>usage</th><th>hardcoded settings</th><th>HTML variables</th></tr>\n")
    allowed_filters = filters_allowed_for_datasource(datasourcename)
    # sort filters according to title
    s = [(filt.title, fname, filt) for fname, filt in allowed_filters.items()]
    s.sort()
    for title, fname, filt in s:
	html.write("<tr>")
	html.write("<td class=title>%s" % title)
	if filt.comment:
	    html.write("<br><div class=filtercomment>%s</div>" % filt.comment)
	html.write("</td>")
	html.write("<td class=usage>")
	html.sorted_select("filter_%s" % fname, 
		[("off", "Don't use"), 
		("show", "Show to user"), 
		("hide", "Use for linking"), 
		("hard", "Hardcode")], 
		"", "filter_activation")
	html.write("</td><td class=widget>")
	filt.display()
	html.write("</td>")
	html.write("<td><tt>")
	html.write(" ".join(filt.htmlvars))
	html.write("</tt></td>")
	html.write("</tr>\n")
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
	    else:
		html.write("<i> with link to </i>")
		select_view("%slink_%d" % (var_prefix, n))
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

# Called by edit function in order to prefill HTML form
def load_view_into_html_vars(view):
    # view is well formed, not checks neccessary
    html.set_var("view_title",       view["title"])
    html.set_var("view_description", view.get("description", ""))
    html.set_var("view_name",        view["name"])
    html.set_var("datasource",       view["datasource"])
    html.set_var("column_headers",   view.get("column_headers", "off"))
    html.set_var("layout",           view["layout"])
    html.set_var("public",           view["public"] and "on" or "")
    html.set_var("hidden",           view["hidden"] and "on" or "")
    html.set_var("mustsearch",       view["mustsearch"] and "on" or "")

    # [3] Filters
    for name, filt in multisite_filters.items():
	if name in view["show_filters"]:
	    html.set_var("filter_%s" % name, "show")
	elif name in view["hard_filters"]:
	    html.set_var("filter_%s" % name, "hard")
	elif name in view["hide_filters"]:
	    html.set_var("filter_%s" % name, "hide")

    for varname, value in view["hard_filtervars"]:
	if not html.has_var(varname):
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
    for name, viewname in view["group_painters"]:
	html.set_var("group_%d" % n, name)
	if viewname:
	    html.set_var("group_link_%d" % n, viewname)
	n += 1

    # [6] Columns
    n = 1
    for name, viewname in view["painters"]:
	html.set_var("col_%d" % n, name)
	if viewname:
	    html.set_var("col_link_%d" % n, viewname)
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
    public     = html.var("public", "") != ""
    hidden     = html.var("hidden", "") != ""
    mustsearch = html.var("mustsearch", "") != ""
    column_headers = html.var("column_headers")
    show_filternames = []
    hide_filternames = []
    hard_filternames = []
    hard_filtervars = []

    for fname, filt in multisite_filters.items():
	usage = html.var("filter_%s" % fname)
	if usage == "show":
	    show_filternames.append(fname)
	elif usage == "hide":
	    hide_filternames.append(fname)
	elif usage == "hard":
	    hard_filternames.append(fname)
	if usage in [ "show", "hard" ]:
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
	viewname = html.var("group_link_%d" % n)
	if pname:
	    if viewname not in  html.available_views:
		viewname = None
	    group_painternames.append((pname, viewname))

    painternames = []
    for n in range(1, max_display_columns+1):
	pname = html.var("col_%d" % n)
	viewname = html.var("col_link_%d" % n)
	if pname:
	    if viewname not in  html.available_views:
		viewname = None
	    painternames.append((pname, viewname))
  
    return { 
	"name"            : name,
	"owner"           : html.req.user,
	"title"           : title,
	"description"     : html.var("view_description", ""),
	"datasource"      : datasourcename,
	"public"          : public,
	"hidden"          : hidden,
	"mustsearch"      : mustsearch,
	"layout"          : layoutname,
	"column_headers"  : column_headers,
	"show_filters"    : show_filternames,
	"hide_filters"    : hide_filternames,
	"hard_filters"    : hard_filternames,
	"hard_filtervars" : hard_filtervars,
	"sorters"         : sorternames,
	"group_painters"  : group_painternames,
	"painters"        : painternames
    }


# ---------------------------------------------------------------------
#  __     ___                       _               
#  \ \   / (_) _____      __ __   _(_) _____      __
#   \ \ / /| |/ _ \ \ /\ / / \ \ / / |/ _ \ \ /\ / /
#    \ V / | |  __/\ V  V /   \ V /| |  __/\ V  V / 
#     \_/  |_|\___| \_/\_/     \_/ |_|\___| \_/\_/  
#                                                   
# ---------------------------------------------------------------------
# Show one view filled with data
def page_view(h):
    global html
    html = h
    load_views()
    view_name = html.var("view_name")
    view = html.available_views.get(view_name)
    if not view:
	raise MKGeneralException("No view defined with the name '%s'." % view_name)

    show_view(view, True)
    html.footer()

# Display view with real data. This is *the* function everying
# is about.
def show_view(view, show_heading = False):
    # [1] Datasource
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]

    # [2] Layout
    layout = multisite_layouts[view["layout"]]
    
    # [3] Filters
    show_filters = [ multisite_filters[fn] for fn in view["show_filters"] ]
    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    hard_filters = [ multisite_filters[fn] for fn in view["hard_filters"] ]
    for varname, value in view["hard_filtervars"]:
	if not html.var("filled_in"): # shown filters are set, if form is fresh
	    html.set_var(varname, value)

    filterheaders = ""
    only_sites = None
    for filt in show_filters + hide_filters + hard_filters:
	header = filt.filter(tablename)
	if header.startswith("Sites:"):
	    only_sites = header.strip().split(" ")[1:]
	else:
	    filterheaders += header

    query = filterheaders + view.get("add_headers", "")
   
    # Fetch data. Some views show data only after pressing [Search]
    if (not view["mustsearch"]) or html.var("search"):
	columns, rows = query_data(datasource, query, only_sites)
    else:
	columns, rows = [], []

    # [4] Sorting
    sorters = [ (multisite_sorters[sn], reverse) for sn, reverse in view["sorters"] ]
    sort_data(rows, sorters)

    # [5] Grouping
    group_painters = [ (multisite_painters[n], v) for n, v in view["group_painters"] ]
    group_columns = needed_group_columns(group_painters)

    # [6] Columns
    painters = [ (multisite_painters[n], v) for n, v in view["painters"] ]

    # Show heading
    if show_heading:
	html.header(view_title(view))
        show_site_header(html)

    if view["owner"] == html.req.user:
	html.write("<a href=\"edit_view.py?load_view=%s\">Edit this view</a> " % view["name"])

    # Kontext links
    show_context_links(view, show_filters + hide_filters)

    # Actions
    has_done_actions = False
    if len(rows) > 0:
	if html.do_actions() and html.transaction_valid(): # submit button pressed, no reload
	    try:
		has_done_actions = do_actions(tablename, rows)
	    except MKUserError, e:
		html.show_error(e.message)
		html.add_user_error(e.varname, e.message)
		show_action_form(tablename)

        else:
	    show_action_form(tablename)

    if has_done_actions:
	html.write("<a href=\"%s\">Back to search results</a>" % html.makeuri([]))
    else:
        layout["render"]((columns, rows), view, show_filters, group_columns, group_painters, painters)

def view_title(view):
    extra_titles = [ ]
    datasource = multisite_datasources[view["datasource"]]
    tablename = datasource["table"]
    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    for filt in hide_filters:
	heading = filt.heading_info(tablename)
	if heading:
	    extra_titles.append(heading)
    return view["title"] + " " + ", ".join(extra_titles)

def show_context_links(thisview, active_filters):
    # compute list of html variable used actively by hidden or show
    # filters.
    active_filter_vars = set([])
    for filt in active_filters:
	for var in filt.htmlvars:
	   if html.has_var(var) and var not in active_filter_vars:
	       active_filter_vars.add(var)
	       
    first = True
    for name, view in html.available_views.items():
	if view == thisview:
	    continue
	hidden_filternames = view["hide_filters"]
	used_contextvars = []
	skip = False
	for fn in hidden_filternames:
	    filt = multisite_filters[fn]
	    contextvars = filt.htmlvars
	    # now extract those variables which are honored by this
	    # view, regardless if used by hardcoded, shown or hidden filters.
	    for var in contextvars:
		if var not in active_filter_vars:
		    skip = var
		    break
	    used_contextvars += contextvars
	    if skip:
# html.write("%s geht nicht, weil %s fehlt. " % (fn, var))
		break
	if skip:
# html.write("View %s/%s geht also nicht<br>" % (user, name))
	    continue
	
	# add context link to this view    
	if len(used_contextvars) > 0:
	    if first:
		html.write("<div class=contextlinks><h2>Contextlinks</h2>\n")
		first = False
	    vars_values = [ (var, html.var(var)) for var in set(used_contextvars) ]
	    html.write("<a href=\"%s\">%s</a><br>" % \
		    (html.makeuri_contextless(vars_values + [("view_name", name)]), view_title(view)))

    if not first:
	html.write("</div>\n")
	


def needed_group_columns(painters):
    columns = []
    for p, linkview in painters:
	columns += p["columns"] 
    return columns


# Retrieve data via livestatus, convert into list of dicts,
# prepare row-function needed for painters
def query_data(datasource, add_headers, only_sites = None):
    tablename = datasource["table"]
    query = "GET %s\n" % tablename
    columns = datasource["columns"]
    query += "Columns: %s\n" % " ".join(datasource["columns"])
    query += add_headers
    html.live.set_prepend_site(True)
    if check_mk.multiadmin_debug:
	html.write("<div class=message><pre>%s</pre></div>\n" % query)
    
    if only_sites:
	html.live.set_only_sites(only_sites)
    data = html.live.query(query)
    html.live.set_only_sites(None)
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

# -----------------------------------------------------------------------------
#         _        _   _
#        / \   ___| |_(_) ___  _ __  ___
#       / _ \ / __| __| |/ _ \| '_ \/ __|
#      / ___ \ (__| |_| | (_) | | | \__ \
#     /_/   \_\___|\__|_|\___/|_| |_|___/
#
# -----------------------------------------------------------------------------

def show_action_form(tablename):
    if not check_mk.is_allowed_to_act(html.req.user):
	return

    html.begin_form("actions")
    display = html.do_actions()
    toggle_texts = { False: 'Show command form', True: 'Hide command form' }
    html.write("<a id=toggle_actions href=\"#\" onclick=\"toggle_actions(this, '%s', '%s')\">%s</a>" % \
	    (toggle_texts[False], toggle_texts[True], toggle_texts[display]))
    html.hidden_field("_do_actions", "yes")
    html.hidden_field("actions", "yes")
    html.hidden_fields() # set all current variables, exception action vars

    html.write("<table %s id=actions class=form id=actions>\n" % (display and " " or 'style="display: none"'))

    html.write("<tr><td class=legend>Notifications</td>\n"
               "<td class=content>\n"
               "<input type=submit name=_enable_notifications value=\"Enable\"> &nbsp; "
               "<input type=submit name=_disable_notifications value=\"Disable\"> &nbsp; "
               "</td></tr>\n")

    html.write("<tr><td class=legend>Active checks</td>\n"
               "<td class=content>\n"
               "<input type=submit name=_enable_checks value=\"Enable\"> &nbsp; "
               "<input type=submit name=_disable_checks value=\"Disable\"> &nbsp; "
               "<input type=submit name=_resched_checks value=\"Reschedule next check now\"></td></tr>\n"
               "</td></tr>\n")

    html.write("<tr><td rowspan=2 class=legend>Acknowledge</td>\n")
    html.write("<td class=content><input type=submit name=_acknowledge value=\"Acknowledge\"> &nbsp; "
               "<input type=submit name=_remove_ack value=\"Remove Acknowledgement\"></td></tr><tr>"
               "<td class=content><div class=textinputlegend>Comment:</div>")
    html.text_input("_comment")
    html.write("</td></tr>\n")

    html.write("<tr><td class=legend rowspan=3>Schedule Downtimes</td>\n"
               "<td class=content>\n"
               "<input type=submit name=_down_2h value=\"2 hours\"> "
               "<input type=submit name=_down_today value=\"Today\"> "
               "<input type=submit name=_down_week value=\"This week\"> "
               "<input type=submit name=_down_month value=\"This month\"> "
               "<input type=submit name=_down_year value=\"This year\"> "
               " &nbsp; - &nbsp;"
               "<input type=submit name=_down_remove value=\"Remove all\"> "
               "</tr><tr>"
               "<td class=content>"
               "<input type=submit name=_down_custom value=\"Custom time range\"> &nbsp; ")
    html.datetime_input("_down_from", time.time())
    html.write("&nbsp; to &nbsp;")
    html.datetime_input("_down_to", time.time() + 7200)
    html.write("</td></tr>")
    html.write("<tr><td class=content><div class=textinputlegend>Comment:</div>\n")
    html.text_input("_down_comment")
    html.write("</td></tr>")
    html.write("</table></form>\n")

def nagios_action_command(tablename, dataset):
    host = dataset["host_name"]
    descr = dataset.get("service_description") # not available on hosts
    down_from = time.time()
    down_to = None
    if tablename == "hosts":
	spec = host
	cmdtag = "HOST"
	prefix = "host_"
    elif tablename == "services":
	spec = "%s;%s" % (host, descr)
	cmdtag = "SVC"
	prefix = "service_"
    else:
	raise MKInternalError("Sorry, no actions possible on table %s" % tablename)

    if html.var("_enable_notifications"):
        command = "ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec
        title = "<b>enable notifications</b> for"

    elif html.var("_disable_notifications"):
        command = "DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec
        title = "<b>disable notifications</b> for"

    elif html.var("_enable_checks"):
        command = "ENABLE_" + cmdtag + "_CHECK;%s" % spec 
        title = "<b>enable active checks</b> of"

    elif html.var("_disable_checks"):
        command = "DISABLE_" + cmdtag + "_CHECK;%s" % spec
        title = "<b>disable active checks</b> of"

    elif html.var("_resched_checks"):
        command = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(time.time()))
        title = "<b>reschedule an immediate check</b> of"

    elif html.var("_acknowledge"):
        comment = html.var("_comment")
        if not comment:
            raise MKUserError("_comment", "You need to supply a comment.")
        command = "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;2;1;0;%s" % \
                  (spec, html.req.user) + ";" + html.var("_comment")
        title = "<b>acknowledge the problems</b> of"

    elif html.var("_remove_ack"):
        command = "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec
        title = "<b>remove acknowledgements</b> from"

    elif html.var("_down_2h"):
        down_to = down_from + 7200
        title = "<b>schedule an immediate 2-hour downtime</b> on"

    elif html.var("_down_today"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until 24:00:00</b> on"

    elif html.var("_down_week"):
        br = time.localtime(down_from)
        wday = br.tm_wday
        days_plus = 6 - wday
        down_to = time.mktime((br.tm_year, br.tm_mon, br.tm_mday, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        down_to += days_plus * 24 * 3600
        title = "<b>schedule an immediate downtime until sunday night</b> on"

    elif html.var("_down_month"):
        br = time.localtime(down_from)
        new_month = br.tm_mon + 1
        if new_month == 13:
            new_year = br.tm_year + 1
            new_month = 1
        else:
            new_year = br.tm_year
        down_to = time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, br.tm_isdst)) 
        title = "<b>schedule an immediate downtime until end of month</b> on"

    elif html.var("_down_year"):
        br = time.localtime(down_from)
        down_to = time.mktime((br.tm_year, 12, 31, 23, 59, 59, 0, 0, br.tm_isdst)) + 1
        title = "<b>schedule an immediate downtime until end of %d</b> on" % br.tm_year

    elif html.var("_down_custom"):
        down_from = html.get_datetime_input("down_from")
        down_to   = html.get_datetime_input("down_to")
        title = "<b>schedule a downtime from %s to %s</b> on " % (
            time.asctime(time.localtime(down_from)),
            time.asctime(time.localtime(down_to)))

    elif html.var("_down_remove"):
        downtime_ids = []
	for id in dataset[prefix + "downtimes"]:
	   if id != "":
	       downtime_ids.append(int(id))
        commands = []
        for dtid in downtime_ids:
            commands.append("[%d] DEL_%s_DOWNTIME;%d\n" % (int(time.time()), cmdtag, dtid))
        title = "<b>remove all scheduled downtimes</b> of "
        return title, commands

    else:
        raise MKUserError(None, "Sorry. This command is not implemented.")

    if down_to:
        comment = html.var("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", "You need to supply a comment for your downtime.")
        command = (("SCHEDULE_" + cmdtag + "_DOWNTIME;%s;" % spec) \
                   + ("%d;%d;1;0;0;%s;" % (int(down_from), int(down_to), html.req.user)) \
                   + comment)
                  
    nagios_command = ("[%d] " % int(time.time())) + command + "\n"
    return title, [nagios_command]

def do_actions(tablename, rows):
    if not check_mk.is_allowed_to_act(html.req.user):
       html.show_error("You are not allowed to perform actions. If you think this is an error, "
             "please ask your administrator to add your login to <tt>multiadmin_action_users</tt> "
	     "in <tt>main.mk</tt>")
       return False # no actions done

    command = None
    title = nagios_action_command(tablename, rows[0])[0] # just get the title
    if not html.confirm("Do you really want to %s the following %d %s?" % (title, len(rows), tablename)):
	return False # no actions done

    count = 0
    for row in rows:
        title, nagios_commands = nagios_action_command(tablename, row)
	for command in nagios_commands:
	    html.live.command(command, row["site"])
	    count += 1

    if command:
	html.message("Successfully sent %d commands to Nagios. The last one was: <pre>%s</pre>" % (count, command))
    elif count == 0:
	html.message("No matching service. No command sent.")
    return True

def get_context_link(user, viewname):
    if viewname in html.available_views:
        return "view.py?view_name=%s" % viewname
    else:
	return None
