# -*- encoding: utf-8
# pylint: disable=protected-access
import os
import sys
import pytest
from testlib import cmk_path  # pylint: disable=import-error

sys.path.insert(0, os.path.join(cmk_path(), 'agents', 'plugins'))

import mk_jolokia  # pylint: disable=import-error,wrong-import-position

SANITIZE = mk_jolokia.JolokiaInstance._sanitize_config


@pytest.mark.parametrize("removed", ["protocol", "server", "port", "suburi", "timeout"])
def test_missing_config_basic(removed):
    config = mk_jolokia.get_default_config_dict()
    config.pop(removed)
    with pytest.raises(ValueError):
        SANITIZE(config)


def test_missing_config_auth():
    def missing_keys(key_string):
        msg_pattern = r'Missing key\(s\): %s in configuration for UnitTest' % key_string
        return pytest.raises(ValueError, match=msg_pattern)

    config = mk_jolokia.get_default_config_dict()
    for key in ("password", "user", "service_password", "client_cert", "client_key"):
        config.pop(key)
    config["instance"] = "UnitTest"
    config["mode"] = "digest"

    with missing_keys("password, user"):
        SANITIZE(config)
    config["user"] = "TestUser"
    with missing_keys("password"):
        SANITIZE(config)

    config["mode"] = "https"
    with missing_keys("client_cert, client_key"):
        SANITIZE(config)
    config["client_cert"] = "path/to/MyClientCert"
    with missing_keys("client_key"):
        SANITIZE(config)
    config["client_key"] = "mysecretkey"

    config["service_user"] = "service user"
    config["service_url"] = "u://r/l"
    with missing_keys("service_password"):
        SANITIZE(config)


def test_config_instance():
    config = mk_jolokia.get_default_config_dict()
    assert SANITIZE(config).get("instance") == "8080"
    config["instance"] = "some spaces in string"
    assert SANITIZE(config).get("instance") == "some_spaces_in_string"


def test_config_timeout():
    config = mk_jolokia.get_default_config_dict()
    config["timeout"] = '23'
    assert isinstance(SANITIZE(config).get("timeout"), float)


def test_config_legacy_cert_path_to_verify():
    config = mk_jolokia.get_default_config_dict()
    config["verify"] = None
    assert SANITIZE(config).get("verify") is True
    config["cert_path"] = "_default"
    assert SANITIZE(config).get("verify") is True
    config["verify"] = None
    config["cert_path"] = "some/path/to/file"
    assert SANITIZE(config).get("verify") == "some/path/to/file"


@pytest.mark.parametrize("config,base_url", [({
    "protocol": "sftp",
    "server": "billy.theserver",
    "port": 42,
    "suburi": "jolo-site",
    "timeout": 0
}, "sftp://billy.theserver:42/jolo-site/")])
def test_jolokia_instance_base_url(config, base_url):
    joloi = mk_jolokia.JolokiaInstance(config)
    assert joloi._get_base_url() == base_url


def test_jolokia_yield_configured_instances():
    yci = mk_jolokia.yield_configured_instances({
        "instances": [{
            "server": "s1"
        }, {
            "server": "s2"
        }],
        "port": 1234,
    })

    assert next(yci) == {"server": "s1", "port": 1234}
    assert next(yci) == {"server": "s2", "port": 1234}


class _MockHttpResponse(object):
    def __init__(self, http_status, **kwargs):
        self.status_code = http_status
        self.headers = {}
        self.content = b'\x00'
        self._payload = kwargs

    def json(self):
        return self._payload


def test_jolokia_validate_response_skip_mbean():
    for status in (199, 300):
        with pytest.raises(mk_jolokia.SkipMBean):
            mk_jolokia.validate_response(_MockHttpResponse(status))

    # MBean not found
    with pytest.raises(mk_jolokia.SkipMBean):
        mk_jolokia.validate_response(_MockHttpResponse(200, status=404))

    # value not found in MBean
    with pytest.raises(mk_jolokia.SkipMBean):
        mk_jolokia.validate_response(_MockHttpResponse(200, status=200))


def test_jolokia_validate_response_skip_instance():
    for status in (401, 403, 502):
        with pytest.raises(mk_jolokia.SkipInstance):
            mk_jolokia.validate_response(_MockHttpResponse(status))


@pytest.mark.parametrize("data", [
    {
        "status": 200,
        "value": 23,
    },
])
def test_jolokia_validate_response_ok(data):
    assert data == mk_jolokia.validate_response(_MockHttpResponse(200, **data))
