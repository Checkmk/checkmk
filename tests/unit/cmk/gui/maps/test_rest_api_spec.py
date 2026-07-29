#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Maps REST endpoints must produce a valid OpenAPI document.

The five ``map``-domain endpoints (:mod:`cmk.maps.rest_api`) register under
``APIVersion.UNSTABLE`` (first introduction), so they become part of the
``/check_mk/api/unstable`` OpenAPI document that the interactive REST-API docs
(ReDoc) load. A malformed endpoint model, a duplicate path or a colliding schema
name makes spec generation raise at build time -- which surfaces to the user as
``openapi-doc.yaml`` returning a 500 and takes down the interactive docs for the
*whole* REST-API, not just Maps.

Nothing else exercises the Maps endpoints' spec-ability, so pin it here by
running the real spec builder over API version UNSTABLE (the session-autouse
``load_plugins`` fixture has already registered the full edition, Maps included)
and asserting both that it does not raise and that the map domain is present.
"""

from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.spec.spec_generator.generate_api_spec import _make_spec, populate_spec


def test_maps_endpoints_build_a_valid_unstable_openapi_spec() -> None:
    spec = _make_spec(APIVersion.UNSTABLE)
    # Raises on a malformed model / duplicate path / colliding schema name -- the
    # exact failure that 500s openapi-doc.yaml at runtime.
    populate_spec(APIVersion.UNSTABLE, spec, "doc", set(), "checkmk")

    paths = spec.to_dict()["paths"]
    assert any("/map/" in path or path.endswith("/map") for path in paths), (
        f"the map domain is missing from the generated spec (paths: {sorted(paths)})"
    )
