import subprocess
import pytest


@pytest.mark.parametrize("args", [
    [],
    ["-a"],
])
def test_simple_check_mkevents_call(site, args):
    p = site.execute(["./check_mkevents"] + args + ["somehost"],
                     stdout=subprocess.PIPE,
                     cwd=site.path("lib/nagios/plugins"))
    output = p.stdout.read()
    assert output == "OK - no events for somehost\n"
    assert p.wait() == 0
