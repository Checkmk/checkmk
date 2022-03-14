import pytest
from kubernetes import client  # type: ignore[import] # pylint: disable=import-error
from kubernetes.client import ApiClient  # type: ignore[import] # pylint: disable=import-error


def kubernetes_api_client():
    config = client.Configuration()
    config.host = "http://dummy"
    config.api_key_prefix["authorization"] = "Bearer"
    config.api_key["authorization"] = "dummy"
    config.verify_ssl = False
    return ApiClient(config)


@pytest.fixture
def core_client():
    return client.CoreV1Api(kubernetes_api_client())


@pytest.fixture
def batch_client():
    return client.BatchV1Api(kubernetes_api_client())


@pytest.fixture
def apps_client():
    return client.AppsV1Api(kubernetes_api_client())


@pytest.fixture
def dummy_host():
    return kubernetes_api_client().configuration.host
