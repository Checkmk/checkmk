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


@pytest.fixture
def make_folder(mocker):
    """Returns a function to create patched folders for tests."""
    mocker.patch.object(hosts_and_folders.config,
                        'wato_hide_folders_without_read_permissions',
                        True,
                        create=True)

    def unimplemented(self_, x):
        raise Exception('Wrong code path in __init__')

    mocker.patch.object(hosts_and_folders.Folder, '_init_by_loading_existing_directory',
                        unimplemented)

    def prefixed_title(self_, current_depth, pretty):
        return "_" * current_depth + self_.title()

    mocker.patch.object(hosts_and_folders.Folder, '_prefixed_title', prefixed_title)

    def may(self_, _permission):
        return self_._may_see

    mocker.patch.object(hosts_and_folders.Folder, 'may', may)

    # convenience method NOT present in Folder
    def add_subfolders(self_, folders):
        for folder in folders:
            self_._subfolders[folder.name()] = folder
            folder._parent = self_
        return self_

    mocker.patch.object(hosts_and_folders.Folder, 'add_subfolders', add_subfolders, create=True)

    def f(name, title, root_dir='/', parent_folder=None, may_see=True):
        folder = hosts_and_folders.Folder(name,
                                          folder_path=None,
                                          parent_folder=parent_folder,
                                          title=title,
                                          root_dir=root_dir)
        folder._may_see = may_see
        return folder

    return f


def only_root(folder):
    return folder('', title='Main directory')


def three_levels(folder):
    return folder('', title='Main directory').add_subfolders([
        folder('a', title='A').add_subfolders([
            folder('c', title='C'),
            folder('d', title='D'),
        ]),
        folder('b', title='B').add_subfolders([
            folder('e', title='E').add_subfolders([
                folder('f', title='F'),
            ]),
        ]),
    ])


def three_levels_leaf_permissions(folder):
    return folder('', title='Main directory', may_see=False).add_subfolders([
        folder('a', title='A', may_see=False).add_subfolders([
            folder('c', title='C', may_see=False),
            folder('d', title='D'),
        ]),
        folder('b', title='B', may_see=False).add_subfolders([
            folder('e', title='E', may_see=False).add_subfolders([
                folder('f', title='F'),
            ]),
        ]),
    ])


@pytest.mark.parametrize('actual_builder,expected', [
    (only_root, [('', 'Main directory')]),
    (three_levels, [
        ('', 'Main directory'),
        ('a', '_A'),
        ('a/c', '__C'),
        ('a/d', '__D'),
        ('b', '_B'),
        ('b/e', '__E'),
        ('b/e/f', '___F'),
    ]),
    (three_levels_leaf_permissions, [
        ('', 'Main directory'),
        ('a', '_A'),
        ('a/d', '__D'),
        ('b', '_B'),
        ('b/e', '__E'),
        ('b/e/f', '___F'),
    ]),
])
def test_recursive_subfolder_choices(make_folder, actual_builder, expected):
    actual = actual_builder(make_folder)
    assert actual.recursive_subfolder_choices() == expected


def test_recursive_subfolder_choices_function_calls(mocker, make_folder):
    """Every folder should only be visited once"""
    spy = mocker.spy(hosts_and_folders.Folder, '_walk_tree')

    tree = three_levels_leaf_permissions(make_folder)
    tree.recursive_subfolder_choices()

    assert spy.call_count == 7
