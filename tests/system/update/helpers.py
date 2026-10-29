#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import os
import subprocess
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest

from cmk.crypto.certificate import Certificate
from tests.testlib.common.utils2 import (
    get_services_with_status,
    get_supported_distros,
    is_cleanup_enabled,
    parse_files,
    ServiceInfo,
    version_spec_from_env,
)
from tests.testlib.common.version import (
    CMKPackageInfo,
    CMKVersion,
    edition_from_env,
    get_min_version,
    TypeCMKEdition,
)
from tests.testlib.system.site import Site, SiteFactory

MODULE_PATH = Path(__file__).parent.resolve()
RULES_DIR = MODULE_PATH / "rules"
DUMPS_DIR = MODULE_PATH / "dumps"

logger = logging.getLogger(__name__)


def _get_omd_status(site: Site) -> dict[str, str]:
    """Get the omd status for all services of the given site."""
    cmd = [site.path("bin/omd").as_posix(), "status", "--bare"]
    status = {}
    process = site.execute(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        logger.error("omd status returned RC%s and STDERR=%s", process.returncode, stderr)
    for line in [_ for _ in stdout.splitlines() if " " in _]:
        key, val = (_.strip() for _ in line.split(" ", 1))
        status[key] = {"0": "running", "1": "stopped", "2": "partially running"}.get(val, val)
    return status


def get_site_status(site: Site) -> str | None:
    """Get the overall status of the given site."""
    service_status = _get_omd_status(site)
    logger.debug("Status codes: %s", service_status)
    if len(service_status) > 0:
        status = list(service_status.values())[-1]
        if status == "partially running":
            return status
        if status in ("running", "stopped") and all(
            value == status for value in service_status.values()
        ):
            return status
        logger.error("Invalid service status: %s", service_status)
    return None


def _get_site_factory(package: CMKPackageInfo) -> SiteFactory:
    return SiteFactory(
        package=package,
        prefix="update_",
        enforce_english_gui=False,
    )


def create_site(base_package: CMKPackageInfo) -> Site:
    site_name = "central"
    site_factory = _get_site_factory(base_package)
    site = site_factory.get_existing_site(site_name)
    logger.info("Site exists: %s", site.exists())
    if site.exists():
        logger.info("Dropping existing site ...")
        site.rm()
    elif site.is_running():
        logger.info("Stopping running site before update ...")
        site.stop()
        assert get_site_status(site) == "stopped"
    assert not site.exists(), "Trying to install existing site!"
    logger.info("Creating new site")

    is_cloud = base_package.edition.is_cloud_edition()
    if is_cloud:
        from tests.testlib.system.cloud.utils import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
            create_cloud_initial_config,
        )

        create_cloud_initial_config()

    site = site_factory.get_site(site_name)
    if is_cloud:
        from tests.testlib.system.cloud.utils import (  # type: ignore[import-untyped, unused-ignore, import-not-found]
            cloud_environment,
        )

        ctx: AbstractContextManager[object] = cloud_environment(site.apache_port)
    else:
        ctx = nullcontext()
    with ctx:
        site_factory.initialize_site(site, auto_restart_httpd=True)

    return site


def install_package(package: CMKPackageInfo, site_id: str) -> Site:
    """Install a Checkmk package on the host without creating a site.

    Returns the `Site` handle needed to later uninstall it via `cleanup_cmk_package`.
    """
    site_factory = _get_site_factory(package)
    site = site_factory.get_existing_site(site_id, start=False, init_livestatus=False)
    site.install_cmk()
    return site


def get_target_package(target_edition: TypeCMKEdition) -> CMKPackageInfo:
    return CMKPackageInfo(CMKVersion(version_spec_from_env(CMKVersion.DAILY)), target_edition)


def update_site(
    base_site: Site,
    target_package: CMKPackageInfo,
    interactive: bool,
    license_ca_certificate: Certificate | None = None,
) -> Site:
    """
    Update the given site to the target package, either in interactive or non-interactive mode.

    Returns the updated site.

    Args:
        base_site:              The site to be updated.
        target_package:         The target package info.
        interactive:            Whether to run the update in interactive mode.
        license_ca_certificate: The CA certificate to use for licensing: it will be replaced in the
                                target package during the update process so that the site can use
                                the mocked CA certificate for license validation.
    """
    site_factory = _get_site_factory(target_package)
    min_version = get_min_version()
    logger.info("Updating test-site (interactive-mode=%s) ...", interactive)
    if interactive:
        target_site = site_factory.interactive_update(
            base_site,
            target_package,
            min_version=min_version,
            timeout=60,
            license_ca_certificate=license_ca_certificate,
        )
    else:
        target_site = site_factory.update_as_site_user(
            base_site,
            target_package,
            min_version=min_version,
            license_ca_certificate=license_ca_certificate,
        )

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.debug("Successfully updated '%s' > '%s'!", base_site.package, target_site.package)

    assert str(target_package) in target_site.check_output(["omd", "version"]), (
        "Edition and/or version mismatch during update!"
    )

    return target_site


def create_password(site: Site) -> None:
    site.openapi.passwords.create(
        ident="mydummypass",
        title="Dummypass",
        comment="",
        password="dummy",
        owner="admin",
    )
    site.openapi.changes.activate_and_wait_for_completion()


def inject_rules(site: Site) -> None:
    try:
        with open(RULES_DIR / "ignore.txt", encoding="UTF-8") as ignore_list_file:
            ignore_list = [_ for _ in ignore_list_file.read().splitlines() if _]
    except FileNotFoundError:
        ignore_list = []
    rules_file_names = [
        _ for _ in os.listdir(RULES_DIR) if _.endswith(".json") and _ not in ignore_list
    ]
    for rules_file_name in rules_file_names:
        if edition_from_env().is_community_edition() and rules_file_name.startswith("cmc_"):
            continue
        rules_file_path = RULES_DIR / rules_file_name
        with open(rules_file_path, encoding="UTF-8") as ruleset_file:
            logger.info('Importing rules file "%s"...', rules_file_path)
            rules = json.load(ruleset_file)
            for rule in rules:
                site.openapi.rules.create(value=rule)
    site.activate_changes_and_wait_for_core_reload()


def cleanup_cmk_package(site: Site, request: pytest.FixtureRequest) -> None:
    if is_cleanup_enabled() and not request.config.getoption(name="--skip-uninstall"):
        site.uninstall_cmk()


LEGACY_CONF_D_FILE = Path("etc/check_mk/conf.d/zzz_extends_undefined.mk")
# Generated files a site created before 3.0 holds in extend-only style, and the update action
# that makes each of them define its variables. The base site must have them all, or the
# update test would not notice that action going missing.
# hosts.mk is not among them: the config loader reads the hosts.pkl next to it, which
# create_precompiled_files rewrites, so the verification never executes hosts.mk.
GENERATED_EXTEND_ONLY_FILES = {
    "etc/check_mk/conf.d/wato/rules.mk": "rulesets",
    "etc/check_mk/conf.d/wato/contacts.mk": "selfbootstrap_conf_d_files",
    "etc/check_mk/conf.d/wato/tags.mk": "selfbootstrap_conf_d_files",
    "etc/check_mk/conf.d/wato/notifications.mk": "selfbootstrap_conf_d_files",
    "etc/check_mk/conf.d/wato/notification_parameter.mk": "selfbootstrap_conf_d_files",
    "etc/check_mk/conf.d/wato/passwords.mk": "selfbootstrap_conf_d_files",
}
_UNSEEDED_WARNING_LIST_HEADER = "The following configuration files fail to load:"
_DEFAULTS_WARNING_LIST_HEADER = (
    "The following configuration files rely on the defaults of these variables:"
)
# omd update forwards the output of its hook scripts, cmk-update-config among them, with this
# prefix on every line (see omdlib.scripts).
_OMD_HOOK_OUTPUT_PREFIX = "-| "


def check_generated_files_present(site: Site) -> None:
    """Assert the base site holds every generated file the update has to rewrite.

    Only then does check_unseeded_config_warning prove that the responsible update actions
    still exist and work: a file they miss stays extend-only and gets named by the update.
    """
    missing = {
        path: action
        for path, action in GENERATED_EXTEND_ONLY_FILES.items()
        if not site.file_exists(path)
    }
    assert not missing, (
        "The base site lacks generated files, so the update test would not cover the update "
        f"actions that rewrite them: {missing}"
    )
    logger.info(
        "Base site holds the generated files the update rewrites: %s",
        ", ".join(GENERATED_EXTEND_ONLY_FILES),
    )


def plant_legacy_conf_d_file(site: Site) -> Path:
    """Write a hand-written style config file that extends a variable it never defines.

    Checkmk 3.0 still predefines the variable, so the file loads; the update is expected to
    warn about it, as Checkmk 3.1 will not predefine anything. Returns the absolute path, the
    way the update names it.
    """
    site.write_file(
        LEGACY_CONF_D_FILE,
        "# Planted by the update test: extends a variable it does not define.\n"
        "define_hostgroups.update({'legacy': 'Legacy hosts'})\n",
    )
    planted = site.path(LEGACY_CONF_D_FILE)
    logger.info("Planted %s, which extends a variable it does not define", planted)
    return planted


def check_unseeded_config_warning(site: Site, planted: Path) -> None:
    """Assert that the update warned about exactly the planted file.

    `omd update` copies the output of cmk-update-config to var/log/update.log. Every
    generated file must have been rewritten to define its variables, so the planted one is
    the only file the verification at the end of the update may name. With
    check_generated_files_present on the base site, this also proves the actions listed in
    GENERATED_EXTEND_ONLY_FILES did their job. No generated file extends a variable whose
    default is not empty, so the verification must not name any file for that.
    """
    log_lines = [
        line.removeprefix(_OMD_HOOK_OUTPUT_PREFIX)
        for line in site.read_file("var/log/update.log").splitlines()
    ]
    relying = [i for i, line in enumerate(log_lines) if _DEFAULTS_WARNING_LIST_HEADER in line]
    assert not relying, "update.log names files relying on non-empty defaults:\n" + (
        "\n".join(log_lines[relying[-1] : relying[-1] + 20])
    )
    headers = [i for i, line in enumerate(log_lines) if _UNSEEDED_WARNING_LIST_HEADER in line]
    assert headers, "No warning about unseeded config files in update.log, which ends:\n" + (
        "\n".join(log_lines[-40:])
    )
    named_files: set[Path] = set()
    end = start = headers[-1] + 1
    for end, line in enumerate(log_lines[start:], start):
        if not line.strip():
            if named_files:
                break
            continue  # the header is followed by a blank line
        if not line.startswith(" ") or ": " not in line:
            break
        named_files.add(Path(line.strip().split(": ", 1)[0]))
    else:
        end = len(log_lines)
    logger.info(
        "update.log warns about these configuration files:\n%s", "\n".join(log_lines[start:end])
    )
    assert named_files == {planted}, (
        f"The update should warn about the planted file only, but named: {named_files}"
    )
    logger.info("update.log names exactly the planted file %s", planted)


def check_errors_in_log_files(site: Site) -> None:
    """Assert that there are no unexpected errors in the site log-files"""
    # The CMKFormatter includes the log level (e.g. "ERROR") in every line.
    # TODO: Remove "sigterm" from pattern after CMK-24766 is done
    content_pattern = r"^(?!.*(sigterm)).*(?-i:ERROR).*$"

    error_match_dict = parse_files(
        path_name=site.logs_dir,
        files_name_pattern="*log*",
        content_pattern=content_pattern,
        sudo=True,
    )

    assert not error_match_dict, f"Error string found in one or more log files: {error_match_dict}"


def check_services(
    site: Site,
    hostname: str,
    base_data: dict[str, ServiceInfo],
    skipped_prefixes: tuple[str, ...] = (),
) -> None:
    """Assert that current service status matches previous service status.

    Services whose name starts with one of `skipped_prefixes` may change between OK, WARN and
    CRIT, but must not become UNKNOWN.
    """
    # get update monitoring data
    target_data = site.get_host_services(hostname)

    not_found_services = sorted(set(base_data) - set(target_data))
    err_msg = (
        f"The following services were found in base-version but not in target-version: "
        f"{not_found_services}"
    )
    assert not not_found_services, err_msg

    skipped = {service for service in base_data if service.startswith(skipped_prefixes)}
    unknown_skipped_services = sorted(
        service for service in skipped if target_data[service].state == 3
    )
    unknown_details = [(s, target_data[s].summary) for s in unknown_skipped_services]
    err_msg = (
        f"The following services are `UNKNOWN` in target-version: {unknown_skipped_services}"
        f"\nDetails: {unknown_details}"
    )
    assert not unknown_skipped_services, err_msg

    base_ok_services = get_services_with_status(base_data, 0) - skipped
    target_ok_services = get_services_with_status(target_data, 0)

    not_ok_services = [service for service in base_ok_services if service not in target_ok_services]
    err_details = [
        (s, "state: " + str(target_data[s].state), target_data[s].summary) for s in not_ok_services
    ]
    err_msg = (
        f"The following services were `OK` in base-version but not in target-version: "
        f"{not_ok_services}"
        f"\nDetails: {err_details})"
    )
    assert base_ok_services.issubset(target_ok_services), err_msg


def check_core_reinit(site: Site) -> None:
    """Reinitialize (reload, then restart) the core and check the output"""

    # reload the core and check the output (see CMK-20653)
    logger.info("Reloading the core...")
    ret_reload = site.run(["cmk", "--reload", "--debug"])
    assert ret_reload.returncode == 0, f"Reloading the core failed!\n STDERR:{ret_reload.stderr}"
    logger.warning(ret_reload.stderr)  # log possible warnings coming from STDERR
    assert get_site_status(site) == "running", "Invalid service status after reloading!"

    # restart the core and check the output (see CMK-20653)
    logger.info("Restarting the core...")
    ret_restart = site.run(["cmk", "--restart", "--debug"])
    assert ret_restart.returncode == 0, f"Restarting the core failed!\n STDERR:{ret_restart.stderr}"
    logger.warning(ret_restart.stderr)  # log possible warnings coming from STDERR
    assert get_site_status(site) == "running", "Invalid service status after restarting!"


def bulk_discover_and_schedule(site: Site, hostname: str) -> None:
    """Run service bulk discovery for a single host (ignoring errors), activate changes and schedule checks."""
    logger.debug("Discovering services and waiting for completion...")
    site.openapi.service_discovery.run_bulk_discovery_and_wait_for_completion([hostname])
    site.openapi.changes.activate_and_wait_for_completion()
    site.schedule_check(hostname, "Check_MK", 0)


@dataclass
class BaseVersions:
    """Get all base versions used for the test. Up to five versions are used per branch:
    The first one and the last four.
    """

    @staticmethod
    def _limit_versions(versions: list[str], min_version: CMKVersion) -> list[str]:
        """Select supported earliest and latest versions and eliminate duplicates"""
        max_earliest_versions = 1
        max_latest_versions = 4

        active_versions = [_ for _ in versions if CMKVersion(_) >= min_version]
        earliest_versions = active_versions[0:max_earliest_versions]
        latest_versions = active_versions[-max_latest_versions:]
        # do not use a set to retain the order
        return list(dict.fromkeys(earliest_versions + latest_versions))

    min_version = get_min_version()
    _base_packages: list[CMKPackageInfo] | None = None

    @staticmethod
    def _read_versions(file_name: str) -> list[str] | None:
        versions_file = MODULE_PATH / file_name
        if not versions_file.exists():
            return None
        versions: list[str] = json.loads(versions_file.read_text(encoding="utf-8"))
        return versions

    @classmethod
    def _version_lists(cls) -> list[list[str]]:
        """The release-system-maintained version lists, oldest branch first."""
        previous_branch = cls._read_versions("base_versions_previous_branch.json")
        if previous_branch is None:
            previous_branch = cls._read_versions("base_versions.json")
        if previous_branch is None:
            raise FileNotFoundError(f"No base versions list found in {MODULE_PATH}")
        current_branch = cls._read_versions("base_versions_current_branch.json")
        return [previous_branch] + ([current_branch] if current_branch else [])

    @classmethod
    def get_base_packages(cls) -> list[CMKPackageInfo]:
        if cls._base_packages is None:
            cls._base_packages = [
                CMKPackageInfo(CMKVersion(base_version_str), edition_from_env())
                for versions in cls._version_lists()
                for base_version_str in cls._limit_versions(versions, cls.min_version)
            ]

        assert cls._base_packages, "No base packages found for the test!"
        return cls._base_packages

    @classmethod
    def get_first_release_packages(cls) -> list[CMKPackageInfo]:
        """The `X.Y.0` release of every listed branch, oldest first.

        Ignores the update minimum: customers may still run a branch's first release.
        """
        first_releases = dict.fromkeys(
            CMKVersion(version_str).semantic
            for versions in cls._version_lists()
            for version_str in versions
        )
        return [
            CMKPackageInfo(CMKVersion(version_str), edition_from_env())
            for version_str in first_releases
        ]

    @classmethod
    def get_latest_base_package(cls) -> CMKPackageInfo:
        """Get the latest base package used for the test."""
        return cls.get_base_packages()[-1]


@dataclass
class InteractiveModeDistros:
    DISTROS = [
        "ubuntu-24.04",
        "almalinux-9",
    ]
    assert set(DISTROS).issubset(set(get_supported_distros()))
