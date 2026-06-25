#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Gunicorn configuration for the Maps backend.

Log rotation is owned entirely by OMD's logrotate (etc/logrotate.d/maps), whose
postrotate runs `init.d/maps logrotate` → SIGUSR1. gunicorn reopens every
logging.FileHandler on SIGUSR1, so plain FileHandlers pick up the fresh files
after logrotate has renamed them. We deliberately do NOT use RotatingFileHandler:
its in-process size-based rotation would race with logrotate over the same
`.log.1` names and rotate on its own schedule (see werk 19064).
"""

import os
from pathlib import Path

omd_root = Path(os.environ.get("OMD_ROOT", ""))
log_dir = omd_root / "var/log/maps"
log_dir.mkdir(parents=True, exist_ok=True)

# Bind to a Unix socket under tmp/run: the site Apache reverse-proxies
# /<site>/check_mk/maps/api to it (no TCP port to template), and requests are
# authenticated by the Maps ticket.
bind = f"unix:{omd_root}/tmp/run/maps.sock"

# uvicorn ASGI worker: the app is async (SSE, httpx). gunicorn owns the process
# lifecycle (master/worker supervision, graceful reload, pidfile, SIGUSR1 log
# reopen); the uvicorn worker runs the actual ASGI server.
worker_class = "uvicorn_worker.UvicornWorker"

# Graceful worker-shutdown window on SIGTERM before the master force-kills them.
# cmk-maps-server waits slightly longer than this before escalating to SIGKILL.
graceful_timeout = 30

# Restrict the bound Unix socket (tmp/run/maps.sock) to the site user + group.
# gunicorn binds the socket under this umask (see gunicorn.sock.UnixSocket.bind);
# its default of 0 would create a world-writable (0777) socket, which the OMD
# file-permission audit rejects. 0o117 yields 0660 — the site's own Apache (same
# user) reaches it, nothing world-writable is exposed.
umask = 0o117

# Single worker by design: the daemon keeps per-process in-memory state that is
# NOT shared across workers — SSE subscribers + broadcast tasks (core/sse.py,
# api/v1/states.py), delta/dead-site snapshots, the BI compile cache
# (integrations/checkmk.py) and the per-connection Livestatus caches. With >1
# worker these fragment per process and maps break (duplicate broadcasts,
# missing deltas). Do not raise without making that state shared.
workers = 1

# gunicorn reads these module globals as its own settings. accesslog/errorlog
# double as the single source for the file paths: they are reused as the
# logconfig_dict handler filenames below, so the destination is defined once.
accesslog = str(log_dir / "access.log")
errorlog = str(log_dir / "error.log")
# Consumed by gunicorn's access logger to build each line (independent of the
# handler): log the method + path only, NOT "%(r)s" (the full request line).
# SSE and <img> requests carry the signed Maps ticket in ?token=, and the access
# log is long-lived + part of `omd backup` — a logged token would be replayable
# for its TTL. %(U)s is the path without the query string.
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(m)s %(U)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Disable control socket — not needed and it interferes with omd backup.
control_socket_disable = True

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s - %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
    },
    "handlers": {
        "error_file": {
            "class": "logging.FileHandler",
            "formatter": "generic",
            "filename": errorlog,
            "encoding": "utf-8",
        },
        "access_file": {
            "class": "logging.FileHandler",
            "formatter": "access",
            "filename": accesslog,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "gunicorn.error": {
            "level": "ERROR",
            "handlers": ["error_file"],
            "propagate": False,
            "qualname": "gunicorn.error",
        },
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["access_file"],
            "propagate": False,
            "qualname": "gunicorn.access",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["error_file"],
    },
}
