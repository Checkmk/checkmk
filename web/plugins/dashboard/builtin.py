# encoding: utf-8

builtin_dashboards = {
    "main" : {
        "title" : _("Main Overview"),
        "dashlets" : [
            { 
                "title"      : _("Host Problems"),
                "iframe"     : "view.py?view_name=hostproblems_dash&display_options=SIXHR&_body_class=dashlet",
                "position"   : (-1, 1),
                "size"       : (GROW, 8),
            },
            { 
                "title"      : _("Service Problems"),
                "iframe"     : "view.py?view_name=svcproblems_dash&display_options=SIXHR&_body_class=dashlet",
                "position"   : (1, 4),
                "size"       : (GROW, MAX),
            },
            { 
                "title"      : _("Events of recent 4 hours"),
                "iframe"     : "view.py?view_name=events_dash&display_options=SIXHR&_body_class=dashlet",
                "position"   : (-1, -1),
                "size"       : (GROW, GROW),
            },
            { 
                "url"        : "dashlet_overview.py", 
                "position"   : (1, 1),
                "size"       : (GROW, 3),
                "shadow"     : False,
                "background" : False,
            },

            # { 
            #     "title"    : "CPU load of Nagios",
            #     # "url"      : "http://localhost/dk/pnp4nagios/index.php/image?host=DerNagiosSelbst&srv=fs__var&view=0",
            #     "url"      : "http://localhost/dk/pnp4nagios/index.php/popup?host=localhost&srv=CPU_load&view=0&source=2",
            #     "position" : (1, -1),
            #     "size"     : (11, 5),
            # },
            # {
            #     "title"    : "CPU utilization of Nagios",
            #     # "url"      : "http://localhost/dk/pnp4nagios/index.php/image?host=DerNagiosSelbst&srv=fs__var&view=0",
            #     "url"      : "http://localhost/dk/pnp4nagios/index.php/popup?host=localhost&srv=CPU_utilization&view=0&source=2",
            #     "position" : (12, -1),
            #     "size"     : (11, 5),
            # },
            # { 
        ]
    }
}
