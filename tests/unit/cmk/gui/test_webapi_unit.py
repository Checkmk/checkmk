# Needed to make the test load all webapi plugins (incl. CEE)
import cmk.gui.webapi  # pylint: disable=unused-import

from cmk.gui.plugins.webapi.utils import api_call_collection_registry


def test_registered_api_call_collections():
    registered_api_actions = (action \
                              for cls in api_call_collection_registry.values()
                              for action in cls().get_api_calls().iterkeys())
    assert sorted(registered_api_actions) == sorted([
        'activate_changes',
        'add_contactgroup',
        'add_folder',
        'add_host',
        'add_hostgroup',
        'add_hosts',
        'add_servicegroup',
        'add_users',
        'bake_agents',
        'delete_contactgroup',
        'delete_folder',
        'delete_host',
        'delete_hostgroup',
        'delete_hosts',
        'delete_servicegroup',
        'delete_site',
        'delete_users',
        'discover_services',
        'edit_contactgroup',
        'edit_folder',
        'edit_host',
        'edit_hostgroup',
        'edit_hosts',
        'edit_servicegroup',
        'edit_users',
        'get_all_contactgroups',
        'get_all_folders',
        'get_all_hostgroups',
        'get_all_hosts',
        'get_all_servicegroups',
        'get_all_sites',
        'get_all_users',
        'get_bi_aggregations',
        'get_folder',
        'get_graph',
        'get_host',
        'get_hosttags',
        'get_ruleset',
        'get_rulesets_info',
        'get_site',
        'get_sla',
        'login_site',
        'logout_site',
        'set_all_sites',
        'set_hosttags',
        'set_ruleset',
        'set_site',
    ])
