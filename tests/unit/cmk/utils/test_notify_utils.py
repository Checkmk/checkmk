# encoding: utf-8

import cmk.utils.notify as notify


def test_notification_result_message():
    """Regression test for Werk #8783"""
    plugin, exit_code, output = 'bulk asciimail', 0, []
    context = {'CONTACTNAME': 'harri', 'HOSTNAME': 'test'}
    actual = notify.notification_result_message(plugin, context, exit_code, output)
    expected = "%s: %s;%s;%s;%s;%s;%s" % (
        'HOST NOTIFICATION RESULT',
        'harri',
        'test',
        'OK',
        'bulk asciimail',
        '',
        '',
    )
    assert actual == expected
