"""rules_pkg wrappers that keep stamped archives out of the remote cache."""

load("@rules_pkg//pkg:tar.bzl", _pkg_tar = "pkg_tar")
load("@rules_pkg//pkg:zip.bzl", _pkg_zip = "pkg_zip")

# TODO: Get rid and re-think that approach with CMK-40473
# stamp = 1 makes rules_pkg read volatile-status.txt, whose BUILD_TIMESTAMP
# changes with every invocation. The action key is therefore unique per build:
# the remote cache can never serve the result, and uploading it only evicts
# entries other builds still need. Targets packing a stamped archive inherit
# this and carry the tag explicitly, see e.g. //omd:deps_packages.
# Only a literal stamp = 1 is tagged, a select() is not resolved here.
NO_REMOTE_CACHE = "no-remote-cache"

def _with_cache_tag(kwargs):
    tags = kwargs.get("tags") or []
    if kwargs.get("stamp") == 1 and NO_REMOTE_CACHE not in tags:
        kwargs["tags"] = tags + [NO_REMOTE_CACHE]
    return kwargs

def pkg_tar(name, **kwargs):
    _pkg_tar(name = name, **_with_cache_tag(kwargs))

def pkg_zip(name, **kwargs):
    _pkg_zip(name = name, **_with_cache_tag(kwargs))
