# pylint: disable=redefined-outer-name
import subprocess
import pytest  # type: ignore

from testlib import web  # pylint: disable=unused-import
import cmk_base.config as config
import cmk_base.check_api as check_api
import cmk_base.autochecks as autochecks


@pytest.fixture(scope="module")
def test_cfg(web, site):
    print "Applying default config"
    web.add_host("modes-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['modes-test-host']))\n"
    )

    site.makedirs("var/check_mk/agent_output/")
    web.activate_changes()

    yield None

    #
    # Cleanup code
    #
    print "Cleaning up test config"
    web.delete_host("modes-test-host")


# Test whether or not registration of check configuration variables works
def test_test_check_1(request, test_cfg, site, web):

    test_check_path = "local/share/check_mk/checks/test_check_1"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_1.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_1.mk")

        if site.file_exists("var/check_mk/autochecks/modes-test-host.mk"):
            site.delete_file("var/check_mk/autochecks/modes-test-host.mk")

        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path, """

test_check_1_default_levels = 10.0, 20.0

def inventory(info):
    return [(None, "test_check_1_default_levels")]

def check(item, params, info):
    return 0, "OK - %r" % (test_check_1_default_levels, )

check_info["test_check_1"] = {
    "check_function"          : check,
    "inventory_function"      : inventory,
    "service_description"     : "Testcheck 1",
#    "default_levels_variable" : "test_check_1_default_levels"
}
""")

    site.write_file("var/check_mk/agent_output/modes-test-host", "<<<test_check_1>>>\n1 2\n")

    config.load_checks(check_api.get_check_api_context, ["%s/%s" % (site.root, test_check_path)])
    config.load(with_conf_d=False)

    # Verify that the default variable is in the check context and
    # not in the global checks module context.
    assert "test_check_1_default_levels" not in config.__dict__
    assert "test_check_1" in config._check_contexts
    assert "test_check_1_default_levels" in config._check_contexts["test_check_1"]

    web.discover_services("modes-test-host")

    # Verify that the discovery worked as expected
    services = autochecks.parse_autochecks_file("modes-test-host")
    assert services[0].check_plugin_name == "test_check_1"
    assert services[0].item is None
    assert services[0].parameters_unresolved == "test_check_1_default_levels"
    assert services[0].service_labels.to_dict() == {}

    # Now execute the check function to verify the variable is available
    p = site.execute(["cmk", "-nv", "modes-test-host"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "OK - (10.0, 20.0)" in stdout
    assert stderr == ""
    assert p.returncode == 0

    # And now overwrite the setting in the config
    site.write_file("etc/check_mk/conf.d/test_check_1.mk",
                    "test_check_1_default_levels = 5.0, 30.1\n")

    p = site.execute(["cmk", "-nv", "modes-test-host"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "OK - (10.0, 20.0)" not in stdout
    assert "OK - (5.0, 30.1)" in stdout
    assert stderr == ""
    assert p.returncode == 0


# Test whether or not registration of discovery variables work
def test_test_check_2(request, test_cfg, site, web):
    test_check_path = "local/share/check_mk/checks/test_check_2"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_2.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_2.mk")
        if site.file_exists("var/check_mk/autochecks/modes-test-host.mk"):
            site.delete_file("var/check_mk/autochecks/modes-test-host.mk")
        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path, """

discover_service = False

def inventory(info):
    if discover_service:
        return [(None, {})]

def check(item, params, info):
    return 0, "OK, discovered!"

check_info["test_check_2"] = {
    "check_function"      : check,
    "inventory_function"  : inventory,
    "service_description" : "Testcheck 2",
}
""")

    site.write_file("var/check_mk/agent_output/modes-test-host", "<<<test_check_2>>>\n1 2\n")

    config.load_checks(check_api.get_check_api_context, ["%s/%s" % (site.root, test_check_path)])
    config.load(with_conf_d=False)

    # Verify that the default variable is in the check context and
    # not in the global checks module context
    assert "discover_service" not in config.__dict__
    assert "test_check_2" in config._check_contexts
    assert "discover_service" in config._check_contexts["test_check_2"]

    web.discover_services("modes-test-host")

    # Should have discovered nothing so far
    assert site.read_file("var/check_mk/autochecks/modes-test-host.mk") == "[\n]\n"

    web.discover_services("modes-test-host")

    # And now overwrite the setting in the config
    site.write_file("etc/check_mk/conf.d/test_check_2.mk", "discover_service = True\n")

    web.discover_services("modes-test-host")

    # Verify that the discovery worked as expected
    services = autochecks.parse_autochecks_file("modes-test-host")
    assert services[0].check_plugin_name == "test_check_2"
    assert services[0].item is None
    assert services[0].parameters_unresolved == "{}"
    assert services[0].service_labels.to_dict() == {}


# Test whether or not factory settings and checkgroup parameters work
def test_check_factory_settings(request, test_cfg, site, web):
    test_check_path = "local/share/check_mk/checks/test_check_3"

    def cleanup():
        if site.file_exists("etc/check_mk/conf.d/test_check_3.mk"):
            site.delete_file("etc/check_mk/conf.d/test_check_3.mk")
        if site.file_exists("var/check_mk/autochecks/modes-test-host.mk"):
            site.delete_file("var/check_mk/autochecks/modes-test-host.mk")
        site.delete_file(test_check_path)

    request.addfinalizer(cleanup)

    site.write_file(
        test_check_path, """

factory_settings["test_check_3_default_levels"] = {
    "param1": 123,
}

def inventory(info):
    return [(None, {})]

def check(item, params, info):
    return 0, "OK - %r" % (params, )

check_info["test_check_3"] = {
    "check_function"          : check,
    "inventory_function"      : inventory,
    "service_description"     : "Testcheck 3",
    "group"                   : "asd",
    "default_levels_variable" : "test_check_3_default_levels",
}
""")

    site.write_file("var/check_mk/agent_output/modes-test-host", "<<<test_check_3>>>\n1 2\n")

    config.load_checks(check_api.get_check_api_context, ["%s/%s" % (site.root, test_check_path)])

    # Verify that the default variable is in the check context and
    # not in the global checks module context
    assert "test_check_3_default_levels" not in config.__dict__
    assert "test_check_3" in config._check_contexts
    assert "test_check_3_default_levels" in config._check_contexts["test_check_3"]

    web.discover_services("modes-test-host")

    # Verify that the discovery worked as expected
    services = autochecks.parse_autochecks_file("modes-test-host")
    assert services[0].check_plugin_name == "test_check_3"
    assert services[0].item is None
    assert services[0].parameters_unresolved == "{}"
    assert services[0].service_labels.to_dict() == {}

    # Now execute the check function to verify the variable is available
    p = site.execute(["cmk", "-nv", "modes-test-host"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "OK - {'param1': 123}\n" in stdout
    assert stderr == ""
    assert p.returncode == 0

    # And now overwrite the setting in the config
    site.write_file(
        "etc/check_mk/conf.d/test_check_3.mk", """
checkgroup_parameters.setdefault('asd', [])

checkgroup_parameters['asd'] = [
    ( {'param2': 'xxx'}, [], ALL_HOSTS, {} ),
] + checkgroup_parameters['asd']
""")

    # And execute the check again to check for the parameters
    p = site.execute(["cmk", "-nv", "modes-test-host"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    assert "'param1': 123" in stdout
    assert "'param2': 'xxx'" in stdout
    assert stderr == ""
    assert p.returncode == 0
