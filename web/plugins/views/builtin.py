#!/usr/bin/python

multisite_builtin_views = {
    ("", 'servicegroup'): 
	{'datasource': 'services',
                     'group_painters': [],
                     'hard_filters': [],
                     'hard_filtervars': [],
                     'layout': 'table',
                     'name': 'servicegroup',
                     'owner': '_builtin_',
                     'painters': ['host',
                                  'service_state',
                                  'svc_state_age',
                                  'service_description',
                                  'svc_plugin_output'],
                     'public': True,
		     'hidden' : True,
                     'show_filters': [],
                     'hide_filters': ['servicegroup'],
                     'sorters': [('site_host', False), ('svcdescr', False)],
                     'title': 'Servicegroup'},
}
