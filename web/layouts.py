
##################################################################################
# Layouts
##################################################################################

def show_filter_form(filters):
    if len(filters) > 0:
	html.begin_form("filter")
	html.hidden_fields()
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


def render_grouped_list(data, filters, group_columns, group_painters, painters, num_columns):
    show_filter_form(filters)
    columns, rowfunction, rows = data
    html.write("<table class=services>\n")
    last_group = None
    trclass = None
    column = 1

    for row in rows:
	# Show group header, if a new group begins. But only if grouping
        # is activated
        if len(group_painters) > 0:
	    this_group = [ row[c] for c in group_columns ]
	    if this_group != last_group:
		if column != 1: # not a the beginning of a new line
                    html.write("<td></td>" * (len(painters) * (num_columns + 1 - column)))
		    html.write("</tr>\n")
		    column = 1

		# paint group header
		html.write("<tr class=groupheader>")
		html.write("<td colspan=%d><table><tr>" % len(painters))
		for p in group_painters:
		    html.write(p["paint"](rowfunction(p, row)))
		html.write("</tr></table></td></tr>\n")
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
		state = row.get("state", 0)
	    else:
		state = 0
	    if trclass == "odd":
		trclass = "even"
	    else:
		trclass = "odd"
	    html.write("<tr class=%s%d>" % (trclass, state))

        for p in painters:
	    html.write(p["paint"](rowfunction(p, row)))
	    html.write("\n")
	column += 1
    
    # complete half line, if any
    html.write("<td></td>" * (len(painters) * (num_columns + 1 - column)))

    html.write("</tr>\n")
    html.write("<table>\n")

multisite_layouts["table"] = { 
    "title"  : "table, supports grouping",
    "render" : lambda a,b,c,d,e: render_grouped_list(a,b,c,d,e,1),
    "group"  : True
}
multisite_layouts["table_2c"] = { 
    "title"  : "2-column table, supports grouping",
    "render" : lambda a,b,c,d,e: render_grouped_list(a,b,c,d,e,2),
    "group"  : True
}
multisite_layouts["table_3c"] = { 
    "title"  : "3-column table, supports grouping",
    "render" : lambda a,b,c,d,e: render_grouped_list(a,b,c,d,e,3),
    "group"  : True
}
multisite_layouts["table_4c"] = { 
    "title"  : "4-column table, supports grouping",
    "render" : lambda a,b,c,d,e: render_grouped_list(a,b,c,d,e,4),
    "group"  : True
}

