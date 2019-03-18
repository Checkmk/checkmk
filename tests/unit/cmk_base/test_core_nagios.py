# encoding: utf-8

import itertools
import cmk_base.core_nagios as core_nagios


def test_format_nagios_object():
    spec = {
        "use": "ding",
        "bla": u"däng",
        "check_interval": u"hüch",
        u"_HÄÄÄÄ": "XXXXXX_YYYY",
    }
    cfg = core_nagios._format_nagios_object("service", spec)
    assert isinstance(cfg, unicode)
    assert cfg == """define service {
  %-29s %s
  %-29s %s
  %-29s %s
  %-29s %s
}

""" % tuple(itertools.chain(*sorted(spec.items(), key=lambda x: x[0])))
