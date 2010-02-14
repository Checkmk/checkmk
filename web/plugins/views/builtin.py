#!/usr/bin/python

# Be sure to set
# - owner to ''
# - public to True

multisite_builtin_views = {
    ("", 'servicegroup'): 
	{'datasource': 'services',
                     'group_painters': [],
                     'hard_filters': [],
                     'hard_filtervars': [],
                     'layout': 'table',
                     'name': 'servicegroup',
                     'owner': '',
                     'painters': [('host', None),
                                  ('service_state',None),
                                  ('svc_state_age',None),
                                  ('service_description',None),
                                  ('svc_plugin_output',None),
				  ],
                     'public': True,
		     'hidden' : True,
                     'show_filters': [],
                     'hide_filters': ['servicegroup'],
                     'sorters': [('site_host', False), ('svcdescr', False)],
                     'title': 'Servicegroup'},
("", 'services'): {'datasource': 'services',
              'group_painters': [('service_description', None)],
              'hard_filters': [],
              'hard_filtervars': [],
              'hidden': False,
              'hide_filters': [],
              'layout': 'boxed_4',
              'name': 'services',
              'owner': '',
              'painters': [('host',None), ('svc_state_age',None), ('service_state',None)],
              'public': True,
              'show_filters': ['hostgroup'],
              'sorters': [('svcdescr', False)],
              'title': 'Services'},
}
