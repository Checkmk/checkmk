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
        for filename, title, roles in config.config_files:
            if config.role in roles:
                bulletlink(title, "wato.py?filename=%s" % filename)

sidebar_snapins["wato"] = {
    "title" : "Check_MK Web Administration Tool",
    "description" : "WATO - the Web Administration Tool of Check_MK - manage hosts to be monitored without access to the command line",
    "author" : "Mathias Kettner",
    "render" : render_wato_files,
    "allowed" : [ "admin", "user" ],
}
        
    
