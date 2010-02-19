 
##################################################################################
# Layouts
##################################################################################

def paint(p, row):
    painter, linkview = p
    tdclass, content = painter["paint"](row)
    # Create contextlink to other view
    if linkview:
	view = html.available_views.get(linkview)
	if view:
	    filters = [ multisite_filters[fn] for fn in view["hide_filters"] ]
	    filtervars = []
	    for filt in filters:
		filtervars += filt.variable_settings(row)

	    uri = html.makeuri_contextless([("view_name", linkview)] + filtervars)
	    content = "<a href=\"%s\">%s</a>" % (uri, content)

    if tdclass:
	html.write("<td class=\"%s\">%s</td>\n" % (tdclass, content))
    else:
	html.write("<td>%s</td>" % content)

def paint_header(p):
    painter, linkview = p
    t = painter.get("short", painter["title"])
    html.write("<th>%s</th>" % t)
	
def show_filter_form(filters):
    if len(filters) > 0 and not html.do_actions():
	html.begin_form("filter")
	html.write("<table class=form id=filter>\n")
        # sort filters according to title
	s = [(f.title, f) for f in filters]
	s.sort()
	for title, f in s:
	    html.write("<tr><td class=legend>%s</td>" % title)
	    html.write("<td class=content>")
	    f.display()
	    html.write("</td></tr>\n")
	html.write("<tr><td class=legend></td><td class=content>")
	html.button("search", "Search", "submit")
	html.write("</td></tr>\n")
	html.write("</table>\n")
	html.hidden_fields()
	html.end_form()

# -------------------------------------------------------------------------
#    ____  _             _      
#   / ___|(_)_ __   __ _| | ___ 
#   \___ \| | '_ \ / _` | |/ _ \
#    ___) | | | | | (_| | |  __/
#   |____/|_|_| |_|\__, |_|\___|
#                  |___/        
# -------------------------------------------------------------------------
def render_single_dataset(data, view, filters, group_columns, group_painters, painters, num_columns):
    columns, rows = data
    # I'm expecting only one row
    for row in rows:
	html.write("<table class=dataset>\n")
	for p in painters:
	    painter, link = p
	    html.write("<tr><td class=left>%s</td>" % painter["title"])
	    paint(p, row)
	    html.write("</tr>\n")
	html.write("<table>\n")

# -------------------------------------------------------------------------
#    ____                    _ 
#   | __ )  _____  _____  __| |
#   |  _ \ / _ \ \/ / _ \/ _` |
#   | |_) | (_) >  <  __/ (_| |
#   |____/ \___/_/\_\___|\__,_|
#                              
# -------------------------------------------------------------------------
def render_grouped_boxes(data, view, filters, group_columns, group_painters, painters, num_columns):
    show_filter_form(filters)
    columns, rows = data
    # N columns. Each should contain approx the same number of entries
    groups = []
    last_group = None
    for row in rows:
	this_group = [ row[c] for c in group_columns ]
	if this_group != last_group:
	    last_group = this_group
	    current_group = []
	    groups.append((this_group, current_group))
	current_group.append(row)

    def height_of(groups):
	# compute total space needed. I count the group header like two rows.
	return sum([ len(rows) for header, rows in groups ]) + 2 * len(groups)

    # Create empty columns
    columns = [ ]
    for x in range(0, num_columns):
	columns.append([])
    
    # First put everything into the first column
    for group in groups:
	columns[0].append(group)

    # shift from src to dst, if usefull
    def balance(src, dst):
	if len(src) == 0: 
	    return False
	hsrc = height_of(src)
	hdst = height_of(dst)
	shift = len(src[-1][1]) + 2
	if max(hsrc, hdst) > max(hsrc - shift, hdst + shift):
	    dst[0:0] = [ src[-1] ]
	    del src[-1]
	    return True
	return False

    # Shift from left to right as long as usefull
    did_something = True
    while did_something:
        did_something = False
	for i in range(0, num_columns - 1):
	    if balance(columns[i], columns[i+1]):
		did_something = True
    

    # render one group
    def render_group(header, rows, paintheader):
	html.write("<table class=services><tr class=groupheader>")
	html.write("<td colspan=%d><table><tr>" % len(painters))
	first = True
	for p in group_painters:
	    if first:
		first = False
	    else:
		html.write("<td>,</td>")
	    paint(p, rows[0])
		
	html.write("</tr></table></td></tr>\n")
	trclass = None

	# paint table headers, if configured
	if paintheader:
	    html.write("<tr>")
	    for p in painters:
		paint_header(p)
	    html.write("</tr>")

	for row in rows:
	    if trclass == "odd":
		trclass = "even"
	    else:
		trclass = "odd"
	    state = row.get("service_state", row.get("host_state", 0))
	    html.write("<tr class=%s%d>" % (trclass, state))
	    for p in painters:
		paint(p, row)
	    html.write("</tr>\n")

	html.write("</table>\n")

    # render table
    if view.get("column_headers") == "perpage":
	headerswitch = 1
    elif view.get("column_headers") == "pergroup":
	headerswitch = -1
    else:
	headerswitch = 0

    html.write("<table class=boxlayout><tr>")
    for column in columns:
	html.write("<td class=boxcolumn>")
	for header, rows in column:
	    if headerswitch:
		paintheader = True
		headerswitch -= 1
	    else:
		paintheader = False
	    render_group(header, rows, paintheader)
        html.write("</td>")
    html.write("</tr></table>\n")


# -------------------------------------------------------------------------
#    _____     _     _      
#   |_   _|_ _| |__ | | ___ 
#     | |/ _` | '_ \| |/ _ \
#     | | (_| | |_) | |  __/
#     |_|\__,_|_.__/|_|\___|
#                           
# ------------------------------------------------------------------------
def render_grouped_list(data, view, filters, group_columns, group_painters, painters, num_columns):
    show_filter_form(filters)
    columns, rows = data
    html.write("<table class=services>\n")
    last_group = None
    trclass = None
    column = 1

    def show_header_line():
        html.write("<tr>")
	for n in range(1, num_columns + 1):
	    if n > 1:
		html.write("<th class=tablegap></th>\n")
	    for p in painters:
		paint_header(p)
	html.write("</tr>\n")

    if view.get("column_headers") == "perpage":
	show_header_line()

    for row in rows:
	# Show group header, if a new group begins. But only if grouping
        # is activated
        if len(group_painters) > 0:
	    this_group = [ row[c] for c in group_columns ]
	    if this_group != last_group:
		if column != 1: # not a the beginning of a new line
		    html.write("</tr>\n")
		    column = 1

		# paint group header
		html.write("<tr class=groupheader>")
		html.write("<td class=groupheader colspan=%d><table><tr>" % (len(painters) * num_columns + (num_columns - 1)))
		first = True
		for p in group_painters:
		    if first:
			first = False
		    else:
			html.write("<td>,</td>")
		    paint(p, row)
		html.write("</tr></table></td></tr>\n")
		if view.get("column_headers") == "pergroup":
		    show_header_line()
		trclass = "even"
		last_group = this_group

	# Should we wrap over to a new line?
	if column >= num_columns + 1:
            html.write("</tr>\n")
	    column = 1

	# At the beginning of the line? Beginn new line
	if column == 1:
	    # In one-column layout we use the state of the service
	    # or host - if available - to color the complete line
	    if num_columns == 1:
		# render state, if available through whole tr
		state = row.get("service_state", 0)
	    else:
		state = 0
	    if trclass == "odd":
		trclass = "even"
	    else:
		trclass = "odd"
	    html.write("<tr class=%s%d>" % (trclass, state))

	else: # Insert spacing
	    html.write("<td class=tablegap></td>")

        for p in painters:
	    paint(p, row)
	column += 1
    
    html.write("</tr>\n")
    html.write("<table>\n")

multisite_layouts["dataset"] = { 
    "title"  : "single dataset",
    "render" : lambda a,v,b,c,d,e: render_single_dataset(a,v,b,c,d,e,1),
    "group"  : False
}
multisite_layouts["table"] = { 
    "title"  : "table",
    "render" : lambda a,v,b,c,d,e: render_grouped_list(a,v,b,c,d,e,1),
    "group"  : True
}
multisite_layouts["table_2c"] = { 
    "title"  : "table with 2 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_list(a,v,b,c,d,e,2),
    "group"  : True
}
multisite_layouts["table_3c"] = { 
    "title"  : "table with 3 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_list(a,v,b,c,d,e,3),
    "group"  : True
}
multisite_layouts["table_4c"] = { 
    "title"  : "table with 4 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_list(a,v,b,c,d,e,4),
    "group"  : True
}
multisite_layouts["boxed_2"] = { 
    "title"  : "Balanced boxes in 2 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_boxes(a,v,b,c,d,e,2),
    "group"  : True
}
multisite_layouts["boxed_3"] = { 
    "title"  : "Balanced boxes in 3 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_boxes(a,v,b,c,d,e,3),
    "group"  : True
}
multisite_layouts["boxed_4"] = { 
    "title"  : "Balanced boxes in 4 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_boxes(a,v,b,c,d,e,4),
    "group"  : True
}
multisite_layouts["boxed_5"] = { 
    "title"  : "Balanced boxes in 5 columns",
    "render" : lambda a,v,b,c,d,e: render_grouped_boxes(a,v,b,c,d,e,5),
    "group"  : True
}
