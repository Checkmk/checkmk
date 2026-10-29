#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The GUI↔daemon map signature contract, pinned end to end.

The GUI (:mod:`cmk.maps.gui._capabilities`) signs a resolved map config; the
daemon (:mod:`cmk.maps.backend.core.auth`) verifies it. The two live in
different components and cannot import each other, so the byte-for-byte format
lives in :mod:`cmk.maps.shared.map_signature`, which both import. This test signs
with the *real* GUI signer and verifies with the *real* daemon verifier, sharing
one secret, so any drift fails CI.
"""

from pathlib import Path

import pytest

from cmk.maps.backend.core import auth
from cmk.maps.gui import _capabilities
from cmk.utils import paths

_KEY = b"0123456789abcdef0123456789abcdef"

pytestmark = pytest.mark.usefixtures("shared_secret")


@pytest.fixture(name="shared_secret")
def fixture_shared_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point GUI and daemon at one secret file, as in production."""
    secret_file = tmp_path / "site_internal.secret"
    secret_file.write_bytes(_KEY)
    monkeypatch.setattr(paths, "site_internal_secret_file", secret_file)


def test_signed_map_config_round_trips_through_real_signer() -> None:
    config: dict[str, object] = {"name": "shared", "alias": "Shared", "objects": []}
    signed = _capabilities.sign_map_config(config, owner="alice")
    verified = auth.verify_map_config(signed["config_b64"], signed["sig"], owner="alice")
    assert verified == config


def test_tampered_signed_map_config_is_rejected() -> None:
    signed = _capabilities.sign_map_config({"name": "shared", "alias": "Shared"}, owner="alice")
    tampered = _capabilities.sign_map_config({"name": "evil", "alias": "Shared"}, owner="alice")
    with pytest.raises(auth.InvalidSignature):
        auth.verify_map_config(tampered["config_b64"], signed["sig"], owner="alice")


def test_signed_map_config_for_foreign_owner_is_rejected() -> None:
    # The owner is bound into the signature, so a config signed for one owner
    # does not verify under the owner the GUI named for another map.
    signed = _capabilities.sign_map_config({"name": "shared", "alias": "Shared"}, owner="alice")
    with pytest.raises(auth.InvalidSignature):
        auth.verify_map_config(signed["config_b64"], signed["sig"], owner="mallory")
