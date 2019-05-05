import pytest  # type: ignore
# cmk.gui.wato: needed to load all WATO plugins
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.watolib.hosts_and_folders as hosts_and_folders


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
