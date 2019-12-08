#!/usr/bin/env python

import os

import imp
import pytest  # type: ignore[import]

from testlib import repo_path

check_sql = imp.load_source('check_sql', os.path.join(repo_path(), 'active_checks/check_sql'))


@pytest.mark.parametrize("result, warn, crit, reference", [
    ([[3, 'count']], (3, 5), (float('-inf'), 5), (0, 'count: 3.0')),
    ([[2, 'count']], (3, 5), (float('-inf'), 5), (1, 'count: 2.0')),
    ([[5, 'count']], (3, 5), (float('-inf'), 5), (2, 'count: 5.0')),
    ([[5, 'count']], (3, 5), (float('-inf'), 8), (1, 'count: 5.0')),
])
def test_process_result(result, warn, crit, reference):
    assert check_sql.process_result(result, warn, crit) == reference
