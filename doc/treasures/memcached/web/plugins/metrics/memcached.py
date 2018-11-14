# Note: graph_info is not compatible with 1.4.0 anymore
# since it is now an OrderedDict.

metric_info["rusage_user"] = {
    "title": _("User CPU time used"),
    "unit": "",
    "color": "31/a",
}

metric_info["rusage_system"] = {
    "title": _("System CPU time used"),
    "unit": "",
    "color": "41/a",
}

# graph_info.append({
#     "title"   : _("CPU usage"),
#     "metrics" : [
#         ( "rusage_user", "area" ),
#         ( "rusage_system", "stack" ),
#     ],
# })

metric_info["auth_cmds"] = {
    "title": _("Authorizations Total"),
    "unit": "",
    "color": "31/a",
}

metric_info["auth_errors"] = {
    "title": _("Authorization Errors"),
    "unit": "",
    "color": "13/a",
}

# graph_info.append({
#     "title"   : _("Authorizations"),
#     "metrics" : [
#         ( "auth_cmds", "area" ),
#         ( "auth_errors", "line" ),
#     ],
# })

metric_info["bytes_read"] = {"title": _("Read"), "unit": "bytes", "color": "31/a"}

metric_info["bytes_written"] = {"title": _("Written"), "unit": "bytes", "color": "41/a"}

# graph_info.append({
#     "title"   : _("Read and written"),
#     "metrics" : [
#         ( "bytes_read", "area" ),
#         ( "bytes_written", "-area" ),
#     ],
# })

metric_info["get_hits"] = {"title": _("GET Hits"), "unit": "", "color": "31/a"}

metric_info["get_misses"] = {"title": _("GET Misses"), "unit": "", "color": "13/a"}

metric_info["cmd_get"] = {"title": _("GET Commands"), "unit": "", "color": "23/a"}

# graph_info.append({
#     "title"   : _("GET"),
#     "metrics" : [
#         ( "get_hits", "area" ),
#         ( "get_misses", "stack" ),
#         ( "cmd_get", "line" ),
#     ],
# })

metric_info["cmd_set"] = {"title": _("SET Commands"), "unit": "", "color": "33/a"}

metric_info["cmd_flush"] = {"title": _("Flush Commands"), "unit": "", "color": "43/a"}

# graph_info.append({
#     "title"   : _("Commands"),
#     "metrics" : [
#         ( "cmd_get", "area" ),
#         ( "cmd_set", "stack" ),
#         ( "cmd_flush", "stack" ),
#     ],
# })

metric_info["cas_hits"] = {"title": _("CAS hits"), "unit": "", "color": "32/a"}

metric_info["cas_misses"] = {"title": _("CAS misses"), "unit": "", "color": "22/a"}

metric_info["cas_badval"] = {"title": _("CAS bad identifier"), "unit": "", "color": "12/a"}

# graph_info.append({
#     "title"   : _("CAS"),
#     "metrics" : [
#         ( "cas_hits", "area" ),
#         ( "cas_misses", "stack" ),
#         ( "cas_badval", "line" ),
#     ],
# })

metric_info["incr_hits"] = {"title": _("Increase Hits"), "unit": "", "color": "42/a"}

metric_info["incr_misses"] = {"title": _("Increase misses"), "unit": "", "color": "12/a"}

metric_info["decr_hits"] = {"title": _("Decrease Hits"), "unit": "", "color": "45/a"}

metric_info["decr_misses"] = {"title": _("Decrease misses"), "unit": "", "color": "15/a"}

# graph_info.append({
#     "title"   : _("Increase/Decrease"),
#     "metrics" : [
#         ( "incr_hits", "area" ),
#         ( "incr_misses", "stack" ),
#         ( "decr_hits", "-area" ),
#         ( "decr_misses", "-stack" ),
#     ],
# })

metric_info["delete_hits"] = {"title": _("Delete Hits"), "unit": "", "color": "43/a"}

metric_info["delete_misses"] = {"title": _("Delete misses"), "unit": "", "color": "13/a"}

# graph_info.append({
#     "title"   : _("Deletions"),
#     "metrics" : [
#         ( "delete_hits", "area" ),
#         ( "delete_misses", "stack" ),
#     ],
# })

metric_info["total_connections"] = {
    "title": _("Total Connections"),
    "unit": "",
    "color": "33/a",
}

metric_info["conn_yields"] = {
    "title": _("Forced connection yields"),
    "unit": "",
    "color": "14/a",
}

metric_info["curr_connections"] = {
    "title": _("Current Connections"),
    "unit": "",
    "color": "24/a",
}

metric_info["connections_structures"] = {
    "title": _("Connection Structures"),
    "unit": "",
    "color": "44/a",
}

metric_info["listen_disabled_num"] = {
    "title": _("Times listen disabled"),
    "unit": "",
    "color": "15/a",
}

metric_info["total_items"] = {
    "title": _("Total Items"),
    "unit": "",
    "color": "33/a",
}

metric_info["curr_items"] = {"title": _("Items in cache"), "unit": "", "color": "41/a"}

metric_info["reclaimed"] = {
    "title": _("Items reclaimed"),
    "unit": "",
    "color": "22/a",
}

metric_info["cache_hit_rate"] = {
    "title": _("Rate of cache hits"),
    "unit": "%",
    "color": "46/a",
}

metric_info["threads"] = {
    "title": _("Threads"),
    "unit": "",
    "color": "31/a",
}

metric_info["bytes_percent"] = {"title": _("Cache Usage"), "unit": "%", "color": "31/a"}

metric_info["eviction"] = {"title": _("Evictions"), "unit": "", "color": "21/a"}

# graph_info.append({
#     "title"   : _("Items"),
#     "metrics" : [
#         ( "total_items", "area" ),
#         ( "curr_items", "line" ),
#     ],
# })
