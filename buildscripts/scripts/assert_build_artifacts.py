#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

import hashlib
import json
import re
import shutil
import sys
import tempfile
from argparse import ArgumentParser, BooleanOptionalAction
from argparse import Namespace as Args
from collections.abc import Iterator
from os import environ
from pathlib import Path
from typing import get_args, Literal, NamedTuple, Protocol, Self

import requests

sys.path.insert(0, Path(__file__).parent.parent.parent.as_posix())
from buildscripts.scripts.lib.common import (
    flatten,
    load_editions_file,
)

sys.path.insert(0, (Path(__file__).parent.parent.parent / "packages" / "cmk-ccc").as_posix())
from cmk.ccc.version import Edition, Version

HTTP_STATUS_OK = 200
DOCKER_HUB_API = "https://hub.docker.com/v2"
NEXUS_DOCKER_API = "https://artifacts.lan.tribe29.com:4000/v2"
RELAY_IMAGE_NAME = "checkmk/check-mk-relay"
EXIT_CODE_RELAY_MISSING = 2
RELAY_PSEUDO_EDITION = "relay"

UseCase = Literal["release", "daily", "weekly"]
MetaFileExtension = Literal["json", "csv"]

# FQIN -> Fully Qualified Image Name
# The format is: registryhost[:port]/repository/imagename[:tag]
type FQIN = str
type DockerTag = str


class Credentials(NamedTuple):
    username: str
    password: str


class DockerImage(NamedTuple):
    image_name: str
    tag: DockerTag

    def full_name(self) -> FQIN:
        return f"{self.image_name}:{self.tag}"

    @classmethod
    def from_str(cls, fqin: FQIN) -> Self:
        image_name, tag = fqin.rsplit(":", 1)
        return cls(image_name, tag)


class ImageExistsFunc(Protocol):
    def __call__(
        self, base_url: str, version: str, image: DockerImage, session: requests.Session
    ) -> bool: ...


class Registry(NamedTuple):
    editions: list[str]
    url: str
    credentials: Credentials
    image_exists: ImageExistsFunc


def get_url(version: Version) -> str:
    if version.release_candidate.value:
        return f"https://tstbuilds-artifacts.lan.tribe29.com/{version.version_rc_aware}"
    return f"https://download.checkmk.com/checkmk/{version.version_rc_aware}"


def hash_file(artifact_name: str) -> str:
    return f"{artifact_name}.hash"


def build_source_artifacts(version: Version, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        file_name = f"check-mk-{edition}-{version.version_without_rc}.tar.gz"
        internal_only = edition in loaded_yaml.get("internal_editions", [])
        yield file_name, internal_only
        yield hash_file(file_name), internal_only


def build_docker_artifacts(version: Version, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        file_name = f"check-mk-{edition}-docker-{version.version_without_rc}.tar.gz"
        internal_only = edition in loaded_yaml.get("internal_editions", [])
        yield file_name, internal_only
        yield hash_file(file_name), internal_only


def build_docker_image_name_and_registry(
    version: str, loaded_yaml: dict, registries: list[Registry]
) -> Iterator[tuple[DockerImage, str, Registry]]:
    def build_folder(ed: str) -> str:
        match ed:
            case "community" | "ultimate" | "ultimatemt" | "pro":
                return "checkmk/"
            case "cloud":
                return ""
            case _:
                raise RuntimeError(f"Unknown edition {ed}")

    for edition in loaded_yaml["editions"]:
        registry = edition_to_registry(edition, registries)
        yield (
            DockerImage(tag=version, image_name=f"{build_folder(edition)}check-mk-{edition}"),
            edition,
            registry,
        )


def distro_code(distro: str) -> str:
    """Resolve a distro id (e.g. "ubuntu-22.04") to its build codename (e.g. "jammy")
    by reading DISTRO_CODE from the omd/distros/<VENDOR>_<VERSION>.mk file
    """
    if distro.startswith("cma"):
        # CMA builds have no omd/distros/*.mk entry they are just CMA files
        return distro

    distros_dir = Path(__file__).parent.parent.parent / "omd" / "distros"
    distro_code_regex = re.compile(r"^DISTRO_CODE\s*=\s*(\S+)", re.MULTILINE)

    vendor, _, version = distro.partition("-")
    mk_file = distros_dir / f"{vendor.upper()}_{version.upper()}.mk"
    if not mk_file.exists():
        # the codename might be already resolved or it is an EOL distro without a current omd/distros/*.mk entry
        return distro

    match = distro_code_regex.search(mk_file.read_text())
    if not match:
        raise ValueError(f"No DISTRO_CODE found in {mk_file}")
    return match.group(1)


def cmk_package_filename(edition: Edition, distro: str, version: str) -> str:
    """Build the Checkmk package filename for a given edition/distro/version

    The parameter "distro" can be either a raw distro id ("ubuntu-22.04") or an already-resolved codename (e.g. "jammy")
    """
    codename = distro_code(distro)
    version = version.split("-rc", maxsplit=1)[0]

    if codename.startswith(("sles", "el")):
        return f"check-mk-{edition.long}-{version}-{codename}-38.x86_64.rpm"
    if codename.startswith("cma"):
        cma_num = codename.split("-")[1]
        return f"check-mk-{edition.long}-{version}-{cma_num}-x86_64.cma"
    return f"check-mk-{edition.long}-{version}_0.{codename}_amd64.deb"


def build_package_artifacts(
    args: Args, use_case: UseCase, loaded_yaml: dict
) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        for distro in flatten(loaded_yaml["editions"][edition][use_case]):
            package_name = cmk_package_filename(
                edition=Edition.from_long_edition(edition), distro=distro, version=args.version
            )
            internal_only = distro in loaded_yaml.get(
                "internal_distros", []
            ) or edition in loaded_yaml.get("internal_editions", [])
            yield package_name, internal_only
            yield hash_file(package_name), internal_only


def meta_file_name(edition: str, version: str, extension: MetaFileExtension) -> str:
    return f"check-mk-{edition}-{version}-bill-of-materials.{extension}"


def build_meta_artifacts(version: Version, loaded_yaml: dict) -> Iterator[tuple[str, bool]]:
    for edition in loaded_yaml["editions"]:
        bom_file_name = meta_file_name(edition, version.version_without_rc, "json")
        csv_file_name = meta_file_name(edition, version.version_without_rc, "csv")
        internal_only = edition in loaded_yaml.get("internal_editions", [])
        yield bom_file_name, internal_only
        yield hash_file(bom_file_name), internal_only
        yield csv_file_name, internal_only
        yield hash_file(csv_file_name), internal_only

    relay_bom_file_name = meta_file_name(RELAY_PSEUDO_EDITION, version.version_without_rc, "json")
    yield relay_bom_file_name, False
    yield hash_file(relay_bom_file_name), False


def latest_version_alias(args: Args) -> str:
    if args.version_agnostic:
        return "latest"
    return f"{Version.from_str(args.version).base}-latest"


def build_meta_file_latest_mapping(
    args: Args, loaded_yaml: dict, file_type: MetaFileExtension
) -> dict[str, str]:
    return {
        meta_file_name(edition, latest_version_alias(args), file_type): meta_file_name(
            edition, args.version, file_type
        )
        for edition in loaded_yaml["editions"]
        if edition not in loaded_yaml.get("internal_editions", [])
    }


def build_relay_meta_file_latest_mapping(args: Args) -> dict[str, str]:
    return {
        meta_file_name(RELAY_PSEUDO_EDITION, latest_version_alias(args), "json"): meta_file_name(
            RELAY_PSEUDO_EDITION, args.version, "json"
        )
    }


def get_credentials() -> Credentials:
    return Credentials(*get_cmk_download_credentials())


def get_cmk_download_credentials() -> tuple[str, str]:
    jenkins_credentials_file_path = Path("/home") / "jenkins" / ".cmk-credentials"
    etc_credentials_file_path = Path("/etc") / ".cmk-credentials"
    user_credentials_file_path = Path("~").expanduser() / ".cmk-credentials"
    credentials_file_path = (
        jenkins_credentials_file_path
        if jenkins_credentials_file_path.exists()
        else (
            user_credentials_file_path
            if user_credentials_file_path.exists()
            else etc_credentials_file_path
        )
    )
    try:
        with credentials_file_path.open() as credentials_file:
            username, password = credentials_file.read().strip().split(":", maxsplit=1)
            return username, password
    except OSError:
        raise RuntimeError(
            f"Missing file: {credentials_file_path} (Create with content: USER:PASSWORD)"
        )


def file_exists_on_download_server(
    filename: str, version: Version, credentials: Credentials
) -> bool:
    url = f"{get_url(version)}/{filename}"
    sys.stdout.write(f"Checking for {url}...")
    if (
        requests.head(
            url,
            auth=(credentials.username, credentials.password),
            timeout=10,
        ).status_code
        != HTTP_STATUS_OK
    ):
        sys.stdout.write(" MISSING\n")
        return False
    sys.stdout.write(" AVAILABLE\n")
    return True


class ArtifactState(NamedTuple):
    missing: str = "ARTIFACT_MISSING"
    present: str = "ARTIFACT_PRESENT"


class AssertResult(NamedTuple):
    assertion_ok: bool
    message: str


def assert_presence_on_download_server(
    version: Version, internal_only: bool, artifact_name: str, credentials: Credentials
) -> AssertResult:
    if not file_exists_on_download_server(artifact_name, version, credentials) != internal_only:
        return AssertResult(
            assertion_ok=False,
            message=(
                f"{ArtifactState().present if internal_only else ArtifactState().missing}: "
                f"{artifact_name} should {'not ' if internal_only else ''}"
                "be available on download server!"
            ),
        )

    return AssertResult(assertion_ok=True, message="")


def assert_hash_matches_package_content(
    filename: str, version: Version, credentials: Credentials
) -> AssertResult:
    if filename.endswith("hash"):
        # Yes, we don't have hash file for hash files
        return AssertResult(assertion_ok=True, message="not applicable")

    base_url = get_url(version)
    url = f"{base_url}/{filename}"
    hash_url = f"{base_url}/{hash_file(filename)}"

    sys.stdout.write(f"Checking if {url}'s sha256sum matches {hash_url}...")

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / filename
        hash_path = Path(temp_dir) / f"{hash_file(filename)}"

        try:
            _download_file(url, credentials, file_path)
            _download_file(hash_url, credentials, hash_path)
        except requests.exceptions.HTTPError as http_error:
            return AssertResult(
                assertion_ok=False, message=f"Downloading file failed: {http_error}"
            )

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        # Read the expected hash from the hash file
        with open(hash_path) as f:
            expected_hash = f.read().strip().split()[0]

        if not sha256.hexdigest() == expected_hash:
            sys.stdout.write(" MISMATCH!\n")
            return AssertResult(
                assertion_ok=False, message=f"File's sha256 sum does not match the hash file {url}"
            )
        sys.stdout.write(" OK\n")
        return AssertResult(assertion_ok=True, message="")


def _download_file(url, credentials: Credentials, destination: Path):
    with requests.get(
        url, auth=(credentials.username, credentials.password), stream=True, timeout=20
    ) as r:
        r.raise_for_status()

        with open(destination, "wb") as f:
            shutil.copyfileobj(r.raw, f)


def assert_relay_image_on_docker_hub(version: str) -> AssertResult:
    url = f"{DOCKER_HUB_API}/repositories/{RELAY_IMAGE_NAME}/tags/{version}/"
    sys.stdout.write(f"Checking if relay image {RELAY_IMAGE_NAME}:{version} is on Docker Hub...")
    response = requests.get(url, timeout=30)
    if response.status_code == HTTP_STATUS_OK:
        sys.stdout.write(" OK\n")
        return AssertResult(assertion_ok=True, message="")
    sys.stdout.write(f" MISSING (HTTP {response.status_code})\n")
    return AssertResult(
        assertion_ok=False,
        message=f"Relay image {RELAY_IMAGE_NAME}:{version} not found on Docker Hub!",
    )


def get_default_registries() -> list[Registry]:
    return [
        Registry(
            editions=["community", "ultimate", "ultimatemt", "pro"],
            url=DOCKER_HUB_API,
            credentials=get_credentials(),
            image_exists=image_exists_docker_hub,
        ),
        Registry(
            editions=["cloud"],
            url=NEXUS_DOCKER_API,
            credentials=Credentials(
                username=environ.get("NEXUS_USER", ""),
                password=environ.get("NEXUS_PASSWORD", ""),
            ),
            image_exists=image_exists_internal,
        ),
    ]


def edition_to_registry(edition: str, registries: list[Registry]) -> Registry:
    for registry in registries:
        if edition in registry.editions:
            return registry
    raise RuntimeError(f"Cannot determine registry for edition: {edition}!")


def image_exists_internal(
    base_url: str, version: str, image: DockerImage, session: requests.Session
) -> bool:
    url = f"{base_url}/{image.image_name}/tags/list"

    sys.stdout.write(f"Test if {image.tag} can be found in {url}...")

    exists = version in _get_existing_tags(url=url, session=session, internal=True)
    if not exists:
        sys.stdout.write(" NO!\n")
        return False
    sys.stdout.write(" OK\n")
    return True


def image_exists_docker_hub(
    base_url: str, version: str, image: DockerImage, session: requests.Session
) -> bool:
    namespace, image_name = image.image_name.split("/")
    # Current max for page_size is 100.
    # We use the maximimum to minimize requests to Dockerhub.
    url = f"{base_url}/namespaces/{namespace}/repositories/{image_name}/tags?page_size=100"

    sys.stdout.write(f"Test if {image.tag} can be found in {url}...")

    exists = version in _get_existing_tags(url=url, session=session, internal=False)
    if not exists:
        sys.stdout.write(" NO!\n")
        return False
    sys.stdout.write(" OK\n")
    return True


def _get_existing_tags(url: str, session: requests.Session, internal: bool) -> Iterator[DockerTag]:
    response = session.get(
        url,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"Failed to communicate with registry: HTTP status {response.status_code}"
            + (f"- {response.content.decode()}" if response.content else "")
        )

    json_response = response.json()

    if internal:
        tags: list[DockerTag] = json_response["tags"]
        yield from tags
    else:
        for tag in json_response["results"]:
            yield tag["name"]
        if json_response.get("next"):
            yield from _get_existing_tags(
                url=json_response.get("next"), session=session, internal=internal
            )


def assert_build_artifacts(args: Args, loaded_yaml: dict) -> None:
    credentials = get_credentials()
    version = Version.from_str(args.version)
    results = []

    for artifact_name, internal_only in build_source_artifacts(version, loaded_yaml):
        results.append(
            assert_presence_on_download_server(version, internal_only, artifact_name, credentials)
        )
        if not internal_only:
            results.append(assert_hash_matches_package_content(artifact_name, version, credentials))

    for artifact_name, internal_only in build_package_artifacts(args, args.use_case, loaded_yaml):
        results.append(
            assert_presence_on_download_server(version, internal_only, artifact_name, credentials)
        )
        if not internal_only:
            results.append(assert_hash_matches_package_content(artifact_name, version, credentials))

    for artifact_name, internal_only in build_meta_artifacts(version, loaded_yaml):
        results.append(
            assert_presence_on_download_server(version, internal_only, artifact_name, credentials)
        )
        if not internal_only:
            results.append(assert_hash_matches_package_content(artifact_name, version, credentials))

    for artifact_name, internal_only in build_docker_artifacts(version, loaded_yaml):
        results.append(
            assert_presence_on_download_server(version, internal_only, artifact_name, credentials)
        )
        if not internal_only:
            results.append(assert_hash_matches_package_content(artifact_name, version, credentials))

    if not args.skip_docker:
        registries = get_default_registries()

        for image_name, edition, registry in build_docker_image_name_and_registry(
            version=args.version, loaded_yaml=loaded_yaml, registries=registries
        ):
            session = requests.Session()
            session.auth = (registry.credentials.username, registry.credentials.password)

            this_image_exists = registry.image_exists(
                base_url=registry.url, version=args.version, image=image_name, session=session
            )
            results.append(
                AssertResult(
                    assertion_ok=this_image_exists,
                    message=f"{image_name} not found!" if not this_image_exists else "",
                )
            )

    relay_missing = False
    if not args.skip_relay:
        relay_result = assert_relay_image_on_docker_hub(args.version)
        results.append(relay_result)
        relay_missing = not relay_result.assertion_ok

    errors = [r.message for r in results if not r.assertion_ok]

    print("ARTIFACTS_COUNTED: ", len(results))
    print("ARTIFACTS_ERRORS: ", len(errors))

    if errors:
        error_msg = (
            f"The following {len(errors)} build artifacts errors were detected:\n"
            + "\n".join([str(e) for e in errors])
        )
        if relay_missing:
            sys.stderr.write(error_msg + "\n")
            sys.exit(EXIT_CODE_RELAY_MISSING)
        raise RuntimeError(error_msg)


# cloud images
# TODO


def dump_meta_artifacts_mapping(args: Args, loaded_yaml: dict) -> None:
    print(
        json.dumps(
            {
                **build_meta_file_latest_mapping(args, loaded_yaml, "json"),
                **build_meta_file_latest_mapping(args, loaded_yaml, "csv"),
                **build_relay_meta_file_latest_mapping(args),
            }
        )
    )


def parse_arguments() -> Args:
    parser = ArgumentParser()

    parser.add_argument("--editions_file", required=True)
    parser.add_argument(
        "--skip_docker", action="store_true", default=False, help="Skip docker image check"
    )
    parser.add_argument(
        "--skip_relay", action="store_true", default=False, help="Skip relay image check"
    )

    subparsers = parser.add_subparsers(required=True, dest="command")

    sub_assert_build_artifacts = subparsers.add_parser("assert_build_artifacts")
    sub_assert_build_artifacts.set_defaults(func=assert_build_artifacts)
    sub_assert_build_artifacts.add_argument("--version", required=True, default=False)
    sub_assert_build_artifacts.add_argument(
        "--use_case", required=False, default="release", choices=list(get_args(UseCase))
    )

    sub_print_bom_artifacts = subparsers.add_parser("dump_meta_artifacts_mapping")
    sub_print_bom_artifacts.set_defaults(func=dump_meta_artifacts_mapping)
    sub_print_bom_artifacts.add_argument("--version", required=True, default=False)
    sub_print_bom_artifacts.add_argument("--version_agnostic", action=BooleanOptionalAction)

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    args.func(args, load_editions_file(args.editions_file))


if __name__ == "__main__":
    main()
