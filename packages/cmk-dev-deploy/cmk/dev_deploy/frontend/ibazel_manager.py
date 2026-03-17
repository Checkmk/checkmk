# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""iBazel binary management: auto-download, verify, and cache.

Provides :func:`ensure_ibazel` which returns a :class:`~pathlib.Path` to a
verified iBazel v0.28.0 binary.  Resolution order:

1. **System iBazel** -- if ``ibazel`` is on PATH with exact version match,
   use it directly (no download).
2. **Cached binary** -- if ``~/.cache/cmk-dev-deploy/ibazel-v0.28.0-<platform>``
   exists and passes SHA256 re-verification, use it.
3. **Download** -- fetch from GitHub releases, verify SHA256, atomic-rename
   into cache, return path.

Key design decisions (from CONTEXT.md):
- Hardcoded GitHub releases URL (no configurable mirrors)
- SHA256 re-verified on every use (catches silent corruption)
- Corrupt cache = error with manual delete instructions (no self-healing)
- Download to temp file + atomic rename (no partial binary on interrupt)
- Progress bar with ETA on TTY, silent on non-TTY
- 60s download timeout, fail fast, no retry
"""

from __future__ import annotations

import hashlib
import http.client
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import MappingProxyType

from cmk.dev_deploy.core import output
from cmk.dev_deploy.errors import IBazelError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IBAZEL_VERSION = "v0.28.0"

_GITHUB_RELEASES_URL = (
    "https://github.com/bazelbuild/bazel-watcher/releases/download/v0.28.0"
)


def _cache_dir() -> Path:
    return Path.home() / ".cache" / "cmk-dev-deploy"


_PLATFORM_MAP: MappingProxyType[tuple[str, str], str] = MappingProxyType(
    {
        ("Linux", "x86_64"): "linux_amd64",
        ("Linux", "aarch64"): "linux_arm64",
        ("Darwin", "x86_64"): "darwin_amd64",
        ("Darwin", "arm64"): "darwin_arm64",
    }
)

_CHECKSUMS: MappingProxyType[str, str] = MappingProxyType(
    {
        "linux_amd64": "17d412c34afeba69f9d05b6d1ea44848ffd4fdc18ebcd1f524b3699d1de0630e",
        "linux_arm64": "85ef4c7a9a1429e1b3d17ba4f6702e61acb24e5510d006e1fd99d0de4bcd07c0",
        "darwin_amd64": "a08602d4c0ac1419ceb42fbda40d5ad4d0ba76c1fe07497491b807a1bbf93af0",
        "darwin_arm64": "5dddbfe170ab2063d1517fea526b27731893ed561c78776c9bea20b4caafa11e",
    }
)

_VERSION_PATTERN = re.compile(r"iBazel - Version (v[\d.]+(?:-\w+)?)")

_DOWNLOAD_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


def _get_platform_suffix() -> str:
    """Return the iBazel binary suffix for the current platform.

    Raises:
        IBazelError: If the current OS/architecture combination is not
            supported by the iBazel release binaries.
    """
    key = (platform.system(), platform.machine())
    suffix = _PLATFORM_MAP.get(key)
    if suffix is None:
        raise IBazelError(
            f"Unsupported platform: {key[0]} {key[1]}",
            recovery="Install iBazel manually and add to PATH",
        )
    return suffix


# ---------------------------------------------------------------------------
# System iBazel detection
# ---------------------------------------------------------------------------


def _get_ibazel_version(binary_path: str) -> str | None:
    """Parse iBazel version from usage output (stderr).

    iBazel prints usage to stderr when invoked with no valid command.
    The first line contains: ``iBazel - Version v0.28.0``.

    Returns:
        The version string (e.g. ``"v0.28.0"``) or ``None`` if parsing fails.
    """
    try:
        result = subprocess.run(
            [binary_path],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        # Do NOT check returncode -- iBazel may exit non-zero when printing usage
        match = _VERSION_PATTERN.search(result.stderr)
        if match:
            return match.group(1)
    except (subprocess.TimeoutExpired, OSError, FileNotFoundError):
        pass
    return None


def _detect_system_ibazel() -> Path | None:
    """Check for a system iBazel on PATH with exact version match.

    Returns:
        Path to the system binary if found with correct version, else ``None``.
    """
    binary_path = shutil.which("ibazel")
    if binary_path is None:
        return None

    detected_version = _get_ibazel_version(binary_path)
    if detected_version is None:
        output.warn("Could not detect system iBazel version. Using managed version.")
        return None

    if detected_version == _IBAZEL_VERSION:
        return Path(binary_path)

    output.warn(
        f"System iBazel is {detected_version}, need {_IBAZEL_VERSION}. Using managed version."
    )
    return None


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def _get_cache_path() -> Path:
    """Return the expected cache path for the current platform."""
    return _cache_dir() / f"ibazel-{_IBAZEL_VERSION}-{_get_platform_suffix()}"


def _ensure_cache_dir() -> Path:
    """Create the cache directory if it does not exist.

    Raises:
        IBazelError: If the directory cannot be created.
    """
    try:
        _cache_dir().mkdir(parents=True, exist_ok=True)
        return _cache_dir()
    except OSError as exc:
        raise IBazelError(
            f"Cannot create cache directory: {_cache_dir()}\n  OS error: {exc}",
            recovery=(
                f"Check permissions on {_cache_dir().parent} "
                f"or create manually: mkdir -p {_cache_dir()}"
            ),
        ) from exc


# ---------------------------------------------------------------------------
# SHA256 verification
# ---------------------------------------------------------------------------


def _verify_sha256(path: Path) -> bool:
    """Verify that *path* matches the expected SHA256 checksum.

    Reads the file in 8192-byte chunks to avoid loading the entire binary
    into memory.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest() == _CHECKSUMS[_get_platform_suffix()]


# ---------------------------------------------------------------------------
# Download with progress
# ---------------------------------------------------------------------------


def _print_progress(downloaded: int, total: int | None, start_time: float) -> None:
    """Print a curl/wget-style progress bar to stderr.

    All output is gated on ``sys.stderr.isatty()`` to avoid garbled output
    when piped or in CI.
    """
    if not sys.stderr.isatty():
        return

    elapsed = time.monotonic() - start_time
    speed = downloaded / elapsed if elapsed > 0 else 0

    if total and total > 0:
        pct = downloaded * 100 // total
        bar_len = 30
        filled = bar_len * downloaded // total
        bar = "#" * filled + "-" * (bar_len - filled)
        eta = (total - downloaded) / speed if speed > 0 else 0
        sys.stderr.write(
            f"\r  [{bar}] {pct}%  {downloaded // 1024}K/{total // 1024}K  "
            f"{speed / 1024:.0f}K/s  ETA {eta:.0f}s"
        )
    else:
        sys.stderr.write(f"\r  {downloaded // 1024}K  {speed / 1024:.0f}K/s")
    sys.stderr.flush()


def _safe_read(response: http.client.HTTPResponse, size: int) -> bytes:
    """Read *size* bytes from *response*, wrapping timeout/OS errors.

    Raises:
        IBazelError: On read timeout or I/O error.
    """
    try:
        return response.read(size)
    except (TimeoutError, OSError) as exc:
        raise IBazelError(
            f"Download interrupted: {exc}",
            recovery="Check your internet connection and try again.",
        ) from exc


def _download_with_progress(url: str, dest: Path) -> str:
    """Download *url* to *dest*, streaming with progress, return SHA256 hex digest.

    Raises:
        IBazelError: On network errors, timeouts, or other download failures.
    """
    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT)  # nosec B310
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise IBazelError(
            f"Failed to download iBazel from {url}\n  Error: {exc}",
            recovery="Check your internet connection and try again.",
        ) from exc

    try:
        content_length = response.headers.get("Content-Length")
        total = int(content_length) if content_length else None
        downloaded = 0
        start = time.monotonic()
        hasher = hashlib.sha256()

        with open(dest, "wb") as fh:
            while True:
                chunk = _safe_read(response, 8192)
                if not chunk:
                    break
                fh.write(chunk)
                hasher.update(chunk)
                downloaded += len(chunk)
                _print_progress(downloaded, total, start)

        # Clear progress line on TTY
        if sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 72 + "\r")
            sys.stderr.flush()

        return hasher.hexdigest()
    finally:
        response.close()


# ---------------------------------------------------------------------------
# Download and verify
# ---------------------------------------------------------------------------


def _download_and_verify() -> Path:
    """Download iBazel binary, verify checksum, atomic-move to cache.

    Uses a temp file in the same directory as the final path to avoid
    cross-device rename failures.  The executable bit is set AFTER SHA256
    verification passes.

    Raises:
        IBazelError: On download failure or checksum mismatch.
    """
    cache_dir = _ensure_cache_dir()
    final_path = _get_cache_path()
    expected_hash = _CHECKSUMS[_get_platform_suffix()]
    url = f"{_GITHUB_RELEASES_URL}/ibazel_{_get_platform_suffix()}"

    output.info(f"Downloading iBazel {_IBAZEL_VERSION}...")

    # Temp file in same dir as final path (avoids cross-device rename)
    fd = tempfile.NamedTemporaryFile(
        dir=cache_dir, prefix=".ibazel-download-", delete=False
    )
    tmp_path = Path(fd.name)
    try:
        fd.close()  # Close fd so _download_with_progress can open the file
        actual_hash = _download_with_progress(url, tmp_path)

        if actual_hash != expected_hash:
            raise IBazelError(
                f"SHA256 checksum mismatch for iBazel binary!\n"
                f"  Expected: {expected_hash}\n"
                f"  Actual:   {actual_hash}",
                recovery="This may indicate a supply chain attack. Do NOT retry.",
            )

        os.rename(str(tmp_path), str(final_path))
        os.chmod(str(final_path), 0o755)  # nosec B103
        output.success(f"iBazel {_IBAZEL_VERSION} downloaded and verified")
        return final_path
    except BaseException:
        # Clean up temp file on ANY failure (including KeyboardInterrupt)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def ensure_ibazel() -> Path:
    """Return path to a verified iBazel binary.

    Resolution order:

    1. System iBazel on PATH with exact version match.
    2. Cached binary at ``~/.cache/cmk-dev-deploy/`` (re-verified via SHA256).
    3. Download from GitHub releases, verify SHA256, cache.

    Raises:
        IBazelError: On download failure, checksum mismatch, corrupt cache,
            unsupported platform, or cache directory creation failure.
    """
    # 1. Check system iBazel
    system_path = _detect_system_ibazel()
    if system_path is not None:
        return system_path

    # 2. Check cached binary (re-verify SHA256 on every use)
    cache_path = _get_cache_path()
    if cache_path.exists():
        if _verify_sha256(cache_path):
            return cache_path
        # Corrupt cached binary -- error with manual delete instructions
        raise IBazelError(
            f"Cached iBazel binary failed SHA256 verification: {cache_path}",
            recovery=f"Delete the file and retry: rm {cache_path}",
        )

    # 3. Download and verify
    return _download_and_verify()
