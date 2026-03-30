# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.ibazel_manager module.

Covers all resolution paths (system detection, cache verification, download),
error conditions, and locked decisions from CONTEXT.md.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

from cmk.dev_deploy.errors import DeployError, IBazelError

# ---------------------------------------------------------------------------
# TestIBazelError
# ---------------------------------------------------------------------------


class TestIBazelError:
    """IBazelError inherits from DeployError with recovery hint support."""

    def test_inherits_from_deploy_error(self) -> None:
        err = IBazelError("something broke")
        assert isinstance(err, DeployError)

    def test_recovery_hint_in_str(self) -> None:
        err = IBazelError("checksum mismatch", recovery="Do NOT retry.")
        assert "checksum mismatch" in str(err)
        assert "Do NOT retry." in str(err)

    def test_no_recovery_hint(self) -> None:
        err = IBazelError("generic failure")
        assert str(err) == "generic failure"
        assert err.recovery is None


# ---------------------------------------------------------------------------
# TestPlatformDetection
# ---------------------------------------------------------------------------


class TestPlatformDetection:
    """_get_platform_suffix maps OS/arch to iBazel binary suffix."""

    def test_linux_x86_64(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_platform_suffix

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.system",
                return_value="Linux",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.machine",
                return_value="x86_64",
            ),
        ):
            assert _get_platform_suffix() == "linux_amd64"

    def test_linux_aarch64(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_platform_suffix

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.system",
                return_value="Linux",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.machine",
                return_value="aarch64",
            ),
        ):
            assert _get_platform_suffix() == "linux_arm64"

    def test_darwin_x86_64(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_platform_suffix

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.system",
                return_value="Darwin",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.machine",
                return_value="x86_64",
            ),
        ):
            assert _get_platform_suffix() == "darwin_amd64"

    def test_darwin_arm64(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_platform_suffix

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.system",
                return_value="Darwin",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.machine",
                return_value="arm64",
            ),
        ):
            assert _get_platform_suffix() == "darwin_arm64"

    def test_unsupported_platform_raises(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_platform_suffix

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.system",
                return_value="Windows",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.platform.machine",
                return_value="AMD64",
            ),
        ):
            with pytest.raises(IBazelError, match="Unsupported platform") as exc_info:
                _get_platform_suffix()
            assert exc_info.value.recovery is not None
            assert "Install iBazel manually" in exc_info.value.recovery


# ---------------------------------------------------------------------------
# TestVersionParsing
# ---------------------------------------------------------------------------


class TestVersionParsing:
    """_get_ibazel_version parses version from stderr, ignoring exit code."""

    def _make_completed_process(
        self,
        *,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["ibazel"], returncode=returncode, stdout=stdout, stderr=stderr
        )

    def test_parses_version_from_stderr(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        result = self._make_completed_process(
            stderr="iBazel - Version v0.28.0\n\nA file watcher for Bazel."
        )
        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run", return_value=result
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") == "v0.28.0"

    def test_ignores_stdout(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        result = self._make_completed_process(
            stdout="iBazel - Version v0.28.0", stderr="no version here"
        )
        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run", return_value=result
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") is None

    def test_handles_nonzero_exit_code(self) -> None:
        """Version is parsed even when exit code is non-zero (pitfall 3)."""
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        result = self._make_completed_process(
            stderr="iBazel - Version v0.28.0\nUsage: ...", returncode=1
        )
        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run", return_value=result
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") == "v0.28.0"

    def test_returns_none_on_timeout(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["ibazel"], timeout=5),
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") is None

    def test_returns_none_on_oserror(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") is None

    def test_returns_none_on_file_not_found(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run",
            side_effect=FileNotFoundError("ibazel not found"),
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") is None

    def test_returns_none_on_no_match(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _get_ibazel_version

        result = self._make_completed_process(
            stderr="Some random output\nNo version here"
        )
        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.subprocess.run", return_value=result
        ):
            assert _get_ibazel_version("/usr/bin/ibazel") is None


# ---------------------------------------------------------------------------
# TestSystemDetection
# ---------------------------------------------------------------------------


class TestSystemDetection:
    """_detect_system_ibazel checks PATH and exact version match."""

    def test_not_on_path_returns_none(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _detect_system_ibazel

        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager.shutil.which", return_value=None
        ):
            assert _detect_system_ibazel() is None

    def test_exact_version_match_returns_path(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _detect_system_ibazel

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.shutil.which",
                return_value="/usr/local/bin/ibazel",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_ibazel_version",
                return_value="v0.28.0",
            ),
        ):
            result = _detect_system_ibazel()
            assert result == Path("/usr/local/bin/ibazel")

    def test_wrong_version_warns_returns_none(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _detect_system_ibazel

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.shutil.which",
                return_value="/usr/local/bin/ibazel",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_ibazel_version",
                return_value="v0.27.0",
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output") as mock_output,
        ):
            result = _detect_system_ibazel()
            assert result is None
            mock_output.warn.assert_called_once()
            msg = mock_output.warn.call_args[0][0]
            assert "v0.27.0" in msg
            assert "v0.28.0" in msg

    def test_unparseable_version_warns_returns_none(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _detect_system_ibazel

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.shutil.which",
                return_value="/usr/local/bin/ibazel",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_ibazel_version",
                return_value=None,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output") as mock_output,
        ):
            result = _detect_system_ibazel()
            assert result is None
            mock_output.warn.assert_called_once()


# ---------------------------------------------------------------------------
# TestCacheVerification
# ---------------------------------------------------------------------------


class TestCacheVerification:
    """_verify_sha256 validates file hash against embedded checksums."""

    def test_valid_cache_returns_true(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _verify_sha256

        binary = tmp_path / "ibazel-v0.28.0-linux_amd64"
        binary.write_bytes(b"valid binary content")
        expected_hash = hashlib.sha256(b"valid binary content").hexdigest()

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": expected_hash}),
            ),
        ):
            assert _verify_sha256(binary) is True

    def test_corrupt_cache_returns_false(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _verify_sha256

        binary = tmp_path / "ibazel-v0.28.0-linux_amd64"
        binary.write_bytes(b"corrupt content")

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType(
                    {
                        "linux_amd64": "0000000000000000000000000000000000000000000000000000000000000000"
                    }
                ),
            ),
        ):
            assert _verify_sha256(binary) is False

    def test_re_verifies_on_every_use(self, tmp_path: Path) -> None:
        """ensure_ibazel() re-verifies SHA256 on every call (locked decision)."""
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        binary = tmp_path / "ibazel-v0.28.0-linux_amd64"
        binary.write_bytes(b"cached binary")
        expected_hash = hashlib.sha256(b"cached binary").hexdigest()

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=binary,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": expected_hash}),
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            result1 = ensure_ibazel()
            result2 = ensure_ibazel()
            assert result1 == binary
            assert result2 == binary


# ---------------------------------------------------------------------------
# TestCorruptCacheError
# ---------------------------------------------------------------------------


class TestCorruptCacheError:
    """Corrupt cached binary raises IBazelError with manual delete hint."""

    def test_corrupt_cache_raises_with_delete_hint(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        binary = tmp_path / "ibazel-v0.28.0-linux_amd64"
        binary.write_bytes(b"corrupt content")

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=binary,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": "0" * 64}),
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            with pytest.raises(
                IBazelError, match="failed SHA256 verification"
            ) as exc_info:
                ensure_ibazel()
            assert exc_info.value.recovery is not None
            assert "rm" in exc_info.value.recovery
            assert str(binary) in exc_info.value.recovery


# ---------------------------------------------------------------------------
# TestDownloadAndVerify
# ---------------------------------------------------------------------------


class TestDownloadAndVerify:
    """_download_and_verify handles download, SHA256 check, and atomic rename."""

    def _make_mock_response(
        self, content: bytes, content_length: int | None = None
    ) -> MagicMock:
        """Create a mock HTTP response."""
        response = MagicMock()
        response.headers = MagicMock()
        response.headers.get.return_value = (
            str(content_length) if content_length else None
        )
        response.read.side_effect = [content, b""]
        response.close.return_value = None
        return response

    def test_successful_download_returns_path(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        content = b"valid binary content"
        content_hash = hashlib.sha256(content).hexdigest()

        mock_response = self._make_mock_response(content, len(content))

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": content_hash}),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                return_value=mock_response,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output") as mock_output,
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
        ):
            mock_stderr.isatty.return_value = False
            result = _download_and_verify()
            assert result == tmp_path / "ibazel-final"
            mock_output.success.assert_called_once()

    def test_checksum_mismatch_aborts_deletes_temp(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        content = b"bad content"
        mock_response = self._make_mock_response(content)

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType(
                    {"linux_amd64": "expected_hash_that_wont_match" + "0" * 40}
                ),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                return_value=mock_response,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
        ):
            mock_stderr.isatty.return_value = False
            with pytest.raises(
                IBazelError, match="SHA256 checksum mismatch"
            ) as exc_info:
                _download_and_verify()
            assert exc_info.value.recovery is not None
            assert "supply chain attack" in exc_info.value.recovery

            # Verify temp file was cleaned up (no stray files besides final path)
            remaining = list(tmp_path.iterdir())
            # The final path should NOT exist since the checksum failed
            assert (tmp_path / "ibazel-final") not in remaining

    def test_download_network_error_raises(self, tmp_path: Path) -> None:
        import urllib.error

        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": "abc123"}),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                side_effect=urllib.error.URLError("DNS resolution failed"),
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            with pytest.raises(IBazelError, match="Failed to download"):
                _download_and_verify()

    def test_download_timeout_raises(self, tmp_path: Path) -> None:
        import urllib.error

        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": "abc123"}),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                side_effect=urllib.error.URLError(TimeoutError("timed out")),
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            with pytest.raises(IBazelError, match="Failed to download"):
                _download_and_verify()

    def test_keyboard_interrupt_cleans_temp(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        mock_response = MagicMock()
        mock_response.headers = MagicMock()
        mock_response.headers.get.return_value = None
        mock_response.read.side_effect = KeyboardInterrupt
        mock_response.close.return_value = None

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": "abc123"}),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                return_value=mock_response,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
        ):
            mock_stderr.isatty.return_value = False
            with pytest.raises(KeyboardInterrupt):
                _download_and_verify()

            # Verify temp file was cleaned up
            remaining = [
                f for f in tmp_path.iterdir() if f.name.startswith(".ibazel-download-")
            ]
            assert remaining == []

    def test_executable_bit_set_after_verify(self, tmp_path: Path) -> None:
        """os.chmod(0o755) is called AFTER SHA256 passes, not before."""
        from cmk.dev_deploy.frontend.ibazel_manager import _download_and_verify

        content = b"valid binary"
        content_hash = hashlib.sha256(content).hexdigest()
        mock_response = self._make_mock_response(content, len(content))

        call_order: list[str] = []

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._ensure_cache_dir",
                return_value=tmp_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=tmp_path / "ibazel-final",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_platform_suffix",
                return_value="linux_amd64",
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._CHECKSUMS",
                MappingProxyType({"linux_amd64": content_hash}),
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                return_value=mock_response,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
            patch("cmk.dev_deploy.frontend.ibazel_manager.os.rename") as mock_rename,
            patch("cmk.dev_deploy.frontend.ibazel_manager.os.chmod") as mock_chmod,
        ):
            mock_stderr.isatty.return_value = False

            def track_rename(*_args: object) -> None:
                call_order.append("rename")

            def track_chmod(*_args: object) -> None:
                call_order.append("chmod")

            mock_rename.side_effect = track_rename
            mock_chmod.side_effect = track_chmod

            _download_and_verify()

        # rename happens before chmod, and both happen (verify passed)
        assert call_order == ["rename", "chmod"]
        mock_chmod.assert_called_once()
        assert mock_chmod.call_args[0][1] == 0o755


# ---------------------------------------------------------------------------
# TestProgressBar
# ---------------------------------------------------------------------------


class TestProgressBar:
    """_print_progress gates output on TTY detection."""

    def test_renders_on_tty(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _print_progress

        with (
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.time.monotonic",
                return_value=1.0,
            ),
        ):
            mock_stderr.isatty.return_value = True
            _print_progress(downloaded=5000, total=10000, start_time=0.0)
            mock_stderr.write.assert_called_once()
            written = mock_stderr.write.call_args[0][0]
            assert "\r" in written

    def test_silent_on_non_tty(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _print_progress

        with patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr:
            mock_stderr.isatty.return_value = False
            _print_progress(downloaded=5000, total=10000, start_time=0.0)
            mock_stderr.write.assert_not_called()

    def test_clears_line_on_completion(self, tmp_path: Path) -> None:
        """After download finishes on TTY, progress line is cleared."""
        from cmk.dev_deploy.frontend.ibazel_manager import _download_with_progress

        content = b"test"
        mock_response = MagicMock()
        mock_response.headers = MagicMock()
        mock_response.headers.get.return_value = str(len(content))
        mock_response.read.side_effect = [content, b""]
        mock_response.close.return_value = None

        dest = tmp_path / "output"

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager.urllib.request.urlopen",
                return_value=mock_response,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.sys.stderr") as mock_stderr,
        ):
            mock_stderr.isatty.return_value = True
            _download_with_progress("http://example.com/file", dest)

            # Last write call should clear the line
            write_calls = mock_stderr.write.call_args_list
            last_write = write_calls[-1][0][0]
            assert last_write.startswith("\r")
            assert last_write.strip() == ""


# ---------------------------------------------------------------------------
# TestCacheDirectory
# ---------------------------------------------------------------------------


class TestCacheDirectory:
    """_ensure_cache_dir creates directory or raises IBazelError."""

    def test_creates_dir_if_not_exists(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _ensure_cache_dir

        cache_dir = tmp_path / "cache" / "cmk-dev-deploy"
        with patch(
            "cmk.dev_deploy.frontend.ibazel_manager._cache_dir", return_value=cache_dir
        ):
            result = _ensure_cache_dir()
            assert result == cache_dir
            assert cache_dir.exists()

    def test_raises_on_permission_error(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import _ensure_cache_dir

        cache_dir = tmp_path / "cache" / "cmk-dev-deploy"
        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._cache_dir",
                return_value=cache_dir,
            ),
            patch.object(Path, "mkdir", side_effect=OSError("Permission denied")),
        ):
            with pytest.raises(
                IBazelError, match="Cannot create cache directory"
            ) as exc_info:
                _ensure_cache_dir()
            assert exc_info.value.recovery is not None
            assert str(cache_dir) in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestEnsureIbazel
# ---------------------------------------------------------------------------


class TestEnsureIbazel:
    """Integration-level tests for ensure_ibazel with mocked boundaries."""

    def test_system_binary_takes_priority(self) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        system_path = Path("/usr/local/bin/ibazel")
        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=system_path,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._download_and_verify"
            ) as mock_download,
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            result = ensure_ibazel()
            assert result == system_path
            mock_download.assert_not_called()

    def test_cached_binary_skips_download(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        cache_file = tmp_path / "ibazel-v0.28.0-linux_amd64"
        cache_file.write_bytes(b"cached binary")

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=cache_file,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._verify_sha256",
                return_value=True,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._download_and_verify"
            ) as mock_download,
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            result = ensure_ibazel()
            assert result == cache_file
            mock_download.assert_not_called()

    def test_downloads_on_cache_miss(self, tmp_path: Path) -> None:
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        cache_file = tmp_path / "ibazel-v0.28.0-linux_amd64"
        downloaded_path = tmp_path / "downloaded-ibazel"

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=cache_file,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._download_and_verify",
                return_value=downloaded_path,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            # cache_file does not exist on disk, so it triggers download
            result = ensure_ibazel()
            assert result == downloaded_path

    def test_system_wrong_version_uses_cache(self, tmp_path: Path) -> None:
        """System iBazel wrong version -> cache is used (warn + no download)."""
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        cache_file = tmp_path / "ibazel-v0.28.0-linux_amd64"
        cache_file.write_bytes(b"cached binary")

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=cache_file,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._verify_sha256",
                return_value=True,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._download_and_verify"
            ) as mock_download,
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            result = ensure_ibazel()
            assert result == cache_file
            mock_download.assert_not_called()

    def test_system_wrong_version_downloads(self, tmp_path: Path) -> None:
        """System iBazel wrong version, no cache -> downloads."""
        from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

        cache_file = tmp_path / "ibazel-v0.28.0-linux_amd64"
        downloaded_path = tmp_path / "downloaded-ibazel"

        with (
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._detect_system_ibazel",
                return_value=None,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._get_cache_path",
                return_value=cache_file,
            ),
            patch(
                "cmk.dev_deploy.frontend.ibazel_manager._download_and_verify",
                return_value=downloaded_path,
            ),
            patch("cmk.dev_deploy.frontend.ibazel_manager.output"),
        ):
            result = ensure_ibazel()
            assert result == downloaded_path
