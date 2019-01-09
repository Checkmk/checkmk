#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import signal

import cmk

import cmk.gui.config as config
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.watolib.utils import (
    wato_root_dir,
    liveproxyd_config_dir,
    multisite_dir,
)
from cmk.gui.watolib.automations import check_mk_local_automation
from cmk.gui.plugins.watolib import (
    config_domain_registry,
    ConfigDomain,
)


@config_domain_registry.register
class ConfigDomainCore(ConfigDomain):
    needs_sync = True
    needs_activation = True
    ident = "check_mk"

    def config_dir(self):
        return wato_root_dir

    def activate(self):
        return check_mk_local_automation(config.wato_activation_method)

    def default_globals(self):
        return check_mk_local_automation("get-configuration", [],
                                         self._get_global_config_var_names())


@config_domain_registry.register
class ConfigDomainGUI(ConfigDomain):
    needs_sync = True
    needs_activation = False
    ident = "multisite"

    def config_dir(self):
        return multisite_dir

    def activate(self):
        pass

    def default_globals(self):
        return config.default_config


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plugin hierarchy and
# move this to a CEE/CME specific watolib plugin
@config_domain_registry.register
class ConfigDomainLiveproxy(ConfigDomain):
    needs_sync = False
    needs_activation = False
    ident = "liveproxyd"
    in_global_settings = True

    @classmethod
    def enabled(cls):
        return not cmk.is_raw_edition() and config.liveproxyd_enabled

    def config_dir(self):
        return liveproxyd_config_dir

    def save(self, settings, site_specific=False):
        super(ConfigDomainLiveproxy, self).save(settings, site_specific=site_specific)
        self.activate()

    def activate(self):
        #log_audit(None, "liveproxyd-activate",
        #          _("Activating changes of Livestatus Proxy configuration"))

        try:
            pidfile = cmk.utils.paths.livestatus_unix_socket + "proxyd.pid"
            try:
                pid = int(file(pidfile).read().strip())
                os.kill(pid, signal.SIGUSR1)
            except IOError as e:
                if e.errno == 2:  # No such file or directory
                    pass
                else:
                    raise
        except Exception as e:
            logger.exception()
            html.show_warning(
                _("Could not reload Livestatus Proxy: %s. See web.log "
                  "for further information.") % e)

    # TODO: Move default values to common module to share
    # the defaults between the GUI code an liveproxyd.
    def default_globals(self):
        return {
            "liveproxyd_log_levels": {
                "cmk.liveproxyd": cmk.utils.log.INFO,
            },
            "liveproxyd_default_connection_params":
                ConfigDomainLiveproxy.connection_params_defaults(),
        }

    @staticmethod
    def connection_params_defaults():
        return {
            "channels": 5,
            "heartbeat": (5, 2.0),
            "channel_timeout": 3.0,
            "query_timeout": 120.0,
            "connect_retry": 4.0,
            "cache": True,
        }
