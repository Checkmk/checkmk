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
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, NewType, override

from pydantic import BaseModel

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId
from cmk.crypto.certificate import Certificate, CertificatePEM, NegativeSerialException
from cmk.crypto.hash import HashAlgorithm
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import active_config, get_default_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import GlobalSettings, TrustedCertificateAuthorities
from cmk.gui.utils.html import HTML
from cmk.gui.watolib import config_domain_name
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    DomainRequest,
    generate_hosts_to_update_settings,
    SerializedSettings,
)
from cmk.gui.watolib.piggyback_hub import validate_piggyback_hub_config
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir
from cmk.utils.certs import cert_dir, CertManagementEvent, CN_TEMPLATE, RemoteSiteCertsStore, SiteCA
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.log.security_event import log_security_event

ProcessId = NewType("ProcessId", int)


def should_be_negative_serial_exception_be_ignored(exception: NegativeSerialException) -> bool:
    # We ignore CAs with negative serials and we warn about them, except these, see CMK-16410
    return (
        exception.fingerprint
        in (
            "88:49:7F:01:60:2F:31:54:24:6A:E2:8C:4D:5A:EF:10:F1:D8:7E:BB:76:62:6F:4A:E0:B7:F9:5B:A7:96:87:99",  # EC-ACC
        )
    )


@dataclass
class ConfigDomainCoreSettings:
    hosts_to_update: list[HostName] = field(default_factory=list)

    def validate(self) -> None:
        for hostname in self.hosts_to_update:
            if not isinstance(hostname, str):
                raise MKGeneralException(f"Invalid hostname type in ConfigDomain: {self}")

    def __post_init__(self) -> None:
        self.validate()


@lru_cache
def _core_config_default_globals(
    config_var_names: Sequence[str], *, debug: bool
) -> Mapping[str, object]:
    # Import cycle
    from cmk.gui.watolib.check_mk_automations import get_configuration

    return get_configuration(config_var_names, debug=debug).result


def _hang_up(pid_file: Path) -> None:
    if pid := pid_from_file(pid_file):
        os.kill(pid, signal.SIGHUP)


def reload_stunnel() -> None:
    _hang_up(cmk.utils.paths.omd_root / "tmp" / "run" / "stunnel-server.pid")


def reload_agent_receiver() -> None:
    _hang_up(cmk.utils.paths.omd_root / "tmp" / "run" / "agent-receiver.pid")


class ConfigDomainCore(ABCConfigDomain):
    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.CORE

    @override
    def config_dir(self) -> Path:
        return wato_root_dir()

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # Import cycle
        from cmk.gui.watolib.check_mk_automations import reload, restart

        return {"restart": restart, "reload": reload}[active_config.wato_activation_method](
            self._parse_settings(settings).hosts_to_update, debug=active_config.debug
        ).config_warnings

    def _parse_settings(
        self, activate_settings: SerializedSettings | None
    ) -> ConfigDomainCoreSettings:
        if activate_settings is None:
            activate_settings = {}

        return ConfigDomainCoreSettings(
            hosts_to_update=list(activate_settings.get("hosts_to_update", []))
        )

    @override
    def default_globals(self) -> Mapping[str, Any]:
        return _core_config_default_globals(
            tuple(self._get_global_config_var_names()), debug=active_config.debug
        )

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

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.GUI

    @override
    def config_dir(self) -> Path:
        return multisite_dir()

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        warnings: ConfigurationWarnings = []

        if active_config.wato_use_git and shutil.which("git") is None:
            raise MKUserError(
                "",
                _(
                    "'git' command was not found on this system, but it is required for versioning the configuration. "
                    "Please either install 'git' or disable git configuration tracking in Setup."
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

    @override
    def default_globals(self) -> GlobalSettings:
        return get_default_config()

    @classmethod
    def get_domain_request(cls, settings: list[SerializedSettings]) -> DomainRequest:
        setting = SerializedSettings()
        for s in settings:
            setting.update(s)
        return DomainRequest(cls.ident(), setting)


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plug-in hierarchy and
# move this to a commercial edition specific watolib plug-in
class ConfigDomainLiveproxy(ABCConfigDomain):
    needs_sync = False
    needs_activation = False
    in_global_settings = True

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.LIVEPROXY

    @override
    @classmethod
    def enabled(cls) -> bool:
        return (
            cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY
            and active_config.liveproxyd_enabled
        )

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.default_config_dir / "liveproxyd.d/wato"

    @override
    def save(
        self,
        settings: GlobalSettings,
        site_specific: bool = False,
        custom_site_path: str | None = None,
    ) -> None:
        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)
        self.activate()

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        log_audit(
            action="liveproxyd-activate",
            message="Activating changes of Livestatus Proxy configuration",
            user_id=user.id,
            use_git=active_config.wato_use_git,
        )

        try:
            pidfile = cmk.utils.paths.livestatus_unix_socket.with_name("liveproxyd.pid")
            try:
                with pidfile.open(encoding="utf-8") as f:
                    pid = int(f.read().strip())

                os.kill(pid, signal.SIGHUP)
            except ProcessLookupError:
                # ESRCH: PID in pidfiles does not exist: No reload needed.
                logger.warning("Did not reload liveproxyd (PID not found)")
            except FileNotFoundError:
                # ENOENT: No liveproxyd running: No reload needed.
                # Reduced log level, as otherwise it would be displayed in the output
                # of cmk-update-config, where all daemons are stopped.
                logger.info("Did not reload liveproxyd (Missing PID file)")
            except ValueError:
                # ignore empty pid file (may happen during locking in
                # cmk.ccc.daemon.lock_with_pid_file().  We are in the
                # situation where the livstatus proxy is in early phase of the
                # startup. The configuration is loaded later -> no reload needed
                logger.warning("Did not reload liveproxyd (Empty PID file)")

        except Exception as e:
            logger.exception("error reloading liveproxyd")
            raise MKGeneralException(
                _(
                    "Could not reload Livestatus proxy: %s. See web.log and liveproxyd.log "
                    "for further information."
                )
                % e
            )
        return []

    # TODO: Move default values to common module to share
    # the defaults between the GUI code an liveproxyd.
    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "liveproxyd_log_levels": {
                "cmk.liveproxyd": logging.INFO,
            },
            "liveproxyd_default_connection_params": ConfigDomainLiveproxy.connection_params_defaults(),
        }

    @staticmethod
    def connection_params_defaults() -> GlobalSettings:
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

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.CA_CERTIFICATES

    @override
    def config_dir(self) -> Path:
        return multisite_dir()

    @staticmethod
    def log_changes(
        config_before: TrustedCertificateAuthorities | None,
        config_after: TrustedCertificateAuthorities,
    ) -> None:
        if config_before is None:
            current_certs = {}
        else:
            current_certs = {
                (cert := Certificate.load_pem(CertificatePEM(value))).fingerprint(
                    HashAlgorithm.Sha256
                ): cert
                for value in config_before["trusted_cas"] or []
            }

        new_certs = {
            (cert := Certificate.load_pem(CertificatePEM(value))).fingerprint(
                HashAlgorithm.Sha256
            ): cert
            for value in config_after["trusted_cas"]
        }

        added_certs = [
            new_certs[fingerprint] for fingerprint in new_certs if fingerprint not in current_certs
        ]
        removed_certs = [
            current_certs[fingerprint]
            for fingerprint in current_certs
            if fingerprint not in new_certs
        ]

        for cert in added_certs:
            log_security_event(
                CertManagementEvent(
                    event="certificate added",
                    component="trusted certificate authorities",
                    actor=user.id,
                    cert=cert,
                )
            )
        for cert in removed_certs:
            log_security_event(
                CertManagementEvent(
                    event="certificate removed",
                    component="trusted certificate authorities",
                    actor=user.id,
                    cert=cert,
                )
            )

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / (
            "ca-certificates_sitespecific.mk" if site_specific else "ca-certificates.mk"
        )

    @override
    def save(
        self,
        settings: GlobalSettings,
        site_specific: bool = False,
        custom_site_path: str | None = None,
    ) -> None:
        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)

        current_config = settings.get("trusted_certificate_authorities", self.default_globals())

        # We need to activate this immediately to make syncs to distributed
        # setup remote sites possible right after changing the option
        #
        # Since this can be called from any Setup page it is not possible to report
        # errors to the user here. The self._update_trusted_cas() method logs the
        # errors - this must be enough for the moment.
        if not site_specific and custom_site_path is None:
            self._update_trusted_cas(current_config)
            self.update_remote_sites_cas(current_config["trusted_cas"])

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        try:
            warnings = self._update_trusted_cas(active_config.trusted_certificate_authorities)
            reload_stunnel()
        except Exception:
            logger.exception("error updating trusted CAs")
            return [
                f"Failed to create trusted CA file '{self.trusted_cas_file}': {traceback.format_exc()}"
            ]
        return warnings

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    def _update_trusted_cas(
        self, current_config: TrustedCertificateAuthorities
    ) -> ConfigurationWarnings:
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
    def update_remote_sites_cas(cls, trusted_cas: Sequence[str]) -> None:
        remote_cas_store = RemoteSiteCertsStore(cmk.utils.paths.remote_sites_cas_dir)
        for site, cert in cls._remote_sites_cas(trusted_cas).items():
            remote_cas_store.save(site, cert)

    @staticmethod
    def _load_certs(trusted_cas: Sequence[str]) -> Iterable[Certificate]:
        for cert_str in trusted_cas:
            try:
                yield Certificate.load_pem(CertificatePEM(cert_str))
            except NegativeSerialException as e:
                if not should_be_negative_serial_exception_be_ignored(e):
                    logger.warning(
                        "There is a certificate %r with a negative serial number in the trusted certificate authorities! Ignoring that...",
                        e.subject,
                    )

    @staticmethod
    def _remote_sites_cas(trusted_cas: Sequence[str]) -> Mapping[SiteId, Certificate]:
        return {
            site_id: cert
            for cert in sorted(
                ConfigDomainCACertificates._load_certs(trusted_cas),
                key=lambda cert: cert.not_valid_after,
            )
            if (
                (cns := cert.subject.rfc4514_string())
                # TODO: use certificate's subject alternative name instead of "parsing" the CN
                and (site_id := CN_TEMPLATE.extract_site(cns))
            )
        }

    # this is only a non-member, because it used in update config to 2.2
    @staticmethod
    def is_valid_cert(raw_cert: str) -> bool:
        try:
            Certificate.load_pem(CertificatePEM(raw_cert))
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
                except OSError as e:
                    logger.error(
                        "Failed to add certificate '%s' to trusted CA certificates with error '%s'.",
                        cert_file_path,
                        e,
                    )
                    continue

                for raw_cert in raw_certs:
                    try:
                        if self.is_valid_cert(raw_cert):
                            trusted_cas.add(raw_cert)
                            continue
                    except NegativeSerialException as e:
                        if should_be_negative_serial_exception_be_ignored(e):
                            continue

                    logger.exception("Skipping invalid certificates in file %s", cert_file_path)
                    errors.append(
                        f"Failed to add invalid certificate in '{cert_file_path}' to trusted CA certificates. "
                        "See web.log for details."
                    )

            break

        return list(trusted_cas), errors

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                "trusted_cas": [],
            }
        }


class ConfigDomainSiteCertificate(ABCConfigDomain):
    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.SITE_CERTIFICATE

    @override
    def config_dir(self) -> Path:
        return multisite_dir() / "site_certificate"

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        SiteCA.load(cert_dir(cmk.utils.paths.omd_root)).create_site_certificate(
            omd_site(),
            additional_sans=active_config.site_subject_alternative_names,
        )
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        reload_stunnel()
        reload_agent_receiver()

        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return {"site_subject_alternative_names": []}


def pid_from_file(pid_file: Path) -> ProcessId | None:
    """Read a process id from a given pid file"""
    try:
        return ProcessId(int(store.load_object_from_file(pid_file, default=None)))
    except Exception:
        return None


def finalize_specifically_set_settings(
    global_settings: GlobalSettings, site_specific_settings: GlobalSettings
) -> GlobalSettings:
    return {**global_settings, **site_specific_settings}


def finalize_all_settings(
    default_globals: GlobalSettings,
    global_settings: GlobalSettings,
    site_specific_settings: GlobalSettings,
) -> GlobalSettings:
    return {
        **default_globals,
        **finalize_specifically_set_settings(global_settings, site_specific_settings),
    }


def finalize_all_settings_per_site(
    default_globals: GlobalSettings,
    global_settings: GlobalSettings,
    site_specific_settings_per_site: Mapping[SiteId, GlobalSettings],
) -> Mapping[SiteId, GlobalSettings]:
    final_settings_per_site = {
        site_id: finalize_all_settings(default_globals, global_settings, site_conf)
        for site_id, site_conf in site_specific_settings_per_site.items()
    }
    return final_settings_per_site


class ConfigDomainOMD(ABCConfigDomain):
    needs_sync = True
    needs_activation = True
    omd_config_dir = cmk.utils.paths.omd_root / "etc/omd"

    def __init__(self) -> None:
        super().__init__()
        self._logger: logging.Logger = logger.getChild("config.omd")

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return config_domain_name.OMD

    @classmethod
    def hint(cls) -> HTML:
        return HTML.without_escaping(
            _(
                "Changing this setting triggers a full restart of all affected sites during activate changes."
            )
        )

    @override
    def config_dir(self) -> Path:
        return self.omd_config_dir

    @override
    def default_globals(self) -> GlobalSettings:
        return self._from_omd_config(self._load_site_config())

    def save(
        self,
        settings: GlobalSettings,
        site_specific: bool = False,
        custom_site_path: str | None = None,
    ) -> None:
        piggyback_hub_config_var_ident = "site_piggyback_hub"
        # custom_site_path is used for snapshot creation for activate changes, we don't reliably
        # know for which site the settings are being stored here, but they should already be
        # validated at this point
        if piggyback_hub_config_var_ident in settings and not custom_site_path:
            site_specific_settings = {
                site_id: deepcopy(site_conf.get("globals", {}))
                for site_id, site_conf in active_config.sites.items()
            }
            if site_specific:
                global_settings = self.load()
                site_specific_settings[omd_site()] = dict(settings)
            else:
                global_settings = settings

            validate_piggyback_hub_config(
                active_config.sites,
                finalize_all_settings_per_site(
                    self.get_all_default_globals(), global_settings, site_specific_settings
                ),
            )

        super().save(settings, site_specific=site_specific, custom_site_path=custom_site_path)

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        # see if we can / should move something from activate() here
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        current_settings = self._load_site_config()

        omd_settings = finalize_specifically_set_settings(
            self._to_omd_config(self.load()), self._to_omd_config(self.load_site_globals())
        )

        config_change_commands: list[str] = []
        self._logger.debug("Set omd config: %r" % omd_settings)

        for key, val in omd_settings.items():
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
        if is_distributed_setup_remote_site(active_config.sites):
            job = OMDConfigChangeBackgroundJob()
            if (
                result := job.start(
                    JobTarget(
                        callable=omd_config_change_job_entry_point,
                        args=OMDConfigChangeJobArgs(
                            commands=config_change_commands,
                        ),
                    ),
                    InitialStatusArgs(
                        title=job.gui_title(),
                        lock_wato=False,
                        stoppable=False,
                        user=str(user.id) if user.id else None,
                    ),
                )
            ).is_error():
                raise result.error
        else:
            _do_config_change(config_change_commands, self._logger)

        return []

    def _load_site_config(self) -> dict[str, object]:
        return self._load_omd_config(self.omd_config_dir / "site.conf")

    def _load_omd_config(self, file_path: Path) -> dict[str, object]:
        if not file_path.exists():
            return {}

        settings = dict[str, object]()
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
            raise MKGeneralException(_("Cannot read configuration file %s: %s") % (file_path, e))

        return settings

    # Convert the raw OMD configuration settings to the Setup config format.
    # The format that is understood by the valuespecs. Since some valuespecs
    # affect multiple OMD config settings, these need to be converted here.
    #
    # Sadly we can not use the Transform() valuespecs, because each configvar
    # only get's the value associated with it's config key.
    def _from_omd_config(self, omd_config: dict[str, Any]) -> dict[str, object]:
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

        if "TRACE_RECEIVE" in settings:
            if settings["TRACE_RECEIVE"]:
                settings["TRACE_RECEIVE"] = {
                    "address": settings["TRACE_RECEIVE_ADDRESS"],
                    "port": int(settings["TRACE_RECEIVE_PORT"]),
                }
                del settings["TRACE_RECEIVE_ADDRESS"]
                del settings["TRACE_RECEIVE_PORT"]
            else:
                settings["TRACE_RECEIVE"] = None

        if "TRACE_SEND" in settings:
            if settings["TRACE_SEND"]:
                target = settings.pop("TRACE_SEND_TARGET", "")
                if target == "local_site":
                    settings["TRACE_SEND"] = target
                else:
                    settings["TRACE_SEND"] = (
                        "other_collector",
                        {
                            "url": target,
                        },
                    )
            else:
                settings["TRACE_SEND"] = "no_tracing"

        # Convert from OMD key (to lower, add "site_" prefix)
        settings = {"site_%s" % key.lower(): val for key, val in settings.items()}

        return settings

    # Bring the Setup internal representation int OMD configuration settings.
    # Counterpart of the _from_omd_config() method.
    def _to_omd_config(self, settings: GlobalSettings) -> GlobalSettings:
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

        if "TRACE_RECEIVE" in settings:
            if settings["TRACE_RECEIVE"] is not None:
                settings["TRACE_RECEIVE_ADDRESS"] = settings["TRACE_RECEIVE"]["address"]
                settings["TRACE_RECEIVE_PORT"] = str(settings["TRACE_RECEIVE"]["port"])
                settings["TRACE_RECEIVE"] = "on"
            else:
                settings["TRACE_RECEIVE"] = "off"

        if "TRACE_SEND" in settings:
            if settings["TRACE_SEND"] != "no_tracing":
                if settings["TRACE_SEND"] == "local_site":
                    settings["TRACE_SEND_TARGET"] = settings["TRACE_SEND"]
                elif (
                    isinstance(settings["TRACE_SEND"], tuple)
                    and settings["TRACE_SEND"][0] == "other_collector"
                ):
                    settings["TRACE_SEND_TARGET"] = settings["TRACE_SEND"][1]["url"]
                else:
                    raise ValueError(f"Unhandled value: {settings['TRACE_SEND']}")
                settings["TRACE_SEND"] = "on"
            else:
                settings["TRACE_SEND"] = "off"

        omd_config = dict[str, object]()
        for key, value in settings.items():
            if isinstance(value, bool):
                omd_config[key] = "on" if value else "off"
            else:
                omd_config[key] = "%s" % value

        return omd_config


class OMDConfigChangeJobArgs(BaseModel, frozen=True):
    commands: Sequence[str]


def omd_config_change_job_entry_point(
    job_interface: BackgroundProcessInterface, args: OMDConfigChangeJobArgs
) -> None:
    OMDConfigChangeBackgroundJob().do_execute(args.commands, job_interface)


class OMDConfigChangeBackgroundJob(BackgroundJob):
    job_prefix = "omd-config-change"

    @classmethod
    def gui_title(cls) -> str:
        return _("Apply OMD config changes")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def do_execute(
        self, config_change_commands: Sequence[str], job_interface: BackgroundProcessInterface
    ) -> None:
        _do_config_change(config_change_commands, self._logger)
        job_interface.send_result_message(_("OMD config changes have been applied."))


def _do_config_change(config_change_commands: Sequence[str], omd_logger: logging.Logger) -> None:
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
