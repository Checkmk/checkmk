from __future__ import print_function

import glob
import sys
import os
import pwd
import subprocess
import pipes
import time
import shutil
import logging
import six
from six.moves.urllib.parse import urlparse

from testlib.utils import (
    InterProcessLock,
    SiteActionLock,
    cmk_path,
    cme_path,
    cmc_path,
    virtualenv_path,
)
from testlib.web_session import CMKWebSession
from testlib.version import CMKVersion

logger = logging.getLogger(__name__)


class Site(object):  # pylint: disable=useless-object-inheritance
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

    @property
    def apache_port(self):
        if self._apache_port is None:
            self._apache_port = int(self.get_config("APACHE_TCP_PORT"))
        return self._apache_port

    @property
    def internal_url(self):
        return "%s://%s:%s/%s/check_mk/" % (self.http_proto, self.http_address, self.apache_port,
                                            self.id)

    @property
    def livestatus_port(self):
        if self._livestatus_port is None:
            raise Exception("Livestatus TCP not opened yet")
        return self._livestatus_port

    @property
    def live(self):
        import livestatus  # pylint: disable=import-outside-toplevel
        # Note: If the site comes from a SiteFactory instance, the TCP connection
        # is insecure, i.e. no TLS.
        live = (livestatus.LocalConnection() if self._is_running_as_site_user() else
                livestatus.SingleSiteConnection("tcp:%s:%d" %
                                                (self.http_address, self.livestatus_port)))
        live.set_timeout(2)
        return live

    def url_for_path(self, path):
        """
        Computes a full URL inkl. http://... from a URL starting with the path.
        In case no path component is in URL, prepend "/[site]/check_mk" to the path.
        """
        assert not path.startswith("http")
        assert "://" not in path

        if "/" not in urlparse(path).path:
            path = "/%s/check_mk/%s" % (self.id, path)
        return '%s://%s:%d%s' % (self.http_proto, self.http_address, self.apache_port, path)

    def wait_for_core_reloaded(self, after):
        # Activating changes can involve an asynchronous(!) monitoring
        # core restart/reload, so e.g. querying a Livestatus table immediately
        # might not reflect the changes yet. Ask the core for a successful reload.
        def config_reloaded():
            import livestatus  # pylint: disable=import-outside-toplevel
            try:
                new_t = self.live.query_value("GET status\nColumns: program_start\n")
            except livestatus.MKLivestatusException:
                # Seems like the socket may vanish for a short time. Keep waiting in case
                # of livestatus (connection) issues...
                return False
            return new_t > after

        reload_time, timeout = time.time(), 10
        while not config_reloaded():
            if time.time() > reload_time + timeout:
                raise Exception("Config did not update within %d seconds" % timeout)
            time.sleep(0.2)

        assert config_reloaded()

    def restart_core(self):
        # Remember the time for the core reload check and wait a second because the program_start
        # is reported as integer and wait_for_core_reloaded() compares with ">".
        before_restart = time.time()
        time.sleep(1)
        self.omd("restart", "core")
        self.wait_for_core_reloaded(before_restart)

    def send_host_check_result(self, hostname, state, output, expected_state=None):
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_host_check(hostname)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command("[%d] PROCESS_HOST_CHECK_RESULT;%s;%d;%s" %
                          (command_timestamp, hostname, state, output))
        self._wait_for_next_host_check(hostname, last_check_before, command_timestamp,
                                       expected_state)

    def send_service_check_result(self,
                                  hostname,
                                  service_description,
                                  state,
                                  output,
                                  expected_state=None):
        if expected_state is None:
            expected_state = state
        last_check_before = self._last_service_check(hostname, service_description)
        command_timestamp = self._command_timestamp(last_check_before)
        self.live.command("[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s" %
                          (command_timestamp, hostname, service_description, state, output))
        self._wait_for_next_service_check(hostname, service_description, last_check_before,
                                          command_timestamp, expected_state)

    def schedule_check(self, hostname, service_description, expected_state):
        logger.debug("%s;%s schedule check", hostname, service_description)
        last_check_before = self._last_service_check(hostname, service_description)
        logger.debug("%s;%s last check before %r", hostname, service_description, last_check_before)

        command_timestamp = self._command_timestamp(last_check_before)

        command = "[%d] SCHEDULE_FORCED_SVC_CHECK;%s;%s;%d" % \
            (command_timestamp, hostname, service_description.encode("utf-8"), command_timestamp)

        logger.debug("%s;%s: %r", hostname, service_description, command)
        self.live.command(command)

        self._wait_for_next_service_check(hostname, service_description, last_check_before,
                                          command_timestamp, expected_state)

    def _command_timestamp(self, last_check_before):
        # Ensure the next check result is not in same second as the previous check
        timestamp = time.time()
        while int(last_check_before) == int(timestamp):
            timestamp = time.time()
            time.sleep(0.1)
        return timestamp

    def _wait_for_next_host_check(self, hostname, last_check_before, command_timestamp,
                                  expected_state):
        wait_timeout = 20
        last_check, state, plugin_output = self.live.query_row(
            "GET hosts\n" \
            "Columns: last_check state plugin_output\n" \
            "Filter: host_name = %s\n" \
            "WaitObject: %s\n" \
            "WaitTimeout: %d\n" \
            "WaitCondition: last_check > %d\n" \
            "WaitCondition: state = %d\n" \
            "WaitTrigger: check\n" % (hostname, hostname, wait_timeout*1000, last_check_before, expected_state))
        self._verify_next_check_output(command_timestamp, last_check, last_check_before, state,
                                       expected_state, plugin_output, wait_timeout)

    def _wait_for_next_service_check(self, hostname, service_description, last_check_before,
                                     command_timestamp, expected_state):
        wait_timeout = 20
        last_check, state, plugin_output = self.live.query_row(
            "GET services\n" \
            "Columns: last_check state plugin_output\n" \
            "Filter: host_name = %s\n" \
            "Filter: description = %s\n" \
            "WaitObject: %s;%s\n" \
            "WaitTimeout: %d\n" \
            "WaitCondition: last_check > %d\n" \
            "WaitCondition: state = %d\n" \
            "WaitCondition: has_been_checked = 1\n" \
            "WaitTrigger: check\n" % (hostname, service_description, hostname, service_description, wait_timeout*1000, last_check_before, expected_state))
        self._verify_next_check_output(command_timestamp, last_check, last_check_before, state,
                                       expected_state, plugin_output, wait_timeout)

    def _verify_next_check_output(self, command_timestamp, last_check, last_check_before, state,
                                  expected_state, plugin_output, wait_timeout):
        print("processing check result took %0.2f seconds" % (time.time() - command_timestamp))
        assert last_check > last_check_before, \
                "Check result not processed within %d seconds (last check before reschedule: %d, " \
                "scheduled at: %d, last check: %d)" % \
                (wait_timeout, last_check_before, command_timestamp, last_check)
        assert state == expected_state, \
            "Expected %d state, got %d state, output %s" % (expected_state, state, plugin_output)

    def _last_host_check(self, hostname):
        return self.live.query_value(
            "GET hosts\n" \
            "Columns: last_check\n" \
            "Filter: host_name = %s\n" % (hostname))

    def _last_service_check(self, hostname, service_description):
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
        assert isinstance(cmd, list), "The command must be given as list"

        if not self._is_running_as_site_user():
            sys.stdout.write("Executing (sudo): %s\n" % subprocess.list2cmdline(cmd))
            cmd = [
                "sudo", "su", "-l", self.id, "-c",
                pipes.quote(" ".join([pipes.quote(p) for p in cmd]))
            ]
            cmd_txt = " ".join(cmd)
            return subprocess.Popen(cmd_txt, shell=True, *args, **kwargs)  # nosec

        sys.stdout.write("Executing (site): %s\n" % subprocess.list2cmdline(cmd))
        return subprocess.Popen(  # nosec
            subprocess.list2cmdline(cmd), shell=True, *args, **kwargs)

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
                raise Exception("Failed to delete directory %s. Exit-Code: %d" %
                                (rel_path, p.wait()))
        else:
            shutil.rmtree(self.path(rel_path))

    def write_file(self, rel_path, content):
        if isinstance(content, six.text_type):
            content = content.encode("utf-8")
        if not self._is_running_as_site_user():
            p = self.execute(["tee", self.path(rel_path)],
                             stdin=subprocess.PIPE,
                             stdout=open(os.devnull, "w"))
            p.communicate(content)
            p.stdin.close()
            if p.wait() != 0:
                raise Exception("Failed to write file %s. Exit-Code: %d" % (rel_path, p.wait()))
        else:
            return open(self.path(rel_path), "wb").write(content)

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
        with SiteActionLock():
            if not self.version.is_installed():
                self.version.install()

            if self.update_with_git:
                self._copy_omd_version_for_test()

            if not self.reuse and self.exists():
                raise Exception("The site %s already exists." % self.id)

            if not self.exists():
                print("[%0.2f] Creating site '%s'" % (time.time(), self.id))
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
                #self._enabled_liveproxyd_debug_logging()
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
        self.version = CMKVersion(new_version_name, self.version.edition(), self.version._branch)

        print("Copy CMK '%s' to '%s'" % (src_path, self.version.version_path()))
        assert not os.path.exists(self.version.version_path()), \
            "New version path '%s' already exists" % self.version.version_path()

        def execute(cmd):
            print("Executing: %s" % cmd)
            rc = os.system(cmd) >> 8  # nosec
            if rc != 0:
                raise Exception("Failed to execute '%s'. Exit code: %d" % (cmd, rc))

        execute("sudo /bin/cp -a %s %s" % (src_path, self.version.version_path()))

        execute("sudo sed -i \"s|%s|%s|g\" %s/bin/omd" %
                (src_version, new_version_name, self.version.version_path()))

        omd_init_path = "%s/lib/python3/omdlib/__init__.py" % self.version.version_path()
        # Temporary hack. Can be removed after 2019-12-19
        if not os.path.exists(omd_init_path):
            omd_init_path = "%s/lib/python/omdlib/__init__.py" % self.version.version_path()
        execute("sudo sed -i \"s|%s|%s|g\" %s" % (src_version, new_version_name, omd_init_path))

        execute("sudo sed -i \"s|%s|%s|g\" %s/share/omd/omd.info" %
                (src_version, new_version_name, self.version.version_path()))

        # we should use self.version.version_path() in the RPATH, but that is limited to
        # 32 bytes and our versions exceed this limit. We need to use some hack to make
        # this possible
        if not os.path.exists("/omd/v"):
            execute("sudo /bin/ln -s /omd/versions /omd/v")

        execute("sudo chrpath -r /omd/v/%s/lib %s/bin/python" %
                (self.version.version_directory(), self.version.version_path()))

        execute("sudo chrpath -r /omd/v/%s/lib %s/bin/python3" %
                (self.version.version_directory(), self.version.version_path()))

    def _update_with_f12_files(self):
        paths = [
            cmk_path() + "/omd/packages/omd",
            cmk_path() + "/livestatus",
            cmk_path() + "/bin",
            cmk_path() + "/agents/special",
            cmk_path() + "/agents/plugins",
            cmk_path() + "/modules",
            cmk_path() + "/cmk/base",
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
                cmc_path() + "/cmk/base",
                cmc_path() + "/cmk",
                cmc_path() + "/web",
                cmc_path() + "/alert_handlers",
                cmc_path() + "/misc",
                # TODO: To be able to build the core correctly we need to build
                # python/boost/python-modules/rrdtool first. Skip cmc for the moment here
                #cmc_path() + "/core",
                cmc_path() + "/agents",
            ]

        if os.path.exists(cme_path()) and self.version.is_managed_edition():
            paths += [
                cme_path(),
                cme_path() + "/cmk/base",
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

    def _install_test_python_modules(self):
        venv = virtualenv_path()
        bin_dir = venv / "bin"
        packages_dir = venv / "lib/python2.7/site-packages"

        enforce_override = ["backports"]

        for file_name in os.listdir(str(packages_dir)):
            # Only copy modules that do not exist in regular module path
            if file_name not in enforce_override:
                if os.path.exists("%s/lib/python/%s" % (self.root, file_name)) \
                   or os.path.exists("%s/lib/python2.7/site-packages/%s" % (self.root, file_name)):
                    continue

            assert os.system("sudo rsync -a --chown %s:%s %s %s/local/lib/python/" %  # nosec
                             (self.id, self.id, packages_dir / file_name, self.root)) >> 8 == 0

        for file_name in ["py.test", "pytest"]:
            assert os.system("sudo rsync -a --chown %s:%s %s %s/local/bin" %  # nosec
                             (self.id, self.id, bin_dir / file_name, self.root)) >> 8 == 0

    def rm(self, site_id=None):
        if site_id is None:
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
                print("Cleaning up old site: %s" % site_id)
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

        assert os.path.ismount(self.path("tmp")), \
            "The site does not have a tmpfs mounted! We require this for good performing tests"

    def stop(self):
        if not self.is_running():
            return  # Nothing to do

        print("= BEGIN PROCESSES BEFORE =======================================")
        os.system("ps -fwwu %s" % self.id)  # nosec
        print("= END PROCESSES BEFORE =======================================")

        stop_exit_code = self.omd("stop")
        if stop_exit_code != 0:
            print("omd stop exit code: %d" % stop_exit_code)

        print("= BEGIN PROCESSES AFTER STOP =======================================")
        os.system("ps -fwwu %s" % self.id)  # nosec
        print("= END PROCESSES AFTER STOP =======================================")

        try:
            i = 0
            while self.is_running():
                i += 1
                if i > 10:
                    raise Exception("Could not stop site %s" % self.id)
                print("The site %s is still running, sleeping... (round %d)" % (self.id, i))
                sys.stdout.flush()
                time.sleep(0.2)
        except:
            print("= BEGIN PROCESSES AFTER WAIT =======================================")
            os.system("ps -fwwu %s" % self.id)  # nosec
            print("= END PROCESSES AFTER WAIT =======================================")
            raise

    def exists(self):
        return os.path.exists("/omd/sites/%s" % self.id)

    def is_running(self):
        return self.execute(["/usr/bin/omd", "status", "--bare"], stdout=open(os.devnull,
                                                                              "w")).wait() == 0

    def set_config(self, key, val, with_restart=False):
        if self.get_config(key) == val:
            print("omd config: %s is already at %r" % (key, val))
            return

        if with_restart:
            print("Stopping site")
            self.stop()

        print("omd config: Set %s to %r" % (key, val))
        assert self.omd("config", "set", key, val) == 0

        if with_restart:
            self.start()
            print("Started site")

    def set_core(self, core):
        self.set_config("CORE", core, with_restart=True)

    def get_config(self, key):
        p = self.execute(["omd", "config", "show", key],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print(stderr)
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
            print("WATO is already initialized -> Skipping initializiation")
            return

        web = CMKWebSession(self)
        web.login()
        web.set_language("en")

        # Call WATO once for creating the default WATO configuration
        response = web.get("wato.py").text
        assert "<title>WATO" in response
        assert "<div class=\"title\">Manual Checks</div>" in response, \
                "WATO does not seem to be initialized: %r" % response

        wait_time = 20
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
                            'condition': {},
                            'options': {},
                            'value': [('TESTGROUP', ('*gwia*', ''))]
                        },
                    ],
                }
            })

    def _missing_but_required_wato_files(self):
        required_files = [
            "etc/check_mk/conf.d/wato/rules.mk", "etc/check_mk/multisite.d/wato/tags.mk",
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
            "BRANCH": self.version._branch,
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
        print(cmd)
        args = ["/usr/bin/sudo", "--", "/bin/su", "-l", self.id, "-c", cmd]
        return subprocess.call(args)

    # This opens a currently free TCP port and remembers it in the object for later use
    # Not free of races, but should be sufficient.
    def open_livestatus_tcp(self):
        start_again = False

        if self.is_running():
            start_again = True
            self.stop()

        sys.stdout.write("Getting livestatus port lock (/tmp/cmk-test-open-livestatus-port)...\n")
        with InterProcessLock("/tmp/cmk-test-livestatus-port"):
            sys.stdout.write("Have livestatus port lock\n")
            self.set_config("LIVESTATUS_TCP", "on")
            self._gather_livestatus_port()
            self.set_config("LIVESTATUS_TCP_PORT", str(self._livestatus_port))

            if start_again:
                self.start()

        sys.stdout.write("After livestatus port lock\n")

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

        print("Livestatus ports already in use: %r, using port: %d" % (used_ports, port))
        return port


class SiteFactory(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, version, edition, branch, prefix=None):
        self._base_ident = prefix or "s_%s_" % branch[:6]
        self._version = version
        self._edition = edition
        self._branch = branch
        self._sites = {}
        self._index = 1

    @property
    def sites(self):
        return self._sites

    def get_site(self, name):
        if "%s%s" % (self._base_ident, name) in self._sites:
            return self._sites["%s%s" % (self._base_ident, name)]
        # For convenience, allow to retreive site by name or full ident
        if name in self._sites:
            return self._sites[name]
        return self._new_site(name)

    def remove_site(self, name):
        if "%s%s" % (self._base_ident, name) in self._sites:
            site_id = "%s%s" % (self._base_ident, name)
        elif name in self._sites:
            site_id = name
        else:
            print("Found no site for name %s." % name)
            return
        print("Removing site %s" % site_id)
        self._sites[site_id].rm()
        del self._sites[site_id]

    def _get_ident(self):
        new_ident = self._base_ident + str(self._index)
        self._index += 1
        return new_ident

    def _new_site(self, name):
        site_id = "%s%s" % (self._base_ident, name)
        site = Site(site_id=site_id,
                    reuse=False,
                    version=self._version,
                    edition=self._edition,
                    branch=self._branch)
        site.create()
        site.open_livestatus_tcp()
        # No TLS for testing
        site.set_config("LIVESTATUS_TCP_TLS", "off")
        site.start()
        site.prepare_for_tests()
        # There seem to be still some changes that want to be activated
        CMKWebSession(site).activate_changes()
        print("Created site %s" % site_id)
        self._sites[site_id] = site
        return site

    def cleanup(self):
        for site_id in list(self._sites.keys()):
            self.remove_site(site_id)
