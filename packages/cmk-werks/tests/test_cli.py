#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import datetime
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cmk.werks.cli import (
    _reserve_werk_ids,
    main_evaluate,
    main_rewrite_werk,
    main_user_understanding,
)
from cmk.werks.meisterwerk import build_meisterwerk_payload
from cmk.werks.parse import WerkV2ParseResult
from cmk.werks.schemas.werk import Werk as WerkTuple
from cmk.werks.schemas.werk import WerkId


def tw(data: Iterable[int]) -> list[WerkId]:
    """Convert integer iterable to list of WerkId objects."""
    return [WerkId(d) for d in data]


@pytest.mark.parametrize(
    ("first_free", "count_requested", "expected_new_first_free", "expected_ids_reserved"),
    [
        pytest.param(
            10,
            5,
            15,
            tw(range(10, 15)),
            id="request 5 ids, starting from 10",
        ),
        pytest.param(
            12,
            2,
            14,
            tw(range(12, 14)),
            id="request 2 ids, from the middle",
        ),
        pytest.param(
            32,
            2,
            34,
            tw(range(32, 34)),
            id="request 2 ids, from middle of second range",
        ),
        pytest.param(
            10,
            11,
            31,
            tw(chain(range(10, 20), [30])),
            id="request whole first range",
        ),
        pytest.param(
            10,
            25,
            55,
            tw(chain(range(10, 20), range(30, 40), range(50, 55))),
            id="ids from three ranges",
        ),
    ],
)
def test_reserve_werk_id(
    first_free: int,
    count_requested: int,
    expected_new_first_free: int,
    expected_ids_reserved: list[WerkId],
) -> None:
    """Test werk ID reservation functionality."""
    new_first_free, ids_reserved = _reserve_werk_ids(
        [(10, 20), (30, 40), (50, 60)], first_free, count_requested
    )

    assert len(ids_reserved) == count_requested
    assert expected_new_first_free == new_first_free
    assert expected_ids_reserved == ids_reserved


def test_reserve_werk_id_fails() -> None:
    """Test werk ID reservation failure scenarios."""
    with pytest.raises(RuntimeError, match="Configuration error"):
        # first_free does not match the range we should actually be in
        _reserve_werk_ids([(10, 20), (30, 40), (50, 60)], 25, 5)

    with pytest.raises(RuntimeError, match="Not enough ids available"):
        # too many ids requested
        _reserve_werk_ids([(10, 20), (30, 40), (50, 60)], 15, 200)


def test_build_werk_payload_basic() -> None:
    """Test basic werk payload building."""
    metadata = {
        "title": "Test Feature",
        "date": "2024-01-15T10:30:00Z",
        "level": "2",
        "version": "1.0.0",
        "class": "feature",
        "component": "core",
        "compatible": "yes",
    }
    content = WerkV2ParseResult(metadata=metadata, description="Test description")
    werk = WerkTuple(path=Path("/test/path"), id=WerkId(12345), content=content)

    result = build_meisterwerk_payload(werk)

    assert result.title == "Test Feature"
    assert result.date == datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.UTC)
    assert result.level == 2
    assert result.version == "1.0.0"
    assert result.werk_class == "feature"
    assert result.component == "core"
    assert result.compatible is True
    assert result.werk_text == "Test description"


def test_build_werk_payload_incompatible() -> None:
    """Test werk payload building with incompatible changes."""
    metadata = {
        "title": "Breaking Change",
        "date": "2024-06-01T00:00:00Z",
        "level": "1",
        "version": "2.0.0",
        "class": "breaking",
        "component": "api",
        "compatible": "no",
    }
    content = WerkV2ParseResult(metadata=metadata, description="Breaking change description")
    werk = WerkTuple(path=Path("/test/path"), id=WerkId(67890), content=content)

    result = build_meisterwerk_payload(werk)

    assert result.compatible is False
    assert result.werk_class == "breaking"


def test_build_werk_payload_comprehensive() -> None:
    """Test werk payload building with complex content."""
    metadata = {
        "title": "Complex Feature with Unicode: émojis 🚀",
        "date": "2024-12-01T15:45:30Z",
        "level": "3",
        "version": "2.4.0",
        "class": "security",
        "component": "authentication",
        "compatible": "yes",
    }
    description = "Multi-line description\nwith details\n\nand paragraphs"
    content = WerkV2ParseResult(metadata=metadata, description=description)
    werk = WerkTuple(path=Path("/complex/path"), id=WerkId(99999), content=content)

    result = build_meisterwerk_payload(werk)

    assert result.title == "Complex Feature with Unicode: émojis 🚀"
    assert result.werk_text == description
    assert result.version == "2.4.0"


def create_test_werk_file(werk_dir: Path, werk_id: int, title: str, content: str | None) -> Path:
    """Create a test werk file in the given directory."""
    werk_content = f"""[//]: # (werk v2)
# {title}

key | value
--- | ---
class | feature
component | core
date | 2022-01-01T00:00:00+00:00
level | 2
version | 2.0.0
compatible | yes
edition | cre

"""
    if content is None:
        werk_content += f"This is a test werk for {title}.\nIt contains sample content for testing the meisterwerk functionality."
    else:
        werk_content += content
    werk_path = werk_dir / f"{werk_id}.md"
    werk_path.write_text(werk_content)
    return werk_path


def test_main_evaluate_no_id_uses_last_werk() -> None:
    """Test evaluation without ID uses last werk."""
    args = argparse.Namespace(id=None)

    with patch("cmk.werks.cli.get_last_werk", return_value=WerkId(99999)):
        with patch("cmk.werks.cli.werk_path_by_id") as mock_werk_path_by_id:
            with patch("cmk.werks.cli.bail_out") as mock_bail_out:
                mock_path = MagicMock()
                mock_path.exists.return_value = False
                mock_werk_path_by_id.return_value = mock_path
                mock_bail_out.side_effect = SystemExit(1)
                with pytest.raises(SystemExit):
                    main_evaluate(args)
                mock_bail_out.assert_called_once_with("No Werk with this id.")


def test_main_evaluate_rejects_v1_werks() -> None:
    """Test that main_evaluate rejects v1 werks."""
    args = argparse.Namespace(id=12345)

    with patch("cmk.werks.cli.werk_path_by_id") as mock_werk_path_by_id:
        with patch("cmk.werks.cli.bail_out") as mock_bail_out:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.suffix = ""
            mock_werk_path_by_id.return_value = mock_path
            mock_bail_out.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                main_evaluate(args)
            mock_bail_out.assert_called_once_with(
                "Can only evaluate Werk markdown files (with .md suffix)."
            )


def test_main_rewrite_werk_rejects_v1_werks() -> None:
    """Test that main_rewrite_werk rejects v1 werks."""
    args = argparse.Namespace(id=12345, append=False)

    with patch("cmk.werks.cli.werk_path_by_id") as mock_werk_path_by_id:
        with patch("cmk.werks.cli.bail_out") as mock_bail_out:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.suffix = ""
            mock_werk_path_by_id.return_value = mock_path
            mock_bail_out.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                main_rewrite_werk(args)
            mock_bail_out.assert_called_once_with(
                "Can only evaluate Werk markdown files (with .md suffix)."
            )


@pytest.mark.vcr
def test_evaluate_werk_with_unicode_content(tmp_path: Path) -> None:
    """Test evaluation with unicode content using real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()

    unicode_title = "Unicode Test: émojis 🚀 and spëcial chars"
    unicode_content = "This Werk contains émojis 🚀, accented chars like café, and symbols like ©️™️."
    werk_path = create_test_werk_file(werk_dir, 77777, unicode_title, unicode_content)

    args = argparse.Namespace(id=77777)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        main_evaluate(args)
        # No assertions needed - if the API call succeeds, the test passes


@pytest.mark.vcr
def test_rewrite_werk_with_long_content(tmp_path: Path) -> None:
    """Test rewriting with very long content using real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()

    # Create long description
    long_description = (
        "This is a very long description that tests the API's ability to handle large amounts of text. "
        * 50
    )
    werk_path = create_test_werk_file(werk_dir, 88888, "Long Content Test", long_description)

    args = argparse.Namespace(id=88888, append=False)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        main_rewrite_werk(args)
        # No assertions needed - if the API calls succeed, the test passes


@pytest.mark.vcr
def test_user_understanding_minimal_description(tmp_path: Path) -> None:
    """Test user understanding with minimal content using real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()

    werk_content = """[//]: # (werk v2)
# Minimal Werk

key | value
--- | ---
class | fix
component | core
date | 2022-01-01T00:00:00+00:00
level | 1
version | 2.0.0
compatible | yes
edition | cre

Bug fix example.
"""
    werk_path = werk_dir / "99999.md"
    werk_path.write_text(werk_content)

    args = argparse.Namespace(id=99999)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        # This will make a real API call with minimal content
        main_user_understanding(args)
        # No assertions needed - if the API call succeeds, the test passes


@pytest.mark.vcr
def test_evaluate_werk_with_breaking_change(tmp_path: Path) -> None:
    """Test evaluation of breaking change Werk using real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()

    breaking_werk_content = """[//]: # (werk v2)
# Breaking Database Schema Change

key | value
--- | ---
class | breaking
component | database
date | 2024-01-01T00:00:00+00:00
level | 1
version | 3.0.0
compatible | no
edition | cre

We have changed the database schema for performance improvements.
This requires manual migration steps from administrators.
Please run the migration script before upgrading.

Migration steps:
1. Stop the service
2. Run migration-script.sql
3. Restart the service
"""
    werk_path = werk_dir / "55555.md"
    werk_path.write_text(breaking_werk_content)

    args = argparse.Namespace(id=55555)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        # This will make a real API call for a breaking change werk
        main_evaluate(args)
        # No assertions needed - if the API call succeeds, the test passes


@pytest.mark.vcr
def test_user_understanding_complex_feature(tmp_path: Path) -> None:
    """Test user understanding of complex feature using real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()

    complex_werk_content = """[//]: # (werk v2)
# Advanced Monitoring Dashboard with Real-time Analytics

key | value
--- | ---
class | feature
component | dashboard
date | 2024-01-01T00:00:00+00:00
level | 3
version | 2.5.0
compatible | yes
edition | cee

This werk introduces a comprehensive monitoring dashboard that provides real-time analytics
and advanced visualization capabilities for system administrators.

Key features include:
- Interactive charts and graphs
- Customizable dashboards
- Real-time data streaming
- Export functionality for reports
- Integration with external monitoring tools

The dashboard can be accessed through the main navigation menu under "Advanced Monitoring".
Configuration options are available in the administration panel.

Technical implementation details:
- Uses WebSocket connections for real-time updates
- Implements efficient data aggregation algorithms
- Supports multiple chart types and visualization options
- Provides REST API endpoints for integration
"""
    werk_path = werk_dir / "77777.md"
    werk_path.write_text(complex_werk_content)

    args = argparse.Namespace(id=77777)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        main_user_understanding(args)
        # No assertions needed - if the API call succeeds, the test passes


@pytest.mark.vcr
def test_main_user_understanding_success(tmp_path: Path) -> None:
    """Test successful user understanding generation with real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    werk_path = create_test_werk_file(werk_dir, 54321, "User Understanding Test", None)

    args = argparse.Namespace(id=54321)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        main_user_understanding(args)
        # No assertions needed - if the API call succeeds, the test passes


@pytest.mark.vcr
def test_main_rewrite_werk_append_mode(tmp_path: Path) -> None:
    """Test Werk rewriting in append mode with real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    werk_path = create_test_werk_file(werk_dir, 22222, "Append Test", None)
    original_content = werk_path.read_text()

    args = argparse.Namespace(id=22222, append=True)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        with patch("cmk.werks.cli.edit_werk"):  # Mock only the editor call
            with patch("cmk.werks.cli.save_last_werkid"):  # Mock only the file write
                main_rewrite_werk(args)
                updated_content = werk_path.read_text()
                assert len(updated_content) > len(original_content)
                assert "<<<<<--- Rewritten Werk --->>>>" in updated_content
                assert original_content in updated_content


@pytest.mark.vcr
def test_main_evaluate_success(tmp_path: Path) -> None:
    """Test successful Werk evaluation with real API call."""
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    werk_path = create_test_werk_file(werk_dir, 12345, "Test Werk for Evaluation", None)

    args = argparse.Namespace(id=12345)

    with patch("cmk.werks.cli.werk_path_by_id", return_value=werk_path):
        # This will make a real API call to the meisterwerk service
        main_evaluate(args)
        # No assertions needed - if the API call succeeds, the test passes
        # VCR will record the interaction for future test runs
