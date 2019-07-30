# -*- encoding: utf-8
# yapf: disable

checkname = "fileinfo"

info = [
    [u"1563288717"],
    [u"[[[header]]]"],
    [u"name", u"status", u"size", u"time"],
    [u"[[[content]]]"],
    [u"/var/log/syslog", u"ok", u"1307632", u"1563288713"],
    [u"/var/log/syslog.1", u"ok", u"1235157", u"1563259976"],
    [u"/var/log/aptitude", u"ok", u"0", u"1543826115"],
    [u"/var/log/aptitude.2.gz", u"ok", u"3234", u"1539086721"],
    [u"/tmp/20190716.txt", u"ok", u"1235157", u"1563259976"],
]

group_conf = [[("log", ("*syslog*", "")), ("today", ("/tmp/$DATE:%Y%m%d$.txt", ""))]]
mock_host_conf = {"": group_conf, "groups": group_conf}

discovery = {
    "": [("/var/log/aptitude", {}), ("/var/log/aptitude.2.gz", {})],
    "groups": [
        ("log", {
            "group_patterns": [("*syslog*", "")]
        }),
        ("log", {
            "group_patterns": [("*syslog*", "")]
        }),
        ("today", {
            "group_patterns": [('/tmp/$DATE:%Y%m%d$.txt', '')]
        }),
    ]
}

checks = {
    "": [
        ("/var/log/aptitude", {}, [
            (0, "Size: 0 B", [("size", 0, None, None, None, None)]),
            (0, "Age: 225 d", [("age", 19462602, None, None, None, None)]),
        ]),
        ("/var/log/aptitude.2.gz", {
            "minsize": (5120, 10),
            "maxsize": (5242880, 9663676416),
            "minage": (60, 30),
            "maxage": (3600, 10800),
        }, [
            (1, "Size: 3234 B (warn/crit below 5120 B/10 B)", [("size", 3234, 5242880, 9663676416,
                                                                None, None)]),
            (2, "Age: 280 d (warn/crit at 60 m/180 m)", [("age", 24201996, 3600, 10800, None, None)
                                                        ]),
        ]),
        ("/var/log/syslog", {}, [
            (0, "Size: 1307632 B", [("size", 1307632, None, None, None, None)]),
            (0, "Age: 4.00 s", [("age", 4, None, None, None, None)]),
        ]),
        ("/var/log/syslog.1", {}, [
            (0, "Size: 1235157 B", [("size", 1235157, None, None, None, None)]),
            (0, "Age: 7 h", [("age", 28741, None, None, None, None)]),
        ]),
    ],
    "groups": [
        ("log", {
            "precompiled_patterns": [("*syslog*", "")],
            "maxsize": (2, 2097152),
            "minage_newest": (5, 2),
            "maxage_oldest": (3600, 3600 * 5),
        }, [
            (0, "Count: 2", [("count", 2, None, None, None, None)]),
            (2, "Size: 2542789 B (warn/crit at 2 B/2097152 B)", [("size", 2542789, 2.0, 2097152.0,
                                                                  None, None)]),
            (0, "Largest size: 1307632 B", [("size_largest", 1307632, None, None, None, None)]),
            (0, "Smallest size: 1235157 B", [("size_smallest", 1235157, None, None, None, None)]),
            (2, "Oldest age: 7 h (warn/crit at 60 m/300 m)", [("age_oldest", 28741, 3600.0, 18000.0,
                                                               None, None)]),
            (1, "Newest age: 4.00 s (warn/crit below 5.00 s/2.00 s)", [("age_newest", 4, None, None,
                                                                        None, None)]),
            (0,
             "\nInclude patterns: *syslog*\n[/var/log/syslog] Age: 4.00 s, Size: 1307632 B(!)\n[/var/log/syslog.1] Age: 7 h, Size: 1235157 B(!!)",
             []),
        ]),
        ("today", {
            "precompiled_patterns": [("/tmp/$DATE:%Y%m%d$.txt", "")]
        }, [
            (0, 'Count: 1', [('count', 1, None, None, None, None)]),
            (0, 'Size: 1235157 B', [('size', 1235157, None, None, None, None)]),
            (0, 'Largest size: 1235157 B', [('size_largest', 1235157, None, None, None, None)]),
            (0, 'Smallest size: 1235157 B', [('size_smallest', 1235157, None, None, None, None)]),
            (0, 'Oldest age: 7 h', [('age_oldest', 28741, None, None, None, None)]),
            (0, 'Newest age: 7 h', [('age_newest', 28741, None, None, None, None)]),
            (0, 'Date pattern: /tmp/20190716.txt', []),
            (0,
             '\nInclude patterns: /tmp/$DATE:%Y%m%d$.txt\n[/tmp/20190716.txt] Age: 7 h, Size: 1235157 B',
             []),
        ]),
    ]
}
