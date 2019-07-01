#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=redefined-outer-name

import os
import glob
import pwd
import time
import pytest
import platform
import re
import requests
import socket
import pathlib2 as pathlib
import pipes
import subprocess
import sys
import shutil
import ast
import fcntl
from contextlib import contextmanager

from urlparse import urlparse
from bs4 import BeautifulSoup

# Disable insecure requests warning message during SSL testing
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import simplejson as json
except ImportError:
    import json


def skip_unwanted_test_types(item):
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


def repo_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def cmk_path():
    return repo_path()


def cmc_path():
    return repo_path() + "/enterprise"


def cme_path():
    return repo_path() + "/managed"


# Directory for persisting variable data produced by tests
def var_dir():
    if "WORKSPACE" in os.environ:
        base_dir = os.environ["WORKSPACE"] + "/results"
    else:
        base_dir = repo_path() + "/tests/var"

    return base_dir


def virtualenv_path():
    try:
        venv = subprocess.check_output(["pipenv", "--bare", "--venv"])
        return pathlib.Path(venv.decode("utf-8").rstrip("\n"))
    except subprocess.CalledProcessError:
        return None


def current_branch_name():
    branch_name = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).split(
        "\n", 1)[0]
    return branch_name.decode("utf-8")


def get_cmk_download_credentials():
    try:
        return tuple(file("%s/.cmk-credentials" % os.environ["HOME"]).read().strip().split(":"))
    except IOError:
        raise Exception("Missing ~/.cmk-credentials file (Create with content: USER:PASSWORD)")


def wait_until(condition, timeout=1, interval=0.1):
    start = time.time()
    while not condition() and time.time() - start < timeout:
        time.sleep(interval)
    if not condition():
        raise Exception(
            "Timeout out waiting for %r to finish (Timeout: %d sec)" % (condition, timeout))


class APIError(Exception):
    pass


# Used fasteners before, but that was using a file mode that made it impossible to do
# inter process locking involving different users (different sites)
@contextmanager
def InterProcessLock(filename):
    fd = None
    try:
        print "[%0.2f] Getting lock: %s" % (time.time(), filename)
        # Need to unset umask here to get the permissions we need because
        # os.open() mode is using the given mode not as absolute mode, but
        # respects the umask "mode & ~umask" (See "man 2 open").
        old_umask = os.umask(0)
        try:
            fd = os.open(filename, os.O_RDONLY | os.O_CREAT, 0666)
        finally:
            os.umask(old_umask)

        # Handle the case where the file has been renamed/overwritten between
        # file creation and locking
        while True:
            fcntl.flock(fd, fcntl.LOCK_EX)

            try:
                fd_new = os.open(filename, os.O_RDONLY | os.O_CREAT, 0666)
            finally:
                os.umask(old_umask)

            if os.path.sameopenfile(fd, fd_new):
                os.close(fd_new)
                break
            else:
                os.close(fd)
                fd = fd_new

        print "[%0.2f] Have lock: %s" % (time.time(), filename)
        yield
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        print "[%0.2f] Released lock: %s" % (time.time(), filename)
        if fd:
            os.close(fd)


def SiteActionLock():
    return InterProcessLock("/tmp/cmk-test-create-site")


# It's ok to make it currently only work on debian based distros
class CMKVersion(object):
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    CEE = "cee"
    CME = "cme"
    CRE = "cre"
    CME = "cme"

    def __init__(self, version, edition, branch):
        self._version = version
        self._edition = edition
        self._branch = branch

        if len(edition) != 3:
            raise Exception("Invalid edition: %s. Must be short notation (cee, cre, ...)")
        self.edition_short = edition

        self.set_version(version, branch)

    def get_default_version(self):
        if os.path.exists("/etc/alternatives/omd"):
            path = os.readlink("/etc/alternatives/omd")
        else:
            path = os.readlink("/omd/versions/default")
        return os.path.split(path)[-1].rsplit(".", 1)[0]

    def set_version(self, version, branch):
        if version in [CMKVersion.DAILY, CMKVersion.GIT]:
            for days_ago in range(
                    7
            ):  # Try a week's worth of versions. If none of these exist, there's likely another issue at play.
                localtime = time.localtime(time.time() - 60 * 60 * 24 * days_ago)

                date_part = time.strftime("%Y.%m.%d", localtime)

                if branch != "master":
                    self.version = "%s-%s" % (branch, date_part)
                else:
                    self.version = date_part

                if self._version_available():
                    break

        elif version == CMKVersion.DEFAULT:
            self.version = self.get_default_version()

        else:
            if ".cee" in version or ".cre" in version:
                raise Exception("Invalid version. Remove the edition suffix!")
            self.version = version

    def branch(self):
        return self._branch

    def edition(self):
        if self.edition_short == CMKVersion.CRE:
            return "raw"
        elif self.edition_short == CMKVersion.CEE:
            return "enterprise"
        elif self.edition_short == CMKVersion.CME:
            return "managed"

    def is_managed_edition(self):
        return self.edition_short == CMKVersion.CME

    def is_enterprise_edition(self):
        return self.edition_short == CMKVersion.CEE

    def is_raw_edition(self):
        return self.edition_short == CMKVersion.CRE

    def _needed_distro(self):
        return os.popen(
            "lsb_release -a 2>/dev/null | grep Codename | awk '{print $2}'").read().strip()

    def _needed_architecture(self):
        return platform.architecture()[0] == "64bit" and "amd64" or "i386"

    def package_name(self):
        return self.package_name_of_distro(self._needed_distro())

    def package_name_of_distro(self, distro):
        return "check-mk-%s-%s_0.%s_%s.deb" % \
                (self.edition(), self.version, distro, self._needed_architecture())

    def package_url(self):
        return "https://mathias-kettner.de/support/%s/%s" % (self.version, self.package_name())

    def _build_system_package_path(self):
        return os.path.join("/bauwelt/download", self.version, self.package_name())

    def version_directory(self):
        return self.omd_version()

    def omd_version(self):
        return "%s.%s" % (self.version, self.edition_short)

    def version_path(self):
        return "/omd/versions/%s" % self.version_directory()

    def is_installed(self):
        return os.path.exists(self.version_path())

    def _version_available(self):
        if self.is_installed():
            return True

        # Use directly from build server in case the tests are executed there
        if os.path.exists(self._build_system_package_path()):
            return True

        response = requests.head(
            self.package_url(), auth=get_cmk_download_credentials(), verify=False)  # nosec
        return response.status_code == 200

    def install(self):
        if os.path.exists(self._build_system_package_path()):
            print "Install from build system package (%s)" % self._build_system_package_path()
            package_path = self._build_system_package_path()
            self._install_package(package_path)

        else:
            print "Install from download portal"
            package_path = self._download_package()
            self._install_package(package_path)
            os.unlink(package_path)

    def _download_package(self):
        temp_package_path = "/tmp/%s" % self.package_name()

        print(self.package_url())
        response = requests.get(
            self.package_url(), auth=get_cmk_download_credentials(), verify=False)  # nosec
        if response.status_code != 200:
            raise Exception("Failed to load package: %s" % self.package_url())
        file(temp_package_path, "w").write(response.content)
        return temp_package_path

    def _install_package(self, package_path):
        # The following gdebi call will fail in case there is another package
        # manager task being active. Try to wait for other task to finish. Sure
        # this is not race free, but hope it's sufficient.
        while os.system("sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1") >> 8 == 0:
            print("Waiting for other dpkg process to complete...\n")
            time.sleep(1)

        # Improve the protection against other test runs installing packages
        with InterProcessLock("/tmp/cmk-test-install-version"):
            cmd = "sudo /usr/bin/gdebi --non-interactive %s" % package_path
            print(cmd)
            sys.stdout.flush()
            if os.system(cmd) >> 8 != 0:  # nosec
                raise Exception("Failed to install package: %s" % package_path)

        assert self.is_installed()


class Site(object):
    def __init__(self,
                 site_id,
                 reuse=True,
                 version=CMKVersion.DEFAULT,
                 edition=CMKVersion.CEE,
                 branch="master"):
        assert site_id
        self.id = site_id
        self.root = "/omd/sites/%s" % self.id
        self.version = CMKVersion(version, edition, branch)

        self.update_with_git = version == CMKVersion.GIT

        self.reuse = reuse

        self.http_proto = "http"
        self.http_address = "127.0.0.1"
        self.url = "%s://%s/%s/check_mk/" % (self.http_proto, self.http_address, self.id)

        self._apache_port = None  # internal cache for the port
        self._livestatus_port = None

        #self._gather_livestatus_port()

    @property
    def apache_port(self):
        if self._apache_port == None:
            self._apache_port = int(self.get_config("APACHE_TCP_PORT"))
        return self._apache_port

    @property
    def internal_url(self):
        return "%s://%s:%s/%s/check_mk/" % (self.http_proto, self.http_address, self.apache_port,
                                            self.id)

    @property
    def livestatus_port(self):
        if self._livestatus_port == None:
            raise Exception("Livestatus TCP not opened yet")
        return self._livestatus_port

    @property
    def live(self):
        import livestatus
        live = livestatus.LocalConnection()
        live.set_timeout(2)
        return live

    def send_host_check_result(self, hostname, state, output, expected_state=None):
        if expected_state is None:
            expected_state = state

        last_check_before = self._get_last_check(hostname)
        schedule_ts, wait_timeout = time.time(), 20

        # Ensure the next check result is not in same second as the previous check
        while int(last_check_before) == int(schedule_ts):
            schedule_ts = time.time()
            time.sleep(0.1)

        #print "last_check_before", last_check_before, "schedule_ts", schedule_ts

        self.live.command(
            "[%d] PROCESS_HOST_CHECK_RESULT;%s;%d;%s" % (schedule_ts, hostname, state, output))
        self._wait_for_next_check(hostname, last_check_before, schedule_ts, wait_timeout,
                                  expected_state)

    def schedule_check(self, hostname, service_description, expected_state):
        last_check_before = self._get_last_check(hostname)
        schedule_ts, wait_timeout = int(time.time()), 20

        # Ensure the next check result is not in same second as the previous check
        while int(last_check_before) == int(schedule_ts):
            schedule_ts = time.time()
            time.sleep(0.1)

        #print "last_check_before", last_check_before, "schedule_ts", schedule_ts
        self.live.command("[%d] SCHEDULE_FORCED_SVC_CHECK;%s;%s;%d" %
                          (schedule_ts, hostname, service_description.encode("utf-8"), schedule_ts))

        self._wait_for_next_check(
            hostname,
            last_check_before,
            schedule_ts,
            wait_timeout,
            expected_state,
            service_description=service_description)

    def _wait_for_next_check(self,
                             hostname,
                             last_check_before,
                             schedule_ts,
                             wait_timeout,
                             expected_state,
                             service_description=None):
        if not service_description:
            table = "hosts"
            filt = "Filter: host_name = %s\n" % hostname
            wait_obj = "%s" % hostname
        else:
            table = "services"
            filt = "Filter: host_name = %s\nFilter: description = %s\n" % (hostname,
                                                                           service_description)
            wait_obj = "%s;%s" % (hostname, service_description)

        last_check, state, plugin_output = self.live.query_row(
            "GET %s\n" \
            "Columns: last_check state plugin_output\n" \
            "%s" \
            "WaitObject: %s\n" \
            "WaitTimeout: %d\n" \
            "WaitCondition: last_check > %d\n" \
            "WaitCondition: state = %d\n" \
            "WaitTrigger: check\n" % (table, filt, wait_obj, wait_timeout*1000, last_check_before, expected_state))

        print "processing check result took %0.2f seconds" % (time.time() - schedule_ts)

        assert last_check > last_check_before, \
                "Check result not processed within %d seconds (last check before reschedule: %d, " \
                "scheduled at: %d, last check: %d)" % \
                (wait_timeout, last_check_before, schedule_ts, last_check)

        assert state == expected_state, \
            "Expected %d state, got %d state, output %s" % (expected_state, state, plugin_output)

    def _get_last_check(self, hostname, service_description=None):
        if not service_description:
            return self.live.query_value(
                "GET hosts\n" \
                "Columns: last_check\n" \
                "Filter: host_name = %s\n" % (hostname))
        else:
            return self.live.query_value(
                "GET services\n" \
                "Columns: last_check\n" \
                "Filter: host_name = %s\n" \
                "Filter: service_description = %s\n" % (hostname, service_description))

    def get_host_state(self, hostname):
        return self.live.query_value("GET hosts\nColumns: state\nFilter: host_name = %s" % hostname)

    def _is_running_as_site_user(self):
        return pwd.getpwuid(os.getuid()).pw_name == self.id

    def execute(self, cmd, *args, **kwargs):
        assert type(cmd) == list, "The command must be given as list"

        if not self._is_running_as_site_user():
            sys.stdout.write("Executing (sudo): %s\n" % subprocess.list2cmdline(cmd))
            cmd = [
                "sudo", "su", "-l", self.id, "-c",
                pipes.quote(" ".join([pipes.quote(p) for p in cmd]))
            ]
            cmd_txt = " ".join(cmd)
            return subprocess.Popen(cmd_txt, shell=True, *args, **kwargs)  # nosec
        else:
            sys.stdout.write("Executing (site): %s\n" % subprocess.list2cmdline(cmd))
            return subprocess.Popen(
                subprocess.list2cmdline(cmd), shell=True, *args, **kwargs)  # nosec

    def omd(self, mode, *args):
        if not self._is_running_as_site_user():
            cmd = ["sudo"]
        else:
            cmd = []

        cmd += ["/usr/bin/omd", mode]

        if not self._is_running_as_site_user():
            cmd += [self.id]
        else:
            cmd += []

        cmd += args

        sys.stdout.write("Executing: %s\n" % subprocess.list2cmdline(cmd))
        return subprocess.call(cmd)

    def path(self, rel_path):
        return os.path.join(self.root, rel_path)

    def read_file(self, rel_path):
        if not self._is_running_as_site_user():
            p = self.execute(["cat", self.path(rel_path)], stdout=subprocess.PIPE)
            if p.wait() != 0:
                raise Exception("Failed to read file %s. Exit-Code: %d" % (rel_path, p.wait()))
            return p.stdout.read()
        else:
            return open(self.path(rel_path)).read()

    def delete_file(self, rel_path):
        if not self._is_running_as_site_user():
            p = self.execute(["rm", "-f", self.path(rel_path)])
            if p.wait() != 0:
                raise Exception("Failed to delete file %s. Exit-Code: %d" % (rel_path, p.wait()))
        else:
            os.unlink(self.path(rel_path))

    def delete_dir(self, rel_path):
        if not self._is_running_as_site_user():
            p = self.execute(["rm", "-rf", self.path(rel_path)])
            if p.wait() != 0:
                raise Exception(
                    "Failed to delete directory %s. Exit-Code: %d" % (rel_path, p.wait()))
        else:
            shutil.rmtree(self.path(rel_path))

    def write_file(self, rel_path, content):
        if not self._is_running_as_site_user():
            p = self.execute(["tee", self.path(rel_path)],
                             stdin=subprocess.PIPE,
                             stdout=open(os.devnull, "w"))
            p.communicate(content)
            p.stdin.close()
            if p.wait() != 0:
                raise Exception("Failed to write file %s. Exit-Code: %d" % (rel_path, p.wait()))
        else:
            return open(self.path(rel_path), "w").write(content)

    def create_rel_symlink(self, link_rel_target, rel_link_name):
        if not self._is_running_as_site_user():
            p = self.execute(["ln", "-s", link_rel_target, rel_link_name],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
            p.communicate()
            if p.wait() != 0:
                raise Exception("Failed to create symlink from %s to ./%s. Exit-Code: %d" %
                                (rel_link_name, link_rel_target, p.wait()))
        else:
            return os.symlink(link_rel_target, os.path.join(self.root, rel_link_name))

    def file_exists(self, rel_path):
        if not self._is_running_as_site_user():
            p = self.execute(["test", "-e", self.path(rel_path)], stdout=subprocess.PIPE)
            return p.wait() == 0
        else:
            return os.path.exists(self.path(rel_path))

    def makedirs(self, rel_path):
        p = self.execute(["mkdir", "-p", self.path(rel_path)])
        return p.wait() == 0

    def cleanup_if_wrong_version(self):
        if not self.exists():
            return

        if self.current_version_directory() == self.version.version_directory():
            return

        # Now cleanup!
        self.rm()

    def current_version_directory(self):
        return os.path.split(os.readlink("/omd/sites/%s/version" % self.id))[-1]

    def create(self):
        if not self.version.is_installed():
            self.version.install()

        if self.update_with_git:
            self._copy_omd_version_for_test()

        if not self.reuse and self.exists():
            raise Exception("The site %s already exists." % self.id)

        if not self.exists():
            with SiteActionLock():
                print "[%0.2f] Creating site '%s'" % (time.time(), self.id)
                p = subprocess.Popen([
                    "/usr/bin/sudo", "/usr/bin/omd", "-V",
                    self.version.version_directory(), "create", "--admin-password", "cmk",
                    "--apache-reload", self.id
                ])
                exit_code = p.wait()
                print("[%0.2f] Executed create command" % time.time())
                assert exit_code == 0
                assert os.path.exists("/omd/sites/%s" % self.id)

            self._set_number_of_helpers()
            self._enable_mod_python_debug()
            self._enabled_liveproxyd_debug_logging()
            self._enable_mkeventd_debug_logging()

        self._install_test_python_modules()

        if self.update_with_git:
            self._update_with_f12_files()

    # When using the Git version, the original version files will be
    # replaced by the .f12 scripts. When tests are running in parallel
    # with the same daily build, this may lead to problems when the .f12
    # scripts are executed while another test is loading affected files
    # As workaround we copy the original files to a test specific version
    def _copy_omd_version_for_test(self):
        if not os.environ.get("BUILD_NUMBER"):
            return  # Don't do this in non CI environments

        src_version, src_path = self.version.version, self.version.version_path()
        new_version_name = "%s-%s" % (src_version, os.environ["BUILD_NUMBER"])
        self.version = CMKVersion(new_version_name, self.version._edition, self.version._branch)

        print("Copy CMK '%s' to '%s'" % (src_path, self.version.version_path()))
        assert not os.path.exists(self.version.version_path()), \
            "New version path '%s' already exists" % self.version.version_path()

        def execute(cmd):
            print("Executing: %s" % cmd)
            rc = os.system(cmd) >> 8  # nosec
            if rc != 0:
                raise Exception("Failed to execute '%s'. Exit code: %d" % (cmd, rc))

        execute("sudo /bin/cp -pr %s %s" % (src_path, self.version.version_path()))

        execute("sudo sed -i \"s|%s|%s|g\" %s/bin/omd" % (src_version, new_version_name,
                                                          self.version.version_path()))

        execute("sudo sed -i \"s|%s|%s|g\" %s/share/omd/omd.info" % (src_version, new_version_name,
                                                                     self.version.version_path()))

        # we should use self.version.version_path() in the RPATH, but that is limited to
        # 32 bytes and our versions exceed this limit. We need to use some hack to make
        # this possible
        if not os.path.exists("/omd/v"):
            execute("sudo /bin/ln -s /omd/versions /omd/v")

        execute("sudo chrpath -r /omd/v/%s/lib %s/bin/python" % (self.version.version_directory(),
                                                                 self.version.version_path()))

        self._add_version_path_to_index_py()

    def _add_version_path_to_index_py(self):
        os.system(  # nosec
              "sudo sed -i '0,/^$/s|^$|import sys ; sys.path.insert(0, \"%s/lib/python\")\\n|' " \
              "%s/share/check_mk/web/htdocs/index.py" % (self.version.version_path(), self.version.version_path()))

    def _update_with_f12_files(self):
        paths = [
            cmk_path() + "/livestatus",
            cmk_path() + "/livestatus/api/python",
            cmk_path() + "/bin",
            cmk_path() + "/modules",
            cmk_path() + "/cmk_base",
            cmk_path() + "/cmk",
            cmk_path() + "/checks",
            cmk_path() + "/checkman",
            cmk_path() + "/web",
            cmk_path() + "/inventory",
            cmk_path() + "/notifications",
            cmk_path() + "/.werks",
        ]

        if os.path.exists(cmc_path()) and not self.version.is_raw_edition():
            paths += [
                cmc_path() + "/bin",
                cmc_path() + "/modules",
                cmc_path() + "/cmk_base",
                cmc_path() + "/cmk",
                cmc_path() + "/web",
                cmc_path() + "/alert_handlers",
                cmc_path() + "/misc",
                # TODO: To be able to build the core correctly we need to build
                # python/boost/python-modules/rrdtool first. Skip cmc for the moment here
                #cmc_path() + "/core",
                cmc_path() + "/agents/bakery",
                cmc_path() + "/agents/plugins",
                cmc_path() + "/agents",
            ]

        if os.path.exists(cme_path()) and self.version.is_managed_edition():
            paths += [
                cme_path(),
                cme_path() + "/cmk_base",
            ]

        # Prevent build problems of livestatus
        print("Cleanup git files")
        assert os.system("sudo git clean -xfd -e .venv") >> 8 == 0

        for path in paths:
            if os.path.exists("%s/.f12" % path):
                print("Executing .f12 in \"%s\"..." % path)
                sys.stdout.flush()
                assert os.system(  # nosec
                    "cd \"%s\" ; "
                    "sudo PATH=$PATH ONLY_COPY=1 ALL_EDITIONS=0 SITE=%s "
                    "CHROOT_BASE_PATH=$CHROOT_BASE_PATH CHROOT_BUILD_DIR=$CHROOT_BUILD_DIR "
                    "bash -x .f12" % (path, self.id)) >> 8 == 0
                print("Executing .f12 in \"%s\" DONE" % path)
                sys.stdout.flush()

        self._add_version_path_to_index_py()

    def _set_number_of_helpers(self):
        self.makedirs("etc/check_mk/conf.d")
        self.write_file("etc/check_mk/conf.d/cmc-helpers.mk", "cmc_cmk_helpers = 5\n")

    def _enabled_liveproxyd_debug_logging(self):
        self.makedirs("etc/check_mk/liveproxyd.d")
        self.write_file("etc/check_mk/liveproxyd.d/logging.mk",
                        "liveproxyd_log_levels = {'cmk.liveproxyd': 10}")

    def _enable_mkeventd_debug_logging(self):
        self.makedirs("etc/check_mk/mkeventd.d")
        self.write_file(
            "etc/check_mk/mkeventd.d/logging.mk", "log_level = %r\n" % {
                'cmk.mkeventd': 10,
                'cmk.mkeventd.EventServer': 10,
                'cmk.mkeventd.EventServer.snmp': 10,
                'cmk.mkeventd.EventStatus': 10,
                'cmk.mkeventd.StatusServer': 10,
                'cmk.mkeventd.lock': 20
            })

    def _enable_mod_python_debug(self):
        path = "etc/check_mk/apache.conf"
        content = self.read_file(path)

        self.write_file(
            path,
            content.replace("PythonHandler index", "PythonHandler index\n        PythonDebug On"))

    def _install_test_python_modules(self):
        venv = virtualenv_path()
        bin_dir = venv / "bin"
        packages_dir = venv / "lib/python2.7/site-packages"

        for file_name in os.listdir(str(packages_dir)):
            #if "cffi" in file_name:
            #    continue

            assert os.system("sudo rsync -a --chown %s:%s %s %s/local/lib/python/" %  # nosec
                             (self.id, self.id, packages_dir / file_name, self.root)) >> 8 == 0

        for file_name in ["py.test", "pytest"]:
            assert os.system("sudo rsync -a --chown %s:%s %s %s/local/bin" %  # nosec
                             (self.id, self.id, bin_dir / file_name, self.root)) >> 8 == 0

    def rm_if_not_reusing(self):
        if not self.reuse:
            self.rm()

    def rm(self, site_id=None):
        if site_id == None:
            site_id = self.id

        with SiteActionLock():
            # TODO: LM: Temporarily disabled until "omd rm" issue is fixed.
            #assert subprocess.Popen(["/usr/bin/sudo", "/usr/bin/omd",
            subprocess.Popen(
                ["/usr/bin/sudo", "/usr/bin/omd", "-f", "rm", "--apache-reload", "--kill",
                 site_id]).wait()

    def cleanup_old_sites(self, cleanup_pattern):
        if not os.path.exists("/omd/sites"):
            return

        for site_id in os.listdir("/omd/sites"):
            if site_id != self.id and site_id.startswith(cleanup_pattern):
                print "Cleaning up old site: %s" % site_id
                self.rm(site_id)

    def start(self):
        if not self.is_running():
            assert self.omd("start") == 0
            i = 0
            while not self.is_running():
                i += 1
                if i > 10:
                    self.execute(["/usr/bin/omd", "status"]).wait()
                    raise Exception("Could not start site %s" % self.id)
                print("The site %s is not running yet, sleeping... (round %d)" % (self.id, i))
                sys.stdout.flush()
                time.sleep(0.2)

    def stop(self):
        if self.is_running():
            assert self.omd("stop") == 0
            i = 0
            while self.is_running():
                i += 1
                if i > 10:
                    raise Exception("Could not stop site %s" % self.id)
                print("The site %s is still running, sleeping... (round %d)" % (self.id, i))
                sys.stdout.flush()
                time.sleep(0.2)

    def exists(self):
        return os.path.exists("/omd/sites/%s" % self.id)

    def is_running(self):
        return self.execute(["/usr/bin/omd", "status", "--bare"], stdout=open(os.devnull,
                                                                              "w")).wait() == 0

    def set_config(self, key, val, with_restart=False):
        if self.get_config(key) == val:
            print "omd config: %s is already at %r" % (key, val)
            return

        if with_restart:
            print "Stopping site"
            self.stop()

        print "omd config: Set %s to %r" % (key, val)
        assert self.omd("config", "set", key, val) == 0

        if with_restart:
            self.start()
            print "Started site"

    def set_core(self, core):
        self.set_config("CORE", core, with_restart=True)

    def get_config(self, key):
        p = self.execute(["omd", "config", "show", key],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print stderr
        return stdout.strip()

    # These things are needed to make the site basically being setup. So this
    # is checked during site initialization instead of a dedicated test.
    def verify_cmk(self):
        p = self.execute(["cmk", "--help"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         close_fds=True)
        stdout = p.communicate()[0]
        assert p.returncode == 0, "Failed to execute 'cmk': %s" % stdout

        p = self.execute(["cmk", "-U"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         close_fds=True)
        stdout = p.communicate()[0]
        assert p.returncode == 0, "Failed to execute 'cmk -U': %s" % stdout

    def prepare_for_tests(self):
        self.verify_cmk()
        self.init_wato()

    def init_wato(self):
        if not self._missing_but_required_wato_files():
            print "WATO is already initialized -> Skipping initializiation"
            return

        web = CMKWebSession(self)
        web.login()
        web.set_language("en")

        # Call WATO once for creating the default WATO configuration
        response = web.get("wato.py").text
        assert "<title>WATO" in response
        assert "<div class=\"title\">Manual Checks</div>" in response, \
                "WATO does not seem to be initialized: %r" % response

        wait_time = 10
        while self._missing_but_required_wato_files() and wait_time >= 0:
            time.sleep(0.5)
            wait_time -= 0.5

        missing_files = self._missing_but_required_wato_files()
        assert not missing_files, \
            "Failed to initialize WATO data structures " \
            "(Still missing: %s)" % missing_files

        self._add_wato_test_config(web)

    # Add some test configuration that is not test specific. These settings are set only to have a
    # bit more complex Check_MK config.
    def _add_wato_test_config(self, web):
        # This entry is interesting because it is a check specific setting. These
        # settings are only registered during check loading. In case one tries to
        # load the config without loading the checks in advance, this leads into an
        # exception.
        # We set this config option here trying to catch this kind of issue.
        web.set_ruleset(
            "fileinfo_groups",
            {
                "ruleset": {
                    "": [  # "" -> folder
                        {
                            'conditions': {
                                'host_specs': ['@all'],
                                'host_tags': []
                            },
                            'options': {},
                            'path': '',
                            'value': [('TESTGROUP', ('*gwia*', ''))]
                        },
                    ],
                }
            })

    def _missing_but_required_wato_files(self):
        required_files = [
            "etc/check_mk/conf.d/wato/rules.mk", "etc/check_mk/multisite.d/wato/hosttags.mk",
            "etc/check_mk/conf.d/wato/global.mk", "var/check_mk/web/automation",
            "var/check_mk/web/automation/automation.secret"
        ]

        missing = []
        for f in required_files:
            if not self.file_exists(f):
                missing.append(f)
        return missing

    # For reliable testing we need the site environment. The only environment for executing
    # Check_MK is now the site, so all tests that somehow rely on the environment should be
    # executed this way.
    def switch_to_site_user(self):
        env_vars = {
            "VERSION": self.version._version,
            "REUSE": "1" if self.reuse else "0",
        }
        for varname in [
                "WORKSPACE", "PYTEST_ADDOPTS", "BANDIT_OUTPUT_ARGS", "SHELLCHECK_OUTPUT_ARGS",
                "PYLINT_ARGS"
        ]:
            if varname in os.environ:
                env_vars[varname] = os.environ[varname]

        env_var_str = " ".join(["%s=%s" % (k, pipes.quote(v)) for k, v in env_vars.items()]) + " "

        cmd_parts = [
            "python",
            self.path("local/bin/py.test"),
        ] + sys.argv[1:]

        cmd = "cd %s && " % pipes.quote(cmk_path())
        cmd += env_var_str + subprocess.list2cmdline(cmd_parts)
        print cmd
        args = ["/usr/bin/sudo", "--", "/bin/su", "-l", self.id, "-c", cmd]
        return subprocess.call(args)

    # This opens a currently free TCP port and remembers it in the object for later use
    # Not free of races, but should be sufficient.
    def open_livestatus_tcp(self):
        start_again = False

        if self.is_running():
            start_again = True
            self.stop()

        with InterProcessLock("/tmp/cmk-test-livestatus-port"):
            self.set_config("LIVESTATUS_TCP", "on")
            self._gather_livestatus_port()
            self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))

            if start_again:
                self.start()

    def _gather_livestatus_port(self):
        if self.reuse and self.exists():
            port = int(self.get_config("LIVESTATUS_TCP_PORT"))
        else:
            port = self.get_free_port_from(9123)

        self._livestatus_port = port

    def get_free_port_from(self, port):
        used_ports = set([])
        for cfg_path in glob.glob("/omd/sites/*/etc/omd/site.conf"):
            for line in open(cfg_path):
                if line.startswith("CONFIG_LIVESTATUS_TCP_PORT="):
                    port = int(line.strip().split("=", 1)[1].strip("'"))
                    used_ports.add(port)

        while port in used_ports:
            port += 1

        print "Livestatus ports already in use: %r, using port: %d" % (used_ports, port)
        return port

    # Problem: The group change only affects new sessions of the test_user
    #def add_test_user_to_site_group(self):
    #    test_user = pwd.getpwuid(os.getuid())[0]

    #    if os.system("sudo usermod -a -G %s %s" % (self.id, test_user)) >> 8 != 0:
    #        raise Exception("Failed to add test user \"%s\" to site group")


class WebSession(requests.Session):
    def __init__(self):
        self.transids = []
        # Resources are only fetched and verified once per session
        self.verified_resources = set()
        self.via_system_apache = False
        super(WebSession, self).__init__()

    def check_redirect(self, path, proto="http", expected_code=302, expected_target=None):
        url = self.url(proto, path)

        response = self.get(path, expected_code=expected_code, allow_redirects=False)
        if expected_target:
            assert response.headers['Location'] == expected_target

    def get(self, *args, **kwargs):
        return self._request("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._request("post", *args, **kwargs)

    def _request(self,
                 method,
                 path,
                 proto="http",
                 expected_code=200,
                 expect_redirect=None,
                 allow_errors=False,
                 add_transid=False,
                 allow_redirect_to_login=False,
                 allow_retry=True,
                 **kwargs):
        url = self.url(proto, path)

        if add_transid:
            url = self._add_transid(url)

        # Enforce non redirect following in case of expecting one
        if expect_redirect:
            kwargs["allow_redirects"] = False

        if method == "post":
            func = super(WebSession, self).post
        else:
            func = super(WebSession, self).get

        # May raise "requests.exceptions.ConnectionError: ('Connection aborted.', BadStatusLine("''",))"
        # suddenly without known reason. This may be related to some
        # apache or HTTP/1.1 issue when working with keepalive connections. See
        #   https://www.google.de/search?q=connection+aborted+Connection+aborted+bad+status+line
        #   https://github.com/mikem23/keepalive-race
        # Trying to workaround this by trying the problematic request a second time.
        try:
            response = func(url, **kwargs)
        except requests.ConnectionError, e:
            if allow_retry and "Connection aborted" in "%s" % e:
                response = func(url, **kwargs)
            else:
                raise

        self._handle_http_response(response, expected_code, allow_errors, expect_redirect,
                                   allow_redirect_to_login)
        return response

    def _add_transid(self, url):
        if not self.transids:
            raise Exception('Tried to add a transid, but none available at the moment')

        if "?" in url:
            url += "&"
        else:
            url += "?"
        url += "_transid=" + self.transids.pop()
        return url

    def _handle_http_response(self, response, expected_code, allow_errors, expect_redirect,
                              allow_redirect_to_login):
        assert "Content-Type" in response.headers

        # TODO: Copied from CMA tests. Needed?
        # Apache error responses are sent as ISO-8859-1. Ignore these pages.
        #if r.status_code == 200 \
        #   and (not self._allow_wrong_encoding and not mime_type.startswith("image/")):
        #    assert r.encoding == "UTF-8", "Got invalid encoding (%s) for URL %s" % (r.encoding, r.url))

        mime_type = self._get_mime_type(response)

        if expect_redirect:
            expected_code, redirect_target = expect_redirect
            assert response.headers["Location"] == redirect_target, \
                "Expected %d redirect to %s but got this location: %s" % \
                    (expected_code, redirect_target,
                     response.headers.get('Location', "None"))

        assert response.status_code == expected_code, \
            "Got invalid status code (%d != %d) for URL %s (Location: %s)" % \
                  (response.status_code, expected_code,
                   response.url, response.headers.get('Location', "None"))

        if response.history:
            #print "Followed redirect (%d) %s -> %s" % \
            #    (response.history[0].status_code, response.history[0].url, response.url)
            if not allow_redirect_to_login:
                assert "check_mk/login.py" not in response.url, \
                       "Followed redirect (%d) %s -> %s" % \
                    (response.history[0].status_code, response.history[0].url, response.url)

        if mime_type == "text/html":
            self._check_html_page(response, allow_errors)

    def _get_mime_type(self, response):
        return response.headers["Content-Type"].split(";", 1)[0]

    def _check_html_page(self, response, allow_errors):
        self._extract_transids(response.text)
        self._find_errors(response.text, allow_errors)
        self._check_html_page_resources(response)

    def _extract_transids(self, body):
        # Extract transids from the pages to be used in later actions
        # issued by the tests
        matches = re.findall('name="_transid" value="([^"]+)"', body)
        matches += re.findall('_transid=([0-9/]+)', body)
        for match in matches:
            self.transids.append(match)

    def _find_errors(self, body, allow_errors):
        matches = re.search('<div class=error>(.*?)</div>', body, re.M | re.DOTALL)
        if allow_errors and matches:
            print "Found error message, but it's allowed: %s" % matches.groups()
        else:
            assert not matches, "Found error message: %s" % matches.groups()

    def _check_html_page_resources(self, response):
        soup = BeautifulSoup(response.text, "lxml")

        # There might be other resources like iframe, audio, ... but we don't care about them

        self._check_resources(soup, response, "img", "src", ["image/png"])
        self._check_resources(soup, response, "script", "src", ["application/javascript"])
        self._check_resources(
            soup, response, "link", "href", ["text/css"], filters=[("rel", "stylesheet")])
        self._check_resources(
            soup,
            response,
            "link",
            "href", ["image/vnd.microsoft.icon"],
            filters=[("rel", "shortcut icon")])

    def _check_resources(self, soup, response, tag, attr, allowed_mime_types, filters=None):
        parsed_url = urlparse(response.url)

        base_url = parsed_url.path
        if ".py" in base_url:
            base_url = os.path.dirname(base_url)

        for url in self._find_resource_urls(tag, attr, soup, filters):
            # Only check resources once per session
            if url in self.verified_resources:
                continue
            self.verified_resources.add(url)

            assert not url.startswith("/")
            req = self.get(base_url + "/" + url, proto=parsed_url.scheme, verify=False)

            mime_type = self._get_mime_type(req)
            assert mime_type in allowed_mime_types

    def _find_resource_urls(self, tag, attribute, soup, filters=None):
        urls = []

        for element in soup.findAll(tag):
            try:
                skip = False
                for attr, val in filters or []:
                    if element[attr] != val:
                        skip = True
                        break

                if not skip:
                    urls.append(element[attribute])
            except KeyError:
                pass

        return urls

    def login(self, username=None, password=None):
        raise NotImplementedError()

    def logout(self):
        raise NotImplementedError()


class CMKWebSession(WebSession):
    def __init__(self, site):
        self.site = site
        super(CMKWebSession, self).__init__()

    # Computes a full URL inkl. http://... from a URL starting with the path.
    def url(self, proto, path):
        assert not path.startswith("http")
        assert "://" not in path

        # In case no path component is in URL, add the path to the "/[site]/check_mk"
        if "/" not in urlparse(path).path:
            path = "/%s/check_mk/%s" % (self.site.id, path)

        if self.via_system_apache:
            return '%s://%s%s' % (self.site.http_proto, self.site.http_address, path)
        else:
            return '%s://%s:%d%s' % (self.site.http_proto, self.site.http_address,
                                     self.site.apache_port, path)

    def login(self, username="cmkadmin", password="cmk"):
        login_page = self.get("", allow_redirect_to_login=True).text
        assert "_username" in login_page, "_username not found on login page - page broken?"
        assert "_password" in login_page
        assert "_login" in login_page

        r = self.post(
            "login.py",
            data={
                "filled_in": "login",
                "_username": username,
                "_password": password,
                "_login": "Login",
            })
        auth_cookie = r.cookies.get("auth_%s" % self.site.id)
        assert auth_cookie
        assert auth_cookie.startswith("%s:" % username)

        assert "side.py" in r.text
        assert "dashboard.py" in r.text

    def set_language(self, lang):
        lang = "" if lang == "en" else lang

        profile_page = self.get("user_profile.py").text
        assert "name=\"language\"" in profile_page

        if lang:
            assert "value=\"" + lang + "\"" in profile_page

        r = self.post(
            "user_profile.py",
            data={
                "filled_in": "profile",
                "_set_lang": "on",
                "ua_start_url_use": "0",
                "ua_ui_theme_use": "0",
                "language": lang,
                "_save": "Save",
            },
            add_transid=True)

        if lang == "":
            assert "Successfully updated" in r.text, "Body: %s" % r.text
        else:
            assert "Benutzerprofil erfolgreich aktualisiert" in r.text, "Body: %s" % r.text

    def logout(self):
        r = self.get("logout.py", allow_redirect_to_login=True)
        assert "action=\"login.py\"" in r.text

    #
    # Web-API for managing hosts, services etc.
    #

    def _automation_credentials(self):
        secret = self.site.read_file("var/check_mk/web/automation/automation.secret")

        if secret == "":
            raise Exception("Failed to read secret from %s" % secret_path)

        return {
            "_username": "automation",
            "_secret": secret,
        }

    def _api_request(self, url, data, expect_error=False, output_format="json"):
        data.update(self._automation_credentials())

        req = self.post(url, data=data)

        if output_format == "json":
            response = json.loads(req.text)
        elif output_format == "python":
            response = ast.literal_eval(req.text)
        else:
            raise NotImplementedError()

        assert req.headers["access-control-allow-origin"] == "*"

        if not expect_error:
            assert response["result_code"] == 0, \
                   "An error occured: %r" % response
        else:
            raise APIError(response["result"])

        return response["result"]

    def add_host(self,
                 hostname,
                 folder="",
                 attributes=None,
                 cluster_nodes=None,
                 create_folders=True,
                 expect_error=False):
        if attributes == None:
            attributes = {}

        result = self._api_request(
            "webapi.py?action=add_host", {
                "request":
                    json.dumps({
                        "hostname": hostname,
                        "folder": folder,
                        "attributes": attributes or {},
                        "create_folders": create_folders,
                        "nodes": cluster_nodes,
                    }),
            },
            expect_error=expect_error)

        assert result == None

        host = self.get_host(hostname)

        assert host["hostname"] == hostname
        assert host["path"] == folder
        assert host["attributes"] == attributes

    def get_host(self, hostname, effective_attributes=False):
        result = self._api_request(
            "webapi.py?action=get_host", {
                "request":
                    json.dumps({
                        "hostname": hostname,
                        "effective_attributes": effective_attributes,
                    }),
            })

        assert type(result) == dict
        assert "hostname" in result
        assert "path" in result
        assert "attributes" in result

        return result

    def host_exists(self, hostname):
        try:
            result = self._api_request("webapi.py?action=get_host", {
                "request": json.dumps({
                    "hostname": hostname,
                }),
            })
        except AssertionError, e:
            if "No such host" in "%s" % e:
                return False
            else:
                raise

        assert type(result) == dict
        return "hostname" in result

    def add_folder(self, folder_path, attributes=None, create_folders=True, expect_error=False):
        if attributes == None:
            attributes = {}

        result = self._api_request(
            "webapi.py?action=add_folder", {
                "request":
                    json.dumps({
                        "folder": folder_path,
                        "attributes": attributes or {},
                        "create_parent_folders": create_folders,
                    }),
            },
            expect_error=expect_error)

        assert result == None

        folder = self.get_folder(folder_path)
        assert folder["attributes"] == attributes

    def get_folder(self, folder_path, effective_attributes=False):
        result = self._api_request(
            "webapi.py?action=get_folder", {
                "request":
                    json.dumps({
                        "folder": folder_path,
                        "effective_attributes": effective_attributes,
                    }),
            })

        assert type(result) == dict
        assert "attributes" in result

        return result

    def folder_exists(self, folder_path):
        try:
            result = self._api_request("webapi.py?action=get_folder", {
                "request": json.dumps({
                    "folder": folder_path,
                }),
            })
        except AssertionError, e:
            if "does not exist" in "%s" % e:
                return False
            else:
                raise

        assert type(result) == dict
        return "folder" in result

    def delete_folder(self, folder_path):
        result = self._api_request("webapi.py?action=delete_folder", {
            "request": json.dumps({
                "folder": folder_path,
            }),
        })

        assert result == None
        assert not self.folder_exists(folder_path)

    def get_ruleset(self, ruleset_name):
        result = self._api_request(
            "webapi.py?action=get_ruleset&output_format=python", {
                "request": json.dumps({
                    "ruleset_name": ruleset_name,
                }),
            },
            output_format="python")

        assert type(result) == dict
        assert "ruleset" in result
        assert "configuration_hash" in result

        return result

    def set_ruleset(self, ruleset_name, ruleset_spec):
        request = {
            "ruleset_name": ruleset_name,
        }
        request.update(ruleset_spec)

        result = self._api_request(
            "webapi.py?action=set_ruleset&output_format=python&request_format=python", {
                "request": repr(request),
            },
            output_format="python")

        assert result == None

    def get_all_hosts(self, effective_attributes=False):
        result = self._api_request("webapi.py?action=get_all_hosts", {
            "request": json.dumps({
                "effective_attributes": effective_attributes,
            }),
        })

        assert type(result) == dict
        return result

    def delete_host(self, hostname):
        result = self._api_request("webapi.py?action=delete_host", {
            "request": json.dumps({
                "hostname": hostname,
            }),
        })

        assert result == None

        hosts = self.get_all_hosts()
        assert hostname not in hosts

    def get_all_groups(self, group_type):
        result = self._api_request("webapi.py?action=get_all_%sgroups" % group_type, {})
        return result

    def add_group(self, group_type, group_name, attributes, expect_error=False):
        request_object = {"groupname": group_name}
        request_object.update(attributes)

        result = self._api_request(
            "webapi.py?action=add_%sgroup" % group_type, {"request": json.dumps(request_object)},
            expect_error=expect_error)

        assert result == None

    def edit_group(self, group_type, group_name, attributes, expect_error=False):
        request_object = {"groupname": group_name}
        request_object.update(attributes)

        result = self._api_request(
            "webapi.py?action=edit_%sgroup" % group_type, {"request": json.dumps(request_object)},
            expect_error=expect_error)

        assert result == None

    def delete_group(self, group_type, group_name, expect_error=False):
        result = self._api_request(
            "webapi.py?action=delete_%sgroup" % group_type,
            {"request": json.dumps({
                "groupname": group_name,
            })},
            expect_error=expect_error)

        assert result == None

    def get_all_users(self):
        return self._api_request("webapi.py?action=get_all_users", {})

    def add_htpasswd_users(self, users):
        result = self._api_request("webapi.py?action=add_users",
                                   {"request": json.dumps({"users": users})})
        assert result == None

    def edit_htpasswd_users(self, users):
        result = self._api_request("webapi.py?action=edit_users",
                                   {"request": json.dumps({"users": users})})

        assert result == None

    def delete_htpasswd_users(self, userlist):
        result = self._api_request("webapi.py?action=delete_users", {
            "request": json.dumps({"users": userlist}),
        })
        assert result == None

    def discover_services(self, hostname, mode=None):
        request = {
            "hostname": hostname,
        }

        if mode != None:
            request["mode"] = mode

        result = self._api_request("webapi.py?action=discover_services", {
            "request": json.dumps(request),
        })

        assert type(result) == unicode
        assert result.startswith("Service discovery successful"), "Failed to discover: %r" % result

    def activate_changes(self, mode=None, allow_foreign_changes=None):
        request = {}

        if mode != None:
            request["mode"] = mode

        if allow_foreign_changes != None:
            request["allow_foreign_changes"] = "1" if allow_foreign_changes else "0"

        old_t = self.site.live.query_value("GET status\nColumns: program_start\n")

        time_started = time.time()
        result = self._api_request("webapi.py?action=activate_changes", {
            "request": json.dumps(request),
        })

        assert type(result) == dict
        assert len(result["sites"]) > 0

        for site_id, status in result["sites"].items():
            assert status["_state"] == "success", \
                "Failed to activate %s: %r" % (site_id, status)
            assert status["_time_ended"] > time_started

        # Activating changes can involve an asynchronous(!) monitoring
        # core restart/reload, so e.g. querying a Livestatus table immediately
        # might not reflect the changes yet. Ask the core for a successful reload.
        def config_reloaded():
            new_t = self.site.live.query_value("GET status\nColumns: program_start\n")
            return new_t > old_t

        reload_time, timeout = time.time(), 10
        while not config_reloaded():
            if time.time() > reload_time + timeout:
                raise Exception("Config did not update within %d seconds" % timeout)
            time.sleep(0.2)

        assert config_reloaded()

    def get_regular_graph(self, hostname, service_description, graph_index, expect_error=False):
        result = self._api_request(
            "webapi.py?action=get_graph", {
                "request":
                    json.dumps({
                        "specification": [
                            "template",
                            {
                                "service_description": service_description,
                                "site": self.site.id,
                                "graph_index": graph_index,
                                "host_name": hostname,
                            }
                        ],
                        "data_range": {
                            "time_range": [time.time() - 3600, time.time()]
                        }
                    }),
            },
            expect_error=expect_error)

        assert type(result) == dict
        assert "start_time" in result
        assert type(result["start_time"]) == int
        assert "end_time" in result
        assert type(result["end_time"]) == int
        assert "step" in result
        assert type(result["step"]) == int
        assert "curves" in result
        assert type(result["curves"]) == list
        assert len(result["curves"]) > 0

        for curve in result["curves"]:
            assert "color" in curve
            assert "rrddata" in curve
            assert "line_type" in curve
            assert "title" in curve

        return result


class CMKEventConsole(CMKWebSession):
    def __init__(self, site):
        super(CMKEventConsole, self).__init__(site)
        #self._gather_status_port()
        self.status = CMKEventConsoleStatus("%s/tmp/run/mkeventd/status" % site.root)

    def _config(self):
        cfg = {}
        content = self.site.read_file("etc/check_mk/mkeventd.d/wato/global.mk")
        exec (content, {}, cfg)
        return cfg

    def _gather_status_port(self):
        config = self._config()

        if self.site.reuse and self.site.exists() and "remote_status" in config:
            port = config["remote_status"][0]
        else:
            port = self.site.get_free_port_from(self.site.livestatus_port + 1)

        self.status_port = port

    def enable_remote_status_port(self, web):
        html = web.get("wato.py?mode=mkeventd_config").text
        assert "mode=mkeventd_edit_configvar&amp;site=&amp;varname=remote_status" in html

        html = web.get(
            "wato.py?folder=&mode=mkeventd_edit_configvar&site=&varname=remote_status").text
        assert "Save" in html

        html = web.post(
            "wato.py",
            data={
                "filled_in": "value_editor",
                "ve_use": "on",
                "ve_value_0": self.status_port,
                "ve_value_2_use": "on",
                "ve_value_2_value_0": "127.0.0.1",
                "save": "Save",
                "varname": "remote_status",
                "mode": "mkeventd_edit_configvar",
            },
            add_transid=True).text
        assert "%d, no commands, 127.0.0.1" % self.status_port in html

    def activate_changes(self, web):
        old_t = web.site.live.query_value(
            "GET eventconsolestatus\nColumns: status_config_load_time\n")
        #print "Old config load time: %s" % old_t
        assert old_t > time.time() - 86400

        super(CMKEventConsole, self).activate_changes(allow_foreign_changes=True)

        def config_reloaded():
            new_t = web.site.live.query_value(
                "GET eventconsolestatus\nColumns: status_config_load_time\n")
            #print "New config load time: %s" % new_t
            return new_t > old_t

        reload_time, timeout = time.time(), 10
        while not config_reloaded():
            if time.time() > reload_time + timeout:
                raise Exception("Config did not update within %d seconds" % timeout)
            time.sleep(0.2)

        assert config_reloaded()

    @classmethod
    def new_event(cls, attrs):
        default_event = {
            "rule_id": 815,
            "text": "",
            "phase": "open",
            "count": 1,
            "time": time.time(),
            "first": time.time(),
            "last": time.time(),
            "comment": "",
            "host": "test-host",
            "ipaddress": "127.0.0.1",
            "application": "",
            "pid": 0,
            "priority": 3,
            "facility": 1,  # user
            "match_groups": (),
        }

        event = default_event.copy()
        event.update(attrs)
        return event


class CMKEventConsoleStatus(object):
    def __init__(self, address):
        self._address = address

    # Copied from web/htdocs/mkeventd.py. Better move to some common lib.
    def query(self, query):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        timeout = 10

        sock.settimeout(timeout)
        sock.connect(self._address)
        sock.sendall(query)
        sock.shutdown(socket.SHUT_WR)

        response_text = ""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)

    def query_table_assoc(self, query):
        response = self.query(query)
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_value(self, query):
        return self.query(query)[0][0]


class WatchLog(object):
    """Small helper for integration tests: Watch a sites log file"""

    def __init__(self, site, rel_path, default_timeout=5):
        self._site = site
        self._rel_path = rel_path
        self._log = self._open_log()
        self._default_timeout = default_timeout
        self._buf = []

    def _log_path(self):
        return self._rel_path

    def _open_log(self):
        if not self._site.file_exists(self._log_path()):
            self._site.write_file(self._log_path(), "")

        fobj = open(self._site.path(self._log_path()), "r")
        fobj.seek(0, 2)  # go to end of file
        return fobj

    def check_logged(self, match_for, timeout=None):
        if timeout is None:
            timeout = self._default_timeout

        if not self._check_for_line(match_for, timeout):
            raise Exception(
                "Did not find %r in %s after %d seconds" % (match_for, self._log_path(), timeout))

    def check_not_logged(self, match_for, timeout=None):
        if timeout is None:
            timeout = self._default_timeout

        if self._check_for_line(match_for, timeout):
            raise Exception(
                "Found %r in %s after %d seconds" % (match_for, self._log_path(), timeout))

    def _check_for_line(self, match_for, timeout):
        timeout_at = time.time() + timeout
        sys.stdout.write(
            "Start checking for matching line at %d until %d\n" % (time.time(), timeout_at))
        while time.time() < timeout_at:
            #print "read till timeout %0.2f sec left" % (timeout_at - time.time())
            line = self._log.readline()
            if line:
                sys.stdout.write("PROCESS LINE: %r\n" % line)
            if match_for in line:
                return True
            time.sleep(0.1)

        sys.stdout.write("Timed out at %d\n" % (time.time()))
        return False


@pytest.fixture(scope="module")
def web(site):
    web = CMKWebSession(site)
    web.login()
    web.set_language("en")
    return web


@pytest.fixture(scope="module")
def ec(site, web):
    ec = CMKEventConsole(site)
    #ec.enable_remote_status_port(web)
    #ec.activate_changes(web)
    return ec


def create_linux_test_host(request, web, site, hostname):
    def finalizer():
        web.delete_host(hostname)
        web.activate_changes()
        site.delete_file("var/check_mk/agent_output/%s" % hostname)
        site.delete_file("etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname)

    request.addfinalizer(finalizer)

    web.add_host(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['%s']))\n" %
        hostname)

    site.makedirs("var/check_mk/agent_output/")
    site.write_file(
        "var/check_mk/agent_output/%s" % hostname,
        file("%s/tests/integration/cmk_base/test-files/linux-agent-output" % repo_path()).read())


#.
#   .--Checks--------------------------------------------------------------.
#   |                    ____ _               _                            |
#   |                   / ___| |__   ___  ___| | _____                     |
#   |                  | |   | '_ \ / _ \/ __| |/ / __|                    |
#   |                  | |___| | | |  __/ (__|   <\__ \                    |
#   |                   \____|_| |_|\___|\___|_|\_\___/                    |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Testing of Check_MK checks                                           |
#   '----------------------------------------------------------------------'


class CheckManager(object):
    def load(self, file_names=None):
        """Load either all check plugins or the given file_names"""
        import cmk_base.checks as checks
        import cmk.paths

        if file_names is None:
            checks.load()  # loads all checks
        else:
            checks._initialize_data_structures()
            checks.load_checks(map(lambda f: os.path.join(cmk.paths.checks_dir, f), file_names))

    def get_check(self, name):
        main_check = name.split(".", 1)[0]
        self.load([main_check])
        return Check(name)

    def get_active_check(self, name):
        self.load([name])
        return ActiveCheck(name)


class Check(object):
    def __init__(self, name):
        import cmk_base.checks as checks
        self.name = name
        self.info = checks.check_info[name]
        self.context = checks._check_contexts[name]

    def default_parameters(self):
        import cmk_base.checks as checks
        params = {}
        return checks._update_with_default_check_parameters(self.name, params)

    def run_parse(self, info):
        parse_func = self.info.get("parse_function")
        if not parse_func:
            raise Exception("This check has no parse function defined")

        return parse_func(info)

    def run_discovery(self, info):
        # TODO: use standard sanitizing code
        return self.info["inventory_function"](info)

    def run_check(self, item, params, info):
        # TODO: use standard sanitizing code
        return self.info["check_function"](item, params, info)

    #def run_parse_with_walk(self, walk_name):
    #    if "parse_function" not in self.info:
    #        raise Exception("This check has no parse function defined")

    #    return self.info["parse_function"]()

    #def run_discovery_with_walk(self, walk_name):
    #     # TODO: use standard walk processing code
    #    info = self._get_walk(walk_name)

    #    # TODO: use standard sanitizing code
    #    return self.info["inventory_function"](info)

    #def run_check_with_walk(self, walk_name, item, params):
    #     # TODO: use standard walk processing code
    #    info = self._get_walk(walk_name)

    #    # TODO: use standard sanitizing code
    #    return self.info["check_function"](item, params, info)


class ActiveCheck(object):
    def __init__(self, name):
        import cmk_base.checks as checks
        self.name = name
        assert name.startswith(
            'check_'), 'Specify the full name of the active check, e.g. check_http'
        self.info = checks.active_check_info[name[len('check_'):]]

    def run_argument_function(self, params):
        return self.info['argument_function'](params)

    def run_service_description(self, params):
        return self.info['service_description'](params)
