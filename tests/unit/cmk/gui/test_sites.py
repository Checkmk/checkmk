import pytest
import cmk.gui.sites as sites


@pytest.mark.parametrize("site_spec,result", [
    ({
        "socket": ("local", None),
        "proxy": None
    }, "unix:tmp/run/live"),
    ({
        "socket": ("local", None),
        "proxy": {
            "params": None
        },
    }, "unix:tmp/run/liveproxy/mysite"),
    ({
        "socket": ("unix", {
            "path": "/a/b/c"
        }),
        "proxy": None
    }, "unix:/a/b/c"),
    ({
        "socket": ("tcp", {
            "address": ("127.0.0.1", 1234)
        }),
        "proxy": None
    }, "tcp:127.0.0.1:1234"),
    ({
        "socket": ("tcp6", {
            "address": ("::1", 1234)
        }),
        "proxy": None
    }, "tcp6:::1:1234"),
    ({
        "socket": ("unix", {
            "path": "/a/b/c"
        }),
        "proxy": {
            "params": None
        }
    }, "unix:tmp/run/liveproxy/mysite"),
])
def test_encode_socket_for_livestatus(site_spec, result):
    assert sites.encode_socket_for_livestatus("mysite", site_spec) == result


@pytest.mark.parametrize("site_spec,result", [
    ({
        "socket": ("tcp", {
            "address": ("127.0.0.1", 1234),
            "tls": ("encrypted", {
                "verify": True
            })
        }),
        "proxy": None,
    }, {
        "socket": "tcp:127.0.0.1:1234",
        "tls": ("encrypted", {
            "verify": True
        }),
        "proxy": None,
    }),
])
def test_site_config_for_livestatus_tcp_tls(site_spec, result):
    assert sites._site_config_for_livestatus("mysite", site_spec) == result
