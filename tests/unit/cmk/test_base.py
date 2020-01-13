import six
import cmk


def test_version():
    assert isinstance(cmk.__version__, six.text_type)


def test_is_enterprise_edition(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_enterprise_edition() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_enterprise_edition() is True
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_enterprise_edition() is True
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_enterprise_edition() is True


def test_is_raw_edition(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_raw_edition() is True
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_raw_edition() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_raw_edition() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_raw_edition() is False


def test_is_demo(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_demo() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_demo() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_demo() is False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_demo() is True
