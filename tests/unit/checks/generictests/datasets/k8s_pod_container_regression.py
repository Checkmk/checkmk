# yapf: disable


checkname = 'k8s_pod_container'


info = [[u'{"nginx": {"image_pull_policy": "IfNotPresent", "image": "nginx:1.7.9", "container_id": "87cc3642854cc8810e24ca49b4c9ce5a03aee5076284d0945524c229289740a2", "restart_count": 1, "image_id": "docker-pullable://nginx@sha256:e3456c851a152494c3e4ff5fcc26f240206abac0c9d794affb40e0714846c451", "ready": true}}']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0, 'Ready: 1/1', [('docker_all_containers', 1, None, None, 0, 1),
                                    ('ready_containers', 1, None, None, 0, 1)])])]}
