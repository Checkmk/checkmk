#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import shutil
import signal
import subprocess
import traceback
import warnings as warnings_module
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from cryptography.hazmat.primitives import hashes
from cryptography.x509 import Certificate, load_pem_x509_certificate
from cryptography.x509.oid import NameOID

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.certs import CN_TEMPLATE, RemoteSiteCertsStore
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.process import pid_from_file, send_signal

import cmk.gui.watolib.config_domain_name as config_domain_name
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.config import active_config, get_default_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, get_language_alias, is_community_translation
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.userdb import load_users, save_users
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    DomainRequest,
    generate_hosts_to_update_settings,
    SerializedSettings,
)
from cmk.gui.watolib.utils import liveproxyd_config_dir, multisite_dir, wato_root_dir


class _NegativeSerialException(Exception):
    def __init__(self, message: str, subject: str, fingerprint: str) -> None:
        super().__init__(message)
        self.subject = subject
        self.fingerprint = fingerprint

    def should_be_ignored(self) -> bool:
        # We ignore CAs with negative serials and we warn about them, except these, see CMK-16410
        return self.fingerprint in (
            "88497f01602f3154246ae28c4d5aef10f1d87ebb76626f4ae0b7f95ba7968799",  # EC-ACC
        )


@dataclass
class ConfigDomainCoreSettings:
    hosts_to_update: list[HostName] = field(default_factory=list)

    def validate(self) -> None:
        for hostname in self.hosts_to_update:
            if not isinstance(hostname, str):
                raise MKGeneralException(f"Invalid host name type in ConfigDomain: {self}")

    def __post_init__(self) -> None:
        self.validate()


class ConfigDomainCore(ABCConfigDomain):
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.CORE

    def config_dir(self):
        return wato_root_dir()

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # Import cycle
        from cmk.gui.watolib.check_mk_automations import reload, restart

        return {"restart": restart, "reload": reload}[active_config.wato_activation_method](
            self._parse_settings(settings).hosts_to_update
        ).config_warnings

    def _parse_settings(
        self, activate_settings: SerializedSettings | None
    ) -> ConfigDomainCoreSettings:
        if activate_settings is None:
            activate_settings = {}

        return ConfigDomainCoreSettings(**activate_settings)

    def default_globals(self) -> Mapping[str, Any]:
        # Import cycle
        from cmk.gui.watolib.check_mk_automations import get_configuration

        return get_configuration(*self._get_global_config_var_names()).result

    @classmethod
    def get_domain_request(cls, settings: list[SerializedSettings]) -> DomainRequest:
        # The incremental activate only works, if all changes use the hosts_to_update option
        hosts_to_update: set[HostName] = set()
        for setting in settings:
            if not setting.get("hosts_to_update"):
                return DomainRequest(cls.ident(), generate_hosts_to_update_settings([]))
            hosts_to_update.update(setting["hosts_to_update"])

        return DomainRequest(cls.ident(), generate_hosts_to_update_settings(list(hosts_to_update)))


class ConfigDomainGUI(ABCConfigDomain):
    needs_sync = True
    needs_activation = False

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.GUI

    def config_dir(self):
        return multisite_dir()

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        warnings: ConfigurationWarnings = []
        if not active_config.enable_community_translations:
            # Check whether a community translated language is set either as default language or as
            # user specific UI language. Fix the respective language settings to 'English'.
            dflt_lang = active_config.default_language
            if is_community_translation(dflt_lang):
                warnings.append(
                    f"Resetting the default language '{get_language_alias(dflt_lang)}' to 'English' due to "
                    "globally disabled commmunity translations (Global settings > User interface)."
                )
                gui_config = self.load()
                gui_config.pop("default_language", None)
                self.save(gui_config)
                active_config.default_language = "en"

            users = load_users()
            for ident, user_config in users.items():
                lang: str = user_config.get("language", "en")
                if lang is None:
                    lang = "en"
                if is_community_translation(lang):
                    warnings.append(
                        f"For user '{ident}': Resetting the language '{get_language_alias(lang)}' to the default "
                        f"language '{get_language_alias(active_config.default_language)}' due to "
                        "globally disabled commmunity translations (Global settings > User "
                        "interface)."
                    )
                    user_config.pop("language", None)
            save_users(users, datetime.now())

        if active_config.wato_use_git and shutil.which("git") is None:
            raise MKUserError(
                "",
                _(
                    "'git' command was not found on this system, but it is required for versioning the configuration."
                    "Please either install 'git' or disable git configuration tracking in setup."
                ),
            )

        if settings and settings.get("need_apache_reload", False):
            completed_process = subprocess.run(
                ["omd", "reload", "apache"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )

            if completed_process.returncode:
                warnings.append(completed_process.stdout)

        return warnings

    def default_globals(self) -> Mapping[str, Any]:
        return get_default_config()

    @classmethod
    def get_domain_request(cls, settings: list[SerializedSettings]) -> DomainRequest:
        return DomainRequest(
            cls.ident(), {k: v for setting in settings for k, v in setting.items()}
        )


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plug-in hierarchy and
# move this to a CEE/CME specific watolib plug-in
class ConfigDomainLiveproxy(ABCConfigDomain):
    needs_sync = False
    needs_activation = False
    in_global_settings = True

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.LIVEPROXY

    @classmethod
    def enabled(cls):
        return (
            cmk_version.edition() is not cmk_version.Edition.CRE
            and active_config.liveproxyd_enabled
        )

    def config_dir(self):
        return liveproxyd_config_dir()

    def save(self, settings, site_specific=False, custom_site_path=None):
        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)
        self.activate()

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        log_audit(
            "liveproxyd-activate",
            "Activating changes of Livestatus Proxy configuration",
        )

        try:
            pidfile = Path(cmk.utils.paths.livestatus_unix_socket).with_name("liveproxyd.pid")
            try:
                with pidfile.open(encoding="utf-8") as f:
                    pid = int(f.read().strip())

                os.kill(pid, signal.SIGHUP)
            except ProcessLookupError:
                # ESRCH: PID in pidfiles does not exist: No reload needed.
                pass
            except FileNotFoundError:
                # ENOENT: No liveproxyd running: No reload needed.
                pass
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
    def default_globals(self) -> Mapping[str, Any]:
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
        return config_domain_name.CA_CERTIFICATES

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

        # We need to activate this immediately to make syncs to Setup slave sites
        # possible right after changing the option
        #
        # Since this can be called from any Setup page it is not possible to report
        # errors to the user here. The self._update_trusted_cas() method logs the
        # errors - this must be enough for the moment.
        if not site_specific and custom_site_path is None:
            self._update_trusted_cas(current_config)
            self.update_remote_sites_cas(current_config["trusted_cas"])

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
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
                f"Failed to create trusted CA file '{self.trusted_cas_file}': {traceback.format_exc()}"
            ]

    def _update_trusted_cas(self, current_config) -> ConfigurationWarnings:  # type: ignore[no-untyped-def]
        trusted_cas: list[str] = []
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

    # this is only a non-member classmethod, because it used in update config to 2.2
    @classmethod
    def update_remote_sites_cas(cls, trusted_cas: list[str]) -> None:
        remote_cas_store = RemoteSiteCertsStore(cmk.utils.paths.remote_sites_cas_dir)
        for site, cert in cls._remote_sites_cas(trusted_cas).items():
            remote_cas_store.save(site, cert)

    @staticmethod
    def _load_cert(cert_str: str) -> Certificate:
        """load a cert and return it except it has a negative serial number

        Cryptography started to warn about negative serial numbers, these warnings are "blindly" written
        to stderr so it might confuse users.
        Here we catch these warnings and raise an exception if the serial number is negative.
        """
        with warnings_module.catch_warnings(record=True, category=UserWarning):
            cert = load_pem_x509_certificate(cert_str.encode())
            if cert.serial_number < 0:
                raise _NegativeSerialException(
                    f"Certificate with a negative serial number {cert.serial_number!r}",
                    cert.subject.rfc4514_string(),
                    cert.fingerprint(hashes.SHA256()).hex(),
                )
        return cert

    @staticmethod
    def _load_certs(trusted_cas: list[str]) -> Iterable[Certificate]:
        for cert_str in trusted_cas:
            try:
                yield ConfigDomainCACertificates._load_cert(cert_str)
            except _NegativeSerialException as e:
                if not e.should_be_ignored():
                    logger.warning(
                        "There is a certificate %r with a negative serial number in the trusted certificate authorities! Ignoring that...",
                        e.subject,
                    )

    @staticmethod
    def _remote_sites_cas(trusted_cas: list[str]) -> Mapping[SiteId, Certificate]:
        return {
            site_id: cert
            for cert in sorted(
                ConfigDomainCACertificates._load_certs(trusted_cas),
                key=lambda cert: cert.not_valid_after_utc,
            )
            if (
                (cns := cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME))
                and (site_id := CN_TEMPLATE.extract_site(cns[0].rfc4514_string()))
            )
        }

    # this is only a non-member, because it used in update config to 2.2
    @staticmethod
    def is_valid_cert(raw_cert: str) -> bool:
        try:
            ConfigDomainCACertificates._load_cert(raw_cert)
            return True
        except ValueError:
            return False

    def _get_system_wide_trusted_ca_certificates(self) -> tuple[list[str], list[str]]:
        trusted_cas: set[str] = set()
        errors: list[str] = []
        for p in self.system_wide_trusted_ca_search_paths:
            cert_path = Path(p)

            if not cert_path.is_dir():
                continue

            for entry in cert_path.iterdir():
                if entry.suffix not in [".pem", ".crt"]:
                    continue

                cert_file_path = entry.absolute()
                try:
                    raw_certs = raw_certificates_from_file(cert_file_path)
                except (OSError, PermissionError):
                    # This error is shown to the user as warning message during "activate changes".
                    # We keep this message for the moment because we think that it is a helpful
                    # trigger for further checking web.log when a really needed certificate can
                    # not be read.
                    #
                    # We know a permission problem with some files that are created by default on
                    # some distros. We simply ignore these files because we assume that they are
                    # not needed.
                    if cert_file_path != Path("/etc/ssl/certs/localhost.crt"):
                        logger.exception("Error reading certificates from %s", cert_file_path)
                        errors.append(
                            f"Failed to add certificate '{cert_file_path}' to trusted CA certificates. "
                            "See web.log for details."
                        )
                    continue

                for raw_cert in raw_certs:
                    try:
                        if self.is_valid_cert(raw_cert):
                            trusted_cas.add(raw_cert)
                            continue
                    except _NegativeSerialException as e:
                        if e.should_be_ignored():
                            continue

                    logger.exception("Skipping invalid certificates in file %s", cert_file_path)
                    errors.append(
                        f"Failed to add invalid certificate in '{cert_file_path}' to trusted CA certificates. "
                        "See web.log for details."
                    )

            break

        return list(trusted_cas), errors

    def default_globals(self) -> Mapping[str, Any]:
        return {
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            }
        }


class ConfigDomainOMD(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    omd_config_dir = f"{cmk.utils.paths.omd_root}/etc/omd"

    def __init__(self) -> None:
        super().__init__()
        self._logger: logging.Logger = logger.getChild("config.omd")

    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.OMD

    def config_dir(self):
        return self.omd_config_dir

    def default_globals(self) -> Mapping[str, Any]:
        return self._from_omd_config(self._load_site_config())

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        current_settings = self._load_site_config()

        settings = {}
        settings.update(self._to_omd_config(self.load()))
        settings.update(self._to_omd_config(self.load_site_globals()))

        config_change_commands: list[str] = []
        self._logger.debug("Set omd config: %r" % settings)

        for key, val in settings.items():
            if key not in current_settings:
                continue  # Skip settings unknown to current OMD

            if current_settings[key] == val:
                continue  # Skip unchanged settings

            config_change_commands.append(f"{key}={val}")

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

            job.start(lambda job_interface: job.do_execute(config_change_commands, job_interface))
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

    # Convert the raw OMD configuration settings to the Setup config format.
    # The format that is understood by the valuespecs. Since some valuespecs
    # affect multiple OMD config settings, these need to be converted here.
    #
    # Sadly we can not use the Transform() valuespecs, because each configvar
    # only get's the value associated with it's config key.
    def _from_omd_config(self, omd_config):  # pylint: disable=too-many-branches
        settings: dict[str, Any] = {}

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

    # Bring the Setup internal representation int OMD configuration settings.
    # Counterpart of the _from_omd_config() method.
    def _to_omd_config(self, settings):  # pylint: disable=too-many-branches
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


class OMDConfigChangeBackgroundJob(BackgroundJob):
    job_prefix = "omd-config-change"

    @classmethod
    def gui_title(cls) -> str:
        return _("Apply OMD config changes")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )

    def do_execute(
        self,
        config_change_commands: list[str],
        job_interface: BackgroundProcessInterface,
    ) -> None:
        _do_config_change(config_change_commands, self._logger)
        job_interface.send_result_message(_("OMD config changes have been applied."))


def _do_config_change(config_change_commands: list[str], omd_logger: logging.Logger) -> None:
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
