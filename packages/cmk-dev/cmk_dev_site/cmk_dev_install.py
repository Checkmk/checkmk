# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""cmk-dev-install

Download and install a Checkmk version.

If the version is already installed, it will only be downloaded and installed again if
the "-f" flag is used and no site is running on that version. Either way, the version
will be made the default OMD version. This is done to ease the follow-up use of
`cmk-dev-site`, which will by default use the default OMD version to create sites.

Depending on the specified version, the script looks in the following locations:
    https://download.checkmk.com/checkmk
    https://tstbuilds-artifacts.lan.tribe29.com
The script expects credentials to be stored in ~/.cmk-credentials file in the format
user:password (please follow the instructions https://wiki.lan.checkmk.net/x/aYUuBg)
"""

import argparse
import asyncio
import getpass
import hashlib
import http.client
import logging
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import Any, Literal, NamedTuple, override

import requests

from .omd import (
    BaseVersion,
    CMKPackage,
    Edition,
    edition_value_from_package_name,
    GitVersion,
    INSTALLATION_PATH,
    PartialVersion,
    Version,
    VersionWithPatch,
    VersionWithReleaseCandidate,
    VersionWithReleaseDate,
)
from .utils import run_command as run_command_c
from .utils.cli import clean_cli_exit, report_duration, resolve_argv
from .utils.log import colorize, generate_log_decorator, get_logger
from .utils.update_check import check_for_update
from .version import __version__

logger = get_logger(__name__)
log = generate_log_decorator(logger)

CREDENTIALS_FILE = Path("~/.cmk-credentials").expanduser()
CONFIG_PATH = Path("~/.config/jenkins_jobs/jenkins_jobs.ini").expanduser()
TSBUILD_URL = "https://tstbuilds-artifacts.lan.tribe29.com"
CMK_DOWNLOAD_URL = "https://download.checkmk.com/checkmk"
DOWNLOAD_DIR = Path("/tmp")  # nosec B108


def find_cached_deb(pkg: CMKPackage, download_dir: Path = DOWNLOAD_DIR) -> Path | None:
    """Return the path to a cached .deb file in download_dir if it exists, else None."""
    path = download_dir / pkg.package_name
    return path if path.exists() else None


def run_command(  # type: ignore[explicit-any]
    args: Sequence[str],
    check: bool = True,
    error_message: str | None = None,
    raise_runtime_error: bool = True,
    text: bool = True,
    silent: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    return run_command_c(
        args,
        check=check,
        error_message=error_message,
        raise_runtime_error=raise_runtime_error,
        text=text,
        silent=silent,
        logger=logger,  # slightly hackish: pass in the right logger
        **kwargs,
    )


def build_download_url(url: str, pkg: CMKPackage) -> str:
    """
    Generate the download URL for a given package.
    """
    return f"{url}/{pkg.version.download_folder_name}/{pkg.package_name}"


@log()
def remove_package(pkg_name: str, installed_path: Path) -> None:
    """
    Remove a package using apt.
    """
    # making sure the path is relative to /omd/versions/
    if not installed_path.is_relative_to(INSTALLATION_PATH):
        raise RuntimeError(f"ERROR: Removing package failed: {installed_path} is not a valid path")
    run_command(
        [
            "sudo",
            "rm",
            "-rf",
            str(installed_path),
        ],
    )
    # Check if package is installed first
    check_result = run_command(
        [
            "dpkg",
            "-l",
            pkg_name,
        ],
        raise_runtime_error=False,
    )

    # Only attempt removal if package is installed
    if check_result.returncode == 0:
        run_command(
            [
                "sudo",
                "apt-get",
                "purge",
                "-y",
                pkg_name,
            ],
        )


def _existing_deb_path(value: str) -> Path:
    deb_path = Path(value)
    if not deb_path.is_file():
        raise argparse.ArgumentTypeError(f"deb file does not exist: {deb_path}")
    return deb_path.absolute()


def _omd_version_from_deb_path(deb_path: Path) -> str:
    # Reverse the package naming done in omd.CMKPackage.package_name:
    #   check-mk-<edition>-<version>_0.<distro>_<arch>.deb -> <version>.<edition value>
    name = re.sub(r"_0\.[^_]+_[^_]+$", "", deb_path.stem)
    name = name.removeprefix("check-mk-")
    edition_pkg, version_str = name.split("-", 1)
    return f"{version_str}.{edition_value_from_package_name(edition_pkg)}"


@log()
def install_package(pkg_path: Path) -> None:
    """
    Install a package using apt from the provided file path.
    """
    run_command(
        [
            "sudo",
            "apt-get",
            "install",
            "-y",
            str(pkg_path),
        ],
        error_message="Failed to install package",
    )


def get_user_pass() -> tuple[str, str]:
    """Get the user and password from the credentials file"""

    try:
        user, password = CREDENTIALS_FILE.read_text(encoding="utf-8").strip().split(":", 1)
        return (user, password)
    except Exception as e:
        raise RuntimeError(
            f"ERROR: Credentials file not found or is not in a correct format: {CREDENTIALS_FILE}"
            ", please follow the instructions https://wiki.lan.checkmk.net/x/aYUuBg"
        ) from e


@dataclass
class DistroVersionInfo:
    version_id: str
    version_codename: str


def get_distro_version_info() -> DistroVersionInfo:
    """Get the distribution version ID and codename for Ubuntu."""
    data = dict(
        line.split("=", 1)
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    if data.get("ID") == "ubuntu" and {"VERSION_ID", "VERSION_CODENAME"} <= data.keys():
        return DistroVersionInfo(
            version_id=data["VERSION_ID"].strip('"'),
            version_codename=data["VERSION_CODENAME"].strip('"'),
        )
    raise RuntimeError("ERROR: Unsupported distribution or missing version info.")


DISTRO_FALLBACKS: dict[str, DistroVersionInfo] = {
    "resolute": DistroVersionInfo(version_id="24.04", version_codename="noble"),
}


def distro_candidates(distro: DistroVersionInfo) -> list[DistroVersionInfo]:
    if (fallback := DISTRO_FALLBACKS.get(distro.version_codename)) is None:
        return [distro]
    return [distro, fallback]


def warn_on_distro_fallback(cmk_pkg: CMKPackage, distro: DistroVersionInfo) -> None:
    if cmk_pkg.distro_codename != distro.version_codename:
        logger.warning(
            "No %(codename)s package found, trying the %(fallback_codename)s package instead",
            {"codename": distro.version_codename, "fallback_codename": cmk_pkg.distro_codename},
        )


def redirect_discontinued_minor(base: BaseVersion) -> BaseVersion:
    """Redirect a requested 2.6 version to 3.0.

    There is no 2.6 release: the version after 2.5.0 is 3.0.0. When a user asks
    for 2.6 we understand they want 3.0, so remap the base version explicitly.
    Using ``type(base)`` preserves a ``PartialVersion`` (e.g. the bare "2.6" form).
    """
    if (base.major, base.minor) == (2, 6):
        logger.info("There is no 2.6 release; using 3.0 instead.")
        return type(base)(3, 0)
    return base


def parse_version(
    version: str,
) -> Version:
    """Parse the version string into a Version object."""

    def base(version_str: str) -> BaseVersion:
        return redirect_discontinued_minor(BaseVersion.from_str(version_str))

    if match := re.match(r"^(\d+\.\d+\.\d+)-daily$", version):
        return VersionWithReleaseDate(
            base_version=base(match.group(1)),
            release_date=datetime.today().date(),
        )

    if match := re.match(r"^(\d+\.\d)+$", version):
        return redirect_discontinued_minor(PartialVersion.from_str(match.group(1)))

    if match := re.match(r"^(\d+\.\d+\.\d+)$", version):
        return base(match.group(1))

    if match := re.match(r"^(\d+\.\d+(?:\.\d+)?)(p|b)(\d+)$", version):
        return VersionWithPatch(
            base_version=base(match.group(1)),
            patch_type="p" if match.group(2) == "p" else "b",
            patch=int(match.group(3)),
        )

    if match := re.match(r"^(\d+\.\d+(?:\.\d+)?)(p|b)(\d+)-rc(\d+)$", version):
        return VersionWithReleaseCandidate(
            base_version=base(match.group(1)),
            patch_type="p" if match.group(2) == "p" else "b",
            patch=int(match.group(3)),
            rc=int(match.group(4)),
        )
    if match := re.match(r"^git:(.+?):(.+?)$", version):
        return GitVersion(
            branch=match.group(1),
            commit_hash=match.group(2),
        )

    if match := re.match(r"^(\d+\.\d+\.\d+)-(\d+[.-]\d+[.-]\d+)$", version):
        return VersionWithReleaseDate(
            base_version=base(match.group(1)),
            release_date=datetime.strptime(match.group(2).replace(".", "-"), "%Y-%m-%d").date(),
        )

    raise argparse.ArgumentTypeError(
        f"{version!r} doesn't match expected format '2.2.0p23|2.2.0p23-rc1|2.2.0-YYYY-MM-DD|"
        "2.2.0-YYYY.MM.DD|2.2|2.2.0-daily|git:<branch>:<commit_hash>'"
    )


class FileServer:
    """Represents a file server to download packages from."""

    def __init__(
        self,
        user: str,
        password: str,
    ):
        self.user = user
        self.password = password
        self._session = requests.Session()
        self._session.auth = (user, password)
        self._timeout = 120

    def _get(self, url: str, **kwargs: Any) -> requests.Response:  # type: ignore[explicit-any]
        try:
            response = self._session.get(url, timeout=self._timeout, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"ERROR: {e}") from e

        return response

    @log(max_level=logging.DEBUG)
    def download_hash(self, download_url: str) -> str:
        """Download the hash file for a given file."""
        response = self._get(f"{download_url}.hash")

        hash_data = response.text.strip().split()

        if not hash_data:
            raise ValueError("Empty or invalid hash file.")

        return hash_data[0]

    def _calculate_file_hash(self, file_path: Path, hash_type: str = "sha256") -> str:
        """
        Calculate the hash of a file.

        :param file_path: Path to the file.
        :param hash_type: Hash algorithm (e.g., 'sha256', 'md5', 'sha1').
        :return: Hexadecimal hash of the file.
        """
        try:
            with open(file_path, "rb") as f:
                digest = hashlib.file_digest(f, hash_type)
            return digest.hexdigest()
        except FileNotFoundError as e:
            raise RuntimeError(f"ERROR: File not found: {file_path}") from e

    @log()
    def verify_hash(self, download_url: str, file_path: Path) -> bool:
        """
        Verify the hash of a file.
        :param download_url: The URL of the hash file.
        :param file_path: Path to the file.
        :return: True if the hash matches, False otherwise.
        """
        file_hash = self.download_hash(download_url)
        calculated_hash = self._calculate_file_hash(file_path)

        return file_hash == calculated_hash

    @log()
    def download_package(
        self,
        url: str,
        download_path: Path,
    ) -> None:
        """
        Downloads a package from the file server.

        :param url: The URL of the package.
        :param download_path: The local path where the package will be saved.
        """

        start = time.monotonic()
        response = self._get(
            url,
            stream=True,
        )

        file_size = int(response.headers["Content-Length"])
        with open(download_path, "wb") as file:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                file.write(chunk)
                downloaded += len(chunk)
                progress = (downloaded / file_size) * 100
                download_rate = downloaded / 1024 / 1024 / (time.monotonic() - start)
                logger.progress(f"Downloading... {progress:.2f}% ({download_rate:.2f} MB/s)")

    def _query_available_versions(self, url: str) -> Sequence[VersionWithReleaseDate]:
        response = self._get(url)
        vs_parser = VersionParser()
        vs_parser.feed(response.text)
        return vs_parser.versions

    @log(max_level=logging.DEBUG)
    def list_folders(self, url: str) -> list[str]:
        link_parser = FolderLinkParser()
        link_parser.feed(self._get(f"{url}/").text)
        return link_parser.folders

    @log(max_level=logging.DEBUG)
    def list_versions_with_date(
        self, url: str, base_version: BaseVersion
    ) -> list[VersionWithReleaseDate]:
        return [vs for vs in self._query_available_versions(url) if vs.base_version == base_version]

    @log()
    def query_latest_base_version(self, urls: list[str]) -> BaseVersion:
        # if we have no version *at all*, this raises.
        return max(
            (v.base_version for url in urls for v in self._query_available_versions(url)),
        )

    @log(max_level=logging.DEBUG)
    def url_exists(self, url: str) -> bool:
        response = self._session.head(
            url,
            timeout=self._timeout,
        )
        return response.status_code == HTTPStatus.OK


class VersionParser(HTMLParser):
    """
    This class is used to parse the versions from the Checkmk download page with re.Pattern.
    """

    def __init__(self) -> None:
        super().__init__()
        self._versions: list[VersionWithReleaseDate] = []
        self._pattern = re.compile(r"^(\d+\.\d+\.\d+)-(\d+.\d+.\d+)")

    @property
    def versions(self) -> Sequence[VersionWithReleaseDate]:
        return self._versions

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)

        if tag == "a" and (href := attrs_dict.get("href")) and (match := self._pattern.match(href)):
            self._versions.append(
                VersionWithReleaseDate(
                    base_version=BaseVersion.from_str(match.group(1)),
                    release_date=datetime.strptime(match.group(2), "%Y.%m.%d").date(),
                )
            )


class FolderLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.folders: list[str] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        href = dict(attrs).get("href")
        if tag == "a" and href and href.endswith("/") and not href.startswith(("/", "?", ".")):
            self.folders.append(href.removesuffix("/"))


@log()
def resolve_release_candidate_folder(
    file_server: FileServer, url: str, version: VersionWithReleaseCandidate
) -> VersionWithReleaseCandidate:
    """Find the folder of a release candidate, which may carry a suffix like "+security"."""
    expected = version.download_folder_name
    suffixes = sorted(
        match.group(1) or ""
        for folder in file_server.list_folders(url)
        if (match := re.fullmatch(rf"{re.escape(expected)}(\+.+)?", folder))
    )
    if not suffixes:
        raise RuntimeError(f"ERROR: Release candidate folder {expected} not found in {url}")
    return VersionWithReleaseCandidate(
        base_version=version.base_version,
        patch_type=version.patch_type,
        patch=version.patch,
        rc=version.rc,
        folder_suffix=suffixes[0],
    )


@log()
def validate_jenkins_jobs_ini() -> bool:
    """
    Validate the jenkins_jobs.ini file exists or not.
    """

    if not CONFIG_PATH.exists():
        this_user_name = run_command(["git", "config", "user.email"]).stdout.strip().split("@")[0]
        config_content = f"""
In order to interact with Jenkins you need to have a file at
"~/.config/jenkins_jobs/jenkins_jobs.ini" containing the following content

# start of file
[jenkins]
user={this_user_name}
# Get the APIKEY from the CI web UI, click top right Profile -> Security -> Add new Token
# https://ci.lan.tribe29.com/user/{this_user_name}/security
password=API_KEY_NOT_YOUR_PASSWORD
url=https://ci.lan.tribe29.com
query_plugins_info=False
# end of file
"""
        logger.error(
            config_content,
        )
        return False
    return True


def unify_ci_artifacts_logging() -> None:
    """Route checkmk-dev-tools log output through our stderr handler."""
    ci_logger = logging.getLogger("trickkiste.cmk-dev")
    if not ci_logger.handlers:
        get_logger("trickkiste.cmk-dev")
    ci_logger.propagate = False
    ci_logger.setLevel(logger.getEffectiveLevel())


@log()
def build_install_git_version(
    branch: str, commit_hash: str, edition: Edition, distro_id: str
) -> Path:
    """
    Build and install a version from a specific branch and commit hash.

    :param branch: The branch to build the version from.
    :param commit_hash: The commit hash to build the version from.
    :param edition: The edition of the version.
    :param distro_id: The distro ID to build the version for.
    :return: The path to the built package.
    """
    from cmk_dev.ci_artifacts import (  # pyright: ignore[reportMissingTypeStubs]
        fetch_artifacts,
    )

    if not validate_jenkins_jobs_ini():
        raise RuntimeError("ERROR: Jenkins jobs ini file is not found")

    job_name = "trigger-cmk-distro-package"
    job_edition = str(edition.name.lower())
    if branch in ("2.3.0", "2.4.0"):
        job_name = "build-cmk-distro-package"
        job_edition = job_edition.removeprefix("old_")

    unify_ci_artifacts_logging()
    result = asyncio.run(
        fetch_artifacts(
            f"checkmk/{branch}/builders/{job_name}",
            params={
                "DISTRO": f"ubuntu-{distro_id}",
                "EDITION": job_edition,
                "CUSTOM_GIT_REF": commit_hash,
            },
            out_dir=DOWNLOAD_DIR,
            no_remove_others=True,
        )
    )
    if result["result"] == "FAILURE":
        raise RuntimeError("ERROR: Failed to build the version.")

    filtered_artifacts = [
        artifact
        for artifact in result["artifacts"]
        if "check-mk" in artifact and artifact.endswith(".deb")
    ]

    if not filtered_artifacts:
        raise RuntimeError("ERROR: No artifacts found for the version.")

    return DOWNLOAD_DIR / filtered_artifacts[0]


@log(show_result=True)
def find_last_release(
    download_urls: list[str],
    file_server: FileServer,
    base_version: BaseVersion,
    edition: Edition,
    distro_codenames: Sequence[str],
) -> CMKPackage:
    """
    Find the last release date for a version.
    """
    url_version_date = [
        (url, v_date)
        for url in download_urls
        for v_date in file_server.list_versions_with_date(url, base_version)
    ]
    url_version_date.sort(key=lambda p: p[1].release_date, reverse=True)

    for url, version_date in url_version_date:
        for distro_codename in distro_codenames:
            pkg = CMKPackage(
                version=version_date,
                edition=edition,
                distro_codename=distro_codename,
            )
            if file_server.url_exists(build_download_url(url, pkg)):
                return pkg

    raise RuntimeError(f"ERROR: No release found for the version {base_version}")


def select_package(
    file_server: FileServer,
    download_urls: list[str],
    version: VersionWithPatch | VersionWithReleaseDate | BaseVersion | VersionWithReleaseCandidate,
    edition: Edition,
    distro_codenames: Sequence[str],
    download_dir: Path = DOWNLOAD_DIR,
) -> CMKPackage:
    """
    Return the package for the first distro codename that is cached or available for download.
    The last codename is returned without checking, so a missing package is reported on download.
    """
    *preferred, last = (
        CMKPackage(version=version, edition=edition, distro_codename=distro_codename)
        for distro_codename in distro_codenames
    )
    for pkg in preferred:
        if find_cached_deb(pkg, download_dir) is not None or any(
            file_server.url_exists(build_download_url(url, pkg)) for url in download_urls
        ):
            return pkg
    return last


@log(max_level=logging.DEBUG)
def find_sitenames_by_version(version: str) -> list[str]:
    """
    Get the list of sitenames that are running by a specific version
    """
    site_names: list[str] = []
    try:
        for path in Path("/omd/sites").glob("*"):
            path = path / "version"
            if path.is_symlink():
                target = path.readlink()  # Read the symlink target
                site_version = target.name  # Extract the version from the target path
                site_name = path.parent.name
                if site_version == version:
                    site_names.append(site_name)
        return site_names
    except OSError as e:
        raise RuntimeError(f"ERROR: {e.strerror}") from e


def apply_acls_to_version(version: str) -> None:
    """
    Apply ACLs to omd version.
    """
    version_path = INSTALLATION_PATH / version
    user = getpass.getuser()

    if not version_path.exists():
        raise RuntimeError(f"ERROR: Version {version_path.name} does not exist")
    if not shutil.which("setfacl"):
        logger.warning(
            "'setfacl' not found, skipping ACL setup for %(version)s. "
            "As a result, you may not be able to write files or apply changes "
            "in %(version_path)s as the current user. "
            "To fix this, install the 'acl' package and reinstall the version:\n"
            "  sudo apt-get install acl\n",
            {"version": version, "version_path": version_path},
        )
        return
    run_command(
        [
            "sudo",
            "setfacl",
            "--recursive",
            "-m",
            f"user:{user}:rwX",
            str(version_path),
        ],
    )


def get_default_version() -> str:
    return run_command(["sudo", "omd", "version", "-b"]).stdout.strip()  # type: ignore[no-any-return]


@log(max_level=logging.DEBUG)
def set_default_version(version: str) -> None:
    """
    Set the default version to the specified version.
    """
    if version == get_default_version():
        return
    run_command(
        ["sudo", "omd", "setversion", version],
    )


@log()
def ensure_sudo() -> None:
    """It increases the sudo timeout and refreshes it."""
    run_command(["sudo", "-v"])


class ArgFormatter(argparse.RawTextHelpFormatter):
    pass


class DevInstallArgs(argparse.Namespace):
    build: Version
    edition: Edition
    force: bool
    verbose: int
    quiet: int
    download_only: bool
    path: Path | None


def create_parser() -> argparse.ArgumentParser:
    assert __doc__ is not None, "__doc__ must be a non-None string"  # type: ignore[comparison-overlap]
    prog, descr = __doc__.split("\n", 1)

    parser = argparse.ArgumentParser(
        prog=prog,
        description=descr,
        formatter_class=ArgFormatter,
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def setup_parser(parser: argparse.ArgumentParser) -> None:
    """Setup the argument parser for the script."""

    parser.add_argument(
        "build",
        metavar="build-version",
        type=parse_version,
        nargs="?",
        help=f"""specify the build version in one of the following formats:

  {colorize("2.4.0-daily", "green")}: install today's daily version
  {colorize("2.4", "green")}: install the latest available daily build
  {colorize("2.4.0-YYYY-MM-DD", "green")} (e.g. 2.4.0-2025-01-30): install specific daily version
  {colorize("2.4.0p23", "green")}: install released patch version
  {colorize("2.4.0p23-rc1", "green")}: install a release candidate from tstbuilds
  {colorize("git:master:39f57c98f92", "green")}: Build and install from a specific
    branch and commit

Per default it will try to install the daily version of the
latest branch that can be found.
""",
    )

    parser.add_argument(
        "-e",
        "--edition",
        type=Edition,
        default=None,
        choices=Edition,
        help="specify the edition of the version to install (default: %(default)s).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force re-downloading and installing the version.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output verbosity",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="suppress stderr output.'-q': suppress info, '-qq': suppress warnings.",
    )
    parser.add_argument(
        "-d",
        "--download-only",
        action="store_true",
        help="download only (do not install)",
    )
    parser.add_argument(
        "-p",
        "--path",
        type=_existing_deb_path,
        help="specify the deb file to install",
    )


@log(max_level=logging.DEBUG)
def validate_installation(cmk_pkg: CMKPackage, force: bool, download_only: bool) -> bool:
    """
    Validate if the installation should go through.
    """
    already_installed = (INSTALLATION_PATH / Path(cmk_pkg.omd_version)).exists()

    if already_installed and not (force or download_only):
        logger.warning(
            "Version %(path)s already installed.",
            {"path": INSTALLATION_PATH / Path(cmk_pkg.omd_version)},
        )
        logger.warning("Use --force to re-download and re-install.")

        return False

    if (
        already_installed
        and (existed_sitenames := find_sitenames_by_version(cmk_pkg.omd_version))
        and not download_only
    ):
        nl = "\n"
        raise RuntimeError(
            f"Found sites existed with the version {cmk_pkg.omd_version}: {existed_sitenames}\n"
            "Please remove the site, before reinstalling using:\n"
            f"""{
                nl.join(
                    [
                        f"sudo omd -f rm --kill --apache-reload {sitename}"
                        for sitename in existed_sitenames
                    ]
                )
            }"""
        )

    return True


def _fetch_and_verify(
    file_server: FileServer,
    urls: list[str],
    cmk_pkg: CMKPackage,
    download_path: Path,
) -> None:
    """Find a valid download URL, fetch the package, and verify its hash."""
    valid_url = None
    for url in urls:
        logger.debug("Checking URL: %(url)s", {"url": url})
        pkg_url = build_download_url(url, cmk_pkg)

        if not file_server.url_exists(pkg_url):
            logger.warning(
                "Version %(version)s not found in the download server %(url)s",
                {"version": cmk_pkg, "url": url},
            )
        else:
            valid_url = pkg_url
            break

    if valid_url is None:
        raise RuntimeError("Download URL not found.")
    file_server.download_package(
        url=valid_url,
        download_path=download_path,
    )
    if not (file_server.verify_hash(valid_url, download_path)):
        raise RuntimeError("ERROR: Hash verification failed.")


def download_and_install_cmk_pkg(
    file_server: FileServer,
    urls: list[str],
    cmk_pkg: CMKPackage,
    force: bool,
    download_only: bool,
) -> CMKPackage:
    """
    Download and install a Checkmk package.
    """
    if not validate_installation(cmk_pkg, force, download_only):
        set_default_version(cmk_pkg.omd_version)
        return cmk_pkg

    download_path = DOWNLOAD_DIR / cmk_pkg.package_name
    cached = find_cached_deb(cmk_pkg, DOWNLOAD_DIR)
    if cached is not None and not force:
        logger.info("Found cached .deb at %(path)s, skipping download", {"path": cached})
    else:
        if cached is not None and force:
            logger.info("--force specified, ignoring cached .deb")
        _fetch_and_verify(file_server, urls, cmk_pkg, download_path)
    if not download_only:
        remove_package(cmk_pkg.package_raw_name, INSTALLATION_PATH / Path(cmk_pkg.omd_version))
        install_package(download_path)
    return cmk_pkg


@log(max_level=logging.DEBUG)
def core_logic(
    version: Version | None, edition: Edition, force: bool, download_only: bool
) -> tuple[str, Path]:
    """
    Download and Install a Checkmk version.

    :param version: The version to install.
    :param edition: The edition of the version.
    :param force: Re-download and re-install the version.
    :param download: Download only (no install).
    :return: The installed version and the package path.
    """
    if not download_only:
        ensure_sudo()

    download_urls = [CMK_DOWNLOAD_URL]
    if (
        edition is Edition.OLD_SAAS
        or edition is Edition.CLOUD
        or isinstance(version, VersionWithReleaseCandidate)
    ):
        # cloud editions and release candidates are only available via tstbuilds
        download_urls = [TSBUILD_URL]

    user, password = get_user_pass()
    file_server = FileServer(user=user, password=password)
    distro = get_distro_version_info()
    distros = distro_candidates(distro)
    distro_codenames = [d.version_codename for d in distros]

    match version:
        case GitVersion(branch=branch, commit_hash=commit_hash):
            build_distro = distros[-1]
            if build_distro != distro:
                logger.warning(
                    "Building the package for Ubuntu %(build_version)s, as builds for %(version)s may not be supported",
                    {"build_version": build_distro.version_id, "version": distro.version_id},
                )
            pkg_path = build_install_git_version(
                branch, commit_hash, edition, build_distro.version_id
            )
            install_package(pkg_path)
            # default version will point to the latest installed version
            # we don't have to figure out which git version we just installed
            installed_version = get_default_version()

        case PartialVersion():
            cmk_pkg = find_last_release(
                download_urls, file_server, version, edition, distro_codenames
            )
            warn_on_distro_fallback(cmk_pkg, distro)
            cmk_pkg = download_and_install_cmk_pkg(
                file_server=file_server,
                urls=download_urls,
                cmk_pkg=cmk_pkg,
                force=force,
                download_only=download_only,
            )
            pkg_path = DOWNLOAD_DIR / cmk_pkg.package_name
            installed_version = cmk_pkg.omd_version
        case _:
            if version is None:
                version = VersionWithReleaseDate(
                    base_version=file_server.query_latest_base_version(
                        [f"{u}/" for u in download_urls]
                    ),
                    release_date=datetime.today().date(),
                )
            if isinstance(version, VersionWithReleaseCandidate):
                version = resolve_release_candidate_folder(file_server, TSBUILD_URL, version)
            cmk_pkg = select_package(file_server, download_urls, version, edition, distro_codenames)
            warn_on_distro_fallback(cmk_pkg, distro)
            cmk_pkg = download_and_install_cmk_pkg(
                file_server=file_server,
                urls=download_urls,
                cmk_pkg=cmk_pkg,
                force=force,
                download_only=download_only,
            )
            pkg_path = DOWNLOAD_DIR / cmk_pkg.package_name
            installed_version = cmk_pkg.omd_version

    if not download_only:
        apply_acls_to_version(installed_version)

    return installed_version, pkg_path


def validate_version_edition(
    version: Version | None, edition: Edition | None
) -> tuple[Version | None, Edition]:
    # editions changed with the release of 2.5.0
    # we want to find out which editions are valid with the current version
    # if version is None, we install the newest version, so we are clearly post240:
    editions_to_use: Literal["pre250", "post240", "dontknow"] = "post240"
    if version is not None:
        # TODO: Need refactoring
        if isinstance(
            version,
            (VersionWithReleaseDate, VersionWithPatch, VersionWithReleaseCandidate),
        ):
            base_version = version.base_version
        else:
            base_version = version  # type: ignore[assignment]
        match base_version:
            case GitVersion():
                editions_to_use = "dontknow"
            case _:
                # editions changed with 2.5.0: versions older than that use the
                # old specifiers, 2.5.0 and newer (incl. 3.x) use the new ones.
                if base_version < BaseVersion(2, 5, 0):
                    editions_to_use = "pre250"

    # first we want to figure out the default edition,
    # if no explicit edition is specified by the user:
    if edition is None:
        if editions_to_use == "pre250":
            edition = Edition.OLD_ENTERPRISE
        elif editions_to_use == "post240":
            edition = Edition.PRO
        else:
            raise RuntimeError("Please specify edition if you want to build from git")

    # the user can mix editions and version, but we want to make sure
    # only versions and editions can continue that actually match:
    valid_post_240_editions = {
        Edition.COMMUNITY,
        Edition.PRO,
        Edition.ULTIMATEMT,
        Edition.ULTIMATE,
        Edition.CLOUD,
    }
    if editions_to_use == "post240" and edition not in valid_post_240_editions:
        raise RuntimeError(
            "You want to install version 2.5.0 or higher, "
            "you have to use the new Edition specifier."
            f"\nGot {edition}, expected {', '.join(sorted(valid_post_240_editions))}"
        )

    valid_pre_250_editions = {
        Edition.OLD_RAW,
        Edition.OLD_ENTERPRISE,
        Edition.OLD_MANAGED,
        Edition.OLD_CLOUD,
        Edition.OLD_SAAS,
    }
    if editions_to_use == "pre250" and edition not in valid_pre_250_editions:
        raise RuntimeError(
            "You want to install version 2.4.0 or smaller, "
            "you have to use the old Edition specifier."
            f"\nGot {edition}, expected {', '.join(sorted(valid_pre_250_editions))}"
        )

    return version, edition


class ExitCode(IntEnum):
    SUCCESS = 0
    ERROR = 1


class InstallResult(NamedTuple):
    exit_code: ExitCode
    # the resolved OMD version (e.g. "2.3" is resolved to
    # "2.3.0-2026.07.10.cee"), or None if the installation failed.
    installed_version: str | None


def execute(args: argparse.Namespace) -> InstallResult:
    """Run the installation."""
    logger.setLevel(max(logging.INFO - ((args.verbose - args.quiet) * 10), logging.DEBUG))

    if args.verbose - args.quiet > 3:
        # disable the custom logging, otherwise we see all messages twice
        logger.removeHandler(logger.handlers[0])
        logging.basicConfig(level=logging.DEBUG)
        logger_urllib = logging.getLogger("requests.packages.urllib3")
        logger_urllib.setLevel(logging.DEBUG)
        logger_urllib.propagate = True

    if args.verbose - args.quiet > 4:
        http.client.HTTPConnection.debuglevel = 1

    if logger.level <= logging.DEBUG:
        logger.debug(
            "%(label)s: %(version)s",
            {
                "label": colorize("cmk-dev-site version:", "cyan"),
                "version": colorize(str(__version__), "green"),
            },
        )

    if args.path:
        deb_path = args.path
        ensure_sudo()
        install_package(deb_path)
        omd_version = _omd_version_from_deb_path(deb_path)
        apply_acls_to_version(omd_version)
        print(omd_version)  # noqa: T201
        return InstallResult(ExitCode.SUCCESS, omd_version)

    try:
        version, edition = validate_version_edition(args.build, args.edition)
        installed_version, pkg_path = core_logic(version, edition, args.force, args.download_only)
    except RuntimeError as e:
        logger.error(e)  # noqa: TRY400
        return InstallResult(ExitCode.ERROR, None)

    print(installed_version)  # noqa: T201
    if args.download_only:
        print(pkg_path)  # noqa: T201
    return InstallResult(ExitCode.SUCCESS, installed_version)


def run(sys_argv: list[str] | None = None) -> InstallResult:
    """Run the installation and return the exit code and the resolved OMD version."""
    parser = create_parser()
    setup_parser(parser)

    args = parser.parse_args(resolve_argv(sys_argv, sys.argv[1:]), namespace=DevInstallArgs())
    return execute(args)


def main(sys_argv: list[str] | None = None) -> int:
    with check_for_update(), report_duration(), clean_cli_exit():
        return run(sys_argv).exit_code
