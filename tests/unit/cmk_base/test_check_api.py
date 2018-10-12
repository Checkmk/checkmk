import pytest

import cmk_base.discovery as discovery
import cmk_base.config as config
import cmk_base.check_utils
import cmk_base.check_api as check_api
from cmk.exceptions import MKGeneralException

@check_api.get_parsed_item_data
def check_foo(item, params, parsed_item_data):
    return 2, "bar"

def test_get_parsed_item_data():
    params = {}
    parsed = {1: "one", 3: {}, 4: [], 5: ""}
    info = [[1, "one"], [2, "two"]]
    assert check_foo(1, params, parsed) == (2, "bar")
    assert check_foo(2, params, parsed) == None
    assert check_foo(3, params, parsed) == None
    assert check_foo(4, params, parsed) == None
    assert check_foo(5, params, parsed) == None
    assert check_foo(1, params, info) == (3, "Wrong usage of decorator function 'get_parsed_item_data': parsed is not a dict")
    assert check_foo.__name__ == "check_foo"

