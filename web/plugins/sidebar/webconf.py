#!/usr/bin/python

import config

def render_webconf_files():
    if not config.may("use_webconf"):
        html.write("You are not allowed to use Check_MK's web configuration GUI.")
    elif len(config.config_files)== 0:
        html.write("No configuration files are defined. Please set the variable <tt>config_files</tt> in <tt>multisite.mk</tt>.")

    else:
        for filename, title, roles in config.config_files:
            if config.role in roles:
                bulletlink(title, "webconf.py?filename=%s" % filename)

sidebar_snapins["webconf"] = {
    "title" : "Check_MK Webconfig",
    "description" : "Web configuration GUI for Check_MK - manage hosts to be monitored without access to the command line",
    "author" : "Mathias Kettner",
    "render" : render_webconf_files,
    "allowed" : [ "admin", "user" ],
}
        
    
