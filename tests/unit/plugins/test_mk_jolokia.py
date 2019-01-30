# -*- encoding: utf-8
# pylint: disable=protected-access
import os
import sys
import copy
import pytest
from testlib import cmk_path  # pylint: disable=import-error

sys.path.insert(0, os.path.join(cmk_path(), 'agents', 'plugins'))

import mk_jolokia  # pylint: disable=import-error,wrong-import-position


SANITIZE = mk_jolokia.JolokiaInstance._sanitize_config


@pytest.mark.parametrize("removed", ["protocol", "server", "port", "suburi"])
def test_missing_config_basic(removed):
    config = copy.deepcopy(mk_jolokia.DEFAULT_CONFIG)
    config.pop(removed)
    with pytest.raises(ValueError):
        SANITIZE(config)


def test_config_instance():
    config = copy.deepcopy(mk_jolokia.DEFAULT_CONFIG)
    assert SANITIZE(config).get("instance") == "8080"
    config["instance"] = "some spaces in string"
    assert SANITIZE(config).get("instance") == "some_spaces_in_string"


@pytest.mark.parametrize("config,base_url", [
    ({"protocol": "sftp", "server": "billy.theserver", "port": 42,
      "suburi": "jolo-site"}, "sftp://billy.theserver:42/jolo-site/")
])
def test_jolokia_instance_base_url(config, base_url):
    joloi = mk_jolokia.JolokiaInstance(config)
    assert joloi._get_base_url() == base_url
