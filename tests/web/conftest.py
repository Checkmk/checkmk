import __builtin__
import sys
import _pytest
import testlib
import cmk

monkeypatch = _pytest.monkeypatch.MonkeyPatch()
# TODO: Use site path (in integration tests)
monkeypatch.syspath_prepend("%s/web/htdocs" % (testlib.cmk_path()))
#monkeypatch.syspath_prepend("/omd/sites/%s/%s/htdocs" % (os.environ["OMD_SITE"], cmk.paths.web_dir))

# Fake the localization wrapper _(...)
monkeypatch.setattr(__builtin__, "_", lambda x: x, raising=False)

# Fake mod_python.apache to make html_mod_python.py stuff importable
class FakeModPythonUnderscoreApache(object):
    # These are all fake values!
    SERVER_RETURN = None
    AP_CONN_UNKNOWN = None
    AP_CONN_CLOSE = None
    AP_CONN_KEEPALIVE = None
    APR_NOFILE = None
    APR_REG = None
    APR_DIR = None
    APR_CHR = None
    APR_BLK = None
    APR_PIPE = None
    APR_LNK = None
    APR_SOCK = None
    APR_UNKFILE = None

    def parse_qs(self, *args, **kwargs):
        raise NotImplemented()

    def parse_qsl(self, *args, **kwargs):
        raise NotImplemented()

    def table(self, *args, **kwargs):
        raise NotImplemented()

    def log_error(self, *args, **kwargs):
        raise NotImplemented()

    def config_tree(self, *args, **kwargs):
        raise NotImplemented()

    def server_root(self, *args, **kwargs):
        raise NotImplemented()

    def mpm_query(self, *args, **kwargs):
        raise NotImplemented()

    def exists_config_define(self, *args, **kwargs):
        raise NotImplemented()

    def stat(self, *args, **kwargs):
        raise NotImplemented()


monkeypatch.setitem(sys.modules, "_apache", FakeModPythonUnderscoreApache())

