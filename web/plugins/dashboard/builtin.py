builtin_dashboards = {
    "main" : {
        "title" : "Main Overview",
        "dashlets" : [
            # { 
            #     "title" : "Host problems",
            #     "content" : "TEST",
            #     "position" : (1, 1),
            #     "size" : (0, 2),
            # },
            # { 
            #     "title" : "Anderer Host",
            #     "content" : "TEST",
            #     "position" : (6, 6),
            #     "size" : (0, 1),
            # },
            { 
                "title" : "Host problems",
                "content" : '<iframe width="100%" height="100%" src="view.py?view_name=host&site=&host=begeistert&display_options=SIXH"></iframe>',
                "position" : (1, 1),
                "size" : (0, 0),
            },
            { 
                "title" : "Host problems",
                "content" : '<iframe width="100%" height="100%" src="view.py?view_name=host&site=&host=begeistert&display_options=SIXH"></iframe>',
                "position" : (-1, 1),
                "size" : (0, 0),
            },
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
