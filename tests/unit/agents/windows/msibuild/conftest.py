# pylint: disable=redefined-outer-name
from __future__ import print_function

import pytest  # type: ignore
from pathlib2 import Path

import cmk_base.cee.agent_bakery_plugins


@pytest.fixture(autouse=True, scope="session")
def session_info():
    pass


@pytest.fixture()
def conf_dir(tmp_path):
    return tmp_path


@pytest.fixture()
def cmk_dir():
    try:
        p = Path(__file__)
        cmk_root_table = p.parent
        cmk_root = Path(cmk_root_table).joinpath("../../../../..")
        return cmk_root.resolve()
    except IOError as e:
        print("Exception {}".format(e))
        return Path("")
