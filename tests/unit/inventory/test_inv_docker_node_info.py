import os
import pytest

INV_FILE = os.path.join(os.path.dirname(__file__), '../../../inventory/docker_node_info')


class MockTree(object):
    def __init__(self):
        self.data = {}

    def get_dict(self, path):
        return self.data.setdefault(path, dict())

    def get_list(self, path):
        return self.data.setdefault(path, list())


@pytest.mark.parametrize('parsed,inv_data,stat_data',
                         [({
                             "nothing": "usable"
                         }, {
                             "software.applications.docker.": {}
                         }, {
                             "software.applications.docker.": {}
                         }),
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
                              "software.applications.docker.": {
                                  "version": "1.17",
                                  "registry": u'https://registry.access.redhat.com/v1/',
                                  "swarm_state": "active",
                                  "swarm_node_id": u'Hier koennte ihre Werbung stehen.',
                              },
                          }, {
                              "software.applications.docker.": {
                                  "num_containers_total": 11,
                                  "num_containers_running": 11,
                                  "num_containers_paused": 0,
                                  "num_containers_stopped": 0,
                                  "num_images": 22,
                              },
                          })])
def test_inv_docker_node_info(parsed, inv_data, stat_data):
    inventory_tree = MockTree()
    status_data_tree = MockTree()

    context = {'inv_info': {}}
    exec (open(INV_FILE).read(), context)
    inv_docker_node_info = context["inv_docker_node_info"]

    inv_docker_node_info(parsed, inventory_tree, status_data_tree)
    assert inventory_tree.data == inv_data
    assert status_data_tree.data == stat_data
