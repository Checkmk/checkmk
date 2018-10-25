import pytest

import cmk.gui.plugins.visuals
import cmk.gui.visuals as visuals


def test_get_filter():
    f = visuals.get_filter("hostregex")
    assert isinstance(f, cmk.gui.plugins.visuals.Filter)


def test_get_not_existing_filter():
    with pytest.raises(KeyError):
        visuals.get_filter("dingelig")


def test_filters_allowed_for_info():
    allowed = visuals.filters_allowed_for_info("host")
    assert isinstance(allowed["host"], cmk.gui.plugins.visuals.filters.FilterText)
    assert "service" not in allowed


def test_filters_allowed_for_infos():
    allowed = visuals.filters_allowed_for_infos(["host", "service"])
    assert isinstance(allowed["host"], cmk.gui.plugins.visuals.filters.FilterText)
    assert isinstance(allowed["service"], cmk.gui.plugins.visuals.filters.FilterText)
