
##################################################################################
# Data sources
##################################################################################

multisite_datasources["hosts"] = {
    "title"   : "All hosts",
    "table"   : "hosts",
    "columns" : ["name", "state"],
}

multisite_datasources["services"] = {
    "title"   : "All services",
    "table"   : "services",
    "columns" : ["description", "plugin_output", "state", "has_been_checked", 
                 "host_name", "host_state", "last_state_change", "downtimes" ],
}

