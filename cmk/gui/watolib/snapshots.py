#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Coordinates the collection and packing of snapshots"""

from __future__ import annotations

import logging
import multiprocessing.pool
import os
import shutil
import subprocess
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId

import cmk.utils.paths

from cmk.gui import hooks
from cmk.gui.log import logger
from cmk.gui.watolib.config_sync import (
    ABCSnapshotDataCollector,
    create_distributed_wato_files,
    create_rabbitmq_new_definitions_file,
    get_site_globals,
    replication_path_registry,
    ReplicationPath,
    ReplicationPathType,
    SnapshotSettings,
)
from cmk.gui.watolib.global_settings import save_site_global_settings

from cmk import trace

tracer = trace.get_tracer()


def make_cre_snapshot_manager(
    work_dir: str,
    site_snapshot_settings: dict[SiteId, SnapshotSettings],
) -> SnapshotManager:
    return SnapshotManager(
        work_dir,
        site_snapshot_settings,
        CRESnapshotDataCollector(site_snapshot_settings),
        reuse_identical_snapshots=True,
        generate_in_subprocess=False,
    )


class SnapshotManager:
    def __init__(
        self,
        activation_work_dir: str,
        site_snapshot_settings: dict[SiteId, SnapshotSettings],
        data_collector: ABCSnapshotDataCollector,
        reuse_identical_snapshots: bool,
        generate_in_subprocess: bool,
    ) -> None:
        super().__init__()
        self._activation_work_dir = activation_work_dir
        self._site_snapshot_settings = site_snapshot_settings
        self._data_collector = data_collector
        self._reuse_identical_snapshots = reuse_identical_snapshots
        self._generate_in_subproces = generate_in_subprocess

        # Stores site and folder specific information to speed-up the snapshot generation
        self._logger = logger.getChild(self.__class__.__name__)

    def generate_snapshots(self) -> None:
        if not self._site_snapshot_settings:
            return  # Nothing to do

        # 1. Collect files to "var/check_mk/site_configs" directory
        with tracer.span("prepare_snapshot_files"):
            self._data_collector.prepare_snapshot_files()

        # 2. Allow hooks to further modify the reference data for the remote site
        hooks.call("post-snapshot-creation", self._site_snapshot_settings)


def _clone_site_config_directory(
    site_logger: logging.Logger,
    site_id: str,
    snapshot_settings: SnapshotSettings,
    origin_site_work_dir: str,
) -> None:
    site_logger.debug("Processing site %s", site_id)

    if os.path.exists(snapshot_settings.work_dir):
        shutil.rmtree(snapshot_settings.work_dir)

    completed_process = subprocess.run(
        ["cp", "-al", origin_site_work_dir, snapshot_settings.work_dir],
        shell=False,
        close_fds=True,
        check=False,
    )

    assert completed_process.returncode == 0
    site_logger.debug("Finished site")


class CRESnapshotDataCollector(ABCSnapshotDataCollector):
    def prepare_snapshot_files(self) -> None:
        """Collect the files to be synchronized for all sites

        This is done by copying the things declared by the generic components together to a single
        site_config for one site. This will result in a directory containing only hard links to
        the original files.

        This directory is then cloned recursively for all sites, again with the result of having
        a single directory per site containing a lot of hard links to the original files.

        As last step the site individual files will be added.
        """
        # Choose one site to create the first site config for
        site_ids = list(self._site_snapshot_settings.keys())
        first_site = site_ids.pop(0)

        # Create first directory and clone it once for each destination site
        with tracer.span("prepare_first_site"):
            self._prepare_site_config_directory(first_site)
            self._clone_site_config_directories(first_site, site_ids)

        for site_id, snapshot_settings in sorted(
            self._site_snapshot_settings.items(), key=lambda x: x[0]
        ):
            with tracer.span(f"prepare_site_{site_id}"):
                save_site_global_settings(
                    get_site_globals(site_id, snapshot_settings.site_config),
                    custom_site_path=snapshot_settings.work_dir,
                )
                create_distributed_wato_files(
                    Path(snapshot_settings.work_dir), site_id, is_remote=True
                )
                create_rabbitmq_new_definitions_file(
                    Path(snapshot_settings.work_dir), snapshot_settings.rabbitmq_definition
                )

    def _prepare_site_config_directory(self, site_id: SiteId) -> None:
        """
        Gather files to be synchronized to remote sites from etc hierarchy

        - Iterate all files declared by snapshot components
        - Synchronize site hierarchy with site_config directory
          - Remove files that do not exist anymore
          - Add hard links
        """
        self._logger.debug("Processing first site %s", site_id)
        snapshot_settings = self._site_snapshot_settings[site_id]

        # Currently we don't have an incremental sync on disk. The performance of some mkdir/link
        # calls should be good enough
        if os.path.exists(snapshot_settings.work_dir):
            shutil.rmtree(snapshot_settings.work_dir)

        for component in self.get_generic_components():
            # Generic components (i.e. any component that does not have "ident"
            # = "sitespecific") are collected to be snapshotted. Site-specific
            # components as well as distributed wato components are done later on
            # in the process.

            # Note that at this stage, components that have been deselected
            # from site synchronisation by the user must not be pre-filtered,
            # otherwise these settings would cascade randomly from the first site
            # to the other sites.

            # These components are deselected in the snapshot settings of the
            # site, which is the basis of the actual synchronisation.

            # Examples of components that can be excluded:
            # - event console ("mkeventd", "mkeventd_mkp")
            # - MKPs ("local", "mkps")

            source_path = cmk.utils.paths.omd_root / component.site_path
            target_path = Path(snapshot_settings.work_dir).joinpath(component.site_path)

            target_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

            if not source_path.exists():
                # Not existing files things can simply be skipped, not existing files could also be
                # skipped, but we create them here to be 1:1 compatible with the pre 1.7 sync.
                if component.ty is ReplicationPathType.DIR:
                    target_path.mkdir(mode=0o770, exist_ok=True, parents=True)

                continue

            # Recursively hard link files (rsync --link-dest or cp -al)
            # With Python 3 we could use "shutil.copytree(src, dst, copy_function=os.link)", but
            # please have a look at the performance before switching over...
            # shutil.copytree(source_path, str(target_path.parent) + "/", copy_function=os.link)

            completed_process = subprocess.run(
                ["cp", "-al", str(source_path), str(target_path.parent) + "/"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                shell=False,
                close_fds=True,
                check=False,
            )
            if completed_process.returncode:
                self._logger.error(
                    "Failed to clone files from %s to %s: %s",
                    source_path,
                    str(target_path),
                    completed_process.stdout,
                )
                raise MKGeneralException("Failed to create site config directory")

        self._logger.debug("Finished site")

    def _clone_site_config_directories(
        self, origin_site_id: SiteId, site_ids: list[SiteId]
    ) -> None:
        clone_args = [
            (
                self._logger.getChild(f"site[{site_id}]"),
                site_id,
                self._site_snapshot_settings[site_id],
                self._site_snapshot_settings[origin_site_id].work_dir,
            )
            for site_id in site_ids
        ]

        num_threads = 5  # based on rudimentary tests, performance improvement drops off after
        with multiprocessing.pool.ThreadPool(processes=num_threads) as copy_pool:
            copy_pool.starmap(_clone_site_config_directory, clone_args)

    def get_generic_components(self) -> list[ReplicationPath]:
        return list(replication_path_registry.values())

    def get_site_components(
        self, snapshot_settings: SnapshotSettings
    ) -> tuple[list[ReplicationPath], list[ReplicationPath]]:
        generic_site_components = []
        custom_site_components = []

        for component in snapshot_settings.snapshot_components:
            if component.ident == "sitespecific":
                # Only the site specific global files are individually handled in the non CME snapshot
                custom_site_components.append(component)
            else:
                generic_site_components.append(component)

        return generic_site_components, custom_site_components
