#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package sanity check: install CMK package(s) on a clean OS in a Docker container.

For each package a matching OS container is started (the target OS is derived from
the package file name), the package is installed without any pre-existing custom
dependencies, an OMD site is created and started, and the site is checked for Python
ImportErrors and -- optionally -- missing shared-library dependencies.

Run it directly as a script (see ``--help`` for options and examples) or drive the
``CmkPackageSanity`` class from a test (see ``tests/packaging/test_package_sanity.py``).
"""

import argparse
import io
import json
import tarfile
from concurrent.futures import as_completed, ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from re import match, search
from sys import exit as sys_exit
from textwrap import dedent
from typing import ClassVar, Literal

import docker
import docker.models
import docker.models.containers
import docker.models.images
import requests


class OsContainer:
    """Base OS container. Subclasses define class-level config attributes."""

    os_type: ClassVar[Literal["linux"]] = "linux"
    os_descriptor: ClassVar[Literal["lsb", "el", "sles"]]
    os_title: ClassVar[str]
    package_format: ClassVar[Literal["deb", "msi", "rpm"]]
    package_manager: ClassVar[Literal["dnf", "apt-get", "zypper"]]
    image_name: ClassVar[str]
    yes_flag: ClassVar[str] = "-y"
    package_manager_flags: ClassVar[str] = ""
    environment: ClassVar[dict[str, str]] = {}

    def __init__(
        self,
        tag_name: str | None = None,
        os_version: Decimal | None = None,
        verbose: bool = False,
    ) -> None:
        self.tag_name = tag_name
        self.os_version = os_version
        self.verbose = verbose

        self.client = docker.from_env()
        print(f"Pulling {self.os_title} {self.tag_name} image...")
        self.image: docker.models.images.Image = self.client.images.pull(
            f"{self.image_name}:{self.tag_name}"
        )
        print("Starting container...")
        self.container: docker.models.containers.Container = self.client.containers.run(
            self.image,
            name=f"checkmk_{self.os_title}-{self.tag_name}",
            command="sleep infinity",  # keep container running
            detach=True,
        )
        self.container.reload()
        self.network_settings = self.container.attrs["NetworkSettings"]
        networks = self.network_settings.get("Networks", {})
        self.ip = self.network_settings.get(
            "IPAddress",
            next(
                (networks[network].get("IPAddress") for network in networks),
                "127.0.0.1",
            ),
        )
        for file_path, file_bytes in self.files().items():
            self.write_text_file(file_bytes=file_bytes, file_path=file_path)

    @property
    def os_label(self) -> str:
        return f"{self.os_title} {self.tag_name}"

    @staticmethod
    def step(title: str) -> None:
        print(f"\n{'─' * 60}\n{title}")

    @staticmethod
    def step_out(text: str) -> None:
        for line in text.splitlines():
            if line.strip():
                print(f"  {line}")

    def run_step(
        self, title: str, cmd: str, echo_cmd: bool = False, check: bool = True
    ) -> tuple[int, str]:
        if echo_cmd:
            self.step_out(f"$ {cmd}")
        print(title)
        all_output: list[str] = []
        pending = ""
        api = self.client.api
        exec_id = api.exec_create(self.container.id, cmd, environment=self.environment)["Id"]
        for chunk in api.exec_start(exec_id, stream=True):
            decoded = chunk.decode()
            all_output.append(decoded)
            pending += decoded
            *lines, pending = pending.split("\n")
            if self.verbose:
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
        if self.verbose and pending.strip():
            print(f"  {pending}")
        rc = api.exec_inspect(exec_id)["ExitCode"]
        output = "".join(all_output)
        if check and rc != 0:
            raise RuntimeError(f"Command failed with rc={rc}: {cmd}\n{output}")
        return rc, output

    def files(self) -> dict[str, bytes]:
        """Return the files that must be written to the container."""
        return {}

    def install_extras(self) -> None:
        """Install OS-specific prerequisites before the CMK package."""

    def run_ldd(self, binary_path: str, site_name: str) -> tuple[str, list[str]]:
        """Run ldd on a binary inside the container; return (path, missing libs)."""
        result = self.container.exec_run(
            ["bash", "-c", f'sudo -i -u "{site_name}" ldd "{binary_path}" 2>&1']
        )
        missing = [
            line.strip() for line in result.output.decode().splitlines() if "not found" in line
        ]
        return binary_path, missing

    def write_text_file(
        self,
        file_bytes: bytes,
        file_path: Path | str,
    ) -> None:
        """Write a text file to a container"""
        file_path = Path(file_path)
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(name=file_path.name)
            tarinfo.size = len(file_bytes)
            tar.addfile(tarinfo, io.BytesIO(file_bytes))
        tarstream.seek(0)
        self.container.put_archive(path=file_path.parent.as_posix(), data=tarstream)


class AlmaLinuxContainer(OsContainer):
    os_descriptor: ClassVar[Literal["lsb", "el", "sles"]] = "el"
    os_title = "AlmaLinux"
    package_format: ClassVar[Literal["deb", "msi", "rpm"]] = "rpm"
    package_manager: ClassVar[Literal["dnf", "apt-get", "zypper"]] = "dnf"
    image_name = "almalinux"

    def install_extras(self) -> None:
        epel_package = (
            f"https://dl.fedoraproject.org/pub/epel/epel-release-latest-{self.tag_name}.noarch.rpm"
        )
        self.run_step(
            f"Installing latest EPEL {self.tag_name} package...",
            f"{self.package_manager} {self.package_manager_flags} install {self.yes_flag} {epel_package}",
        )
        if self.tag_name == "8":
            self.run_step(
                "Enable powertools...",
                f"{self.package_manager} config-manager --set-enabled powertools",
            )


class AptContainer(OsContainer):
    os_descriptor: ClassVar[Literal["lsb", "el", "sles"]] = "lsb"
    package_format: ClassVar[Literal["deb", "msi", "rpm"]] = "deb"
    package_manager: ClassVar[Literal["dnf", "apt-get", "zypper"]] = "apt-get"
    environment = {"DEBIAN_FRONTEND": "noninteractive"}

    @property
    def os_label(self) -> str:
        return f"{self.os_title} {self.os_version} {self.tag_name}"


class DebianContainer(AptContainer):
    os_title = "Debian"
    image_name = "debian"
    _CODENAME_VERSIONS: ClassVar[dict[str, Decimal]] = {
        "jessie": Decimal("8"),
        "stretch": Decimal("9"),
        "buster": Decimal("10"),
        "bullseye": Decimal("11"),
        "bookworm": Decimal("12"),
        "trixie": Decimal("13"),
        "forky": Decimal("14"),
    }


class UbuntuContainer(AptContainer):
    os_title = "Ubuntu"
    image_name = "ubuntu"

    @staticmethod
    def series() -> dict[str, Decimal]:
        """Return Ubuntu series (i.e. tags and versions)"""
        sources_url = "https://api.launchpad.net/devel/ubuntu/series"
        return {
            _.get("name", ""): Decimal(_.get("version", ""))
            for _ in json.loads(requests.get(sources_url).text).get("entries", {})
        }

    def files(self) -> dict[str, bytes]:
        """Return the files that must be written to the container."""
        return {
            "/etc/apt/sources.list.d/ubuntu.sources": dedent(f"""
            Types: deb
            URIs: http://de.archive.ubuntu.com/ubuntu/
            Suites: {self.tag_name} {self.tag_name}-updates
            Components: main universe
            Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

            Types: deb
            URIs: http://security.ubuntu.com/ubuntu/
            Suites: {self.tag_name}-security
            Components: main universe
            Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

            """).encode("utf-8")
        }


class SLESContainer(OsContainer):
    os_descriptor: ClassVar[Literal["lsb", "el", "sles"]] = "sles"
    os_title = "SLES"
    package_format: ClassVar[Literal["deb", "msi", "rpm"]] = "rpm"
    package_manager: ClassVar[Literal["dnf", "apt-get", "zypper"]] = "zypper"
    image_name = "registry.suse.com/bci/bci-base"
    yes_flag = ""
    package_manager_flags = "--non-interactive"

    def install_extras(self) -> None:
        self.run_step(
            "Registering PackageHub extension...",
            f"SUSEConnect -p PackageHub/{self.tag_name}/x86_64",
        )
        self.run_step(
            "Refreshing repositories...",
            f"{self.package_manager} --gpg-auto-import-keys {self.package_manager_flags} refresh",
        )
        self.run_step(
            "Installing graphviz...",
            f"{self.package_manager} {self.package_manager_flags} install {self.yes_flag} graphviz",
        )


@dataclass
class PackageResult:
    package_name: str
    os_name: str
    edition: str
    version: str
    rc: int
    broken_dependencies: dict[str, list[str]] = field(default_factory=dict)
    import_errors: list[tuple[str, str]] = field(default_factory=list)
    log: list[tuple[str, str]] = field(default_factory=list)


class PackageSanityArgs(argparse.Namespace):
    """Collects the CLI interface to the script."""

    all: bool
    check_dependencies: bool
    interactive: bool
    skip_cleanup: bool
    verbose: bool
    package_paths: list[Path]


class CmkPackageSanity:
    def __init__(
        self,
        check_dependencies: bool = False,
        interactive: bool = False,
        skip_cleanup: bool = False,
        verbose: bool = False,
        package_paths: list[Path] | None = None,
    ) -> None:
        self.args = PackageSanityArgs(
            check_dependencies=check_dependencies,
            interactive=interactive,
            skip_cleanup=skip_cleanup,
            verbose=verbose,
            package_paths=package_paths or [],
        )

    def _parse_arguments(self) -> None:
        """Define and document CLI arguments to the script."""
        parser = argparse.ArgumentParser(
            prog="cmk_package_sanity",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=dedent(
                """\
                Install Checkmk package(s) on a clean OS in a Docker container and verify
                the resulting site.

                The target OS is detected from each package file name:
                  *-elN-*.rpm                 -> AlmaLinux N (with EPEL)
                  *-slesN.N-*.rpm / *-NspN-*  -> SLES N.N (with PackageHub)
                  *.deb (known Ubuntu series) -> Ubuntu <release>
                  *.deb (other)               -> Debian <codename>

                Every package is installed with no pre-installed custom dependencies, an
                OMD site is created (and started in --interactive mode), and Python
                ImportErrors and broken shared-library dependencies are reported. The
                process exit code is the highest per-package return code (0 = all clean).

                With no PACKAGE argument, all supported packages in the current directory
                are tested.
                """
            ),
            epilog=dedent(
                """\
                examples:
                  # Test every supported package found in the current directory
                  %(prog)s

                  # Test a single package and verify its shared-library dependencies
                  %(prog)s --check-dependencies check-mk-pro-2.6.0-el9-38.x86_64.rpm

                  # Bring the site up and pause so you can browse to it, then clean up
                  %(prog)s --interactive check-mk-pro-2.6.0_0.noble_amd64.deb

                  # Keep the container and stream output for debugging after the run
                  %(prog)s --skip-cleanup --verbose check-mk-pro-*.rpm
                """
            ),
        )
        parser.add_argument(
            "--check-dependencies",
            dest="check_dependencies",
            action="store_true",
            help="Check dependencies of installed build (default: %(default)s)",
        )
        parser.add_argument(
            "--interactive",
            dest="interactive",
            action="store_true",
            help="Run container in interactive mode (default: %(default)s)",
        )
        parser.add_argument(
            "--skip-cleanup",
            dest="skip_cleanup",
            action="store_true",
            help="Skip the container cleanup (default: %(default)s)",
        )
        parser.add_argument(
            "--verbose",
            dest="verbose",
            action="store_true",
            help="Stream per-line command output from the container (default: %(default)s)",
        )
        parser.add_argument(
            dest="package_paths",
            nargs="*",
            type=Path,
            metavar="PACKAGE",
            help="Path(s) of CMK package(s) to test. Multiple packages are processed sequentially.",
        )
        self.args = parser.parse_args(namespace=PackageSanityArgs())

    @staticmethod
    def _find_packages(directory: Path) -> list[Path]:
        """Return all supported package files found in directory."""
        return sorted(directory.glob("*.deb")) + [
            p
            for p in sorted(directory.glob("*.rpm"))
            if match(r".*-el[0-9]+-.*.rpm", p.name)
            or match(r".*-sles\d+(?:\.\d+|sp\d+)-.*.rpm", p.name)
        ]

    @staticmethod
    def _parse_edition_version(name: str) -> tuple[str, str]:
        m = match(r"check-mk-([a-z]+)-([\d.]+(?:-[\d.]+)?)", name)
        return (m.group(1), m.group(2)) if m else ("", "")

    def _get_target_os(self, package_path: Path) -> OsContainer:
        name = package_path.name
        verbose = self.args.verbose
        if m := search(r"-el(\d+)-.*\.rpm$", name):
            tag = m.group(1)
            return AlmaLinuxContainer(tag_name=tag, os_version=Decimal(tag), verbose=verbose)
        if match(r".*-sles\d+(?:\.\d+|sp\d+)-.*.rpm", name):
            if m := search(r"sles(\d+\.\d+)", name):
                tag = m.group(1)
            elif m := search(r"sles(\d+)sp(\d+)", name):
                tag = f"{m.group(1)}.{m.group(2)}"
            else:
                raise ValueError(f"Cannot parse SLES version from '{name}'")
            return SLESContainer(tag_name=tag, os_version=Decimal(tag), verbose=verbose)
        if package_path.suffix == ".deb":
            for tag, version in UbuntuContainer.series().items():
                if search(rf"[._-]{tag}(?=[._-])", name):
                    return UbuntuContainer(tag_name=tag, os_version=version, verbose=verbose)
            codename = name.removesuffix(package_path.suffix).rsplit(".", 1)[-1].split("_")[0]
            return DebianContainer(
                tag_name=codename,
                os_version=DebianContainer._CODENAME_VERSIONS.get(codename, Decimal(0)),
                verbose=verbose,
            )
        raise ValueError(f'Unsupported package "{package_path}"!')

    def _process_package(
        self,
        package_path: Path,
        cleanup: bool,
        check_dependencies: bool = False,
        interactive: bool = False,
    ) -> PackageResult:
        """Install and test a single package."""
        rc = 0
        import_errors: list[tuple[str, str]] = []
        broken: dict[str, list[str]] = {}
        log: list[tuple[str, str]] = []
        target_os = self._get_target_os(package_path)
        edition, version = self._parse_edition_version(package_path.name)

        def run(title: str, cmd: str, echo_cmd: bool = False, check: bool = True) -> str:
            rc, output = target_os.run_step(title, cmd, echo_cmd=echo_cmd, check=check)
            if self.args.verbose or check and rc != 0:
                log.append((title, output))
            for line in output.splitlines():
                _, sep, rest = line.partition("ImportError:")
                if sep:
                    import_errors.append((title, ("ImportError:" + rest).strip()))
            return output

        apache_port = 5000
        site_name = "cmk"
        admin_password = "cmk"
        site_url = f"http://{target_os.ip}:{apache_port}/{site_name}/check_mk/"
        try:
            target_os.step(f"Copying {package_path.name} to container...")
            stream = io.BytesIO()
            with (
                tarfile.open(fileobj=stream, mode="w|") as tar,
                open(package_path, "rb") as f,
            ):
                info = tar.gettarinfo(fileobj=f)
                info.name = package_path.name
                tar.addfile(info, f)
            target_os.container.put_archive("/tmp", stream.getvalue())

            target_os.install_extras()

            run(
                "Updating package repo...",
                f"{target_os.package_manager} {target_os.package_manager_flags} update {target_os.yes_flag}",
            )

            install_cmd = f"{target_os.package_manager} {target_os.package_manager_flags} install {target_os.yes_flag} /tmp/{package_path.name}"
            run("Installing package file...", install_cmd, echo_cmd=True)

            create_site_cmd = f'omd create --no-tmpfs --admin-password "{admin_password}" --apache-reload "{site_name}"'
            run(
                f'Creating site "{site_name}"...',
                create_site_cmd,
                echo_cmd=True,
            )

            # NOTE: neither su nor sudo are always available by default
            run(
                "Installing sudo...",
                f"{target_os.package_manager} {target_os.package_manager_flags} install {target_os.yes_flag} sudo",
            )

            if interactive:
                run(
                    "Configuring Apache listening address...",
                    f'sudo -i -u "{site_name}" omd config set APACHE_TCP_ADDR 0.0.0.0',
                )
                run(
                    f'Starting site "{site_name}"...',
                    f'sudo -i -u "{site_name}" omd start',
                )
                print(f"Container {target_os.container.name or target_os.container.id} is ready.")
                print(f"You can access the site at {site_url}.")
                if cleanup:
                    input("To remove the container, press Enter to continue...")

            if check_dependencies:
                check_dir = f"/omd/sites/{site_name}/version"
                find_binary_cmd = (
                    f"""sudo -i -u "{site_name}" bash -c """
                    f"""'find -L "{check_dir}" -type f -exec file {{}} + | grep " ELF " | cut -d: -f1'"""
                )
                site_binaries = [
                    b
                    for b in run(
                        f"Finding binary files in {check_dir}...",
                        find_binary_cmd,
                        echo_cmd=True,
                    ).splitlines()
                    if b.strip()
                ]
                target_os.step(f"Checking ldd on {len(site_binaries)} binaries in {check_dir}...")
                with ThreadPoolExecutor(max_workers=32) as pool:
                    futures = {
                        pool.submit(target_os.run_ldd, binary, site_name): binary
                        for binary in site_binaries
                    }
                    for future in as_completed(futures):
                        binary_path, missing = future.result()
                        if missing:
                            broken[binary_path] = missing

                if broken:
                    print("Missing / Unresolvable Dependencies:")
                    for binary, libs in sorted(broken.items()):
                        print(f"  {binary}:\n    {'\n    '.join(libs)}")
                    rc = 1
                else:
                    print("All dependencies resolved.")

            import_errors = list(dict.fromkeys(import_errors))
            if import_errors:
                print("Detected Python ImportErrors:")
                for step, err in import_errors:
                    print(f"  [{step}] {err}")
                rc = 1
        finally:
            if cleanup:
                target_os.step("Stopping and removing the container...")
                target_os.container.stop()
                target_os.container.remove(force=True)
        return PackageResult(
            package_name=package_path.name,
            os_name=target_os.os_label,
            edition=edition,
            version=version,
            rc=rc,
            broken_dependencies=broken,
            import_errors=import_errors,
            log=log,
        )

    def main(self) -> None:
        self._parse_arguments()
        if not self.args.package_paths:
            self.args.package_paths = self._find_packages(Path.cwd())
            if not self.args.package_paths:
                print(
                    "Error: No supported packages found in the current directory.\n"
                    "Pass one or more package paths explicitly, or run with --help for usage."
                )
                sys_exit(2)

        if self.args.interactive and len(self.args.package_paths) > 1:
            print("Error: --interactive cannot be used with multiple packages.")
            sys_exit(2)

        missing = [p for p in self.args.package_paths if not p.is_file()]
        if missing:
            for p in missing:
                print(f"Error: Package file {p} not found.")
            sys_exit(2)

        results: list[PackageResult] = []
        for i, package_path in enumerate(self.args.package_paths):
            OsContainer.step(f"Package {i + 1}/{len(self.args.package_paths)}: {package_path.name}")
            results.append(
                self._process_package(
                    package_path,
                    cleanup=not self.args.skip_cleanup,
                    check_dependencies=self.args.check_dependencies,
                    interactive=self.args.interactive,
                )
            )

        sys_exit(max(r.rc for r in results))


if __name__ == "__main__":
    app = CmkPackageSanity()
    app.main()
