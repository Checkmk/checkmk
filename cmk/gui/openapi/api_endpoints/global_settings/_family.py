#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

GLOBAL_SETTINGS_FAMILY = EndpointFamily(
    name="Global settings (internal)",
    description=(
        """
Global settings are the configuration variables shown on the "Global settings" page of
the user interface. Each variable is addressed by its internal name, e.g. `log_levels`.

Event Console settings - the variables of the "Event Console configuration" page, e.g.
`log_level` - are addressed through the same endpoints. They are ordinary entries of the
same configuration variable registry and are read and written by the same calls; only the
permission required to touch them differs, and that is derived from the variable itself.

Two scopes are available:

* the central value, which applies to every site that does not override it
* the site-specific value of a single site connection, which overrides the central value
  for that one site

A `DELETE` on either scope resets the setting: for the central scope back to the built-in
default, for a site connection by removing the site-specific override.
"""
    ),
    doc_group="Checkmk Internal",
)
