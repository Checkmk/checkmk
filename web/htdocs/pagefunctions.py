import check_mk


def show_site_header(html):
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

