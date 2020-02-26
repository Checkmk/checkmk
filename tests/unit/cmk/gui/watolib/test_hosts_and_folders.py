import contextlib
import os
import shutil

import pytest  # type: ignore[import]
from werkzeug.test import create_environ

import cmk.gui.config as config  # pylint: disable=unused-import
import cmk.gui.watolib as watolib  # pylint: disable=unused-import
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders
import cmk.gui.htmllib as htmllib

from cmk.gui.http import Request, Response
from cmk.gui.globals import AppContext, RequestContext

from testlib.utils import DummyApplication


@pytest.fixture(name="mocked_user")
def fixture_mocked_user(monkeypatch):
    # Write/Read operations always require a valid user
    monkeypatch.setattr(config, "user", config.LoggedInSuperUser())


@pytest.fixture(autouse=True)
def test_env(mocked_user, load_config, load_plugins):
    # Ensure we have clean folder/host caches
    hosts_and_folders.Folder.invalidate_caches()

    yield

    # Cleanup WATO folders created by the test
    shutil.rmtree(hosts_and_folders.Folder.root_folder().filesystem_path())
    os.mkdir(hosts_and_folders.Folder.root_folder().filesystem_path())


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
        for _, host in read_folder_hosts.iteritems():
            assert host.attributes() == attributes


@contextlib.contextmanager
def in_chdir(directory):
    cur = os.getcwd()
    os.chdir(directory)
    yield
    os.chdir(cur)


def test_create_nested_folders(register_builtin_html):
    with in_chdir("/"):
        root = watolib.Folder.root_folder()

        folder1 = watolib.Folder("folder1", parent_folder=root)
        folder1.persist_instance()

        folder2 = watolib.Folder("folder2", parent_folder=folder1)
        folder2.persist_instance()

        shutil.rmtree(os.path.dirname(folder1.wato_info_path()))


@pytest.mark.parametrize("protocol,host_attribute,base_variable,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "management_snmp_credentials", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials_explicit_host(protocol, host_attribute, base_variable,
                                                credentials, folder_credentials):

    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([("test-host", {
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
        host_attribute: credentials,
    }, [])])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["test-host"] == protocol
    assert data[base_variable]["test-host"] == credentials


@pytest.mark.parametrize("protocol,host_attribute,base_variable,folder_credentials", [
    ("snmp", "management_snmp_community", "management_snmp_credentials", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", "management_ipmi_credentials", {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials(protocol, host_attribute, base_variable, folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([("mgmt-host", {
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
    }, [])])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials


@pytest.mark.parametrize("protocol,host_attribute,base_variable,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "management_snmp_credentials", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol_explicit_host(protocol, host_attribute, base_variable, credentials,
                                             folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", None)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([("mgmt-host", {
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
        host_attribute: credentials,
    }, [])])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == credentials


@pytest.mark.parametrize("protocol,host_attribute,base_variable,folder_credentials", [
    ("snmp", "management_snmp_community", "management_snmp_credentials", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", "management_ipmi_credentials", {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol(protocol, host_attribute, base_variable, folder_credentials):
    folder = hosts_and_folders.Folder.root_folder()
    folder.set_attribute("management_protocol", protocol)
    folder.set_attribute(host_attribute, folder_credentials)

    folder.create_hosts([("mgmt-host", {
        "ipaddress": "127.0.0.1",
    }, [])])

    data = folder._load_hosts_file()
    assert data["management_protocol"]["mgmt-host"] == protocol
    assert data[base_variable]["mgmt-host"] == folder_credentials
