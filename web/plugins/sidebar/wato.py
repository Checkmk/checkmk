#!/usr/bin/python

import config

def render_wato_files():
    if not config.may("use_wato"):
        html.write("You are not allowed to use Check_MK's web configuration GUI.")
    elif len(config.config_files)== 0:
        html.write("No configuration files are defined.<br>"
	"Please set the variable <tt>config_files</tt><br>"
        "in <tt>multisite.mk</tt>.")

    else:
        if config.is_multisite():
            sitenames = config.sites.keys()
            sitenames.sort()
            for sitename in sitenames:
                site = config.sites[sitename]
                state = html.site_status[sitename]["state"]
                if state != "disabled":
                    html.write("<h3>%s</h3>\n" % site["alias"])
                    ajax_url = site["url_prefix"] + "check_mk/ajax_wato_files.py?site=" + sitename
                    html.javascript("document.write(get_url_sync('%s'));" % ajax_url)
        else:
            ajax_wato_files(html)

def ajax_wato_files(h):
    global html
    html = h
    sitename = html.var('site', '')
    if config.may("use_wato"):
        for filename, title, roles in config.config_files:
            if config.role in roles:
                if sitename:
                    bulletlink(title, "/%s/check_mk/wato.py?filename=%s" % (sitename, filename))
                else:
                    bulletlink(title, "wato.py?filename=%s" % filename)


sidebar_snapins["wato"] = {
    "title" : "Check_MK Web Administration Tool",
    "description" : "WATO - the Web Administration Tool of Check_MK - manage hosts to be monitored without access to the command line",
    "author" : "Mathias Kettner",
    "render" : render_wato_files,
    "allowed" : [ "admin", "user" ],
}
        
    
