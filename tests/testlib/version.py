from __future__ import print_function

import os
import time
import sys
import platform
import logging

import requests

from testlib.utils import InterProcessLock, get_cmk_download_credentials

logger = logging.getLogger()


# It's ok to make it currently only work on debian based distros
class CMKVersion(object):  # pylint: disable=useless-object-inheritance
    DEFAULT = "default"
    DAILY = "daily"
    GIT = "git"

    CEE = "cee"
    CRE = "cre"
    CME = "cme"

    def __init__(self, version, edition, branch):
        self._version = version
        self._branch = branch

        self._set_edition(edition)
        self.set_version(version, branch)

    def _set_edition(self, edition):
        # Allow short (cre) and long (raw) notation as input
        if edition not in [CMKVersion.CRE, CMKVersion.CEE, CMKVersion.CME]:
            edition_short = self._get_short_edition(edition)
        else:
            edition_short = edition

        if edition_short not in [CMKVersion.CRE, CMKVersion.CEE, CMKVersion.CME]:
            raise NotImplementedError("Unknown short edition: %s" % edition_short)

        self.edition_short = edition_short

    def _get_short_edition(self, edition):
        if edition == "raw":
            return "cre"
        if edition == "enterprise":
            return "cee"
        if edition == "managed":
            return "cme"
        raise NotImplementedError("Unknown edition: %s" % edition)

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
        if self.edition_short == CMKVersion.CEE:
            return "enterprise"
        if self.edition_short == CMKVersion.CME:
            return "managed"
        raise NotImplementedError()

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
        return "amd64" if platform.architecture()[0] == "64bit" else "i386"

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

        response = requests.head(  # nosec
            self.package_url(), auth=get_cmk_download_credentials(), verify=False)
        return response.status_code == 200

    def install(self):
        if os.path.exists(self._build_system_package_path()):
            logger.info("Install from build system package (%s)", self._build_system_package_path())
            package_path = self._build_system_package_path()
            self._install_package(package_path)

        else:
            logger.info("Install from download portal")
            package_path = self._download_package()
            self._install_package(package_path)
            os.unlink(package_path)

    def _download_package(self):
        temp_package_path = "/tmp/%s" % self.package_name()

        logger.info(self.package_url())
        response = requests.get(  # nosec
            self.package_url(), auth=get_cmk_download_credentials(), verify=False)
        if response.status_code != 200:
            raise Exception("Failed to load package: %s" % self.package_url())
        open(temp_package_path, "wb").write(response.content)
        return temp_package_path

    def _install_package(self, package_path):
        # The following gdebi call will fail in case there is another package
        # manager task being active. Try to wait for other task to finish. Sure
        # this is not race free, but hope it's sufficient.
        while os.system("sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1") >> 8 == 0:
            logger.info("Waiting for other dpkg process to complete...")
            time.sleep(1)

        # Improve the protection against other test runs installing packages
        with InterProcessLock("/tmp/cmk-test-install-version"):
            cmd = "sudo /usr/bin/gdebi --non-interactive %s" % package_path
            logger.info(cmd)
            sys.stdout.flush()
            if os.system(cmd) >> 8 != 0:  # nosec
                raise Exception("Failed to install package: %s" % package_path)

        assert self.is_installed()
