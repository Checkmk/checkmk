#!/usr/bin/env python
import pytest


def test_sanitize_line(check_manager):
    input = [
        u'cephfs_data', u'1', u'N/A', u'N/A', u'1.6', u'GiB', u'1.97', u'77', u'GiB', u'809',
        u'809', u'33', u'B', u'177', u'KiB', u'4.7', u'GiB'
    ]
    expected = [
        u'cephfs_data', u'1', u'N/A', u'N/A', u'1.6GiB', u'1.97', u'77GiB', u'809', u'809', u'33B',
        u'177KiB', u'4.7GiB'
    ]
    check = check_manager.get_check('ceph_df')
    sanitize_line = check.context['_sanitize_line']
    assert expected == sanitize_line(input)
