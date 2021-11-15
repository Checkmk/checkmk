#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This package allows checks to keep a memory until the next time
the check is being executed.

The most frequent use case is computation of rates from two succeeding counter values.

While a host is being checked this memory is kept in _global_state.

.. NOTE::

  The value stores file is kept in tmpfs and not reboot-persistent.
  Do not store long-time things here. Also do not store complex
  structures like log files or stuff.

This package exposes one function to the plugins (via the Check API), and
one function to the backend.

Check API
---------

.. autofunction:: get_value_store


.. autoclass:: cmk.base.api.agent_based.value_store._utils._ValueStore


Backend
-------

It is the backends responsibility to load the appropriate
host value store and enter the services context, before
the check function is called.


.. autofunction:: load_host_value_store


.. autoclass:: ValueStoreManager

"""

from ._global_state import get_value_store, load_host_value_store
from ._utils import ValueStoreManager

__all__ = [
    "get_value_store",
    "load_host_value_store",
    "ValueStoreManager",
]
