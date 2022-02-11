#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import os
import re
from pathlib import Path
import signal
import subprocess
import traceback
from typing import Any, Dict, List, Tuple, Set

from six import ensure_binary, ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.store as store
import cmk.utils.paths

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.hooks as hooks
import cmk.gui.config as config
import cmk.gui.mkeventd as mkeventd
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.watolib.changes import log_audit
from cmk.gui.watolib.utils import (
    wato_root_dir,
    liveproxyd_config_dir,
    multisite_dir,
)
from cmk.gui.plugins.watolib import (
    config_domain_registry,
    ABCConfigDomain,
)
from cmk.gui.type_defs import ConfigDomainName


@config_domain_registry.register
class ConfigDomainCore(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "check_mk"

    def config_dir(self):
        return wato_root_dir()

    def activate(self):
        # TODO: Cleanup
        from cmk.gui.watolib.automations import check_mk_local_automation
        return check_mk_local_automation(config.wato_activation_method)

    def default_globals(self):
        # TODO: Cleanup
        from cmk.gui.watolib.automations import check_mk_local_automation
        return check_mk_local_automation("get-configuration", [],
                                         self._get_global_config_var_names())


@config_domain_registry.register
class ConfigDomainGUI(ABCConfigDomain):
    needs_sync = True
    needs_activation = False

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "multisite"

    def config_dir(self):
        return multisite_dir()

    def activate(self):
        pass

    def default_globals(self):
        return config.default_config


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
        return not cmk_version.is_raw_edition() and config.liveproxyd_enabled

    def config_dir(self):
        return liveproxyd_config_dir()

    def save(self, settings, site_specific=False, custom_site_path=None):
        super(ConfigDomainLiveproxy, self).save(settings,
                                                site_specific=site_specific,
                                                custom_site_path=custom_site_path)
        self.activate()

    def activate(self):
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
                _("Could not reload Livestatus Proxy: %s. See web.log and liveproxyd.log "
                  "for further information.") % e)

    # TODO: Move default values to common module to share
    # the defaults between the GUI code an liveproxyd.
    def default_globals(self):
        return {
            "liveproxyd_log_levels": {
                "cmk.liveproxyd": logging.INFO,
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
        return config.mkeventd_enabled

    def config_dir(self):
        return str(ec.rule_pack_dir())

    def activate(self):
        if getattr(config, "mkeventd_enabled", False):
            mkeventd.execute_command("RELOAD", site=config.omd_site())
            log_audit("mkeventd-activate", _("Activated changes of event console configuration"))
            if hooks.registered('mkeventd-activate-changes'):
                hooks.call("mkeventd-activate-changes")

    def default_globals(self):
        return ec.default_config()


@config_domain_registry.register
class ConfigDomainCACertificates(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    always_activate = True  # Execute this on all sites on all activations

    trusted_cas_file = "%s/var/ssl/ca-certificates.crt" % cmk.utils.paths.omd_root

    # This is a list of directories that may contain .pem files of trusted CAs.
    # The contents of all .pem files will be contantenated together and written
    # to "trusted_cas_file". This is done by the function update_trusted_cas().
    # On a system only a single directory, the first existing one is processed.
    system_wide_trusted_ca_search_paths = [
        "/etc/ssl/certs",  # Ubuntu/Debian/SLES
        "/etc/pki/tls/certs",  # CentOS/RedHat
    ]

    _PEM_RE = re.compile(b"-----BEGIN CERTIFICATE-----\r?.+?\r?-----END CERTIFICATE-----\r?\n?"
                         b"", re.DOTALL)

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
        super(ConfigDomainCACertificates, self).save(settings,
                                                     site_specific=site_specific,
                                                     custom_site_path=custom_site_path)

        current_config = settings.get("trusted_certificate_authorities", {
            "use_system_wide_cas": True,
            "trusted_cas": [],
        })

        # We need to activate this immediately to make syncs to WATO slave sites
        # possible right after changing the option
        #
        # Since this can be called from any WATO page it is not possible to report
        # errors to the user here. The self._update_trusted_cas() method logs the
        # errors - this must be enough for the moment.
        if not site_specific and custom_site_path is None:
            self._update_trusted_cas(current_config)

    def activate(self):
        try:
            return self._update_trusted_cas(config.trusted_certificate_authorities)
        except Exception:
            logger.exception("error updating trusted CAs")
            return [
                "Failed to create trusted CA file '%s': %s" %
                (self.trusted_cas_file, traceback.format_exc())
            ]

    def _update_trusted_cas(self, current_config):
        trusted_cas: List[bytes] = []
        errors: List[str] = []

        if current_config["use_system_wide_cas"]:
            trusted, errors = self._get_system_wide_trusted_ca_certificates()
            trusted_cas += trusted

        trusted_cas += [ensure_binary(e) for e in current_config["trusted_cas"]]

        store.save_bytes_to_file(
            self.trusted_cas_file,
            # we sort to have a deterministic output, s.t. for example liveproxyd can reliably check
            # if the file changed
            b"\n".join(sorted(trusted_cas)),
        )
        return errors

    def _get_system_wide_trusted_ca_certificates(self) -> Tuple[List[bytes], List[str]]:
        trusted_cas: Set[bytes] = set()
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

                    trusted_cas.update(self._get_certificates_from_file(cert_file_path))
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

                    errors.append("Failed to add certificate '%s' to trusted CA certificates. "
                                  "See web.log for details." % cert_file_path)

            break

        return list(trusted_cas), errors

    def _get_certificates_from_file(self, path: Path) -> List[bytes]:
        try:
            # This IO is done as binary IO, even if the files are text files. Since we work with
            # arbitrary files here, we can not be sure about the encoding of these files. Since we
            # only want to concatenate them to a Checkmk global file, it is OK to treat them all as
            # binary.
            with path.open("rb") as f:
                return [match.group(0) for match in self._PEM_RE.finditer(f.read())]
        except IOError as e:
            if e.errno == errno.ENOENT:
                # Silently ignore e.g. dangling symlinks
                return []
            raise

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
        super(ConfigDomainOMD, self).__init__()
        self._logger = logger.getChild("config.omd")

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return "omd"

    def config_dir(self):
        return self.omd_config_dir

    def default_globals(self):
        return self._from_omd_config(self._load_site_config())

    def activate(self):
        current_settings = self._load_site_config()

        settings = {}
        settings.update(self._to_omd_config(self.load()))
        settings.update(self._to_omd_config(self.load_site_globals()))

        config_change_commands = []
        self._logger.debug("Set omd config: %r" % settings)

        for key, val in settings.items():
            if key not in current_settings:
                continue  # Skip settings unknown to current OMD

            if current_settings[key] == settings[key]:
                continue  # Skip unchanged settings

            config_change_commands.append("%s=%s" % (key, val))

        if not config_change_commands:
            self._logger.debug("Got no config change commands...")
            return

        self._logger.debug("Executing \"omd config change\"")
        self._logger.debug("  Commands: %r" % config_change_commands)
        p = subprocess.Popen(
            ["omd", "config", "change"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            close_fds=True,
            encoding="utf-8",
        )
        stdout, _stderr = p.communicate(input="\n".join(config_change_commands))
        self._logger.debug("  Exit code: %d" % p.returncode)
        self._logger.debug("  Output: %r" % stdout)
        if p.returncode != 0:
            raise MKGeneralException(
                _("Failed to activate changed site "
                  "configuration.\nExit code: %d\nConfig: %s\nOutput: %s") %
                (p.returncode, config_change_commands, stdout))

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
                    line = ensure_str(line.strip())

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
                    settings["LIVESTATUS_TCP"]["only_from"] = \
                        settings["LIVESTATUS_TCP_ONLY_FROM"].split()

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
                        settings["LIVESTATUS_TCP"]["only_from"])
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
