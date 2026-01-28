#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Gunicorn configuration for agent-receiver with log rotation."""

import os

# Get OMD_ROOT from environment
omd_root = os.environ.get("OMD_ROOT", "")
log_dir = os.path.join(omd_root, "var/log/agent-receiver")

# Ensure log directory exists
os.makedirs(log_dir, exist_ok=True)

# Access log configuration with rotation
accesslog = os.path.join(log_dir, "access.log")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Error log configuration with rotation
errorlog = os.path.join(log_dir, "error.log")
loglevel = "info"

# Log rotation settings
# Max 100MB per log file, keep 5 backup files
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
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "generic",
            "filename": errorlog,
            "maxBytes": 100 * 1024 * 1024,  # 100 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "access_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "access",
            "filename": accesslog,
            "maxBytes": 100 * 1024 * 1024,  # 100 MB
            "backupCount": 5,
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
