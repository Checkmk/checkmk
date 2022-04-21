#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import os
import signal
import subprocess
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.process import pid_from_file, send_signal
from cmk.utils.site import omd_site
from cmk.utils.type_defs import ConfigurationWarnings, HostName

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.hooks as hooks
import cmk.gui.mkeventd as mkeventd
from cmk.gui.config import active_config, get_default_config
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_domain_registry,
    DomainRequest,
    SerializedSettings,
)
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import ConfigDomainName
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.utils import liveproxyd_config_dir, multisite_dir, wato_root_dir
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob


@dataclass
class ConfigDomainCoreSettings:
    hosts_to_update: List[HostName] = field(default_factory=list)

    def validate(self) -> None:
        for hostname in self.hosts_to_update:
            if not isinstance(hostname, HostName):
                raise MKGeneralException(f"Invalid hostname type in ConfigDomain: {self}")

    def __post_init__(self) -> None:
        self.validate()


@config_domain_registry.register
class ConfigDomainCore(ABCConfigDomain):
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "check_mk"

    def config_dir(self):
        return wato_root_dir()

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        # TODO: Cleanup
        from cmk.gui.watolib.check_mk_automations import reload, restart

        return {"restart": restart, "reload": reload,}[
            active_config.wato_activation_method
        ](self._parse_settings(settings).hosts_to_update).config_warnings

    def _parse_settings(
        self, activate_settings: Optional[SerializedSettings]
    ) -> ConfigDomainCoreSettings:
        if activate_settings is None:
            activate_settings = {}

        return ConfigDomainCoreSettings(**activate_settings)

    def default_globals(self):
        # TODO: Cleanup
        from cmk.gui.watolib.check_mk_automations import get_configuration

        return get_configuration(*self._get_global_config_var_names()).result

    @classmethod
    def generate_hosts_to_update_settings(cls, hostnames: Iterable[HostName]) -> SerializedSettings:
        return {"hosts_to_update": hostnames}

    @classmethod
    def generate_domain_settings(cls, hostnames: Iterable[HostName]) -> SerializedSettings:
        return {cls.ident(): cls.generate_hosts_to_update_settings(hostnames)}

    @classmethod
    def get_domain_request(cls, settings: List[SerializedSettings]) -> DomainRequest:
        # The incremental activate only works, if all changes use the hosts_to_update option
        hosts_to_update: Set[HostName] = set()
        for setting in settings:
            if len(setting.get("hosts_to_update", [])) == 0:
                return DomainRequest(cls.ident(), cls.generate_hosts_to_update_settings([]))
            hosts_to_update.update(setting["hosts_to_update"])

        return DomainRequest(cls.ident(), cls.generate_hosts_to_update_settings(hosts_to_update))


@config_domain_registry.register
class ConfigDomainGUI(ABCConfigDomain):
    needs_sync = True
    needs_activation = False

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "multisite"

    def config_dir(self):
        return multisite_dir()

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        return []

    def default_globals(self):
        return get_default_config()


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plugin hierarchy and
# move this to a CEE/CME specific watolib plugin
@config_domain_registry.register
class ConfigDomainLiveproxy(ABCConfigDomain):
    needs_sync = False
    needs_activation = False
    in_global_settings = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "liveproxyd"

    @classmethod
    def enabled(cls):
        return not cmk_version.is_raw_edition() and active_config.liveproxyd_enabled

    def config_dir(self):
        return liveproxyd_config_dir()

    def save(self, settings, site_specific=False, custom_site_path=None):
        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)
        self.activate()

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        log_audit("liveproxyd-activate", _("Activating changes of Livestatus Proxy configuration"))

        try:
            pidfile = Path(cmk.utils.paths.livestatus_unix_socket).with_name("liveproxyd.pid")
            try:
                with pidfile.open(encoding="utf-8") as f:
                    pid = int(f.read().strip())

                os.kill(pid, signal.SIGHUP)
            except OSError as e:
                # ENOENT: No liveproxyd running: No reload needed.
                # ESRCH: PID in pidfiles does not exist: No reload needed.
                if e.errno not in (errno.ENOENT, errno.ESRCH):
                    raise
            except ValueError:
                # ignore empty pid file (may happen during locking in
                # cmk.utils.daemon.lock_with_pid_file().  We are in the
                # situation where the livstatus proxy is in early phase of the
                # startup. The configuration is loaded later -> no reload needed
                pass

        except Exception as e:
            logger.exception("error reloading liveproxyd")
            raise MKGeneralException(
                _(
                    "Could not reload Livestatus Proxy: %s. See web.log and liveproxyd.log "
                    "for further information."
                )
                % e
            )
        return []

    # TODO: Move default values to common module to share
    # the defaults between the GUI code an liveproxyd.
    def default_globals(self):
        return {
            "liveproxyd_log_levels": {
                "cmk.liveproxyd": logging.INFO,
            },
            "liveproxyd_default_connection_params": ConfigDomainLiveproxy.connection_params_defaults(),
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


@config_domain_registry.register
class ConfigDomainEventConsole(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    in_global_settings = False

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "ec"

    @classmethod
    def enabled(cls):
        return active_config.mkeventd_enabled

    def config_dir(self):
        return str(ec.rule_pack_dir())

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        if getattr(active_config, "mkeventd_enabled", False):
            mkeventd.execute_command("RELOAD", site=omd_site())
            log_audit("mkeventd-activate", _("Activated changes of event console configuration"))
            if hooks.registered("mkeventd-activate-changes"):
                hooks.call("mkeventd-activate-changes")
        return []

    def default_globals(self):
        return ec.default_config()


@config_domain_registry.register
class ConfigDomainCACertificates(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    always_activate = True  # Execute this on all sites on all activations

    trusted_cas_file = cmk.utils.paths.trusted_ca_file

    # This is a list of directories that may contain .pem files of trusted CAs.
    # The contents of all .pem files will be contantenated together and written
    # to "trusted_cas_file". This is done by the function update_trusted_cas().
    # On a system only a single directory, the first existing one is processed.
    system_wide_trusted_ca_search_paths = [
        "/etc/ssl/certs",  # Ubuntu/Debian/SLES
        "/etc/pki/tls/certs",  # CentOS/RedHat
    ]

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "ca-certificates"

    def config_dir(self):
        return multisite_dir()

    def config_file(self, site_specific=False):
        if site_specific:
            return os.path.join(self.config_dir(), "ca-certificates_sitespecific.mk")
        return os.path.join(self.config_dir(), "ca-certificates.mk")

    def save(self, settings, site_specific=False, custom_site_path=None):
        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)

        current_config = settings.get(
            "trusted_certificate_authorities",
            {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            },
        )

        # We need to activate this immediately to make syncs to WATO slave sites
        # possible right after changing the option
        #
        # Since this can be called from any WATO page it is not possible to report
        # errors to the user here. The self._update_trusted_cas() method logs the
        # errors - this must be enough for the moment.
        if not site_specific and custom_site_path is None:
            self._update_trusted_cas(current_config)

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        try:
            warnings = self._update_trusted_cas(active_config.trusted_certificate_authorities)
            stunnel_pid = pid_from_file(
                cmk.utils.paths.omd_root / "tmp" / "run" / "stunnel-server.pid"
            )
            if stunnel_pid:
                send_signal(stunnel_pid, signal.SIGHUP)
            return warnings
        except Exception:
            logger.exception("error updating trusted CAs")
            return [
                "Failed to create trusted CA file '%s': %s"
                % (self.trusted_cas_file, traceback.format_exc())
            ]

    def _update_trusted_cas(self, current_config) -> ConfigurationWarnings:
        trusted_cas: List[str] = []
        errors: ConfigurationWarnings = []

        if current_config["use_system_wide_cas"]:
            trusted, errors = self._get_system_wide_trusted_ca_certificates()
            trusted_cas += trusted

        trusted_cas += current_config["trusted_cas"]

        store.save_text_to_file(
            self.trusted_cas_file,
            # we sort to have a deterministic output, s.t. for example liveproxyd can reliably check
            # if the file changed
            "\n".join(sorted(trusted_cas)),
        )
        return errors

    def _get_system_wide_trusted_ca_certificates(self) -> Tuple[List[str], List[str]]:
        trusted_cas: Set[str] = set()
        errors: List[str] = []
        for p in self.system_wide_trusted_ca_search_paths:
            cert_path = Path(p)

            if not cert_path.is_dir():
                continue

            for entry in cert_path.iterdir():
                cert_file_path = entry.absolute()
                try:
                    if entry.suffix not in [".pem", ".crt"]:
                        continue

                    trusted_cas.update(raw_certificates_from_file(cert_file_path))
                except (IOError, PermissionError):
                    # This error is shown to the user as warning message during "activate changes".
                    # We keep this message for the moment because we think that it is a helpful
                    # trigger for further checking web.log when a really needed certificate can
                    # not be read.
                    #
                    # We know a permission problem with some files that are created by default on
                    # some distros. We simply ignore these files because we assume that they are
                    # not needed.
                    if cert_file_path == Path("/etc/ssl/certs/localhost.crt"):
                        continue

                    logger.exception("Error reading certificates from %s", cert_file_path)

                    errors.append(
                        "Failed to add certificate '%s' to trusted CA certificates. "
                        "See web.log for details." % cert_file_path
                    )

            break

        return list(trusted_cas), errors

    def default_globals(self):
        return {
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            }
        }


@config_domain_registry.register
class ConfigDomainOMD(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    omd_config_dir = "%s/etc/omd" % (cmk.utils.paths.omd_root,)

    def __init__(self):
        super().__init__()
        self._logger: logging.Logger = logger.getChild("config.omd")

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "omd"

    def config_dir(self):
        return self.omd_config_dir

    def default_globals(self):
        return self._from_omd_config(self._load_site_config())

    def activate(self, settings: Optional[SerializedSettings] = None) -> ConfigurationWarnings:
        current_settings = self._load_site_config()

        settings = {}
        settings.update(self._to_omd_config(self.load()))
        settings.update(self._to_omd_config(self.load_site_globals()))

        config_change_commands: List[str] = []
        self._logger.debug("Set omd config: %r" % settings)

        for key, val in settings.items():
            if key not in current_settings:
                continue  # Skip settings unknown to current OMD

            if current_settings[key] == val:
                continue  # Skip unchanged settings

            config_change_commands.append("%s=%s" % (key, val))

        if not config_change_commands:
            self._logger.debug("Got no config change commands...")
            return []

        self._logger.debug('Executing "omd config change"')
        self._logger.debug("  Commands: %r" % config_change_commands)

        # We need a background job on remote sites to wait for the restart, so
        # that the central site can gather the result of the activation.
        # On a central site, the waiting for the end of the restart is already
        # taken into account by the activate changes background job within
        # async_progress.js. Just execute the omd config change command
        if is_wato_slave_site():
            job = OMDConfigChangeBackgroundJob()
            if job.is_active():
                raise MKUserError(None, _("Another omd config change job is already running."))

            job.set_function(job.do_execute, config_change_commands)
            job.start()
        else:
            _do_config_change(config_change_commands, self._logger)

        return []

    def _load_site_config(self):
        return self._load_omd_config("%s/site.conf" % self.omd_config_dir)

    def _load_omd_config(self, path):
        settings = {}

        file_path = Path(path)

        if not file_path.exists():
            return {}

        try:
            with file_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if line == "" or line.startswith("#"):
                        continue

                    var, value = line.split("=", 1)

                    if not var.startswith("CONFIG_"):
                        continue

                    key = var[7:].strip()
                    val = value.strip().strip("'")

                    settings[key] = val
        except Exception as e:
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (path, e))

        return settings

    # Convert the raw OMD configuration settings to the WATO config format.
    # The format that is understood by the valuespecs. Since some valuespecs
    # affect multiple OMD config settings, these need to be converted here.
    #
    # Sadly we can not use the Transform() valuespecs, because each configvar
    # only get's the value associated with it's config key.
    def _from_omd_config(self, omd_config):
        settings: Dict[str, Any] = {}

        for key, value in omd_config.items():
            if value == "on":
                settings[key] = True
            elif value == "off":
                settings[key] = False
            else:
                settings[key] = value

        if "LIVESTATUS_TCP" in settings:
            if settings["LIVESTATUS_TCP"]:
                settings["LIVESTATUS_TCP"] = {
                    "port": int(settings["LIVESTATUS_TCP_PORT"]),
                    "tls": settings["LIVESTATUS_TCP_TLS"],
                }
                del settings["LIVESTATUS_TCP_PORT"]
                del settings["LIVESTATUS_TCP_TLS"]

                # Be compatible to older sites that don't have the key in their config yet
                settings.setdefault("LIVESTATUS_TCP_ONLY_FROM", "0.0.0.0")

                if settings["LIVESTATUS_TCP_ONLY_FROM"] != "0.0.0.0":
                    settings["LIVESTATUS_TCP"]["only_from"] = settings[
                        "LIVESTATUS_TCP_ONLY_FROM"
                    ].split()

                del settings["LIVESTATUS_TCP_ONLY_FROM"]
            else:
                settings["LIVESTATUS_TCP"] = None

        if "NSCA" in settings:
            if settings["NSCA"]:
                settings["NSCA"] = int(settings["NSCA_TCP_PORT"])
            else:
                settings["NSCA"] = None

        if "MKEVENTD" in settings:
            if settings["MKEVENTD"]:
                settings["MKEVENTD"] = []

                for proto in ["SNMPTRAP", "SYSLOG", "SYSLOG_TCP"]:
                    if settings["MKEVENTD_%s" % proto]:
                        settings["MKEVENTD"].append(proto)
            else:
                settings["MKEVENTD"] = None

        # Convert from OMD key (to lower, add "site_" prefix)
        settings = {"site_%s" % key.lower(): val for key, val in settings.items()}

        return settings

    # Bring the WATO internal representation int OMD configuration settings.
    # Counterpart of the _from_omd_config() method.
    def _to_omd_config(self, settings):
        # Convert to OMD key
        settings = {key.upper()[5:]: val for key, val in settings.items()}

        if "LIVESTATUS_TCP" in settings:
            if settings["LIVESTATUS_TCP"] is not None:
                settings["LIVESTATUS_TCP_PORT"] = "%s" % settings["LIVESTATUS_TCP"]["port"]
                settings["LIVESTATUS_TCP_TLS"] = settings["LIVESTATUS_TCP"].get("tls", False)

                if "only_from" in settings["LIVESTATUS_TCP"]:
                    settings["LIVESTATUS_TCP_ONLY_FROM"] = " ".join(
                        settings["LIVESTATUS_TCP"]["only_from"]
                    )
                else:
                    settings["LIVESTATUS_TCP_ONLY_FROM"] = "0.0.0.0"

                settings["LIVESTATUS_TCP"] = "on"
            else:
                settings["LIVESTATUS_TCP"] = "off"

        if "NSCA" in settings:
            if settings["NSCA"] is not None:
                settings["NSCA_TCP_PORT"] = "%s" % settings["NSCA"]
                settings["NSCA"] = "on"
            else:
                settings["NSCA"] = "off"

        if "MKEVENTD" in settings:
            if settings["MKEVENTD"] is not None:
                for proto in ["SNMPTRAP", "SYSLOG", "SYSLOG_TCP"]:
                    settings["MKEVENTD_%s" % proto] = proto in settings["MKEVENTD"]

                settings["MKEVENTD"] = "on"

            else:
                settings["MKEVENTD"] = "off"

        omd_config = {}
        for key, value in settings.items():
            if isinstance(value, bool):
                omd_config[key] = "on" if value else "off"
            else:
                omd_config[key] = "%s" % value

        return omd_config


@gui_background_job.job_registry.register
class OMDConfigChangeBackgroundJob(WatoBackgroundJob):
    job_prefix = "omd-config-change"

    @classmethod
    def gui_title(cls):
        return _("Apply OMD config changes")

    def __init__(self):
        super().__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def do_execute(self, config_change_commands: List[str], job_interface):
        _do_config_change(config_change_commands, self._logger)
        job_interface.send_result_message(_("OMD config changes have been applied."))


def _do_config_change(config_change_commands: List[str], omd_logger: logging.Logger) -> None:
    completed_process = subprocess.run(
        ["omd", "config", "change"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
        input="\n".join(config_change_commands),
        check=False,
    )

    omd_logger.debug("  Exit code: %d" % completed_process.returncode)
    omd_logger.debug("  Output: %r" % completed_process.stdout)
    if completed_process.returncode:
        raise MKGeneralException(
            _(
                "Failed to activate changed site "
                "configuration.\nExit code: %d\nConfig: %s\nOutput: %s"
            )
            % (
                completed_process.returncode,
                config_change_commands,
                completed_process.stdout,
            )
        )
