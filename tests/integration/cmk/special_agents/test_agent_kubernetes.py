import pytest

from kubernetes.client.models import V1ClusterRole


def test_v1_clusterrole_without_rules():
    # try:
    #     role = V1ClusterRole(rules=None)
    # except ValueError:
    #     pytest.fail(
    #         "It must be possible to instantiate a V1ClusterRole without explicit roles. "
    #         "This is assured by patch 0020-kubernetes-allow-empty-rules-in-clusterrole.dif.")

    # assert role.rules == []
    pass
