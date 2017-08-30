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
#   .--Registration--------------------------------------------------------.
#   |        ____            _     _             _   _                     |
#   |       |  _ \ ___  __ _(_)___| |_ _ __ __ _| |_(_) ___  _ __          |
#   |       | |_) / _ \/ _` | / __| __| '__/ _` | __| |/ _ \| '_ \         |
#   |       |  _ <  __/ (_| | \__ \ |_| | | (_| | |_| | (_) | | | |        |
#   |       |_| \_\___|\__, |_|___/\__|_|  \__,_|\__|_|\___/|_| |_|        |
#   |                  |___/                                               |
#   +----------------------------------------------------------------------+
#   | Check for the loaded automation plugins                              |
#   '----------------------------------------------------------------------'

def test_registered_automations(site):
    import cmk_base.automations
    automations = cmk_base.automations.automations._automations

    needed_automations = [
        'active-check',
        'analyse-service',
        'delete-hosts',
        'diag-host',
        'get-agent-output',
        'get-autochecks',
        'get-check-information',
        'get-check-manpage',
        'get-configuration',
        'get-real-time-checks',
        'inventory',
        'notification-analyse',
        'notification-get-bulks',
        'notification-replay',
        'reload',
        'rename-hosts',
        'restart',
        'scan-parents',
        'set-autochecks',
        'try-inventory',
        'update-dns-cache',
    ]

    if site.version.is_enterprise_edition():
        needed_automations += [
            'bake-agents',
            'get-package-info',
            'get-package',
            'create-package',
            'edit-package',
            'install-package',
            'remove-package',
            'release-package',
            'remove-unpackaged-file',
        ]


    all_automations = sorted(automations.keys())

    assert sorted(needed_automations) == all_automations


#.
#   .--Autom.calls---------------------------------------------------------.
#   |            _         _                             _ _               |
#   |           / \  _   _| |_ ___  _ __ ___    ___ __ _| | |___           |
#   |          / _ \| | | | __/ _ \| '_ ` _ \  / __/ _` | | / __|          |
#   |         / ___ \ |_| | || (_) | | | | | || (_| (_| | | \__ \          |
#   |        /_/   \_\__,_|\__\___/|_| |_| |_(_)___\__,_|_|_|___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Test the command line automation calls                               |
#   '----------------------------------------------------------------------'

def _execute_automation(site, cmd, args=None, stdin=None,
                        expect_stdout=None, expect_stderr="", expect_exit_code=0,
                        parse_data=True):
    if args is None:
        args = []

    if args:
        args = [ "--" ] + args

    p = site.execute(["cmk", "--automation", cmd ] + args,
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                      stdin=subprocess.PIPE)

    stdout, stderr = p.communicate(stdin)

    assert p.wait() == expect_exit_code, "Output: %r, Error: %r" % (stdout, stderr)
    assert stderr == expect_stderr
    if expect_stdout != None:
        assert stdout == expect_stdout

    if parse_data:
        data = ast.literal_eval(stdout)
        return data


def test_automation_discovery_no_host(test_cfg, site):
    p = site.execute(["cmk", "--automation", "inventory", "@raiseerrors", "new" ],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate()
    assert "Need two arguments:" in stderr
    assert stdout == ""
    assert p.wait() == 1


def test_automation_discovery_single_host(test_cfg, site):
    data = _execute_automation(site, "inventory",
            args=["@raiseerrors", "new", "modes-test-host"])

    assert type(data) == tuple
    assert len(data) == 2

    assert len(data[0]) == 1
    assert "modes-test-host" in data[0]
    assert len(data[0]["modes-test-host"]) == 4

    assert data[1] == {}


def test_automation_discovery_multiple_hosts(test_cfg, site):
    data = _execute_automation(site, "inventory",
            args=["@raiseerrors", "new", "modes-test-host", "modes-test-host2"])

    assert type(data) == tuple
    assert len(data) == 2

    assert len(data[0]) == 2
    assert "modes-test-host" in data[0]
    assert "modes-test-host2" in data[0]
    assert len(data[0]["modes-test-host"]) == 4
    assert len(data[0]["modes-test-host2"]) == 4

    assert data[1] == {}


def test_automation_discovery_not_existing_host(test_cfg, site):
    data = _execute_automation(site, "inventory",
            args=["@raiseerrors", "new", "xxxhost"])

    assert type(data) == tuple
    assert len(data) == 2

    assert data[0]["xxxhost"] == [0, 0, 0, 0]
    assert data[1] == {"xxxhost": ''}


def test_automation_discovery_with_cache_option(test_cfg, site):
    data = _execute_automation(site, "inventory",
            args=["@cache", "new", "modes-test-host"])

    assert type(data) == tuple
    assert len(data) == 2

    assert len(data[0]) == 1
    assert "modes-test-host" in data[0]
    assert len(data[0]["modes-test-host"]) == 4

    assert data[1] == {}


def test_automation_analyse_service_autocheck(test_cfg, site):
    data = _execute_automation(site, "analyse-service",
            args=[ "modes-test-host", "CPU load"])

    assert data["origin"] == "auto"
    assert data["checktype"] == "cpu.loads"
    assert data["item"] == None
    assert data["checkgroup"] == "cpu_load"


def test_automation_analyse_service_no_check(test_cfg, site):
    data = _execute_automation(site, "analyse-service",
            args=[ "modes-test-host", "XXX CPU load"])
    assert data == {}


def test_automation_try_discovery_not_existing_host(test_cfg, site):
    data = _execute_automation(site, "try-inventory",
        args=["xxx-not-existing-host"],
        expect_stderr="Failed to lookup IPv4 address of xxx-not-existing-host via DNS: [Errno -2] Name or service not known\n\n",
        expect_stdout="",
        expect_exit_code=2,
        parse_data=False,
    )


def test_automation_try_discovery_host(test_cfg, site):
    data = _execute_automation(site, "try-inventory",
            args=["modes-test-host"])
    print data


def test_automation_get_autochecks_unknown_host(test_cfg, site):
    data = _execute_automation(site, "get-autochecks",
            args=["unknown-host"])
    assert data == []


def test_automation_get_autochecks_known_host(test_cfg, site):
    data = _execute_automation(site, "get-autochecks",
            args=["modes-test-host"])

    assert type(data) == list
    for entry in data:
        assert len(entry) == 4
        checktype, item, resolved_paramstring, paramstring = entry
        assert type(checktype) == str
        assert item is None or type(item) == unicode
        assert type(paramstring) == str


def test_automation_set_autochecks(test_cfg, site):
    new_items = {
        ("df", "xxx")    : "'bla'",
        ("uptime", None) : None,
    }

    data = _execute_automation(site, "set-autochecks",
            args=["blablahost"], stdin=repr(new_items))
    assert data == None

    data = _execute_automation(site, "get-autochecks",
            args=["blablahost"])

    assert sorted(data) == sorted([
        ('df', u'xxx', 'bla', "'bla'"),
        ('uptime', None, None, 'None')
    ])


def test_automation_update_dns_cache(test_cfg, site, web):
    cache_path = 'var/check_mk/ipaddresses.cache'

    if site.file_exists(cache_path):
        site.delete_file(cache_path)

    try:
        web.add_host("update-dns-cache-host")
        web.add_host("localhost")

        data = _execute_automation(site, "update-dns-cache")
        assert type(data) == tuple
        assert len(data) == 2

        assert data[0] > 0
        assert data[1] == ["update-dns-cache-host"]

        assert site.file_exists(cache_path)

        cache = eval(site.read_file(cache_path))
        assert type(cache) == dict
        assert cache[("localhost", 4)] == "127.0.0.1"

    finally:
        web.delete_host("localhost")
        web.delete_host("update-dns-cache-host")


# TODO: Test with the different cores
def test_automation_reload(test_cfg, site):
    data = _execute_automation(site, "reload")
    assert data == []


# TODO: Test with the different cores
def test_automation_restart(test_cfg, site):
    data = _execute_automation(site, "restart")
    assert data == []


def test_automation_get_check_information(test_cfg, site):
    data = _execute_automation(site, "get-check-information")
    assert type(data) == dict
    assert len(data) > 1000

    for check_type, info in data.items():
        assert type(info["title"]) == unicode
        assert "service_description" in info
        assert "snmp" in info


def test_automation_get_real_time_checks(test_cfg, site):
    data = _execute_automation(site, "get-real-time-checks")
    assert type(data) == list
    assert len(data) > 5

    for check_type, title in data:
        assert type(check_type) == str
        assert type(title) == unicode


def test_automation_get_check_manpage(test_cfg, site):
    data = _execute_automation(site, "get-check-manpage",
                args=["uptime"])
    assert type(data) == dict
    assert data["type"] == "check_mk"

    for key in [ "snmp_info", "has_perfdata", "service_description", "group", "header" ]:
        assert key in data

    assert "description" in data["header"]
    assert "title" in data["header"]
    assert "agents" in data["header"]
    assert "license" in data["header"]
    assert "distribution" in data["header"]


def test_automation_notification_replay(test_cfg, site):
    site.write_file("var/check_mk/notify/backlog.mk", "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]")

    data = _execute_automation(site, "notification-replay",
                args=["0"])
    assert data is None


def test_automation_notification_analyse(test_cfg, site):
    site.write_file("var/check_mk/notify/backlog.mk", "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]")

    data = _execute_automation(site, "notification-analyse",
                args=["0"])
    assert type(data) == tuple


def test_automation_notification_get_bulks(test_cfg, site):
    data = _execute_automation(site, "notification-get-bulks",
                args=["0"])
    assert data == []

def test_automation_get_agent_output(test_cfg, site):
    data = _execute_automation(site, "get-agent-output",
                args=["modes-test-host", "agent"])
    assert type(data) == tuple
    assert len(data) == 3

    assert data[0] == True
    assert data[1] == ""

    assert type(data[2]) == str
    assert "<<<uptime>>>" in data[2]


def test_automation_get_agent_output_unknown_host(test_cfg, site):
    data = _execute_automation(site, "get-agent-output",
                args=["xxxhost", "agent"])
    assert type(data) == tuple
    assert len(data) == 3

    assert data[0] == False
    assert data[1].startswith("Failed to fetch data from ")
    assert data[2] == ""


# TODO: active-check: Add test for real active_checks check
# TODO: active-check: Add test for real custom_checks check
def test_automation_active_check_unknown(test_cfg, site):
    data = _execute_automation(site, "active-check",
                args=["xxxhost", "xxxplugin", "xxxitem"])
    assert data is None


def test_automation_active_check_unknown_custom(test_cfg, site):
    data = _execute_automation(site, "active-check",
                args=["xxxhost", "custom", "xxxitem"])
    assert data is None


def test_automation_get_configuration(test_cfg, site):
    variable_names = [
        "agent_port",
    ]

    data = _execute_automation(site, "get-configuration",
                stdin=repr(variable_names))
    assert type(data) == dict
    assert data["agent_port"] == 6556

    try:
        site.write_file("etc/check_mk/main.mk", "agent_port = 6558")

        data = _execute_automation(site, "get-configuration",
                    stdin=repr(variable_names))
        assert data["agent_port"] == 6558

        site.write_file("etc/check_mk/conf.d/agent-port.mk", "agent_port = 1234")

        data = _execute_automation(site, "get-configuration",
                    stdin=repr(variable_names))
        assert data["agent_port"] == 6558

        site.write_file("etc/check_mk/main.mk", "")

        data = _execute_automation(site, "get-configuration",
                    stdin=repr(variable_names))
        assert data["agent_port"] == 6556

        site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        data = _execute_automation(site, "get-configuration",
                    stdin=repr(variable_names))
        assert data["agent_port"] == 6556
    finally:
        if site.file_exists("etc/check_mk/conf.d/agent-port.mk"):
            site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        site.write_file("etc/check_mk/main.mk", "")


# TODO: rename-hosts
# TODO: delete-hosts
# TODO: scan-parents
# TODO: diag-host
