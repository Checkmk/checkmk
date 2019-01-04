import pytest
import cmk.gui.sites as sites


@pytest.mark.parametrize("socket_spec,result", [
    (("local", None), "unix:tmp/run/live"),
    (("unix", {
        "path": "/a/b/c"
    }), "unix:/a/b/c"),
    (("tcp", {
        "address": ("127.0.0.1", 1234)
    }), "tcp:127.0.0.1:1234"),
    (("tcp6", {
        "address": ("::1", 1234)
    }), "tcp6:::1:1234"),
    (("proxy", {
        "socket": ("unix", {
            "path": "/a/b/c"
        })
    }), "unix:tmp/run/liveproxy/mysite"),
])
def test_encode_socket_for_livestatus(socket_spec, result):
    assert sites.encode_socket_for_livestatus("mysite", socket_spec) == result
