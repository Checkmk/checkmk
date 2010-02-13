import check_mk, livestatus, htmllib, time, os, re, pprint, time
from lib import *
from pagefunctions import *

multisite_datasources = {}
multisite_filters     = {}
multisite_layouts     = {}
multisite_painters    = {}
multisite_sorters     = {}
multisite_builtin_views = {}
multisite_views       = {}

plugins_path = check_mk.web_dir + "/plugins/views"
for fn in os.listdir(plugins_path):
    if fn.endswith(".py"):
	execfile(plugins_path + "/" + fn)

max_display_columns   = 10
max_group_columns     = 3
max_sort_columns      = 4

def load_views(**args):
    override_builtins = args.get("override_builtins", None)
    global multisite_views
    multisite_views = multisite_builtin_views
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
		    view["owner"] = user
		    view["name"] = name
		    multisite_views[(user, name)] = view
	except IOError:
	     pass
	except SyntaxError, e:
	     raise MKGeneralException("Cannot load views from %s/views.mk: %s" % (dirpath, e))

    # Remove builtins, if user has same view and override_builtins is True
    if override_builtins:
	for (user, name), view in multisite_views.items():
	    if user == override_builtins and ("", name) in multisite_views:
		del multisite_views[("", name)]


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
    if view["owner"] == html.req.user:
	html.write("<a href=\"edit_view.py?load_view=%s\">Edit this view</a>" % view["name"])

    html.footer()

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
	del multisite_views[(html.req.user, delname)]
	save_views(html.req.user)
	changed = True

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
	changed = True
	
    if changed:
	html.javascript("parent.frames[0].location.reload();");

    html.write("<table class=views>\n")

    keys_sorted = multisite_views.keys()
    keys_sorted.sort()
    first = True
    for (owner, viewname) in keys_sorted:
	view = multisite_views[(owner, viewname)]
	if owner == html.req.user or view["public"]:
	    if first:
		html.write("<tr><th>Name</th><th>Title</th><th>Owner</th><th>Public</th><th>hidden</th><th>Datasource</th><th></th></tr>\n")
		first = False
	    html.write("<tr><td class=legend>%s</td>" % viewname)
	    html.write("<td class=content><a href=\"view.py?view_name=%s/%s\">%s</a>" % (owner, viewname, view["title"]))
	    html.write("<td class=content>%s</td>" % owner)
	    html.write("<td class=content>%s</td>" % (view["public"] and "yes" or "no"))
	    html.write("<td class=content>%s</td>" % (view["hidden"] and "yes" or "no"))
	    html.write("</td><td class=content>%s</td><td class=buttons>\n" % view["datasource"])
	    html.buttonlink("edit_views.py?clone=%s/%s" % (owner, viewname), "Clone")
	    if owner == html.req.user:
		html.buttonlink("edit_view.py?load_view=%s" % viewname, "Edit")
		html.buttonlink("edit_views.py?delete=%s" % viewname, "Delete!")
	    html.write("</td></tr>")

    html.write("<tr><td class=legend colspan=7>")
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
    html.write("<p>Edit the properties of the view or go <a href=\"edit_views.py\">back to this list of all views</a>.<br />")
    html.write("<a href=\"view.py?view_name=%s/%s\">Visit view (does not save)</a></p>" % (html.req.user, viewname))
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
    html.write("<br />\n")
    html.checkbox("hidden")
    html.write(" hide this view from the sidebar")
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
	html.sorted_select("filter_%s" % fname, [("off", "Don't use"), ("show", "Show to user"), ("hide", "Hide but use"), ("hard", "Hardcode")], "", "filter_activation")
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
    html.set_var("hidden",     view["hidden"] and "on" or "")

    # [3] Filters
    for name, filt in multisite_filters.items():
	if name in view["show_filters"]:
	    html.set_var("filter_%s" % name, "show")
	elif name in view["hard_filters"]:
	    html.set_var("filter_%s" % name, "hard")
	elif name in view["hide_filters"]:
	    html.set_var("filter_%s" % name, "hide")

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
    hidden = html.var("hidden", "") != ""
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
	"owner"           : html.req.user,
	"title"           : title,
	"datasource"      : datasourcename,
	"public"          : public,
	"hidden"          : hidden,
	"layout"          : layoutname,
	"show_filters"    : show_filternames,
	"hide_filters"    : hide_filternames,
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
    hide_filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
    hard_filters = [ multisite_filters[fn] for fn in view["hard_filters"] ]
    for varname, value in view["hard_filtervars"]:
	html.set_var(varname, value)
    filterheaders = "".join(f.filter(tablename) for f in show_filters + hide_filters + hard_filters)
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

    # Actions
    has_done_actions = False
    if len(rows) > 0:
	if html.do_actions(): # submit button pressed
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
    if check_mk.multiadmin_debug:
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

def nagios_action_command(tablename, service):
    host = service["host_name"]
    descr = service.get("service_description") # not available on hosts
    down_from = time.time()
    down_to = None
    if tablename == "hosts":
	spec = host
	cmdtag = "HOST"
    elif tablename == "services":
	spec = "%s;%s" % (host, descr)
	cmdtag = "SVC"
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
	for id in service["service_downtimes"]:
	   if id != "":
	       downtime_ids.append(int(id))
        commands = []
        for dtid in downtime_ids:
            commands.append("[%d] DEL_" + cmdtag + "_DOWNTIME;%d\n" % (int(time.time()), dtid))
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
       return
    count = 0
    pipe = file(html.req.defaults["nagios_command_pipe_path"], "w")
    command = None
    for row in rows:
        title, nagios_commands = nagios_action_command(tablename, row)
        confirms = html.confirm("Do you really want to %s the following %d %s?" % (title, len(rows), tablename))
        if not confirms:
	    return False
        for command in nagios_commands:
            pipe.write(command)
            count += 1
    if command:
	html.message("Successfully sent %d commands to Nagios. The last one was: <pre>%s</pre>" % (count, command))
    else:
	html.message("No matching service. No command sent.")
    return True

def get_context_link(user, viewname):
    if multisite_views == {}:
	load_views()
    # Try to get view of user. If not available, get builtin view
    # with that name
    if (user, viewname) not in multisite_views and ("", viewname) in multisite_views:
	user = ""
    return "view.py?view_name=%s/%s" % (user, viewname)
