import check_mk

# TODO: Remove this. It is replace by side bar plugin?
# Or only show this, if sidebar snapin is not used?
def show_site_header(html):
    return False

    if check_mk.is_multisite():
	html.write("<table class=siteheader><tr>")
	for sitename in check_mk.sites():
	    site = check_mk.site(sitename)
	    state = html.site_status[sitename]["state"]
	    if state == "disabled":
		switch = "on"
	    else:
		switch = "off"
	    uri = html.makeuri([("_site_switch", sitename + ":" + switch)])
	    if check_mk.multiadmin_use_siteicons:
		html.write("<td>")
		add_site_icon(html, sitename)
		html.write("</td>")
	    html.write("<td class=%s>" % state)
	    html.write("<a href=\"%s\">%s</a></td>" % (uri, site["alias"]))
	html.write("</tr></table>\n")

def add_site_icon(html, sitename):
    if check_mk.multiadmin_use_siteicons:
	html.write("<img class=siteicon src=\"icons/site-%s-24.png\"> " % sitename)
        return True
    else:
	return False

def site_selector(html, htmlvar, enforce = True):
    if enforce:
        choices = []
    else:
	choices = [("","")]
    for sitename, state in html.site_status.items():
	if state["state"] == "online":
	    choices.append((sitename, check_mk.site(sitename)["alias"]))
    html.sorted_select(htmlvar, choices)
