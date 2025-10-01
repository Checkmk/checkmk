#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_receiver.config import get_config
from cmk.agent_receiver.log import logger


class GetConfigSerialError(Exception):
    pass


def retrieve_config_serial() -> str:
    """
    Determine the current config serial by following the helper_config/latest symlink.

    Expected structure:
        $OMD_ROOT/var/check_mk/core/helper_config/
        <serial_id>/                # directories named by a serial
        latest -> <serial_id>/      # symlink pointing to the active serial directory

    The serial is taken from the basename of the resolved target of 'latest'.
    Errors (symlink missing/not a symlink, invalid target) raise GetConfigSerialError.
    """
    latest_link = get_config().helper_config_dir / "latest"

    if not latest_link.exists():
        logger.exception("Latest symlink %s does not exist", latest_link)
        raise GetConfigSerialError("latest symlink missing")

    if not latest_link.is_symlink():
        logger.exception("Path %s exists but is not a symlink", latest_link)
        raise GetConfigSerialError("latest is not a symlink")

    try:
        # Resolve the symlink; we only need the final directory name.
        target_path = latest_link.resolve(strict=True)
    except FileNotFoundError:
        logger.exception("Symlink %s points to a non-existent target", latest_link)
        raise GetConfigSerialError("latest symlink target missing")
    except OSError as e:
        logger.exception("Failed to resolve symlink %s: %s", latest_link, e)
        raise GetConfigSerialError("could not resolve latest symlink")

    serial = target_path.name
    return serial
