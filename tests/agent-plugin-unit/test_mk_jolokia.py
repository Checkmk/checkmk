#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"
# ruff: noqa: RUF100
# ruff: noqa: I001

from typing import Mapping

import pytest
from agents.plugins import mk_jolokia


@pytest.mark.parametrize("removed", ["protocol", "server", "port", "suburi", "timeout"])
def test_missing_config_basic(removed: str) -> None:
    config = mk_jolokia.get_default_config_dict()
    config.pop(removed)
    with pytest.raises(ValueError):
        mk_jolokia.JolokiaInstance._sanitize_config(config)


def test_missing_config_auth() -> None:
    def missing_keys(key_string):
        msg_pattern = r"Missing key\(s\): %s in configuration for UnitTest" % key_string
        return pytest.raises(ValueError, match=msg_pattern)

    config = mk_jolokia.get_default_config_dict()
    for key in ("password", "user", "service_password", "client_cert", "client_key"):
        config.pop(key)
    config["instance"] = "UnitTest"
    config["mode"] = "digest"

    with missing_keys("password, user"):
        mk_jolokia.JolokiaInstance._sanitize_config(config)
    config["user"] = "TestUser"
    with missing_keys("password"):
        mk_jolokia.JolokiaInstance._sanitize_config(config)

    config["mode"] = "https"
    with missing_keys("client_cert, client_key"):
        mk_jolokia.JolokiaInstance._sanitize_config(config)
    config["client_cert"] = "path/to/MyClientCert"
    with missing_keys("client_key"):
        mk_jolokia.JolokiaInstance._sanitize_config(config)
    config["client_key"] = "mysecretkey"

    config["service_user"] = "service user"
    config["service_url"] = "u://r/l"
    with missing_keys("service_password"):
        mk_jolokia.JolokiaInstance._sanitize_config(config)


def test_config_instance() -> None:
    config = mk_jolokia.get_default_config_dict()
    assert mk_jolokia.JolokiaInstance._sanitize_config(config).get("instance") == "8080"
    config["instance"] = "some spaces in string"
    assert (
        mk_jolokia.JolokiaInstance._sanitize_config(config).get("instance")
        == "some_spaces_in_string"
    )


def test_config_timeout() -> None:
    config = mk_jolokia.get_default_config_dict()
    config["timeout"] = "23"
    assert isinstance(mk_jolokia.JolokiaInstance._sanitize_config(config).get("timeout"), float)


def test_config_legacy_cert_path_to_verify() -> None:
    config = mk_jolokia.get_default_config_dict()
    config["verify"] = None
    assert mk_jolokia.JolokiaInstance._sanitize_config(config).get("verify") is True
    config["cert_path"] = "_default"
    assert mk_jolokia.JolokiaInstance._sanitize_config(config).get("verify") is True
    config["verify"] = None
    config["cert_path"] = "some/path/to/file"
    assert mk_jolokia.JolokiaInstance._sanitize_config(config).get("verify") == "some/path/to/file"


@pytest.mark.parametrize(
    "config,base_url",
    [
        (
            {
                "protocol": "sftp",
                "server": "billy.theserver",
                "port": 42,
                "suburi": "jolo-site",
                "timeout": 0,
            },
            "sftp://billy.theserver:42/jolo-site/",
        )
    ],
)
def test_jolokia_instance_base_url(config: Mapping[str, object], base_url: str) -> None:
    joloi = mk_jolokia.JolokiaInstance(config, mk_jolokia.USER_AGENT)
    assert joloi._get_base_url() == base_url


def test_jolokia_yield_configured_instances() -> None:
    yci = mk_jolokia.yield_configured_instances(
        {
            "instances": [{"server": "s1"}, {"server": "s2"}],
            "port": 1234,
        }
    )

    assert next(yci) == {"server": "s1", "port": 1234}
    assert next(yci) == {"server": "s2", "port": 1234}


class _MockHttpResponse:
    def __init__(self, http_status: int, **kwargs: object) -> None:
        self.status_code = http_status
        self.headers = {}  # type: dict
        self.content = b"\x00"
        self._payload = kwargs

    def json(self):
        return self._payload


def test_jolokia_validate_response_skip_mbean() -> None:
    for status in (199, 300):
        with pytest.raises(mk_jolokia.SkipMBean):
            mk_jolokia.validate_response(_MockHttpResponse(status))

    # MBean not found
    with pytest.raises(mk_jolokia.SkipMBean):
        mk_jolokia.validate_response(_MockHttpResponse(200, status=404))

    # value not found in MBean
    with pytest.raises(mk_jolokia.SkipMBean):
        mk_jolokia.validate_response(_MockHttpResponse(200, status=200))


def test_jolokia_validate_response_skip_instance() -> None:
    for status in (401, 403, 502):
        with pytest.raises(mk_jolokia.SkipInstance):
            mk_jolokia.validate_response(_MockHttpResponse(status))


@pytest.mark.parametrize(
    "data",
    [
        {
            "status": 200,
            "value": 23,
        },
    ],
)
def test_jolokia_validate_response_ok(data: Mapping[str, int]) -> None:
    assert data == mk_jolokia.validate_response(_MockHttpResponse(200, **data))


def test_jolokia_escape_path_separator() -> None:
    config = mk_jolokia.load_config(None)
    data = mk_jolokia.JolokiaInstance(config=config, user_agent="NOT_IMPORTANT").get_post_data(
        path="Catalina:J2EEApplication=none,J2EEServer=none,WebModule=*localhost!/docs,j2eeType=Servlet,name=default/requestCount",
        function="read",
        use_target=True,
    )

    assert (
        data["mbean"]
        == "Catalina:J2EEApplication=none,J2EEServer=none,WebModule=*localhost/docs,j2eeType=Servlet,name=default"
    )
    assert data["attribute"] == "requestCount"


def test_parse_fetched_data_v2_0_2() -> None:
    data = {
        "agent": "2.0.2",
        "protocol": "7.2",
        "details": {
            "agent_version": "2.0.2",
            "agent_id": "192.168.0.221-21185-5ce94d31-servlet",
            "server_product": "tomcat",
            "server_vendor": "Apache",
            "server_version": "10.1.16",
            "secured": True,
            "url": "http://192.168.0.221:8080/jolokia",
        },
    }
    product, version, agentversion = mk_jolokia._parse_fetched_data(data)
    assert product == "tomcat"
    assert version == "10.1.16"
    assert agentversion == "2.0.2"


def test_parse_fetched_data_v1_2_0() -> None:
    data = {
        "protocol": "7.1",
        "agent": "1.2.0",
        "info": {
            "product": "glassfish",
            "vendor": "Oracle",
            "version": "4.0",
            "extraInfo": {"amxBooted": False},
        },
    }
    product, version, agentversion = mk_jolokia._parse_fetched_data(data)
    assert product == "glassfish"
    assert version == "4.0"
    assert agentversion == "1.2.0"


def test_parse_fetched_data_v2_0_2_missing_server_product() -> None:
    data = {
        "agent": "2.0.2",
        "protocol": "7.2",
        "details": {
            "agent_version": "2.0.2",
            "agent_id": "192.168.0.221-21185-5ce94d31-servlet",
            "server_vendor": "Apache",
            "server_version": "10.1.16",
            "secured": True,
            "url": "http://192.168.0.221:8080/jolokia",
        },
    }
    product, version, agentversion = mk_jolokia._parse_fetched_data(data)
    assert product == "unknown"
    assert version == "10.1.16"
    assert agentversion == "2.0.2"


def test_parse_fetched_data_v2_0_2_missing_server_version() -> None:
    data = {
        "agent": "2.0.2",
        "protocol": "7.2",
        "details": {
            "agent_version": "2.0.2",
            "agent_id": "192.168.0.221-21185-5ce94d31-servlet",
            "server_product": "tomcat",
            "server_vendor": "Apache",
            "secured": True,
            "url": "http://192.168.0.221:8080/jolokia",
        },
    }
    product, version, agentversion = mk_jolokia._parse_fetched_data(data)
    assert product == "tomcat"
    assert version == "unknown"
    assert agentversion == "2.0.2"
