
##################################################################################
# Data sources
##################################################################################

multisite_datasources["hosts"] = {
    "title"   : "All hosts",
    "table"   : "hosts",
    "columns" : ["name", "alias", "state", "has_been_checked", "downtimes", 
   "num_services", "num_services_pending", "num_services_ok", "num_services_warn", "num_services_unknown", "num_services_crit" ],
}

multisite_datasources["services"] = {
    "title"   : "All services",
    "table"   : "services",
    "columns" : ["description", "plugin_output", "state", "has_been_checked", 
                 "host_name", "host_state", "host_has_been_checked", 
		 "last_state_change", "downtimes", "perf_data" ],
}


