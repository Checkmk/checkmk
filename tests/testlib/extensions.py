import contextlib
from pathlib import Path
from typing import Iterator, NamedTuple

import pytest
import requests

from tests.testlib.site import Site


def download_extension(url: str, timeout: int = 10) -> bytes:
    try:
        response = requests.get(url, timeout=timeout)
    except requests.ConnectionError as e:
        raise pytest.skip(f"Encountered connection issues when attempting to download {url}") from e
    if not response.ok:
        raise pytest.skip(
            f"Got non-200 response when downloading {url}: {response.status_code}. "
            f"Raw response: {response.text}"
        )
    try:
        # if the response is valid json, something went wrong (we still get HTTP 200 though ...)
        raise pytest.skip(f"Downloading {url} failed: {response.json()}")
    except ValueError:
        return response.content
    return response.content


class DownloadedExtension(NamedTuple):
    name: str
    version: str


@contextlib.contextmanager
def install_extension(site: Site, path: Path) -> Iterator[DownloadedExtension]:
    extension = None
    try:
        extension = add_extension(site, path)
        enable_extension(site, extension.name, extension.version)
        yield extension
    finally:
        if extension:
            disable_extension(site, extension.name, extension.version)
            remove_extension(site, extension.name, extension.version)


def add_extension(site: Site, path: Path) -> DownloadedExtension:
    command_output = site.check_output(["mkp", "add", str(path)])
    name, version = command_output.splitlines()[0].split(maxsplit=1)
    return DownloadedExtension(name, version)


def enable_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "enable", name, version])


def disable_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "disable", name, version])


def remove_extension(site: Site, name: str, version: str) -> None:
    site.check_output(["mkp", "remove", name, version])
