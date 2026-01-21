#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import os
import subprocess
import sys
from collections.abc import Sequence
from enum import auto, Enum
from pathlib import Path
from uuid import uuid4

import omdlib
from omdlib.config_hooks import config_set_all, load_config, save_site_conf, update_cmk_core_config
from omdlib.contexts import SiteContext
from omdlib.instance_id import create_instance_id
from omdlib.scripts import call_scripts
from omdlib.site_paths import SitePaths
from omdlib.system_apache import register_with_system_apache
from omdlib.tmpfs import prepare_and_populate_tmpfs
from omdlib.type_defs import Config
from omdlib.users_and_groups import switch_to_site_user
from omdlib.version_info import VersionInfo

from cmk.ccc.site import SiteId
from cmk.utils.certs import (
    agent_root_ca_path,
    cert_dir,
    RelaysCA,
    RootCA,
    SiteCA,
)


def initialize_site_ca(
    site: SiteContext, site_key_size: int = 4096, root_key_size: int = 4096
) -> None:
    """Initialize the site local CA and create the default site certificate
    This will be used e.g. for serving SSL secured livestatus

    site_key_size specifies the length of the site certificate's private key. It should only be
    changed for testing purposes.
    """
    site_home = SitePaths.from_site_name(site.name).home
    site_id = SiteId(site.name)
    ca_path = cert_dir(Path(site_home))
    ca = SiteCA.load_or_create(site_id, ca_path, key_size=root_key_size)

    if not ca.site_certificate_exists(ca.cert_dir, site_id):
        # Additional subject alternative names can be configured in the UI later, but not on first
        # init for now.
        ca.create_site_certificate(site_id, additional_sans=[], key_size=site_key_size)


def initialize_agent_ca(site: SiteContext) -> None:
    """Initialize the agents CA folder alongside a default agent signing CA.
    The default CA shall be used for issuing certificates for requesting agent controllers.
    Additional CAs/root certs that may be placed at the agent CA folder shall be used as additional
    root certs for agent receiver certificate verification (either as client or server cert)
    """
    site_home = Path(SitePaths.from_site_name(site.name).home)
    RootCA.load_or_create(agent_root_ca_path(site_home), f"Site '{site.name}' agent signing CA")


def initialize_relay_ca(site: SiteContext) -> None:
    """Initialize the relay CA folder alongside a default relay signing CA."""
    site_home = Path(SitePaths.from_site_name(site.name).home)
    ca_path = cert_dir(Path(site_home))
    RelaysCA.load_or_create(ca_path, SiteId(site.name))


class CommandType(Enum):
    create = auto()
    move = auto()
    copy = auto()

    # reuse in options or not:
    restore_existing_site = auto()
    restore_as_new_site = auto()

    @property
    def short(self) -> str:
        if self is CommandType.create:
            return "create"

        if self is CommandType.move:
            return "mv"

        if self is CommandType.copy:
            return "cp"

        if self in [CommandType.restore_as_new_site, CommandType.restore_existing_site]:
            return "restore"

        raise TypeError()


class FinalizeOutcome(enum.Enum):
    OK = 0
    ABORTED = 1
    WARN = 2


def finalize_site_as_user(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    command_type: CommandType,
    verbose: bool,
    ignored_hooks: Sequence[str],
) -> FinalizeOutcome:
    # Mount and create contents of tmpfs. This must be done as normal
    # user. We also could do this at 'omd start', but this might confuse
    # users. They could create files below tmp which would be shadowed
    # by the mount.
    site_home = SitePaths.from_site_name(site.name).home
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    prepare_and_populate_tmpfs(
        config,
        version_info,
        site.name,
        site_home,
        site.tmp_dir,
        site.replacements(),
        site.skel_permissions,
        skelroot,
    )

    # Run all hooks in order to setup things according to the
    # configuration settings
    config_set_all(site, config, verbose, ignored_hooks)
    initialize_site_ca(site)
    initialize_agent_ca(site)
    initialize_relay_ca(site)
    save_site_conf(site_home, config)

    if command_type in [CommandType.create, CommandType.copy, CommandType.restore_as_new_site]:
        create_instance_id(site_home=Path(site_home), instance_id=uuid4())

    call_scripts(site.name, "post-" + command_type.short, open_pty=sys.stdout.isatty())
    update_cmk_core_config(site_home, config)
    if not _crontab_access():
        sys.stderr.write("Warning: site user cannot access crontab\n")
        return FinalizeOutcome.WARN
    return FinalizeOutcome.OK


def _crontab_access() -> bool:
    return (
        subprocess.run(
            ["crontab", "-e"],
            env={"VISUAL": "true", "EDITOR": "true"},
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


# Is being called at the end of create, cp and mv.
# What is "create", "mv" or "cp". It is used for
# running the appropriate hooks.
def finalize_site(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    command_type: CommandType,
    apache_reload: bool,
    verbose: bool,
) -> FinalizeOutcome:
    # Now we need to do a few things as site user. Note:
    # - We cannot use setuid() here, since we need to get back to root.
    # - We cannot use seteuid() here, since the id command call will then still
    #   report root and confuse some tools
    # - We cannot sue setresuid() here, since that is not supported an Python 2.4
    # So we need to fork() and use a real setuid() here and leave the main process
    # at being root.
    pid = os.fork()
    if pid == 0:
        try:
            # From now on we run as normal site user!
            switch_to_site_user(site.name)

            # avoid executing hook 'TMPFS' and cleaning an initialized tmp directory
            # see CMK-3067
            outcome = finalize_site_as_user(
                version_info, site, config, command_type, verbose, ignored_hooks=["TMPFS"]
            )
            sys.exit(outcome.value)
        except Exception as e:
            sys.stderr.write(f"Failed to finalize site: {e}\n")
            sys.exit(FinalizeOutcome.ABORTED.value)
    else:
        _wpid, status = os.waitpid(pid, 0)
        if (
            not os.WIFEXITED(status)
            or (outcome := FinalizeOutcome(os.WEXITSTATUS(status))) is FinalizeOutcome.ABORTED
        ):
            sys.exit("Error in non-priviledged sub-process.")

    # The config changes above, made with the site user, have to be also available for
    # the root user, so load the site config again. Otherwise e.g. changed
    # APACHE_TCP_PORT would not be recognized
    config = load_config(site, verbose)
    site_home = SitePaths.from_site_name(site.name).home
    register_with_system_apache(
        version_info,
        SitePaths.from_site_name(site.name).apache_conf,
        site.name,
        site_home,
        config["APACHE_TCP_ADDR"],
        config["APACHE_TCP_PORT"],
        apache_reload,
        verbose=verbose,
    )
    return outcome
