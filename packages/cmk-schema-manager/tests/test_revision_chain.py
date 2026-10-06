#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest

from cmk.schema_manager.errors import InvalidRevisionChainError
from cmk.schema_manager.revision import RevisionChain
from cmk.testlib.schema_manager import FakeRevision


def _revision(id_: str) -> FakeRevision[object]:
    return FakeRevision(id_)


def test_revision_chain_rejects_empty_sequence() -> None:
    with pytest.raises(InvalidRevisionChainError, match="must not be empty"):
        RevisionChain(revisions=())


def test_revision_chain_reports_only_duplicate_ids() -> None:
    with pytest.raises(
        InvalidRevisionChainError, match=re.escape("duplicate revision ids: ['0001']") + "$"
    ):
        RevisionChain(revisions=(_revision("0001"), _revision("0002"), _revision("0001")))


def test_revision_chain_preserves_declaration_order() -> None:
    first, second = _revision("0001"), _revision("0002")

    chain = RevisionChain(revisions=(first, second))

    assert list(chain) == [first, second]
