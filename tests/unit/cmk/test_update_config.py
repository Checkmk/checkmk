import argparse
import sys
import StringIO

import cmk.utils.log
import cmk.update_config as update_config
import cmk.gui.config


def test_parse_arguments_defaults():
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose():
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug():
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init():
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_main(monkeypatch):
    buf = StringIO.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: sys.stdout.write("XYZ\n"))
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()
