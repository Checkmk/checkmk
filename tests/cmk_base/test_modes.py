import pytest
import subprocess

from testlib import web, repo_path

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

    web.delete_host("modes-test-host")
    web.delete_host("modes-test-host2")
    web.delete_host("modes-test-host3")

#.
#   .--General options-----------------------------------------------------.
#   |       ____                           _               _               |
#   |      / ___| ___ _ __   ___ _ __ __ _| |   ___  _ __ | |_ ___         |
#   |     | |  _ / _ \ '_ \ / _ \ '__/ _` | |  / _ \| '_ \| __/ __|        |
#   |     | |_| |  __/ | | |  __/ | | (_| | | | (_) | |_) | |_\__ \_       |
#   |      \____|\___|_| |_|\___|_|  \__,_|_|  \___/| .__/ \__|___(_)      |
#   |                                               |_|                    |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def test_list_hosts(test_cfg, site):
    for opt in [ "--list-hosts", "-l" ]:
        p = site.execute(["cmk", opt], stdout=subprocess.PIPE)
        assert p.wait() == 0
        output = p.stdout.read()
        assert output == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


# TODO: add host to group and test the group filtering of --list-hosts


#.
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'

def test_list_tag_all(test_cfg, site):
    p = site.execute(["cmk", "--list-tag"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    output = p.stdout.read()
    assert output == "modes-test-host\nmodes-test-host2\nmodes-test-host3\n"


def test_list_tag_single_tag_filter(test_cfg, site):
    p = site.execute(["cmk", "--list-tag", "test"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    output = p.stdout.read()
    assert output == "modes-test-host2\nmodes-test-host3\n"


def test_list_tag_offline(test_cfg, site):
    p = site.execute(["cmk", "--list-tag", "offline"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    output = p.stdout.read()
    assert output == "modes-test-host4\n"


def test_list_tag_multiple_tags(test_cfg, site):
    p = site.execute(["cmk", "--list-tag", "test", "xyz"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    output = p.stdout.read()
    assert output == ""


def test_list_tag_multiple_tags_2(test_cfg, site):
    p = site.execute(["cmk", "--list-tag", "test", "cmk-agent"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert p.wait() == 0
    assert p.stderr.read() == ""
    output = p.stdout.read()
    assert output == "modes-test-host2\nmodes-test-host3\n"


#.
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def test_list_checks(test_cfg, site):
    output_long = None
    for opt in [ "--list-checks", "-L" ]:
        p = site.execute(["cmk", opt], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert "zypper" in output
        assert "Check for (security) updates via Zypper" in output
        assert output.count(" snmp ") > 300
        assert output.count(" tcp ") > 200

        if output_long == None:
            output_long = output
        else:
            assert output == output_long


#.
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'

def test_dump_agent_missing_arg(test_cfg, site):
    output_long = None
    for opt in [ "--dump-agent", "-d" ]:
        p = site.execute(["cmk", opt], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert p.wait() == 1


def test_dump_agent_error(test_cfg, site):
    output_long = None
    for opt in [ "--dump-agent", "-d" ]:
        p = site.execute(["cmk", opt, "modes-test-host4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.returncode == 3
        assert stdout == ""
        assert "Problem contacting agent" in stderr

        if output_long == None:
            output_long = stdout
        else:
            assert stdout == output_long


def test_dump_agent_test(test_cfg, site):
    for opt in [ "--dump-agent", "-d" ]:
        p = site.execute(["cmk", opt, "modes-test-host"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.returncode == 0
        assert stderr == ""
        assert stdout == file("%s/tests/data/linux-agent-output" % repo_path()).read()

#.
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'

def test_dump_agent_dump_all_hosts(test_cfg, site):
    for opt in [ "--dump", "-D" ]:
        p = site.execute(["cmk", opt], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert stdout.count("Addresses: ") == 3


def test_dump_agent(test_cfg, site):
    for opt in [ "--dump", "-D" ]:
        p = site.execute(["cmk", opt, "modes-test-host"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert "Addresses: " in stdout
        assert "Type of agent: " in stdout
        assert "Services:" in stdout


#.
#   .--paths---------------------------------------------------------------.
#   |                                  _   _                               |
#   |                      _ __   __ _| |_| |__  ___                       |
#   |                     | '_ \ / _` | __| '_ \/ __|                      |
#   |                     | |_) | (_| | |_| | | \__ \                      |
#   |                     | .__/ \__,_|\__|_| |_|___/                      |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'

def test_paths(test_cfg, site):
    p = site.execute(["cmk", "--paths"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert "Main components of check_mk" in stdout
    assert "Locally installed " in stdout
    assert len(stdout.split("\n")) > 40


#.
#   .--donate--------------------------------------------------------------.
#   |                       _                   _                          |
#   |                    __| | ___  _ __   __ _| |_ ___                    |
#   |                   / _` |/ _ \| '_ \ / _` | __/ _ \                   |
#   |                  | (_| | (_) | | | | (_| | ||  __/                   |
#   |                   \__,_|\___/|_| |_|\__,_|\__\___|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def test_donate_no_hosts(test_cfg, site):
    p = site.execute(["cmk", "--donate"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 1
    assert stderr.startswith("No hosts specified.")
    assert stdout == ""

#.
#   .--backup/restore------------------------------------------------------.
#   |      _                _                  __             _            |
#   |     | |__   __ _  ___| | ___   _ _ __   / / __ ___  ___| |_          |
#   |     | '_ \ / _` |/ __| |/ / | | | '_ \ / / '__/ _ \/ __| __|         |
#   |     | |_) | (_| | (__|   <| |_| | |_) / /| | |  __/\__ \ |_ _        |
#   |     |_.__/ \__,_|\___|_|\_\\__,_| .__/_/ |_|  \___||___/\__(_)       |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'

def test_backup(test_cfg, site):
    p = site.execute(["cmk", "--backup", "x.tgz"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout == ""
    assert site.file_exists("x.tgz")


def test_restore(test_cfg, site):
    # First copy the whole etc/check_mk dir, then restore, then compare
    assert site.execute(["cp", "-pr", "etc/check_mk", "etc/check_mk.sav"]).wait() == 0
    assert site.execute(["rm", "etc/check_mk/main.mk"]).wait() == 0

    p = site.execute(["cmk", "--restore", "x.tgz"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout == ""

    p = site.execute(["diff", "-ur", "etc/check_mk", "etc/check_mk.sav"],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = p.communicate()[0]
    assert p.wait() == 0, "Found differences after restore: %s" % stdout

#.
#   .--package-------------------------------------------------------------.
#   |                                 _                                    |
#   |                _ __   __ _  ___| | ____ _  __ _  ___                 |
#   |               | '_ \ / _` |/ __| |/ / _` |/ _` |/ _ \                |
#   |               | |_) | (_| | (__|   < (_| | (_| |  __/                |
#   |               | .__/ \__,_|\___|_|\_\__,_|\__, |\___|                |
#   |               |_|                         |___/                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--localize------------------------------------------------------------.
#   |                    _                 _ _                             |
#   |                   | | ___   ___ __ _| (_)_______                     |
#   |                   | |/ _ \ / __/ _` | | |_  / _ \                    |
#   |                   | | (_) | (_| (_| | | |/ /  __/                    |
#   |                   |_|\___/ \___\__,_|_|_/___\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--config-check--------------------------------------------------------.
#   |                      __ _                  _               _         |
#   |      ___ ___  _ __  / _(_) __ _        ___| |__   ___  ___| | __     |
#   |     / __/ _ \| '_ \| |_| |/ _` |_____ / __| '_ \ / _ \/ __| |/ /     |
#   |    | (_| (_) | | | |  _| | (_| |_____| (__| | | |  __/ (__|   <      |
#   |     \___\___/|_| |_|_| |_|\__, |      \___|_| |_|\___|\___|_|\_\     |
#   |                           |___/                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--update-dns-cache----------------------------------------------------.
#   |                        _            _                                |
#   |        _   _ _ __   __| |        __| |_ __  ___        ___           |
#   |       | | | | '_ \ / _` | _____ / _` | '_ \/ __|_____ / __|          |
#   |       | |_| | |_) | (_| ||_____| (_| | | | \__ \_____| (__ _         |
#   |        \__,_| .__/ \__,_(_)     \__,_|_| |_|___/      \___(_)        |
#   |             |_|                                                      |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--scan-parents--------------------------------------------------------.
#   |                                                         _            |
#   |    ___  ___ __ _ _ __        _ __   __ _ _ __ ___ _ __ | |_ ___      |
#   |   / __|/ __/ _` | '_ \ _____| '_ \ / _` | '__/ _ \ '_ \| __/ __|     |
#   |   \__ \ (_| (_| | | | |_____| |_) | (_| | | |  __/ | | | |_\__ \     |
#   |   |___/\___\__,_|_| |_|     | .__/ \__,_|_|  \___|_| |_|\__|___/     |
#   |                             |_|                                      |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--nagios-config-------------------------------------------------------.
#   |                     _                                  __ _          |
#   |   _ __   __ _  __ _(_) ___  ___        ___ ___  _ __  / _(_) __ _    |
#   |  | '_ \ / _` |/ _` | |/ _ \/ __|_____ / __/ _ \| '_ \| |_| |/ _` |   |
#   |  | | | | (_| | (_| | | (_) \__ \_____| (_| (_) | | | |  _| | (_| |   |
#   |  |_| |_|\__,_|\__, |_|\___/|___/      \___\___/|_| |_|_| |_|\__, |   |
#   |               |___/                                         |___/    |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--compile-------------------------------------------------------------.
#   |                                           _ _                        |
#   |                  ___ ___  _ __ ___  _ __ (_) | ___                   |
#   |                 / __/ _ \| '_ ` _ \| '_ \| | |/ _ \                  |
#   |                | (_| (_) | | | | | | |_) | | |  __/                  |
#   |                 \___\___/|_| |_| |_| .__/|_|_|\___|                  |
#   |                                    |_|                               |
#   '----------------------------------------------------------------------'
# TODO


#.
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--man-----------------------------------------------------------------.
#   |                                                                      |
#   |                        _ __ ___   __ _ _ __                          |
#   |                       | '_ ` _ \ / _` | '_ \                         |
#   |                       | | | | | | (_| | | | |                        |
#   |                       |_| |_| |_|\__,_|_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--browse-man----------------------------------------------------------.
#   |    _                                                                 |
#   |   | |__  _ __ _____      _____  ___       _ __ ___   __ _ _ __       |
#   |   | '_ \| '__/ _ \ \ /\ / / __|/ _ \_____| '_ ` _ \ / _` | '_ \      |
#   |   | |_) | | | (_) \ V  V /\__ \  __/_____| | | | | | (_| | | | |     |
#   |   |_.__/|_|  \___/ \_/\_/ |___/\___|     |_| |_| |_|\__,_|_| |_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'

def test_inventory_all_hosts(test_cfg, site):
    for opt in [ "--inventory", "-i" ]:
        p = site.execute(["cmk", opt], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert stdout == ""


def test_inventory_single_host(test_cfg, site):
    for opt in [ "--inventory", "-i" ]:
        p = site.execute(["cmk", opt, "modes-test-host"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert stdout == ""


def test_inventory_multiple_hosts(test_cfg, site):
    for opt in [ "--inventory", "-i" ]:
        p = site.execute(["cmk", opt, "modes-test-host", "modes-test-host2"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert stdout == ""


def test_inventory_verbose(test_cfg, site):
    for opt in [ "--inventory", "-i" ]:
        p = site.execute(["cmk", "-v", opt, "modes-test-host"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        assert p.wait() == 0
        assert stderr == ""
        assert stdout.startswith("Doing HW/SW-Inventory for modes-test-host...")
        assert "check_mk " in stdout
        assert "lnx_if " in stdout
        assert "mem " in stdout


#.
#   .--inventory-as-check--------------------------------------------------.
#   | _                      _                              _     _        |
#   |(_)_ ____   _____ _ __ | |_ ___  _ __ _   _        ___| |__ | | __    |
#   || | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |_____ / __| '_ \| |/ /    |
#   || | | | \ V /  __/ | | | || (_) | |  | |_| |_____| (__| | | |   < _   |
#   ||_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |      \___|_| |_|_|\_(_)  |
#   |                                      |___/                           |
#   '----------------------------------------------------------------------'

def test_inventory_as_check_unknown_host(test_cfg, site):
    p = site.execute(["cmk", "--inventory-as-check", "xyz"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 1
    assert stderr == ""
    assert stdout.startswith("WARN - Inventory failed: Cannot resolve")


def test_inventory_as_check(test_cfg, site):
    p = site.execute(["cmk", "--inventory-as-check", "modes-test-host"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout.startswith("OK - found ")


#.
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--notify--------------------------------------------------------------.
#   |                                 _   _  __                            |
#   |                     _ __   ___ | |_(_)/ _|_   _                      |
#   |                    | '_ \ / _ \| __| | |_| | | |                     |
#   |                    | | | | (_) | |_| |  _| |_| |                     |
#   |                    |_| |_|\___/ \__|_|_|  \__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--discover-marked-hosts-----------------------------------------------.
#   |           _ _                                 _            _         |
#   |        __| (_)___  ___   _ __ ___   __ _ _ __| | _____  __| |        |
#   |       / _` | / __|/ __| | '_ ` _ \ / _` | '__| |/ / _ \/ _` |        |
#   |      | (_| | \__ \ (__ _| | | | | | (_| | |  |   <  __/ (_| |        |
#   |       \__,_|_|___/\___(_)_| |_| |_|\__,_|_|  |_|\_\___|\__,_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'

def test_inventory_as_check_unknown_host(test_cfg, site):
    p = site.execute(["cmk", "--check-discovery", "xyz"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 1
    assert stderr == ""
    assert stdout.startswith("WARN - Discovery failed: Name or service not known")


def test_inventory_as_check(test_cfg, site):
    p = site.execute(["cmk", "--check-discovery", "modes-test-host"],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert p.wait() == 0
    assert stderr == ""
    assert stdout.startswith("OK - ")

#.
#   .--discover------------------------------------------------------------.
#   |                     _ _                                              |
#   |                  __| (_)___  ___ _____   _____ _ __                  |
#   |                 / _` | / __|/ __/ _ \ \ / / _ \ '__|                 |
#   |                | (_| | \__ \ (_| (_) \ V /  __/ |                    |
#   |                 \__,_|_|___/\___\___/ \_/ \___|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--version-------------------------------------------------------------.
#   |                                     _                                |
#   |                 __   _____ _ __ ___(_) ___  _ __                     |
#   |                 \ \ / / _ \ '__/ __| |/ _ \| '_ \                    |
#   |                  \ V /  __/ |  \__ \ | (_) | | | |                   |
#   |                   \_/ \___|_|  |___/_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
# TODO

#.
#   .--help----------------------------------------------------------------.
#   |                         _          _                                 |
#   |                        | |__   ___| |_ __                            |
#   |                        | '_ \ / _ \ | '_ \                           |
#   |                        | | | |  __/ | |_) |                          |
#   |                        |_| |_|\___|_| .__/                           |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'
# TODO

