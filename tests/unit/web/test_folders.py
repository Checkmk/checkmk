#!/usr/bin/python
import pytest  # type: ignore[import]

import os
from imp import load_source

if os.path.isfile('../web/htdocs/watolib.py'):
    # don't load the watolib in integration tests
    watolib = load_source('watolib', '../web/htdocs/watolib.py')


@pytest.fixture
def make_folder(mocker):
    """Returns a function to create patched folders for tests."""
    mocker.patch.object(
        watolib.config, 'wato_hide_folders_without_read_permissions', True, create=True)

    def unimplemented(self_, x):
        raise Exception('Wrong code path in __init__')

    mocker.patch.object(watolib.Folder, '_init_by_loading_existing_directory', unimplemented)

    def prefixed_title(self_, current_depth=0):
        return "_" * current_depth + self_.title()

    mocker.patch.object(watolib.Folder, '_prefixed_title', prefixed_title)

    def may(self_, _permission):
        return self_._may_see

    mocker.patch.object(watolib.Folder, 'may', may)

    # convenience method NOT present in Folder
    def add_subfolders(self_, folders):
        for folder in folders:
            self_._subfolders[folder.name()] = folder
            folder._parent = self_
        return self_

    mocker.patch.object(watolib.Folder, 'add_subfolders', add_subfolders, create=True)

    def f(name, title, root_dir='/', parent_folder=None, may_see=True):
        folder = watolib.Folder(
            name, folder_path=None, parent_folder=parent_folder, title=title, root_dir=root_dir)
        folder._may_see = may_see
        return folder

    return f


def only_root(folder):
    return folder('', title='Main directory')


def three_levels(folder):
    return folder(
        '', title='Main directory').add_subfolders([
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
    return folder(
        '', title='Main directory', may_see=False).add_subfolders([
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
    ])
])
def test_recursive_subfolder_choices(make_folder, actual_builder, expected):
    actual = actual_builder(make_folder)
    assert actual.recursive_subfolder_choices() == expected


def test_recursive_subfolder_choices_function_calls(mocker, make_folder):
    """Every folder should only be visited once"""
    spy = mocker.spy(watolib.Folder, '_walk_tree')

    tree = three_levels_leaf_permissions(make_folder)
    tree.recursive_subfolder_choices()

    assert spy.call_count == 7
