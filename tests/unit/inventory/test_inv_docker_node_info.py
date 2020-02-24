import pytest  # type: ignore[import]


@pytest.mark.parametrize('parsed, inventory_data, status_data', [
    ({
        "nothing": "usable"
    }, {}, {}),
    ({
        'ServerVersion': u'1.17',
        'IndexServerAddress': u'https://registry.access.redhat.com/v1/',
        u'Containers': 11,
        u'ContainersPaused': 0,
        u'ContainersRunning': 11,
        u'ContainersStopped': 0,
        u'Images': 22,
        u'Swarm': {
            'LocalNodeState': u'active',
            'NodeID': u'Hier koennte ihre Werbung stehen.'
        },
    }, {
        "version": "1.17",
        "registry": u'https://registry.access.redhat.com/v1/',
        "swarm_state": "active",
        "swarm_node_id": u'Hier koennte ihre Werbung stehen.',
    }, {
        "num_containers_total": 11,
        "num_containers_running": 11,
        "num_containers_paused": 0,
        "num_containers_stopped": 0,
        "num_images": 22,
    }),
])
def test_inv_docker_node_info(inventory_plugin_manager, parsed, inventory_data, status_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('docker_node_info')
    inventory_tree_data, status_tree_data = inv_plugin.run_inventory(parsed)

    path = "software.applications.docker."
    assert path in inventory_tree_data
    assert path in status_tree_data

    node_inventory_data = inventory_tree_data[path]
    node_status_data = status_tree_data[path]

    assert sorted(node_inventory_data.items()) == sorted(inventory_data.items())
    assert sorted(node_status_data.items()) == sorted(status_data.items())
