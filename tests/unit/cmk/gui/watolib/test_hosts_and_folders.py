import pytest  # type: ignore
import json
import urllib
# cmk.gui.wato: needed to load all WATO plugins
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.config as config  # pylint: disable=unused-import
import cmk.gui.watolib as watolib  # pylint: disable=unused-import
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders

from cmk.gui.plugins.wato import host_attribute_registry
import cmk.gui.htmllib as htmllib

from werkzeug.test import create_environ
from testlib.utils import DummyApplication
from cmk.gui.http import Request, Response
from cmk.gui.globals import AppContext, RequestContext


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize("attributes,expected_tags", [
    ({
        "tag_snmp": "no-snmp",
        "tag_agent": "no-agent",
        "site": "ding",
    }, {
        'address_family': 'ip-v4-only',
        'ip-v4': 'ip-v4',
        'agent': 'no-agent',
        'snmp_ds': 'no-snmp',
        'ping': 'ping',
        'site': 'ding',
        'piggyback': 'auto-piggyback',
    }),
    ({
        "tag_snmp": "no-snmp",
        "tag_agent": "no-agent",
        "tag_address_family": "no-ip",
    }, {
        'agent': 'no-agent',
        'address_family': 'no-ip',
        'snmp_ds': 'no-snmp',
        'site': 'NO_SITE',
        'piggyback': 'auto-piggyback',
    }),
    ({
        "site": False,
    }, {
        'agent': 'cmk-agent',
        'address_family': 'ip-v4-only',
        'ip-v4': 'ip-v4',
        'snmp_ds': 'no-snmp',
        'site': '',
        'tcp': 'tcp',
        'piggyback': 'auto-piggyback',
    }),
])
def test_host_tags(attributes, expected_tags):
    folder = hosts_and_folders.Folder.root_folder()
    host = hosts_and_folders.Host(folder, "test-host", attributes, cluster_nodes=None)

    assert host.tag_groups() == expected_tags


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize("attributes,result", [
    ({
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "no-agent",
    }, True),
    ({
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "cmk-agent",
    }, False),
    ({
        "tag_snmp_ds": "no-snmp",
        "tag_agent": "no-agent",
        "tag_address_family": "no-ip",
    }, False),
])
def test_host_is_ping_host(attributes, result):
    folder = hosts_and_folders.Folder.root_folder()
    host = hosts_and_folders.Host(folder, "test-host", attributes, cluster_nodes=None)

    assert host.is_ping_host() == result


@pytest.mark.parametrize("attributes", [{
    "tag_snmp_ds": "no-snmp",
    "tag_agent": "no-agent",
    "alias": "testalias",
    "parents": ["ding", "dong"],
}])
def test_write_and_read_host_attributes(tmp_path, attributes, monkeypatch):
    folder_path = str(tmp_path)

    # Write/Read operations always require a valid user
    monkeypatch.setattr(config, "user", config.LoggedInSuperUser())

    # Used to write the data
    write_data_folder = watolib.Folder("testfolder", folder_path=folder_path, parent_folder=None)

    # Used to read the previously written data
    read_data_folder = watolib.Folder("testfolder", folder_path=folder_path, parent_folder=None)

    environ = dict(create_environ(), REQUEST_URI='')
    with AppContext(DummyApplication(environ, None)), \
         RequestContext(htmllib.html(Request(environ), Response(is_secure=False))):
        # Write data
        # Note: The create_hosts function modifies the attributes dict, adding a meta_data key inplace
        write_data_folder.create_hosts([("testhost", attributes, [])])
        write_folder_hosts = write_data_folder.hosts()
        assert len(write_folder_hosts) == 1

        # Read data back
        read_folder_hosts = read_data_folder.hosts()
        assert len(read_folder_hosts) == 1
        for hostname, host in read_folder_hosts.iteritems():
            assert host.attributes() == attributes
