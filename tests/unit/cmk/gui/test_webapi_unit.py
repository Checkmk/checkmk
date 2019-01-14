
import cmk.gui.webapi

import cmk.gui.plugins.webapi.utils as webapi_utils

def test_registered_api_call_collections():
    registered_plugins = sorted(webapi_utils.api_call_collection_registry.keys())
    assert registered_plugins == [
        'APICallBIAggregationState',
        'APICallBakery',
        'APICallFolders',
        'APICallGraph',
        'APICallGroups',
        'APICallHosts',
        'APICallHosttags',
        'APICallOther',
        'APICallRules',
        'APICallSLA',
        'APICallSites',
        'APICallUsers',
    ]
