builtin_dashboards = {
    "main" : {
        "title" : "Main Overview",
        "dashlets" : [
            { 
                "title"    : "Host Problems",
                "iframe"   : "view.py?view_name=hostproblems_dash&display_options=SIXHR&_body_class=dashlet",
                "position" : (-1, 1),
                "size"     : (0, 8),
            },
            { 
                "title"    : "Service Problems",
                "iframe"   : "view.py?view_name=svcproblems_dash&display_options=SIXHR&_body_class=dashlet",
                "position" : (1, 1),
                "size"     : (0, 0),
            },
            { 
                "title"    : "Events of recent 4 hours",
                "iframe"   : "view.py?view_name=events_dash&display_options=SIXHR&_body_class=dashlet",
                "position" : (-1, -1),
                "size"     : (0, 0),
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
