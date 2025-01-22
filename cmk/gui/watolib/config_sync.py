#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Preparing the site configuration in distributed setups for synchronization"""

import abc
import hashlib
import itertools
import multiprocessing
import os
import subprocess
import tarfile
import time
import traceback
from pathlib import Path
from typing import NamedTuple

from livestatus import SiteConfiguration, SiteGlobals, SiteId

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry

import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.userdb import user_sync_default_config
from cmk.gui.watolib.config_domain_name import wato_fileheader

from cmk.messaging import rabbitmq

Command = list[str]


class _BaseReplicationPath(NamedTuple):
    """Needed for the ReplicationPath class to call __new__ method."""

    ty: str
    ident: str
    site_path: str
    excludes: list[str]


class ReplicationPath(_BaseReplicationPath):
    def __new__(cls, ty: str, ident: str, site_path: str, excludes: list[str]) -> "ReplicationPath":
        if site_path.startswith("/"):
            raise Exception("ReplicationPath.path must be a path relative to the site root")
        cleaned_path = site_path.rstrip("/")

        if ".*new*" not in excludes:
            final_excludes = excludes[:]
            final_excludes.append(".*new*")  # exclude all temporary files
        else:
            final_excludes = excludes

        return super().__new__(
            cls,
            ty=ty,
            ident=ident,
            site_path=cleaned_path,
            excludes=final_excludes,
        )


class ReplicationPathRegistry(Registry[ReplicationPath]):
    def plugin_name(self, instance: ReplicationPath) -> str:
        return instance.ident


replication_path_registry = ReplicationPathRegistry()


class SnapshotSettings(NamedTuple):
    # TODO: Refactor to Path
    snapshot_path: str
    # TODO: Refactor to Path
    work_dir: str
    # TODO: Clarify naming (-> replication path or snapshot component?)
    snapshot_components: list[ReplicationPath]
    component_names: set[str]
    site_config: SiteConfiguration
    rabbitmq_definition: rabbitmq.Definitions


class ABCSnapshotDataCollector(abc.ABC):
    """Prepares files to be synchronized to the remote sites"""

    def __init__(self, site_snapshot_settings: dict[SiteId, SnapshotSettings]) -> None:
        super().__init__()
        self._site_snapshot_settings = site_snapshot_settings
        self._logger = logger.getChild(self.__class__.__name__)

    @abc.abstractmethod
    def prepare_snapshot_files(self) -> None:
        """Site independent preparation of files to be used for the sync snapshots
        This will be called once before iterating over all sites.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_generic_components(self) -> list[ReplicationPath]:
        """Return the site independent snapshot components
        These will be collected by the SnapshotManager once when entering the context manager
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_site_components(
        self, snapshot_settings: SnapshotSettings
    ) -> tuple[list[ReplicationPath], list[ReplicationPath]]:
        """Split the snapshot components into generic and site specific components

        The generic components have the advantage that they only need to be created once for all
        sites and can be shared between the sites to optimize processing."""
        raise NotImplementedError()


class SnapshotCreationBase:
    def __init__(self, activation_work_dir: str) -> None:
        super().__init__()
        self._logger = logger.getChild("SnapshotCreationBase")
        self._multitar_workdir = os.path.join(activation_work_dir, "multitar_workdir")
        self._rsync_target_dir = os.path.join(self._multitar_workdir, "synced_files")
        self._tarfile_dir = os.path.join(self._multitar_workdir, "subtars")

        self._available_snapshots: dict[tuple[str, ...], str] = {}

        # Debugging stuff
        self._statistics_rsync: list[str] = []
        self._statistics_tar: dict[str, list[str]] = {}

    def output_statistics(self) -> None:
        self._logger.debug("============= Snapshot creation statistics =============")
        for line in self._statistics_rsync:
            self._logger.debug("RSYNC: %s" % line)

        for filepath, lines in self._statistics_tar.items():
            self._logger.debug("TAR: %s" % filepath)
            for line in lines:
                self._logger.debug("TAR:     - %s" % line)

    def _generate_snapshot(
        self,
        snapshot_work_dir: str,
        target_filepath: str,
        generic_components: list[ReplicationPath],
        custom_components: list[ReplicationPath],
        reuse_identical_snapshots: bool,
    ) -> None:
        generate_start_time = time.time()
        target_basename = os.path.basename(target_filepath)
        store.makedirs(os.path.dirname(target_filepath))

        # This is not supported in CME, most of the CME files are customized!
        # Only the sitespecific custom component is currently supported
        if reuse_identical_snapshots:
            # Note/Requirement: There is (currently) no need to rsync custom components, since these components are always
            #                   generated on the fly in a custom directory
            # Check if a snapshot with the same content has already been packed.
            snapshot_fingerprint = self._get_snapshot_fingerprint(
                snapshot_work_dir, generic_components, custom_components
            )
            identical_snapshot = self._available_snapshots.get(snapshot_fingerprint)
            if identical_snapshot:
                os.symlink(identical_snapshot, target_filepath)
                self._statistics_tar[os.path.basename(identical_snapshot)].append(
                    "Reused by %-40s (took %.4fsec)"
                    % (target_basename, time.time() - generate_start_time)
                )
                return

        # Generate the final tar command
        required_subtars = ["%s.tar" % c.ident for c in generic_components]
        final_tar_command = [
            "tar",
            "czf",
            target_filepath,
            "--owner=0",
            "--group=0",
            "-C",
            self._tarfile_dir,
        ] + required_subtars

        # Add custom files to final tar command
        if custom_components:
            base_dir = os.path.basename(target_filepath)
            tarfile_dir = f"{self._tarfile_dir}/custom_files/{base_dir}"
            os.makedirs(tarfile_dir)

            self._create_custom_components_tarfiles(
                snapshot_work_dir, custom_components, tarfile_dir
            )
            required_custom_subtars = ["%s.tar" % c.ident for c in custom_components]
            final_tar_command.extend(["-C", tarfile_dir] + required_custom_subtars)

        # Execute final tar command, create the snapshot
        self._execute_bash_commands([final_tar_command])

        if reuse_identical_snapshots:
            self._available_snapshots[snapshot_fingerprint] = target_filepath

        self._statistics_tar.setdefault(target_basename, []).append(
            "Snapshot creation took %.4fsec" % (time.time() - generate_start_time)
        )
        self._logger.debug(
            "Snapshot %-30s took %.4fsec" % (target_basename, (time.time() - generate_start_time))
        )

    def _get_rsync_and_tar_commands(
        self, component: ReplicationPath, rsync_target_dir: str, tarfile_target_dir: str
    ) -> list[Command]:
        bash_commands = []

        # Rsync from source
        bash_commands.append(self._get_rsync_command(component, rsync_target_dir))

        # Create subtar
        bash_commands.append(
            self._get_subtar_command(component, rsync_target_dir, tarfile_target_dir)
        )
        return bash_commands

    def _get_rsync_command(self, component: ReplicationPath, rsync_target_dir: str) -> Command:
        exclude_args = list(
            itertools.chain.from_iterable([("--exclude", f) for f in component.excludes])
        )

        source_path = os.path.join(cmk.utils.paths.omd_root, component.site_path)
        if component.ty == "dir":
            # Sync the content of the directory, but not the directory itself
            source_path += "/"

        return ["rsync", "-av", "--delete", source_path, rsync_target_dir] + exclude_args

    def _get_subtar_command(
        self, component: ReplicationPath, source_dir: str, tarfile_target_dir: str
    ) -> Command:
        if component.ty == "dir":
            files_location = [source_dir, "."]
        else:
            files_location = [source_dir, os.path.basename(component.site_path)]

        return [
            "tar",
            "cf",
            os.path.join(tarfile_target_dir, component.ident + ".tar"),
            "--force-local",
            "-C",
        ] + files_location

    def _execute_bash_commands(self, commands: list[Command], debug: bool = False) -> None:
        if not commands:
            return

        for command in commands:
            if debug:
                self._logger.debug(" ".join(command))
            try:
                completed_process = subprocess.run(
                    command,
                    stdin=subprocess.PIPE,
                    capture_output=True,
                    close_fds=True,
                    encoding="utf-8",
                    check=False,
                )

                if completed_process.returncode:
                    raise MKGeneralException(
                        _(
                            "Activate changes error. Unable to prepare site snapshots. Failed command: %r; StdOut: %r; StdErr: %s"
                        )
                        % (command, completed_process.stdout, completed_process.stderr)
                    )
            except OSError as e:
                raise MKGeneralException(
                    _(
                        "Activate changes error. Unable to prepare site snapshots. Failed command: %r, Exception: %s"
                    )
                    % (command, e)
                )

    def _create_custom_components_tarfiles(
        self, snapshot_work_dir: str, custom_components: list[ReplicationPath], tarfile_dir: str
    ) -> None:
        # Add any custom_components
        custom_components_commands = []
        for component in custom_components:
            source_path = os.path.join(snapshot_work_dir, component.site_path)

            if not os.path.exists(source_path):
                # Create an empty tarfile for this component
                with tarfile.open(os.path.join(tarfile_dir, "%s.tar" % component.ident), "w"):
                    pass
                continue

            base_dir = source_path if component.ty == "dir" else os.path.dirname(source_path)

            custom_components_commands.append(
                self._get_subtar_command(component, base_dir, tarfile_dir)
            )
        self._execute_bash_commands(custom_components_commands)

    def _get_snapshot_fingerprint(
        self,
        snapshot_work_dir: str,
        generic_components: list[ReplicationPath],
        custom_components: list[ReplicationPath],
    ) -> tuple[str, ...]:
        custom_components_md5sum = self._get_custom_components_md5sum(
            snapshot_work_dir, custom_components
        )
        return tuple(sorted(c.ident for c in generic_components) + [custom_components_md5sum])

    def _get_custom_components_md5sum(
        self, snapshot_work_dir: str, custom_components: list[ReplicationPath]
    ) -> str:
        if not custom_components:
            return ""

        # Note: currently there is only one custom component, the sitespecific.mk
        #       If there additional custom components in the future this call will fail
        #       This function raises an exception in case of an unknown component
        def is_supported(component: ReplicationPath) -> bool:
            return (
                component.ident == "sitespecific"
                and component.ty == "file"  #
                and component.site_path.endswith("sitespecific.mk")  #
            )

        for component in custom_components:
            if not is_supported(component):
                raise MKGeneralException(
                    _(
                        "Identical snapshot detection not supported. Cannot create md5sum. "
                        "Unsupported custom snapshot component: %s."
                    )
                    % str(component)
                )

        # Simply compute the checksum of the sitespecific.mk
        source_path = os.path.join(snapshot_work_dir, custom_components[0].site_path)
        return hashlib.md5(  # pylint: disable=unexpected-keyword-arg
            open(source_path, "rb").read(),
            usedforsecurity=False,
        ).hexdigest()


class SnapshotCreator(SnapshotCreationBase):
    """Packe the snapshots into snapshot archives"""

    def __init__(
        self, activation_work_dir: str, all_generic_components: list[ReplicationPath]
    ) -> None:
        super().__init__(activation_work_dir)
        self._setup_directories()
        self._generic_components = all_generic_components
        self._worker_subprocesses: list[multiprocessing.Process] = []

    def generate_snapshot(
        self,
        snapshot_work_dir: str,
        target_filepath: str,
        generic_components: list[ReplicationPath],
        custom_components: list[ReplicationPath],
        reuse_identical_snapshots: bool,
    ) -> None:
        self._generate_snapshot(
            snapshot_work_dir,
            target_filepath,
            generic_components,
            custom_components,
            reuse_identical_snapshots,
        )

    def generate_snapshot_in_subprocess(
        self,
        snapshot_work_dir: str,
        target_filepath: str,
        generic_components: list[ReplicationPath],
        custom_components: list[ReplicationPath],
        reuse_identical_snapshots: bool,
    ) -> None:
        def myworker() -> None:
            log = logger.getChild("SnapshotWorker(%d)" % os.getpid())
            try:
                self._generate_snapshot(
                    snapshot_work_dir,
                    target_filepath,
                    generic_components,
                    custom_components,
                    reuse_identical_snapshots,
                )
            except Exception:
                log.error("Error in subprocess")
                log.error(traceback.format_exc())

        worker = multiprocessing.Process(target=myworker)
        worker.daemon = True
        self._worker_subprocesses.append(worker)

    def _setup_directories(self) -> None:
        for path in [self._rsync_target_dir, self._tarfile_dir]:
            if not os.path.exists(path):
                os.makedirs(path)

    def __enter__(self) -> "SnapshotCreator":
        self._prepare_generic_tar_files()
        return self

    def __exit__(self, *exc_info: object) -> None:
        max_workers = 10
        try:
            max_workers = max(1, multiprocessing.cpu_count() - 1)
        except NotImplementedError:
            pass

        running_jobs: list[multiprocessing.Process] = []
        while self._worker_subprocesses or len(running_jobs) > 0:
            # Housekeeping, remove finished jobs
            for job in running_jobs[:]:
                if job.is_alive():
                    continue
                job.join()
                running_jobs.remove(job)

            time.sleep(0.05)

            # Continue if at max concurrent jobs
            if len(running_jobs) == max_workers:
                continue

            # Start new jobs
            while self._worker_subprocesses:
                job = self._worker_subprocesses.pop(0)
                job.start()
                running_jobs.append(job)
                if len(running_jobs) == max_workers:
                    break

        self.output_statistics()

    def _prepare_generic_tar_files(self) -> None:
        bash_commands: list[Command] = []
        prepare_start_time = time.time()
        for component in self._generic_components:
            rsync_target_dir = os.path.join(self._rsync_target_dir, component.ident)
            source_path = os.path.join(cmk.utils.paths.omd_root, component.site_path)

            os.makedirs(rsync_target_dir)

            if os.path.exists(source_path):
                bash_commands.extend(
                    self._get_rsync_and_tar_commands(component, rsync_target_dir, self._tarfile_dir)
                )
            else:
                # create an empty tarfile for this component
                with tarfile.open(os.path.join(self._tarfile_dir, "%s.tar" % component.ident), "w"):
                    pass

        self._execute_bash_commands(bash_commands)
        self._statistics_rsync.append(
            _("RSync of generic files took %.4fsec") % (time.time() - prepare_start_time)
        )


def is_user_file(filepath: str) -> bool:
    entry = os.path.basename(filepath)
    return entry.startswith("user_") or entry in ["tableoptions.mk", "treestates.mk", "sidebar.mk"]


def get_site_globals(site_id: SiteId, site_config: SiteConfiguration) -> SiteGlobals:
    site_globals = site_config.get("globals", {}).copy()
    site_globals.update(
        {
            "wato_enabled": not site_config.get("disable_wato", True),
            "userdb_automatic_sync": site_config.get(
                "user_sync", user_sync_default_config(site_id)
            ),
            "user_login": site_config.get("user_login", False),
        }
    )
    return site_globals


def create_distributed_wato_files(base_dir: Path, site_id: SiteId, is_remote: bool) -> None:
    _create_distributed_wato_file_for_base(base_dir, site_id, is_remote)
    _create_distributed_wato_file_for_dcd(base_dir, is_remote)
    _create_distributed_wato_file_for_omd(base_dir, is_remote)


def _create_distributed_wato_file_for_base(
    base_dir: Path, site_id: SiteId, is_remote: bool
) -> None:
    output = wato_fileheader()
    output += (
        "# This file has been created by the master site\n"
        "# push the configuration to us. It makes sure that\n"
        "# we only monitor hosts that are assigned to our site.\n\n"
    )
    output += "distributed_wato_site = '%s'\n" % site_id
    output += "is_wato_slave_site = %r\n" % is_remote

    store.save_text_to_file(base_dir.joinpath("etc/check_mk/conf.d/distributed_wato.mk"), output)


def _create_distributed_wato_file_for_dcd(base_dir: Path, is_remote: bool) -> None:
    if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CRE:
        return

    output = wato_fileheader()
    output += "dcd_is_wato_remote_site = %r\n" % is_remote

    store.save_text_to_file(base_dir.joinpath("etc/check_mk/dcd.d/wato/distributed.mk"), output)


def _create_distributed_wato_file_for_omd(base_dir: Path, is_remote: bool) -> None:
    output = wato_fileheader()
    output += f"is_wato_remote_site = {is_remote}\n"
    store.save_text_to_file(base_dir / "etc/omd/distributed.mk", output)


def create_rabbitmq_new_definitions_file(base_dir: Path, definition: rabbitmq.Definitions) -> None:
    store.save_text_to_file(base_dir / rabbitmq.NEW_DEFINITIONS_FILE_PATH, definition.dumps())
