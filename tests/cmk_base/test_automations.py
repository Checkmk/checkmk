import pytest
import subprocess

from testlib import web, repo_path
import ast

@pytest.fixture(scope="module")
def test_cfg(web, site):
    print "Applying default config"
    web.add_host("modes-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("modes-test-host2", attributes={
        "ipaddress": "127.0.0.1",
        "tag_criticality": "test",
    })
    web.add_host("modes-test-host3", attributes={
        "ipaddress": "127.0.0.1",
        "tag_criticality": "test",
    })
    web.add_host("modes-test-host4", attributes={
        "ipaddress": "127.0.0.1",
        "tag_criticality": "offline",
    })

    site.write_file("etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n")

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/modes-test-host",
            file("%s/tests/data/linux-agent-output" % repo_path()).read())
    site.write_file("var/check_mk/agent_output/modes-test-host2",
            file("%s/tests/data/linux-agent-output" % repo_path()).read())
    site.write_file("var/check_mk/agent_output/modes-test-host3",
            file("%s/tests/data/linux-agent-output" % repo_path()).read())

    web.discover_services("modes-test-host")
    web.discover_services("modes-test-host2")
    web.discover_services("modes-test-host3")

    web.activate_changes()
    yield None

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    site.delete_dir("var/check_mk/agent_output")

    site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

    web.delete_host("modes-test-host")
    web.delete_host("modes-test-host2")
    web.delete_host("modes-test-host3")
    web.delete_host("modes-test-host4")

#.
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def test_automation_analyse_service_autocheck(test_cfg, site):
    p = site.execute(["cmk", "--automation", "analyse-service", "--", "modes-test-host", "CPU load"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    data = ast.literal_eval(stdout)

    assert data["origin"] == "auto"
    assert data["checktype"] == "cpu.loads"
    assert data["item"] == None
    assert data["checkgroup"] == "cpu_load"


def test_automation_analyse_service_no_check(test_cfg, site):
    p = site.execute(["cmk", "--automation", "analyse-service", "--", "modes-test-host", "XXX CPU load"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout == "{}\n"
