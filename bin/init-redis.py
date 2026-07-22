#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import getLogger

from cmk.gui.search import index as search_index


def main() -> None:
    logger = getLogger("init-redis")
    try:
        search_index.request_rebuild()
    except Exception:
        logger.exception("Failed to request building of Setup search index")


if __name__ == "__main__":
    main()
