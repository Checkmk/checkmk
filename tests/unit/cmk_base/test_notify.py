# encoding: utf-8

import os
from cmk_base import notify


def test_os_environment_does_not_override_notification_script_env(monkeypatch):
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, 'environ', {'NOTIFY_CONTACTEMAIL': ''})
    script_env = notify.notification_script_env({'CONTACTEMAIL': 'ab@test.de'})
    assert script_env == {'NOTIFY_CONTACTEMAIL': 'ab@test.de'}
