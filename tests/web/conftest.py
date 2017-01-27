import __builtin__
import _pytest
import testlib
import cmk

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
# TODO: Use site path (in integration tests)
monkeypatch.syspath_prepend("%s/web/htdocs" % (testlib.cmk_path()))
#monkeypatch.syspath_prepend("/omd/sites/%s/%s/htdocs" % (os.environ["OMD_SITE"], cmk.paths.web_dir))

# Fake the localization wrapper _(...)
monkeypatch.setattr(__builtin__, "_", lambda x: x, raising=False)
