import pytest
import os

pytestmark = pytest.mark.checks

exec (open(os.path.join(os.path.dirname(__file__), '../../../checks/docker.include')).read())


@pytest.mark.parametrize('indata,expected', [
    ("docker-pullable://nginx@sha256:e3456c851a152494c3e4ff5fcc26f240206abac0c9d794affb40e0714846c451",
     "e3456c851a15"),
])
def test_parse_short_id(indata, expected):
    actual = docker_get_short_id(indata)
    assert actual == expected
