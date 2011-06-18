builtin_dashboards = {
    "main" : {
        "title" : "Main Overview",
        "dashlets" : [
            { 
                "title"    : "Host problems",
                "content"  : "0",
                "position" : (1, 1),
                "size"     : (20, 0),
            },
            { 
                "title"    : "Host problems",
                # "content"  : "1",
                "content" : '<iframe width="100%" height="100%" src="http://localhost/lancom/check_mk/view.py?host=&opthostgroup=&view_name=allhosts&site=&is_summary_host=0&num_columns=1&display_options=SIXH&_link_target=main"></iframe>',
                "position" : (21, 1),
                "size"     : (0, 0),
            },
            { 
                "title"    : "Host problems",
                "content"  : "2x1 @ 4,2",
                "position" : (1, -1),
                "size"     : (0, 8),
            },
            # { 
            #     "title" : "Anderer Host",
            #     "content" : "TEST",
            #     "position" : (6, 6),
            #     "size" : (0, 1),
            # },
            # { 
            #     "title" : "Host problems",
            #     # "url" : 'view.py?view_name=dash_hosts&display_options=SIX',
            #     "content" : 'Nummer 0',
            #     "position" : (1, 1),
            #     "size" : (0, 0),
            # },
            # { 
            #     "title" : "Host problems",
            #     # "content" : '<iframe width="100%" height="100%" src="view.py?view_name=host&site=&host=begeistert&display_options=SIXH"></iframe>',
            #     "content" : 'Nummer 1',
            #     "position" : (-1, 1),
            #     "size" : (0, 0),
            # },
            # { 
            #     "title" : "Host problems",
            #     "content" : "Fester Inhalt",
            #     "position" : (-1, 1),
            #     "size" : (0, 4),
            # },
            # { 
            #     "title" : "Host problems",
            #     "content" : "Fester Inhalt",
            #     "position" : (-1, -1),
            #     "size" : (1, 1),
            # },
        ]
    }
}
