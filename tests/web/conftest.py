import __builtin__
import _pytest
import cmk

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
monkeypatch.syspath_prepend("%s/htdocs" % cmk.paths.web_dir)

# Fake the localization wrapper _(...)
monkeypatch.setattr(__builtin__, "_", lambda x: x, raising=False)
