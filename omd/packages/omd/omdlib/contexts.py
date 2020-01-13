#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import os
import sys
from typing import cast, Optional  # pylint: disable=unused-import
import six

from cmk.utils.exceptions import MKTerminate

import omdlib
from omdlib.init_scripts import check_status
from omdlib.config_hooks import call_hook, sort_hooks
from omdlib.utils import is_dockerized
from omdlib.type_defs import Config, Replacements  # pylint: disable=unused-import
from omdlib.skel_permissions import (  # pylint: disable=unused-import
    load_skel_permissions, load_skel_permissions_from, Permissions)


class AbstractSiteContext(six.with_metaclass(abc.ABCMeta, object)):
    """Object wrapping site specific information"""
    def __init__(self, sitename):
        # type: (Optional[str]) -> None
        super(AbstractSiteContext, self).__init__()
        self._sitename = sitename
        self._config_loaded = False
        self._config = {}  # type: Config

    @property
    def name(self):
        # type: () -> Optional[str]
        return self._sitename

    @abc.abstractproperty
    def version(self):
        # type: () -> Optional[str]
        raise NotImplementedError()

    @abc.abstractproperty
    def dir(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractproperty
    def tmp_dir(self):
        # type: () -> str
        raise NotImplementedError()

    @property
    def version_meta_dir(self):
        # type: () -> str
        return "%s/.version_meta" % self.dir

    @property
    def conf(self):
        # type: () -> Config
        """{ "CORE" : "nagios", ... } (contents of etc/omd/site.conf plus defaults from hooks)"""
        if not self._config_loaded:
            raise Exception("Config not loaded yet")
        return self._config

    @abc.abstractmethod
    def load_config(self):
        # type: () -> None
        raise NotImplementedError()

    @abc.abstractmethod
    def exists(self):
        # type: () -> bool
        raise NotImplementedError()

    @abc.abstractmethod
    def is_empty(self):
        # type: () -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def is_site_context():
        # type: () -> bool
        raise NotImplementedError()


class SiteContext(AbstractSiteContext):
    @property
    def name(self):
        # type: () -> str
        return cast(str, self._sitename)

    @property
    def dir(self):
        # type: () -> str
        return "/omd/sites/" + cast(str, self._sitename)

    @property
    def tmp_dir(self):
        # type: () -> str
        return "%s/tmp" % self.dir

    @property
    def version(self):
        # type: () -> Optional[str]
        """The version of a site is solely determined by the link ~SITE/version
        In case the version of a site can not be determined, it reports None."""
        version_link = self.dir + "/version"
        try:
            return os.readlink(version_link).split("/")[-1]
        except Exception:
            return None

    @property
    def replacements(self):
        # type: () -> Replacements
        """Dictionary of key/value for replacing macros in skel files"""
        return {
            "###SITE###": self.name,
            "###ROOT###": self.dir,
        }

    def load_config(self):
        # type: () -> None
        """Load all variables from omd/sites.conf. These variables always begin with
        CONFIG_. The reason is that this file can be sources with the shell.

        Puts these variables into the config dict without the CONFIG_. Also
        puts the variables into the process environment."""
        self._config = self.read_site_config()

        # Get the default values of all config hooks that are not contained
        # in the site configuration. This can happen if there are new hooks
        # after an update or when a site is being created.
        hook_dir = self.dir + "/lib/omd/hooks"
        if os.path.exists(hook_dir):
            for hook_name in sort_hooks(os.listdir(hook_dir)):
                if hook_name[0] != '.' and hook_name not in self._config:
                    content = call_hook(self, hook_name, ["default"])[1]
                    self._config[hook_name] = content

        self._config_loaded = True

    def read_site_config(self):
        # type: () -> Config
        """Read and parse the file site.conf of a site into a dictionary and returns it"""
        config = {}  # type: Config
        confpath = "%s/etc/omd/site.conf" % (self.dir)
        if not os.path.exists(confpath):
            return {}

        for line in open(confpath):
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            var, value = line.split("=", 1)
            if not var.startswith("CONFIG_"):
                sys.stderr.write("Ignoring invalid variable %s.\n" % var)
            else:
                config[var[7:].strip()] = value.strip().strip("'")

        return config

    def exists(self):
        # type: () -> bool
        # In dockerized environments the tmpfs may be managed by docker (when
        # using the --tmpfs option).  In this case the site directory is
        # created as parent of the tmp directory to mount the tmpfs during
        # container initialization. Detect this situation and don't treat the
        # site as existing in that case.
        if is_dockerized():
            if not os.path.exists(self.dir):
                return False
            if os.listdir(self.dir) == ["tmp"]:
                return False
            return True

        return os.path.exists(self.dir)

    def is_empty(self):
        # type: () -> bool
        for entry in os.listdir(self.dir):
            if entry not in ['.', '..']:
                return False
        return True

    def is_autostart(self):
        # type: () -> bool
        """Determines whether a specific site is set to autostart."""
        return self.conf.get('AUTOSTART', 'on') == 'on'

    def is_disabled(self):
        # type: () -> bool
        """Whether or not this site has been disabled with 'omd disable'"""
        apache_conf = "/omd/apache/%s.conf" % self.name
        return not os.path.exists(apache_conf)

    def is_stopped(self):
        # type: () -> bool
        """Check if site is completely stopped"""
        return check_status(self, display=False) == 1

    @staticmethod
    def is_site_context():
        # type: () -> bool
        return True

    @property
    def skel_permissions(self):
        # type: () -> Permissions
        """Returns the skeleton permissions. Load either from version meta directory
        or from the original version skel.permissions file"""
        if not self._has_version_meta_data():
            if self.version is None:
                raise MKTerminate("Failed to determine site version")
            return load_skel_permissions(self.version)

        return load_skel_permissions_from(self.version_meta_dir + "/skel.permissions")

    @property
    def version_skel_dir(self):
        # type: () -> str
        """Returns the current version skel directory. In case the meta data is
        available and fits the sites version use that one instead of the version
        skel directory."""
        if not self._has_version_meta_data():
            return "/omd/versions/%s/skel" % self.version
        return self.version_meta_dir + "/skel"

    def _has_version_meta_data(self):
        # type: () -> bool
        if not os.path.exists(self.version_meta_dir):
            return False

        if self._version_meta_data_version() != self.version:
            return False

        return True

    def _version_meta_data_version(self):
        # type: () -> str
        with open(self.version_meta_dir + "/version") as f:
            return f.read().strip()


class RootContext(AbstractSiteContext):
    def __init__(self):
        # type: () -> None
        super(RootContext, self).__init__(sitename=None)

    @property
    def dir(self):
        # type: () -> str
        return "/"

    @property
    def tmp_dir(self):
        # type: () -> str
        return "/tmp"

    @property
    def version(self):
        # type: () -> str
        return omdlib.__version__

    def load_config(self):
        # type: () -> None
        pass

    def exists(self):
        # type: () -> bool
        return False

    def is_empty(self):
        # type: () -> bool
        return False

    @staticmethod
    def is_site_context():
        # type: () -> bool
        return False
